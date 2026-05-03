---
name: codebase-analyzer
description: Use when given a path to an autonomous-driving (or related ML) codebase to analyze. The skill walks the codebase, identifies the methods and architectures currently in use, references the personal-library wiki to map them onto known patterns, and proposes concrete upgrade paths citing specific papers from the wiki. Triggers include "analyze this codebase", "what methods is this repo using", "suggest upgrades for this repo based on the wiki", "what could I improve here", "review this repo against the wiki".
---

# Codebase Analyzer (with Wiki-Referenced Upgrades)

You are inspecting an existing codebase and producing a structured report that:

1. Outlines what methods / architectures the codebase currently uses, with file references.
2. Maps those methods onto the architecture-tag clusters used by the personal-library wiki (`data/wiki/architectures.md`).
3. Proposes concrete upgrade paths, each citing specific paper(s) from the wiki by `paper_id` and giving an integration sketch.

The wiki is the authoritative reference for "what's known and worth borrowing". Never propose an upgrade based on something not in the wiki without explicitly labelling it as `(no wiki precedent — outside-of-corpus suggestion)`.

## When to use

- "Analyze this codebase" / "what's this repo using?"
- "Suggest upgrades to this repo based on the wiki"
- "What's missing here that the recent literature has?"
- "Review this driving stack and tell me where it lags"

Stop using this skill when the task is something else — a code review, a bug fix, a refactor — those are different tasks.

## Inputs you need

| Input | Default | Notes |
|---|---|---|
| Codebase path | (mandatory) | Absolute or repo-relative; assume read-only |
| Wiki root | `data/wiki/` | Where `architectures.md`, `taxonomy.md`, `categories/*.md` live |
| Distillations root | `doc/distilled/` | Per-paper deep notes used for upgrade citations |
| Output path | `<codebase>/UPGRADE_PROPOSALS.md` | Override if user names a path |

If the wiki root is empty or missing, **stop** and tell the user to generate it first (`python cli.py wiki-from-distilled` and the `wiki-generation` skill). The whole point of this skill is the wiki-grounded comparison.

## Workflow

### Step 1 — Scope the codebase (DO NOT read every file)

Use Glob and Read to understand the layout — selectively. Read in this priority order, stopping early once you have enough:

1. **README** (`README.md`, `README.rst`) — what *is* this codebase?
2. **Setup files** — `pyproject.toml`, `setup.py`, `requirements.txt`, `environment.yml`, `package.json`. Frameworks tell you a lot: PyTorch + Lightning vs. JAX + Flax vs. plain numpy.
3. **Top-level layout** — list the top directory and 1 level into anything that looks like the model code (`models/`, `networks/`, `architectures/`, `policies/`).
4. **Model definition file(s)** — search for `nn.Module` (PyTorch), `nnx.Module` (Flax), `tf.keras.Model` (TF), or top-level `class .*Model` / `class .*Net` declarations.
5. **Training entry point** — `train.py`, `main.py`, `trainer.py`, `pl_module.py`. Tells you the optimizer, loss, schedule.
6. **Data loader** — what inputs is the model actually fed (image count, sensor types, temporal horizon)?
7. **Forward pass** — trace one call: input → backbone → middle representation → head → output.
8. **Tests** (lightly) — what's the model's contract (input/output shape)?

A static read of 8-15 carefully-chosen files is usually enough. If the codebase is genuinely large (>200K LOC), say so in the report and pick a single subsystem (perception, planning, …) with the user.

### Step 2 — Identify methods (with file:line references)

Distill what you saw into a table. For each *axis*, give a name and a code citation.

The canonical axes (cover all that apply):

| Axis | Examples |
|---|---|
| **Inputs** | 6 surround cams + 32-beam LiDAR / front cam only / ego state / nav goal |
| **Backbone** | ResNet-50 / Swin-T / ViT-L/14 / Qwen-VL-7B / EfficientNet-B3 |
| **Intermediate representation** | BEV queries (200×200, 256-d) / Image tokens / Voxel grid / Agent queries |
| **Temporal handling** | None / 2-frame fusion / Recurrent BEV / Video-tokenizer + LLM |
| **Decoder / head** | MLP regression / Classifier / Diffusion / Autoregressive / Flow-matching |
| **Output** | Single trajectory (12 waypoints, 2D) / Multi-mode (K=8) / Action / Occupancy |
| **Loss** | MSE / Cross-entropy / Diffusion / Imitation + L1 |
| **Inference** | Single-pass / Cascaded (slow-fast) / Multi-step denoising |
| **Training data** | nuScenes / CARLA / Internal logs / nuPlan |
| **Eval** | Open-loop L2 / NAVSIM PDMS / Closed-loop CARLA |

For each row, cite the file and line where the choice is observed:

```
- **Backbone:** ResNet-50 — `models/perception.py:42`
- **Decoder:** 3-layer MLP regression to 12 waypoints — `models/planner.py:120`
- **Loss:** MSE on waypoints — `train.py:88`
```

If you can't find the answer for an axis from a static read, write `not determined from a static read` and surface it in the open-questions section. Don't guess.

### Step 3 — Map the codebase to wiki architecture tags

Read `data/wiki/architectures.md`. The wiki uses these heuristic tags:

| Tag | What it means |
|---|---|
| `uses-vlm-backbone` | VLM/MLLM as policy backbone |
| `uses-diffusion-head` | Diffusion / denoising / flow-matching trajectory or action head |
| `uses-bev-transformer` | Learned BEV queries with deformable cross-attention |
| `uses-occupancy-grid` | Voxel / occupancy output instead of (or alongside) boxes |
| `uses-world-model` | Generative future prediction (video / occupancy / point clouds) |
| `uses-cnn-backbone` | ResNet / Swin / EfficientNet / ViT image encoder |
| `uses-trajectory-anchors` | K-Means clustered anchors + learned offset/score (often paired with diffusion or vocabulary planning) |
| `uses-classical-planner` | Hand-crafted planner coupled with a learned model (often slow-fast) |

Produce two lists:
- **Tags currently present** in the codebase (with the file:line evidence reused from Step 2).
- **Tags absent** — i.e. patterns the wiki recognizes that the codebase doesn't use yet. These are your **upgrade frontier**.

If the codebase uses a pattern the wiki doesn't have a tag for, mention it under `(no wiki tag — propose a new tag?)`.

### Step 4 — Propose upgrades

For each tag in the upgrade frontier (and for any axis where the current choice is suboptimal vs. recent literature), propose 1–3 concrete upgrade paths. **Order by impact × ease**, leading with cheap-and-effective.

Each proposal has six fields (use the template in §Output template):

1. **Title** — one-line claim. ("Replace the MLP regression head with a truncated diffusion head.")
2. **Motivation** — what problem this addresses in *this* codebase, not in the abstract. Cite the file:line again.
3. **Wiki precedent** — `paper_id`(s) from the wiki demonstrating the pattern, with a one-line distillation summary copied verbatim from the per-paper distilled MD's `one_line_summary` front-matter field. Do NOT invent paper_ids — verify each exists under `doc/distilled/`.
4. **Integration sketch** — pseudocode or a diff outline showing where the swap goes, referencing the current code's files. Should be ~10–20 lines.
5. **Risks** — what could go wrong, what's the rollback. Be specific (e.g. "training time +30%; may regress single-mode metrics that don't reward multi-mode behavior").
6. **Cost** — engineering effort `S` (a day) / `M` (a week) / `L` (multi-week). Plus inference-time / training-time cost change estimate when known.

If a proposal has no wiki precedent (e.g. you want to suggest a state-space-model backbone but the wiki doesn't cover it), label it explicitly: **"no wiki precedent — outside-of-corpus suggestion"**. Lead the report with wiki-grounded proposals; outside-of-corpus suggestions go at the end.

### Step 5 — Write the report

Save the report at `<codebase>/UPGRADE_PROPOSALS.md` (or the user's path). Use the template in §Output template.

### Step 6 — Self-check

- [ ] Every method axis in the Identified Methods table has a `file:line` reference (or `not determined from a static read`).
- [ ] Every upgrade proposal has either a `paper_id` from the wiki OR an explicit `(no wiki precedent — …)` label.
- [ ] Every cited `paper_id` actually exists under `doc/distilled/<cat>/<stem>.md` with that ID in its front-matter.
- [ ] Proposals are ordered by impact × ease (cheap-and-effective first).
- [ ] An "Open Questions" section lists items you couldn't determine.
- [ ] No invented numbers, no marketing language.

If any check fails, fix before reporting done.

## Heuristics for method identification

Static patterns to look for (case-insensitive, regex-ish):

| Heuristic | Likely identification |
|---|---|
| `from torchvision.models import resnet`, `ResNet-?\d` | CNN backbone |
| `timm.create_model("swin*"\|"vit*"\|"efficientnet*")` | ViT / Swin / EfficientNet |
| `from transformers import .*Qwen.*\|.*LLaVA.*\|.*LLaMA.*` + a chat-style forward | VLM backbone |
| `BEVFormer`, `BEVQueries`, `bev_queries`, `deformable_attn` | BEV transformer |
| `voxel_features`, `occ_head`, `OccHead`, `dense_voxel` | Occupancy grid |
| `noise_pred`, `denoise`, `DDPM`, `DDIMScheduler`, `loss_diffusion` | Diffusion head |
| `kmeans.*trajector`, `anchor.*trajectory`, `anchor_offset` | Trajectory anchors |
| `nn.Sequential.*Linear.*Linear.*Linear` ending in waypoint dims | MLP regression head |
| `optimization`, `cvxpy`, `casadi`, `mpc`, `scipy.optimize` | Classical planner / optimization |

Beyond static patterns, look at:
- The `forward` argument names and shapes (`(B, V, C, H, W)` is multi-view; `(B, T, ...)` is temporal).
- Loss names (`mse_loss` → regression; `cross_entropy` → classification; `ddpm_loss` → diffusion).
- Output post-processing (`top_k_trajectories(...)`, `nms_3d(...)`).

## Heuristics for upgrade selection

When choosing what to recommend from the wiki:

- **Start with the closest cluster the codebase isn't in yet.** If it has CNN backbone + MLP regression and you see the `uses-bev-transformer` and `uses-diffusion-head` clusters in the wiki, those are the highest-leverage swaps.
- **Prefer recent papers** (2024–2026) when multiple candidates exist in the same cluster, unless the foundational paper is the cleanest reference.
- **Prefer papers that explicitly fit the codebase's regime** — if the codebase is camera-only, cite `2024-carllava` over LiDAR-fusion papers. If it's NAVSIM-evaluated, cite `2024-diffusiondrive` / `2025-goalflow` (NAVSIM SOTA).
- **Pair related upgrades.** If proposing a diffusion head, mention that anchored-Gaussian (`2024-diffusiondrive`) typically pairs with the diffusion swap to avoid mode collapse.
- **Don't recommend the same paper in 5 different sections.** Cite where most relevant once.

## Anti-patterns

- ❌ Inventing methods or papers not in the codebase or wiki.
- ❌ Surface-level summary without `file:line` evidence.
- ❌ Proposing changes without citing a wiki paper (or labelling as no-precedent).
- ❌ Boil-the-ocean refactors ("rewrite in JAX", "switch to a fundamentally different stack"). Stick to incremental swaps.
- ❌ Papering over genuine architectural drift; if the codebase has multiple incompatible patterns, name the conflict in the report.
- ❌ Reading every file — read selectively. Time is the cost.
- ❌ Citing `paper_id`s without verifying they exist in `doc/distilled/`.
- ❌ Mixing "what the codebase does today" with "what it should do tomorrow" in the same section.
- ❌ Proposing 10 upgrades. 3–6 well-scoped is more useful than 10 scattered.

## Output template

Save at `<codebase>/UPGRADE_PROPOSALS.md`:

```markdown
# Upgrade Proposals: <codebase name>

**Analyzed:** <YYYY-MM-DD>
**Codebase root:** <abs path>
**Wiki:** <wiki path>
**Files read:** <count> (out of <total>)

## Codebase Summary

<one paragraph: what is this codebase, what's its primary task,
what's its current evaluation regime>

## Identified Methods

| Axis | Current | Source (file:line) |
|---|---|---|
| Inputs | 6 surround cams (1 Hz, 2-frame history) | `data/loader.py:34` |
| Backbone | ResNet-50 | `models/perception.py:42` |
| Intermediate rep. | BEV queries (200×200, 256-d) | `models/perception.py:118` |
| Temporal | Recurrent BEV (1-step memory) | `models/perception.py:160` |
| Decoder / head | 3-layer MLP regression | `models/planner.py:120` |
| Output | Single 12-waypoint trajectory | `models/planner.py:135` |
| Loss | MSE on waypoints | `train.py:88` |
| Inference | Single-pass | `inference.py:50` |
| Training data | nuScenes (700 scenes) | `data/dataset.py:12` |
| Eval | Open-loop L2 / collision | `eval.py:60` |

## Wiki Tag Map

**Tags currently present:**
- `uses-cnn-backbone` (ResNet-50 in `models/perception.py:42`)
- `uses-bev-transformer` (BEV queries, deformable attention in `models/perception.py:118`)

**Tags absent (upgrade frontier):**
- `uses-diffusion-head` — single-mode regression head; multi-mode driving decisions are not represented.
- `uses-trajectory-anchors` — no K-Means anchors; mode collapse is a known failure mode of the current design.
- `uses-vlm-backbone` — no semantic-reasoning track for long-tail scenes.
- `uses-occupancy-grid` — current perception only emits boxes; unknown-geometry obstacles are missed.

## Proposed Upgrades

### 1. Replace the MLP regression head with a truncated diffusion head

**Motivation:** `models/planner.py:120` regresses a single trajectory; ambiguous scenes (intersections, merge decisions) have no multi-mode representation. Mode collapse is the default failure mode.

**Wiki precedent:** `2024-diffusiondrive` — *Truncated diffusion policy that denoises from K-Means trajectory anchors in 2 steps via a cascade transformer decoder; 88.1 PDMS at 45 FPS on NAVSIM with ResNet-34.*

**Integration sketch:**

```python
# models/planner.py — replace regression head
# OLD: head = nn.Sequential(...) -> (B, 12, 2)
# NEW:
class TruncatedDiffusionHead(nn.Module):
    def __init__(self, anchor_path, n_steps=2):
        self.anchors = load_kmeans(anchor_path)        # (K=20, 12, 2)
        self.cascade = CascadeDecoder(n_layers=2)
    def forward(self, bev_features, agent_queries):
        noise = torch.randn_like(self.anchors) * 0.05
        traj = self.anchors + noise
        for step in range(self.n_steps):
            traj = self.cascade(traj, bev_features, agent_queries, step)
        return traj                                    # (B, K, 12, 2)
```

K-Means anchors are pre-computed from the training set's GT trajectories; lift this into a one-time `precompute_anchors.py` script.

**Risks:** training loss now requires sampling and matching to GT (use chamfer or hungarian over the K trajectories); single-mode metrics (single-trajectory L2) will be worse — switch eval to multi-mode (top-K mPADE, NAVSIM PDMS).

**Cost:** **M** — 1–2 weeks. Inference: +1ms/sample (negligible). Training: +20% wall-clock.

---

### 2. <next proposal>
...

## Outside-of-corpus suggestions

(Anything not grounded in the wiki goes here. Always lower priority.)

## Open Questions

- Couldn't determine the temporal horizon of the BEV memory (`models/perception.py:160`); is it 1-step or T-step?
- The codebase doesn't include eval scripts for closed-loop benchmarks; is closed-loop (NAVSIM / Bench2Drive) in scope?
- ...
```

## Worked example (short)

User says: "Analyze `~/projects/my-driving-stack` and suggest upgrades."

1. Glob: `**/*.py` says ~50 files; you read 11 of them (README, pyproject.toml, models/perception.py, models/planner.py, train.py, data/loader.py, configs/default.yaml, eval.py, inference.py, tests/test_planner.py, requirements.txt).
2. You identify: ResNet-50 + BEV-Former-style queries (`uses-cnn-backbone` + `uses-bev-transformer`); MLP regression head with MSE loss; nuScenes-only training; open-loop L2 eval.
3. Wiki tag map: present = `uses-cnn-backbone`, `uses-bev-transformer`. Absent = the other six.
4. Top-3 proposals: (a) truncated diffusion head citing `2024-diffusiondrive` (S–M cost, high impact); (b) NAVSIM closed-loop eval citing `2024-navsim` and `2024-bench2drive` (S cost, surfaces real-world failure modes); (c) add a slow-fast VLM track for long-tail reasoning citing `2024-drivevlm` (L cost, high impact, optional follow-up).
5. Outside-of-corpus suggestion: state-space-model backbone (no wiki precedent yet — Mamba / Hyena / RWKV).
6. Open questions: ego-conditioning quality of the BEV temporal fusion; whether codebase author is open to multi-mode eval metrics.

Write the report to `~/projects/my-driving-stack/UPGRADE_PROPOSALS.md`.

## Final report (after writing the file)

Briefly tell the user:
- Path of the report
- How many proposals, top one's title
- What you couldn't determine from a static read

Keep this final summary under ~150 words. The report file is the artifact.
