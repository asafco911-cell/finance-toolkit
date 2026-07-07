# Python & Git — Study Reference (Chapter 3)

> Data structures, File I/O, JSON, error handling, modules, and clean code.
> Same rule as before: if you can predict the output *before* running it, you understand it.
> Companion to the Chapter 1–2 reference sheet.

---

## PART A — Data Structures in Depth

### 1. Lists — beyond the basics

```python
tickers = ["AAPL", "MSFT", "NVDA"]

print(tickers[0])       # "AAPL"  — index starts at 0, ALWAYS
print(tickers[-1])      # "NVDA"  — negative index counts from the end
print(len(tickers))     # 3       — number of items

tickers.append("KO")    # add to the END of the list
print("KO" in tickers)  # True    — membership check
print("XYZ" not in tickers)  # True
```

**`in` / `not in`** — checks if a value exists inside a collection. Returns `bool`.
This is the building block for duplicate-prevention (see Part D).

### 2. Dictionaries — beyond the basics

```python
stock = {"ticker": "AAPL", "pe": 28}

stock["price"] = 195.20        # add a new key
print(stock.keys())            # all keys
print(stock.values())          # all values
```

**The critical difference: `[key]` vs `.get(key)`**

| Access | Key exists | Key missing |
|---|---|---|
| `stock["pe"]` | returns value | **CRASHES** — `KeyError` |
| `stock.get("pe")` | returns value | returns `None` (no crash) |
| `stock.get("pe", 0)` | returns value | returns your default (`0`) |

Use `.get()` whenever data comes from the outside world (files, APIs) — fields may be missing.

### 3. "Empty" vs "zeros" — a subtle but important distinction

```python
results = []                                    # EMPTY list  — len() == 0
summary = {"cheap": 0, "fair": 0, "expensive": 0}  # FULL dict — 3 keys, values are 0
```

If a loop never runs (empty input), counters initialized *before* the loop still exist —
they just stay at 0. Code reading `summary["cheap"]` won't crash; it reports 0.
That's resilient design: initialize outside the loop, update inside, read after.

---

## PART B — File I/O (reading & writing files)

### Why it exists
Everything in a running program dies when the program ends. Files are how data **survives**
between runs. Write = save to disk. Read = load from disk.

### The one correct way to open files: `with`

```python
with open("notes.txt", "w") as file:
    file.write("First line\n")
# file closes automatically here — even if an error happened inside
```

`with` guarantees the file is closed properly. Never use bare `open()`/`close()` pairs.

### The three modes — memorize this table

| Mode | Meaning | If file missing | Danger |
|---|---|---|---|
| `"r"` | read only | **CRASHES** (`FileNotFoundError`) | none — never changes the file |
| `"w"` | write (wipe & start fresh) | creates it | **DELETES all existing content** |
| `"a"` | append (add to end) | creates it | adds again on EVERY run |

**Key behavioral insight (idempotency):**
- `"r"` is safe to run 100 times — nothing changes.
- `"a"` and `"w"` have side effects — each run changes the file. Know exactly when they run.
- Workflow: use `"a"`/`"w"` deliberately, once; comment it out or remove it after it did its job.

**⚠️ Real danger encountered:** `open("my_script.py", "w")` on the script you're editing
wipes it instantly. Never open a file for writing unless you're 100% sure of the filename.

### Files are just files
A file created by Python is a normal disk file. Notepad, VS Code, and Python all edit the
SAME file. Python reads whatever is currently saved — it doesn't matter who wrote it.
But remember: a `"w"` run will erase manual edits too.

---

## PART C — Working Directory (the bug that bit three times)

**The single most repeated error of this chapter. Internalize it.**

`open("stocks.json")` does NOT look next to your `.py` file.
It looks in the **Working Directory** — the folder your *terminal* is standing in.

```
Where the .py file lives   ≠   Where the terminal is standing
```

**Rules that prevent it:**

| Action | Correct location |
|---|---|
| `python main.py` | `cd` INTO the folder containing `main.py` first |
| Any `git` command | `cd` to the **repository ROOT** (e.g. `finance-toolkit`) |
| Checking where you are | read the prompt before `>`, or run `pwd` |

**Symptoms that mean "check your working directory":**
- `FileNotFoundError` on a file you can SEE in the Explorer
- `can't open file ... main.py: No such file or directory`
- Git showing weird `../` paths in `git status`
- A file you created appearing in the "wrong" folder

**Prefer `cd folder` + `python main.py` over the green Run button** in multi-file projects —
the Run button may execute from a stale working directory.

---

## PART D — JSON (structured data that survives)

### The problem JSON solves
`file.write(str(stocks))` saves TEXT that *looks* like a list — but reads back as a useless
string. JSON saves the STRUCTURE, so it comes back as a real list/dict.

### The four operations

```python
import json                              # required at the top, once

# WRITE structure → file
with open("stocks.json", "w") as file:
    json.dump(stocks, file, indent=4)    # indent=4 → human-readable formatting

# READ file → structure
with open("stocks.json", "r") as file:
    loaded = json.load(file)             # loaded is a REAL list/dict again

print(type(loaded))                      # <class 'list'> — not str!
```

**Memorize:** `dump` = save (dump it out). `load` = read (load it in).

### ⚠️ JSON + append ("a") = broken file

JSON is ONE complete structure (`[ ... ]`). Appending a second structure at the end
produces invalid JSON that `json.load()` cannot parse:

```
[{"ticker": "AAPL"}]{"ticker": "MSFT"}   ← two glued structures = corrupt
```

**The correct pattern — Read → Modify in memory → Write everything back:**

```python
with open("stocks.json", "r") as file:      # 1. READ what exists
    stocks = json.load(file)

stocks.append({"ticker": "MSFT", "pe": 35})  # 2. MODIFY in memory (list.append!)

with open("stocks.json", "w") as file:       # 3. WRITE it all back ("w", not "a"!)
    json.dump(stocks, file)
```

### Preventing duplicates before adding

```python
existing = []
for stock in stocks:
    existing.append(stock["ticker"])

if new_ticker not in existing:
    stocks.append({"ticker": new_ticker, "pe": new_pe})
```

### Removing duplicates that already exist (deduplication)

```python
seen = []
unique = []
for stock in stocks:
    if stock["ticker"] not in seen:
        seen.append(stock["ticker"])
        unique.append(stock)
# write `unique` back with "w"
```

---

## PART E — Exceptions: `try / except`

### Reading a Traceback (error message)

```
Traceback (most recent call last):
  File "...\main.py", line 3, in <module>     ← WHERE it happened
    with open("stocks.json", "r") as file:     ← the exact line
FileNotFoundError: [Errno 2] No such file...   ← WHAT type + human explanation
```

Read errors bottom-up: type first, then location. The terminal is telling you the answer.

### The safety-net pattern

```python
try:
    with open("stocks.json", "r") as file:
        return json.load(file)              # runs if everything works
except FileNotFoundError:
    print("File missing — starting fresh.")
    return []                                # runs ONLY on that specific error
```

- Exactly ONE of the two `return`s executes per call.
- The program **keeps running** instead of crashing — it handles the problem and moves on.
- A function that always returns something usable (full list or empty list) is resilient.

### Always catch SPECIFIC exceptions

```python
except:                        # ❌ BAD — swallows every error, hides your own bugs
except FileNotFoundError:      # ✅ GOOD — handles exactly what you planned for
except (FileNotFoundError, json.JSONDecodeError):   # ✅ multiple specific types
```

`json.JSONDecodeError` = file exists but its content is corrupt/not valid JSON.

---

## PART F — Modules & Imports (splitting code across files)

### Why
One giant file with mixed logic becomes unreadable (you experienced it). Each file gets
ONE clear job — same "separation of concerns" as functions, at file level.

### The pattern

**`storage.py`** — the specialist (defines tools, runs nothing):
```python
import json

def load_stocks():
    with open("stocks.json", "r") as file:
        return json.load(file)

def save_stocks(stocks):
    with open("stocks.json", "w") as file:
        json.dump(stocks, file)
```

**`main.py`** — the runner (imports tools, uses them):
```python
from storage import load_stocks, save_stocks

stocks = load_stocks()
stocks.append({"ticker": "MSFT", "pe": 35})
save_stocks(stocks)
```

**Rules:**
- `from storage import load_stocks` — filename WITHOUT `.py`
- Both files must be in the SAME folder (otherwise `ModuleNotFoundError`)
- You run `main.py`, never the module — a recipe book isn't a meal
- After importing, the functions work as if written locally

### Returning two values at once

```python
def analyze_portfolio(stocks):
    ...
    return results, summary          # returns BOTH

results, summary = analyze_portfolio(stocks)   # unpack in order
```

---

## PART G — OOP Basics (Classes) — concept level only

```python
class Stock:
    def __init__(self, ticker, pe):    # runs when creating an instance
        self.ticker = ticker            # self = "this specific object"
        self.pe = pe

    def classify(self):
        if self.pe < 15:
            return "Cheap"
        return "Expensive"

aapl = Stock("AAPL", 28)     # an INSTANCE of the Stock template
print(aapl.ticker)            # AAPL
print(aapl.classify())        # Expensive
```

A `class` = template bundling DATA (`ticker`, `pe`) + BEHAVIOR (`classify`) together,
instead of a separate dict + separate function. Each instance remembers its own data.
Depth comes later — the concept is enough for now.

---

## PART H — Clean & Secure Code

1. **Clear names** — `load_stocks`, not `f1`. Code is read far more than written.
2. **Style details matter** — `result = classify(x)` (spaces around `=`), `def classify(pe):`
   (no space before parenthesis), `/` not `\` in text (`P/E` — backslash is an escape char:
   `\n` newline, `\t` tab; `\E` triggers a SyntaxWarning).
3. **NEVER hardcode secrets** — API keys go in `.env` (already in your `.gitignore`),
   loaded with `python-dotenv`. Critical in a finance workplace.
4. **Clean up experiment layers** — commented-out trials are fine while learning, but final
   files contain only the final logic. Duplicate `import json` lines = a smell of leftover layers.
5. **Minimal Reproducible Example** — when debugging, isolate the problem in a tiny clean
   file instead of commenting out chunks of a big messy one.

---

## PART I — Git, deeper level

### `git add .` — the dot is NOT optional

```bash
git add          # ❌ "Nothing specified, nothing added" — silently does nothing
git add .        # ✅ stages everything from the current folder down
```

A missing dot cascades: empty staging → empty commit → "Everything up-to-date" push.
**Read Git's hints** — it literally told you: `hint: Maybe you wanted to say 'git add .'?`

### Run Git from the repository ROOT

`git add .` = "current folder **and below**". Run from a subfolder, it misses sibling files,
and `git status` shows confusing `../` paths. Always `cd` to the repo root (`finance-toolkit`)
before Git commands.

| Tool | Where to stand |
|---|---|
| `python main.py` | the script's own folder |
| `git` anything | the repository root |

### `.gitignore` is NOT retroactive

`.gitignore` only blocks files Git hasn't tracked yet. If a file slipped into tracking
(e.g. `__pycache__` grabbed by an early `git add .`), it keeps being committed forever
until you remove it from tracking:

```bash
git rm -r --cached __pycache__     # remove from Git tracking ONLY
git commit -m "Remove __pycache__ from tracking"
git push origin main
```

`--cached` = untrack but KEEP the file on disk. Without it, the file is deleted for real.

---

## The complete Chapter-3 project structure (`portfolio_analyzer/`)

```
portfolio_analyzer/
  ├── stocks.json      # input data (written by hand or by another program)
  ├── loader.py         # load_stocks() with try/except → never crashes
  ├── analysis.py        # classify() + analyze_portfolio() → returns results, summary
  ├── main.py             # imports both, prints, saves report.json (indent=4)
  └── report.json         # output artifact, created by the program
```

Data flows: `stocks.json` → `loader` → `analysis` → `main` → `report.json`.
Each file has one job. `main.py` reads like a story: load, analyze, print, save.

---

## 60-second self-test (cover the answers)

1. `stock["x"]` vs `stock.get("x")` when key missing? → crash (`KeyError`) vs `None`
2. Which file mode deletes existing content? → `"w"`
3. Which mode is safe to re-run endlessly, and why? → `"r"` — it has no side effects
4. Python says `FileNotFoundError` but you SEE the file in Explorer — first suspect? → Working Directory (`pwd`, then `cd`)
5. Why does appending (`"a"`) to a JSON file corrupt it? → JSON is one complete structure; a second glued structure is invalid
6. The correct pattern to add one record to a JSON file? → read (`load`) → modify in memory (`list.append`) → write all back (`"w"` + `dump`)
7. `json.dump` vs `json.load`? → dump = structure→file (save), load = file→structure (read)
8. Why `except FileNotFoundError:` and never bare `except:`? → bare except hides bugs you didn't plan for
9. In `from loader import load_stocks` — where must `loader.py` be? → same folder; note: no `.py` in the import
10. Which do you run — `main.py` or the module? → `main.py`; modules are recipe books
11. An empty-input run: `results` vs `summary`? → `results == []` (empty); `summary` has all 3 keys with value 0
12. `git add` did "nothing" silently — what's missing? → the dot: `git add .`
13. Where do you stand for Git commands vs for running scripts? → repo root for Git; script's folder for `python`
14. `__pycache__` keeps appearing in commits despite `.gitignore` — fix? → `git rm -r --cached __pycache__` (ignore isn't retroactive)
15. Where do API keys live? → `.env` (gitignored), never in code
