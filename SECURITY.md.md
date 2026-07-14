# SECURITY.md — Architecture, Data Governance & Threat Model

**Project:** `finance-toolkit` — LLM-powered financial document analysis
**Scope:** Where each component runs, how secrets are managed, what data leaves the
machine, what attacks this system defends against, and what I would change before
production in a regulated financial firm.

---

## 1. Threat Model — What Am I Actually Defending Against?

| # | Threat | Why it matters here | Status |
|---|---|---|---|
| **T1** | **Prompt injection** — malicious instructions hidden *inside a document* hijack the model | RAG injects **untrusted third-party text** directly into the prompt. Attack surface is far larger than a plain chatbot's. | ✅ Mitigated (3 layers) |
| **T2** | **Unauthenticated API access** | An open endpoint lets anyone trigger paid LLM calls, DeepL translations, and WhatsApp sends **on my account** | ✅ Mitigated (API key) |
| **T3** | **Arbitrary code execution** — `eval()` on model-generated input | The agent's calculator ran `eval()` on strings the LLM produced from untrusted document text | ✅ Mitigated (AST parser) |
| **T4** | **Data exfiltration to a third-party LLM** | Client data or a revealing question sent to a public API | ⚠️ Partially — architecture defined, not enforced in code |
| **T5** | **Secret leakage** | API keys committed to git, or readable from disk | ⚠️ `.env` + `.gitignore` only — insufficient for production |
| **T6** | **Hallucinated output presented as fact** | A wrong figure that *looks right* is more dangerous than an obvious error | ✅ Mitigated (grounding + Pydantic validators) |

---

## 2. Component Map — Where Everything Runs

| Component | Runs where | Data crosses the network? |
|---|---|---|
| **PDF ingestion** (`pdf_ingestor`) | Local | No |
| **Chunking** | Local | No |
| **Embedding model** (`all-MiniLM-L6-v2`) | **Local** (CPU) | No — downloaded once, then offline |
| **Vector DB** (ChromaDB) | **Local**, in-memory | No |
| **Retrieval** | Local | No |
| **LLM generation — cloud** (`generate_answer`) | **Anthropic servers** | **Yes** — excerpts + question |
| **LLM generation — local** (`generate_answer_local`) | **Local** (Ollama, `localhost:11434`) | **No** |
| **Translation** (DeepL) | **DeepL servers** | **Yes** — the final answer text only |
| **Distribution** (Twilio → WhatsApp) | **Twilio → Meta** | **Yes** — the finished message |
| **API layer** (FastAPI/uvicorn) | Local, `127.0.0.1:8000` | No — localhost only |

### The critical observation

**Retrieval and embedding are already fully local.** The vector database never
leaves the machine. Only the **generation** step reaches out — and Chapter 11
proved that step can also be run locally.

**This is the foundation of the hybrid architecture below:** the expensive,
privacy-relevant decision is isolated to **one swappable function.**

---

## 3. What Leaves the Machine — Precisely

A careless claim ("everything is local") is wrong and an interviewer will catch it.
The precise accounting:

| | Downloaded once | Sent per request |
|---|---|---|
| **Model weights** (Llama, MiniLM) | ✅ Public files, inbound only — same as `pip install` | — |
| **Retrieved excerpts** | — | ✅ **Yes**, to the cloud LLM |
| **The user's question** | — | ✅ **Yes** ⚠️ |
| **Chunks / vector DB** | — | ❌ Never |
| **The final answer** | — | ✅ To DeepL, then Twilio |

### ⚠️ The question is data too

This is the subtlety most people miss:

> The 10-K is public. But a question like **"Is our fund's position in Uber at
> risk?"** leaks internal information — *even though the document is public.*

**Therefore the governing rule is not** *"is the document public?"* **but:**

> ## **"Is EVERYTHING that leaves — document, question, AND context — public?"**

In a brokerage, the **question sometimes reveals more than the answer.**

---

## 4. Defenses Implemented

### 4.1 Prompt Injection — Defense in Depth (3 layers)

There is no perfect defense against prompt injection; it remains an open problem
in the industry. What exists is **layering**.

| Layer | Mechanism | Catches |
|---|---|---|
| **1. Input scanning** | `scan_for_injection()` — regex patterns on the user's question | Direct attacks: *"ignore all previous instructions"*, *"reveal your system prompt"* |
| **2. Retrieved-content sanitization** | `sanitize_chunks()` — **scans the chunks coming back from the document** | **Poisoned documents** — the attack most implementations miss entirely |
| **3. Instruction hierarchy** | System prompt explicitly declares excerpts to be **untrusted data, not instructions** | Attacks that slip past the regex |

**Layer 2 is the one that matters most in RAG.** Most implementations scan only user
input — but in a RAG system, the greater danger is text **inside the document**,
which the user may never have seen.

Asymmetric handling, by design:
- **Injection in the user's question** → **reject the entire request**
- **Injection inside a document chunk** → **drop that chunk, continue with the rest**
  (a document with one poisoned passage may still contain legitimate information)

**Verified by `security/test_injection.py`** — 4/4 attacks handled:

| Attack | Result |
|---|---|
| Direct instruction override | 🛑 Blocked (layer 1) |
| System-prompt extraction hidden mid-question | 🛑 Blocked (layer 1) |
| **Legitimate financial question** | ✅ **Passed through** — no false positive |
| **Poisoned chunk inside the 10-K** | 🛑 Dropped before reaching the LLM (layer 2) |

**The third test is as important as the others.** A defense that blocks innocent
questions is worthless — false positives kill products.

### 4.2 API Authentication

| | Before | After |
|---|---|---|
| `POST /ask` | 🔓 Open to anyone reaching the port | 🔒 Requires `X-API-Key` |
| `POST /distribute` | 🔓 Open — **anyone could spend my Twilio credit** | 🔒 Requires `X-API-Key` |
| `GET /health` | 🔓 Open | 🔓 **Deliberately open** — DevOps must probe liveness without a key |

**Constant-time comparison.** The check uses `secrets.compare_digest()`, not `==`.

A normal `==` **short-circuits on the first differing character**, so it returns
faster when the *first* character is wrong than when only the *last* is. An
attacker can measure that difference and recover the key **character by
character** — a **timing attack**. `compare_digest()` always takes the same time.

**Distinct status codes, deliberately:**
- `401 Unauthorized` — *no key presented* → usually a misconfigured client
- `403 Forbidden` — *key presented but wrong* → **possible key-guessing attack.** In
  production, a spike in `403`s is a **security event** worth alerting on.

### 4.3 Safe Arithmetic — Eliminating `eval()`

The agent's calculator originally ran `eval()` on expressions **generated by the
LLM from untrusted document text.** The `{"__builtins__": {}}` sandbox is *not*
airtight — known escape techniques exist, and `eval("9" * 10**9)` alone is a DoS.

**Principle: never `eval()` input you did not write.** Not user input, not model
output, not document content.

**Replacement:** `safe_calculate()` parses the expression into an **AST**, walks the
tree, and computes only nodes on an explicit **allowlist** (`+ - * / **`, unary
minus, numeric literals). Everything else is rejected by default.

**Allowlist, not blocklist** — you will always forget an entry on a blocklist. With
an allowlist, anything unanticipated is denied automatically.

**Verified by `security/test_calculator.py`** — 12/12:

| Malicious input | Result |
|---|---|
| `__import__('os').system('dir')` | 🛑 `Expression type not allowed: Call` |
| `open('.env').read()` | 🛑 Blocked — **this would have dumped every API key** |
| `eval('1+1')` | 🛑 Blocked |
| `9 ** 999999999` | 🛑 `Exponent too large` (DoS) |
| `(1).__class__.__bases__` | 🛑 `Attribute` — classic sandbox-escape technique |

Note how most attacks fail for the *same* reason: `Call` simply isn't on the
allowlist. No attack-specific logic was needed.

### 4.4 Grounding & Output Validation

Security is not only about attackers. **A confidently wrong number is a security
failure too.**

| Defense | Mechanism |
|---|---|
| **Grounding** | System prompt: answer **only** from excerpts; if not found, say so |
| **Honest refusal** | `found: false` — the system can say *"not in the report"* |
| **Citations** | `sources: [1, 2]` — every claim traceable to an excerpt |
| **Type validation** | Pydantic — the response must match `RAGAnswer` |
| **Business validation** | `@field_validator` — **rejects citations to excerpts that don't exist** |
| **Consistency validation** | `@model_validator` — rejects `found=true` with zero sources |

**This is not theoretical.** Running the same question five times against a local
Llama 3.2 produced a citation to **"Excerpt 53"** when only **3** excerpts had been
provided — plus an answer claiming `found=true` while citing nothing. Both were
caught. Without validation, the system would have displayed a fabricated citation
**with total confidence.**

### 4.5 Secrets

- All keys in `.env`; `.env` is in `.gitignore` and has **never** been committed.
- Keys: `ANTHROPIC_API_KEY`, `DEEPL_API_KEY`, `TWILIO_ACCOUNT_SID`,
  `TWILIO_AUTH_TOKEN`, `APP_API_KEY`.
- `APP_API_KEY` generated with `secrets.token_urlsafe(32)` — cryptographically
  random, not a chosen password.

**`.env` is the right *first* step and the wrong *final* one** — see §6.

---

## 5. Production Architecture — The Hybrid Model

> **If I moved this to production at a brokerage, I would run a hybrid
> architecture — and the routing rule would not be a matter of taste.**

### The decision rule

```
                    ┌─────────────────────────────────────┐
                    │  Is EVERYTHING that leaves public?   │
                    │  (document + question + context)     │
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
             YES                                        NO
              │                                          │
              ▼                                          ▼
   ┌──────────────────────┐                 ┌──────────────────────────┐
   │  CLOSED CLOUD        │                 │  LOCAL MODEL             │
   │  AWS Bedrock (Claude)│                 │  Ollama, on-prem         │
   │  or Azure OpenAI     │                 │  + strict output         │
   │                      │                 │    validation            │
   │  Best quality        │                 │  Zero egress             │
   └──────────────────────┘                 └──────────────────────────┘

   Public 10-K analysis                     Client portfolios
   Market commentary                        Undisclosed positions
   Neutral research questions               Internal memos
                                            Anything revealing strategy
```

### Why hybrid, and not one or the other

A single choice forces a bad trade:

- **Cloud-only** → best quality, but *some* data can never be sent, full stop.
  Regulation doesn't negotiate.
- **Local-only** → total privacy, but measurably worse output. Chapter 11 produced
  a **fabricated citation** and an **ungrounded answer** from the local model on the
  same question the cloud model answered correctly and consistently.

**Hybrid lets each class of data get the treatment it actually requires** — rather
than paying a privacy tax on public data, or an accuracy tax on sensitive data.

### Why AWS Bedrock for the cloud side

1. **It serves Claude** — the model this system is already built and tested against.
   No re-validation of prompts, grounding behavior, or output format.
2. **Runs inside the firm's own VPC** — data never transits Anthropic's public
   infrastructure.
3. **Contractual Zero Data Retention** — the critical promise: *company data is
   never used to train public models.* The analogy: making sure the confidential
   documents you handed the translator don't show up in the book he publishes.
4. **Audit logs, IAM, and compliance certifications** IT already understands.

*(**Azure OpenAI** is the equally defensible choice — and often the better one if
the firm is already a Microsoft shop, because it inherits Entra ID / Active
Directory identity and existing compliance posture. The deciding factor is what IT
already runs, not model preference. What matters is that it is a **closed cloud
environment with a contractual ZDR guarantee** — not the public consumer API.)*

### Why the local side is not a fallback but a requirement

The local path is not "the cheap option." For some data, **it is the only legal
option.** But — as Chapter 11 demonstrated with real logs — a local model **must**
be wrapped in strict output validation, because it hallucinates citations. Privacy
without validation just moves the risk.

---

## 6. What I Would Change Before Production

**Honest assessment of what this system is not yet ready for:**

| # | Gap | Fix |
|---|---|---|
| **1** | **`.env` on disk** — anyone with server access can read every key | **Secrets manager**: AWS Secrets Manager / Azure Key Vault / HashiCorp Vault. Adds access control, rotation, and audit trails. |
| **2** | **Single static API key** — no per-user identity, no revocation, no rate limiting | OAuth2 / OIDC via the firm's identity provider; per-client keys; rate limiting |
| **3** | **`/docs` is publicly served** — a complete map of the attack surface, handed to an attacker | Disable in production: `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)` |
| **4** | **Silent background failures** — after `200 OK`, a DeepL or Twilio failure is invisible to everyone | Job-status store, retries with backoff, dead-letter alerting |
| **5** | **No audit log** — cannot answer *"who asked what, and what did the system say?"* — a regulatory requirement | Structured logging of every request, retrieval, and response; immutable storage |
| **6** | **No PII detection** — nothing stops a user pasting a client name or account number into a question bound for the cloud | PII scanner + redaction **before** any external call |
| **7** | **In-memory vector DB** — re-indexes on every restart; no access control on the index | pgvector / managed vector store, with row-level permissions |
| **8** | **Regex-based injection detection** — signature-based, and will miss novel phrasings | Add an LLM-based classifier as a fourth layer; treat regex as necessary-but-not-sufficient |
| **9** | **No human-in-the-loop on the agent** | Mandatory approval gate before any irreversible action |

---

## 7. The One-Paragraph Answer

*If asked in an interview: "How would you ensure client data never leaks?"*

> **First, I'd note that most of this system is already local — ingestion, chunking,
> embeddings, and the vector database never touch the network. The only component
> that reaches out is generation, and I've built that as a swappable function, so
> the decision is isolated to one place.**
>
> **Second, the routing rule: anything where the document, the question, *and* the
> context are all public goes to a closed cloud environment — AWS Bedrock or Azure
> OpenAI — inside the firm's VPC with a contractual zero-data-retention guarantee.
> Anything else runs on a local model. And I'd emphasize that the *question* is data
> too: "is our position in Uber at risk?" leaks strategy even though the 10-K is
> public. That's the distinction most people miss.**
>
> **Third, the local path is not free. I tested it: the local model fabricated a
> citation to "Excerpt 53" when only three excerpts existed. So privacy requires
> validation — I built Pydantic validators that reject citations to sources that
> don't exist, and tests that prove they fire.**
>
> **Fourth, the attack I take most seriously is prompt injection, because RAG feeds
> untrusted document text straight into the prompt. I defend it in three layers, and
> the one that matters most scans the *retrieved chunks* — not just user input.
> Most implementations miss that.**
>
> **Finally, I'd tell you what's still missing: `.env` isn't good enough for
> production — that needs a secrets manager. There's no audit log, and a regulated
> firm needs one. And there's no PII redaction before external calls. Those are the
> first three things I'd fix.**

---

## 8. Reference

- **OWASP Top 10 for LLM Applications** — the canonical threat taxonomy
  (LLM01: Prompt Injection, LLM06: Sensitive Information Disclosure)
- **AWS Bedrock** / **Azure OpenAI Service** — closed cloud environments
- **Anthropic / OpenAI Enterprise & Zero Data Retention policies**

---

## Verification

Every claim in this document is backed by a test that can be run:

```
python security/test_injection.py     # 4/4 — prompt injection defenses
python security/test_calculator.py    # 12/12 — safe arithmetic
python local_rag/test_validation.py   # 5/5 — hallucinated-citation rejection
```

**A safety net you haven't tested is not a safety net — it's hope.**
