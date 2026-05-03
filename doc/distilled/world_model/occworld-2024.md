---
paper_id: 2024-occworld
title: "OccWorld: Learning a 3D Occupancy World Model for Autonomous Driving"
authors: [Wenzhao Zheng, Weiliang Chen, Yuanhui Huang, Borui Zhang, Yueqi Duan, Jiwen Lu]
year: 2024
venue: ECCV 2024
arxiv_id: "2311.16038"
url: https://arxiv.org/abs/2311.16038
primary_category: world_model
secondary_categories: [perception, e2e_planning]
keywords: [3d-occupancy, world-model, vqvae, gpt-transformer, 4d-forecasting, motion-planning, nuscenes]
one_line_summary: A self-supervised 3D occupancy world model that jointly forecasts future scene occupancy and ego trajectory using a VQ-VAE tokenizer plus GPT-like spatial-temporal generative transformer.
distilled_at: 2026-05-02
source_pdf: doc/papers/world_model/occworld-2024.pdf
---

# OccWorld: Learning a 3D Occupancy World Model for Autonomous Driving

## Keywords
- 3d-occupancy, world-model, vqvae, gpt-transformer, 4d-forecasting, motion-planning, nuscenes

## TL;DR
Existing autonomous-driving stacks predict future motion at the bounding-box level, missing fine-grained scene structure, and require expensive instance/map labels. The authors propose OccWorld, which tokenizes 3D semantic occupancy with a VQ-VAE and uses a GPT-like spatial-temporal generative transformer to autoregressively forecast future occupancy plus ego trajectory jointly. On nuScenes/Occ3D it reaches 17.14 average mIoU for 4D occupancy forecasting and an L2 of 1.17 m for planning without map or box supervision.

## Problem & Motivation
Conventional perception-prediction-planning pipelines (UniAD, VAD, ST-P3) rely on costly ground-truth labels at every stage (3D boxes, HD maps, tracklets) and only model object-level motion, so they cannot capture fine-grained structural and semantic evolution of the scene. Existing 3D occupancy methods focus on single-frame perception and ignore temporal evolution. Other world-model approaches operate in the 2D image space (DriveDreamer, GAIA-1) and lack 3D understanding, or use raw point-cloud forecasting that lacks semantics. The authors target a unified 3D-occupancy world model that jointly forecasts surrounding scene evolution and the ego trajectory in a self-supervisable way.

## Innovation Points
- **3D occupancy as world-model representation** — chosen for expressiveness (dense voxel-level structure + semantics), efficiency (learnable from sparse LiDAR or self-supervision), and versatility (camera or LiDAR input).
- **3D-occupancy scene tokenizer** — a VQ-VAE with 2D-conv encoder/decoder over BEV-flattened occupancy that produces discrete high-level scene tokens from a learnable codebook (default 512 codes, 128-d).
- **Spatial-temporal generative transformer** — GPT-style autoregressive model that interleaves spatial aggregation (multi-scale, K levels via 2x2 stride-2 merging) with spatial-wise temporal causal self-attention; a U-Net aggregates predictions across scales.
- **Joint scene + ego token modelling** — an extra ego token is appended to the scene tokens so the same world-model attention captures high-order interactions between ego motion and the surrounding scene.
- **Two-stage self-supervised training** — Stage 1 trains the tokenizer with softmax + lovasz-softmax occupancy reconstruction; Stage 2 trains the transformer with token cross-entropy plus L2 on ego displacement, requiring no instance or map labels.

## Model Architecture
- Inputs: T past frames of 3D semantic occupancy y in R^{H x W x D} (H=W=200, D=16 on Occ3D), 2 s history (4 frames) -> forecast 3 s (6 frames).
- Scene tokenizer e: lift voxels to BEV via learnable class embeddings -> 2D-conv encoder downsamples by factor 4 to features in R^{H/4 x W/4 x C}; vector-quantize to nearest of N=512 codes (C=128); decoder of 2D deconv layers reconstructs occupancy via softmax over D x C''/D height channels.
- World tokens T = {z_i} per frame; an ego token z_0 in R^C is concatenated.
- Spatial aggregation: K-level hierarchical merging (2x2 stride-2 windows, downsample by 4 each level) yielding {T_0, ..., T_K}; sub-world models w_i operate at each scale.
- Temporal block: spatial-wise temporal causal self-attention applies masked attention across time at each spatial position; 6 layers for scene tokens, 2 layers cross-attention for ego planning tokens; U-Net merges multi-scale predictions.
- Ego decoder d_ego: MLP on the predicted ego token producing displacement (dx, dy) per future frame.
- Variants by scene-representation source r: OccWorld-O (oracle GT 3D occupancy), OccWorld-D (TPVFormer trained with dense GT 3D-occ), OccWorld-T (TPVFormer trained with semantic LiDAR), OccWorld-S (TPVFormer trained self-supervised, SelfOcc).
- Training: AdamW + cosine, lr 1e-3, weight decay 0.01, batch 1/GPU on 8x RTX 4090.

## Benchmark Results
**4D occupancy forecasting on Occ3D (Table 1, mIoU/IoU averaged over 1s/2s/3s):**

| Method        | Input  | Aux. Sup.       | mIoU 1s | mIoU 2s | mIoU 3s | Avg mIoU | Avg IoU | FPS  |
|---------------|--------|-----------------|---------|---------|---------|----------|---------|------|
| Copy&Paste    | 3D-Occ | None            | 14.91   | 10.54   | 8.52    | 11.33    | 20.52   | -    |
| **OccWorld-O**| 3D-Occ | None            | 25.78   | 15.14   | 10.51   | **17.14**| **26.63**| 18.0|
| OccWorld-D    | Camera | 3D-Occ          | 11.55   | 8.10    | 6.22    | 8.62     | 16.53   | 2.8  |
| OccWorld-T    | Camera | Semantic LiDAR  | 4.68    | 3.36    | 2.63    | 3.56     | 8.34    | 2.8  |
| OccWorld-S    | Camera | None            | 0.28    | 0.26    | 0.24    | 0.26     | 5.00    | 2.8  |

**Motion planning on nuScenes (Table 2, L2 m and Collision % averaged over 1/2/3 s):**

| Method        | Input  | Aux. Sup.                          | Avg L2 (m) | Avg Col. (%) | FPS  |
|---------------|--------|------------------------------------|------------|--------------|------|
| UniAD         | Camera | Map & Box & Motion & Tracklets & Occ | 1.03     | 0.31         | 1.8  |
| VAD-Base      | Camera | Map & Box & Motion                 | 1.22       | 0.53         | 4.5  |
| OccNet        | Camera | 3D-Occ & Map & Box                 | 2.14       | 0.72         | 2.6  |
| **OccWorld-O**| 3D-Occ | None                               | **1.17**   | 0.60         | 18.0 |
| OccWorld-D    | Camera | 3D-Occ                             | 1.40       | 0.87         | 2.8  |
| OccWorld-T    | Camera | Semantic LiDAR                     | 1.52       | 0.70         | 2.8  |
| OccWorld-S    | Camera | None                               | 1.83       | 2.02         | 2.8  |

Ablations (Table 4, scene representation = OccWorld-O):
- w/o spatial attention: forecast Avg mIoU 17.14 -> 10.07; planning L2 1.17 -> 1.42.
- w/o temporal attention (replaced by conv): mIoU -> 8.98; L2 -> 2.56.
- w/o ego token (forecast only): mIoU -> 15.13.
- w/o ego temporal attention (MLP head): L2 jumps to 5.89, mIoU drops to 12.07 — a wrongly predicted ego trajectory misleads scene forecasting.

Tokenizer hyperparameters (Table 3): default (50^2 latent grid, 128-d, 512 codes) gives Avg forecast mIoU 17.14 / planning L2 1.17 at 18 FPS; larger grid (100^2) improves reconstruction (mIoU 78.12) but hurts forecasting (Avg 16.30) and planning (1.36) due to overfitting; smaller grid (25^2) collapses forecasting to 8.81 mIoU.

## Limitations & Open Questions
- Long-horizon planning degrades: best L2 at 1 s (0.43 m for OccWorld-O) but reaches 1.99 m at 3 s (vs. UniAD 1.65), and collision rate is slightly worse than methods that exploit explicit freespace/box supervision.
- Cannot forecast new vehicles entering the field of view (acknowledged in Fig. 1 caption) — purely conditioned on past observations.
- Camera-only self-supervised variant (OccWorld-S) is far weaker (0.26 mIoU avg, 1.83 m L2), so end-to-end vision-only quality hinges on having stronger 3D-occupancy perception.
- Evaluated only on nuScenes/Occ3D; no closed-loop testing or generalization study to other datasets.
- Scaling behavior of the codebook/transformer to larger driving corpora is suggested but not demonstrated.
