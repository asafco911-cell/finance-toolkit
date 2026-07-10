# PDF Processing & Document Ingestion — Study Reference (Chapter 6)

> Extracting clean data from financial PDFs: text, tables, OCR, and chunking —
> the foundation of "garbage in, garbage out" for any downstream analysis.
> Same rule: if you can predict the output *before* running it, you understand it.
> Companion to the Chapter 1–5 reference sheets.

---

## PART A — Why PDF parsing is hard

A PDF is NOT structured like Word or HTML. It's built for PRINTING — essentially "pictures of
letters placed at exact coordinates on a page." The computer doesn't know that 3 words are a
"heading" vs a "paragraph"; it only knows "letter X sits at coordinate (120, 450)." Libraries
like `pdfplumber` do the detective work of reconstructing logical structure from raw positions.

### Text-based vs Scanned PDF
| Type | Test | What extract_text() returns |
|---|---|---|
| **Text-based** | you CAN select/copy text | real text |
| **Scanned** (image) | you CANNOT select text | `None` or `""` (empty — NOT an error) |

An empty string with no error = the "fingerprint" of a scanned PDF: the file opened fine, but
there's no text layer to extract. That's when you'd need OCR, not more `pdfplumber` attempts.

### OCR (Optical Character Recognition)
Reads text from an image (like your phone reading a receipt). Never perfect — may misread
`0`→`O` or `1`→`l`, which can silently corrupt financial numbers. Always verify OCR on critical
data. Requires installing Tesseract as separate software (not just a Python library).

---

## PART B — pdfplumber basics

```python
import pdfplumber

with pdfplumber.open("report.pdf") as pdf:      # same 'with' pattern as open() (Ch.3)
    num_pages = len(pdf.pages)                    # pdf.pages is a LIST of page objects
    first_page = pdf.pages[0]                      # index 0 = first page (lists start at 0!)
    text = first_page.extract_text()              # returns the page's text, or None if empty
    print(text[:500])                              # slicing: first 500 chars only (Ch.6 new)
```

### Slicing (new this chapter)
```python
text[:500]    # from start to index 500
text[6:]      # from index 6 to the end
text[6:11]    # from index 6 up to (not including) 11
my_list[:3]   # works on lists too — first 3 items
```

### Extracting all pages (with the accumulator pattern)
```python
all_text = ""                                     # initialize the "notebook" before the loop
for page_number, page in enumerate(pdf.pages):    # enumerate gives index AND item
    page_text = page.extract_text()
    if page_text:                                 # skip empty/scanned pages, don't crash
        all_text += page_text + "\n"
    else:
        print(f"Page {page_number + 1}: no text.")  # +1 because humans count from 1, Python from 0
```

**`enumerate(list)`** — gives you both the index (0,1,2…) and the item in each loop pass.
Without it you'd have the page but not its number.

---

## PART C — Table extraction (the real challenge)

Plain text is easy ("take words in order"). Tables need STRUCTURE preserved — which number
belongs to which row and column. `pdfplumber` has a dedicated `extract_tables()` for this,
separate from `extract_text()`.

### The problem: no visible column lines
Financial tables often align columns with WHITESPACE, not vertical lines. The default
`extract_tables()` looks for lines to find column boundaries — so it returns `0` tables on a
table that clearly exists to your eye.

### table_settings — adapting the detection strategy
```python
table_settings = {
    "vertical_strategy": "text",      # find columns by text alignment, not lines
    "horizontal_strategy": "lines",   # find rows by the horizontal lines that DO exist
}
tables = page.extract_tables(table_settings=table_settings)
```
Options per axis: `"lines"` (needs real line objects), `"text"` (infers from text position).
Each table has its own visual "signature" — match the strategy to the specific table.

### The limit of classic parsing
`"vertical_strategy": "text"` treats EVERY small gap as a column boundary — so it splits even
single words in half (`"exclusive"` → `"exclusiv"` + `"e"`) on text with uneven spacing. It
works on cleanly-spaced numbers but breaks on prose. This is where LLMs win (Part E).

### Writing a table to CSV
```python
import csv
with open("output/income_statement.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerows(table)   # 'rows' plural — writes a list-of-lists as rows
```
- `newline=""` — ALWAYS with csv.writer (prevents blank lines between rows on Windows)
- `writerows` expects a list of lists (each inner list = one row)
- **Python creates files, NOT folders** — the `output/` folder must exist first (make it manually)

---

## PART D — Finding the right page automatically (don't guess the index)

The printed page number (e.g. "73" at the bottom) does NOT reliably equal the `pdf.pages`
index — cover pages, tables of contents, and unnumbered pages shift the count. And a heading
like "Income Statement" may appear twice (once in the summary, once in the full statements).
So don't hardcode `pdf.pages[72]` — SEARCH for it and VERIFY:

```python
target_index = None
for page_number, page in enumerate(pdf.pages):
    text = page.extract_text()
    if text and "CONSOLIDATED STATEMENTS OF OPERATIONS" in text.upper():
        target_index = page_number
        break                                     # stop at the first match
if target_index is not None:
    target_page = pdf.pages[target_index]
    print(target_page.extract_text()[:300])       # VERIFY before proceeding
```
- `.upper()` before comparing — makes the match case-insensitive
- `break` — stop looping once found
- Print & verify first — don't waste effort extracting from the wrong page again

---

## PART E — LLM-assisted extraction (classic parser + LLM = best result)

When the classic parser mangles a complex table, send the RAW TEXT (already extracted) to an
LLM and let it structure the data — reusing the exact Ch.5 stack (Anthropic + JSON + fences).

### Slicing out just the relevant text (save tokens)
```python
start = full_text.find("CONSOLIDATED STATEMENTS OF OPERATIONS")  # index where it begins, or -1
income_text = full_text[start:start + 3000]                       # a 3000-char window, not all 650k
```
`.find(substring)` returns the starting index (or `-1` if absent). Combined with slicing, this
cuts just the relevant section from a huge document — no need to send the whole 10-K to the API.

### Then: same LLM + JSON pattern as Ch.5
```python
response = client.messages.create(model="claude-sonnet-4-5", max_tokens=1500,
    system="Extract the income statement as a JSON array... ONLY valid JSON, no fences.",
    messages=[{"role": "user", "content": income_text}])
raw = response.content[0].text.strip()
if raw.startswith("```"):                          # strip markdown fences (Ch.5 pattern)
    raw = raw.split("```")[1]
    if raw.startswith("json"): raw = raw[4:]
    raw = raw.strip()
parsed = json.loads(raw)
```

**The lesson (exactly what the course intended):** combining a classic parser (to FIND the
page / extract raw text) with an LLM (to INTERPRET complex tables) beats either method alone.
You experienced the classic parser failing, then solved it with an LLM.

---

## PART F — Chunking (preparing for RAG, Chapter 7)

A 10-K is hundreds of pages — too big to send to an LLM at once (token limits + cost). Chunking
cuts it into small, overlapping pieces so you can later retrieve only the relevant one.

```python
def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()                          # split into a list of words (by any whitespace)
    chunks = []
    start = 0
    while start < len(words):
        chunk_words = words[start:start + chunk_size]   # slice out chunk_size words
        chunks.append(" ".join(chunk_words))             # join words back into a string
        start += chunk_size - overlap                     # advance by 450, not 500 → 50-word overlap
    return chunks
```

### Two new string tools
- **`text.split()`** — string → list of words (splits on any whitespace)
- **`" ".join(words)`** — list of words → string, joined with a space (the inverse of split)

### Why overlap matters
Without overlap, an important sentence could be cut exactly at a chunk boundary, and neither
half makes sense alone. Overlap means each new chunk STARTS ~50 words before the previous one
ended — a small deliberate duplication that preserves continuity across boundaries. Advancing
`start` by `chunk_size - overlap` (450) instead of `chunk_size` (500) creates that overlap.

---

## PART G — Git housekeeping: ignoring large source files

Large binary source files (the 149-page PDF) don't belong in the repo — keep the code and the
OUTPUTS (CSV/JSON), not the heavy source.

```gitignore
# PDF source files (large, not needed in repo)
*.pdf
```
- `*.pdf` — a wildcard: ANY file ending in `.pdf`, in any folder (vs `.env` = one exact name)
- Verify before committing: `git add pdf_ingestor/` then `git status` — confirm `report.pdf`
  is NOT in the staged list.

---

## The complete Chapter-6 project structure (`pdf_ingestor/`)

```
pdf_ingestor/
  ├── report.pdf                       # source 10-K (gitignored — not uploaded)
  ├── pdf_ingestor.py                   # full text extraction + auto page-search + table attempt
  ├── income_statement_llm.py            # the fix: Claude extracts the table from raw text
  ├── chunker.py                          # splits full text into ~500-word overlapping chunks
  ├── output_full_text.txt                # all 650k chars extracted from the PDF
  └── output/
        ├── income_statement.csv          # classic parser result (broken — kept for comparison)
        ├── income_statement_llm.json      # LLM result (clean, structured)
        └── chunks.json                      # 221 chunks, ready for RAG (Ch.7)
```

Pipeline: PDF → extract all text → auto-find the income-statement page → try classic table
extraction (fails on prose) → fall back to LLM extraction from raw text (works) → chunk the
full text for retrieval. Garbage in, garbage out: clean extraction is the foundation of
everything downstream.

---

## 60-second self-test (cover the answers)

1. Why is a PDF harder to parse than HTML? → it stores letter positions, not logical structure
2. `extract_text()` returns `""` with no error — what does that mean? → scanned/image PDF, no text layer (needs OCR)
3. `pdf.pages[0]` — which page, and why the 0? → the first page; lists index from 0
4. What does `enumerate()` give you? → both the index and the item in each loop pass
5. Why print `page_number + 1`? → humans count pages from 1, Python indexes from 0
6. `extract_text()` vs `extract_tables()` — the difference? → text returns one string; tables preserve row/column structure
7. Why did `extract_tables()` find 0 tables on a table that clearly exists? → no vertical LINES; default strategy needs them → use `vertical_strategy: "text"`
8. Why can't you trust "printed page 73 = index 72"? → cover/TOC/unnumbered pages shift the count; headings may repeat
9. Better approach than guessing the index? → search page text for the heading, then verify with `[:300]`
10. When does an LLM beat the classic parser, and how do you combine them? → on messy prose tables; parser finds page/raw text, LLM structures it
11. `full_text.find("X")` returns what? → the starting index of X, or -1 if absent
12. Why slice `full_text[start:start+3000]` before sending to the API? → send only the relevant section, saving tokens
13. `text.split()` vs `" ".join(list)`? → string→list of words vs list of words→string (inverses)
14. Why overlap between chunks? → so sentences cut at a boundary aren't lost; preserves continuity
15. Why advance `start` by `chunk_size - overlap`? → that gap (450 vs 500) is exactly what creates the 50-word overlap
16. `*.pdf` in `.gitignore` vs `.env` — the difference? → wildcard (any .pdf anywhere) vs one exact filename
17. `csv.writer` needs which two open() arguments? → `newline=""` and `encoding="utf-8"`
18. Does Python create missing folders automatically? → no — it creates files, but the folder must already exist
