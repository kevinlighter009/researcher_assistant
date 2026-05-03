---
paper_id: 2025-goalflow
title: "GoalFlow: Goal-Driven Flow Matching for Multimodal Trajectories Generation in End-to-End Autonomous Driving"
authors: [Zebin Xing, Xingyu Zhang, Yang Hu, Bo Jiang, Tong He, Qian Zhang, Xiaoxiao Long, Wei Yin]
year: 2025
venue: arXiv
arxiv_id: "2503.05689"
url: https://arxiv.org/abs/2503.05689
primary_category: e2e_planning
secondary_categories: [diffusion_decoder]
keywords: [flow-matching, rectified-flow, goal-point, multimodal-trajectory, navsim, single-step-inference, dac-score]
one_line_summary: Constrains rectified-flow trajectory generation with a scored goal point picked from a discretized vocabulary; achieves PDMS 90.3 on Navsim with a single denoising step.
distilled_at: 2026-05-02
source_pdf: doc/papers/e2e_planning/goalflow-2025.pdf
cross_listed_with: doc/distilled/diffusion_decoder/goalflow-2025.md
---

# GoalFlow: Goal-Driven Flow Matching for Multimodal Trajectories Generation in End-to-End Autonomous Driving

## Keywords
- flow-matching, rectified-flow, goal-point, multimodal-trajectory, navsim, single-step-inference, dac-score

## TL;DR
Diffusion-based trajectory decoders for end-to-end driving suffer from trajectory divergence and weak alignment between guidance and scene context, which complicates downstream selection. GoalFlow first picks a single high-quality goal point from a discretized vocabulary using a learned distance + drivable-area scorer, then conditions a rectified-flow trajectory generator on that goal to produce constrained multimodal candidates. On the Navsim benchmark it reaches PDMS 90.3, surpassing TransFuser, UniAD, and PARA-Drive, and remains stable down to a single denoising step.

## Problem & Motivation
Recent end-to-end driving methods increasingly model multimodal trajectory distributions, but two problems persist. (1) Pure diffusion-based generators (e.g. Diffusion-ES) produce highly divergent trajectories with no clear modal boundaries, so a downstream scorer must use HD maps to align candidates with the road network — information often unavailable in end-to-end settings. (2) Methods like MotionDiffuser anchor on the ground-truth endpoint, which over-constrains the prior. Goal-based regression methods (VAD, SparseDrive, GoalGAN) either rely on hand-designed discrete commands or use grid-cell sampling that ignores the goal-point distribution. The authors argue that a single, precisely-localized goal point provides a strong constraint on the generative prior, while still leaving room for multimodal trajectory shapes around it.

## Innovation Points
- **Goal Point Vocabulary** — clusters trajectory endpoints from training data into N=4096 or 8192 candidates (`(x, y, theta)`), avoiding HD-map dependence inspired by VADv2's discretization of trajectory space.
- **Dual-score Goal Point Scorer** — a transformer decoder predicts per-candidate Distance Score (softmax over Euclidean distance to GT endpoint) and Drivable Area Compliance (DAC) Score (binary, via a shadow-vehicle polygon test), aggregated by `w1 log dis + w2 log dac` for selection.
- **Rectified-Flow trajectory decoder conditioned on goal** — uses Liu et al.'s straight-line optimal-transport flow matching, conditioning on BEV features, ego status, and the selected goal embedding; achieves robust performance even at a single denoising step.
- **Shadow-trajectory selection** — when the predicted goal point may be unreliable, a shadow trajectory is generated; if it diverges significantly from the main trajectory, the goal is treated as unreliable and the shadow is used instead.
- **Trajectory Scorer without simulation** — replaces Diffusion-ES/SparseDrive's kinematic collision simulation with a lightweight goal-distance + ego-progress trade-off `f = -lambda1 Phi(f_dis) + lambda2 Phi(f_pg)`, cutting selection cost.

## Model Architecture
Three modules over fused camera+LiDAR input:

- **Perception Module** — TransFuser-style fusion: 3 front-area camera views concatenated (`I in R^{3xHxW}`) and LiDAR tensor (`L in R^{KxKx3}`) pass through separate backbones; multi-layer transformer fuses them into BEV feature `F_bev`. Auxiliary supervision: HD-map cross-entropy loss (`L_HD`), 3D bbox classification (`L_bbox`), 3D bbox regression (`L_loc`); weights `w1=10.0, w2=1.0, w3=10.0`.
- **Goal Point Construction Module** — Vocabulary `V = {g_i}` with N=4096 or 8192 endpoints. Vocab encoder + ego encoder produce `F_v`, `F_ego`; transformer decoder uses `F_v + F_ego` as query, `F_bev` as K/V; two MLP heads emit `delta_dis` and `delta_dac` per candidate. Goal `g*` = argmax of fused score.
- **Trajectory Planning Module** — Rectified-flow network `G` (N transformer layers). Inputs: time embedding `F_t`, noisy trajectory encoding `F_traj`, environment encoding `F_env = E_env(Q, F_BEV+F_ego, F_BEV+F_ego)`, goal embedding `F_goal`. Predicts shift `v_t = tau^norm - x_0` along the linear interpolation `x_t = (1-t)x_0 + t tau^norm`, with `x_0 ~ N(0, sigma^2 I)`, `sigma=0.1`. Generates 128/256 candidate trajectories via classifier-free guidance; trajectory scorer picks the optimal one.
- **Output** — 4-second trajectory at 2 Hz, interpolated by an LQR controller to 10 Hz for Navsim closed-loop scoring.
- **Training scale** — 4 nodes x 8 RTX 4090/3090 GPUs; trained on OpenScene/Navsim (1192 trainval scenarios).

## Benchmark Results
**Navsim Test (PDM Score):**
| Method            | S_NC | S_DAC | S_TTC | S_CF | S_EP | PDMS |
|-------------------|------|-------|-------|------|------|------|
| TransFuser        | 97.7 | 92.8  | 92.8  | 100  | 79.2 | 84.0 |
| UniAD             | 97.8 | 91.9  | 92.9  | 100  | 78.8 | 83.4 |
| PARA-Drive        | 97.9 | 92.4  | 93.0  | 99.8 | 79.3 | 84.0 |
| **GoalFlow**      | **98.4** | **98.3** | **94.6** | 100 | **85.0** | **90.3** |
| GoalFlow (oracle goal) | 99.8 | 97.9 | 98.6 | 100 | 85.4 | 92.1 |
| Human             | 100  | 100   | 100   | 99.9 | 87.5 | 94.8 |

The +5.5 jump in DAC and +5.7 in EP over the second-best baseline are attributed to the goal-point constraint keeping trajectories drivable while enabling higher progress.

Ablations:
- Removing distance-score and DAC-score guidance (M0, base flow matching only): PDMS drops to 85.6 (-4.7).
- Adding distance score map (M1): PDMS 88.5; adding DAC score (M2): 89.4; adding trajectory scorer (M3): 90.3.
- Inference steps T = {20, 10, 5, 1}: PDMS 89.9 / 90.1 / 90.3 / 88.9 — single-step decoding only loses 1.6% from optimum at ~6% of the runtime (10.4 ms vs 177.8 ms).
- Initial-noise sigma = 0.05/0.1/0.2/0.3 → PDMS 90.1 / 90.3 / 49.0 / 18.8 — model collapses for sigma > 0.1.
- Scaling Trajectory Planning hidden dim 256 → 1024 with V2-99 backbone: PDMS 86.5 → 89.4.

## Limitations & Open Questions
- Closed-loop evaluation limited to Navsim (non-reactive simulation over OpenScene); no real-vehicle or reactive-agent results.
- Goal vocabulary is built by clustering training-set endpoints (N=4096/8192) — generalization to out-of-distribution scenes (e.g. unusual road geometries) is not assessed.
- Performance is highly sensitive to initial-noise sigma (collapse beyond 0.1); sensitivity to other hyperparameters such as score weights `w1, w2`, `lambda1, lambda2` is not reported.
- DAC-Score uses a shadow-vehicle polygon over the predicted drivable-area polygon `D`; quality depends on the perception module's HD-map auxiliary head, whose failure modes are not analyzed.
- Despite the "goal-driven" framing, the trajectory scorer trades off only goal distance vs ego progress — interactions with surrounding agents are not modeled at selection time, unlike SparseDrive/Diffusion-ES.
