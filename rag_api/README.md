# RAG API — 10-K Financial Q&A Service

A FastAPI service that answers natural-language questions about a company's
10-K filing, grounded strictly in the filing's content, with source citations.

Built on top of the RAG pipeline in `../rag_pipeline/` (retrieval via ChromaDB,
generation via Claude, structured/validated output via Pydantic).

## Architecture

Client → POST /ask → FastAPI → retrieve() (ChromaDB) → build_user_prompt()
→ generate_answer() (Claude API) → RAGAnswer
→ JSON response

## Endpoints

| Method | Path      | Description                                  |
|--------|-----------|-----------------------------------------------|
| GET    | `/health` | Liveness check. Returns `{"status": "ok"}`.   |
| POST   | `/ask`    | Ask a question about the indexed 10-K filing. |
| GET    | `/docs`   | Auto-generated interactive Swagger UI.        |

### `POST /ask`

**Request body:**
```json
{
  "question": "What were the main risk factors mentioned in the report?"
}
```

**Response body (`RAGAnswer`):**
```json
{
  "found": true,
  "answer": "The main risk factors include...",
  "sources": [1, 2, 3]
}
```

- `found` — whether the answer was grounded in the retrieved excerpts.
- `answer` — the answer text, or a brief explanation if not found.
- `sources` — excerpt numbers (from the retrieved context) supporting the answer.

If the question cannot be answered from the filing, `found` will be `false`
and the system will not fabricate an answer.

## Setup

1. From `finance-toolkit/`, ensure dependencies are installed: pip install fastapi uvicorn chromadb anthropic python-dotenv pydantic
2. Ensure `rag_pipeline/.env` contains a valid `ANTHROPIC_API_KEY`.
3. Ensure `rag_pipeline/chunks.json` exists (10-K chunks — see `rag_pipeline/README` or Chapter 6/7 docs for how it's generated).

## Running

From `rag_api/`:python -m uvicorn main:app --reload

Server starts at `http://127.0.0.1:8000`. On startup, it loads and re-indexes
all chunks into an in-memory ChromaDB collection (this happens once, at
server start — not per request).

## Testing

Open `http://127.0.0.1:8000/docs`, expand `POST /ask`, click **Try it out**,
enter a question, and click **Execute**.

Or via curl:
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What was the revenue growth?"}'
```

## Known Limitations

- Vector DB is in-memory only — re-indexes on every server restart.
- Chunks carry no page-level metadata, so citations reference excerpt
  numbers, not report page numbers.
- No conversation memory — each question is independent.
- No authentication or rate limiting on the API yet.

## Tech Stack

Python · FastAPI · Uvicorn · ChromaDB · Anthropic API (Claude) · Pydantic