---
paper_id: 2023-uniad
title: "Planning-oriented Autonomous Driving"
authors: [Yihan Hu, Jiazhi Yang, Li Chen, Keyu Li, Chonghao Sima, Xizhou Zhu, et al.]
year: 2023
venue: CVPR 2023 (award candidate)
arxiv_id: "2212.10156"
url: https://arxiv.org/abs/2212.10156
primary_category: e2e_planning
secondary_categories: [perception]
keywords: [unified-pipeline, query-based, trackformer, motionformer, occformer, bev, nuscenes]
one_line_summary: Planning-oriented end-to-end driving pipeline that unifies tracking, mapping, motion, occupancy and planning via shared query interfaces over BEV features on nuScenes.
distilled_at: 2026-05-02
source_pdf: doc/papers/e2e_planning/uniad-2023.pdf
---

# Planning-oriented Autonomous Driving

## Keywords
- unified-pipeline, query-based, trackformer, motionformer, occformer, bev, nuscenes

## TL;DR
Modular AV stacks (separate detection / tracking / mapping / motion / planning) accumulate errors across hand-crafted interfaces, and naive multi-task learning suffers negative transfer. UniAD unifies five driving tasks (tracking, online mapping, motion forecasting, occupancy prediction, planning) into a single transformer-decoder pipeline whose modules talk through learnable queries over a shared BEV feature, all jointly optimized toward planning. On nuScenes, UniAD outperforms task-specific and prior end-to-end baselines across every metric, cutting planning L2 by 51.2% and collision rate by 56.3% versus ST-P3.

## Problem & Motivation
Industry stacks deploy standalone models per task, which leak information at module boundaries and accumulate errors. Naive multi-task learning (MTL) with shared backbone + per-task heads risks negative transfer. Pure "tabula-rasa" end-to-end learners (predict trajectory directly from pixels) lack interpretability and safety guarantees, especially in dynamic urban scenes. The authors argue prior end-to-end attempts (PnPNet, ViP3D, P3, MP3, ST-P3, LAV) miss components needed for safe planning. The central design question: which preceding tasks are required, and how should they be coordinated, in service of planning?

## Innovation Points
- **Planning-oriented philosophy** — explicitly orders perception and prediction tasks toward the planner as the ultimate objective; selection and ordering of modules is justified by ablations rather than convenience.
- **Query-based unified interface** — every module (TrackFormer, MapFormer, MotionFormer, OccFormer, Planner) is a transformer decoder that exchanges learnable queries instead of bounding-box / map-element protocols, giving a larger receptive field and softening compounding error.
- **MotionFormer with scene-centric joint prediction** — predicts top-k multi-modal trajectories for all agents in one forward pass, with three interaction types (agent-agent, agent-map, agent-goal-point) and a deformable-attention goal refinement; uses both scene-level and agent-level k-means anchors plus a non-linear smoother for kinematic plausibility.
- **OccFormer with pixel-agent attention** — produces instance-aware future BEV occupancy by dense pixel queries cross-attending to agent features under an agent-occupied attention mask, dispensing with hand-crafted clustering post-processing.
- **Occupancy-aware Planner** — converts navigation command into a learnable embedding fused with the ego-vehicle query from MotionFormer, and refines the predicted trajectory at inference via a Newton-style optimizer that pushes the trajectory away from OccFormer-predicted occupied cells (collision term + L2 anchor).
- **Ego-vehicle query threading** — a dedicated ego query is propagated from TrackFormer through MotionFormer into the Planner, so the self-driving car is modeled jointly with other agents in a scene-centric coordinate frame.

## Model Architecture
- Inputs: multi-view surround camera images on nuScenes (no LiDAR, no HD map, no predefined route).
- Backbone: image feature extractor + BEVFormer-style encoder producing a unified BEV feature B.
- TrackFormer: detection queries + persistent track queries cross-attend to B; performs joint detection and multi-object tracking without non-differentiable post-processing; outputs Q_A for N_a valid agents and an explicit ego-vehicle query.
- MapFormer: panoptic-segmentation-style queries (Panoptic SegFormer) over B; lanes/dividers/crossings as things, drivable area as stuff; updated map queries Q_M passed to MotionFormer.
- MotionFormer: N stacked layers; per-layer captures agent-agent (MHSA on Q), agent-map (MHCA against Q_M) and agent-goal (deformable attention on B around predicted endpoint) interactions; queries combine context Q_ctx with positional encoding of (scene anchor I^s, agent anchor I^a, current position, predicted endpoint); outputs top-k trajectories per agent {x_{i,k}} in R^{T x 2}.
- OccFormer: T_o sequential blocks operating at 1/4 BEV resolution downsampled to 1/8 for attention; per timestep fuses agent feature G^t (track query + position + max-pooled motion query) with dense scene state F^{t-1} via masked cross-attention (agent-occupied mask); upsamples to H x W; instance-level future occupancy via matmul of agent-level feature U^t with decoded scene feature F^t_dec.
- Planner: takes ego query from MotionFormer, fuses it with one of three learnable command embeddings (turn left / right / keep forward) to form a "plan query", attends to BEV B, decodes future waypoints; at inference runs Newton optimization with cost f(tau) = lambda_coord ||tau - tau_hat||_2 + lambda_obs * sum_t D(tau_t, O_hat^t) using OccFormer's binary occupancy.
- Training: two-stage; first jointly train perception (track + map) for ~6 epochs, then end-to-end train all modules for 20 epochs. Bipartite (DETR-style) shared matching used in tracking and online mapping; matches reused downstream so motion/occupancy operate on the same instance set.
- Output: future ego trajectory (planning horizon up to 3 s on nuScenes) with collision-aware refinement.

## Benchmark Results
Dataset: nuScenes validation set; vision-only.

**Planning (headline result, Table 7) — L2 (m) and Collision Rate (%) lower is better:**
| Method | L2 1s | L2 2s | L2 3s | L2 avg | Col 1s | Col 2s | Col 3s | Col avg |
|--------|-------|-------|-------|--------|--------|--------|--------|---------|
| ST-P3 | 1.33 | 2.11 | 2.90 | 2.11 | 0.23 | 0.62 | 1.27 | 0.71 |
| **UniAD** | **0.48** | **0.96** | **1.65** | **1.03** | **0.05** | **0.17** | **0.71** | **0.31** |

The paper highlights a 51.2% reduction in average L2 and 56.3% reduction in average collision rate vs. ST-P3, and reports outperforming several LiDAR-based baselines (NMP, SA-NMP, FF, EO).

**Other tasks (single trained UniAD):**
- Multi-object tracking (Table 3): AMOTA 0.359, IDS 906; +6.5 / +14.2 AMOTA over MUTR3D / ViP3D respectively.
- Online mapping (Table 4): Lanes IoU 31.3 (+7.4 over BEVFormer-reimpl); Drivable 69.1; Divider 25.7; Crossing 13.8.
- Motion forecasting (Table 5): minADE 0.71 m, minFDE 1.02 m, MR 0.151, EPA 0.456; reduces minADE by 38.3% / 65.4% over PnPNet-vision / ViP3D.
- Occupancy prediction (Table 6): IoU-near 63.4, IoU-far 40.2, VPQ-near 54.7, VPQ-far 33.5; +4.0 / +2.0 IoU-near over FIERY / BEVerse.

**Key ablations:**
- Joint-task ablation (Table 2): naive MTL baseline (ID-0) reaches L2 avg 1.154 / col avg 0.941; the full UniAD (ID-12) reaches 1.004 / 0.430. Removing either motion or occupancy alone (ID-10/11) is worse than including both, supporting the claim that both prediction tasks are needed for safe planning.
- MotionFormer (Table 8): scene-level anchor is the single biggest contributor (-15.8% minADE, -11.2% minFDE); goal interaction and ego-query each add further gains; non-linear smoother adds -5.0% minADE / -8.4% minFDE.
- OccFormer (Table 9): pixel-agent attention with the agent-occupied mask plus reuse of the mask feature for instance-level occupancy is best (IoU-n 62.6, VPQ-n 53.2).
- Planner (Table 10): adding BEV cross-attention, collision loss, and occupancy-based optimization successively reduces collision rate from 1.64 to 1.05 average.

## Limitations & Open Questions
- Authors explicitly note coordinating many tasks is non-trivial and computationally heavy, especially with temporal history; lightweight deployment is left for future work.
- Compute / parameter counts and inference latency are not reported in the main text.
- Tracking still trails specialized tracking-by-detection systems (e.g. Immortal Tracker AMOTA 0.378 vs UniAD 0.359) and mapping trails some perception-oriented baselines on specific classes; the design trade-off favors planning quality over peak perception accuracy.
- Evaluated only on nuScenes, open-loop, vision-only; no closed-loop simulation. Failure cases concentrated in long-tail scenarios (e.g. large trucks, trailers).
- Planning horizon shown is 3 s; no demonstration of HD-map-free, route-conditioned long-horizon planning.
- Whether incorporating additional tasks (depth, behavior prediction) further helps planning is left open.
