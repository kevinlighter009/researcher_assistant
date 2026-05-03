---
paper_id: 2022-bevformer
title: "BEVFormer: Learning Bird's-Eye-View Representation from Multi-Camera Images via Spatiotemporal Transformers"
authors: [Zhiqi Li, Wenhai Wang, Hongyang Li, Enze Xie, Chonghao Sima, Tong Lu, Yu Qiao, Jifeng Dai]
year: 2022
venue: ECCV 2022
arxiv_id: "2203.17270"
url: https://arxiv.org/abs/2203.17270
primary_category: perception
secondary_categories: []
keywords: [bev, multi-camera, spatiotemporal-transformer, deformable-attention, 3d-detection, map-segmentation, nuscenes, waymo]
one_line_summary: Spatiotemporal transformer with grid-shaped BEV queries that fuses multi-camera spatial features (spatial cross-attention) and recurrent history BEV (temporal self-attention); 56.9% NDS on nuScenes test.
distilled_at: 2026-05-02
source_pdf: doc/papers/perception/bevformer-eccv2022.pdf
---

# BEVFormer: Learning Bird's-Eye-View Representation from Multi-Camera Images via Spatiotemporal Transformers

## Keywords
- bev, multi-camera, spatiotemporal-transformer, deformable-attention, 3d-detection, map-segmentation, nuscenes, waymo

## TL;DR
Camera-only 3D perception lagged LiDAR because prior BEV pipelines either processed each view independently or relied on brittle depth estimates. BEVFormer introduces a unified BEV encoder built from grid-shaped learnable BEV queries, a deformable spatial cross-attention that lifts each query to multi-camera image features, and a temporal self-attention that recurrently fuses the previous-timestamp BEV. With a ResNet-101-DCN backbone the system reaches 56.9% NDS on the nuScenes test set, 9.0 points above DETR3D, and matches some LiDAR baselines while remarkably improving velocity estimation and recall under low visibility.

## Problem & Motivation
Vision-based 3D perception is attractive (cheap sensors, captures stoplines/signs) but trailed LiDAR. Two dominant prior camera paradigms each had problems: (1) monocular detectors processed each view independently and used cross-camera post-processing, losing inter-view information and efficiency; (2) BEV-from-depth methods (e.g. Lift-Splat, OFT) generated BEV features by lifting pixels with predicted depth/depth-distributions — sensitive to depth error and prone to compounding inaccuracy. In addition, multi-view 3D detectors rarely exploited temporal context, hurting velocity estimation and detection of occluded objects; naïvely stacking BEV features across timestamps was costly and noisy. The authors wanted a BEV generator that (a) does not depend on explicit depth and (b) integrates temporal information cheaply.

## Innovation Points
- **Grid-shaped learnable BEV queries** — a H×W×C learnable tensor where each query owns a real-world grid cell (default 200×200 at 0.512 m on nuScenes); a single shared BEV representation feeds multiple downstream heads.
- **Spatial Cross-Attention (SCA)** — each BEV query is lifted to a pillar of N_ref=4 anchor heights (-5 m to 3 m), points are projected to whichever cameras hit them, and features are aggregated with deformable attention; avoids global multi-head attention cost and avoids depth-prior dependence.
- **Temporal Self-Attention (TSA)** — current BEV queries attend, via deformable attention, to the previous timestamp's BEV (ego-motion-aligned), giving an RNN-style hidden-state mechanism that propagates history at low cost; the offsets are predicted from the concatenation of Q and B'_{t-1} to handle moving objects.
- **Versatile BEV head interface** — the single B_t feature plugs into a Deformable-DETR-style 3D detection head and a Panoptic-SegFormer-style map segmentation head, enabling joint multi-task perception.
- **Recurrent training over a 4-frame window** — at training a sample is paired with 3 prior frames (no gradients) to build B_{t-3..t-1} so the temporal pathway gets meaningful state without back-propagating through the full sequence.

## Model Architecture
- 6 surround cameras at one timestamp t → CNN backbone (ResNet-101-DCN initialized from FCOS3D, or VoVNet-99 from DD3D) → FPN multi-scale features F_t = {F_t^i} for N_view views.
- Grid-shaped learnable BEV queries Q ∈ R^{H×W×C}, with H=W=200, C=256, grid resolution s = 0.512 m, perception range ±51.2 m on nuScenes (300×220, s=0.5 m, range -35 to 75 m on Waymo). Learnable positional embedding added.
- 6 stacked encoder layers, each layer = TSA → Add&Norm → SCA → Add&Norm → FFN → Add&Norm.
  - **TSA**: each query attends to {Q, B'_{t-1}} (ego-aligned previous BEV) via deformable attention; degenerates to plain self-attention for the first frame in a sequence.
  - **SCA**: each query lifted to a pillar of N_ref=4 reference heights, projected per-camera through extrinsics/intrinsics; deformable attention samples 4 offsets per reference point per head, only on hit views V_hit; output is the average over hit views.
- Output BEV B_t ∈ R^{200×200×256} consumed by:
  - **3D detection head**: Deformable-DETR-style decoder over single-scale BEV; predicts 3D boxes + velocity, L1 regression, no NMS.
  - **Map segmentation head**: Panoptic-SegFormer mask decoder with class-fixed queries (car, vehicles, road, lane).
- Training: 24 epochs, lr 2e-4; recurrent 4-frame window sampled from the past 2 s of the same scene.

## Benchmark Results

**3D detection on nuScenes test set (Table 1):**
| Method | Modality | Backbone | NDS ↑ | mAP ↑ | mAVE ↓ |
|---|---|---|---|---|---|
| FCOS3D | C | R101 | 0.428 | 0.358 | 1.434 |
| DETR3D | C | V2-99* | 0.479 | 0.412 | 0.845 |
| BEVFormer-S | C | R101 | 0.462 | 0.409 | 0.925 |
| **BEVFormer** | C | R101 | **0.535** | **0.445** | **0.435** |
| **BEVFormer** | C | V2-99* | **0.569** | **0.481** | **0.378** |
| CenterPoint-Voxel | L | – | 0.655 | 0.580 | – |
| PointPainting | L&C | – | 0.581 | 0.464 | 0.247 |

- BEVFormer (V2-99) is +9.0 NDS over DETR3D (47.9 → 56.9) on test, and within range of LiDAR baselines (SSN 56.9 NDS, PointPainting 58.1 NDS).
- mAVE drops to 0.378 m/s (test), versus ~0.85–1.5 for prior camera-only methods.

**3D detection on nuScenes val set (Table 2):** BEVFormer R101 reaches 0.517 NDS / 0.416 mAP vs DETR3D 0.425 / 0.346; BEVFormer-S R101 reaches 0.448 / 0.375.

**Waymo val (Table 3, vehicle, IoU=0.5):** BEVFormer L1/L2 APH = 0.280 / 0.241 vs DETR3D 0.220 / 0.216 (+6.0 / +2.5 APH); on nuScenes-style metrics on Waymo, BEVFormer 0.426 NDS vs DETR3D 0.394 (+3.2 NDS).

**Joint detection + map seg on nuScenes val (Table 4):** BEVFormer det+seg reaches 0.520 NDS / 0.412 mAP and BEV-IoU Car 46.8 / Vehicles 46.7 / Road 77.5 / Lane 23.9; outperforms Lift-Splat by ~11.0 NDS and +5.6 IoU on Lane (23.9 vs 18.3).

**Ablations:**
- Spatial-attention variant (Table 5, BEVFormer-S, R101): Local deformable 0.448 NDS vs Global 0.404 NDS vs Points-only 0.423 NDS — local sparse attention beats both, while global needs ~36 G memory vs ~20 G for local.
- Removing temporal self-attention (BEVFormer → BEVFormer-S, Table 1, V2-99 test): NDS 0.569 → 0.495, mAVE 0.378 → 0.842; temporal context contributes most of the velocity gain and improves recall, especially on the 0–40% visibility subset (>6.0 pp recall gap, Fig. 3).
- Latency / scale (Table 6, V100, R101-DCN, 900×1600): default 1.7 FPS (130 ms BEVFormer block), config D (1 layer, 100×100 BEV, single-scale) reaches 2.3 FPS at 47.8 NDS, showing flexibility but backbone dominates cost.

## Limitations & Open Questions
- Camera-only methods still trail LiDAR in absolute NDS / mAP and in 3D localization accuracy; precise 3D position from 2D remains open (paper's own statement).
- Inference is ~1.7 FPS with R101-DCN at 900×1600 — far from real-time deployment; the backbone is the bottleneck and efficient backbones are left for future work.
- Multi-task joint training shows negative transfer on road and lane segmentation versus single-task training.
- Temporal pathway uses only one previous BEV (RNN-style); long-horizon temporal modeling is not explored.
- Anchor-height set (-5 to 3 m, 4 heights) and fixed grid resolution are hand-designed; sensitivity to these hyperparameters not deeply studied.
- Evaluation is open-loop perception only; no closed-loop driving evaluation.
