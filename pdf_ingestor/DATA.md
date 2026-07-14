# Source Document

**Company:** Uber Technologies, Inc. (NYSE: UBER)
**Filing:** Form 10-K, fiscal year 2025 (149 pages)
**Source:** SEC EDGAR — https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001543151&type=10-K

## Why the PDF is not in this repository

The filing is a large binary file and is **publicly available** from the SEC. Git is
not the right place for it (see `.gitignore`: `*.pdf`).

## To reproduce the pipeline from scratch

1. Download the 10-K from the link above.
2. Save it as `pdf_ingestor/report.pdf`.
3. Run:

       cd pdf_ingestor
       python pdf_ingestor.py     # PDF -> clean text + income_statement.csv
       python chunker.py          # text -> chunks.json (221 chunks)

4. Copy the resulting `chunks.json` to `rag_pipeline/chunks.json`.

**Note:** `rag_pipeline/chunks.json` is already committed, so the RAG system runs
out of the box **without** this step. This document exists so the ingestion stage
is fully reproducible.