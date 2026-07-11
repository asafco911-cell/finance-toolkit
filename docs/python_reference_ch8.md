# Python Reference — Chapter 8: RAG Architecture

**Project:** `finance-toolkit/rag_pipeline/`
**Prerequisite chapters:** 4 (LLM APIs), 5 (Prompt Engineering + Pydantic), 6 (PDF → chunks), 7 (Embeddings + Vector DB)
**Status:** Complete — working end-to-end RAG system with grounded, source-cited, schema-validated answers.

---

## Intro — What This Chapter Actually Added

Chapter 7 built **half** of a RAG system: the ability to *find* relevant text. Chapter 8 built the other half: the ability to *reason over* that text and produce a trustworthy answer.

**RAG = Retrieve → Augment → Generate.**

| Stage | What it does | Built in | Engine used |
|---|---|---|---|
| **R**etrieve | Question → top-k semantically similar chunks | Ch. 7 | ChromaDB (vectors) |
| **A**ugment | Package chunks + question into one prompt | **Ch. 8** | Plain Python string building |
| **G**enerate | Send prompt to LLM → grounded answer | **Ch. 8** | Anthropic API (Claude) |

The single most important conceptual clarification of this chapter: **only the question is ever converted to a vector.** The system prompt, the excerpts, and the final prompt are all *plain text*. Embeddings live exclusively inside the Retrieve stage and are irrelevant afterward.

**Analogy:** A librarian (ChromaDB) finds 3 relevant books by *meaning*, hands them over, and leaves. Then an analyst (Claude) sits at a desk with those 3 books, a fixed set of house rules ("answer only from what's on this desk, cite your source"), and the question. The analyst has no idea what a vector is.

---

## PART 1 — Why RAG Instead of Dumping the Whole 10-K into the Prompt

A classic interview question. Four independent reasons:

| Reason | Explanation |
|---|---|
| **Context window (hard limit)** | Every model has a token ceiling (e.g. ~200K for Claude). A full 10-K + conversation history may simply *not fit*, regardless of budget. This is a technical wall, not a cost preference. |
| **Cost** | Tokens are billed on both input and output. Sending 200 pages per question is orders of magnitude more expensive than sending 3 excerpts. |
| **"Lost in the middle"** | LLMs demonstrably degrade at retrieving facts buried in the middle of very long contexts. More text ≠ better answers. |
| **Grounding precision** | Narrow, relevant context forces the model to answer from *verified* material, and makes citations meaningful. |

---

## PART 2 — The Retrieve Layer (Refactored from Ch. 7)

Chapter 7's code hardcoded the question. Chapter 8 wraps it in a reusable function — the same `def` principle from Chapter 2.

```python
def retrieve(question, n_results=3):
    results = collection.query(
        query_texts=[question],   # question is embedded HERE, and only here
        n_results=n_results
    )
    return results["documents"][0]   # [0] = results for our single query
```

**Why `[0]`?** `collection.query()` is designed to accept a *list* of questions at once and return a list of result-lists. Even with one question, the response is nested. `[0]` unwraps our single query's results.

**Why `n_results=3` instead of Ch. 7's `10`?** Directly follows from "lost in the middle" + cost. Fewer, higher-quality chunks beat more, noisier ones.

---

## PART 3 — The Augment Layer (New)

Two components: a **constant** system prompt, and a **dynamic** user prompt builder.

```python
SYSTEM_PROMPT = """You are a financial analyst assistant. Answer using ONLY the
context excerpts provided below, which come from a company's 10-K filing.

Rules:
- If the answer is not found in the excerpts, set "found" to false and briefly explain why.
- Track which excerpt numbers support each claim in the "sources" list.
- Respond with ONLY a JSON object, no markdown fences, no extra text:
{"found": true/false, "answer": "...", "sources": [1, 2]}"""


def build_user_prompt(question, retrieved_chunks):
    excerpts = "\n\n".join(
        f"[Excerpt {i + 1}]\n{chunk}"          # i + 1 → human-friendly numbering
        for i, chunk in enumerate(retrieved_chunks)   # enumerate: same as Ch. 6/7
    )
    return f"""Context excerpts from the 10-K:

{excerpts}

Question: {question}"""
```

### The critical relationship

```
question  →  retrieve()         →  3 chunks
question  +  3 chunks           →  build_user_prompt()  →  user_prompt
SYSTEM_PROMPT  +  user_prompt   →  Claude               →  answer
```

**`question` is NOT the same as `user_prompt`.** The question is a *component inside* the user prompt. The user prompt is the question **plus** the retrieved evidence — that packaging *is* the "Augmentation" in RAG.

### System vs. User prompt — why separate

| | System prompt | User prompt |
|---|---|---|
| **Changes per question?** | No — constant | Yes — rebuilt each time |
| **Contains** | Behavioral rules, output format, grounding constraints | Retrieved excerpts + the specific question |
| **Maintenance** | Edit in one place → applies to every future question | Generated programmatically |
| **API mapping** | `system=` parameter | `messages=[{"role": "user", ...}]` |

This separation isn't stylistic — it mirrors how the Anthropic API is actually structured (Ch. 4), and the API gives system-prompt instructions persistent weight across the conversation.

---

## PART 4 — The Generate Layer (New)

```python
def generate_answer(system_prompt, user_prompt):
    response = client_anthropic.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=system_prompt,                                   # ← Ch. 4
        messages=[{"role": "user", "content": user_prompt}]     # ← Ch. 4
    )
    raw_text = response.content[0].text                         # ← Ch. 4
    cleaned_text = strip_markdown_fence(raw_text)               # ← safety net 1
    data = json.loads(cleaned_text)                             # ← Ch. 5 (JSON mode)
    return RAGAnswer(**data)                                    # ← safety net 2 (Pydantic)
```

Every line here traces back to a prior chapter. Chapter 8 didn't teach new API mechanics — it **composed** existing ones.

---

## PART 5 — Structured Output: From Free Text to Validated Object

**The problem with free text.** Version 1 of the pipeline returned prose: *"Revenue growth was 18%... (Source: Excerpt 1)"*. Readable by a human, but a downstream system (FastAPI in Ch. 9, a frontend, a database) cannot reliably parse it. "Not found in the report" can be phrased a hundred different ways.

**The solution: a Pydantic schema** (`schema.py`):

```python
from pydantic import BaseModel, Field
from typing import List


class RAGAnswer(BaseModel):
    found: bool = Field(description="Whether the answer was found in the excerpts")
    answer: str = Field(description="The answer, or a brief explanation if not found")
    sources: List[int] = Field(description="Excerpt numbers supporting the answer, e.g. [1, 2]")
```

| Before (free text) | After (Pydantic) |
|---|---|
| `"Not found in the report."` | `result.found == False` — an unambiguous boolean |
| `"(Source: Excerpt 1)"` buried in prose | `result.sources == [1, 2]` — a real list of ints |
| Must be parsed with string matching | Attribute access: `result.answer` |
| Malformed output fails silently downstream | `ValidationError` raised immediately at the boundary |

**`Field(description=...)` does double duty:** it documents the schema for humans *and* guides the model on what each field should contain, because the same descriptions inform the JSON structure requested in the system prompt.

---

## PART 6 — The Markdown Fence Trap (Recurring Pattern)

**The problem.** LLMs are heavily trained to wrap code and JSON in markdown fences:

````
```json
{"found": true, "answer": "...", "sources": [1]}
```
````

Even when explicitly told "JSON only, no fences," the model sometimes complies with its training habit instead. `json.loads()` is a strict parser — it requires the string to *begin* with `{`. A leading fence produces `JSONDecodeError: Expecting value: line 1 column 1`.

**This is the same trap first encountered in Chapter 5** with `financial_extractor`.

**The defensive helper:**

```python
def strip_markdown_fence(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]        # split once → drop the ```json line
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]      # rsplit = split from the right → drop closing fence
    return text.strip()
```

**Key property: it is safe when there is no fence.** If `startswith("```")` is `False`, the block is skipped entirely and the text passes through untouched. A good safety net is invisible when unneeded.

### The two safety nets (from Ch. 5, applied here)

| Net | Catches | Raised as |
|---|---|---|
| `strip_markdown_fence` + `json.loads` | Model returned non-JSON or fenced JSON | `JSONDecodeError` |
| `RAGAnswer(**data)` | JSON is valid but has missing/wrong-typed fields | `ValidationError` |

---

## PART 7 — Grounding: The Non-Negotiable Requirement

In finance, an answer without a source is worthless — for regulation and for trust. Two tests must both pass:

**Test 1 — Accuracy with citation (answer IS in the report):**
```
Question: What was the revenue growth?
Found:    True
Answer:   Revenue growth was 18% year-over-year. Revenue increased from
          $43,978 million in 2024 to $52,017 million in 2025 (+$8.0 billion).
Sources:  [1, 2]
```
Note that the retrieved excerpts were *extremely noisy* — fragmented PDF tables reduced to number soup. The model correctly filtered signal from noise. This is what RAG buys you beyond keyword search.

**Test 2 — Honest refusal (answer is NOT in the report):**
```
Question: What is Uber's CEO's favorite programming language?
Found:    False
Answer:   Not found in the report. The excerpts discuss business operations,
          technology platform, acquisitions, cybersecurity, and governance,
          but contain no information about the CEO's favorite language.
```
**A RAG system that cannot refuse is not a RAG system — it is a hallucination machine with extra steps.** Test 2 is as important as Test 1.

---

## PART 8 — Housekeeping: `__pycache__`

The moment `rag_pipeline.py` began importing `schema.py`, Python auto-created a `__pycache__/` folder containing `schema.cpython-314.pyc`.

- **What it is:** compiled bytecode, cached so Python doesn't re-translate unchanged modules on every run.
- **When it appears:** only when one file `import`s another — not for standalone scripts.
- **What to do:** ignore it, and **never commit it**. It is auto-generated from source.

```
# .gitignore
__pycache__/
*.pyc
```

Remember: **`.gitignore` is not retroactive.** If already tracked: `git rm -r --cached __pycache__`.

---

## Full Project Structure

```
finance-toolkit/
└── rag_pipeline/
    ├── chunks.json          # 221 chunks from the Uber 10-K (output of Ch. 6)
    ├── schema.py            # RAGAnswer — Pydantic model for the structured answer
    ├── rag_pipeline.py      # The complete RAG system
    └── __pycache__/         # auto-generated, gitignored
```

### `rag_pipeline.py` — architecture at a glance

```python
# ---------- Setup ----------
#   load .env → Anthropic client
#   load chunks.json → ChromaDB collection (embedding happens here, once)

# ---------- Retrieve ----------
def retrieve(question, n_results=3): ...        # question → vector → top-k chunks

# ---------- Augment ----------
SYSTEM_PROMPT = """..."""                        # constant rules + JSON format spec
def build_user_prompt(question, chunks): ...     # chunks + question → one prompt

# ---------- Generate ----------
def strip_markdown_fence(text): ...              # safety net 1
def generate_answer(system, user): ...           # API call → parse → validate → RAGAnswer

# ---------- Run ----------
question = "What was the revenue growth?"
retrieved_chunks = retrieve(question, n_results=3)
user_prompt = build_user_prompt(question, retrieved_chunks)
result = generate_answer(SYSTEM_PROMPT, user_prompt)
print(result.found, result.answer, result.sources)
```

---

## Known Limitations (Carried Forward to Ch. 14)

Worth being able to articulate these in an interview — knowing what your system *can't* do is a senior signal:

1. **In-memory vector DB.** `chromadb.Client()` is ephemeral. Every run re-embeds all 221 chunks from scratch. Ch. 14 needs a *persistent* client.
2. **No metadata on chunks.** Chunks are bare strings — no page numbers, no section labels. Citations therefore point to "Excerpt 2," not "page 73, Item 7." This must be fixed for a production-grade citation.
3. **Chunking splits tables.** Inherited from Ch. 6. Financial tables get fragmented across chunk boundaries, producing the "number soup" visible in the excerpts.
4. **Retrieval quality is the ceiling.** If `retrieve()` returns the wrong chunks, a perfect LLM still produces a wrong answer. Garbage in, garbage out — the highest-leverage place to invest effort.
5. **No conversation memory.** Each question is stateless.
6. **No prompt-injection defense.** Malicious text inside a filing could attempt to override the system prompt (Ch. 13).

---

## 60-Second Self-Test

1. What do the three letters in RAG stand for, and which chapter built each?
2. In the whole pipeline, *what exactly* gets converted into a vector?
3. Does the system prompt influence which chunks are retrieved? Why or why not?
4. Why does `retrieve()` end with `results["documents"][0]` — what is the `[0]` unwrapping?
5. Is `question` the same object as `user_prompt`? Explain the relationship.
6. Give two reasons not to just paste the entire 10-K into the prompt.
7. What is "lost in the middle"?
8. Name two advantages of keeping the system prompt separate from the user prompt.
9. What does `enumerate()` give you, and why is `i + 1` used in `build_user_prompt`?
10. Why does `json.loads()` fail on a fenced JSON response?
11. What does `text.rsplit("```", 1)[0]` do, and why `rsplit` rather than `split`?
12. Is `strip_markdown_fence` safe to call on clean, unfenced JSON? Why?
13. Name the two independent "safety nets" between the raw API response and a usable object, and the exception each raises.
14. Why is `found: bool` better than checking whether the answer string contains "Not found"?
15. Why is the "honest refusal" test as important as the accuracy test?
16. What creates `__pycache__`, and why should it never be committed?
17. Name the single biggest bottleneck on overall RAG answer quality.
18. Which Anthropic API parameter carries the system prompt, and which carries the user prompt?

---

### Answers

1. **R**etrieve (Ch. 7), **A**ugment (Ch. 8), **G**enerate (Ch. 8).
2. Only the `question`, inside `collection.query()`. (The chunks were embedded earlier, once, at index time.) Nothing else is ever vectorized.
3. No. The system prompt is never passed to ChromaDB — it only goes to Claude in the Generate stage.
4. `collection.query()` accepts a *list* of queries and returns a list of result-lists. `[0]` unwraps the results for our single query.
5. No. `question` is a *component inside* `user_prompt`. `user_prompt` = retrieved excerpts + question, packaged together. That packaging *is* the Augment step.
6. Any two of: hard context-window limit; token cost; "lost in the middle" degradation; weaker grounding/citations.
7. LLMs retrieve facts less reliably when they are buried in the middle of a very long context. More context ≠ better answers.
8. (a) Maintenance — change the rules in one place, applies to all future questions. (b) It mirrors the actual API structure (`system=` vs `messages=`), and the API weights system instructions persistently.
9. `enumerate()` yields index *and* value together. `i + 1` because Python indexes from 0, but "Excerpt 1" is more natural for both humans and the model than "Excerpt 0."
10. `json.loads()` is strict — it requires the string to begin with `{`. A leading ` ```json ` breaks it with `JSONDecodeError`.
11. It splits once *from the right* and takes the part before the closing fence. `rsplit` because the closing fence is at the end; a left-side `split` could break on a fence appearing earlier inside the content.
12. Yes. If `startswith("```")` is `False`, the block is skipped and the text passes through unchanged. A good safety net is invisible when unneeded.
13. (a) `strip_markdown_fence` + `json.loads` → `JSONDecodeError`. (b) `RAGAnswer(**data)` → `ValidationError`.
14. Because a boolean is unambiguous and machine-checkable (`if result.found:`), while "not found" can be phrased a hundred different ways in prose.
15. Because a RAG system that cannot say "I don't know" will hallucinate instead — which in finance is worse than no answer at all.
16. Python auto-generates it (compiled bytecode) whenever one module `import`s another. It's derived from source, so it belongs nowhere in version history.
17. **Retrieval quality.** If the wrong chunks come back, even a perfect LLM produces a wrong answer.
18. `system=` carries the system prompt; `messages=[{"role": "user", "content": ...}]` carries the user prompt.

---

## Where This Leads

| Next | What it adds |
|---|---|
| **Ch. 9 — FastAPI** | Wraps `generate_answer()` in `POST /ask`. The `RAGAnswer` model you just built becomes the API's `response_model` — this is exactly why structured output mattered. |
| **Ch. 13 — Security** | Prompt-injection defense on the retrieved chunks; architecture documentation. |
| **Ch. 14 — Capstone** | Persistent vector DB, chunk metadata for real page-level citations, full README. |

**You now have a working, grounded, schema-validated RAG system.** Everything after this is productionization.
