---
paper_id: 2024-sparsedrive
title: "SparseDrive: End-to-End Autonomous Driving via Sparse Scene Representation"
authors: [Wenchao Sun, et al.]
year: 2024
venue: arXiv
arxiv_id: "2405.19620"
url: https://arxiv.org/abs/2405.19620
primary_category: e2e_planning
secondary_categories: [perception]
keywords: [sparse-query, bev-free, symmetric-perception, parallel-motion-planner, collision-aware-rescore, nuscenes]
one_line_summary: BEV-free sparse-query end-to-end driving stack with symmetric perception (det/track/map) and a parallel motion-planner that beats UniAD on nuScenes with much higher efficiency.
distilled_at: 2026-05-02
source_pdf: doc/papers/e2e_planning/sparsedrive-2024.pdf
---

# SparseDrive: End-to-End Autonomous Driving via Sparse Scene Representation

## Keywords
- sparse-query, bev-free, symmetric-perception, parallel-motion-planner, collision-aware-rescore, nuscenes

## TL;DR
Existing end-to-end driving stacks (UniAD, VAD) build dense BEV features and chain perception, prediction and planning sequentially, which is computationally expensive and ignores ego–agent symmetry. The authors propose SparseDrive, a fully sparse instance-based pipeline with a symmetric perception module (detection / tracking / online mapping) and a parallel motion planner that predicts multi-modal trajectories for ego and surrounding agents jointly, then selects a safe trajectory via a collision-aware rescore module. On nuScenes it cuts L2 by 19.4% and collision rate by 71.4% versus VAD while running 4.1x faster at inference.

## Problem & Motivation
Prior end-to-end driving methods (UniAD, VAD) rely on computationally expensive dense BEV features and adopt a sequential prediction-then-planning design. The authors identify three neglected parallels between motion prediction and planning: (1) interactions among agents (including ego) are bidirectional, but sequential designs ignore the ego's effect on surrounding agents; (2) the ego instance is randomly initialized and lacks the rich semantic/geometric features that surrounding agent queries enjoy; (3) planning is multi-modal under uncertainty, but prior work outputs a single deterministic trajectory. These design choices cap performance and efficiency.

## Innovation Points
- **Sparse-Centric paradigm** — replaces dense BEV features with a fully sparse instance representation (decoupled instance feature + geometric anchor) shared across detection, tracking, mapping, prediction and planning.
- **Symmetric Sparse Perception** — detection and online mapping share a symmetric encoder-decoder structure (deformable aggregation, self/cross attention, FFN, refinement), with tracking handled via Sparse4Dv3-style ID-locking that needs no extra constraints.
- **Parallel Motion Planner** — concatenates ego and agent instances, then runs agent-temporal cross-attention, agent-agent self-attention and agent-map cross-attention to predict multi-modal trajectories for ego and surrounding agents simultaneously.
- **Ego Instance Initialization** — initializes ego features by AveragePool over the smallest front-camera feature map (since ego is in camera blind spot) plus a non-leaking ego-status auxiliary task; supplies semantic/geometric context to the ego query.
- **Hierarchical Planning Selection with collision-aware rescore** — filters multi-modal trajectory proposals by driving command (turn left/right/straight), then zeros the score of trajectories with high predicted collision probability instead of post-optimization.

## Model Architecture
- Inputs: multi-view surround cameras (nuScenes 6-cam) -> image encoder (ResNet-50 for SparseDrive-S at 256x704; ResNet-101 for SparseDrive-B at 512x1408) + neck -> multi-scale feature maps I.
- Symmetric Sparse Perception (Fig. 3): two parallel branches sharing the same decoder structure.
  - Detection/tracking: N_d agent instances = (feature F_d in R^{N_d x C}, anchor B_d in R^{N_d x 11} = {x,y,z,ln w,ln h,ln l,sin yaw,cos yaw,vx,vy,vz}); N_dec decoders (1 non-temporal + N_dec-1 temporal) with deformable aggregation, self/cross-attention, FFN, refinement & classification.
  - Online mapping: N_m map instances with anchor polylines L_m in R^{N_m x N_p x 2}.
  - Tracking: Sparse4Dv3-style ID locking once detection confidence exceeds T_thresh.
- Instance Memory Queue: FIFO of (N_d+1) x H frames for temporal cross-attention.
- Parallel Motion Planner (Fig. 4): ego instance F_e in R^{1xC}, B_e in R^{1x11} initialized from smallest front-cam feature; concatenated with agent instances -> 3 stacked blocks of agent-temporal cross-attention, agent-agent self-attention, agent-map cross-attention.
- Outputs:
  - Multi-modal motion: tau_m in R^{N_d x K_m x T_m x 2} with scores s_m.
  - Multi-modal planning: tau_p in R^{N_c x K_p x T_p x 2} with scores s_p, conditioned on N_cmd=3 driving commands; default K_p = 6 modes, T_p = 3s horizon.
- Hierarchical Planning Selection: pick subset matching driving command, apply collision-aware rescore (zero out colliding proposals), output highest-score trajectory.
- End-to-end loss: L = L_det + L_map + L_motion + L_plan + L_depth (depth as auxiliary task); winner-takes-all for multi-modal heads; two-stage training (perception, then full e2e).
- Trained on 8x RTX 4090 24GB; nuScenes only.

## Benchmark Results
Dataset: nuScenes val (1000 scenes). Two variants: SparseDrive-S (ResNet-50, 256x704) and SparseDrive-B (ResNet-101, 512x1408).

**Planning (Tab. 2b) — primary headline:**
| Method     | L2 Avg (m) | Coll. Rate Avg (%) |
|------------|-----------|---------------------|
| ST-P3      | 2.11      | 0.71                |
| UniAD      | 1.03      | 0.61                |
| VAD        | 0.72      | 0.21                |
| SparseDrive-S | 0.61   | 0.08                |
| **SparseDrive-B** | **0.58** | **0.06**       |

vs. VAD: L2 -19.4%, collision rate -71.4%.

**3D detection (Tab. 1a):** SparseDrive-B 49.6% mAP / 58.8% NDS vs. UniAD 38.0 / 49.8 (+11.6 mAP, +9.0 NDS).
**Tracking (Tab. 1b):** SparseDrive-B AMOTA 0.501 vs. UniAD 0.359 (+14.2), IDS 632 vs. 906 (-30.2%).
**Online mapping (Tab. 1c):** SparseDrive-B 56.2% mAP vs. VAD 47.6 (+8.6).
**Motion prediction (Tab. 2a):** SparseDrive-B minADE 0.60 m, minFDE 0.96 m, MR 13.2%, EPA 0.555 (best among reported methods).
**Efficiency (Tab. 3):** SparseDrive-S vs. UniAD: 7.2x faster training (20 h vs. 144 h on 8 GPUs), 5.0x faster inference (9.0 vs. 1.8 FPS), 85.9 M vs. 125.0 M params. SparseDrive-B: 4.8x faster training, 4.1x faster inference.

Ablations:
- Parallel design (Tab. 4 ID-2): switching to sequential degrades both prediction and collision rate.
- Ego instance initialization (ID-3): random init + zero anchor degrades L2 and collision rate.
- Multi-modal planning (Tab. 6): mode count 1->6 improves L2 0.69->0.61 and collision rate 0.25->0.07; saturates at 6.
- Collision-aware rescore (Tab. 5): drops collision rate 0.12% -> 0.08% with negligible L2 change; UniAD's post-optimization actually worsens collision rate to 0.61%.

## Limitations & Open Questions
- Authors note end-to-end model still trails single-task SOTA on subtasks like online mapping.
- Evaluated only on nuScenes (open-loop); no closed-loop (CARLA / nuPlan / NAVSIM) results.
- Open-loop nuScenes planning metrics (L2, collision rate) are known to be weakly correlated with real driving safety; ego-status leakage concerns are mitigated but not eliminated.
- Trajectory scoring relies on motion-prediction outputs for collision estimation; failure modes when prediction is wrong are not analyzed.
