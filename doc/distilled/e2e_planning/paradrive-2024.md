---
paper_id: 2024-paradrive
title: "PARA-Drive: Parallelized Architecture for Real-time Autonomous Driving"
authors: [Xinshuo Weng, Boris Ivanovic, Yan Wang, Yue Wang, Marco Pavone]
year: 2024
venue: CVPR 2024
arxiv_id: null
url: https://xinshuoweng.github.io/paradrive/
primary_category: e2e_planning
secondary_categories: [perception]
keywords: [parallel-architecture, bev-features, multi-task-learning, modular-e2e, nuscenes, runtime-efficiency, design-space]
one_line_summary: Fully parallel end-to-end modular AV stack co-trained on shared BEV features; matches/beats UniAD/VAD on nuScenes planning while running ~2.77x faster.
distilled_at: 2026-05-02
source_pdf: doc/papers/e2e_planning/paradrive-2024.pdf
---

# PARA-Drive: Parallelized Architecture for Real-time Autonomous Driving

## Keywords
- parallel-architecture, bev-features, multi-task-learning, modular-e2e, nuscenes, runtime-efficiency, design-space

## TL;DR
Recent end-to-end modular AV stacks (UniAD, VAD, OccNet) entangle perception, prediction, and planning via sequential or hybrid inter-module connections, leaving the design space (module necessity, placement, information flow) under-explored and runtime-slow. The authors systematically ablate this design space on nuScenes and propose PARA-Drive, a fully parallel architecture in which mapping, motion prediction, occupancy prediction, and planning are co-trained on a shared BEV feature map with no inter-module dependencies. PARA-Drive matches state-of-the-art planning (up to 28.8% L2 reduction and 43.3% collision-rate reduction over prior work), preserves perception/prediction quality, and achieves a 2.77x runtime speed-up over UniAD by deactivating auxiliary modules at inference.

## Problem & Motivation
Prior end-to-end modular stacks (UniAD CVPR'23, VAD ICCV'23, OccNet ICCV'23) differ widely in (a) which modules they include (e.g., occupancy yes/no, semantic vs. vectorized maps), (b) how they are placed (sequential, hybrid, parallel), and (c) what flows between them (compact outputs vs. high-dim latent queries). No prior work systematically studies these axes; meanwhile sequential dependencies hurt runtime and can propagate noisy intermediate outputs (e.g., noisy lane queries from a 1st-stage mapping head). Evaluation methodology is also inconsistent across UniAD/VAD/AD-MLP (averaging conventions, pedestrian filtering, frame masking, axis-aligned ego boxes, coarse BEV grids), making prior comparisons unreliable.

## Innovation Points
- **Systematic design-space study** — three axes: module necessity, module placement, and information flow; ablated exhaustively on top of UniAD as a base.
- **Standardized evaluation protocol** — fixes averaging-over-time, pedestrian inclusion, frame-masking, oriented ego bounding boxes, and a finer 1000x1000 BEV grid (vs. 200x200) to remove false-positive collisions; adds map-compliance metrics (off-road, off-lane) and a 686-frame "targeted" turning/lane-change subset of the nuScenes val set.
- **Parallel modular architecture (PARA-Drive)** — mapping, motion prediction, occupancy prediction, and planning all consume BEV features in parallel via cross-attention with no module-to-module edges.
- **Operational independence at inference** — auxiliary heads (mapping, motion, occupancy) can be deactivated at runtime while planning continues, enabling near-real-time speed without retraining.
- **Empirical insight on redundancy** — modules that are redundant under sequential placement (e.g., motion vs. occupancy prediction) become complementary under parallel co-training of BEV features.

## Model Architecture
- Inputs: sequence of surround camera images + ego state (CAN bus: velocity, acceleration, angular velocity), history trajectories, and a high-level command.
- Backbone: BEVFormerV2-t1 with R50 (also evaluated with R101); one frame of historical BEV features kept in memory for temporal context.
- Shared representation: BEV feature map.
- Four parallel heads, each with its own learnable query set, all attending to the BEV features:
  - Online mapping: Panoptic Segformer producing a 4-channel semantic BEV map (road boundary, lane divider, pedestrian crossing, drivable area). Trained with L1 + Dice + GIoU.
  - Tracking + motion prediction: query-based, sparse object-level outputs; Hungarian matching with NLL + Dice + BCE losses; motion module also consumes tracked-object boxes and latent features.
  - Occupancy prediction: scene-level probabilistic BEV occupancy map with self-attention between agents.
  - Motion planning: planning query (learnable) concatenated with the high-level-command embedding (and optionally CAN-bus features), cross-attends to the BEV map, then MLPs regress the future ego trajectory.
- Output: 3-second future ego trajectory at 2 Hz on nuScenes (L2 + collision evaluated at 1s/2s/3s).
- No inter-module edges (information flow happens implicitly through tokenized BEV features); auxiliary heads can be turned off at inference.

## Benchmark Results
Dataset: nuScenes val set, under the authors' standardized evaluation methodology. Headline numbers (Table 6, Ave_all unless noted):

**Planning, val set, no ego-state input:**
| Method        | L2 (m) Ave_all ↓ | Col. Rate (%) Ave_all ↓ |
|---------------|------------------|--------------------------|
| UniAD         | 0.8317           | 0.40                     |
| VAD           | 0.7192           | 0.21                     |
| **PARA-Drive**| **0.5574**       | **0.17**                 |

**Planning, val set, with ego state (CAN bus + history):**
| Method        | L2 Ave_all ↓ | Col. Rate Ave_all ↓ | Map Comp. Off-Lane ↓ |
|---------------|--------------|----------------------|----------------------|
| AD-MLP        | 0.6632       | 0.20                 | 2.45                 |
| **PARA-Drive+**| **0.4939**  | **0.13**             | **0.78**             |

Reported gains over prior work: up to 28.8% L2 reduction and 43.3% collision-rate reduction (abstract / Sec. 1).

**Targeted (turning / lane-change) scenarios, no ego state:** PARA-Drive Ave_all L2 = 0.9082, Col. Ave_1,2,3s = 0.34 (vs. UniAD 1.1594 / 0.45, VAD 1.0840 / 0.39).

**Perception & prediction (Table 7):** with the same R101 backbone, PARA-Drive matches or slightly exceeds UniAD on detection (mAP 0.37 vs. 0.38, NDS 0.48 vs. 0.50), motion prediction (minADE 0.71 vs. 0.73), mapping (IoU-real 0.71 vs. 0.67), and occupancy (VPQ-n 55.6 vs. 52.8) — i.e., parallelizing does not degrade upstream tasks.

**Runtime:** 2.77x speed-up vs. UniAD-base (compute mostly in the backbone; further gains projected with a lighter R50-tiny).

Key ablations (Sec. 3.3):
- Removing edges (1)+(2) (mapping->motion, mapping-query->planning) on top of UniAD already improves planning (the "improved baseline") because lane queries from a 1st-stage mapping head are noisy and TTO is not in training.
- Adding more inter-module edges on top of the improved baseline gives no further gain — supporting the parallel design.
- Removing any single auxiliary head (mapping, occupancy, or motion) hurts planning, confirming all are needed for proper BEV co-training; mapping removal especially harms map-compliance.
- High-dim query passing > compact-output passing when sequential edges are kept, but BEV-only parallel design wins overall.

## Limitations & Open Questions
- Open-loop only on nuScenes; no closed-loop / simulator results (authors flag this as future work).
- Evaluated solely on nuScenes; generalization to other datasets and sensor configs is untested.
- Speed-up of 2.77x is measured on a research stack; embedded-deployment numbers (latency, power) are not reported.
- Despite "operational independence", deactivating auxiliary heads at inference removes the very interpretability signals (maps, occupancy, motion) cited as a benefit; the trade-off curve is not quantified.
- The parallel design's benefit hinges on "proper BEV co-training", but how it scales beyond R50/R101 backbones and beyond four heads is an open question.
