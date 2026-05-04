---
paper_id: 2022-petr
title: "PETR: Position Embedding Transformation for Multi-View 3D Object Detection"
authors: [Yingfei Liu, Tiancai Wang, Xiangyu Zhang, Jian Sun]
year: 2022
venue: ECCV 2022
arxiv_id: "2203.05625"
url: https://arxiv.org/abs/2203.05625
primary_category: perception
secondary_categories: []
keywords: [3d-object-detection, multi-view, position-embedding, detr, transformer, nuscenes, end-to-end]
one_line_summary: Encodes 3D coordinates into 2D image features as a 3D position embedding so DETR-style object queries directly perform 3D detection without 2D-to-3D projection or feature sampling.
distilled_at: 2026-05-02
source_pdf: doc/papers/perception/petr-eccv2022.pdf
---

# PETR: Position Embedding Transformation for Multi-View 3D Object Detection

## Keywords
- 3d-object-detection, multi-view, position-embedding, detr, transformer, nuscenes, end-to-end

## TL;DR
DETR3D performs multi-view 3D detection by repeatedly projecting predicted 3D reference points back into 2D images to sample features, which is sensitive to projection error and limited to local features. PETR instead encodes 3D world-space coordinates of the camera frustum into 2D image features as a "3D position embedding," producing 3D position-aware features that DETR-style object queries attend to directly. On nuScenes test set with VoVNetV2 backbone and external data, PETR reaches 50.4% NDS / 44.1% mAP, the first vision-only method to surpass 50% NDS.

## Problem & Motivation
DETR3D (the prior DETR-style multi-view 3D detector) suffers from three concrete issues with its 2D-to-3D projection pipeline: (1) predicted 3D reference points may be inaccurate, so sampled 2D features land outside the object region; (2) only the feature at the projected point is collected, preventing global representation learning; (3) the explicit projection-and-sample procedure is awkward for deployment. BEV-based methods (BEVDet, etc.) avoid this but introduce Z-axis error and lose the end-to-end DETR spirit. The authors want a DETR-style framework that gives queries 3D awareness without the online 2D-to-3D transformation.

## Innovation Points
- **3D Position Embedding (3D PE)** — encodes per-pixel 3D world coordinates (derived from camera frustum + intrinsics/extrinsics) into a position embedding added to the 2D image feature, turning multi-view 2D features into 3D position-aware features.
- **3D Coordinates Generator** — discretizes the shared camera frustum into a (W_F, H_F, D) meshgrid, applies the inverse camera matrix per view, and normalizes to a fixed RoI (e.g. [-61.2, 61.2] m XY, [-10, 10] m Z) to get 3D world coords for every pixel of every view.
- **3D Position Encoder** — small MLP (1x1 ReLU 1x1) on the D*4-dim coordinate stack maps 3D coords to a position embedding that is *added* to the 1x1-projected 2D feature; the result is flattened and fed to the decoder.
- **Learned 3D anchor queries** — object queries are produced by feeding learnable 3D anchor points (uniformly initialized in normalized 3D space) through a 2-layer MLP; this beat DETR-style learnable parameters and BEV-grid anchors in their ablations.
- **Offline-friendly inference** — because the 3D PE depends only on camera geometry, it can be precomputed once and served as a static input, removing per-frame projection from the runtime path.

## Model Architecture
- N surround camera images (nuScenes: 6 views) → backbone (ResNet-50/101, Swin-T/S/B, or VoVNetV2) → 2D features F^{2d} from upsampled+fused C5/C4 stage at 1/16 resolution.
- 3D coordinates generator: discretize camera frustum into (W_F, H_F, D=64 LID-spaced) meshgrid → invert camera matrix per view → normalize to RoI → yields P^{3d} of shape (D*4, H_F, W_F) per view.
- 3D position encoder: P^{3d} → MLP (FC-ReLU-FC) → 3D PE; 2D feat → 1x1 conv → reduced 2D feat; element-wise add → 3D position-aware features F^{3d}; flatten across views.
- Query generator: 1500 learnable 3D anchor points in normalized 3D space → 2-layer MLP → initial object queries Q_0.
- Transformer decoder: L standard DETR decoder layers; queries attend (multi-head attention + FFN) to flattened 3D position-aware features.
- Heads: per-query classification (focal loss) + 3D box regression (L1 on offsets relative to anchor); Hungarian matching.
- Training: AdamW, lr 2e-4 cosine, 24 epochs (2x), batch 8 on 8x V100, multi-scale shorter side in [640, 900], no TTA at inference.

## Benchmark Results

**nuScenes test set (Tab. 2):**
| Method            | Backbone | NDS ↑ | mAP ↑ |
|-------------------|----------|-------|-------|
| FCOS3D†           | Res-101  | 0.428 | 0.358 |
| PGD‡              | Res-101  | 0.448 | 0.386 |
| DETR3D*‡          | V2-99    | 0.479 | 0.412 |
| BEVDet*           | V2-99    | 0.488 | 0.424 |
| **PETR (Swin-B)** | Swin-B   | 0.483 | **0.445** |
| **PETR\*** (ext.) | V2-99    | **0.504** | 0.441 |

(* = external data, ‡ = test-time augmentation, † = init from FCOS3D backbone.)

**nuScenes val set (Tab. 1):** PETR with Res-101 1408x512 reaches 0.421 NDS / 0.357 mAP; with Swin-T 1408x512 reaches 0.431 NDS / 0.361 mAP. PETR† (FCOS3D-init) Res-101 1600x900 reaches 0.442 NDS / 0.370 mAP, beating DETR3D† (0.434 / 0.349) under matched settings.

**Key ablations (ResNet-50, single-level C5, no CBGS, Tab. 3 / Tab. 5):**
- 2D PE only (DETR-style): 0.069 mAP. Add multi-view prior: 0.089 mAP. **3D PE alone: 0.305 mAP** (showing 3D PE is the primary driver). All three combined: 0.309 mAP.
- 3D PE network: simple 1x1-ReLU-1x1 MLP works (0.309 mAP); two 3x3 convs do not converge (3x3 destroys 2D-3D correspondence).
- Fusion: Add (0.359 NDS) ≈ Concat (0.358) > Multiply (0.357).
- Anchors: Learned-3D (0.359 NDS) > Fix-3D (0.343) > Fix-BEV (0.337); DETR-style "None" fails to converge.
- Anchor count: 1500 best (0.359 NDS) vs 600 (0.339).
- Speed (Fig. 5b, V100): R50 384x1056 at 10.7 FPS; R101 900x1600 at 1.7 FPS; vs BEVDet 4.2 FPS at 1056x384 (on stronger 3090).

## Limitations & Open Questions
- Slower convergence than DETR3D in early epochs; needs the full 24-epoch (2x) schedule for global attention to learn the 3D correlation.
- High-resolution / large-backbone configurations are slow (R101 at 1600x900 runs at 1.7 FPS), and the strongest 50.4% NDS result requires the V2-99 backbone with external data.
- Failure modes shown: small/distant objects missed, and visually similar vehicle classes (truck vs bus, etc.) get misclassified.
- Single-frame only — no temporal context, which later works (PETRv2, BEVFormer temporal) explicitly add.
- 3D PE assumes accurate, fixed camera intrinsics/extrinsics; robustness to calibration drift is not evaluated.
