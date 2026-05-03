# Contributing

Thanks for considering a contribution. Researcher Assistant is built around a
few opinionated conventions; following them makes review fast and keeps the
system coherent across the library, the UI, the CLI, and the three skills.

---

## Setup

```bash
conda env create -f environment.yml
conda activate researcher_assistant
# or: python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

cp .env.example .env   # set ANTHROPIC_API_KEY only if you intend to run API-driven flows
```

Run the test suite to verify the install:

```bash
pytest -q
```

You should see **all tests passing in well under 5 seconds**. The suite is
hermetic — it never touches the network or invokes a real `claude` CLI. If a
test you write needs the network, mock it (see existing patterns in
`tests/test_anthropic_client.py` and `tests/test_claude_code_client.py`).

---

## Test-driven discipline

Every code-touching change follows the same five-step rhythm. The
implementation plan in `docs/superpowers/plans/2026-05-02-personal-library-core.md`
walks through 19 tasks built this way; new contributions should match the
pattern.

1. Write the failing test.
2. Run the test and **confirm it fails for the right reason** (e.g.
   `ModuleNotFoundError`, `AssertionError` on the actual behavior).
3. Write the minimal implementation that makes the test pass.
4. Run the test and confirm it passes.
5. Run the full suite (`pytest -q`) — no regressions allowed.

For UI-only changes (`ui/pages/*.py`) tests are hard to unit-write; the
acceptance bar is **HTTP 200 on every page** plus no errors in the
Streamlit dev log. The recipe is:

```bash
streamlit run ui/Home.py --server.headless=true --server.port=8772 &
sleep 5
for url_path in "" Wiki_Browser Distillation_Manager Architecture_Explorer Codebase_Analyzer Compare Wiki_Maintenance; do
  curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8772/$url_path"
done
kill %1
```

When the UI page exposes new logic, factor the testable bits into `lib/`
and unit-test there. (See `lib/notes/store.py` ↔ `ui/pages/1_Wiki_Browser.py`
for the existing pattern.)

---

## Module boundaries

The library is intentionally split into well-bounded modules. Imports across
boundaries follow these rules — don't break them without raising the issue
in your PR.

| Module | May import from | MUST NOT import from |
|---|---|---|
| `lib.llm.*` | stdlib, `anthropic`, `subprocess` (only `claude_code_client`) | any other `lib.*` |
| `lib.ingestion.*` | `lib.llm.base`, `lib.models`, `lib.storage`, `fitz` | `lib.indexing`, `lib.query`, `lib.search` |
| `lib.indexing.*` | `lib.models`, `lib.storage` | `lib.ingestion`, `lib.query`, `lib.search` |
| `lib.query.*` | `lib.llm.base`, `lib.storage`, `lib.indexing.writer` (just `WikiPaths`) | `lib.ingestion`, `lib.search` |
| `lib.search.*` | stdlib, `rank_bm25` | any other `lib.*` |
| `lib.codebase.*` | `lib.llm.base`, stdlib | `lib.ingestion`, `lib.indexing`, `lib.query`, `lib.search` |
| `lib.notes.*` | stdlib | any other `lib.*` |
| `lib.distillation.*` | `lib.llm.base`, `lib.indexing.from_distilled` (only `parse_distilled_md`), `lib.ingestion.pdf_parser` | other modules |
| `lib.pipeline` | `lib.ingestion`, `lib.indexing` | _is the only place these may meet_ |

In short: **anything that talks to an LLM goes through `lib.llm`. The wiki
layer never edits distillations. The search layer is read-only.**

---

## Adding a paper to the corpus

Two paths, both produce a SKILL.md-format distillation:

**A. Manual (Claude Code, free):**

1. Drop the PDF into `doc/papers/<category>/<stem>.pdf`.
2. Open Claude Code in this repo.
3. Tell it: *"use `skills/paper-distillation/SKILL.md` to distill `doc/papers/<category>/<stem>.pdf`"*.
4. Verify the output at `doc/distilled/<category>/<stem>.md` — it should
   start with valid YAML front-matter (`paper_id`, `title`, `year`,
   `primary_category`, `keywords`, …) and have `## Keywords` as its first
   body section.
5. `python cli.py wiki-from-distilled` to refresh the wiki.

**B. API (`ANTHROPIC_API_KEY` required):**

```bash
python cli.py distill-run --only <category>/<stem>
python cli.py wiki-from-distilled
```

Or use the **Distillation Manager** UI page for batch runs.

PRs that add distillations are welcome. PDFs themselves should NOT be
committed (`doc/papers/` is gitignored — too large + copyright concerns);
each distilled MD's `arxiv_id` / `url` field provides the reproducibility
path on a fresh clone.

---

## Adding or evolving a skill

Skills under `skills/<name>/SKILL.md` are first-class artifacts. They drive
LLM-side behavior, so they need to stay self-consistent with the
deterministic Python that pairs with them.

If you add a skill:
- Keep its triggers (in the YAML frontmatter `description`) specific.
- Include a **worked example** at the bottom.
- Cross-reference any related Python modules so a reader knows where the
  shared heuristics live (e.g. `wiki-generation` skill points at
  `lib.indexing.from_distilled` for the architecture-tag table).
- If the skill's output format changes, update the corresponding parser
  (and its tests) in the same PR.

If you change an existing skill's output schema, update the parser
(`lib/indexing/from_distilled.py::parse_distilled_md` for paper distillations)
and the tests in the same PR. A drift between SKILL.md and the parser is
a top source of subtle failures.

---

## Adding a new architecture tag

Architecture tags are heuristic clusters (e.g. `uses-vlm-backbone`,
`uses-diffusion-head`) used in:

- `lib/indexing/from_distilled.py::_ARCH_PATTERNS` — the regex table.
- `skills/wiki-generation/SKILL.md` — the documented table.
- `data/wiki/architectures.md` — the cross-reference page (regenerable).

To add one:

1. Pick a name in the existing kebab-case `uses-<thing>` pattern.
2. Add it to `_ARCH_PATTERNS` with regex patterns that match it.
3. Add a row to the table in `skills/wiki-generation/SKILL.md`.
4. Re-run `python cli.py wiki-from-distilled` and verify the new tag bucket
   surfaces papers as expected. Any `untagged` papers that should fall in
   the new bucket — adjust regexes.
5. Add a test in `tests/test_from_distilled.py` covering at least one
   positive and one negative match.
6. Open a PR titled `feat(indexing): tag <new-tag>` describing what it
   represents and which papers it newly surfaces.

---

## Commit message convention

We follow a `<type>(<area>): <imperative summary>` form. Examples:

```
feat(search): BM25 content search across wiki + distilled MDs
feat(ui): Tier-2 features — Compare page + Notes mode in Wiki Browser
feat(skills): wiki-generation SKILL.md
fix(query): preserve order of cited paper_ids
docs(readme): add License + Contributing sections
chore: bump rank-bm25 floor to 0.2.3
ci: add pytest workflow
test(notes): cover empty-content-deletes-existing-note
```

Common types: `feat`, `fix`, `docs`, `test`, `chore`, `ci`, `refactor`.

If your commit makes the test count change, mention the delta in the body
(e.g. `Test count 105 -> 109`). For UI changes, include the result of the
HTTP-200 sweep.

The original implementation history uses this convention end-to-end —
`git log --oneline` is a quick reference for tone.

---

## Code style

Light-touch — no enforced linter. The conventions used throughout:

- `from __future__ import annotations` at the top of every Python file.
- `Path` over `str` for filesystem paths in public APIs.
- Keyword-only public APIs (`def f(*, x, y, ...)`) for anything with more
  than one argument.
- `dataclass` for in-memory transit objects; `pydantic.BaseModel` for
  serialized state (e.g. `meta.json`, `Config`).
- Module docstrings stating the module's one responsibility.
- No emoji in code or comments unless explicitly requested by the
  surface (`st.set_page_config(page_icon=...)` is fine).

---

## Pull-request checklist

Before opening a PR:

- [ ] `pytest -q` passes locally.
- [ ] Test count moves only in the direction your change implies (no
      silent regressions; new feature should add tests).
- [ ] No new heavy dependencies (no torch / transformers / vector DBs)
      without raising the trade-off in the PR description.
- [ ] Module boundaries respected (see table above).
- [ ] If the change affects the wiki-generation flow, you've re-run
      `python cli.py wiki-from-distilled` against the seed corpus.
- [ ] Commit messages follow the `<type>(<area>): <summary>` form.

---

## Asking for help

Open an issue describing:

- What you're trying to do.
- What you tried.
- What happened.

Pointers to specific files / line numbers help. The codebase is small —
~1.5k lines of library + 7 UI pages + 3 skills — so a precise question
usually gets a precise answer fast.
