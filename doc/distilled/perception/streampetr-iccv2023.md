---
paper_id: 2023-streampetr
title: "Exploring Object-Centric Temporal Modeling for Efficient Multi-View 3D Object Detection"
authors: [Shihao Wang, Yingfei Liu, Tiancai Wang, Ying Li, Xiangyu Zhang]
year: 2023
venue: ICCV 2023
arxiv_id: "2303.11926"
url: https://arxiv.org/abs/2303.11926
primary_category: perception
secondary_categories: [e2e_planning]
keywords: [streampetr, object-centric-temporal, sparse-query, memory-queue, motion-aware-ln, nuscenes, multi-view-3d-detection]
one_line_summary: Object-centric temporal modeling that propagates sparse object queries through a FIFO memory queue plus motion-aware layer normalization for efficient long-sequence multi-view 3D detection.
distilled_at: 2026-05-02
source_pdf: doc/papers/perception/streampetr-iccv2023.pdf
---

# Exploring Object-Centric Temporal Modeling for Efficient Multi-View 3D Object Detection

## Keywords
- streampetr, object-centric-temporal, sparse-query, memory-queue, motion-aware-ln, nuscenes, multi-view-3d-detection

## TL;DR
Existing temporal multi-view 3D detectors fuse either dense BEV features (heavy receptive-field requirements, poor moving-object modeling) or perspective features (repeated cross-attention over multi-frame image tokens). The authors introduce StreamPETR, an online framework built on PETR-series sparse queries that propagates only a small set of object queries through a FIFO memory queue and a propagation transformer, with a motion-aware layer normalization (MLN) encoding ego pose, time interval, and velocity. With a ViT-Large backbone, StreamPETR reaches 67.6% NDS / 65.3% AMOTA on nuScenes test, comparable to LiDAR-based CenterPoint and is the first online camera-only method to do so.

## Problem & Motivation
Recent multi-view 3D detectors model temporal context two ways. (1) BEV temporal methods (BEVFormer, BEVDet4D, SOLOFusion) warp dense BEV grids from history to current frame; the highly structured BEV features need large receptive fields to handle moving objects, so long-horizon fusion is expensive. (2) Perspective temporal methods (PETRv2, Sparse4D, DETR4D) cross-attend object queries to multi-frame image features, which is convenient for moving objects but cost grows with history length. The paper argues that sparse object queries can themselves serve as the hidden state of temporal propagation, giving cheap long-term modeling with global receptive fields.

## Innovation Points
- **Object-centric temporal paradigm** — historical state is carried by a small set of sparse object queries instead of dense BEV maps or repeated multi-frame image attention; cost is roughly constant in horizon length.
- **Memory queue (FIFO, N x K)** — stores top-K (K=256) foreground queries from each of N=4 recent frames along with relative time interval, context embedding, object center, velocity, and ego-pose matrix; recurrently updated frame by frame.
- **Propagation transformer with hybrid attention** — replaces the DETR self-attention with attention between current queries and concatenated memory queries, performing temporal interaction and duplicate removal at negligible cost (memory queries used only as K/V).
- **Motion-aware Layer Normalization (MLN)** — conditional LN whose affine parameters (gamma, beta) are predicted from ego pose, timestamp, and velocity; implicitly compensates ego and object motion, outperforming explicit motion compensation in their ablation.
- **Query propagation across frames** — top-K foreground queries from the previous frame are concatenated with randomly initialized queries to seed the next frame, transferring spatial/contextual priors directly.
- **Streaming online inference** — frame-by-frame predictions on streaming video with constant per-frame cost; demonstrated extensibility by plugging the same scheme into DETR3D (Stream-DETR3D, +4.9% mAP / +6.8% NDS over DETR3D).

## Model Architecture
- Inputs: multi-view surround camera frames from streaming video; nuScenes 6 cameras at 2 Hz, key-frames only.
- Image encoder: 2D backbone (ResNet-50 / ResNet-101 / V2-99 / ViT-Large) producing perspective features F_2d; auxiliary 2D supervision inherited from Focal-PETR.
- Memory queue: N x K = 4 x 256 entries storing per-query {time interval delta_t, context embedding Q_c, center Q_p, velocity v, ego-pose matrix E}; FIFO update with the top-K classification-score queries pushed in each frame.
- Propagation transformer (6 layers), each layer:
  1. MLN re-normalizes memory queries using (E_{t-1}^{t}, v, delta_t); centers Q_p are explicitly aligned to current frame via the ego-pose product.
  2. Hybrid attention between current queries (Q) and concatenated [current, propagated, memory] queries (K, V) — replaces vanilla self-attention.
  3. Cross-attention between current queries and current image tokens F_2d with PETR-style 3D position encoding.
- Initial query for current frame = concat(randomly initialized queries, propagated top-K queries from t-1).
- Output: PETR-style detection head emitting 3D boxes b = (x, y, z, l, w, h, theta, v_x, v_y, cls).
- Default config in main results: 644 random + 256 propagated queries; trained 24 (ablation) / 60 epochs (main); AdamW, batch 16, base LR 4e-4, cosine schedule, no CBGS.

## Benchmark Results
**nuScenes val (R50, 256 x 704, 8 frames):**
| Method | mAP up | NDS up | FPS up |
|---|---|---|---|
| BEVFormerv2 (R50) | 0.423 | 0.529 | not reported |
| SOLOFusion (16+1) | 0.427 | 0.534 | 11.4 |
| **StreamPETR** | **0.432** | **0.540** | **27.1** |
| StreamPETR (300 rand + 128 prop) | 0.450 | 0.550 | 31.7 |

**nuScenes val (R101-DCN, 512 x 1408):**
| Method | mAP | NDS | FPS |
|---|---|---|---|
| SOLOFusion (R101, 16+1) | 0.483 | 0.582 | not reported |
| **StreamPETR (R101)** | **0.504** | **0.592** | 6.4 |

**nuScenes test (no TTA):**
- StreamPETR with V2-99 (640 x 1600): 55.0 mAP / 63.6 NDS / 23.9 mASE / 24.1 mAVE.
- StreamPETR with ViT-L (800 x 1600): **62.0 mAP / 67.6 NDS / 25.8 mAOE / 23.6 mAVE** — first camera-only online method comparable to CenterPoint LiDAR (60.3 / 67.3).

**3D tracking, nuScenes test:** AMOTA 0.653, AMOTP 0.876, RECALL 73.3% — surpasses ByteTrackv2 by +8.9 AMOTA and exceeds CenterPoint AMOTA.

**Waymo Open val (R101):** mAPL 0.399, mAP 0.553, mAPH 0.517 — beats BEVFormer++ and MV-FCOS3D++ on official metrics.

**Ablations (val):**
- Training-frame length (Table 5): 1 -> 38.6 NDS (single frame); scales monotonically; 8 frames in video test = 50.5 NDS, 12 frames only marginal (50.7 W / 50.9 W).
- Memory size (Table 7): 0 frames 37.2 NDS -> 1 frame 50.1 NDS -> 2 frames 50.5 NDS (saturates ~1 second / 2 frames).
- MLN (Table 6): turning on LN-conditioned ego-pose adds +1.8 NDS over no-MLN; adding time + velocity adds another +0.4. Explicit motion compensation underperforms MLN.
- Perspective vs. object memory (Table 8): object-centric beats perspective memory on both speed (27.1 vs 18.9 FPS) and accuracy (50.5 vs 49.6 NDS); combining the two does not improve further.

## Limitations & Open Questions
- Failure cases on remote objects (>30 m): many false positives / duplicated predictions for distant targets, a common camera-only weakness (paper Sec. 5.5).
- Moving-object detection still lags static detection by a notable margin even with temporal modeling.
- Memory queue saturates at ~1 second / 2 frames; scaling memory to genuinely long horizons (tens of seconds, occluded re-identification) is not demonstrated.
- ViT-L training cost is large (Flash Attention used to fit 27 GB GPU memory); deployment cost on vehicle hardware not addressed.
- Evaluation is open-loop detection / tracking only; no closed-loop or downstream-planning study.
