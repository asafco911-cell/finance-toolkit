# Local RAG — On-Premise Financial Q&A

The Chapter 8 RAG pipeline, with the cloud LLM swapped for a **local open-source
model** (Llama 3.2 via Ollama) — plus a validation layer that catches the
hallucinations local models actually produce.

**No data leaves the machine.**

---

## Why This Exists

Every query in the cloud version sends 10-K excerpts over the internet to
Anthropic's servers. For a public filing, that's fine. Now substitute:

- client portfolios
- undisclosed fund positions
- an internal memo on a deal under review

Now it's a problem — not because the API is insecure, but because **regulation
may simply forbid** that data leaving the organization.

**The analogy:** instead of sending confidential documents to an outside
translation agency, you hire an in-house translator. Maybe less brilliant — but
the documents never leave the building.

---

## Architecture

Only **one layer changed**. Retrieve and Augment are imported unmodified from
`../rag_pipeline/`:

```
question
   ↓
retrieve()            ← UNCHANGED (ChromaDB, local embeddings)
   ↓
build_user_prompt()   ← UNCHANGED (same SYSTEM_PROMPT)
   ↓
generate_answer_local()  ← CHANGED: Claude API → Ollama (localhost:11434)
   ↓
ValidatedRAGAnswer    ← NEW: business-logic validation, not just type checking
```

This is the payoff of Chapter 8's modularity: swap one component, the rest
doesn't move.

---

## Setup

1. Install [Ollama](https://ollama.com), then pull a model:
   ```
   ollama pull llama3.2
   ```
2. Verify it runs locally:
   ```
   ollama run llama3.2
   ```
   (Disconnect your Wi-Fi and ask it something — it still works.)

3. Ensure `../rag_pipeline/chunks.json` exists.

## Running

```
python local_rag.py        # ask the indexed 10-K a question
python test_validation.py  # verify the safety net actually catches bad output
```

No API key. No account. No billing.

---

## How "Local" Really Works

`local_rag.py` imports the **OpenAI SDK** — which looks alarming until you see
the one line that matters:

```python
client_local = OpenAI(
    base_url="http://localhost:11434/v1",   # ← the local Ollama server
    api_key="ollama"                        # ← required by the SDK, ignored by Ollama
)
```

Ollama exposes an **OpenAI-compatible API** on `localhost:11434` (a local server,
exactly like uvicorn on `:8000`). The SDK is just the grammar; the address is
your own machine. Nothing is sent to OpenAI.

### "Nothing left the machine" — the precise claim

| | Model download | Model inference |
|---|---|---|
| **When** | Once | Every query |
| **What crosses the network** | Public weight files | **Nothing** |
| **Direction** | Inbound only | — |

The embedding model and the LLM were both downloaded once from public
repositories — the same as `pip install`. **No query, no chunk, and no client
data ever leaves the machine.** In a truly air-gapped environment, models are
downloaded once in a controlled setting and moved inside; from then on, zero
egress.

---

## The Honest Comparison

Same question (`"What was the revenue growth?"`), same retrieved excerpts, same
system prompt.

| | Claude (cloud) | Llama 3.2 3B (local) |
|---|---|---|
| **Answer** | "Revenue growth was 18% YoY. Revenue increased from $43,978M in 2024 to $52,017M in 2025, representing an $8.0B increase." | `"18%"` / `"$8.0 billion, or 18% year-over-year"` |
| **Sources** | `[1, 2]` — consistent | `[1,2]`, `[1]`, `[2]`, **`[53]`**, **`[]`** — *varies per run* |
| **Consistency** | Stable across runs | **Highly non-deterministic** |
| **Speed** | Fast | Noticeably slower |
| **Cost** | Per token | Hardware only; inference free |
| **Privacy** | Data leaves the org | **Nothing leaves the machine** |
| **Dependency** | Internet + vendor | Fully independent |

### What actually went wrong (real logs)

Five runs of the **identical** question produced five different `sources` values:

```
Run 1: [1, 2]     ✅
Run 2: [1, 2]     ✅
Run 3: [53]       ❌ Excerpt 53 — of 3 provided
Run 4: []         ❌ claims found=True, cites nothing
Run 5: [1]        ✅
```

And the nastiest case of all:

```
[53, 2]           ❌ one real source, one fabricated — mixed together
```

**The model did not fail loudly.** It returned well-formed JSON with a perfect
schema and a **citation to an excerpt that does not exist**. A system displaying
that output would be lying to the user with total confidence.

This is the same failure mode identified in Chapter 10: **not an obviously wrong
answer — a wrong answer that looks right.**

---

## The Validation Layer

Type checking is **not enough**. `sources: [53]` passes a `List[int]` check —
`53` is a perfectly valid integer. The problem isn't the type; it's the **value**.

`validated_answer.py` adds two business-logic validators:

```python
@field_validator("sources")
def sources_must_exist(cls, v, info):
    n_excerpts = (info.context or {}).get("n_excerpts")
    invalid = [s for s in v if s < 1 or s > n_excerpts]
    if invalid:
        raise ValueError(f"Hallucinated source(s): {invalid}. "
                         f"Only excerpts 1-{n_excerpts} were provided.")
    return v


@model_validator(mode="after")
def found_requires_sources(self):
    if self.found and not self.sources:
        raise ValueError("Answer claims found=True but cites no sources.")
    return self
```

- **`@field_validator`** — validates one field. Needs external context
  (`n_excerpts`), injected via `model_validate(data, context={...})`.
- **`@model_validator(mode="after")`** — validates a rule spanning **two fields**
  (`found` **and** `sources`), which a field validator cannot express.

### Testing the safety net

**A safety net you haven't tested is not a safety net — it's hope.**

`test_validation.py` covers five cases, all passing:

| Case | Expected |
|---|---|
| Valid answer with real sources `[1, 2]` | accept |
| Hallucinated source `[5]` of 3 | **reject** |
| Hallucinated mixed with real `[53, 2]` | **reject** |
| `found=True` with `sources: []` | **reject** |
| Honest refusal: `found=False`, `sources: []` | accept |

---

## When To Use Which — The Architectural Call

> **Sensitive data** (client portfolios, undisclosed positions, internal memos)
> → **local model**, wrapped in strict output validation.
>
> **Public data** (10-K filings, news, market commentary)
> → **cloud API**, where quality is critical and privacy is not.

The decision is not "local is better" or "cloud is better." It's: *what is this
specific data, and what is the cost of it leaving?*

---

## Known Limitations

1. **Small model (3B).** Llama 3.2 3B was chosen to run without a strong GPU.
   A larger model (`llama3.1:8b`, `mistral`) would likely reduce hallucination —
   at the cost of speed and hardware.
2. **Non-determinism is not solved, only caught.** Validation *rejects* bad
   output; it does not make the model consistent. Production would need retries
   with a bounded attempt count, and escalation to a human on repeated failure.
3. **No retry logic.** A rejected response currently just fails.
4. **Answer quality is thinner** than the cloud model's — correct but sparse,
   often lacking the supporting figures an analyst needs.
5. **Models were downloaded from the internet.** True air-gapping requires a
   one-time controlled transfer.

---

## Tech Stack

Python · Ollama · Llama 3.2 (3B) · OpenAI SDK (as an OpenAI-compatible client) ·
ChromaDB · Pydantic (field + model validators)
