---
paper_id: 2023-occ3d
title: "Occ3D: A Large-Scale 3D Occupancy Prediction Benchmark for Autonomous Driving"
authors: [Xiaoyu Tian, Tao Jiang, Longfei Yun, Yucheng Mao, Huitong Yang, Yue Wang, Yilun Wang, Hang Zhao]
year: 2023
venue: NeurIPS 2023 D&B
arxiv_id: "2304.14365"
url: https://arxiv.org/abs/2304.14365
primary_category: datasets
secondary_categories: [perception]
keywords: [3d-occupancy, benchmark, voxel-labels, visibility-mask, ctf-occ, waymo, nuscenes, general-objects]
one_line_summary: Large-scale 3D occupancy prediction benchmark on Waymo/nuScenes with semi-automatic visibility-aware label pipeline; introduces CTF-Occ coarse-to-fine voxel transformer baseline.
distilled_at: 2026-05-02
source_pdf: doc/papers/perception/occ3d-neurips2023.pdf
---

# Occ3D: A Large-Scale 3D Occupancy Prediction Benchmark for Autonomous Driving

## Keywords
- 3d-occupancy, benchmark, voxel-labels, visibility-mask, ctf-occ, waymo, nuscenes, general-objects

## TL;DR
3D bounding boxes erase fine geometry and ignore out-of-vocabulary objects, but no high-quality 3D occupancy benchmark existed for driving. The authors build a semi-automatic label pipeline (voxel densification, occlusion reasoning, image-guided refinement) and release Occ3D-Waymo (200K frames) and Occ3D-nuScenes (40K frames) with a "General Objects" class. They also propose CTF-Occ, a coarse-to-fine voxel transformer that beats BEVFormer by 1.65 mIoU on Occ3D-nuScenes and 1.97 mIoU on Occ3D-Waymo.

## Problem & Motivation
3D object detection over a closed ontology has two failure modes for driving safety: (1) bounding boxes do not capture fine geometric detail (e.g. construction vehicle arms protrude); (2) rare or out-of-vocabulary categories (trash cans, irregular debris) are ignored. 3D occupancy prediction (per-voxel state + semantics) is the natural successor, but prior occupancy datasets (SemanticKITTI, KITTI-360) lack surround-view images and are limited in diversity, scale, and resolution. Constructing a labeled occupancy dataset from LiDAR is hard due to point sparsity, occlusion, and 3D-2D misalignment from sensor noise/pose error.

## Innovation Points
- **Occ3D-Waymo / Occ3D-nuScenes benchmarks** — surround-view image inputs with dense per-voxel semantic occupancy; Waymo split has 1000 sequences, 200K frames, 0.05 m voxels, 14 classes + GO; nuScenes split has 40K frames, 0.4 m voxels, 16 classes + GO.
- **General Objects (GO) class** — explicit label for out-of-vocabulary objects so safety-critical unknowns are evaluated, not silently dropped.
- **Three-stage label pipeline** — voxel densification (dynamic/static segmentation, multi-frame aggregation, KNN label assignment, VDBFusion mesh reconstruction), occlusion reasoning (LiDAR + camera visibility masks via ray casting), and image-guided voxel refinement (eliminate misaligned voxels using 2D semantic masks).
- **Visibility masks for evaluation** — separate LiDAR and camera visibility masks restrict mIoU evaluation to "observed" voxels, avoiding penalizing models for unseen regions.
- **3D-2D consistency quality metric** — quantitative pipeline-validation metric reprojecting 3D voxel labels onto manually-labeled 2D image masks (pixel-level Precision/Recall/IoU/mIoU).
- **CTF-Occ network** — transformer baseline using a learnable 200x200x256 voxel embedding, pyramid coarse-to-fine encoder with incremental top-K (0.2 ratio) token selection over uncertain voxels, deformable spatial cross-attention into image features, and an implicit MLP occupancy decoder for arbitrary-resolution queries.

## Model Architecture
CTF-Occ baseline:
- Multi-view surround camera images -> ResNet-101 (FCOS3D-pretrained) image backbone -> multi-level 2D features (image size 640x960 for Waymo; 928x1600 for nuScenes).
- Learnable voxel embedding 200x200x256, fed through 4 encoder layers without token selection.
- Coarse-to-fine voxel encoder: 3 pyramid stages (z-axis res 8, 16, 32 on Waymo; 8, 16 on nuScenes); each stage applies (a) binary "empty/occupied" classifier per voxel, (b) incremental top-K uncertain-token selection (K = 0.2), (c) one 3D spatial cross-attention layer (deformable sampling into multi-view image features), (d) stacked 3D conv feature interaction, (e) trilinear upsampling to next stage.
- Implicit decoder: MLP takes (voxel feature, 3D coordinate) and outputs C' semantic-class logits.
- Output: dense W x H x L x C' semantic occupancy at voxel size 0.4 m.
- Losses: OHEM-weighted occupancy cross-entropy + per-pyramid-level binary occupancy supervision.

## Benchmark Results
**Occ3D-nuScenes (mIoU, vision-only):**
| Method      | mIoU  |
|-------------|-------|
| MonoScene   | 6.06  |
| TPVFormer   | 27.83 |
| BEVDet      | 19.38 |
| OccFormer   | 21.93 |
| BEVFormer   | 26.88 |
| **CTF-Occ** | **28.53** |

**Occ3D-Waymo (mIoU, vision-only):**
| Method      | mIoU  |
|-------------|-------|
| BEVDet      | 9.88  |
| TPVFormer   | 16.76 |
| BEVFormer   | 16.76 |
| **CTF-Occ** | **18.73** |

LiDAR-Only on Occ3D-Waymo reaches 29.74 mIoU; BEVFormer-Fusion (camera+LiDAR) reaches 39.05 mIoU — a large gap above all vision-only methods.

Pipeline ablation (Table 2, Occ3D-Waymo subset, mIoU): single-frame points 13.32 -> +multi-frame 17.65 -> +0.1 m voxelization 41.17 -> +mesh recon 41.99 -> 0.05 m voxel 43.58 -> +image-guided refinement 58.50.

Model ablation (Table 5, Occ3D-Waymo): top-K only 14.06 mIoU; +OHEM with random selection 16.62; +OHEM with uncertain selection 17.37; +OHEM with top-K 18.43. OHEM and uncertain/top-K selection together provide most of the gain on small classes (PED, CC).

## Limitations & Open Questions
- Sensor calibration error: pipeline depends on precise LiDAR-camera calibration and pose for multi-frame aggregation.
- Dynamic and deformable objects: relies on 3D box annotations and rigid-body assumption — un-boxed animals and articulated motions (pedestrian arm swing) still produce motion blur.
- Closed-ontology General Objects: GO is a single bucket; no fine-grained semantics for OOV categories like trash cans or cones — open-vocabulary annotation is left as future work.
- Instance IDs and motion vectors are defined in the task formulation but explicitly left as future work; current benchmark is per-voxel state + class only.
