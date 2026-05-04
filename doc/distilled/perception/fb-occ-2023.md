---
paper_id: 2023-fb-occ
title: "FB-OCC: 3D Occupancy Prediction based on Forward-Backward View Transformation"
authors: [Zhiqi Li, Zhiding Yu, David Austin, Mingsheng Fang, Shiyi Lan, Jan Kautz, Jose M. Alvarez]
year: 2023
venue: "CVPR 2023 Workshop (3D Occupancy Prediction Challenge winner)"
arxiv_id: "2307.01492"
url: https://arxiv.org/abs/2307.01492
primary_category: perception
secondary_categories: []
keywords: [occupancy-prediction, forward-backward-projection, bev, lss, bevformer, internimage-h, occ3d-nuscenes]
one_line_summary: Camera-only 3D occupancy network combining forward (LSS) and backward (BEVFormer-style) view transformations with depth+semantic pre-training and InternImage-H scaling; 54.19% mIoU, 1st on Occ3D-nuScenes challenge.
distilled_at: 2026-05-02
source_pdf: doc/papers/perception/fb-occ-2023.pdf
---

# FB-OCC: 3D Occupancy Prediction based on Forward-Backward View Transformation

## Keywords
- occupancy-prediction, forward-backward-projection, bev, lss, bevformer, internimage-h, occ3d-nuscenes

## TL;DR
Forward-only view transformations (LSS) yield sparse 3D voxels, while backward-only transformations (BEVFormer) miss strong geometric priors. The authors propose FB-OCC, which chains a forward LSS-style projection (producing an initial 3D voxel volume) with a depth-aware backward projection that compresses to BEV and refines with cross-attention; combined with joint depth+semantic pre-training and the 1.2B-parameter InternImage-H backbone, FB-OCC reaches 54.19% mIoU on the Occ3D-nuScenes test set, ranking 1st in the CVPR 2023 3D Occupancy Prediction Challenge.

## Problem & Motivation
Camera-based 3D perception relies on view transformation, but the two dominant strategies have complementary weaknesses: forward projection (LSS) lifts pixels to 3D using predicted depth distributions, producing relatively sparse voxel volumes; backward projection (BEVFormer) uses learned BEV queries that randomly initialize and lack the geometric priors LSS provides. For dense 3D occupancy prediction, sparsity hurts directly. Additionally, large-scale 2D vision backbones (e.g., 1B-param InternImage-H) overfit when fine-tuned on the small 40K-sample nuScenes set, making naive scaling ineffective for 3D perception.

## Innovation Points
- **Forward-Backward View Transformation (F-VTM + B-VTM)** — sequentially apply LSS forward projection to seed a 3D voxel volume, then a depth-aware backward projection where compressed BEV features query image features; combines geometric priors of LSS with the refinement power of BEVFormer-style attention.
- **Depth-aware backward projection** — unlike BEVFormer's random BEV queries, the backward stage uses the depth distribution from the forward stage to model projection more precisely.
- **Joint depth + semantic pre-training** — large-scale pre-training on nuScenes that combines depth estimation (supervised with LiDAR) and 2D semantic segmentation (with SAM-generated masks for thing classes and LiDAR-projected masks for stuff classes), avoiding the over-bias toward depth that pure depth pre-training would cause.
- **Large-scale backbone scaling (InternImage-H, 1.2B params)** — leverages challenge-allowed external data (Object365 pre-training) to make 1B+ backbones viable for 3D perception without overfitting.
- **Test-time augmentation + temporal TTA** — horizontal/vertical flip ensemble plus reusing predicted static voxels from previous frames near the ego car to mitigate distance-based accuracy degradation.
- **Multi-model ensemble with NNI-searched weights** — final submission ensembles 7 models with per-model and per-class weights tuned via Neural Network Intelligence.

## Model Architecture
- Input: multi-view surround images (640x1600, up to 16 historical frames following SOLOFusion online temporal training).
- 2D backbone: scaled from ResNet-50 (ablation) up to InternImage-H (1.2B params); features downsampled with stride 16.
- Depth Net: predicts 80 discrete depth bins covering 2-42m.
- F-VTM (Forward View Transformation Module): LSS-style lift-splat-shoot using depth distribution; produces initial 3D voxel features at 200x200x16, supervised with point-cloud-derived depth ground truth (BEVDepth-style).
- B-VTM (Backward View Transformation Module): collapses voxels to a BEV feature map; the BEV map serves as queries and attends to image encoder features (1 layer) using depth-aware projection to refine geometry.
- Fusion: BEV features from B-VTM are unsqueezed and combined with the 3D voxel volume from F-VTM into a unified 3D voxel representation.
- Voxel encoder + occupancy head: produces per-voxel class predictions over 18 classes (17 semantic + free) at 0.4m voxel resolution within [-40m, 40m] x [-40m, 40m] x [-1m, 5.4m].
- Losses: distance-aware Focal loss L_fl (M2BEV-inspired), Dice loss L_dl, affinity losses L_geo_scal and L_sem_scal (MonoScene), lovasz-softmax L_ls (OpenOccupancy), depth supervision L_d, 2D semantic loss L_s.
- Training: batch size 32 on 32 A100 GPUs, AdamW, lr 1e-4, weight decay 0.05, ~50 epochs.

## Benchmark Results
**Occ3D-nuScenes (challenge test set):**
- Final ensemble achieves **54.19% mIoU** (1st place in CVPR 2023 3D Occupancy Prediction Challenge).

**Single-model comparison on Occ3D-nuScenes (Table 1, validation, ResNet-50 backbone, 256x704 input):**
| Method        | mIoU  |
|---------------|-------|
| MonoScene     | 6.06  |
| BEVDet        | 11.73 |
| BEVFormer     | 26.88 |
| CTF-Occ       | 28.53 |
| Version A (FB-OCC vanilla) | 23.12 |
| Version H (FB-OCC + all improvements + TTA) | **42.06** |

**Scaling ablation (Table 2, FB-OCC at increasing model size):**
| Version | Backbone           | Params  | mIoU  |
|---------|--------------------|---------|-------|
| H       | ResNet-50          | 67.8M   | 42.06 |
| I       | VoVNet-99 (960x1760) | 130.8M | 48.90 |
| J       | ViT-L + ViT-Adapter  | 428.8M | 50.47 |
| K       | InternImage-H        | 1200.0M | **52.79** |

Single-design ablations (Table 1, build-up A->H): adding BEVDepth-style depth supervision (B), ignoring camera-invisible voxels (C), bug fixes (D), 16-frame temporal context (E), joint depth+semantic pre-training (F), Dice loss + 3D temporal alignment (G), and TTA (H) progressively raise mIoU from 23.12 to 42.06.

## Limitations & Open Questions
- Pure technical report style; limited methodological ablations isolating the depth-aware backward projection vs. a vanilla backward projection.
- Inference cost of the 1.2B-parameter InternImage-H backbone with 16-frame temporal context and 7-model TTA ensemble is not reported and is clearly far from on-vehicle deployable.
- Evaluated only on Occ3D-nuScenes; generalization to other occupancy benchmarks (e.g., OpenOccupancy, SemanticKITTI) not reported.
- Heavy reliance on external pre-training data (Object365, LiDAR-projected masks, SAM-generated masks) — scaling recipe may not transfer to settings without such data sources.
- The relative contribution of the F+B architecture vs. simple backbone scaling is hard to disentangle from the reported tables.
