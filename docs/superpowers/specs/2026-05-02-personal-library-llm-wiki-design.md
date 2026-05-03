# Personal Library — LLM Wiki Design

**Date:** 2026-05-02
**Status:** Draft, pending user approval
**Inspiration:** Karpathy, "LLM wiki" — https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## 1. Problem & Goal

Build a fully-local personal research library for autonomous-driving papers (focus: VLA, diffusion decoder/policy, world models, end-to-end planning, perception, datasets — papers from 2024/2025/2026).

The library is built and maintained by an LLM and consumed by an LLM. The human's job is only to:
- Provide raw data sources (PDFs, arXiv IDs, web pages, search queries),
- Ask questions through a chat UI.

The LLM's job is to:
- Read each new source once,
- Compress it into per-paper notes and one-line index entries,
- Maintain a navigable wiki of index files,
- Answer questions by routing through those index files (two-pass: route, then read).

This is **not** a RAG system. There is no vector DB, no embeddings. Routing is done by the LLM reading compressed text index files directly — this is what makes it a *wiki* rather than a vector store.

## 2. Scope

### In scope (v1)
- Ingest PDFs (upload), arXiv URLs/IDs, generic web pages.
- Scheduled arXiv keyword search via arXiv API.
- LLM-assisted paper discovery via a search API (e.g., Semantic Scholar API + a general web search API like Tavily/Brave/Exa — exact provider chosen during implementation).
- PyMuPDF for PDF text extraction.
- Per-paper artifacts: original PDF, parsed full text, LLM-authored deep notes (~300–500 words), structured metadata.
- Hybrid taxonomy: seed categories specified up front; LLM may add new categories during rebalance.
- Two-pass query: LLM reads index files to pick relevant papers, then LLM reads those papers' deep notes to answer.
- Pluggable LLM client interface, with two backends wired up:
  - `AnthropicClient` — direct Anthropic API.
  - `ClaudeCodeClient` — invokes Claude Code as a subprocess, capable of using skills.
- Streamlit UI with chat, ingest, browse-wiki, and rebalance surfaces.
- Manual-only rebalance (UI button + CLI command).
- All-local file system. No databases, no cloud storage.

### Out of scope (v1, deferred)
- Vector embeddings / FAISS fallback (revisit when corpus exceeds ~500 papers).
- Multi-user, auth, or sharing.
- Automatic rebalance triggers.
- Cross-paper synthesis beyond what fits in a single second-pass call.
- Mobile UI / hosted deployment.
- Citation graph parsing (we use arXiv metadata as-is).

## 3. Architecture

Five well-bounded units. They communicate only through (a) the file system layout in §4 and (b) a small Python interface for the LLM client.

```
┌───────────────────────────────────────────────────────────────┐
│                    Streamlit UI (ui/)                          │
│   chat panel │ ingest panel │ wiki browser │ rebalance         │
└──────────┬────────────────────────────────────────────────────┘
           │  (in-process Python calls)
           ▼
┌───────────────────────────────────────────────────────────────┐
│                    Core Library (lib/)                         │
│                                                                │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│   │  ingestion/  │  │  indexing/   │  │     query/       │    │
│   │              │  │              │  │                  │    │
│   │ fetchers:    │  │ writes       │  │ 2-pass routing:  │    │
│   │ - upload     │  │ wiki/*.md    │  │  1) read index,  │    │
│   │ - arxiv      │  │ from         │  │     pick papers  │    │
│   │ - web        │  │ papers/*/    │  │  2) read notes,  │    │
│   │ - search API │  │ notes.md     │  │     answer       │    │
│   │              │  │              │  │                  │    │
│   │ pdf parser:  │  │ rebalance    │  │                  │    │
│   │ PyMuPDF      │  │              │  │                  │    │
│   └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘    │
│          │                 │                    │              │
│          ▼                 ▼                    ▼              │
│   ┌─────────────────────────────────────────────────────┐     │
│   │            llm/  (LLMClient interface)              │     │
│   │  AnthropicClient │ ClaudeCodeClient │ (future...)   │     │
│   └─────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   Local FS only  │
                    │  papers/, wiki/  │
                    └──────────────────┘
```

### Module responsibilities

- **`ingestion/`** — Turns a source (file path / URL / arXiv ID / search query) into a populated `papers/<id>/` directory. Does NOT touch `wiki/`.
- **`indexing/`** — Reads `papers/*/notes.md` and `papers/*/meta.json`; writes/updates `wiki/index.md` and `wiki/categories/*.md`. Provides `rebalance()`. Does NOT fetch or parse.
- **`query/`** — Reads `wiki/` and `papers/`; writes nothing. Runs the two-pass routing.
- **`llm/`** — The only module that talks to an LLM. Everything else calls `client.complete(prompt, **kwargs)`.
- **`ui/`** — Streamlit app that calls into `lib/` functions. Contains no domain logic.

### Why these boundaries
- Swap UI without touching wiki logic.
- Swap LLM without touching ingestion.
- Add a new fetcher = drop a single file in `ingestion/fetchers/`.
- Each unit testable in isolation with fixtures (sample PDF, sample notes.md, sample wiki state).

## 4. On-Disk Layout

Everything lives under the repo root. No external storage.

```
personal_library/
├── data/                          # all user data, gitignored
│   ├── papers/
│   │   └── <paper_id>/
│   │       ├── source.pdf         # original (or original.html for web)
│   │       ├── full.md            # PyMuPDF-extracted text, lightly cleaned
│   │       ├── notes.md           # LLM-authored deep notes (300–500 words)
│   │       └── meta.json          # title, authors, year, arxiv_id, url,
│   │                              # keywords[], primary_category,
│   │                              # secondary_categories[], ingested_at,
│   │                              # source_type, hash
│   └── wiki/
│       ├── index.md               # master index: one line per paper
│       ├── categories/
│       │   ├── vla.md
│       │   ├── diffusion_decoder.md
│       │   ├── world_model.md
│       │   ├── e2e_planning.md
│       │   ├── perception.md
│       │   ├── datasets.md
│       │   └── misc.md            # uncategorized / catch-all
│       └── taxonomy.md            # current category list + descriptions
│                                  # (LLM-edited during rebalance)
├── lib/                           # python package
│   ├── ingestion/
│   ├── indexing/
│   ├── query/
│   └── llm/
├── ui/
│   └── app.py                     # streamlit entrypoint
├── cli.py                         # CLI for ingest/rebalance/query
├── config/
│   └── default.yaml               # paths, default LLM, seed taxonomy, etc.
├── tests/
├── docs/superpowers/specs/        # this design doc + future specs
├── environment.yml                # conda env definition
├── pyproject.toml
└── README.md
```

### `paper_id` format
`<year>-<arxiv_id_or_slug>`, e.g. `2024-2406.12345` or `2025-waymo-blogpost-vla`. Stable, human-readable, sortable.

### `wiki/index.md` line format
One line per paper, pipe-delimited:
```
| <paper_id> | <year> | <title> | <primary_category> | <one-line-summary> | <kw1, kw2, kw3> |
```

### `wiki/categories/<cat>.md` format
Markdown with a short category description at the top, then a list of papers in that category, each with the one-line summary and a relative link to `data/papers/<paper_id>/notes.md`.

### `wiki/taxonomy.md`
Authoritative list of current categories. Edited by the LLM during rebalance. Includes a 1–2 sentence description of each category to ground future categorization.

## 5. Data Flows

### 5.1 Ingestion
1. User submits a source via UI or CLI.
2. Appropriate fetcher resolves it to (raw bytes, source-type metadata).
   - `upload`: file already on disk.
   - `arxiv`: arXiv API call → PDF download.
   - `web`: HTTP fetch → readability cleanup → HTML/markdown.
   - `search`: search API → list of candidate URLs/arXiv IDs → user picks (UI) or auto-take top-N (cron).
3. Compute content hash; if a paper with that hash already exists, abort with "already ingested".
4. Allocate `paper_id`, create `papers/<paper_id>/` directory.
5. Save `source.pdf` (or `source.html`).
6. Run PyMuPDF → write `full.md`.
7. LLM call #1: read `full.md` + current `wiki/taxonomy.md` → produce `notes.md` + `meta.json` (incl. one-line summary, keywords, primary category from current taxonomy, optional secondary categories).
8. `indexing/` appends a line to `wiki/index.md` and to `wiki/categories/<primary>.md`.

A scheduled job (`cron` or a simple script run on demand) wraps this for periodic arXiv keyword search.

### 5.2 Query (two-pass)
1. User asks a question in chat.
2. **Pass 1 — Routing:** LLM is given the user's question + `wiki/index.md` + `wiki/taxonomy.md` and is asked to return a list of `paper_id`s most likely to answer the question (typically 1–5, capped at e.g. 8).
3. **Pass 2 — Answering:** LLM is given the question + `notes.md` of each selected paper, and produces the answer with citations back to `paper_id`s.
4. UI renders the answer, lists cited papers as expandable links to their `notes.md` and `source.pdf`.

If pass 1 returns no candidates, the LLM is allowed to answer from general knowledge with an explicit "no library hit" notice.

### 5.3 Rebalance (manual only)
Triggered by UI button or `python cli.py rebalance`.

1. LLM reads `wiki/taxonomy.md`, all category files, and a sampling of `meta.json` entries (counts per category, oldest/newest entries, etc.).
2. LLM proposes changes: split crowded categories, merge sparse ones, rename, add new categories, fix obvious miscategorizations.
3. Proposal is shown to the user as a diff before applying. User confirms.
4. On confirm: `taxonomy.md` is rewritten, `meta.json` files are updated for any reclassified papers, `wiki/index.md` and `wiki/categories/*.md` are regenerated from scratch from the current `meta.json` files.

The "regenerate wiki from meta.json" path is also the disaster-recovery path: if the index files are ever corrupted, they can be rebuilt from `papers/*/meta.json`. `meta.json` is the source of truth.

## 6. LLM Client Interface

```python
# lib/llm/base.py
class LLMClient(Protocol):
    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> str: ...
```

Implementations:
- `AnthropicClient` — uses `anthropic` SDK; reads `ANTHROPIC_API_KEY` from env. Default model: Claude Sonnet (latest available); configurable per-call.
- `ClaudeCodeClient` — invokes `claude` CLI as a subprocess in non-interactive mode, allowing skills to run. Captures stdout. Slower but free for users with a Claude Code subscription, and lets the wiki tasks benefit from skills.

The active client is selected via `config/default.yaml` and overridable per CLI invocation.

## 7. UI (Streamlit)

Single Streamlit app, four tabs:

1. **Chat** — text input, conversation history, expandable "cited papers" panel showing pass-1 routing decisions and pass-2 sources. Settings dropdown for LLM backend.
2. **Ingest** — multi-file PDF upload, arXiv ID/URL paste box, web URL paste box, and a search box that calls the search API and lets the user check papers to ingest. Shows ingest progress and any errors.
3. **Wiki Browser** — left pane lists categories from `taxonomy.md`; clicking shows the category file; clicking a paper shows its `notes.md` with a link to open `source.pdf`. Read-only.
4. **Maintain** — "Rebalance now" button, list of recent ingestions, manual "re-summarize this paper" action, simple stats (papers per category, ingested per month).

No auth. Single-user local tool.

## 8. Configuration

`config/default.yaml`:

```yaml
data_dir: ./data
llm:
  default_backend: anthropic   # or claude_code
  anthropic:
    model: claude-sonnet-latest
  claude_code:
    binary: claude
search:
  arxiv_keywords:
    - "vision language action"
    - "diffusion policy autonomous driving"
    - "world model autonomous driving"
    - "end-to-end driving"
seed_taxonomy:
  - vla
  - diffusion_decoder
  - world_model
  - e2e_planning
  - perception
  - datasets
  - misc
ingest:
  max_paper_id_collisions: 5
```

A local `config/local.yaml` (gitignored) overrides any field. API keys come from `.env` (gitignored).

## 9. Conda Environment

`environment.yml`:

```yaml
name: personal_library
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pip
  - pip:
      - streamlit
      - anthropic
      - pymupdf
      - arxiv          # arxiv API client
      - requests
      - readability-lxml
      - lxml
      - python-dotenv
      - pyyaml
      - pydantic
      - pytest
```

Created via `conda env create -f environment.yml`. Activate with `conda activate personal_library`.

## 10. Error Handling

- **Ingestion failures** (bad PDF, network error, parse error) — abort cleanly, write nothing to `papers/`, surface error in UI/CLI. Idempotent: re-running with the same source is safe.
- **LLM failures** during ingestion — keep raw artifacts (`source.pdf`, `full.md`); mark paper as `notes_pending` in `meta.json`. UI shows a "retry summarization" action.
- **Index corruption** — `meta.json` files are the source of truth; `cli.py rebuild-index` regenerates `wiki/` from scratch.
- **Hash collision / duplicate** — refuse to re-ingest; surface "already exists as `<paper_id>`".
- **Missing taxonomy entry** — if an LLM categorization names a category not in `taxonomy.md`, the paper goes to `misc.md` and a warning is logged. Rebalance is the path to legitimize new categories.

## 11. Testing Strategy

- **Unit:** each module's pure functions tested with fixture files (sample PDF, sample full.md, sample notes.md, sample wiki state). LLM calls mocked via a `FakeLLMClient` that returns canned responses.
- **Integration:** end-to-end ingest of a small fixture PDF using `FakeLLMClient`, asserting the resulting `papers/` and `wiki/` state.
- **Smoke (manual):** ingest 3–5 real arXiv papers using a real LLM backend before each release; eyeball the wiki output.
- **No live network in unit/integration tests.**

## 12. Open Items / Risks

- **Search API choice** — Semantic Scholar (free, academic, rate-limited) is a likely fit alongside arXiv API. General web search provider (Tavily/Brave/Exa) to be picked during implementation based on free-tier availability. Decision deferred to the implementation plan.
- **`ClaudeCodeClient` reliability** — invoking `claude` as a subprocess for structured tasks needs care around output parsing. May need a small "instruct it to wrap output in `<result>` tags" convention.
- **Long papers** — some papers exceed comfortable single-shot context. v1 strategy: truncate `full.md` to a budget (e.g. first 60k tokens) for the summarization pass; note truncation in `meta.json`. Revisit if quality suffers.
- **Scale** — pure-LLM routing is fine for low hundreds of papers; revisit when `index.md` exceeds ~1k lines.
