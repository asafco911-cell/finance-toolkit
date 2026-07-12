# Python Reference — Chapter 9: FastAPI — Building an Internal API

**Project:** `finance-toolkit/rag_api/`
**Prerequisite chapters:** 3 (modules/imports), 4 (calling an API), 5 (Pydantic), 8 (the RAG pipeline being wrapped)
**Status:** Complete — working HTTP service exposing the RAG system via `POST /ask` and `GET /health`.

---

## Intro — The Inversion

Chapter 4 taught you to be an API **client**: your code sent a request to Anthropic's servers and got a response back. Chapter 9 flips the direction: you are now the API **server**. Other systems send requests to *you*.

**Analogy:** In Ch. 4 you were ordering from a restaurant. In Ch. 9 you *opened* one. FastAPI is the "restaurant-in-a-box" kit — it hands you the menu, the waiters, and the kitchen; you just define the dishes.

**Why this matters for the job:** the role description explicitly requires *"API development — FastAPI for internal interfaces connecting to company IT."* An IT team will never run `python rag_pipeline.py` on your behalf. They will call an endpoint. Without this layer, your tools stay on your laptop. With it, they become infrastructure.

---

## PART 1 — Core Concepts

| Concept | What it is | Analogy |
|---|---|---|
| **FastAPI** | Python framework for building APIs | The restaurant-in-a-box kit |
| **Uvicorn** | The *server* that actually runs your app and listens for requests | The building with an open door; FastAPI only wrote the menu |
| **Endpoint** | A specific address that performs an action (`/ask`) | An item on the menu |
| **`GET` vs `POST`** | `GET` = "give me info"; `POST` = "here's data, process it" | Asking "what's on the menu?" vs. placing an order |
| **Request Body** | The JSON the client sends — validated by Pydantic | The order form |
| **Response Model** | The structure of what comes back — validated by Pydantic | The plated dish |
| **Swagger UI (`/docs`)** | Auto-generated interactive test page | A menu you can order from directly, to test the kitchen |
| **`localhost` / `127.0.0.1`** | "This machine itself" — **not** the public internet | A service door at the back of your own building |

### `GET` vs `POST` — the rule of thumb
If the request carries a **body** (data you're sending, not just an address), it's almost always `POST`. `/ask` sends a question → `POST`. `/health` sends nothing → `GET`.

### Important clarification: this is not a public website
`http://127.0.0.1:8000` is **localhost** — only your machine can reach it. In production it would run on a company server, reachable by internal systems, not by the public. The browser is a **testing tool** here, not the intended audience. The intended clients are *other programs*.

---

## PART 2 — The Minimal App

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

- **`app = FastAPI()`** — the central object representing the whole application. Conceptually similar to the `client` object created for Anthropic in Ch. 4.
- **`@app.get("/health")`** — a **decorator** (new syntax in this course). It's a label stuck onto a function that tells FastAPI: *"when a GET request arrives at `/health`, run this function."* Without it, the function is just an ordinary `def` that nothing external can reach.
- **Returning a `dict`** — FastAPI converts it to JSON automatically. Same result as `json.dump` from Ch. 3, but handled behind the scenes.
- **Why `/health` exists** — an industry standard. It does nothing but reply "I'm alive," so DevOps/IT can automatically monitor whether the service is up without consuming real resources.

### Running it

```powershell
python -m uvicorn main:app --reload
```

| Part | Meaning |
|---|---|
| `python -m uvicorn` | Run uvicorn *through Python*. Avoids the `'uvicorn' is not recognized` PATH error common on Windows. |
| `main` | The **filename** (`main.py`, no extension) |
| `app` | The **variable** inside that file (`app = FastAPI()`) |
| `--reload` | Watch for file changes and auto-restart the server |

**The terminal stays occupied — this is correct, not a hang.** The server is a long-running process waiting for requests. Stop it with `Ctrl + C`.

---

## PART 3 — Wrapping the RAG Pipeline

```python
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "rag_pipeline"))

from fastapi import FastAPI
from pydantic import BaseModel
from rag_pipeline import retrieve, build_user_prompt, generate_answer, SYSTEM_PROMPT
from schema import RAGAnswer

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok"}


class AskRequest(BaseModel):          # ← input schema (NEW)
    question: str


@app.post("/ask", response_model=RAGAnswer)     # ← output schema (from Ch. 8!)
def ask(request: AskRequest):
    retrieved_chunks = retrieve(request.question, n_results=3)
    user_prompt = build_user_prompt(request.question, retrieved_chunks)
    result = generate_answer(SYSTEM_PROMPT, user_prompt)
    return result
```

### Pydantic now guards **both** ends

| | Model | Guards | Failure mode |
|---|---|---|---|
| **Input** | `AskRequest` | The JSON a client sends | FastAPI rejects with `422 Validation Error` **before your code runs at all** |
| **Output** | `RAGAnswer` | What your function returns | FastAPI verifies the response matches the schema |

This is the payoff for the Ch. 8 decision to return a validated `RAGAnswer` object instead of free text: **`response_model=RAGAnswer` reuses it verbatim.** Had `generate_answer()` returned prose, this line would be impossible.

### `def ask(request: AskRequest)` — the type hint does real work
The annotation `request: AskRequest` isn't documentation. FastAPI **reads** it and automatically parses + validates the incoming JSON into an `AskRequest` object before your function body executes.

---

## PART 4 — Cross-Directory Imports

`rag_api/` and `rag_pipeline/` are **sibling** folders. Python doesn't import across siblings by default.

```python
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "rag_pipeline"))
```

| Piece | What it does |
|---|---|
| `__file__` | Path of **the file this line physically lives in** |
| `os.path.dirname(__file__)` | Its containing folder (`rag_api/`) |
| `os.path.join(..., "..", "rag_pipeline")` | Go up one level, then into `rag_pipeline/`. `join` handles `\` vs `/` cross-platform. |
| `sys.path.append(...)` | `sys.path` is the list of folders Python searches for imports. We add ours to it. |

---

## PART 5 — The Two Traps Hit in This Chapter

### Trap 1: Relative file paths break under `import`

**The error:** `FileNotFoundError: No such file or directory: 'chunks.json'`

**Why:** `rag_pipeline.py` opened `"chunks.json"` — a **relative** path, resolved against the *current working directory*. That worked when running `python rag_pipeline.py` **from inside** `rag_pipeline/`. But uvicorn runs from `rag_api/`, so Python looked for `rag_api/chunks.json`, which doesn't exist.

This is the **Working Directory trap** from Ch. 3, in a more advanced disguise.

**The fix — anchor paths to the file, not the working directory:**
```python
BASE_DIR = os.path.dirname(__file__)
CHUNKS_PATH = os.path.join(BASE_DIR, "chunks.json")

with open(CHUNKS_PATH, "r", encoding="utf-8") as file:
    chunks = json.load(file)
```

**Critical rule:** `__file__` always points to **the file where the line physically sits** — never to the file that imported it. Therefore this fix belongs inside `rag_pipeline.py`, not `main.py`. (Putting it in `main.py` was the first attempt, and it failed for exactly this reason.)

**Generalized rule:** *any file that might be imported from elsewhere must build data paths with `__file__`, never with bare relative strings.*

### Trap 2: `import` executes the whole file

**The symptom:** every time the server started or reloaded, it printed `=== Question: What was the revenue growth? ===` and made a real (billable) Claude API call — before any client had asked anything.

**Why:** when Python imports a module, it **runs the entire file top to bottom, once.** Two kinds of lines behave differently:

| Line type | On import |
|---|---|
| `def foo(): ...` — a **definition** | Registered, but **not executed**. Like writing a recipe in a cookbook. |
| `result = generate_answer(...)` — a **bare statement outside any `def`** | **Executed immediately.** Like actually cooking. |

Importing `retrieve` does not "skip" the rest of the file. Everything outside a `def` runs regardless of what you imported.

**The fix:**
```python
if __name__ == "__main__":
    question = "What was the revenue growth?"
    ...
    print(f"Found: {result.found}")
```

**How it works:** `__name__` is a special variable Python sets automatically in every file:

| How the file was invoked | Value of `__name__` inside it |
|---|---|
| `python rag_pipeline.py` (run directly) | `"__main__"` |
| `import rag_pipeline` (imported) | `"rag_pipeline"` |

So `if __name__ == "__main__":` means *"only run this if I'm the file being executed directly, not if someone merely imported me."*

**What NOT to wrap:** the **Setup** block (loading `chunks.json`, building the ChromaDB collection) must still run on import — the API needs `collection` to exist before any request arrives. Only the **demo/run** block gets wrapped.

---

## PART 6 — Testing via Swagger UI

Navigate to `http://127.0.0.1:8000/docs`. FastAPI generated this page **automatically** — zero lines of code written for it.

1. Expand `POST /ask` → **Try it out**
2. Enter the request body:
   ```json
   {"question": "What were the main risk factors mentioned in the report?"}
   ```
3. **Execute**

**What to verify:**

| Response code | Meaning |
|---|---|
| `200` | Success |
| `422` | Validation error — the request body didn't match `AskRequest` |
| `500` | Internal server error — your code raised an exception |

**Proof it traveled over the network:** the terminal logs a line in real time:
```
INFO: 127.0.0.1:50503 - "POST /ask HTTP/1.1" 200 OK
```
This is the difference between calling a Python function directly and calling a **service**. Swagger UI is only a test client — it *composed and sent an HTTP request* to the uvicorn server. Closing the browser wouldn't stop the server.

**Equivalent curl** (Swagger even shows it):
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What was the revenue growth?"}'
```

---

## Full Project Structure

```
finance-toolkit/
├── rag_api/
│   ├── main.py           # FastAPI app: /health, POST /ask
│   ├── README.md         # architecture, endpoints, setup, limitations
│   └── __pycache__/      # auto-generated, gitignored
└── rag_pipeline/
    ├── chunks.json
    ├── schema.py         # RAGAnswer — now doubles as the API's response_model
    └── rag_pipeline.py   # updated: __file__-anchored paths + if __name__ guard
```

---

## Known Limitations (→ Ch. 13 & 14)

1. **Re-indexes on every restart.** The ChromaDB client is in-memory. All 221 chunks are re-embedded each time the server boots. Needs a persistent client.
2. **No authentication or rate limiting.** Anyone who can reach the port can query it.
3. **No input sanitization / prompt-injection defense.** A malicious question (or malicious text inside the filing) could attempt to override `SYSTEM_PROMPT`. (Ch. 13)
4. **Synchronous handlers.** `def ask(...)` is not `async def`, so requests are handled one at a time. Under concurrent load (several analysts asking at once), they queue.
5. **No conversation memory.** Each request is stateless.
6. **Single hardcoded document.** The API serves one indexed 10-K; there's no upload endpoint or multi-document routing.

---

## 60-Second Self-Test

1. In Ch. 4 you were the API *client*. What are you in Ch. 9?
2. What is the difference between FastAPI and Uvicorn?
3. Why is `/ask` a `POST` and `/health` a `GET`?
4. Is `http://127.0.0.1:8000` accessible from the public internet? What is it?
5. What does the `@app.post("/ask")` decorator actually do?
6. Name the two Pydantic models in the API and what each one guards.
7. Why was it possible to write `response_model=RAGAnswer` without defining anything new?
8. What HTTP status code does FastAPI return if the request body is malformed, and does your function body run in that case?
9. What does `--reload` do, and why does the terminal stay occupied when uvicorn runs?
10. Why did `open("chunks.json")` suddenly fail once `rag_pipeline` was imported by `main.py`?
11. What does `__file__` point to — the file containing the line, or the file that imported it?
12. When Python imports a module, which lines execute and which don't?
13. What are the two possible values of `__name__`, and what determines which one you get?
14. Why must the **Setup** block (ChromaDB indexing) stay *outside* the `if __name__ == "__main__":` guard?
15. Who generated the `/docs` page, and how much code did you write for it?
16. When you click Execute in Swagger, what proves the request traveled over the network rather than being a direct function call?
17. Name two production limitations of the current API.
18. What does `sys.path.append(...)` accomplish?

---

### Answers

1. The API **server**. Other systems now call you.
2. FastAPI defines the routes and logic; **Uvicorn is the server process** that actually listens on a port and runs the app. FastAPI alone cannot receive requests.
3. `/ask` carries a **body** (the question) and triggers processing → `POST`. `/health` sends nothing and only reports status → `GET`.
4. No. `127.0.0.1` is **localhost** — the machine itself. Only you can reach it. The browser is a testing tool, not the target audience.
5. It registers the function with FastAPI so that a POST request to `/ask` invokes it. Without the decorator, it's an ordinary function unreachable from outside.
6. `AskRequest` guards the **input** (incoming JSON). `RAGAnswer` guards the **output** (the response).
7. Because `RAGAnswer` was already built in Ch. 8 as the validated return type of `generate_answer()`. Structured output paid off immediately.
8. `422 Validation Error` — and **no**, your function body never runs. FastAPI rejects it first.
9. `--reload` auto-restarts the server when files change. The terminal stays occupied because the server is a **long-running process** waiting for requests — that's correct behavior, not a hang. `Ctrl + C` stops it.
10. `"chunks.json"` is a **relative** path, resolved against the current working directory. Uvicorn ran from `rag_api/`, so Python looked for `rag_api/chunks.json`. (The Working Directory trap.)
11. **The file containing the line.** Always. That's why the fix had to go inside `rag_pipeline.py`, not `main.py`.
12. `def` definitions are **registered but not executed**. Every bare statement **outside** a `def` is **executed immediately** — including function calls — regardless of what you imported.
13. `"__main__"` if the file was run directly (`python file.py`); the module's own name (`"rag_pipeline"`) if it was imported.
14. Because the API needs the ChromaDB `collection` to exist before any request arrives. Guarding it would leave `retrieve()` with nothing to query.
15. FastAPI generated it **automatically**, from the type hints and Pydantic models. Zero lines written for it.
16. The terminal log line: `INFO: 127.0.0.1:xxxxx - "POST /ask HTTP/1.1" 200 OK`. That's an HTTP request, not a function call.
17. Any two of: no auth/rate limiting; re-indexes on every restart; no prompt-injection defense; synchronous (non-async) handlers; no conversation memory; single hardcoded document.
18. It adds a folder to the list of locations Python searches when resolving `import` statements — enabling the cross-sibling-directory import of `rag_pipeline`.

---

## Where This Leads

| Next | What it adds |
|---|---|
| **Ch. 10 — Frameworks/Agents** | Rewrite the RAG core in LlamaIndex; build an agent that chooses tools. You built it by hand first — now you'll see what frameworks hide. |
| **Ch. 13 — Security** | Auth, prompt-injection defense, architecture doc — turning this from a demo into something IT would deploy. |
| **Ch. 14 — Capstone** | Persistent vector DB, chunk metadata for page-level citations, polished README + screenshots. This API is roughly 80% of the capstone. |

**Interview framing:** you can now say *"I built a RAG system from scratch and exposed it as a FastAPI service with validated request/response schemas, a health endpoint, auto-generated OpenAPI docs, and grounded, source-cited answers — and I can explain every architectural decision, including what I'd fix before production."* That sentence is the entire point of Chapters 1–9.
