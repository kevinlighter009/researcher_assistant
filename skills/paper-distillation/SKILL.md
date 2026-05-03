---
name: paper-distillation
description: Use when reading a research-paper PDF (typically autonomous-driving — VLA, diffusion decoder, world model, end-to-end planning, perception, datasets) to produce a single structured Markdown file capturing keywords, innovation points, model architecture, and benchmark results. Output includes parseable YAML front-matter so a downstream wiki-generation step can index it without re-reading the paper. Triggers include "distill this paper", "summarize this paper for the wiki", "extract architecture and results from <pdf>".
---

# Paper Distillation

You are reading a research paper and producing a single structured Markdown file. The file you write will later be consumed mechanically by a wiki-generation script — so the structure matters, not just the content.

## When to use

Invoke this skill when the user asks you to read, summarize, distill, or extract from a research-paper PDF. Examples:

- "distill `doc/papers/vla/drivevlm-2024.pdf`"
- "extract the key points from this paper for my wiki"
- "summarize the architecture and results of <paper>"

Stop using this skill when the user asks for something else (a survey across papers, a code review, a refactor — those are different tasks).

## What you produce

Exactly one Markdown file with this layout:

1. **YAML front-matter** (machine-readable metadata)
2. **`# <Title>`** (H1 heading — the paper's title)
3. **`## Keywords`** — 5–8 short technical tokens. **THIS IS THE FIRST BODY SECTION, ALWAYS.**
4. **`## TL;DR`** — 2–4 sentences: what problem, what method, what result
5. **`## Problem & Motivation`** — what's broken about prior work that this paper fixes
6. **`## Innovation Points`** — 3–6 bulleted contributions
7. **`## Model Architecture`** — end-to-end data flow with key blocks
8. **`## Benchmark Results`** — datasets, headline numbers, key ablations
9. **`## Limitations & Open Questions`** — acknowledged or apparent

No other top-level sections. No alternate orderings. The wiki generator depends on these exact section names.

## Where to save the file

If the user names a path, use it.

Otherwise, mirror the source PDF location into a `distilled/` tree:

| Source PDF | Distilled MD |
|---|---|
| `doc/papers/<category>/<stem>.pdf` | `doc/distilled/<category>/<stem>.md` |
| `<anywhere>/<stem>.pdf` (no category) | `doc/distilled/misc/<stem>.md` |

The stem (filename without extension) carries over unchanged. So `doc/papers/vla/drivevlm-2024.pdf` → `doc/distilled/vla/drivevlm-2024.md`.

If the file already exists, ask the user whether to overwrite or skip. Do not silently clobber existing distillations.

## Workflow

### Step 1 — Read the paper

Use the Read tool on the PDF. For PDFs over ~10 pages, read pages 1–5 and the experiments section first (use `pages: "1-5"` and `pages: "<exp-pages>"`). Read the rest only if needed for architecture detail or limitations.

Read in priority order:
- **Abstract** — gives the framing in 200 words; often the cleanest summary the authors will produce.
- **Introduction** — almost always contains an explicit "our contributions are…" bullet list. Use it.
- **Method / Architecture** — figure captions are often more dense than body text. Read figures.
- **Experiments** — find the main result table. Note datasets, baselines, primary metric.
- **Conclusion / Limitations** — failure modes and future work.

### Step 2 — Identify bibliographic metadata

From the PDF (and a brief WebFetch of the arXiv abstract page if information is missing):
- Title, authors, year (publication or arXiv year)
- Venue (CVPR / ICCV / NeurIPS / arXiv / etc.) — look on the title page; also the arXiv "comments" field often says e.g. "Accepted at CVPR 2025"
- arXiv ID (e.g. `2402.12289`) and URL (`https://arxiv.org/abs/2402.12289`)
- A `paper_id` of the form `<year>-<slug>`, where `<slug>` is a short kebab-case version of the paper's short name (e.g. `2024-drivevlm`, not `2024-the-convergence-of-autonomous-driving-and-large-vision-language-models`). Pick the name the community uses.

If a field is not stated, use `null` (front-matter) and note it in the report — never invent.

### Step 3 — Choose categories

`primary_category` MUST be exactly one of:

| Value | Meaning |
|---|---|
| `vla` | Vision-Language-Action / VLM-conditioned driving |
| `diffusion_decoder` | Diffusion-based action / trajectory heads |
| `world_model` | Generative future prediction (video / occupancy / point cloud) for driving |
| `e2e_planning` | End-to-end perception+prediction+planning, **not** VLA-driven and **not** world-model-driven |
| `perception` | 3D detection, BEV, occupancy, HD-mapping |
| `datasets` | Datasets and benchmarks |
| `misc` | Anything that doesn't fit |

Pick the BEST single fit, even if the paper touches several. Use `secondary_categories` for the others. Tie-breaking guidance:

- Paper uses an LLM/VLM as the policy backbone? → `vla`
- Paper's headline contribution is a diffusion / flow-matching action head? → `diffusion_decoder`
- Paper predicts future frames / occupancy / point clouds and that's the central contribution? → `world_model`
- Paper trains a single network for perception+prediction+planning, no LLM, no diffusion? → `e2e_planning`
- Paper's contribution is upstream of planning (3D detection, BEV, occupancy, mapping)? → `perception`
- Paper introduces or evaluates on a new dataset / benchmark and that's the contribution? → `datasets`

### Step 4 — Write each section

#### `## Keywords` (first body section, always)

5–8 short technical tokens, comma-separated in a single bullet list or one line. Think "search tags". Examples:

> `vla, mllm, slow-fast-inference, drivevlm-13b, nuscenes`
> `diffusion-policy, denoising-head, trajectory-decoding, navsim`

Avoid: `autonomous-driving` (implicit), `paper`, `deep-learning`, full-sentence phrases.

#### `## TL;DR`

2–4 sentences. Pattern: *Problem. Method. Result.* No marketing words. Concrete.

> ❌ "We introduce a groundbreaking framework that revolutionizes…"
> ✅ "Existing end-to-end driving stacks are brittle in long-tail scenes. The authors couple a VLM (slow, scene-level reasoning) with a classical planner (fast, control-rate trajectories) via predicted meta-actions. On nuScenes-Hard the system reduces planning failure rate from X% to Y%."

#### `## Problem & Motivation`

Why this paper exists. Be concrete about prior approaches and their named failure modes. Don't speak in generalities.

#### `## Innovation Points`

A bulleted list of 3–6 items. Format each as:

```
- **<short name>** — <what it is>; <why it matters / what it enables>.
```

Use the paper's own naming for novel components (e.g. "slow-fast inference", "trajectory anchor mining"). Compress. One sentence per point.

#### `## Model Architecture`

Describe the data flow end-to-end: inputs → key blocks → outputs. Use bullet points or a small ASCII diagram. Include:
- Input modalities (camera count, LiDAR, radar, history horizon)
- Backbones (named, with size if stated)
- Intermediate representations (BEV, queries, latent video, etc.)
- Decoder / head
- Output (trajectory, control, occupancy, etc.) and its dimensionality
- Total params / training data scale, if stated

Example:

```
- 6 surround cameras (1 Hz, 2-frame history) → ResNet-50 + FPN
- BEV queries (200×200 grid, 256-d) → 6-layer deformable BEV-Former
- LLM head: Qwen2-7B, fed BEV-tokenized scene + ego state + textual prompt
- Output: 6-second future ego trajectory (12 waypoints, 2D) + textual rationale
- Trained on nuScenes (700 scenes) + 30K Wayve internal logs
```

#### `## Benchmark Results`

Lead with the **headline number**: dataset, primary metric, value, and the strongest baseline being beaten. Then 1–2 informative ablations (not all of them). Use a small table when comparing multiple methods:

```
**Closed-loop NAVSIM (PDMS):**
| Method            | PDMS ↑ |
|-------------------|--------|
| UniAD             | 83.2   |
| Hydra-MDP         | 86.5   |
| **This paper**    | **88.1** |

Ablations:
- Removing slow-pass VLM: PDMS drops 2.7 → confirms VLM contribution.
- Without temporal context: PDMS drops 1.4.
```

If a number isn't in the paper, **say so** (`not reported`) — never invent.

#### `## Limitations & Open Questions`

Either the paper's own acknowledged limitations OR the obvious gaps (e.g. "evaluated only on nuScenes; no closed-loop test", "13B model — inference cost not reported"). 2–4 bullets is enough.

### Step 5 — Write the YAML front-matter

```yaml
---
paper_id: <year>-<slug>
title: <full paper title>
authors: [<First Author>, et al.]
year: <YYYY>
venue: <e.g. CVPR 2025 | NeurIPS 2024 D&B | arXiv>
arxiv_id: <id or null>
url: <arxiv abs URL or null>
primary_category: <one of the 7 enumerated values>
secondary_categories: [<...>]
keywords: [kw1, kw2, kw3, kw4, kw5]
one_line_summary: <single technical line, ≤200 chars>
distilled_at: <YYYY-MM-DD>
source_pdf: <relative path from repo root, e.g. doc/papers/vla/drivevlm-2024.pdf>
---
```

Rules:
- Lists use bracket form: `[a, b, c]`. Don't use multi-line YAML lists — keeps the file compact and the parser simple.
- Strings with colons or special chars must be quoted.
- `keywords` in front-matter must be the same set (and order) as the `## Keywords` body section.
- `primary_category` must be one of the 7 enumerated values exactly.

### Step 6 — Self-check before finalizing

Before declaring done, verify:

- [ ] YAML front-matter is valid (every line is `key: value` or list/dict)
- [ ] `primary_category` is one of the 7 enumerated values
- [ ] `paper_id` follows `<year>-<slug>` form
- [ ] `## Keywords` is the FIRST body section (immediately after the `# <Title>` H1)
- [ ] All 7 mandatory body sections are present, in order, with non-empty content
- [ ] No invented numbers in Benchmark Results
- [ ] File saved at the agreed location
- [ ] Original PDF unchanged

If any check fails, fix before reporting done.

## Style rules

- **Technical, not marketing.** "Improves L2 by 12%" beats "significantly improves L2".
- **Quote numbers, not adjectives.**
- **Use the paper's own names** for novel components (don't synonym them away).
- **Don't pad.** A focused 400–700-word distillation is more useful than 2000 words.
- **One paper, one file.** Never combine multiple papers in one distillation.
- **Third person.** "The authors propose…", not "We propose…".

## Anti-patterns

- ❌ Pasting the abstract verbatim into TL;DR.
- ❌ Listing every section heading from the paper.
- ❌ Inventing numbers. If a value isn't in the paper, write `not reported`.
- ❌ Skipping the YAML front-matter (the wiki generator parses it).
- ❌ Putting `## Keywords` anywhere other than first body section.
- ❌ Renaming sections ("Method" instead of "Model Architecture").
- ❌ Using `primary_category: e2e-planning` (with hyphen) instead of `e2e_planning` (the enum value).
- ❌ Distilling multiple papers into one file.

## Example output (short)

```markdown
---
paper_id: 2024-drivevlm
title: "DriveVLM: The Convergence of Autonomous Driving and Large Vision-Language Models"
authors: [Xiaoyu Tian, et al.]
year: 2024
venue: CoRL 2024
arxiv_id: "2402.12289"
url: https://arxiv.org/abs/2402.12289
primary_category: vla
secondary_categories: [e2e_planning]
keywords: [vla, mllm, slow-fast, scene-description, meta-action, nuscenes]
one_line_summary: Hybrid VLM (slow, scene-level reasoning) + classical planner (fast, control-rate) via predicted meta-actions; reduces long-tail planning failures on nuScenes.
distilled_at: 2026-05-02
source_pdf: doc/papers/vla/drivevlm-2024.pdf
---

# DriveVLM: The Convergence of Autonomous Driving and Large Vision-Language Models

## Keywords
- vla, mllm, slow-fast, scene-description, meta-action, nuscenes

## TL;DR
End-to-end driving stacks fail on long-tail scenes that require semantic reasoning (construction signs, gestures, ambiguous right-of-way). The authors couple a 13B VLM that produces scene description and a sequence of "meta-actions" with a classical motion planner that consumes the meta-actions at control rate. On nuScenes long-tail subsets, planning failure rate drops vs. UniAD.

## Problem & Motivation
Pure end-to-end models (UniAD, VAD) have no mechanism to reason about scene semantics that don't appear in training-time supervision. They fail silently on novel construction zones, hand-waving police officers, etc. Pure VLM planners are too slow for closed-loop driving.

## Innovation Points
- **Slow-fast hybrid** — VLM runs at scene cadence (~1 Hz) emitting meta-actions; downstream planner runs at control rate consuming them.
- **Meta-action vocabulary** — discrete intent tokens (e.g. "yield to pedestrian on left", "slow for construction") that bridge VLM output and trajectory planner input.
- **Scene-description chain** — VLM first describes scene textually, then predicts meta-actions, then optionally a coarse trajectory; explicit chain helps interpretability and few-shot transfer.

## Model Architecture
- 6 surround cameras → image tokenizer → 13B VLM (Qwen-VL backbone)
- VLM output 1: scene description string
- VLM output 2: 6-step meta-action sequence (1 Hz)
- Downstream planner: lightweight transformer that consumes meta-actions + ego state at 10 Hz, emits 6-second waypoint trajectory.
- Trained on internal long-tail dataset + nuScenes annotations.

## Benchmark Results
**nuScenes long-tail evaluation:**
| Method     | Planning failure rate ↓ |
|------------|--------------------------|
| UniAD      | (paper baseline)        |
| **DriveVLM** | **lower by ~30% relative** |

Ablations: removing the chain-of-thought scene description hurts performance ~5%. Replacing 13B VLM with 7B costs ~3%.

(Exact numbers in paper Tables 2–3; not reproduced here.)

## Limitations & Open Questions
- 13B VLM inference cost not addressed for vehicle deployment.
- Closed-loop testing limited; mostly open-loop evaluation.
- Meta-action vocabulary is hand-designed; scaling to fully open-vocabulary intents is open.
```

## After completing the distillation

Report back to the user:
- Path of the file you wrote
- Word count of the file
- Any unresolved metadata fields (e.g. "venue not stated, marked `arXiv`")
- Any choices you made the user might want to override (e.g. "I categorized this as `vla` over `e2e_planning` because the LLM is the policy backbone")

If the user is asking you to distill a batch of papers, do them one at a time, reporting between each. Do not batch-write multiple distillations without checkpoints — papers are individually substantive enough to warrant per-paper review.
