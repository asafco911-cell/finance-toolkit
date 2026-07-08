# Prompt Engineering & Structured Outputs — Study Reference (Chapter 5)

> Prompt engineering, JSON mode, and Pydantic validation — turning an LLM from a
> "toy" into a reliable infrastructure component.
> Same rule: if you can predict the output *before* running it, you understand it.
> Companion to the Chapter 1–4 reference sheets.

---

## PART A — Prompt Engineering techniques

### The core idea
The precision of your request determines whether the answer is USABLE by code, not just
readable. A vague prompt gives a random result; a precise prompt gives a consistent,
parseable one.

```python
# ❌ vague — unpredictable
"Tell me about this report"

# ✅ precise — predictable, machine-usable
"""Extract exactly these 4 fields: revenue, net_income, eps, guidance.
Return ONLY valid JSON, no text before or after."""
```

### The three techniques and when to use each

| Technique | What it does | When to use |
|---|---|---|
| **Precise prompt** | clear, specific instructions | ALWAYS — the baseline for everything |
| **Few-shot** | give 1–3 input→output examples | to lock in a FORMAT or teach a pattern by example |
| **Chain-of-Thought** | ask the model to reason step-by-step | for CALCULATION or multi-step REASONING tasks |

**The judgment call (from this chapter):** for a pure EXTRACTION task (pull 4 fields that
already exist in the text), a precise prompt is enough — no chain-of-thought needed (nothing
to calculate), though few-shot can help pin the exact JSON format. Match the technique to the
task type: extraction → precise; reasoning/math → chain-of-thought; format/pattern → few-shot.

### Few-shot example structure
```
Classify sentiment as Positive/Neutral/Negative.

Example 1:
Text: "We exceeded expectations and raised guidance."
Sentiment: Positive

Now classify:
Text: "We're cutting guidance amid headwinds."
Sentiment:
```

---

## PART B — Structured Output: why "almost JSON" breaks everything

### The problem
Without enforcement, a model may wrap JSON in chatter or markdown:

```
Sure! Here's the data:
```json
{"revenue": 5000000, ...}
```
Let me know if you need more!
```

`json.loads()` on this **CRASHES** (`JSONDecodeError`) — it expects pure JSON only.

### Why this is severe, not just wasteful
It's not about a few wasted tokens. In an automated pipeline running unattended over 400
reports, one stray word breaks `json.loads()` → the program **crashes**, not "continues with
waste." And it's INCONSISTENT — sometimes clean, sometimes not — so it may crash on report
#247 at night, with no human watching. "Structured output + validation" is exactly what turns
an LLM from a toy (a human reads the answer) into infrastructure (other code trusts the format
100% of the time).

### Two enforcement layers

**Layer 1 — instruct in the prompt (both providers):**
```python
SYSTEM_PROMPT = """Return ONLY the raw JSON object, starting with { and ending with }.
Do NOT wrap it in markdown code fences (no ```json or ```).
Do NOT include any explanation before or after.
Numbers must be plain (121700000, NOT "121.7 million").
guidance must always be a string — use "not mentioned" if absent, never null."""
```

**Layer 2 — OpenAI's built-in JSON mode (server-enforced):**
```python
response = openai_client.chat.completions.create(
    model="gpt-4o",
    response_format={"type": "json_object"},   # API GUARANTEES valid JSON
    messages=[...]
)
```
This is enforcement, not a polite request. But valid JSON still isn't guaranteed to have the
RIGHT fields — that's what Pydantic (Part C) is for.

**Layer 3 — defensive code: strip markdown fences even if the model adds them anyway:**
```python
raw_text = response.content[0].text.strip()
if raw_text.startswith("```"):
    raw_text = raw_text.split("```")[1]     # take the middle piece
    if raw_text.startswith("json"):
        raw_text = raw_text[4:]              # drop the word "json"
    raw_text = raw_text.strip()
```
Prompt instructions aren't obeyed 100% of the time — back yourself up in code.

---

## PART C — Pydantic: the schema validator

### The idea
Pydantic is a "bank clerk checking a form BEFORE it enters the system" — if a field is
missing or the wrong type, it hands the form back immediately with a precise explanation,
instead of letting bad data crawl in and cause a mysterious bug later.

### Defining a schema (same idea as a class from Chapter 3)
```python
from pydantic import BaseModel, Field

class EarningsData(BaseModel):
    revenue: float = Field(description="Total revenue in USD, as a number")
    net_income: float = Field(description="Net income in USD, as a number")
    eps: float = Field(description="Earnings per share, as a number")
    guidance: str = Field(description="raised, lowered, maintained, or not mentioned")
```

- `class X(BaseModel)` — like `class Stock` (Ch. 3), but Pydantic auto-builds `__init__`.
- `revenue: float` — a TYPE ANNOTATION: this field MUST be a float.
- `Field(description=...)` — optional metadata; documents the field for humans AND can be
  exported into the prompt so the model knows exactly what's expected.

### Creating & accessing (dot notation, NOT brackets)
```python
data = EarningsData(revenue=5000000, net_income=1200000, eps=2.5, guidance="raised")
print(data.revenue)   # 5000000.0  — access with a dot, like aapl.ticker (Ch.3)
```
Note: `5000000` (int) became `5000000.0` (float) — automatic type coercion.

### Type coercion — flexible when sensible, strict when not
| Input | Result | Why |
|---|---|---|
| `eps=5000000` (int) | `5000000.0` | int→float is unambiguous |
| `eps="2.5"` (str) | `2.5` | string clearly represents a number |
| `eps="not a number"` | **ValidationError** | no sensible conversion |
| `eps="121.7 million"` | **ValidationError** | "million" can't be auto-interpreted |
| field missing entirely | **ValidationError** | nothing to convert |

Pydantic sits between "too strict" and "too lax" — it coerces when obvious, rejects when not.

### Feeding JSON into Pydantic
```python
raw_data = json.loads(response_text)       # text → dict  (Ch. 3)
validated = EarningsData(**raw_data)        # dict → validated object
```
`**raw_data` — the double-star "unpacks" all dict key-value pairs as separate arguments,
equivalent to `EarningsData(revenue=..., net_income=..., ...)` but automatic for any fields.

### Validation type ≠ content quality
`guidance: str` only checks it's a STRING — it won't reject a long paragraph when you wanted
one of four categories. To enforce exact categories, use
`Literal["raised", "lowered", "maintained", "not_mentioned"]` instead of `str`.

---

## PART D — The two safety nets (try/except with two error types)

```python
from pydantic import ValidationError   # Pydantic-specific — must be imported

try:
    raw_json = json.loads(raw_text)         # net 1: is it valid JSON at all?
    validated = EarningsData(**raw_json)     # net 2: does it match the schema?
    return validated, input_tokens, output_tokens
except json.JSONDecodeError:                 # caught if NOT valid JSON
    print(f"Raw response was: {raw_text}")   # print the raw text — essential for debugging
    return None, input_tokens, output_tokens
except ValidationError as e:                  # caught if valid JSON but wrong structure
    print(f"Schema mismatch:\n{e}")           # 'e' holds exactly which field failed
    return None, input_tokens, output_tokens
```

- `except json.JSONDecodeError` — the model returned non-JSON (chatter, markdown, etc.)
- `except ValidationError as e` — JSON is valid but a field is missing/wrong-typed; `as e`
  captures the details so you can see exactly what failed.
- The function ALWAYS returns something (validated object OR None) — it never crashes.
- Return tokens even on failure: you were still billed for the API call, so the total stays accurate.

---

## PART E — Useful patterns from this chapter

### `if __name__ == "__main__":`
```python
if __name__ == "__main__":
    test = EarningsData(revenue=5000000, net_income=1200000, eps=2.5, guidance="raised")
    print(test)
```
Runs a block ONLY when the file is executed directly (`python schema.py`), NOT when another
file imports it. Lets you test a "tools" module without the test firing on import.

### Accumulator pattern (same as the counter, Ch. 3)
```python
total_input_tokens = 0                 # initialize before the loop
for filename in report_files:
    ...
    total_input_tokens += input_tokens  # add each call's tokens (not just +1)
print(total_input_tokens)               # sum across all reports, after the loop
```
Like `cheap_count += 1`, but adding a variable amount instead of a fixed 1.

### Number formatting for money
```python
f"${result.revenue:,.0f}"   # 5000000.0 → "$5,000,000"
```
- `,` — thousands separators
- `.0f` — no decimals (cleaner for large dollar amounts)
- handles negatives correctly too: `-177000000` → `-$177,000,000`

---

## The complete Chapter-5 project structure (`financial_extractor/`)

```
financial_extractor/
  ├── report1_panw.txt, report2_camt.txt, report3_amzn.txt   # 3 different inputs
  ├── schema.py       # EarningsData (Pydantic BaseModel with 4 typed fields)
  ├── extractor.py     # extract_earnings_data(): API call + fence-strip + validate
  └── main.py           # loops all 3 reports, prints results + accumulates token cost
```

Data flow: each report → `main` reads it → `extractor` calls the API, strips markdown,
parses JSON, validates against the schema → returns a validated object (or None on failure) →
`main` prints results and sums total tokens/cost. Every report is processed independently:
one failure prints "Skipping…" and the loop continues (resilient pipeline).

---

## 60-second self-test (cover the answers)

1. Match the task to the technique: extracting 4 existing fields? → precise prompt (no CoT needed)
2. When is Chain-of-Thought worth it? → calculation / multi-step reasoning tasks
3. Why is "valid JSON wrapped in chatter" severe, not just wasteful? → `json.loads` crashes; breaks unattended automation inconsistently
4. Two enforcement layers for clean JSON? → prompt instruction + (OpenAI) `response_format`, plus defensive fence-stripping in code
5. What is Pydantic's job in one sentence? → validate that parsed data matches an expected schema, before it enters your system
6. `revenue: float` — what does the annotation do? → requires the field to be (or coerce to) a float
7. `eps="2.5"` vs `eps="121.7 million"` — what does Pydantic do? → coerces "2.5"→2.5; rejects "121.7 million" (ValidationError)
8. Access a Pydantic field — dot or brackets? → dot (`result.revenue`), like a class instance
9. What does `**raw_data` do? → unpacks dict keys/values into separate keyword arguments
10. Two except types you need, and when each fires? → `JSONDecodeError` (not valid JSON) / `ValidationError` (valid JSON, wrong structure)
11. Why import `ValidationError` but not `JSONDecodeError`? → ValidationError is Pydantic-specific; JSONDecodeError is under the built-in json module
12. Why return tokens even when extraction fails? → you were billed regardless; keeps the total accurate
13. `if __name__ == "__main__":` — what's it for? → run a block only on direct execution, not on import
14. Does `guidance: str` guarantee the content is one of your 4 categories? → no; type ≠ content quality. Use `Literal[...]` for that
15. `f"${x:,.0f}"` on 5000000.0 → ? → "$5,000,000"
