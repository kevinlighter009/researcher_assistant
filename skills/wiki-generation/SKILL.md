---
name: wiki-generation
description: Use when generating, refreshing, or maintaining the personal-library wiki from distilled paper Markdown files (`doc/distilled/<category>/<stem>.md`). Triggers include "rebuild the wiki", "regenerate the index", "rebalance categories", "add the new papers to the wiki", "refresh the wiki", "the corpus changed". Output is a coherent set of Markdown files under `data/wiki/` plus a short report listing files written, paper counts, and any proposed taxonomy changes.
---

# Wiki Generation & Maintenance

You are producing or refreshing the *index* layer of a paper library whose primary content lives in `doc/distilled/<category>/<stem>.md` files (the `paper-distillation` skill produces those). Each distillation has YAML front-matter with `paper_id`, `title`, `year`, `venue`, `arxiv_id`, `url`, `primary_category`, `secondary_categories`, `keywords`, `one_line_summary`, plus body sections: `## Keywords`, `## TL;DR`, `## Problem & Motivation`, `## Innovation Points`, `## Model Architecture`, `## Benchmark Results`, `## Limitations & Open Questions`.

The wiki is read by an LLM later (or a human) to find and reason about papers. The model architecture content is the wiki's distinctive value-add — never compress it; embed full sections.

## When to use

- A new distillation MD has been added under `doc/distilled/<cat>/<stem>.md`.
- A distillation MD was removed (paper deleted) and stale rows must be purged.
- A paper's `primary_category` changed in its YAML front-matter.
- Editorial content (taxonomy descriptions, architecture-cluster prose, category narratives) needs to be authored or refreshed.
- A taxonomy change is proposed (split / merge / rename of a category).

If the wiki has never been generated, this is **full rebuild**; otherwise it's **maintenance** (incremental add/remove/update).

## What you produce

Under `<wiki_root>/` (default `data/wiki/`):

| File | Owner | Refreshed how |
|---|---|---|
| `index.md` | Auto | Regenerated every run from distillations. |
| `categories/<cat>.md` | Mostly auto | Regenerated each run; embeds full architecture sections. May carry a narrative intro (see §Editorial layer). |
| `architectures.md` | Mostly auto | Regenerated each run with tag-based clustering. May carry an editorial intro and per-cluster prose. |
| `taxonomy.md` | **You** | LLM-authored. Authoritative description of every category in use. Persists across regens. |
| `pending.md` | Auto (snapshot) | Lists PDFs with no matching distillation, so coverage gaps are visible. Re-snapshot each run. |

There is a deterministic helper that handles the routine bits: `python cli.py wiki-from-distilled` regenerates `index.md`, `categories/<cat>.md`, and `architectures.md`. **Use it as the baseline.** Then apply the editorial layer described in §Editorial layer below — that's the part that needs judgment.

## Source of truth

- **`doc/distilled/<cat>/<stem>.md`** — authoritative. The wiki MUST NOT contradict it.
- **Never edit a distilled MD from this skill.** If a paper's metadata is wrong, fix the distillation upstream (via `paper-distillation` skill); then re-run wiki generation.

## Workflow

### Mode A — Full rebuild

For a fresh wiki, or when the corpus changed substantially.

1. **Discover** distillations: walk `doc/distilled/` recursively. Skip any `MANIFEST.md`. For each `.md` parse the YAML front-matter and split the body into the seven canonical sections.
2. **Group** by `primary_category`.
3. **Validate** — every `primary_category` value should appear in the seed taxonomy (`vla`, `diffusion_decoder`, `world_model`, `e2e_planning`, `perception`, `datasets`, `misc`). Unknown values trigger a taxonomy proposal in the report (do not silently invent).
4. **Generate** each output by following the schemas in §File schemas.
5. **Tag** architectures using §Architecture tagging.
6. **Apply editorial layer** (§Editorial layer): write `taxonomy.md`, write narrative intros for each populated category, write the architecture-cluster prose in `architectures.md`, write `pending.md` if there are missing distillations.
7. **Self-check** (§Self-check). Fix any issues.
8. **Report** what changed (§Report).

If the deterministic helper is available, prefer:
```bash
python cli.py wiki-from-distilled
```
…then perform steps 6–8 only.

### Mode B — Incremental add (paper newly distilled)

1. Parse the new MD; pull `paper_id`, `primary_category`, `keywords`, and the architecture body.
2. Insert a row into `index.md`, sorted by `(primary_category, paper_id)`.
3. Insert a per-paper entry into `categories/<primary_category>.md`. Embed the full `## Model Architecture` section verbatim.
4. Update `architectures.md`: re-evaluate the new paper's tags and add it under each matching tag bucket; refresh per-category quick-scan tables.
5. If the new paper introduces a `primary_category` not in `taxonomy.md`, ADD a `taxonomy.md` entry AND surface the new category in your report so the user can review.
6. Increment paper counts in headers.

If the new paper has changed `primary_category` since a previous wiki state, also REMOVE its row from the old category's page.

### Mode C — Incremental remove (paper deleted)

1. Locate the matching `paper_id` in `index.md` and remove the row.
2. Remove the matching entry block from `categories/<primary_category>.md`.
3. Remove all references to the `paper_id` from `architectures.md`.
4. Decrement counts in any headers.
5. If a category becomes empty, **leave the category file in place** (still referenced by `taxonomy.md` for browsing). Do not delete category pages without explicit instruction.

### Mode D — Rebalance / taxonomy change

Triggered when a category is too large, too small, or visibly heterogeneous; or when a clearly distinct cluster has emerged from new distillations.

1. Read every distilled MD's front-matter; tally `primary_category` counts and inspect the keyword frequencies inside oversized buckets.
2. Inspect each oversized category for sub-clusters (e.g. `diffusion_decoder` splitting into `action_diffusion` vs `trajectory_diffusion`).
3. Inspect each undersized category — is there a sibling it should merge into?
4. Draft a **proposal**: a list of category creations / deletions / renames, plus per-paper `primary_category` reassignments, with one-sentence justifications.
5. **Show the proposal to the user before applying.** Do not silently rebalance.
6. Once confirmed, the SOURCE-OF-TRUTH edit is in each affected distillation's YAML front-matter (`primary_category` field). Either edit them programmatically or hand them back to the user. **The wiki layer must not carry per-paper assignments that disagree with the distilled MDs.**
7. Re-run Mode A.

## File schemas

### `index.md`

Pipe-table, one row per paper, sorted `(primary_category, paper_id)`:

```
| paper_id | year | category | title | venue | one_line_summary | keywords |
|----------|------|----------|-------|-------|------------------|----------|
| 2024-foo | 2024 | vla     | Title... | CVPR 2025 | One technical line. | kw1, kw2 |
```

Rules:
- Escape any literal `|` in cell values as `\|`.
- Collapse newlines to spaces.
- Title cell may be long — that's fine.
- Sort key: `primary_category` (alphabetical) then `paper_id`.

### `categories/<cat>.md`

```
# <cat>

<2-sentence narrative intro: what this category covers, what its papers tend
to focus on, and what the typical architectural shape looks like. You write
this with judgment — DO NOT copy from a paper's TL;DR.>

(<N> paper(s))

## <paper_id> — <title>
- **Venue / year:** <venue> / <year>
- **Summary:** <one_line_summary>
- **Keywords:** <kw1, kw2, ...>
- **Architecture signature:** <first non-empty bulleted line of the arch section, ≤240 chars>
- **Architecture tags:** <tag1, tag2, ...>
- **arXiv:** <url or —>
- **Distilled MD:** `doc/distilled/<cat>/<stem>.md`

### Model Architecture

<the full ## Model Architecture body verbatim from the distilled MD>

---

## <next paper>
...
```

The architecture section is **embedded verbatim** — never paraphrase. If the section is long, it's long; readability is fine because the wiki is structured by paper and most readers focus on one paper at a time.

### `architectures.md`

```
# Architectures Cross-Reference

<2-paragraph editorial intro: what tag clusters mean here, how to read this
page, and a one-line orientation to the corpus's overall architectural shape.>

## By inferred architecture tag

### `<tag>` (N)

<one-paragraph editorial blurb: what defines this cluster, what's the
typical input/backbone/decoder shape, what trade-off this approach makes.>

- **<paper_id>** — <title>  
  *<primary_category> • <venue> <year>*  
  Architecture: <one-line signature>
- ...

(repeat per tag, in the canonical order — see §Architecture tagging)

## By primary category

### `<cat>` (N)

| paper_id | title | tags | architecture (1-line) |
|----------|-------|------|------------------------|
| ...      | ...   | ...  | ...                    |
```

### `taxonomy.md`

You write this. It is the authoritative list of categories. Format:

```
# Taxonomy

The corpus is organized into <N> categories. Every distillation's
`primary_category` field MUST be one of the keys below. New categories
proposed during a Mode-D rebalance are also recorded here once accepted.

## `<cat>`

<2-3 sentences describing what this category covers; what makes a paper
belong here vs a sibling category; whether there are sub-clusters worth
noting (helpful for future rebalances).>

(repeat for each category in use)
```

A category should appear in `taxonomy.md` if either (a) it has at least one paper or (b) it's in the seed taxonomy.

### `pending.md`

Auto-snapshot of coverage gaps:

```
# Pending Distillations

PDFs present under `doc/papers/<cat>/` with no matching distillation under
`doc/distilled/<cat>/`. Surface these so coverage gaps are obvious; close
them by running the `paper-distillation` skill (manual via Claude Code) or
`python cli.py distill-run` (API).

(<N> pending)

| category | stem | source PDF |
|----------|------|------------|
| <cat>    | <stem> | doc/papers/<cat>/<stem>.pdf |
```

Group by category in the table for browsability.

## Editorial layer

These four pieces of editorial content are what distinguish a thoughtful wiki from a mechanical dump. They sit on top of the deterministic generator output:

1. **`taxonomy.md`** — described above. Persists across regens (the deterministic helper does NOT touch it).
2. **Per-category narrative intro** — the 2-sentence intro at the top of each populated `categories/<cat>.md`. The deterministic helper writes a placeholder ("Papers categorized as `<cat>`."); you replace it after each run with a substantive intro that captures what differentiates this category.
3. **`architectures.md` editorial intro + per-cluster prose** — the 2-paragraph intro at the top, and the 1-paragraph blurb above each tag's bullet list. Replace the placeholder text the deterministic helper writes.
4. **`pending.md`** — auto-snapshot from `python cli.py distill-check`-equivalent logic. Re-snapshot every run.

If you re-run the deterministic helper later, the auto-generated bits get overwritten — so re-apply this editorial layer afterward. `taxonomy.md` and `pending.md` survive.

## Architecture tagging

Tag a paper by case-insensitive regex matching against:
- The paper's `keywords` (front-matter list, joined by spaces)
- The paper's `## Model Architecture` body (raw text)

Canonical tags and patterns (this matches what the deterministic helper does — keep them in sync):

| Tag | Patterns (regex, case-insensitive) |
|---|---|
| `uses-vlm-backbone` | `vlm`, `mllm`, `llava`, `qwen-?vl`, `llama`, `vision[- ]language`, `gpt-4` |
| `uses-diffusion-head` | `diffusion`, `denois`, `ddim`, `ddpm`, `score-matching`, `flow[- ]matching` |
| `uses-bev-transformer` | `bev`, `deformable[- ]attention`, `bev[- ]former`, `bev[- ]queries` |
| `uses-occupancy-grid` | `occupancy`, `occworld`, `occ3d`, `3d occupancy` |
| `uses-world-model` | `world[- ]model`, `future video`, `video[- ]gen`, `video diffusion` |
| `uses-cnn-backbone` | `resnet-?\d`, `efficientnet`, `convnext`, `swin`, `vit` |
| `uses-trajectory-anchors` | `trajectory anchor`, `k-?means anchor`, `anchor(ed)? gaussian`, `meta[- ]action` |
| `uses-classical-planner` | `classical planner`, `rule-?based planner`, `slow[- ]fast`, `hybrid (planner\|policy)` |

Tags are non-exclusive; a paper may carry many. The first bucket order in `architectures.md` follows the table order above.

When you encounter a paper that doesn't fit any tag, list it under an `untagged` bucket at the end and surface it in your report — it might motivate a new tag.

When new architectural patterns emerge in the corpus that warrant a new tag (e.g. `uses-state-space-model`, `uses-flow-matching`), propose the addition in your report. Do not invent a tag silently.

## Self-check

Before declaring done:

- [ ] Every distillation under `doc/distilled/` is represented by exactly one row in `index.md`.
- [ ] Sort order: `index.md` is sorted by `(primary_category, paper_id)`.
- [ ] Every `primary_category` value used in `index.md` has a section in `taxonomy.md`.
- [ ] Every `paper_id` in `index.md` has a corresponding `## <paper_id> — <title>` entry in its `categories/<primary_category>.md`.
- [ ] Every category page's count line matches the number of paper entries in it.
- [ ] Every paper appears in at least one tag bucket in `architectures.md` (or in `untagged`).
- [ ] No literal `|` in pipe-table cells (escape as `\|`).
- [ ] No paraphrased architecture sections — every `### Model Architecture` block is verbatim from the distilled MD.
- [ ] `taxonomy.md` describes every category in use.
- [ ] `pending.md` (if produced) reflects the current PDF/distillation diff.

If any check fails, fix before reporting done.

## Anti-patterns

- ❌ Inventing paper rows — every entry must come from a parsed distillation.
- ❌ Modifying distilled MDs from the wiki layer — they're upstream; fix in the distillation flow if metadata is wrong.
- ❌ Silently renaming or removing a category. Always propose taxonomy changes and wait for confirmation.
- ❌ Filling tag buckets with synthetic content — tag a paper only if the patterns actually match.
- ❌ Mixing editorial prose into the index pipe-table — keep cells one-line and machine-parseable.
- ❌ Deleting an empty category file because it has zero papers — categories persist for browsing.
- ❌ Paraphrasing or compressing an embedded `### Model Architecture` block. Embed it verbatim.
- ❌ Letting `taxonomy.md` go stale. If a `primary_category` value appears that taxonomy doesn't cover, add it (and report).

## Report format

After applying the skill, report:

- **Files written / updated** (paths + a one-line description per file).
- **Paper counts** — total + per-category, with deltas from the previous state if known (e.g. "vla: 11 → 12 (+1)").
- **New tags** introduced (if any).
- **Proposed taxonomy changes** (Mode D), with paper counts that motivate them.
- **Pending distillations** count.
- **Anomalies** — missing front-matter fields, duplicate `paper_id`s, papers without an architecture section, papers in categories not in `taxonomy.md`.

Keep the report under ~300 words; the wiki itself is the artifact.

## Worked example (short)

Suppose `doc/distilled/` has the existing 18 distillations and one new one is added at `doc/distilled/world_model/gaia-2-wayve-2025.md`.

- Run `python cli.py wiki-from-distilled` → 19 papers indexed; `world_model` category file populated; one paper now under `uses-world-model` and `uses-vlm-backbone` (if its keywords match) tags.
- Replace the stub intro in `categories/world_model.md` with a 2-sentence narrative.
- Replace the placeholder intro in `architectures.md` with editorial prose; add prose to the `uses-world-model` tag block now that it has content.
- Add a `## world_model` section to `taxonomy.md` if it wasn't there.
- Refresh `pending.md` from the latest sync diff.
- Report: "world_model: 0 → 1 (+1); index 18 → 19; new tag bucket populated: uses-world-model; no taxonomy change proposed; pending: 40 (was 41)."
