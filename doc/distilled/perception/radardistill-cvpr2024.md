---
paper_id: 2024-radardistill
title: "RadarDistill: Boosting Radar-based Object Detection Performance via Knowledge Distillation from LiDAR Features"
authors: [Geonho Bang, Kwangjin Choi, Jisong Kim, Dongsuk Kum, Jun Won Choi]
year: 2024
venue: CVPR 2024
arxiv_id: "2403.05061"
url: https://arxiv.org/abs/2403.05061
primary_category: perception
secondary_categories: []
keywords: [radar-3d-detection, lidar-to-radar-distillation, bev, cross-modality-alignment, activation-based-distillation, proposal-based-distillation, nuscenes, pillarnet]
one_line_summary: LiDAR-to-radar BEV knowledge distillation with cross-modality alignment, activation-based, and proposal-based feature matching; new SOTA radar-only 3D detection on nuScenes (20.5 mAP / 43.7 NDS).
distilled_at: 2026-05-02
source_pdf: doc/papers/perception/radardistill-cvpr2024.pdf
---

# RadarDistill: Boosting Radar-based Object Detection Performance via Knowledge Distillation from LiDAR Features

## Keywords
- radar-3d-detection, lidar-to-radar-distillation, bev, cross-modality-alignment, activation-based-distillation, proposal-based-distillation, nuscenes, pillarnet

## TL;DR
Radar point clouds are sparse and noisy, so radar-only 3D detectors trail far behind LiDAR ones. RadarDistill distills knowledge from a LiDAR teacher into a radar student via three components — Cross-Modality Alignment (CMA) to densify radar BEV features, Activation-based Feature Distillation (AFD) for low-level features split into active/inactive regions, and Proposal-based Feature Distillation (PFD) for high-level features split by TP/FP/FN proposal regions. On the nuScenes test set the radar-only model reaches 20.5 mAP / 43.7 NDS, exceeding the previous radar-only SOTA (KPConvPillars) by +15.6 mAP and +29.8 NDS.

## Problem & Motivation
Radar is cheap and weather-robust but produces sparse, noisy point clouds with poor angular resolution and many multi-path false positives, so radar-only 3D detectors (Radar-PointGNN, KPConvPillars) lag substantially behind camera and LiDAR detectors. Prior cross-modality distillation work (BEVDistill, DistillBEV, S2M2-SSD, UniDistill) targets camera-from-LiDAR or LiDAR-from-fusion; none is tailored to radar's two-fold pathology of (a) extreme spatial sparsity (radar non-empty pillars are about 10 percent of LiDAR's), which makes naive feature matching transfer mostly empty regions, and (b) magnitude mismatch between radar and LiDAR high-level features. The authors set out to design KD specifically for radar's sparse and noisy structure.

## Innovation Points
- **Cross-Modality Alignment (CMA)** — a side-pathway densification module of stacked Down/Up blocks (deformable conv + ConvNeXt V2) plus an Aggregation Module that increases the ratio of active radar BEV pillars before any feature matching, addressing the sparsity gap that otherwise wastes the KD signal.
- **Activation-based Feature Distillation (AFD)** — splits low-level BEV features into Active Regions (both teacher and student active) and Inactive Regions (only student active) via thresholded channel-summed activation masks, applies separate L2 losses with adaptive area-ratio weights so AR is not drowned by IR.
- **Proposal-based Feature Distillation (PFD)** — uses CenterHead classification heatmaps from teacher and student to label proposals as TP, FP, FN, then matches normalized high-level features inside TP and FN regions while suppressing student activations inside FP regions; channel-wise softmax normalization closes the radar/LiDAR magnitude gap.
- **First LiDAR-to-radar 3D detection KD** — explicitly targets the radar-only category and shows the same student backbone (PillarNet-18) jumps from 8.6 to 20.5 mAP without any inference-time LiDAR.
- **Plug-in to fusion** — the distilled radar branch also lifts BEVFusion-style camera-radar fusion (BEVFusion 38.3 mAP / 45.3 NDS to 39.6 / 46.4).

## Model Architecture
- Inputs: nuScenes 5-radar 360-degree point cloud (student) and 32-beam LiDAR (teacher, training only). Detection range [-54, 54] m in X/Y, [-5, 3] m in Z, pillar size 0.075 x 0.075 m.
- Both branches share the PillarNet-18 layout (ResNet-18 backbone): 2D Pillar Encoding -> SparseEnc (2D sparse conv) -> low-level BEV features F^(l) at H/8 x W/8.
- CMA (radar branch only) inserts after SparseEnc: stacked Down blocks (deformable conv + ConvNeXt V2) and Up blocks (transposed conv) with 1x1-conv Aggregation Modules, producing two densified radar low-level features F_rdr^(l1), F_rdr^(l2) at 1/8 resolution.
- DenseEnc (2D dense conv) lifts low-level BEV features to two high-level feature maps F^(h1), F^(h2) per branch.
- CenterHead produces per-class heatmaps H^cls and regression outputs.
- KD losses: AFD on (F_ldr^(l), F_rdr^(l1)) and (F_ldr^(l), F_rdr^(l2)) with active/inactive masks and area-ratio weighting; PFD on softmax-normalized (F_ldr^(h1), F_rdr^(h1)) and (F_ldr^(h2), F_rdr^(h2)) with TP/FP/FN proposal weights (sigma = 0.1).
- Total loss: L_total = L_det + gamma * L_AFD + delta * L_PFD with gamma = 5, delta = 25; AFD weights alpha = 3e-4, beta = 5e-5; PFD weights lambda1 = 5, lambda2 = 1.
- Training: 40 epochs, batch 16, Adam, one-cycle LR (peak 1e-3), CBGS class-balanced sampling, radar backbone initialized from pretrained LiDAR backbone via Inheriting Strategy, 4 x RTX 3090. LiDAR branch is discarded at inference; runtime cost is unchanged from baseline PillarNet-18.

## Benchmark Results
**nuScenes test set, radar-only 3D detection (Table 1):**

| Method                | Input | KD | mAP  | NDS  |
|-----------------------|-------|----|------|------|
| Radar-PointGNN        | R     | -  | 0.5  | 3.4  |
| KPConvPillars         | R     | -  | 4.9  | 13.9 |
| PillarNet-18 baseline | R     | -  | 8.6  | 34.7 |
| **RadarDistill**      | R     | yes| **20.5** | **43.7** |

Headline gain over previous radar-only SOTA (KPConvPillars): +15.6 mAP, +29.8 NDS. Per-class on nuScenes test (Table 2): Car AP 54.0 (vs baseline 41.8 and CenterFusion C+R 50.9), Trailer 29.5 (+23 over baseline). Pedestrian, motorcycle, bicycle remain weak (9.2, 15.3, 0.9), where camera detectors dominate.

**Component ablation on nuScenes val (Table 3):**

| CMA | AFD | PFD | mAP | NDS |
|-----|-----|-----|-----|-----|
|     |     |     | 5.4 | 27.3 |
|  X  |     |     | 6.4 | 29.3 |
|  X  |  X  |     | 10.9| 33.7 |
|  X  |  X  |  X  | **11.2** | **34.7** |
|     |  X  |  X  | 7.0 | 30.7 |

Removing CMA while keeping AFD and PFD drops NDS from 34.7 to 30.7, confirming CMA is the pivotal component. AFD beats Complete / Gaussian / FG-BG KD baselines on Car AP (45.8 vs 39.0–42.1, Table 4). PFD beats the same baselines (46.1 vs 45.2–45.9 Car AP, Table 5). Removing PFD scale normalization costs 6.2 Car AP, 2.7 mAP, 2.9 NDS (Table 6).

**Camera-radar fusion (Table 7):** dropping the distilled radar branch into BEVFusion lifts Car AP 65.9 to 67.7, mAP 38.3 to 39.6, NDS 45.3 to 46.4.

## Limitations & Open Questions
- Evaluated only on nuScenes; no Waymo / View-of-Delft / K-Radar generalization, and no closed-loop or tracking evaluation.
- Per-class results show RadarDistill still underperforms camera detectors on small or thin objects (pedestrian 9.2, bicycle 0.9) — radar resolution remains the upstream bottleneck that distillation cannot fully close.
- Requires paired LiDAR-radar data and a trained LiDAR teacher at training time; transferability to radar-only datasets without LiDAR supervision is not addressed.
- Fusion gains over BEVFusion are modest (+1.3 mAP / +1.1 NDS); the authors note more sophisticated fusion strategies are left to future work.
- Inference latency / parameter overhead from CMA during training is not reported, and the choice of activation threshold and the many loss weights (alpha, beta, gamma, delta, lambda1, lambda2) appears hand-tuned.
