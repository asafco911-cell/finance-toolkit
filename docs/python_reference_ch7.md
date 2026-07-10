# Embeddings, Vector Databases & RAG — Study Reference (Chapter 7)

> Semantic search over documents: embeddings, vector databases, and the RAG pattern —
> where everything from Chapters 1–6 connects into a question-answering system.
> Same rule: if you can predict the output *before* running it, you understand it.
> Companion to the Chapter 1–6 reference sheets.

---

## PART A — The problem RAG solves

You have 221 chunks of a 10-K. You ask: "What was the R&D spending?" A literal search
(Ctrl+F) only finds the EXACT words "R&D spending." If the report says "research and
development costs" or "innovation investments," literal search MISSES it entirely — same
meaning, different words. Embeddings solve exactly this: finding text by MEANING, not by
exact wording.

---

## PART B — Embeddings: turning meaning into numbers

### The core idea
An embedding converts a piece of text into a long list of numbers (a vector, e.g. 1,536
numbers) such that texts with SIMILAR MEANING get vectors that are CLOSE together in space.

**Map analogy:** cities near each other get similar coordinates. Embeddings do this for
meaning — "R&D spending" and "research and development costs" land close together even with
zero shared words; "the weather is nice" lands far away.

### How the machine "learns" meaning (no LLM hand-coding)
Meaning is learned from CONTEXT, not from definitions. "Tell me the company you keep and I'll
tell you who you are" — words that appear in the same contexts tend to be similar. Trained on
trillions of words, a neural net repeatedly predicts "what word comes next?" and, as a
by-product, a numeric representation crystallizes for each word/phrase that reflects all the
contexts it appeared in. Words in similar contexts converge to similar numbers — not because
anyone programmed it, but because that's the natural way the network organizes information to
predict well. The model doesn't "understand" like a human; it's massive statistical
compression of language patterns — but because language itself is built on context, the
practical result closely resembles understanding.

### Cross-lingual embeddings
Modern embedding models are trained on MANY languages together (including parallel texts), so
Hebrew and English share ONE meaning-space from the start — the model doesn't "translate then
compare," it learned directly that equivalent phrases belong close together. Caveat: not all
models are equally multilingual; English-only-trained models handle Hebrew poorly. Check for
explicit multilingual support (e.g. OpenAI's `text-embedding-3-large`).

### Vector = just a list of numbers
Don't fear the word. A vector is a Python list of numbers (Ch. 2). Real embeddings are just
LONG (e.g. 1,536 numbers) to capture many nuances of meaning.

### Similarity (Cosine Similarity)
Measures how close two vectors are. Think of two arrows from the same point: same direction →
similar (≈1.0); opposite → dissimilar (≈0). You don't compute it by hand — libraries do. Just
know: a number (roughly 0–1) saying how alike two texts are in meaning.

### Cost note
Calling an embeddings API IS an API call and DOES cost tokens — but only INPUT tokens (the
text you send), no text output (you get back numbers). Usually much cheaper than a chat call.
(ChromaDB's default model runs LOCALLY, so it costs nothing — see Part D.)

---

## PART C — Vector Databases

### Why a special database (not just a list)?
Comparing a query against 221 vectors in a plain loop is fine. But at 10,000+ vectors (all
your tracked tickers' filings), checking every one on every query is slow and doesn't scale.
A vector DB stores vectors in an INDEXED structure so "give me the 5 most similar" is fast —
like a library catalog vs an unsorted pile of books.

### The three steps of every RAG system
```
1. INDEX (once, upfront):   each chunk → embedding → stored in the vector DB
2. QUERY (per question):    user's question → embedding (the question is embedded too!)
3. SEARCH:                   vector DB finds the N nearest chunk-vectors → returns those chunks
```
**Critical:** the QUESTION is also turned into an embedding. That's the magic — you compare
vector-to-vector, so "R&D spending" (question) finds "research and development costs" (report).

---

## PART D — ChromaDB in practice

```python
import chromadb

client = chromadb.Client()                              # like Anthropic(...) — a client object
collection = client.create_collection(name="uber_10k")   # a "table" for your embeddings

chunk_ids = [f"chunk_{i}" for i in range(len(chunks))]    # list comprehension (new, Part E)

collection.add(documents=chunks, ids=chunk_ids)          # Chroma embeds each chunk AUTOMATICALLY

results = collection.query(query_texts=["revenue growth"], n_results=3)
for i, chunk in enumerate(results["documents"][0]):       # [0] = results for the first query
    print(f"--- Result {i+1} ---")
    print(chunk[:400])
```

- `collection.add(documents=...)` — you pass raw TEXT; Chroma calls an embedding model itself,
  converts, and stores vector + text + id. You never compute embeddings by hand.
- **Default model runs LOCALLY:** on first `add`, Chroma downloads `all-MiniLM-L6-v2` to
  `~/.cache/chroma/` and runs it ON YOUR MACHINE — so indexing costs NO API tokens.
- `ids` — each chunk needs a unique id (like a dict key) so you know which chunk came back.
- `results["documents"]` is a list-of-lists (one inner list per query); `[0]` = first query's results.

---

## PART E — List comprehension (new syntax)

A compact one-line way to build a list.

```python
# the long way you already know (Ch. 2–3):
chunk_ids = []
for i in range(len(chunks)):
    chunk_ids.append(f"chunk_{i}")

# the same thing as a list comprehension:
chunk_ids = [f"chunk_{i}" for i in range(len(chunks))]
```
Pattern: `[EXPRESSION for VARIABLE in ITERABLE]`. Not required — the loop works identically —
but very common in real Python, worth recognizing.

---

## PART F — What RAG is (the big picture)

**RAG = Retrieval-Augmented Generation.** Instead of asking an LLM to answer from its own
memory (which may be outdated or may hallucinate), you:
1. **Retrieve** the most relevant chunks from YOUR documents (vector search),
2. **Augment** the prompt by inserting those chunks as context,
3. **Generate** an answer with the LLM, grounded in that retrieved context.

The LLM answers using YOUR data, with the source chunks right there — so answers are current,
specific to your documents, and traceable to a source.

---

## PART G — Advantages & disadvantages of RAG

### Advantages
- **Grounded in your data** — answers come from your actual filings, not the model's training.
- **Up to date** — add a new 10-K to the DB and it's immediately answerable; no retraining.
- **Reduces hallucination** — the model is handed the real text, not asked to recall it.
- **Traceable** — you can show WHICH chunk the answer came from (auditability — key in finance).
- **Cheaper than fine-tuning** — no model training; just embed and store.
- **Scales across documents** — one system can search thousands of filings.

### Disadvantages / limits (which you SAW first-hand)
- **Retrieval quality caps everything** — if the right chunk isn't retrieved, the LLM can't use
  it. Your best chunk ("Total Revenue $37,281 $43,978") ranked #5, not top-3.
- **Default embedding models are mediocre** — `all-MiniLM-L6-v2` is small/fast but imprecise;
  it ranked cost-percentage chunks above the actual revenue chunk.
- **Naive chunking splits meaning** — word-count chunks cut tables mid-structure ("Total
  Revenue $ 3…" was truncated), weakening each piece's semantic signal.
- **Garbage in, garbage out** — bad extraction (Ch. 6) → bad chunks → bad retrieval.
- **No reasoning in retrieval** — similarity ≠ relevance; "lots of dollar signs and %" can look
  similar without answering the actual question.

---

## PART H — More professional methods (future improvements)

What practitioners do beyond a default ChromaDB setup:
- **Stronger embedding models** — e.g. OpenAI `text-embedding-3-large` instead of the free
  default; far better semantic precision (and genuinely multilingual).
- **Structure-aware chunking** — respect table/paragraph/section boundaries instead of blind
  word counts, so a table stays in one chunk.
- **Re-ranking** — retrieve top 10–20 by vector search (fast), then have an LLM re-judge which
  are truly most relevant (accurate). Combines speed with reasoning.
- **Hybrid search** — combine embedding search WITH literal keyword search to catch things each
  alone would miss (exact figures, proper nouns).
- **Metadata filtering** — tag chunks (year, section, ticker) and filter before searching.
- **Query rewriting** — have an LLM rephrase/expand the question before embedding it.
- **Persistent storage** — `chromadb.PersistentClient` to save the DB to disk instead of
  rebuilding it every run.

**The lesson you found yourself:** basic RAG is the START, not the finish. Recognizing WHY it's
only partially accurate — not just that "the code ran" — is the skill that separates someone
who runs working code from someone who understands it.

---

## The complete Chapter-7 project structure (`rag_pipeline/`)

```
rag_pipeline/
  ├── chunks.json          # copied from pdf_ingestor/output (221 chunks of the 10-K)
  └── rag_pipeline.py       # loads chunks → ChromaDB collection → embeds → semantic query
```

Pipeline: `chunks.json` → load → `collection.add()` (auto-embeds locally) → `collection.query()`
turns the question into a vector and returns the nearest chunks. This is the retrieval half of
RAG; adding an LLM to generate a grounded answer from the retrieved chunks is the final project.

---

## 60-second self-test (cover the answers)

1. Why does literal (Ctrl+F) search fail where embeddings succeed? → literal matches exact words; embeddings match MEANING
2. What is an embedding, in one line? → text converted to a vector of numbers where similar meaning = nearby vectors
3. How does a model "learn" meaning without being given definitions? → from context — words in similar contexts converge to similar vectors
4. What is a "vector," really? → just a (long) list of numbers
5. What does cosine similarity measure? → how close two vectors are (≈1 similar, ≈0 unrelated)
6. Does calling an embeddings API cost tokens? → yes, input tokens only; but ChromaDB's default model runs locally = free
7. Why a vector DB instead of a plain list + loop? → indexed structure scales to many thousands of vectors; fast nearest-neighbor
8. The three steps of RAG? → index chunks, embed the query, search for nearest chunks
9. What surprising thing is ALSO embedded, besides the chunks? → the user's question
10. In `collection.add(documents=...)`, who computes the embeddings? → ChromaDB, automatically, with a local default model
11. `results["documents"][0]` — why the `[0]`? → results is a list per query; [0] is the first (only) query's results
12. `[f"chunk_{i}" for i in range(n)]` — what is this and its equivalent? → a list comprehension; equals a for-loop with .append
13. What does RAG stand for and mean? → Retrieval-Augmented Generation: retrieve your chunks, add as context, LLM generates a grounded answer
14. Two big advantages of RAG over asking the LLM directly? → grounded/current in your data; reduces hallucination and is traceable
15. You saw the ideal chunk rank #5, not #1 — name two causes? → weak default embedding model; naive word-count chunking splitting the table
16. Three professional improvements beyond default RAG? → stronger embeddings, structure-aware chunking, re-ranking (also hybrid search, metadata filters)
17. Why does "retrieval quality cap everything"? → if the right chunk isn't retrieved, the LLM never sees it and can't use it
