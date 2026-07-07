# Python & LLM APIs — Study Reference (Chapter 4)

> Working with LLM APIs (Anthropic + OpenAI): keys, requests, tokens, cost.
> Same rule: if you can predict the output *before* running it, you understand it.
> Companion to the Chapter 1–2 and Chapter 3 reference sheets.

---

## PART A — Core Concepts (the vocabulary)

| Term | What it is | Analogy |
|---|---|---|
| **API** | how your code talks to an external service | a waiter — you order, the kitchen (model) cooks, you get a dish back |
| **API Key** | a personal secret that identifies AND bills you | a credit card + ID in one; keep it absolutely secret |
| **Request** | what you send (the message + instructions) | your order |
| **Response** | what comes back (usually JSON) | the dish delivered |
| **Tokens** | text units the model counts, for input AND output | minutes on a phone plan — you're billed by usage |
| **System Prompt** | the model's role/rules, constant across the chat | the job briefing to an employee |
| **User Prompt** | the specific task for this request, changes each time | today's actual assignment |
| **Temperature** | how creative (high) vs consistent (low) the model is | consistent employee vs improvising one |
| **Streaming** | receiving the reply word-by-word in real time | reading a live-typed message vs a full letter |

**Key insight on temperature:** for financial analysis (summarizing facts, numbers),
use `temperature=0.0` — you want accuracy and consistency, NOT creativity.

**Key insight on tokens:** a long earnings report = many tokens = real money.
Cost matters when running across hundreds of tickers. Different providers count the
SAME text as different token counts (different tokenizers) — you can't guess, you measure.

---

## PART B — Securing API Keys (`.env` + dotenv)

### The golden rule
NEVER hardcode a key in your code. If it's in the code, it goes to GitHub, and anyone
can spend on your account.

```python
# ❌ NEVER
api_key = "sk-ant-api03-abc123..."

# ✅ ALWAYS
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")
```

### The `.env` file (in your project root)

```
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
OPENAI_API_KEY=sk-proj-your-key-here
```

Rules: no quotes, no spaces around `=`, one key per line.

### How the pieces fit
- `load_dotenv()` — reads `.env` and loads its values into the program's environment
- `os.getenv("NAME")` — retrieves a value by name; returns `None` if missing
- Verify without exposing: `print(f"Key loaded: {api_key is not None}")` — prints `True`,
  NEVER the key itself. Never print secrets, even in tests.

### `.env` MUST be in `.gitignore`
Confirm the line `.env` exists in `.gitignore`. It protects `.env` even inside subfolders
(`earnings_summarizer/.env`). **Always check `git status` before `add` — `.env` must NOT appear.**

---

## PART C — SDKs (Software Development Kits)

An SDK is a ready-made Python library the provider wrote, wrapping the messy networking
details into simple function calls.

```bash
pip install anthropic python-dotenv openai
```

- `anthropic` — Claude's official SDK
- `openai` — GPT's official SDK
- `python-dotenv` — reads `.env` files

`pip` is smart: "Requirement already satisfied" means it's installed; it won't reinstall.

---

## PART D — The Client pattern (same idea as a class instance)

Creating a client is exactly like `aapl = Stock("AAPL", 28)` from Chapter 3 — you make an
INSTANCE that remembers your key for every future call.

```python
from anthropic import Anthropic
from openai import OpenAI

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

---

## PART E — Calling Anthropic (Claude)

```python
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=500,                    # ceiling on OUTPUT length — cost protection
    system=SYSTEM_PROMPT,              # system prompt = SEPARATE parameter
    messages=[
        {"role": "user", "content": text}
    ]
)

summary = response.content[0].text            # extract the text
input_tokens = response.usage.input_tokens    # API reports token counts for you
output_tokens = response.usage.output_tokens
```

**`messages` is a list of dicts** — exactly the structure from Chapters 2–3. Each dict is
one turn: `"role"` (`"user"` or `"assistant"`) + `"content"`.

`response.content[0]` — the `[0]` is index 0 (lists start at 0, Chapter 3). `.text` pulls
the actual string out of that content block.

---

## PART F — Calling OpenAI (GPT) — and the differences that matter

```python
response = openai_client.chat.completions.create(
    model="gpt-4o",
    max_tokens=500,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},   # system goes INSIDE messages here
        {"role": "user", "content": text}
    ]
)

summary = response.choices[0].message.content
input_tokens = response.usage.prompt_tokens
output_tokens = response.usage.completion_tokens
```

### The critical comparison table (memorize this)

| | Anthropic | OpenAI |
|---|---|---|
| create client | `Anthropic(api_key=...)` | `OpenAI(api_key=...)` |
| the call | `client.messages.create(...)` | `client.chat.completions.create(...)` |
| system prompt | **separate** param: `system="..."` | **inside** messages: `{"role":"system",...}` |
| extract reply | `response.content[0].text` | `response.choices[0].message.content` |
| input tokens | `response.usage.input_tokens` | `response.usage.prompt_tokens` |
| output tokens | `response.usage.output_tokens` | `response.usage.completion_tokens` |

**Why the course made you use both:** the *idea* is identical (send system+user, get
reply+tokens), but the *technical details* differ per provider. This is what real API work
is like — you constantly adapt to each provider's specific shape.

---

## PART G — Multi-line strings & constants

```python
SYSTEM_PROMPT = """You are a careful financial analyst. Summarize in 5 bullets:
1. Revenue
2. Profit/Earnings
3. Surprises
4. Risks
5. Management tone"""
```

- **`"""..."""`** (triple quotes) — a multi-line string; single quotes can't break lines.
- **ALL_CAPS name** — convention for a "constant" (a value that won't change). Python
  doesn't enforce it, but it signals intent to any reader.
- Define the prompt ONCE, reuse it for both providers — "define once, use many times."

---

## PART H — Measuring token cost

Prices are quoted PER MILLION tokens (industry standard). The API returns exact counts;
you just multiply.

```python
# Example rates — ALWAYS verify current prices on the provider's pricing page
claude_cost = (input_tokens / 1_000_000) * 3 + (output_tokens / 1_000_000) * 15
gpt_cost    = (input_tokens / 1_000_000) * 2.5 + (output_tokens / 1_000_000) * 10

print(f"Cost: ${claude_cost:.4f}")   # :.4f = 4 decimals (single calls cost fractions of a cent)
```

- `1_000_000` — underscores are just visual separators for readability (= 1000000).
- `:.4f` inside an f-string — format with 4 digits after the decimal point.
- Input and output are priced DIFFERENTLY (output usually costs more).

---

## PART I — Useful patterns from this chapter

### Encoding for text files
```python
with open("earnings_release.txt", "r", encoding="utf-8") as file:
    text = file.read()
```
`encoding="utf-8"` — a safe habit for ANY text file; prevents character corruption
(critical for Hebrew/non-English; harmless for English).

### RTL display quirk (Hebrew in the terminal)
PowerShell may render Hebrew reversed/garbled — this is a TERMINAL display issue, NOT a
code or data bug. The string is stored correctly. Fix: write output to a file
(`encoding="utf-8"`) and open in VS Code, or work in English (financial text usually is).

### String multiplication
```python
print("=" * 60)   # a line of 60 '=' characters — visual separators without typing them
```

### Save before you run
The `U` (or a dot ●) next to a tab = UNSAVED. `Ctrl+S` before every run. An `ImportError:
cannot import name X` often means the module file wasn't saved — Python read the old version on disk.

---

## The complete Chapter-4 project structure (`earnings_summarizer/`)

```
earnings_summarizer/
  ├── earnings_release.txt   # real earnings press release (input)
  ├── summarizer.py           # summarize_with_anthropic() + summarize_with_openai()
  └── main.py                  # reads file, calls both, prints side-by-side, compares cost
```

Data flow: `earnings_release.txt` → `main` reads it → sends to BOTH providers via
`summarizer` → prints both summaries + token counts + estimated costs, side by side.
Same modular separation as Chapter 3: `summarizer.py` defines tools, `main.py` runs them.

---

## 60-second self-test (cover the answers)

1. Where do API keys live, and why never in code? → `.env` (gitignored); code goes to GitHub, keys would leak
2. `load_dotenv()` then `os.getenv("X")` — what does each do? → loads `.env` into env; retrieves a value by name
3. How do you verify a key loaded WITHOUT exposing it? → `print(api_key is not None)` — never print the key
4. What must you check in `git status` before every push in this chapter? → that `.env` does NOT appear
5. Temperature for summarizing financial facts — high or low, why? → low (0.0); you want accuracy/consistency, not creativity
6. System prompt vs user prompt? → role/rules (constant) vs the specific task (changes each call)
7. Anthropic: where does the system prompt go? → a separate `system=` parameter
8. OpenAI: where does the system prompt go? → inside `messages` as `{"role":"system",...}`
9. Extract the reply text — Anthropic vs OpenAI? → `response.content[0].text` vs `response.choices[0].message.content`
10. Token count fields — Anthropic vs OpenAI? → `input_tokens`/`output_tokens` vs `prompt_tokens`/`completion_tokens`
11. Why do the two providers report different token counts for the same text? → different tokenizers
12. What does `max_tokens` limit — input or output? → output; it caps reply length (cost protection)
13. `"""..."""` — what and why? → multi-line string; single quotes can't span lines
14. `"=" * 60` produces what? → a 60-character line of `=` (string multiplication)
15. `ImportError: cannot import name X` — first thing to suspect? → the module file wasn't saved (`Ctrl+S`)
