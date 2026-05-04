---
paper_id: 2024-bev-planner
title: "Is Ego Status All You Need for Open-Loop End-to-End Autonomous Driving?"
authors: [Zhiqi Li, Zhiding Yu, Shiyi Lan, Jiahan Li, Jan Kautz, Tong Lu, Jose M. Alvarez]
year: 2024
venue: CVPR 2024
arxiv_id: "2312.03031"
url: https://arxiv.org/abs/2312.03031
primary_category: e2e_planning
secondary_categories: [perception, datasets]
keywords: [bev-planner, ego-mlp, ad-mlp, ego-status-leakage, nuscenes, ccr-metric, open-loop-planning, label-leakage]
one_line_summary: Critical analysis showing nuScenes open-loop e2e driving SOTA is dominated by ego-status leakage; introduces Curb Collision Rate metric and a perception-free BEV-Planner baseline that matches UniAD/VAD.
distilled_at: 2026-05-02
source_pdf: doc/papers/e2e_planning/bevplanner-admlp-2024.pdf
---

# Is Ego Status All You Need for Open-Loop End-to-End Autonomous Driving?

## Keywords
- bev-planner, ego-mlp, ad-mlp, ego-status-leakage, nuscenes, ccr-metric, open-loop-planning, label-leakage

## TL;DR
The authors investigate why simple MLP baselines (AD-MLP) rival sophisticated end-to-end stacks (UniAD, VAD) on nuScenes open-loop planning, and find the cause is ego-status leakage combined with a dataset where 73.9% of scenes are straight driving. They reproduce AD-MLP without history-trajectory GTs (Ego-MLP) and show it still matches SOTA on L2 and collision rate, then propose a minimal BEV-Planner that bypasses perception/prediction entirely yet achieves competitive results. They introduce a Curb Collision Rate (CCR) metric using rasterized road boundaries to expose that current metrics fail to penalize off-road trajectories.

## Problem & Motivation
Recent open-loop end-to-end driving methods (UniAD, VAD, ST-P3) report state-of-the-art L2 distance and collision rate on nuScenes and claim that perception, prediction, and planning multi-task learning is responsible. AD-MLP showed an MLP fed only ego status and history GT trajectories matches these systems, but its use of history-trajectory GTs raised label-leakage concerns. The motivating question is whether the apparent superiority of these heavy stacks reflects real planning capability or is an artifact of (a) ego-status shortcut learning, (b) the heavily straight-driving nuScenes distribution, and (c) incomplete metrics that ignore road geometry.

## Innovation Points
- **Ego-MLP reproduction** — A re-implemented AD-MLP variant that drops past-trajectory GTs and uses only ego velocity, acceleration, yaw, and driving command; still matches UniAD/VAD on L2 and collision rate, isolating ego status as the dominant signal.
- **BEV-Planner / BEV-Planner++ baseline** — A minimal pipeline (BEV features → cross-attention with a learnable ego query → MLP → trajectory) trained with a single L1 trajectory loss; no perception annotations (no boxes, tracking IDs, HD maps); ++ variant adds ego status to BEV and planner.
- **Curb Collision Rate (CCR) metric** — Computes collisions between predicted trajectories and rasterized road boundaries (0.1 m grid), penalizing off-road planning that L2 and inter-agent collision rate ignore.
- **Ego-status leakage diagnosis** — Systematic perturbation study on VAD: blanking all camera input barely changes planning output, while perturbing ego velocity (e.g., setting it to 100 m/s) catastrophically degrades trajectories — quantifying disproportionate dependence on ego status.
- **nuScenes imbalance audit** — Shows 73.9% of scenes are straight driving; provides L2-ST/L2-LR and Collision-ST/Collision-LR splits separating straight vs. turning commands so that turning-scene gains are not hidden in averages.
- **UniAD post-processing critique** — Demonstrates that UniAD's nonlinear collision-avoidance post-processing reduces inter-agent collisions but markedly increases CCR (off-road risk), exposing a single-objective optimization hazard.

## Model Architecture
BEV-Planner (the paper's proposed baseline):
- Inputs: 6 surround camera images at 256×704; 4-frame history of BEV features.
- Backbone: ResNet-50 image encoder; BEV features at 128×128 covering ~50 m perception range.
- Temporal fusion: Channel-wise concatenation of past 4 BEV timesteps (no feature alignment), then a BEV encoder (from method [14]) squeezes channels to 256.
- Planner head: A learnable ego query Q cross-attends to the fused BEV features B; output passes through MLPs to predict the trajectory τ. Formulation: τ = MLP(attn(q=Q, k=B, v=B)).
- Variants:
  - BEV-Planner (base): no ego status anywhere.
  - BEV-Planner++: ego status concatenated into BEV features and into the ego query before the planner.
  - BEV-Planner+Map: adds a UniAD-style map perception task as an auxiliary head.
- Output: 3-second future ego trajectory at 1/2/3 s waypoints (open-loop).
- Training: 12 epochs on 8 V100 GPUs, batch size 32, learning rate 1e-4. Single L1 trajectory loss; no detection/tracking/HD-map labels.

Ego-MLP (reproduced AD-MLP variant): A small MLP that consumes only ego velocity, acceleration, yaw angle, and driving command, and outputs the future trajectory. No perception, no history-trajectory GTs.

## Benchmark Results
Open-loop planning on nuScenes (Table 1, partial; lower is better):

| ID | Method        | Ego-Status (BEV / Planner) | L2 Avg (m) ↓ | Collision Avg (%) ↓ | CCR Avg (%) ↓ |
|----|---------------|----------------------------|--------------|----------------------|----------------|
| 2  | UniAD (off.)  | x / yes                    | 0.66         | 0.62                 | 1.72           |
| 6  | VAD-Base (off.) | x / yes                  | 0.37         | 0.33                 | 2.47           |
| 7  | GoStright     | - / yes                    | 0.83         | 1.08                 | 8.62           |
| 8  | Ego-MLP       | - / yes                    | 0.35         | 0.37                 | 2.93           |
| 10 | BEV-Planner   | x / x                      | 0.55         | 0.59                 | 4.26           |
| 12 | BEV-Planner++ | yes / yes                  | 0.35         | 0.34                 | 3.16           |

Headline: Ego-MLP (no perception, no history GT) matches VAD-Base on L2 (0.35 vs 0.37) and collision (0.37 vs 0.33). BEV-Planner++ ties Ego-MLP at 0.35 L2 / 0.34 collision despite using neither tracking nor HD-map labels.

Key ablations:
- Ego-status perturbation on VAD (Table 2): blanking camera input changes L2 from 0.37 → 0.46 (minor); setting ego velocity to 100 m/s blows L2 up to 208 m and CCR to 27.0% — confirms planning is dominated by ego status.
- Adding map perception to BEV-Planner (Table 3): L2 worsens (0.55 → 0.96) and inter-agent collision worsens (0.59 → 0.89), but CCR improves (4.26 → 2.60). Multi-task perception does not uniformly help.
- Driving-command split (Tables 4–5): adding map perception hurts straight-driving scenes (the dominant 74%) but helps turning scenes (Collision-LR 2.25 → 0.78).
- UniAD post-processing (Table 6): turning P.P. off cuts CCR 7.83% → 1.72% but raises inter-agent collision 0.51% → 0.62% — single-objective optimization creates an off-road hazard.

## Limitations & Open Questions
- All analysis is restricted to nuScenes open-loop; the paper explicitly does not perform closed-loop evaluation, leaving open whether ego-status shortcuts persist when the planner can affect future ego state.
- BEV-Planner is positioned as a diagnostic baseline, not a deployable system — the authors note it lacks adequate constraints and interoperability for real-world use.
- CCR depends on rasterized road boundaries from nuScenes maps that may include traversable boundaries (e.g., parking exits), so it is statistically rather than per-instance accurate.
- The paper does not propose a new training paradigm or dataset; it leaves construction of a more diverse open-loop benchmark and richer evaluation metrics as future work.
- No discussion of whether the diagnosis transfers to other AV datasets (Waymo Open, nuPlan) where ego-status correlation with future trajectory may differ.
