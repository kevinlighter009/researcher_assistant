---
paper_id: 2023-surroundocc
title: "SurroundOcc: Multi-Camera 3D Occupancy Prediction for Autonomous Driving"
authors: [Yi Wei, Linqing Zhao, Wenzhao Zheng, Zheng Zhu, Jie Zhou, Jiwen Lu]
year: 2023
venue: ICCV 2023
arxiv_id: "2303.09551"
url: https://arxiv.org/abs/2303.09551
primary_category: perception
secondary_categories: [datasets]
keywords: [3d-occupancy, multi-camera, 2d-3d-spatial-attention, multi-scale, dense-occupancy-gt, nuscenes, semantickitti]
one_line_summary: Multi-camera 3D semantic occupancy network using 2D-3D spatial cross-attention with multi-scale supervision, plus a Poisson-Reconstruction pipeline that turns sparse LiDAR into dense occupancy ground truth.
distilled_at: 2026-05-02
source_pdf: doc/papers/perception/surroundocc-iccv2023.pdf
---

# SurroundOcc: Multi-Camera 3D Occupancy Prediction for Autonomous Driving

## Keywords
- 3d-occupancy, multi-camera, 2d-3d-spatial-attention, multi-scale, dense-occupancy-gt, nuscenes, semantickitti

## TL;DR
Vision-based 3D perception methods (depth, BEV detection) miss occluded geometry and cannot describe arbitrary-shape objects. SurroundOcc lifts multi-camera 2D features to a 3D voxel volume via 2D-3D spatial cross-attention in a multi-scale U-Net, supervising occupancy at every level. To avoid expensive labeling, the authors build a pipeline that stitches multi-frame LiDAR (static scenes + objects separately), fills holes via Poisson Reconstruction, and propagates semantics by NN — yielding dense occupancy GT on nuScenes. The model achieves state-of-the-art SC IoU and SSC mIoU on the resulting nuScenes occupancy benchmark and on monocular SemanticKITTI.

## Problem & Motivation
- Multi-camera 3D detection (e.g. BEVFormer) suffers from long-tail and cannot represent objects of arbitrary shape (vegetation, barriers).
- Depth-prediction approaches recover only the nearest surface per ray and cannot reason about occluded geometry; multi-camera consistency is not guaranteed.
- Earlier occupancy works are limited: MonoScene is monocular and naive multi-camera fusion underperforms; TPVFormer trains only with sparse LiDAR supervision and produces sparse predictions.
- Outdoor multi-camera datasets (nuScenes) have no dense occupancy labels, and SemanticKITTI-style manual labeling does not scale.

## Innovation Points
- **2D-3D spatial cross-attention** — 3D volume queries (instead of BEV queries) project to 2D views and aggregate features via deformable attention, preserving 3D structure that BEV-based attention collapses.
- **Multi-scale 2D-3D U-Net** — multi-level 2D features feed multi-level 3D volume features that are progressively upsampled by 3D deconvolution and fused with skip connections.
- **Multi-scale occupancy supervision with decayed loss** — every resolution level outputs an occupancy prediction, weighted alpha_j = 1/(2^j), giving fine-grained detail at the highest resolution.
- **Dense occupancy GT pipeline** — two-stream multi-frame LiDAR stitching (static scene + dynamic objects, indexed by 3D box), Poisson Surface Reconstruction to fill gaps, then NN-based semantic label propagation; uses only existing 3D detection and segmentation labels.
- **nuScenes occupancy benchmark** — releases dense occupancy labels and code, enabling subsequent multi-camera occupancy research.

## Model Architecture
- Inputs: N surround cameras at 1600x900; backbones ResNet101-DCN (FCOS3D init) for nuScenes, EfficientNetB7 for SemanticKITTI; FPN to produce M=4 multi-scale 2D feature maps.
- 2D-3D spatial cross-attention at each scale: 3D volume queries Q in R^{C x H x W x Z} project each voxel center to 2D views (only views the point hits); deformable attention aggregates sampled 2D features.
- Number of attention layers per level: [1, 3, 6] (nuScenes) and [1, 3, 8] (SemanticKITTI), skip connection skipped at level 0.
- 3D U-Net body: 3D convolutions for intra-volume mixing; 3D deconvolution upsamples Y_{j-1} and fuses with current-level F_j: Y_j = F_j + Deconv(Y_{j-1}).
- Output: per-level occupancy V_j in R^{C_j x H_j x W_j x Z_j}; final volume on nuScenes is 200x200x16 at 0.5 m voxels (range [-50,50] m XY, [-5,3] m Z); on SemanticKITTI 256x256x32 at 0.2 m voxels.
- Losses: multi-class cross-entropy + scene-class affinity loss (from MonoScene) for semantic occupancy; two-class CE for scene reconstruction.
- Training: 8 RTX 3090s.

## Benchmark Results

**3D semantic occupancy on nuScenes validation (Table 1):**
| Method     | SC IoU | SSC mIoU |
|------------|--------|----------|
| MonoScene  | 23.96  |  7.31    |
| Atlas      | 28.66  | 15.00    |
| BEVFormer  | 30.50  | 16.75    |
| TPVFormer* (dense GT) | 30.86 | 17.10 |
| **SurroundOcc** | **31.49** | **20.30** |

**Monocular SSC on SemanticKITTI test (Table 3):**
- SurroundOcc 34.72 SC IoU / 11.86 SSC mIoU vs. MonoScene 34.16 / 11.08 and TPVFormer 34.25 / 11.26 (best on both metrics although the model is not designed for monocular input).

**3D scene reconstruction on nuScenes validation (Table 4):**
- SurroundOcc CD 1.950 / F-score 0.483 vs. best baseline TransformerFusion CD 2.205 / F-score 0.453; also best Comp 1.226 and Recall 0.602.

**Ablations:**
- 2D-3D spatial attention vs. averaging features: SC IoU 31.49 vs. 29.78 (no attention) and 30.45 (BEV-based attention) — Table 5.
- Multi-scale: removing multi-scale structure drops to 30.41 SC IoU / 18.22 SSC mIoU; removing multi-scale supervision drops to 31.16 / 19.73 — Table 6.
- Dense supervision: training on sparse LiDAR points gives 11.96 SC IoU / 12.17 SSC mIoU; sparse occupancy labels give 30.58 / 18.83; dense occupancy labels give 31.49 / 20.30 — Table 7.

**Efficiency on one RTX 3090, 6 cams at 1600x900 (Table 8):**
- SurroundOcc 0.34 s latency / 5.9 GB memory; BEVFormer 0.31 / 4.5; TPVFormer 0.32 / 5.1; MonoScene 0.87 / 20.3.

## Limitations & Open Questions
- Single-frame occupancy only — the authors flag occupancy flow (temporal prediction) as future work for downstream prediction/planning.
- GT pipeline still depends on LiDAR plus existing 3D detection and segmentation labels; self-supervised RGB-only occupancy is acknowledged as a valuable open direction.
- NN-based semantic labeling is sensitive to noise in original LiDAR semantic annotations, which the authors note is unresolved.
- Per-class breakdowns show small/rare classes (bicycle, motorcycle) remain low (e.g. 11.68 / 10.70 IoU on nuScenes), suggesting the long-tail issue is reduced but not solved.
