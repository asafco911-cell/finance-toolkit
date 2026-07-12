# Python Reference — Chapter 10: AI Frameworks & Autonomous Agents

**Project:** `finance-toolkit/rag_frameworks/`
**Prerequisite chapters:** 4 (Anthropic SDK), 5 (Pydantic), 7 (embeddings), 8 (hand-built RAG), 9 (FastAPI)
**Status:** Complete — RAG rewritten in LlamaIndex with an explicit prompt override, plus a from-scratch ReAct agent with two tools.

---

## Intro — Why Building It By Hand First Was the Whole Point

You built RAG **by hand** in Chapter 8. Now you use frameworks that do part of that work for you.

**The syllabus is explicit about why the order matters:** *"It's very important that you learned RAG by hand first — that way you'll know when the framework helps and when it hides problems."*

Most candidates for this role can say "I know LlamaIndex," meaning they can copy 20 lines from the docs. You can say something different:

> *"I built RAG from scratch — embeddings, chunking, retrieval, grounding, structured output — then rewrote it in LlamaIndex. I know exactly what `as_query_engine()` hides, and where it will break."*

That is the difference between an engineer and someone who followed a tutorial.

**Analogy:** In Ch. 8 you built furniture from raw wood — you learned carpentry. Now you assemble IKEA. Much faster, but you already understand what's under the screws.

---

## PART 1 — The Framework Landscape

| Term | What it is | Analogy |
|---|---|---|
| **Framework** | Pre-built tooling that shortens development | IKEA vs. raw lumber |
| **LangChain** | General-purpose LLM framework: chains, memory, tools, 100+ integrations | An **assembly line** — fixed stations in sequence |
| **LlamaIndex** | Specializes specifically in RAG and document indexing | A purpose-built RAG kit |
| **LangGraph** | Workflow orchestration as a **graph** — nodes, conditional edges, shared state | A **flowchart** with decision points, not a straight line |
| **Agent** | An LLM that decides *which tools to run and in what order* to reach a goal | An employee given a goal and a toolbox, not a script |
| **Tool** | A capability handed to the agent (search, calculator, DB read) | The toolbox itself |
| **CrewAI** | Multiple agents collaborating as a team | A team of analysts: one extracts, one assesses risk, one writes |

### Chain vs. Agent vs. Graph — the core distinction

| | Control flow | Who decides the order? | What you built |
|---|---|---|---|
| **Chain** | Fixed: A → B → C | **You**, in code | Ch. 8 (by hand), LlamaIndex (hidden) |
| **Agent (ReAct)** | Loop: LLM picks tools until done | **The LLM**, at runtime | `agent.py` — from scratch |
| **Graph (LangGraph)** | State machine: nodes + conditional edges | **You**, but with branches and state | Not built (next level) |

**Critical clarification:** LlamaIndex is **not** an agent. Running `as_query_engine()` executes exactly the same fixed chain you built in Ch. 8 — someone else just wrote the code and hid it.

---

## PART 2 — LlamaIndex: The Rewrite

```python
Settings.llm = Anthropic(model="claude-sonnet-4-5", api_key=os.getenv("ANTHROPIC_API_KEY"))
Settings.embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

documents = [Document(text=chunk) for chunk in chunks]
index = VectorStoreIndex.from_documents(documents)

query_engine = index.as_query_engine(similarity_top_k=3)
response = query_engine.query("What was the revenue growth?")
```

~20 lines replaced ~100. **Identical answer** (18%, $43,978M → $52,017M).

### What each object replaced

| LlamaIndex | Replaced from Ch. 8 |
|---|---|
| `Settings.llm = Anthropic(...)` | `client_anthropic` + `client.messages.create(...)` |
| `Settings.embed_model = ...` | The embedding model that was **hidden inside ChromaDB** |
| `Document(text=chunk)` | Manual `chunk_ids` construction |
| `VectorStoreIndex.from_documents()` | `chromadb.Client()` + `create_collection()` + `collection.add()` |
| `index.as_query_engine(similarity_top_k=3)` | `retrieve()` **+** `build_user_prompt()` **+** `generate_answer()` — **all three** |
| `similarity_top_k=3` | `n_results=3` |

**`as_query_engine()` swallows three hand-built stages.** That's the magic, and that's the danger.

---

## PART 3 — What the Framework HID (The Point of the Chapter)

Five things vanished from view. None of them stopped existing — they were replaced by **defaults you did not choose and cannot see**.

| # | What disappeared | Why it matters |
|---|---|---|
| **1** | **Your `SYSTEM_PROMPT`** | You wrote *"answer ONLY from context; if not found, say Not found; cite the excerpt."* LlamaIndex substituted **its own prompt**, which you have never read. |
| **2** | **Grounding guarantees** | Who prevents hallucination now? You **hope** the default is good. You didn't test. In finance, "I hope" is not an answer. |
| **3** | **`RAGAnswer` (Pydantic)** | Output is now a **free-text string**. No `found: bool`. No `sources: [1, 2]` — only a count (`len(response.source_nodes)`). You lost the structured output that made `response_model=RAGAnswer` possible in Ch. 9. |
| **4** | **Your chunking strategy** | Ch. 6 chunking (with deliberate overlap) may be **re-chunked** by LlamaIndex defaults you never picked. |
| **5** | *(Inverted!)* **The embedding model** | Here the framework **forced** you to choose explicitly — while ChromaDB (Ch. 7) hid it entirely. **Frameworks don't only hide; sometimes they expose.** |

### The insight

> **The framework didn't eliminate the stages — it hid them.** Had you not built it by hand first, you would not know that `as_query_engine()` contains a prompt written by someone else — a prompt that determines whether your system fabricates financial figures.

---

## PART 4 — Taking Control Back: Prompt Override

The mature move is not "framework OR hand-written." It's **hybrid**.

```python
from llama_index.core.prompts import PromptTemplate

GROUNDED_PROMPT = PromptTemplate(
    """You are a financial analyst assistant. Answer using ONLY the context below,
which comes from a company's 10-K filing.

Rules:
- If the answer is not in the context, say exactly: "Not found in the report."
- Do not guess and do not use outside knowledge.
- Cite the source excerpt for every claim.

Context:
---------------------
{context_str}
---------------------

Question: {query_str}
Answer: """
)

query_engine = index.as_query_engine(similarity_top_k=3)
query_engine.update_prompts(
    {"response_synthesizer:text_qa_template": GROUNDED_PROMPT}
)
```

- **`{context_str}`** — LlamaIndex injects the retrieved chunks here. This is exactly what `build_user_prompt()` did manually.
- **`{query_str}`** — the question goes here.
- **`update_prompts({...})`** — the override. *"Throw away your internal prompt. Use mine."*

### The decision rule (interview answer)

Not "prototype vs. production." The real criterion is:

> **What am I willing to let someone else's default decide?**
>
> - DB connections, retries, parsing, index management → **framework**. Let them handle the boring infrastructure.
> - *Whether my system fabricates a financial figure* → **me. Never a default.**

Use the framework for speed; **override anything business-critical**: the prompt, the grounding, the output schema, the chunking.

---

## PART 5 — Agents: The Real Shift

Everything until now was a **chain** — fixed order, every time.

An **agent** is given a **goal** and a **toolbox**, and decides *at runtime* which tools to call, in what order, and how many times.

### The ReAct loop (Reason + Act)

```
LLM thinks:  "I need net income. I don't have it. I'll use search_report."
     ↓
Tool call:   search_report("net income")
     ↓
Result:      "Net income attributable to Uber... was $10.1 billion"
     ↓
LLM thinks:  "Got it. Now I need to divide. I'll use calculator."
     ↓
Tool call:   calculator("10053 / 2100")
     ↓
Result:      4.787...
     ↓
LLM thinks:  "I have everything. Compose the answer."
     ↓
Final answer
```

**There is no magic here — it's a `for` loop and an `if`.** The loop continues while Claude says `tool_use` and stops when it says `end_turn`.

### The mechanism: Anthropic's `tool_use`

Adding one parameter — `tools=TOOLS` — changes what `messages.create()` can return:

| `stop_reason` | Meaning | What you do |
|---|---|---|
| `"end_turn"` | "I'm done, here's the answer" | Print it, exit the loop |
| `"tool_use"` | **"Run this tool for me and give me the result"** | Execute it, append the result, call again |

**Critical: Claude never executes any code.** It only *requests* a call, naming the tool and its arguments. **You** run it in Python and hand back the result. Claude is the brain; your code is the hands.

---

## PART 6 — The Agent, Built From Scratch

LangChain was attempted first and **failed**: `ImportError: cannot import name 'create_tool_calling_agent'` — the library's API had changed, and it isn't stable on Python 3.14. (The syllabus warned: *"frameworks change fast — always cross-check the official docs."* That warning landed live.)

**This is itself a lesson:** the hand-written Ch. 8 code still runs perfectly. Framework code broke on a version bump. **Frameworks are a dependency.**

So the agent was built directly against the Anthropic SDK — fewer layers, no external version risk, and it teaches the **actual mechanism** LangChain wraps.

### Tool definition — what Claude sees

```python
TOOLS = [
    {
        "name": "search_report",
        "description": (
            "Search the company's 10-K filing for information. Use this whenever you "
            "need a fact, figure, or statement that comes from the report itself. "
            "Never guess a number — always retrieve it with this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for, e.g. 'net income'"}
            },
            "required": ["query"]
        }
    },
    # ... calculator ...
]
```

**The `description` is not documentation — it is the instruction to the LLM.** A bad description produces bad tool selection. Write it like you're onboarding a new employee.

**`input_schema`** is Pydantic's idea in JSON form: it defines the parameters and their types so Claude constructs a valid call.

### The loop

```python
def run_agent(question, max_iterations=5):
    messages = [{"role": "user", "content": question}]

    for i in range(max_iterations):                       # ← hard safety ceiling
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,                                  # ← the only new parameter
            messages=messages
        )

        if response.stop_reason == "end_turn":
            return response.content[0].text

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    func = TOOL_FUNCTIONS[block.name]     # name (string) → real function
                    output = func(**block.input)          # ** unpacks {"query": "..."} into kwargs

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,          # must match the request
                        "content": output
                    })

            messages.append({"role": "user", "content": tool_results})

    return "Max iterations reached without a final answer."
```

**`messages` IS the `agent_scratchpad`** you saw in LangChain — now you can see exactly what's inside it: the question, every tool request, and every tool result. That accumulating history is the agent's memory.

**`search_report` is just a wrapper around your Ch. 8 `retrieve()`.** Your RAG pipeline became a tool.

---

## PART 7 — The Run (And the Impressive Part)

```
--- Iteration 1 ---
[stop_reason] tool_use
[TOOL CALL] search_report({'query': 'net income'})       ← Claude chose this string itself

--- Iteration 2 ---
[stop_reason] tool_use
[TOOL CALL] calculator({'expression': '10053 / 2100'})   ← inferred the next step alone

--- Iteration 3 ---
[stop_reason] end_turn
```

**Nobody told it the sequence.** There is no `if` in your code saying "search first, then calculate."

And the final answer went further than asked:

> *"Note: This is very close to the actual basic EPS of $4.82 reported in the 10-K, which used a weighted-average of 2,085.253 million shares rather than the flat 2.1 billion you specified."*

The agent **critiqued the premise of the question** — flagging that the user's flat share count differs from the report's weighted average. That is exactly *"autonomous analysis of financial reports"* from the job description.

---

## PART 8 — The Risks (Interview-Critical)

Autonomy is not free. Five risks, in order of severity for a financial firm:

| # | Risk | Why it's dangerous |
|---|---|---|
| **1** | **Infinite loop / failure to converge** | The agent doesn't decide to stop. Without `max_iterations`, a stuck agent burns tokens (money) indefinitely. |
| **2** | **Error propagation** ⚠️ | If `search_report` returns the **wrong number** (Adjusted EBITDA instead of Net income — they look similar in a 10-K), the calculator will compute it **perfectly**. The result is **mathematically precise and factually wrong** — and it *looks* authoritative. This is worse than an obviously-wrong answer. |
| **3** | **Non-determinism** | The same question twice can produce different tool paths and different answers. Before a regulator, "sometimes X, sometimes Y" is unacceptable. |
| **4** | **Tools with side effects** | Read-only tools that fail return a bad answer. A `execute_trade` or `send_email` tool that fails does **real, irreversible damage**. |
| **5** | **Prompt injection** | Text hidden *inside the 10-K itself* ("Ignore previous instructions...") arrives as a "tool result" and may be obeyed. (→ Ch. 13) |

### Risk #2, observed live

The `[TOOL RESULT]` for `search_report("net income")` was noisy table soup containing `$10,099`, `(242)`, `(336)`, `$6,895`, `$9,763`... Claude extracted `10,053`.

**How do you know it extracted the right one?** In the code as originally written — **you don't.** The output was truncated to 200 chars, and `10,053` didn't even appear in the visible portion.

Had it grabbed `10,099` instead, the answer would have been **$4.81** — equally clean, equally plausible, equally undetectable.

### Four layers of defense

| Layer | Defense | Strength |
|---|---|---|
| **1** | **Full provenance logging.** Never truncate tool output. Log everything that entered the agent's context. | Enables auditing after the fact |
| **2** | **Demand verbatim citation.** System prompt: *"When you extract a figure, you MUST quote the exact sentence it came from."* | Lets you verify the number's origin |
| **3** | **Deterministic tools.** Replace free-text `search_report(query)` with `get_financial_metric("net_income")` reading from **structured data** (the Ch. 6 `income_statement.csv`), not text soup. | Removes LLM judgment from the critical path |
| **4** | **Human-in-the-loop.** "Found net_income = $10,053M from this sentence: [...]. Confirm?" before proceeding. | Mandatory for irreversible actions |

**The principle:** *the more critical the task, the less discretion you leave the LLM.* Don't make it extract numbers from soup — hand it numbers already extracted.

### The closing insight

> **Agents are not "a system that gives answers." They are "a system that does work a human must verify."**
>
> Their value is **time saved**, not **responsibility removed**. The most dangerous failure mode is not that the agent fails — it's that it returns a **wrong number that looks right**.

**Interview answer to "would you let an autonomous agent analyze filings?"** — neither yes nor no:

> *"Yes, for retrieval and analysis — with a bounded `max_iterations`, full logging of every tool call, a requirement to quote verbatim any figure extracted, and deterministic tools wherever possible instead of free-text search. No, for irreversible actions without human approval. The most dangerous problem isn't that it fails — it's that it returns a wrong figure that looks correct."*

---

## PART 9 — LangGraph (Concept)

**The problem it solves:** a ReAct agent is a **simple loop** — "keep calling tools until done." That breaks down when you need:

- **Conditional branches** — "if confidence < 70%, route to human review; else continue"
- **Shared state** across steps
- **Controlled retries** — "retry, but max 3 times, and only on error type X"
- **Multi-agent teams** — extractor → risk analyst → report writer

**What it is:** LangGraph models the workflow as a **graph** — nodes and conditional edges — instead of a loop. You explicitly declare: *"from this node, if condition X, go there; otherwise, go elsewhere."*

**Analogy:** If LangChain is an **assembly line** (straight, station after station), LangGraph is a **flowchart** with decision points, branches, and loop-backs.

**Financial example:**
```
[10-K input]
     ↓
[extract figures] ──→ all figures found?
     ↓ no                    ↓ yes
[human review]        [risk analysis]
                            ↓
                    confidence > 80%?
                     ↓ no          ↓ yes
              [flag for review]  [write report]
```

**When you need it:** not for simple pipelines. **Yes** when the flow has decision points and you need control and reliability — i.e., **exactly a regulated financial environment**.

**Interview framing:** *"A ReAct agent is a loop. LangGraph is a state machine. In regulated financial production you want a state machine — because you need to know exactly what state the system is in, and where the human enters."*

---

## Full Project Structure

```
finance-toolkit/
└── rag_frameworks/
    ├── llamaindex_rag.py    # Ch. 8 RAG rewritten in ~20 lines + explicit prompt override
    └── agent.py             # ReAct agent from scratch: 2 tools, bounded loop, full logging
```

---

## Known Limitations (→ Ch. 13 & 14)

1. **`search_report` returns free text**, so the agent must extract numbers from noisy table soup. Should be replaced by a deterministic metric lookup.
2. **`calculator` uses `eval()`** — sandboxed here (`{"__builtins__": {}}`), but `eval` on model-generated input is a code-execution risk in principle. A safe expression parser (e.g. `ast.literal_eval` or `sympy`) is the production answer.
3. **No human-in-the-loop.** The agent runs to completion unsupervised.
4. **No prompt-injection defense** on retrieved chunks. (Ch. 13)
5. **Non-deterministic.** Same question may take different tool paths.
6. **LangChain not covered hands-on** — it broke on Python 3.14. A Python 3.12 virtualenv would be needed to build with it.
7. **LlamaIndex version still returns free text**, not `RAGAnswer`. The structured-output override (`output_parser`) was not implemented.

---

## 60-Second Self-Test

1. Is LlamaIndex an agent? What is it actually running?
2. Which three hand-built Ch. 8 functions does `as_query_engine()` replace?
3. Name three things LlamaIndex hid that you had explicitly built in Ch. 8.
4. Which thing did LlamaIndex *expose* that ChromaDB had hidden?
5. What is the real decision criterion for "framework vs. hand-written"?
6. What do `{context_str}` and `{query_str}` do in a `PromptTemplate`?
7. What is the difference between a chain, an agent, and a graph?
8. What are the two values of `stop_reason` in the agent loop, and what does each trigger?
9. Does Claude execute your tool code? Who does?
10. In a tool definition, what is the `description` field actually for?
11. What does `func(**block.input)` do?
12. Why must `tool_use_id` be included in the tool result?
13. What plays the role of LangChain's `agent_scratchpad` in the hand-built agent?
14. Why is `max_iterations` not optional?
15. Explain "error propagation" and why it's the most dangerous risk in a financial agent.
16. Why is `output[:200]` in the logging a real problem, not a cosmetic one?
17. Name the four layers of defense against a wrong-but-plausible agent answer.
18. What does LangGraph give you that a ReAct loop cannot?
19. Why did LangChain fail here, and what does that teach about frameworks?

---

### Answers

1. **No.** It runs the same **fixed chain** as Ch. 8 (retrieve → augment → generate). Someone else just wrote and hid the code.
2. `retrieve()`, `build_user_prompt()`, and `generate_answer()` — all three, in one call.
3. Any three of: your `SYSTEM_PROMPT`; grounding guarantees; the `RAGAnswer` Pydantic schema; your chunking strategy.
4. The **embedding model** — LlamaIndex forces an explicit choice (`HuggingFaceEmbedding(...)`), while ChromaDB used a hidden default.
5. **"What am I willing to let someone else's default decide?"** Infrastructure → framework. Whether the system fabricates a financial figure → never a default.
6. `{context_str}` is where the framework injects the retrieved chunks; `{query_str}` is where the question goes. Together they're the framework's version of `build_user_prompt()`.
7. **Chain** = fixed order you coded. **Agent** = loop where the LLM picks tools at runtime. **Graph** = state machine with conditional branches and shared state.
8. `"end_turn"` → Claude is done; return the text and exit the loop. `"tool_use"` → Claude wants a tool run; execute it, append the result, and call again.
9. **No.** Claude only *requests* a call (naming the tool and arguments). **Your Python code** executes it and returns the result. Claude is the brain, your code is the hands.
10. It is **the instruction to the LLM** about when to use the tool — not documentation. A bad description causes bad tool selection.
11. `**` unpacks the dict into keyword arguments: `{"query": "net income"}` becomes `search_report(query="net income")`.
12. So Claude knows **which request** each result corresponds to — it may have requested several tools in one turn.
13. The `messages` list. It accumulates the question, every tool request, and every tool result — that's the agent's working memory.
14. Because the agent doesn't decide to stop on its own. Without a ceiling, a non-converging agent loops indefinitely, burning tokens and money.
15. A wrong figure retrieved in step 1 gets computed **perfectly** in step 2. The output is mathematically precise and factually wrong — and looks authoritative. Worse than an obviously-broken answer, because it's undetectable.
16. Because the extracted number (`10,053`) **didn't appear** in the first 200 characters. The truncation destroyed the audit trail — you literally could not verify where the figure came from.
17. (1) Full provenance logging. (2) Demand verbatim citation of the source sentence. (3) Deterministic tools instead of free-text search. (4) Human-in-the-loop before irreversible actions.
18. Conditional branching, shared state, controlled retries, and multi-agent handoffs — a **state machine** rather than a simple loop. Essential when you need to know exactly what state the system is in and where a human enters.
19. `create_tool_calling_agent` no longer existed in the installed version — the API had changed, and LangChain isn't stable on Python 3.14. Lesson: **frameworks are a dependency.** The hand-written Ch. 8 code still runs fine; the framework code broke on a version bump.

---

## Where This Leads

| Next | What it adds |
|---|---|
| **Ch. 11 — Local models** | Ollama / Hugging Face. Directly relevant to data security: run the LLM on-prem so no client data ever leaves the firm. |
| **Ch. 13 — Security** | Prompt-injection defense (Risk #5), architecture documentation. |
| **Ch. 14 — Capstone** | Deterministic tools, page-level citations, persistent index — turning Risk #2's defenses from theory into code. |

**Interview framing:** *"I built RAG by hand, then in LlamaIndex — and I can tell you exactly what the framework hid, including the prompt that determines whether it hallucinates. I built a ReAct agent from scratch against the raw `tool_use` API, so I know what LangChain's `AgentExecutor` is actually doing. And I can tell you the failure mode that scares me: not that the agent breaks, but that it returns a wrong number that looks right."*
