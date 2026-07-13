# Distribution Pipeline — Automated Analysis → Translation → WhatsApp

Takes a question about a 10-K filing, runs it through the RAG pipeline, translates
the grounded answer to Hebrew, and delivers it as a WhatsApp message — end to end,
with no human in the loop.

Exposed as a **webhook**, so any external system (n8n, Make, a file watcher, a cron
job) can trigger the entire flow with a single HTTP call.

---

## Why This Exists

Everything built through Chapter 11 **waits to be asked**. An analyst has to open
Swagger, type a question, and read an English answer.

The real value in a brokerage runs the other direction: a filing arrives → the
system analyzes it → translates it → and pushes the summary to the analyst or
client **in the channel they already live in**. Nobody clicks a button.

This is the **distribution layer**.

---

## Architecture

```
POST /distribute  ──→  returns 200 OK immediately
                            │
                            └──→ (background task)
                                      │
                                      ├── [1/4] retrieve()          ChromaDB
                                      ├── [2/4] generate_answer()   Claude + grounding
                                      │         └── if not found → STOP, send nothing
                                      ├── [3/4] translate_to_hebrew()   DeepL
                                      └── [4/4] send_whatsapp()         Twilio
                                                    │
                                                    ▼
                                              📱 client's phone
```

Every layer below the webhook is **imported unchanged** from earlier projects.
`pipeline.py` contains no new logic — it is pure **orchestration**.

---

## Files

| File | Role |
|---|---|
| `translator.py` | DeepL wrapper — `translate_to_hebrew(text)` |
| `whatsapp_sender.py` | Twilio wrapper — `send_whatsapp(body, to_number)` |
| `pipeline.py` | Orchestrates RAG → translate → send |
| `webhook_api.py` | FastAPI endpoint (`POST /distribute`) with background execution |

---

## Setup

### 1. DeepL (free tier: 500k chars/month)

Register at [deepl.com/pro-api](https://www.deepl.com/pro-api) → **DeepL API Free**.

### 2. Twilio WhatsApp Sandbox (free)

1. Register at [twilio.com](https://www.twilio.com)
2. Console → **Messaging → Try it out → Send a WhatsApp message**
3. From your own WhatsApp, send the join code (`join xxxx-xxxx`) to Twilio's sandbox number

**Why a sandbox?** WhatsApp forbids messaging people who haven't opted in — an
anti-spam protection. The sandbox lets you message **only numbers that explicitly
joined** (i.e. yours). Real production requires Meta approval and an approved
business number.

### 3. `.env`

```
ANTHROPIC_API_KEY=...
DEEPL_API_KEY=...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
MY_WHATSAPP_NUMBER=whatsapp:+972XXXXXXXXX
```

**Format matters:** numbers must be prefixed `whatsapp:` and in international
format (`+972`, no leading zero).

### 4. Install

```
pip install deepl twilio fastapi uvicorn
```

---

## Running

**Direct (one-shot):**
```
python pipeline.py
```

**As a service:**
```
python -m uvicorn webhook_api:app --reload
```
Then `POST http://127.0.0.1:8000/distribute` with:
```json
{"question": "What are the main risk factors?"}
```

Response is **immediate**:
```json
{"status": "accepted", "message": "Analysis started. The result will be sent via WhatsApp."}
```
The analysis runs in the background; the result arrives on WhatsApp seconds later.

---

## Key Design Decisions

### 1. Translate *after* the RAG, not inside it

The RAG answers in English; DeepL translates afterward. Claude speaks Hebrew — so
why the extra step?

| For translating last | For asking the RAG in Hebrew directly |
|---|---|
| **Separation of concerns** — each stage testable and replaceable independently | **Fewer moving parts** — one less service, one less key, one less failure point |
| **Verifiable against the source** — the answer stays in the filing's language | **Context-aware translation** — Claude *knows* it's a financial report; DeepL is a blind translator |
| **Analytical quality** — LLMs reason better in English, especially on financial terminology. Asking for Hebrew forces the model to analyze *and* translate at once | |
| **Multi-language fan-out** — one English answer → N translations, vs. N expensive RAG calls | |

The cost of this choice is terminology precision. In practice DeepL handled it
well ("year-over-year" → "לעומת השנה הקודמת", not a literal rendering).

### 2. `if not result.found: return None`

The `found: bool` field built in Chapter 8 pays off precisely here. Without this
guard, the system would faithfully translate *"Not found in the report"* into
Hebrew and WhatsApp it to a client.

**Distribution-layer principle:** always ask *"is there anything worth
distributing?"* before distributing.

### 3. Background tasks, not synchronous execution

The full pipeline takes several seconds. A synchronous endpoint would hold the
caller hanging — and a caller that times out assumes failure, even though nothing
failed.

**The pattern:** accept the request → acknowledge immediately → process in the
background → deliver the result **through a separate channel**.

**Analogy:** a delivery service doesn't keep you on the phone for 40 minutes. It
says "order received" and hangs up. The result arrives at the door — here, on
WhatsApp.

### 4. A webhook is just a FastAPI endpoint

Nothing new was needed. `POST /distribute` is structurally identical to
`POST /ask` from Chapter 9. The only difference is **who calls it**: not a human
in Swagger, but an automated system.

---

## Sample Output

**Input:**
```json
{"question": "What are the main risk factors?"}
```

**Delivered to WhatsApp:**
```
📊 ניתוח דוח

שאלה: What are the main risk factors?

גורמי הסיכון העיקריים כוללים: (1) סיכוני שוק – סיכון ריבית, סיכון השקעה
וסיכון מטבע חוץ... (6) סיכונים גיאופוליטיים – סכסוכים כגון אלה המתרחשים
במזרח התיכון ובין רוסיה לאוקראינה...

מקורות: קטעים [1, 2, 3]
```

The grounding built in Chapter 8 survives all the way to the end user.

---

## Known Limitations

1. **Silent background failures.** ⚠️ The most serious gap. Once `200 OK` is
   returned, the caller is gone. If DeepL or Twilio fails, the pipeline crashes in
   the background and **nobody finds out**. Production needs: try/except around
   each stage, a job-status store (`/status/{job_id}`), retries with backoff, and
   a dead-letter alert.
2. **No retries.** A single transient network blip loses the whole job.
3. **The question stays in English** inside a Hebrew message — a UX wart. Either
   translate the question too, or accept Hebrew input and translate it to English
   before the RAG.
4. **No authentication on the webhook.** Anyone who can reach the port can trigger
   analyses and send WhatsApp messages on your account.
5. **Twilio sandbox only.** Can message only numbers that have explicitly joined.
   Production requires Meta business verification.
6. **Cloud LLM used.** Fine for a public 10-K — but note that **the question
   itself** also leaves the machine. A question like *"is our position in Uber at
   risk?"* leaks internal information even though the filing is public. Sensitive
   questions belong on the local model (Ch. 11).
7. **Message length.** WhatsApp caps message size; long analyses would need
   splitting.
8. **n8n / Make not used.** The flow is coded directly. A visual tool would make
   it editable by non-developers — a real advantage in an organization.

---

## Tech Stack

Python · FastAPI (webhook + `BackgroundTasks`) · DeepL API · Twilio WhatsApp API ·
ChromaDB · Anthropic API · Pydantic
