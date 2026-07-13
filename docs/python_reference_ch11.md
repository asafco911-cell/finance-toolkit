# Python Reference — Chapter 11: Local Models — Ollama & Hugging Face

**Project:** `finance-toolkit/local_rag/`
**Prerequisite chapters:** 4 (LLM APIs, OpenAI SDK), 5 (Pydantic), 7 (embeddings), 8 (the RAG pipeline), 9 (servers & localhost), 10 (hallucination risk)
**Status:** Complete — RAG running entirely on-premise via Ollama, wrapped in a business-logic validation layer that provably catches the model's hallucinations.

---

## Intro — The Question That Forces This Chapter

Every query in the cloud version does something easy to forget: it takes chunks of the 10-K, packages them into a prompt, and **sends them over the internet to servers in another country.**

For a public Uber filing, that's fine. Now substitute:

- client portfolios
- undisclosed fund positions
- an internal memo on a deal under review

**Now it's a problem** — not because the API is insecure, but because **regulation may simply forbid** that data leaving the organization. Full stop. No amount of encryption changes that.

**Analogy (from the syllabus):** instead of sending confidential documents to an outside translation agency, you hire an **in-house translator**. Maybe less brilliant — but the documents never leave the building.

**Why it matters for the job:** the role description says *"local model deployment (Ollama / Hugging Face) when needed"* and *"strict data-security requirements."* Being able to say *"sensitive analysis runs on a local model, general analysis runs on a cloud API"* is not a technical trick — it's **architectural maturity**.

---

## PART 1 — Core Concepts

| Term | What it is | Analogy |
|---|---|---|
| **Open-source model** | A model whose **weights** (the giant file of numbers produced by training) are downloadable. Llama, Mistral, Gemma, Qwen. | You own the brain |
| **Closed model (Claude, GPT)** | Weights are a trade secret. The only access is sending requests to the vendor's servers. | The brain is theirs; you mail it letters |
| **Ollama** | Turns "run a local model" from an engineering project into one command | *"Spotify for models"* — `pull` then `run` |
| **Hugging Face** | The *"GitHub of models"*: thousands of open models, datasets, and libraries. Ollama's models generally originate here. | A vast library of ready-made artificial minds |

**A language model is a file.** `llama3.2` downloaded as **2.0 GB**. Everything it "knows" is compressed into that one artifact. Easy to miss, important to internalize.

---

## PART 2 — The Key Insight: Ollama Is a Local Server

This is the piece that connects the chapter to everything you've already built.

**Ollama runs a local server** — exactly like uvicorn in Ch. 9 — listening on `http://localhost:11434`, exposing an API that is **OpenAI-compatible**.

Which means: your code talks to it using **the same SDK and the same syntax** you learned in Ch. 4 — but the request never leaves the machine.

```python
from openai import OpenAI          # ← the OpenAI SDK...

client_local = OpenAI(
    base_url="http://localhost:11434/v1",   # ← ...pointed at YOUR machine
    api_key="ollama"                        # ← required by the SDK, ignored by Ollama
)

response = client_local.chat.completions.create(
    model="llama3.2",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
)
return response.choices[0].message.content   # identical to Ch. 4
```

| Line | What it really means |
|---|---|
| `from openai import OpenAI` | The SDK is just **grammar**. Nothing goes to OpenAI. Ollama's API is OpenAI-compatible — a de-facto industry standard. |
| `base_url="http://localhost:11434/v1"` | **The single line that makes everything local.** `localhost` = this machine (Ch. 9). `11434` = Ollama's port, like uvicorn's `8000`. |
| `api_key="ollama"` | The SDK technically requires one; Ollama ignores it entirely. **No key, no account, no billing.** |

Nothing here is new — it's Ch. 4 (API calls) plus Ch. 9 (local servers), recombined.

---

## PART 3 — What Changed, and What Didn't

Only **one layer** was swapped:

```
question
   ↓
retrieve()               ← UNCHANGED, imported from rag_pipeline
   ↓
build_user_prompt()      ← UNCHANGED, same SYSTEM_PROMPT
   ↓
generate_answer_local()  ← CHANGED: Claude API → Ollama
   ↓
ValidatedRAGAnswer       ← NEW
```

```python
from rag_pipeline import retrieve, build_user_prompt, SYSTEM_PROMPT, strip_markdown_fence
```

Retrieve and Augment were **imported verbatim**. Not one line rewritten.

**This is the payoff of Ch. 8's modularity:** swap one component, the rest doesn't move. Separation of concerns stops being an abstract principle and becomes a concrete saving.

*(Note: the embeddings were already running locally since Ch. 7 — only the generation step had been going to the cloud.)*

---

## PART 4 — "Nothing Leaves the Machine" — The Precise Claim

A careless version of this claim is wrong, and an interviewer will catch it. The models **were downloaded** from the internet (you saw `model.safetensors: 100% | 90.9MB` scroll past). So what exactly is the guarantee?

| | Model download | Model inference |
|---|---|---|
| **When** | Once | Every single query |
| **What crosses the network** | Public weight files | **Nothing** |
| **Direction** | Inbound only | — |

**No query, no chunk, and no client data ever leaves the machine.** What crossed the wire was a request for a public file — exactly like `pip install`. Nobody worries about client data leaking when you install a library.

**In a truly air-gapped environment:** models are downloaded **once** in a controlled setting, transferred inside, and from then on there is **zero egress**. That is the complete answer.

---

## PART 5 — The Honest Comparison (Real Data)

Same question. Same retrieved excerpts. Same system prompt.

| | Claude (cloud) | Llama 3.2 3B (local) |
|---|---|---|
| **Answer** | "Revenue growth was 18% YoY. Revenue increased from $43,978M in 2024 to $52,017M in 2025, representing an $8.0B increase." | `"18%"` — correct but **empty** |
| **Sources** | `[1, 2]` — stable | `[1,2]`, `[1]`, `[2]`, **`[53]`**, **`[]`** — *varies every run* |
| **Consistency** | Stable | **Highly non-deterministic** |
| **Speed** | Fast | Noticeably slower |
| **Cost** | Per token | Hardware only; inference free |
| **Privacy** | Data leaves the org | **Nothing leaves the machine** |
| **Dependency** | Internet + vendor | Fully independent |

**Claude gave the story. Llama gave a number.** An analyst can't act on `"18%"` alone.

### What actually went wrong — five runs, identical question

```
Run 1: [1, 2]     ✅
Run 2: [1, 2]     ✅
Run 3: [53]       ❌ Excerpt 53 — of 3 provided
Run 4: []         ❌ claims found=True, cites nothing
Run 5: [1]        ✅
```

And the nastiest case observed:

```
[53, 2]           ❌ one real source, one fabricated — mixed together
```

**The model did not fail loudly.** It returned well-formed JSON, a perfect schema, and a **citation to an excerpt that does not exist**. A system displaying that output would be lying to the user with total confidence.

This is the exact failure mode from Ch. 10: **not an obviously wrong answer — a wrong answer that looks right.** Here it struck the *citation* field — the very thing meant to be the anchor of truth.

Interestingly, three consecutive runs all hallucinated **the same number (53)**. The hallucination wasn't random noise; the model had a *bias* toward a specific fabrication.

---

## PART 6 — The Validation Layer (The Real Lesson)

### Why the existing `RAGAnswer` was not enough

The Ch. 5/8 model checks **types**: `sources` must be a `List[int]`. And `[53]` **passes** — 53 is a perfectly valid integer.

**The problem is not the type. It's the value.**

This introduces a new distinction:

| | Technical validation | Business validation |
|---|---|---|
| **Asks** | "Is this an int?" | "Is this int *meaningful in context*?" |
| **Tool** | Type hints (`List[int]`) | `@field_validator` / `@model_validator` |
| **Catches** | `sources: "five"` | `sources: [53]` when only 3 excerpts exist |

### Validator 1 — field-level, with injected context

```python
@field_validator("sources")
@classmethod
def sources_must_exist(cls, v: List[int], info: ValidationInfo) -> List[int]:
    n_excerpts = (info.context or {}).get("n_excerpts")

    if n_excerpts is None:
        return v   # no context supplied — skip the check rather than crash

    invalid = [s for s in v if s < 1 or s > n_excerpts]

    if invalid:
        raise ValueError(
            f"Hallucinated source(s): {invalid}. "
            f"Only excerpts 1-{n_excerpts} were provided to the model."
        )

    return v
```

**The challenge this solves:** `RAGAnswer` has no idea how many excerpts were sent — that lives in `local_rag.py`. So the value must be **injected from outside**:

```python
return ValidatedRAGAnswer.model_validate(
    data,
    context={"n_excerpts": n_excerpts}   # ← the injection channel
)
```

`info.context` is how a validator reads external state. `model_validate(data, context={...})` is how you supply it. Note `n_excerpts=len(retrieved_chunks)` — **counted, not hardcoded**, so it adapts if the index returns fewer chunks than requested.

### Validator 2 — model-level, spanning two fields

```python
@model_validator(mode="after")
def found_requires_sources(self):
    if self.found and not self.sources:
        raise ValueError(
            "Answer claims found=True but cites no sources. "
            "A grounded answer must reference at least one excerpt."
        )
    return self
```

**Why not another `@field_validator`?** Because this rule depends on **two fields together** (`found` **and** `sources`). A field validator only sees one field. `@model_validator(mode="after")` runs once all individual fields have validated, and sees the whole object.

**This caught the `sources: []` case** — where the model claimed `found=True` while citing nothing. Run 4 would otherwise have passed silently: an ungrounded claim, presented as grounded.

### The two safety nets, now three

| Net | Catches | Raises |
|---|---|---|
| `strip_markdown_fence` + `json.loads` | Not valid JSON at all | `JSONDecodeError` |
| Type annotations (`List[int]`) | Wrong types | `ValidationError` |
| **`@field_validator` / `@model_validator`** | **Valid types, false content** | **`ValidationError`** |

---

## PART 7 — Testing the Safety Net

> **A safety net you haven't tested is not a safety net — it's hope.**

`test_validation.py` doesn't wait for a bug to appear by luck. It **constructs** the failure cases and asserts they're rejected.

```python
def check(name, data, should_pass):
    try:
        ValidatedRAGAnswer.model_validate(data, context={"n_excerpts": 3})
        passed = True
    except ValidationError as e:
        passed = False
        error = e
    ...
```

| Case | Expected | Result |
|---|---|---|
| Valid answer, real sources `[1, 2]` | accept | ✅ PASS |
| Hallucinated source `[5]` of 3 | **reject** | ✅ PASS |
| Hallucinated mixed with real `[53, 2]` | **reject** | ✅ PASS |
| `found=True` with `sources: []` | **reject** | ✅ PASS |
| Honest refusal: `found=False`, `sources: []` | **accept** | ✅ PASS |

**The last case is the subtle one.** When `found=False`, having no sources is *correct* — an honest refusal shouldn't be punished. A validator that rejected it would break the most important behavior in the whole system.

**Placement matters:** the tests live in their own file, not inside `local_rag.py`. They're the **asset**, not the debris — but they don't belong polluting every normal run.

---

## PART 8 — The Architectural Call

> **Sensitive data** (client portfolios, undisclosed positions, internal memos)
> → **local model**, wrapped in strict output validation.
>
> **Public data** (10-K filings, news, market commentary)
> → **cloud API**, where quality is critical and privacy is not.

The decision is never "local is better" or "cloud is better." It's: **what is this specific data, and what is the cost of it leaving?**

---

## Full Project Structure

```
finance-toolkit/
└── local_rag/
    ├── local_rag.py           # RAG with Ollama generation + validated output
    ├── validated_answer.py    # ValidatedRAGAnswer: field + model validators
    ├── test_validation.py     # 5 sanity checks — proves the net catches real failures
    └── README.md              # honest cloud-vs-local comparison with real logs
```

---

## Known Limitations

1. **Small model (3B).** Chosen to run without a strong GPU. A larger model (`llama3.1:8b`, `mistral`) would likely reduce hallucination — at the cost of speed and hardware.
2. **Non-determinism is caught, not solved.** Validation *rejects* bad output; it does not make the model consistent. Production needs bounded retries and escalation to a human on repeated failure.
3. **No retry logic.** A rejected response currently just fails.
4. **Answer quality is thinner** — correct but sparse, often missing the supporting figures an analyst actually needs.
5. **Models were downloaded from the internet.** True air-gapping requires a one-time controlled transfer.
6. **Hugging Face `transformers` not used directly.** Ollama abstracts it away; loading a model manually via `transformers` is the deeper (and more painful) path.

---

## 60-Second Self-Test

1. Why can't you just download Claude and run it locally?
2. What is Ollama, mechanically — and what does it have in common with uvicorn?
3. Why does `local_rag.py` import the **OpenAI** SDK? Does anything go to OpenAI?
4. Which single line makes the entire pipeline local?
5. Why does `api_key="ollama"` work, and what does that tell you about billing?
6. Which parts of the Ch. 8 pipeline were rewritten for this chapter?
7. State precisely what does — and does not — cross the network in a local setup.
8. What is a language model, physically?
9. Give the cloud-vs-local trade-off across five dimensions.
10. Five identical runs produced five different `sources` values. What is this called, and why is it dangerous in finance?
11. Why did `sources: [53]` pass the original `RAGAnswer` type check?
12. What is the difference between technical validation and business validation?
13. Why does `sources_must_exist` need `info.context`, and how is the context supplied?
14. Why is `n_excerpts=len(retrieved_chunks)` better than hardcoding `3`?
15. Why must `found_requires_sources` be a `@model_validator` and not a `@field_validator`?
16. Why must the test case `found=False, sources=[]` be *accepted*?
17. What's wrong with a safety net you never tested?
18. Give the one-sentence architectural rule for choosing local vs. cloud.
19. Name the three safety nets now standing between the raw model output and a usable object.

---

### Answers

1. Claude's **weights** are a trade secret — there is no file to download. Open models (Llama, Mistral) publish theirs; closed models don't.
2. Ollama runs a **local server** on `localhost:11434` exposing an OpenAI-compatible API — structurally identical to uvicorn serving your FastAPI app on `:8000`.
3. Because Ollama's API is **OpenAI-compatible** (a de-facto standard). The SDK is only the grammar. **Nothing** goes to OpenAI — the `base_url` points at your own machine.
4. `base_url="http://localhost:11434/v1"`.
5. The SDK requires a key field; **Ollama ignores it**. No key, no account, **no billing**.
6. **Only the generation layer.** `retrieve()` and `build_user_prompt()` were imported verbatim from `rag_pipeline`. (Embeddings were already local since Ch. 7.)
7. **Downloaded once:** public model weight files (inbound only). **During inference:** nothing. No query, no chunk, no client data ever leaves.
8. A **file**. `llama3.2` is 2.0 GB — everything it knows, compressed into one artifact.
9. Quality (cloud wins), privacy (local wins), cost (local wins at scale), speed (cloud wins), dependency (local wins — no internet, no vendor).
10. **Non-determinism.** Dangerous because the model doesn't fail *always* — it fails *sometimes*, unpredictably, and **with full confidence**. You cannot reproduce a result for a regulator.
11. Because `53` **is** a valid integer. The type was right; the **value** was fabricated. Type checking cannot catch this.
12. **Technical:** "is this an int?" **Business:** "is this int *meaningful in this context*?" — e.g. must be between 1 and the number of excerpts actually sent.
13. Because the model has no idea how many excerpts were sent — that lives in the caller. It's injected via `model_validate(data, context={"n_excerpts": n})` and read via `info.context`.
14. Because it **adapts automatically** if the index returns fewer chunks than requested. Hardcoding `3` would silently accept a bogus source if only 2 chunks came back.
15. Because the rule spans **two fields** (`found` **and** `sources`). A field validator sees only one field; `@model_validator(mode="after")` sees the whole object.
16. Because an **honest refusal** legitimately has no sources. A validator that rejected it would break the single most important behavior in the system — the ability to say "I don't know."
17. It's **not a safety net — it's hope.** You have no evidence it fires when it matters.
18. **Sensitive data → local model with strict validation. Public data → cloud API.** The question is never "which is better," but "what is the cost of *this* data leaving?"
19. (1) `strip_markdown_fence` + `json.loads` → `JSONDecodeError`. (2) Type annotations → `ValidationError`. (3) `@field_validator` / `@model_validator` → `ValidationError` on *valid types with false content*.

---

## Where This Leads

| Next | What it adds |
|---|---|
| **Ch. 12 — Automation & Integration** | Scheduling, WhatsApp, translation — connecting these tools to real workflows. |
| **Ch. 13 — Security** | Prompt-injection defense; the local-model architecture from this chapter is a **core part** of the security answer. |
| **Ch. 14 — Capstone** | The retry-and-escalate loop that turns "validation rejects bad output" into "the system recovers from bad output." |

**Interview framing:** *"I ran the same question five times against a local Llama 3.2. I got five different answers — including a citation to 'Excerpt 53' when only three excerpts existed, and an answer claiming found=true while citing nothing. So I built a Pydantic validation layer that checks not just types but business logic, and a test file proving it catches every one of those cases. My conclusion: local models buy you privacy, but they **require** an output validation layer. The architecture I'd propose is hybrid — sensitive data local with strict validation, public data on a cloud API."*

That answer is not a claim. **It's backed by logs.**
