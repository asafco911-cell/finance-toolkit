# Python & Git — Study Reference (Chapters 1–2)

> A memorization sheet. Every concept has a minimal, runnable example.
> Rule of thumb: if you can predict the output *before* running it, you understand it.

---

## PART A — Terminal, Git & GitHub (Chapter 1)

### Environment check commands

| Command | Purpose | Expected output |
|---|---|---|
| `python --version` | Check Python is installed & on PATH | `Python 3.14.3` |
| `pip --version` | Check the package manager | `pip 25.3 from ...` |
| `git --version` | Check Git is installed | `git version 2.53.0` |

### One-time Git identity setup

```bash
git config --global user.name "Asaf Cohen"
git config --global user.email "asafco911@gmail.com"
```

Stored on disk (`~/.gitconfig`), **not** tied to any terminal session. Set once, persists forever.

### The core Git lifecycle (memorize this cold)

```bash
git clone <url>          # Download a repo from GitHub to your machine
cd <folder>              # Enter the project folder

git status               # "Where do I stand?" — run this constantly
git add .                # Stage ALL changed/new files
git commit -m "message"  # Save a snapshot locally, with a description
git push origin main     # Send local commits up to GitHub (the cloud)
git pull                 # Download others' commits FROM GitHub
```

**Mental model of the three states:**

```
Working files  --(git add)-->  Staging area  --(git commit)-->  Local repo  --(git push)-->  GitHub
```

### Two files every repository needs (once, at the repo root)

| File | Role | Why it matters |
|---|---|---|
| `README.md` | The "sign on the door" — what/why/how | First thing a recruiter reads, before any code |
| `.gitignore` | The "do-not-upload list" | Security (`.env` secrets) + cleanliness (`__pycache__`, `venv/`) |

`.gitignore` essentials:

```gitignore
__pycache__/     # Python cache junk
venv/            # virtual environments (huge, regenerable)
.vscode/         # personal IDE settings
.env             # SECRETS — API keys, passwords. NEVER upload.
.DS_Store        # OS metadata
```

### Running a Python file

```bash
python stock_screener.py   # runs the whole file
```

**Common Chapter-1 traps:**
- Save the file (with `.py`) **before** running, or you get `No such file or directory`.
- Check you're in the right folder (`cd`) before running.
- `>>>` in the terminal = you're inside the Python REPL. Type `exit()` to leave.

---

## PART B — Python Fundamentals (Chapter 2)

### 1. Variables

A named box holding a value. `=` means **"put in the box"**, not mathematical equality.

```python
price = 430.50
ticker = "MSFT"
```

### 2. Data types

| Type | Meaning | Example | How Python detects it |
|---|---|---|---|
| `int` | Whole number | `10` | no decimal point |
| `float` | Decimal number | `430.50` | has a decimal point |
| `str` | Text | `"MSFT"` | wrapped in quotes |
| `bool` | True / False | `True` | reserved keyword |

```python
shares = 10           # int
price = 430.50        # float
ticker = "MSFT"       # str
is_cheap = True       # bool

print(type(price))    # <class 'float'>  — check any variable's type live
```

**Key rule:** Python does **not** auto-convert types. `"Price: " + 430.50` → `TypeError`.
Convert explicitly with `str()`, `int()`, `float()`:

```python
price_text = "430.40"
price_num = float(price_text)   # now a real number you can compute with
```

Keep numbers as numbers for math; convert to text only for display.

### 3. f-strings (formatted output)

The `f` before the quotes enables `{}` placeholders. Inside `{}` is **live Python code**.

```python
price = 430.50
print(f"Price: {price}")              # Price: 430.5
print(f"Total: {price * 2}")          # Total: 861.0  — math inside braces
print(f"Ticker: {ticker.upper()}")    # calls a function inside braces
```

Without the `f`, braces are literal text: `print("Price: {price}")` → `Price: {price}`.

**Quote nesting:** inside `f"..."`, use single quotes for dict keys → `f"{stock['ticker']}"`.

### 4. Arithmetic operators

| Operator | Meaning | Example | Result |
|---|---|---|---|
| `+` | Add | `100 + 10` | `110` |
| `-` | Subtract | `100 - 10` | `90` |
| `*` | Multiply | `100 * 2` | `200` |
| `/` | Divide (always returns `float`) | `10 / 4` | `2.5` |
| `//` | Integer divide (rounds down) | `10 // 3` | `3` |
| `%` | Remainder (modulo) | `10 % 3` | `1` |

```python
print(10 / 3)    # 3.3333333333333335  (float)
print(10 // 3)   # 3                    (int)
```

### 5. Comparison operators (always return `bool`)

| Operator | Meaning | Example | Result |
|---|---|---|---|
| `>` | Greater than | `12 > 15` | `False` |
| `<` | Less than | `12 < 15` | `True` |
| `>=` | Greater or equal | `15 >= 15` | `True` |
| `<=` | Less or equal | `12 <= 15` | `True` |
| `==` | Equal to (a QUESTION) | `15 == 15` | `True` |
| `!=` | Not equal to | `12 != 15` | `True` |

**Critical:** `=` assigns ("put in box"); `==` compares ("are these equal?"). Never mix them.

### 6. Logical operators

| Operator | Meaning | Example | Result |
|---|---|---|---|
| `and` | Both must be True | `True and False` | `False` |
| `or` | At least one True | `True or False` | `True` |
| `not` | Flips the value | `not True` | `False` |

```python
pe = 12
price = 200
if pe < 15 and price < 300:
    print("Buy signal")
```

### 7. Conditionals: `if / elif / else`

Decision-making. Python checks top-to-bottom and **stops at the first True condition**.

```python
pe = 20

if pe < 15:
    print("Cheap")
elif pe < 30:
    print("Fair")
else:
    print("Expensive")
# Output: Fair
```

**Three non-negotiable rules:**
1. Each `if` / `elif` / `else` line ends with a colon `:`
2. The body must be **indented** (4 spaces). Indentation defines what's inside the block.
3. Order matters — first matching condition wins, the rest are skipped.

### 8. Loops: `for`

Repeat an action for every item in a collection.

```python
tickers = ["AAPL", "MSFT", "NVDA"]

for ticker in tickers:      # 'tickers' = whole list, 'ticker' = one item per pass
    print(ticker)
# AAPL / MSFT / NVDA
```

Convention: plural for the collection, singular for the loop variable.

**`range()`** — loop a fixed number of times (starts at 0, excludes the end):

```python
for i in range(5):
    print(i)        # 0 1 2 3 4  (five numbers, 0 through 4)
```

### 9. Loops: `while`

Repeat **as long as** a condition is True. Use when you don't know the count in advance.

```python
count = 0
while count < 3:
    print(count)
    count += 1       # MUST update, or infinite loop. Ctrl+C to break one.
# 0 1 2
```

### 10. Functions: `def` and `return`

A reusable recipe. Define once, call infinitely.

```python
def classify(pe):           # 'pe' is a parameter — a temp variable, NO quotes
    if pe < 15:
        return "Cheap"      # return HANDS BACK a value (unlike print)
    elif pe < 30:
        return "Fair"
    else:
        return "Expensive"

result = classify(45)       # call it; result = "Expensive"
print(f"NVDA is {classify(45)}")
```

**`return` vs `print`:**
- `return` → hands a value back you can store/reuse (`result = classify(10)`)
- `print` → only displays; the function gives back `None`

**Separation of concerns:** `classify` only knows `pe`. It has no idea what a ticker is.
The *loop* combines ticker + result. Each piece does one narrow job.

### 11. Data structure: list of dictionaries

```python
stocks = [
    {"ticker": "AAPL", "pe": 28},    # keys ALWAYS in quotes
    {"ticker": "NVDA", "pe": 45},
]

for stock in stocks:
    print(stock["ticker"])           # access value by key → "AAPL"
    print(stock["pe"])               # → 28
```

**Brackets cheat-sheet:**

| Symbol | Structure | Ordered? | Duplicates? |
|---|---|---|---|
| `[ ]` | **list** | yes | yes |
| `{ }` with `key: value` | **dictionary** | — | keys unique |
| `{ }` with bare values | **set** | NO | no |

For a stock watchlist, always use a `list` (`[ ]`) — order is preserved.

**Quotes rule (the big one):**
- Dictionary **key** → in quotes: `stock["pe"]`, `{"pe": 28}`
- Variable / parameter **name** → no quotes: `def classify(pe)`, `pe = 28`
- A value that IS text → in quotes: `"Cheap"`
- A value that IS a number → no quotes: `28`

### 12. Counter pattern (`+=`)

Count occurrences across a loop.

```python
cheap_count = 0                       # 1. INITIALIZE before the loop (once)

for stock in stocks:
    result = classify(stock["pe"])
    if result == "Cheap":
        cheap_count += 1              # 2. UPDATE inside the loop (per item)
                                      #    cheap_count += 1  ==  cheap_count = cheap_count + 1
print(f"Total cheap: {cheap_count}")  # 3. READ after the loop (once)
```

**Placement is everything:**
- Initialize (`= 0`) → **before** the loop (or it resets every pass)
- Update (`+= 1`) → **inside** the loop (indented)
- Print summary → **after** the loop (not indented — runs once at the end)

### Escape sequences (inside strings)

| Sequence | Meaning |
|---|---|
| `\n` | New line |
| `\t` | Tab |

Note: `\` is special. Writing `P\E` triggers a warning — you meant `/` (forward slash): `P/E`.

---

## The complete Chapter-2 project pattern (`stock_screener.py`)

This one script combines **every** concept above:

```python
# Data: list of dictionaries
stocks = [
    {"ticker": "AAPL", "pe": 28},
    {"ticker": "NVDA", "pe": 45},
    {"ticker": "KO",   "pe": 12},
]

# Function: define once
def classify(pe):
    if pe < 15:
        return "cheap"
    elif pe < 30:
        return "fair"
    else:
        return "expensive"

# Counters: initialize before loop
cheap_count = 0
fair_count = 0
expensive_count = 0

# Loop: process every stock
for stock in stocks:
    result = classify(stock["pe"])
    print(f"{stock['ticker']} is {result} with P/E of {stock['pe']}")

    if result == "cheap":
        cheap_count += 1
    elif result == "fair":
        fair_count += 1
    else:
        expensive_count += 1

# Summary: after loop, runs once
print(f"\nSummary: {cheap_count} cheap, {fair_count} fair, {expensive_count} expensive")
```

---

## 60-second self-test (cover the answers)

1. Difference between `=` and `==`? → assign vs. compare
2. What does `10 / 3` return vs `10 // 3`? → `3.333...` (float) vs `3` (int)
3. Why quotes on `"pe"` in a dict but not in `def classify(pe)`? → key (label) vs. parameter (variable name)
4. `return` vs `print` inside a function? → hands a value back vs. only displays
5. Where do you initialize a counter — inside or outside the loop? → outside (once)
6. What does `range(5)` produce? → `0 1 2 3 4` (starts at 0, excludes 5)
7. Which Git command shows your current state? → `git status`
8. What belongs in `.gitignore` and why? → secrets/junk/venv — security + cleanliness
