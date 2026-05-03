# Researcher Assistant

A fully-local, LLM-maintained research-paper wiki — designed for one researcher
working through a fast-moving literature (autonomous-driving papers in the
seed corpus, but the architecture generalizes).

Inspired by Andrej Karpathy's
["LLM wiki" idea](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f):
the human supplies raw inputs (PDFs, arXiv links, search queries); the LLM
distills them into structured Markdown notes; a deterministic pass indexes
those notes into a navigable wiki; and a Streamlit UI lets you browse, search,
compare, annotate, and use the wiki to suggest upgrades to your own codebase.

The whole system runs locally. The only network calls are (a) optional
Anthropic API for batch / API-driven distillation and (b) optional Claude Code
CLI for skill-driven distillation. The default flow is **manual via Claude
Code reading the skills**, which keeps spend low and curation human.

---

## Table of contents

- [Why this exists](#why-this-exists)
- [Architecture at a glance](#architecture-at-a-glance)
- [Install](#install)
- [Quickstart](#quickstart)
- [Skills](#skills)
- [UI tour (7 pages)](#ui-tour-7-pages)
- [CLI reference](#cli-reference)
- [Project layout](#project-layout)
- [Status & tests](#status--tests)
- [Design history](#design-history)

---

## Why this exists

Reading 60+ recent papers on a fast-moving topic is hard:

1. **Distillation friction** — every paper takes 30–60 minutes to digest into
   reusable notes; you stop doing it after the first few.
2. **No cross-paper structure** — your notes file gets bigger but doesn't get
   more navigable; you can't easily find "all VLA-style planners that use a
   classical fallback" or "which 2024 papers use trajectory anchors".
3. **No connection to your code** — when you go to upgrade your own driving
   stack, the literature you've read isn't a queryable index of architectural
   options.

This project is an opinionated answer to those three problems:

1. The **`paper-distillation` skill** turns each PDF into a strictly-
   structured Markdown distillation (front-matter metadata + sections in fixed
   order: Keywords / TL;DR / Problem / Innovation / Architecture / Benchmark /
   Limitations).
2. The **`wiki-generation` skill** plus a deterministic generator turn a folder
   of distillations into a coherent wiki: master pipe-table, per-category
   pages with full architecture sections embedded, an
   architectures-by-tag-cluster cross-reference, and an LLM-curated
   `taxonomy.md`.
3. The **`codebase-analyzer` skill** walks a target codebase, identifies the
   methods it currently uses, maps them onto the wiki's architecture-tag
   clusters, and proposes upgrades citing specific papers from the corpus.

The Streamlit UI is the convenience layer on top: search, browse, compare,
annotate, run analyses, monitor coverage.

## Architecture at a glance

```
PDF / arXiv URL                          (the human supplies these)
   │
   │  paper-distillation skill (manual via Claude Code)   OR
   │  python cli.py distill-run                          (API)
   ▼
doc/distilled/<category>/<stem>.md       (committed; the source of truth)
   │
   │  python cli.py wiki-from-distilled  (deterministic, no LLM call)
   │  +  wiki-generation skill           (editorial layer — taxonomy &
   │                                      narrative intros & cluster prose)
   ▼
data/wiki/                               (gitignored; regenerable)
├── index.md                             one-line-per-paper pipe-table
├── taxonomy.md                          LLM-authored category descriptions
├── architectures.md                     8-cluster cross-reference
├── categories/<cat>.md                  full ## Model Architecture sections
└── pending.md                           coverage-gap snapshot

   │                                                         ▲
   ▼                                                         │
Streamlit UI                                  Browse / search / compare / annotate
(7 pages, see UI tour)                        Run codebase-analyzer against your repo
```

Five well-bounded Python modules under `lib/` keep the concerns separate:

| Module | Responsibility |
|---|---|
| `lib.llm` | Single `LLMClient` Protocol; backends: `FakeLLMClient` (test), `AnthropicClient`, `ClaudeCodeClient` (subprocess). |
| `lib.ingestion` | PDF → text → LLM-summarized notes. (Plan-1 ingestion path.) |
| `lib.distillation` | API-driven distillation in SKILL.md format + sync-diff between PDFs and distilled MDs. |
| `lib.indexing` | Wiki generation from distilled MDs + deterministic regen. |
| `lib.search` | BM25 content search across wiki + distilled MDs. |
| `lib.codebase` | Walk a target codebase, bundle strategic files, drive `codebase-analyzer` skill. |
| `lib.notes` | File-backed personal annotations, mirror layout under `doc/notes/`. |

Tests are hermetic — no live network in unit tests; `FakeLLMClient` everywhere.

## Install

Either conda or pip works.

**Conda (recommended; matches CI):**

```bash
conda env create -f environment.yml
conda activate researcher_assistant
```

**Pip / venv:**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Optional — set your Anthropic API key:**

```bash
cp .env.example .env
# then edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

Without an API key, the manual distillation flow (Claude Code + the
`paper-distillation` skill) and all read-only / deterministic features
still work end-to-end. The API key is only needed for the API-driven
distillation runner and the API-backed Codebase Analyzer page.

## Quickstart

```bash
# 1) Drop a PDF into a category
mkdir -p doc/papers/vla
cp ~/Downloads/drivevlm.pdf doc/papers/vla/drivevlm-2024.pdf

# 2) Distill it (one of two paths)

# 2a) Manual via Claude Code:
#     Open Claude Code in this repo; tell it:
#     "use skills/paper-distillation/SKILL.md to distill
#      doc/papers/vla/drivevlm-2024.pdf"
#     The skill writes doc/distilled/vla/drivevlm-2024.md

# 2b) Or API-driven (needs ANTHROPIC_API_KEY):
python cli.py distill-run --only vla/drivevlm-2024

# 3) Generate the wiki
python cli.py wiki-from-distilled

# 4) Run the UI
streamlit run ui/Home.py
# open http://localhost:8501
```

## Skills

Three reusable skills under `skills/`. Each is a self-contained `SKILL.md`
that an LLM (Claude Code or any model that ingests SKILL.md-style guidance)
can read and apply.

| Skill | What it does |
|---|---|
| [`paper-distillation`](skills/paper-distillation/SKILL.md) | Reads a PDF and produces a strictly-structured distillation Markdown — YAML front-matter (paper_id, title, authors, year, venue, arxiv_id, primary_category, keywords, one_line_summary, …) + body sections in fixed order. |
| [`wiki-generation`](skills/wiki-generation/SKILL.md) | Generates / refreshes / maintains the wiki from distillations. Modes: full rebuild, incremental add, incremental remove, taxonomy rebalance. Co-evolves with the deterministic generator (`lib.indexing.from_distilled`). |
| [`codebase-analyzer`](skills/codebase-analyzer/SKILL.md) | Given a path to a codebase, walks it selectively, identifies the methods in use, maps them onto the wiki's architecture-tag clusters, and proposes upgrades citing specific paper_ids from the corpus. Output: `<codebase>/UPGRADE_PROPOSALS.md`. |

The skills and the deterministic Python code share heuristics (e.g.
architecture-pattern tags) so a manual application of a skill produces
output compatible with the deterministic flow.

## UI tour (7 pages)

```
streamlit run ui/Home.py
```

| Page | What it gives you |
|---|---|
| **Home** | Sync-status overview + corpus stats: per-year / per-category / per-tag bar charts, year × category and tag × category coverage matrices, most-architecturally-rich-papers table. |
| **Wiki Browser** | BM25 content search across wiki + distillations (kebab-aware tokenizer, ranked snippets). Grouped browse with filename filter. **Notes mode** for personal annotations saved under `doc/notes/`. |
| **Distillation Manager** | Three tabs: Missing (run API distillation per-paper with progress), Orphans (delete with type-`delete`-to-confirm gate), In sync (dataframe). |
| **Architecture Explorer** | Faceted view by inferred architecture tag. Multi-select tags + AND/OR combine + category filter + sort options. Each match expands to the full `## Model Architecture` section verbatim. |
| **Codebase Analyzer** | Path input + backend selector + Preview-bundle button (cheap) + Run-analysis button. Reports save to `data/codebase_analyses/<repo>/<timestamp>.md` and a dropdown lets you revisit past runs. |
| **Compare** | Side-by-side architecture / benchmark / TL;DR / innovation / limitations of 2-3 selected papers, with optional shared-keyword highlighting throughout. |
| **Wiki Maintenance** | Drift indicator (distillations vs indexed papers), Regenerate-wiki button (deterministic, no LLM), Snapshot-pending.md button, copy-pasteable editorial-layer prompt for the `wiki-generation` skill. |

## CLI reference

```
python cli.py ingest <pdf>                       # original Plan-1 ingest path (LLM summarize + meta.json)
python cli.py query "..."                        # two-pass query against the wiki
python cli.py rebuild-index                      # regenerate wiki from papers/*/meta.json (Plan-1 path)

python cli.py wiki-from-distilled                # NEW: regenerate wiki from doc/distilled/ (no LLM)

python cli.py distill-check                      # diff doc/papers/ ↔ doc/distilled/
python cli.py distill-run [--only cat/stem]      # API-driven distillation for missing PDFs
python cli.py distill-clean [--yes]              # remove orphan distillations (dry-run by default)

python cli.py search-index [--rebuild]           # build/refresh the BM25 search index
python cli.py search "<query>" [--k N]           # ranked content search

python cli.py --backend {anthropic,claude_code} <subcommand>
```

The CLI mirrors the UI's read/write surfaces so the system is fully usable
headless or in a terminal-only environment.

## Project layout

```
researcher_assistant/
├── README.md                    you are here
├── requirements.txt             pip-installable lock-file (mirror of environment.yml's pip section)
├── environment.yml              conda env (recommended)
├── pyproject.toml               packaging + pytest config
├── .env.example                 template for ANTHROPIC_API_KEY
├── .gitignore
│
├── cli.py                       single argparse entrypoint
│
├── config/
│   └── default.yaml             default model, taxonomy, ingest budget; override via config/local.yaml
│
├── lib/                         all the library code (~1.5k LOC)
│   ├── llm/                     LLMClient Protocol + 3 backends
│   ├── ingestion/               Plan-1 PDF ingestion path
│   ├── distillation/            sync diff + API-driven distillation
│   ├── indexing/                wiki generation (deterministic)
│   ├── query/                   two-pass query (Plan-1)
│   ├── search/                  BM25 content search
│   ├── codebase/                codebase-analyzer runner
│   ├── notes/                   personal-annotations file store
│   ├── config.py                YAML config loader
│   ├── models.py                pydantic schemas
│   ├── pipeline.py              ingest+index façade (Plan-1)
│   └── storage.py               PaperStorage paths + paper_id allocation
│
├── ui/                          Streamlit multi-page app
│   ├── Home.py                  landing + corpus stats dashboard
│   └── pages/
│       ├── 1_Wiki_Browser.py
│       ├── 2_Distillation_Manager.py
│       ├── 3_Architecture_Explorer.py
│       ├── 4_Codebase_Analyzer.py
│       ├── 5_Compare.py
│       └── 6_Wiki_Maintenance.py
│
├── skills/                      LLM-readable skill specifications
│   ├── paper-distillation/SKILL.md
│   ├── wiki-generation/SKILL.md
│   └── codebase-analyzer/SKILL.md
│
├── tests/                       hermetic test suite (105 tests, <1s)
│
├── docs/
│   ├── smoke-test.md            manual acceptance procedure
│   └── superpowers/
│       ├── specs/               original design doc
│       └── plans/               implementation plan (19 TDD tasks)
│
└── doc/
    ├── papers/                  PDFs (gitignored — researcher's own corpus)
    ├── distilled/               distilled MDs (committed; the source of truth)
    └── notes/                   personal annotations (committable)
```

`data/` is created on demand and **gitignored** — it holds the regenerable
wiki, the search index, and codebase analysis reports.

## Status & tests

```bash
conda activate researcher_assistant
pytest               # 105 tests, all passing in <1s, no live network calls
```

The library is hermetic: every test uses `FakeLLMClient` or mocks
`subprocess.run` / `Anthropic`. You can develop offline. The seed corpus
under `doc/distilled/` ships with the repo so the wiki generator and UI
work out of the box.

## Design history

The `docs/superpowers/` tree captures the full design / implementation
history:

- [`docs/superpowers/specs/2026-05-02-personal-library-llm-wiki-design.md`](docs/superpowers/specs/2026-05-02-personal-library-llm-wiki-design.md)
  — original design (12 sections; architecture, on-disk layout, data
  flows, open items).
- [`docs/superpowers/plans/2026-05-02-personal-library-core.md`](docs/superpowers/plans/2026-05-02-personal-library-core.md)
  — 19-task TDD implementation plan that produced the original Plan-1 core.
- [`docs/smoke-test.md`](docs/smoke-test.md) — manual end-to-end smoke
  test for an API-keyed install.

Subsequent commits added: paper download tooling, the three skills, the
deterministic wiki generator, BM25 search, and the seven-page Streamlit
UI. See `git log --oneline` for the full chronology.

## Acknowledgements

- Andrej Karpathy's
  [LLM wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
  for the core idea.
- Each paper in the seed corpus, properly cited in its distilled MD's
  front-matter.
