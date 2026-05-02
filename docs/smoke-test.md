# Smoke Test — Plan 1 Acceptance

Run after all unit tests pass. Requires `ANTHROPIC_API_KEY` in `.env`.

## Setup
```bash
conda activate personal_library
cp .env.example .env  # then add real key
```

## 1. Ingest a real paper
Download any 1-page or short autonomous-driving paper PDF (e.g. an
arXiv abstract printed to PDF). Then:

```bash
python cli.py ingest path/to/paper.pdf
```

Expected:
- prints `ingested 2024-<slug>` (or similar)
- `data/papers/2024-<slug>/` contains source.pdf, full.md, notes.md, meta.json
- `data/wiki/index.md` has a row for the paper
- `data/wiki/categories/<category>.md` mentions the paper

## 2. Query the wiki
```bash
python cli.py query "summarize what's in my library"
```

Expected:
- prints a paragraph mentioning the paper
- prints `Cited: 2024-<slug>` line

## 3. Disaster recovery
```bash
echo "CORRUPT" > data/wiki/index.md
python cli.py rebuild-index
```

Expected:
- prints `rebuilt wiki from N papers`
- `data/wiki/index.md` is restored

## 4. Idempotent ingestion
Re-run step 1 with the same PDF.
Expected: prints `already ingested as <id>`; no LLM call made.
