# finance-toolkit

**A grounded, secured RAG system for analyzing SEC 10-K filings — built from scratch in Python.**

Ask a natural-language question about a 200-page financial filing. Get an answer that is
**grounded in the document**, **cites its sources**, and **says "not found" instead of
guessing**. Exposed as an authenticated FastAPI service, defended against prompt injection,
and deployable with a local LLM so that sensitive data never leaves the building.

Built as the capstone of a 14-chapter self-directed course, targeting an
**AI & Automation Developer** role in financial services.

---

## The Capstone: Secured RAG over a 10-K

```
                        ┌──────────────────────────────────────────┐
                        │  1. INGESTION                            │
                        │  10-K PDF (149 pages)                    │
                        │    → pdfplumber → clean text             │
                        │    → chunker (overlap) → 221 chunks      │
                        └────────────────────┬─────────────────────┘
                                             ▼
                        ┌──────────────────────────────────────────┐
                        │  2. INDEXING                             │
                        │  chunks → embeddings (local, CPU)        │
                        │    → ChromaDB vector store               │
                        └────────────────────┬─────────────────────┘
                                             ▼
     question ─────────▶ ┌──────────────────────────────────────────┐
                        │  3. RAG CORE                             │
                        │  retrieve (top-k, semantic)              │
                        │    → augment (inject excerpts)           │
                        │    → generate (Claude, grounded)         │
                        │    → validate (Pydantic)                 │
                        └────────────────────┬─────────────────────┘
                                             ▼
                        ┌──────────────────────────────────────────┐
                        │  4. API LAYER                            │
                        │  FastAPI: POST /ask · GET /health        │
                        │  auto-generated OpenAPI docs             │
                        └────────────────────┬─────────────────────┘
                                             ▼
                        ┌──────────────────────────────────────────┐
                        │  5. SECURITY  (cross-cutting)            │
                        │  API key auth · prompt-injection guard   │
                        │  secrets in .env · output validation     │
                        └────────────────────┬─────────────────────┘
                                             ▼
                                   { found, answer, sources }
```

### What makes it different from a demo

| | Typical RAG demo | This system |
|---|---|---|
| **Hallucination** | Answers confidently, always | Returns `found: false` and explains why |
| **Citations** | None, or unverifiable prose | `sources: [1, 2]` — **validated against the excerpts actually sent** |
| **Prompt injection** | Undefended | 3 layers, including **scanning the retrieved document text** |
| **Auth** | Open endpoint | API key with constant-time comparison |
| **Code execution** | `eval()` on model output | AST allowlist parser |
| **Testing** | "It worked when I ran it" | **21 security tests, all passing** |

### Real output — the honest refusal

```
POST /ask   { "question": "what are the innovation costs?" }
```
```json
{
  "found": false,
  "answer": "Innovation costs are not explicitly broken out in the provided excerpts.
             The excerpts discuss research and development expenses, which typically
             include innovation activities, showing R&D expenses of $3,109 million in
             2024 and $3,402 million in 2025. However, there is no specific line item
             labeled 'innovation costs' in these sections.",
  "sources": [1, 2]
}
```

**The system did not invent a number.** It said what it couldn't find, offered the
closest available figure, explained the distinction, and cited its sources. In finance,
this behavior matters more than a fluent answer.

---

## Quick Start

```bash
git clone https://github.com/asafco911-cell/finance-toolkit.git
cd finance-toolkit
pip install -r requirements.txt
```

Create a `.env` file in the repo root:

```
ANTHROPIC_API_KEY=sk-ant-...
APP_API_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(32))">
```

Run the API:

```bash
cd rag_api
python -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs`, paste your `APP_API_KEY` into the `x-api-key` field,
and ask a question.

Or from the command line:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"question": "What was the revenue growth?"}'
```

**The vector index ships with the repo** (`rag_pipeline/chunks.json`, 221 chunks from
Uber's FY2025 10-K), so it runs immediately. To rebuild from the original PDF, see
[`pdf_ingestor/DATA.md`](pdf_ingestor/DATA.md).

### Verify the security layer

```bash
python security/test_injection.py     # 4/4  — prompt injection defenses
python security/test_calculator.py    # 12/12 — safe arithmetic, 5 real exploits blocked
python local_rag/test_validation.py   # 5/5  — hallucinated-citation rejection
```

---

## Security

Full threat model and production architecture: **[`SECURITY.md`](SECURITY.md)**

Three real vulnerabilities were found in this codebase and fixed:

| Vulnerability | Fix | Verified by |
|---|---|---|
| **Prompt injection** — malicious instructions hidden *inside the filing* hijack the model | 3 layers: input scanning, **retrieved-chunk sanitization**, instruction hierarchy | 4/4 attack simulations |
| **Open API** — anyone could trigger paid LLM calls on my accounts | API key auth, `secrets.compare_digest()` (timing-attack resistant) | 401 / 403 / 200 paths |
| **`eval()` on LLM output** — `open('.env').read()` would have dumped **every API key** | AST allowlist parser — `Call` nodes rejected by default | 12/12, incl. 5 exploits |

**The rule that governs cloud vs. local:**

> Not *"is the document public?"* but **"is EVERYTHING that leaves — document,
> question, AND context — public?"**
>
> *"Is our fund's position in Uber at risk?"* leaks strategy even though the 10-K
> is public. **In a brokerage, the question sometimes reveals more than the answer.**

For sensitive data, the generation step swaps to a **local Ollama model** — see
[`local_rag/`](local_rag/). Everything else (ingestion, chunking, embeddings, the vector
DB, retrieval) **is already local and never touches the network.**

---

## The Journey — 14 Chapters, 13 Projects

Each project builds on the last. The capstone is the ⭐ chain.

| # | Project | Chapter | What it taught |
|---|---|---|---|
| 1 | [`exercises/`](exercises/) | 1–3 | Python fundamentals, file I/O, JSON, modules |
| 2 | [`stock_screener/`](stock_screener/) | 2 | First real script — logic, functions, loops |
| 3 | [`portfolio_analyzer/`](portfolio_analyzer/) | 3 | Separation of concerns, error handling, OOP |
| 4 | [`earnings_summarizer/`](earnings_summarizer/) | 4 | LLM APIs — Claude vs. GPT-4o, tokens, cost |
| 5 | [`financial_extractor/`](financial_extractor/) | 5 | Prompt engineering, structured output, **Pydantic** |
| 6 | ⭐ [`pdf_ingestor/`](pdf_ingestor/) | 6 | PDF extraction, table parsing, **chunking with overlap** |
| 7 | ⭐ [`rag_pipeline/`](rag_pipeline/) | 7–8 | Embeddings, ChromaDB, **the full RAG loop + grounding** |
| 8 | ⭐ [`rag_api/`](rag_api/) | 9 | **FastAPI** — turning a script into a service |
| 9 | [`rag_frameworks/`](rag_frameworks/) | 10 | LlamaIndex (and what it *hides*) + a **ReAct agent from scratch** |
| 10 | [`local_rag/`](local_rag/) | 11 | **Ollama on-prem** + validators that catch its hallucinations |
| 11 | [`distribution_pipeline/`](distribution_pipeline/) | 12 | Webhook → RAG → DeepL → **WhatsApp**, async |
| 12 | ⭐ [`security/`](security/) | 13 | **Prompt injection, auth, safe eval** |
| 13 | ⭐ [`whatsapp_bot/`](whatsapp_bot/) | Bonus | **Bidirectional WhatsApp RAG** — Hebrew in, Hebrew out, with Twilio signature verification |
| 14 | [`docs/`](docs/) | 1–13 | 13 reference documents — one per chapter |

### Selected findings from the journey

**Frameworks hide the thing that matters.** LlamaIndex reproduced the RAG pipeline in 20
lines instead of 100 — and silently replaced my grounding prompt with one I never read.
The prompt is what decides whether the system fabricates a financial figure.
→ [`rag_frameworks/`](rag_frameworks/)

**Local models hallucinate citations.** Five runs of the *same* question against Llama 3.2
produced five different `sources` values — including **"Excerpt 53"** when only **3**
excerpts existed, and an answer claiming `found: true` while citing nothing. Type checking
doesn't catch this: `53` is a perfectly valid integer. Business-logic validators do.
→ [`local_rag/`](local_rag/)

**The agent critiqued my premise.** Asked to compute EPS from a flat 2.1B share count, it
retrieved net income, calculated, *and then flagged* that the filing uses a weighted
average of 2,085.253M shares — so the real figure is $4.82, not $4.79. Nobody told it to
check.
→ [`rag_frameworks/agent.py`](rag_frameworks/agent.py)

---

## What I'd Fix Before Production

An honest list. These are the first things I'd address, not an afterthought.

1. **`.env` is not a secrets manager.** Anyone with server access reads every key.
   → AWS Secrets Manager / Azure Key Vault / Vault, with rotation and audit.
2. **No audit log.** Cannot answer *"who asked what, and what did the system reply?"* —
   a **regulatory requirement** in financial services.
3. **No PII redaction** before external calls. Nothing stops a client name being pasted
   into a cloud-bound question.
4. **Single static API key.** No per-user identity, no revocation, no rate limiting.
   → OAuth2/OIDC via the firm's identity provider.
5. **In-memory vector DB.** Re-indexes on every restart; no access control on the index.
   → pgvector with row-level permissions.
6. **`/docs` is publicly served** — a complete map of the attack surface.
   → `FastAPI(docs_url=None)` in production.
7. **Regex-based injection detection** is signature-based and will miss novel phrasings.
   → Add an LLM classifier as a fourth layer.
8. **Silent background failures** in the distribution pipeline — after `200 OK`, a
   downstream failure is invisible. → Job-status store, retries, dead-letter alerting.

---

## Tech Stack

**Core:** Python 3.14 · Pydantic
**LLM:** Anthropic (Claude) · OpenAI · Ollama (Llama 3.2, local)
**RAG:** ChromaDB · sentence-transformers · pdfplumber · LlamaIndex
**API:** FastAPI · Uvicorn
**Integrations:** DeepL · Twilio (WhatsApp)

---

## Data Source

Uber Technologies, Inc. — Form 10-K, FY2025 (149 pages), from
[SEC EDGAR](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001543151&type=10-K).
The PDF is public and not committed to this repo; see
[`pdf_ingestor/DATA.md`](pdf_ingestor/DATA.md) to reproduce the ingestion stage.

---

*Built by Asaf Cohen. Every architectural decision in this repo is one I can defend —
including the ones I'd make differently now.*
