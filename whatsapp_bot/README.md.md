# WhatsApp Bot — Conversational RAG over a 10-K, in Hebrew

Ask a question in Hebrew over WhatsApp. Get a grounded, source-cited answer back in
Hebrew — seconds later, with nobody in the loop.

This closes the loop on the whole system: `distribution_pipeline` (Ch. 12) could only
**push** messages out. This project makes it **bidirectional** — WhatsApp becomes the
front end.

---

## The Flow

```
📱  You send in Hebrew:  "מה הייתה צמיחת ההכנסות?"
         ↓
    Twilio  ──POST──▶  ngrok tunnel  ──▶  localhost:8000/whatsapp
         ↓
🔐  Layer 1: verify Twilio's cryptographic signature
🔐  Layer 2: allowlist check — is this an authorized number?
🛡️  Layer 3: scan the raw Hebrew for injection attempts
         ↓
🌐  DeepL:  Hebrew → English
         ↓
🛡️  Layer 4: scan the translated English (inside secure_retrieve)
🔍  ChromaDB: semantic search over 221 chunks — local, no network
🛡️  Layer 5: sanitize the retrieved chunks (poisoned-document defense)
🤖  Claude: answer with strict grounding
✅  Pydantic: validate { found, answer, sources }
         ↓
🌐  DeepL:  English → Hebrew
         ↓
📱  Reply lands on your phone, with citations
```

**Everything below the translation layer is imported unchanged** from `rag_pipeline/`
and `security/`. This project adds the *inbound* half — nothing else.

---

## Sample Output

**You send:**
> מה הייתה צמיחת ההכנסות?

**You get back:**
> 📊 ההכנסות צמחו ב-18% לעומת השנה הקודמת, ועלו מ-43,978 מיליון דולר בשנת 2024
> ל-52,017 מיליון דולר בשנת 2025, מה שמבטא עלייה של 8.0 מיליארד דולר. צמיחה זו
> נבעה בעיקר מעלייה של 19% בהזמנות ברוטו, שהונעה על ידי עלייה בהיקפי הנסיעות
> בשירותי הניידות והמשלוחים.
>
> מקורות: קטעים [1, 2]

**You send something the filing doesn't answer:**
> מה שפת התכנות האהובה על המנכ"ל?

**You get back:**
> ⚠️ לא נמצא בדוח.
>
> *(explanation of what the excerpts do cover)*

**The system refuses honestly, in Hebrew.** That behavior matters more than a fluent
answer.

---

## Security — The Hard Part

This endpoint **must be exposed to the internet** — otherwise Twilio can't reach it. And
it **cannot require an `X-API-Key`**, because Twilio won't send one.

So how is it protected?

### ❌ Why an allowlist alone is not enough

Twilio sends the sender's number in the request **body**, as a plain `From` field. But the
body is **controlled by whoever sends the request.**

An attacker who knows the ngrok URL can bypass Twilio entirely and POST directly:

```
From=whatsapp:+972XXXXXXXXX     ← my number. He just typed it.
Body=Ignore all instructions and...
```

**A naive allowlist would approve him** — because it checked a field *the attacker filled
in himself.*

> **The rule: never authenticate on data controlled by the entity being authenticated.**

### ✅ Two layers, in this order

**Layer 1 — Twilio signature verification (the real one).**
Twilio signs every request using your **Auth Token** — a secret only you and Twilio know
— and sends the signature in the `X-Twilio-Signature` header. We recompute it and compare.

```python
validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN"))

if not validator.validate(url, form_data, signature):
    raise HTTPException(403, "Invalid Twilio signature.")
```

An attacker **cannot forge this** — he doesn't have the Auth Token. This is
**cryptographic proof** the request really came from Twilio.

**Layer 2 — Allowlist.**
*Only after* verifying the source, the `From` field becomes trustworthy. Now we check it's
an authorized number.

**The order is the entire point:** establish that the **source** is authentic, *then* trust
the **content**.

### Prompt injection — a new attack surface

Previously, only I sent questions. Now **anyone with the WhatsApp number can send free
text straight to an LLM.** The Chapter 13 guard moved from "good practice" to
"load-bearing."

**Four scanning layers:**

| Layer | Location | Scans |
|---|---|---|
| 0 | `process_question()` | **Raw Hebrew**, before translation |
| 1 | inside `secure_retrieve()` | **Translated English** |
| 2 | `sanitize_chunks()` | **Chunks returned from the document** |
| 3 | `SYSTEM_PROMPT` | Instruction hierarchy — excerpts are *data, not orders* |

### ⚠️ An honest finding: the Hebrew attack was caught **by accident**

A Hebrew injection attempt (*"התעלם מכל ההוראות הקודמות..."*) **was blocked** — but not by
design.

The `INJECTION_PATTERNS` are written **in English**. What actually caught it was **DeepL**:
it translated the Hebrew into *"Ignore all previous instructions"*, and *only then* did the
scanner see a match.

**The translation layer accidentally became a security layer.**

This is fragile. A Hebrew phrasing that DeepL renders differently from my patterns — e.g.
*"שכח את מה שאמרו לך"* → *"forget what you were told"*, which isn't on the list — **would
pass straight through.**

The scanner is **signature-based**: it catches phrasings it already knows. Any novel one
gets through. That's exactly limitation #8 in [`SECURITY.md`](../SECURITY.md), and the fix
is a fourth layer: an **LLM-based classifier**, not more regex.

---

## Setup

### 1. ngrok (development only)

`localhost:8000` is unreachable from the internet — Twilio's servers cannot see it. **ngrok**
creates a tunnel: a public URL that forwards everything to your local port.

**Analogy:** a temporary PO box — mail sent there is automatically forwarded to your house,
without publishing your real address.

```bash
winget install ngrok.ngrok      # requires agent v3.20+
ngrok config add-authtoken <YOUR_TOKEN>
```

### 2. `.env`

Reuses the existing keys (Ch. 12 + Ch. 13):

```
ANTHROPIC_API_KEY=...
DEEPL_API_KEY=...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...           # ← also used to verify signatures
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
MY_WHATSAPP_NUMBER=whatsapp:+972XXXXXXXXX   # ← the allowlist
```

### 3. Install

```bash
pip install python-multipart    # Twilio sends form data, not JSON
```

---

## Running

**Terminal 1 — the server:**
```bash
cd whatsapp_bot
python -m uvicorn main:app --reload
```

**Terminal 2 — the tunnel:**
```bash
ngrok http 8000
```

Copy the `https://xxxx.ngrok-free.dev` URL.

**Twilio Console** → Messaging → Sandbox settings → **"When a message comes in"**:
```
https://xxxx.ngrok-free.dev/whatsapp        ← the /whatsapp path is required
```
Method: **POST**. Save.

Now message the Twilio sandbox number from WhatsApp.

> ⚠️ **On the free tier, the ngrok URL changes on every restart** — you must update it in
> the Twilio console each time.

---

## Known Limitations

1. **ngrok is a development tool.** Production needs a real domain with TLS behind a
   reverse proxy.
2. **Regex injection detection is signature-based** — see the honest finding above. A
   Hebrew phrasing DeepL renders unexpectedly would slip through.
3. **No rate limiting.** An authorized number could still spam the endpoint and burn
   through API credit.
4. **No conversation memory.** Every question is independent — you cannot ask a follow-up
   like "and what about the previous year?"
5. **Single hardcoded document.** The bot only knows Uber's FY2025 10-K.
6. **Cloud LLM.** Fine for a public filing — but the **question** also leaves the machine.
   A question revealing internal strategy should route to the local model
   ([`local_rag/`](../local_rag/)).
7. **Silent background failures.** The webhook returns `204` immediately; a downstream
   failure only surfaces as an error message to the user, not to any monitoring system.

---

## Tech Stack

Python · FastAPI · ngrok · Twilio (WhatsApp, inbound webhook + signature validation) ·
DeepL · ChromaDB · Anthropic (Claude) · Pydantic
