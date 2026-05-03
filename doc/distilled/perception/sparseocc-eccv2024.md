---
paper_id: 2024-sparseocc
title: "Fully Sparse 3D Occupancy Prediction"
authors: [Haisong Liu, Yang Chen, Haiguang Wang, Zetong Yang, Tianyu Li, Jia Zeng, Li Chen, Hongyang Li, Limin Wang]
year: 2024
venue: ECCV 2024
arxiv_id: "2312.17118"
url: https://arxiv.org/abs/2312.17118
primary_category: perception
secondary_categories: []
keywords: [3d-occupancy, sparse-voxel, mask-transformer, mask-guided-sampling, rayiou, occ3d-nuscenes]
one_line_summary: Fully sparse camera-only 3D occupancy network with sparse voxel decoder + mask transformer plus a ray-level RayIoU metric; 34.0 RayIoU at 17.3 FPS on Occ3D-nuScenes.
distilled_at: 2026-05-02
source_pdf: doc/papers/perception/sparseocc-eccv2024.pdf
---

# Fully Sparse 3D Occupancy Prediction

## Keywords
- 3d-occupancy, sparse-voxel, mask-transformer, mask-guided-sampling, rayiou, occ3d-nuscenes

## TL;DR
Prior camera-only 3D occupancy networks build dense W x H x D x C feature volumes that waste compute since >90% of voxels are empty. The authors propose SparseOcc, a fully sparse pipeline: a coarse-to-fine sparse voxel decoder reconstructs geometry, then a Mask2Former-style mask transformer with mask-guided sparse sampling predicts semantic/instance labels - no dense features, no sparse-to-dense module, no global attention. They also introduce RayIoU, a ray-cast metric that fixes inflation/depth-inconsistency issues in voxel mIoU. SparseOcc reaches 34.0 RayIoU at 17.3 FPS on Occ3D-nuScenes, scaling to 35.1 with 16 history frames.

## Problem & Motivation
- Existing camera-only occupancy methods (BEVFormer, BEVDet-Occ, FB-Occ) construct dense 3D volumes (e.g. 200 x 200 x 16 x C), running at only ~2-3 FPS on a Tesla A100; this is wasteful since over 90% of voxels are free space.
- Earlier "sparse" attempts (VoxFormer, TPVFormer) still rely on sparse-to-dense modules or projected representations, so they are not fully sparse.
- The dominant evaluation, voxel-level mIoU with a visible mask, is exploitable: dense models trained with the visible mask predict thicker surfaces and gain +5-15 mIoU without genuinely better geometry. The metric inconsistently penalizes depth errors and reduces occupancy to depth estimation, ignoring scene completion.

## Innovation Points
- **Fully sparse architecture** - no dense 3D features, no sparse-to-dense lifting, no global cross attention; first such design for camera-only 3D occupancy.
- **Sparse voxel decoder** - coarse-to-fine 3-layer decoder that starts from 25 x 25 coarse voxels, doubles resolution each layer, and prunes via top-k or thresholding on predicted occupancy scores; only non-free voxels propagate.
- **Mask transformer with mask-guided sparse sampling** - Mask2Former-style decoder where each query samples a small set of 3D points constrained by the previous layer's predicted mask, projected to multi-view image features and aggregated by adaptive mixing; avoids dense cross attention.
- **Sparse temporal modeling** - warps the 3D sampling reference points back to history timestamps and re-samples 2D image features, enabling multi-frame fusion (up to 16 frames) without dense BEV warping.
- **RayIoU metric** - casts query rays into the predicted volume from 8 LiDAR ego-path positions, scores TP if depth-L1 < threshold (1, 2, 4 m) for the first hit, eliminating thicker-surface hacking and inconsistent depth penalties; reported as the average across thresholds.
- **Class-imbalanced BCE weighting** - loss weight w_c = sum_i M_i / M_c rebalances voxel BCE so dominant classes (ground) do not drown out cars/pedestrians.

## Model Architecture
- Inputs: 6 surround cameras at 704 x 256 (history horizon 1f / 8f / 16f).
- Image encoder: ResNet-50 + FPN (multi-scale 2D features).
- Sparse voxel decoder (3 layers, shared spirit with SparseBEV queries):
  - Layer l keeps K_{l-1} sparse voxel queries with 3D coords and C-dim content.
  - Self-attention -> linear head predicts per-query 3D sampling offsets {(dx, dy, dz)} -> project to multi-view image space -> adaptive mixing -> FFN.
  - Occ head -> per-voxel occupancy score; top-k (or threshold > ~0.7) keeps non-free voxels; 2x upsample (each kept voxel splits into 8) -> next layer.
  - Final K x C sparse voxel embeddings V (with K = 32000, ~5% sparsity << 200 x 200 x 16 = 640000); supervised with BCE on kept voxels using class-balanced weights.
- Mask transformer (3 layers, weights shared, inspired by Mask2Former):
  - N queries Q_c (semantic by default; instance for panoptic) with mask queries Q_m initialized from previous layer mask.
  - MHSA across queries -> mask-guided sparse sampling: randomly pick 3D points inside the previous layer's predicted mask, project to multi-view images, bilinearly sample features.
  - Adaptive mixing + FFN -> updated query embedding.
  - Mask head: MLP turns Q_c into mask embedding M (Q x C), dot-product with sparse voxel embeddings V (K x C) -> per-voxel mask logits (constrained to sparse space). Linear+sigmoid classifier on Q_c -> class.
- Losses: L = L_focal + L_mask (BCE) + L_dice + L_occ (sparse voxel decoder), Hungarian matching as in MaskFormer.
- Outputs: class-labeled sparse 3D occupancy on Occ3D-nuScenes 200 x 200 x 16 grid; panoptic variant uses instance queries and reports RayPQ.
- Training: AdamW, lr 2e-4 cosine, batch size 8, 24 epochs default (48 for the strongest 16f run), Tesla A100 PyTorch fp32 inference.

## Benchmark Results
**Occ3D-nuScenes validation (RayIoU, ResNet-50, 704 x 256):**

| Method                | Frames | Epoch | RayIoU | RayIoU 1m / 2m / 4m | mIoU | FPS |
|-----------------------|--------|-------|--------|---------------------|------|-----|
| BEVFormer (R101, 1600x900) | 4f | 24 | 32.4 | 26.1 / 32.9 / 38.0 | 39.2 | 3.0 |
| BEVDet-Occ            | 2f     | 90    | 29.6   | 23.6 / 30.0 / 35.1  | 36.1 | 2.6 |
| BEVDet-Occ-Long       | 8f     | 90    | 32.6   | 26.6 / 33.1 / 38.2  | 39.3 | 0.8 |
| FB-Occ (CVPR'23 winner) | 16f  | 90    | 33.5   | 26.7 / 34.1 / 39.7  | 39.1 | 10.3 |
| **SparseOcc**         | 8f     | 24    | 34.0   | 28.0 / 34.7 / 39.4  | 30.1 | **17.3** |
| **SparseOcc**         | 16f    | 24    | 35.1   | 29.1 / 35.8 / 40.3  | 30.6 | 12.5 |
| **SparseOcc**         | 16f    | 48    | **36.1** | 30.2 / 36.8 / 41.2 | 30.9 | 12.5 |

Headline: SparseOcc 8f beats FB-Occ by +0.5 RayIoU while being ~1.7x faster and using a much smaller backbone/resolution; the 16f / 48-epoch run reaches 36.1 RayIoU.

Key ablations:
- **Sparse vs dense voxel decoder (Tab. 2):** sparse coarse-to-fine matches dense coarse-to-fine on RayIoU (29.9) but runs at 24.0 FPS vs 6.3 FPS - ~4x speed-up at equal quality.
- **Mask transformer (Tab. 3):** no MT 27.0 -> dense cross-attention MT 28.7 (drops to 16.2 FPS) -> sparse sampling 25.8 -> mask-guided sparse sampling 29.2 RayIoU at 24.0 FPS.
- **Sparsity k (Fig. 8a):** optimal at k = 32k-48k (~5-7.5% of dense voxels); above 48k accuracy drops and speed falls.
- **Temporal frames (Fig. 8c):** RayIoU rises with frames, saturates around 12 frames; FPS falls.
- **Visible-mask training (Tab. 4):** training with the visible mask boosts voxel mIoU by ~15 points but costs ~1 RayIoU on BEVFormer; per-class RayIoU shows background classes (drivable surface, terrain, sidewalk) degrade because the model predicts thicker, closer surfaces (Fig. 9).
- **Panoptic occupancy (Tab. 5):** SparseOcc with instance queries reaches RayPQ 14.1 (10.2 / 14.5 / 17.6 at 1 / 2 / 4 m), reported as the first fully sparse panoptic occupancy baseline.

## Limitations & Open Questions
- **Accumulative pruning errors:** voxels mistakenly discarded in early sparse-decoder layers cannot be recovered later, and mask transformer predictions are confined to the (possibly incomplete) sparse space, leading to inadequate training when ground-truth instances are missing.
- **Voxel mIoU drops vs dense baselines** (30.1 vs 39.1 for FB-Occ); only RayIoU remains competitive - so adoption depends on the community accepting RayIoU.
- **Dataset coverage:** evaluated only on Occ3D-nuScenes; no Occ3D-Waymo, OpenOccupancy, or real-vehicle deployment numbers.
- **Sparsity hyper-parameter k** is dataset-tuned by counting max non-free voxels per sample; thresholding generalizes better but optimal threshold is left to practitioner.
- **Panoptic results (RayPQ 14.1)** are reported without comparison baselines, so absolute quality is hard to judge.
