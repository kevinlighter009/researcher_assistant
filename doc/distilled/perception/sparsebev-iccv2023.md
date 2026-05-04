---
paper_id: 2023-sparsebev
title: "SparseBEV: High-Performance Sparse 3D Object Detection from Multi-Camera Videos"
authors: [Haisong Liu, Yao Teng, Tao Lu, Haiguang Wang, Limin Wang]
year: 2023
venue: ICCV 2023
arxiv_id: "2308.09244"
url: https://arxiv.org/abs/2308.09244
primary_category: perception
secondary_categories: []
keywords: [sparse-query, multi-camera-3d-detection, bev-pillars, scale-adaptive-attention, adaptive-spatio-temporal-sampling, adaptive-mixing, nuscenes]
one_line_summary: Fully-sparse query-based camera 3D detector that uses BEV pillar queries with scale-adaptive self-attention, adaptive spatio-temporal sampling, and adaptive mixing to match dense BEV detectors on nuScenes.
distilled_at: 2026-05-02
source_pdf: doc/papers/perception/sparsebev-iccv2023.pdf
---

# SparseBEV: High-Performance Sparse 3D Object Detection from Multi-Camera Videos

## Keywords
- sparse-query, multi-camera-3d-detection, bev-pillars, scale-adaptive-attention, adaptive-spatio-temporal-sampling, adaptive-mixing, nuscenes

## TL;DR
Sparse query-based multi-camera 3D detectors (e.g. DETR3D, PETR) are simpler and faster than dense BEV-encoder pipelines (BEVDet, BEVFormer) but historically trail them in accuracy. The authors argue the gap stems from low decoder adaptability in both BEV and image space, and introduce SparseBEV, which adds scale-adaptive self attention (SASA), adaptive spatio-temporal sampling, and adaptive mixing on top of pillar-shaped BEV queries. On nuScenes test, SparseBEV reaches 67.5 NDS, surpassing BEVFormerV2 by 2.7 NDS while remaining real-time.

## Problem & Motivation
Dense BEV detectors (BEVDet, BEVFormer, BEVDepth, SOLOFusion) construct an explicit BEV feature via complex view transformations and dense BEV encoders, paying high compute cost. Sparse query-based detectors avoid the dense BEV encoder, but DETR3D-style decoders rely on a single fixed reference point per query and static linear processing, which gives them a fixed local image-space receptive field and no multi-scale aggregation in BEV space. The authors trace the accuracy gap to two missing forms of *adaptability*: (i) in BEV space, queries cannot aggregate multi-scale features adaptively, and (ii) in image space, sampling cannot adapt to the wide range of object sizes induced by perspective.

## Innovation Points
- **Pillar-shaped queries** — each query is parameterized as a BEV pillar (translation, dimension, rotation, velocity, learnable feature), giving stronger spatial priors than DETR3D-style 3D reference points (+0.5 NDS over reference points in ablation).
- **Scale-adaptive self attention (SASA)** — a self-attention variant that adds a learned, head-specific receptive-field controller tau to bias attention by inter-query BEV distance, letting different heads cover different scales without an explicit BEV FPN. Heads spontaneously specialize: bus/truck queries acquire larger receptive fields than pedestrian/traffic-cone queries.
- **Adaptive spatio-temporal sampling** — sampling offsets are predicted from the query feature (not the reference point), warped across frames using both ego-motion (from ego pose) and per-query velocity-based object motion, then projected into multi-view, multi-scale image features.
- **Adaptive mixing** — borrowing AdaMixer, sampled features are decoded by query-conditioned dynamic weights applied as channel mixing followed by point mixing, replacing static linear layers.
- **Dual-branch (slow-fast) extension** — optional SlowFast-inspired split into a low-rate high-resolution slow stream and high-rate low-resolution fast stream for long-term temporal modeling, used for the strongest test-set numbers.

## Model Architecture
- 6 surround cameras, multi-frame video (default T = 8 frames, ~0.5 s spacing) -> per-frame ResNet-50 / ResNet-101 / V2-99 image backbone + FPN.
- N learnable BEV pillar queries, each with (x, y, z, w, l, h, theta, vx, vy) and a D-dim feature; z = 0, h ~ 4 m, velocity initialized to 0.
- Decoder repeated L = 6 times with shared weights:
  1. Scale-adaptive self attention (SASA) over queries: Attn(Q, K, V) = softmax(QK^T / sqrt(d) - tau * D) V, with tau predicted per-head from each query.
  2. Spatio-temporal sampling: predict S offsets per query, place P = T * S points along the pillar, warp via ego-pose and per-query velocity, project into each hit camera view and bilinearly sample multi-scale image features.
  3. Adaptive mixing: stack T * S points x C channels, apply query-conditioned channel mixing then point mixing (LayerNorm + ReLU), flatten and project.
  4. FFN, residuals, LayerNorms.
- Two MLP heads on the updated queries: classification and 3D box regression.
- Optional dual-branch (slow + fast) feature stream concatenated before adaptive mixing.
- V2-99 backbone reported at ~70 M parameters (vs. >300 M for BEVFormerV2 with InternImage-XL).

## Benchmark Results
Dataset: nuScenes 3D detection (1000 videos, 700/150/150 split, ~1.4 M boxes, 10 classes). Headline metric: NDS (composite of mAP + TP errors).

**nuScenes val split (ResNet50, 704x256):**

| Method | NDS | mAP | FPS |
|---|---|---|---|
| SOLOFusion | 53.4 | 42.7 | not reported here |
| StreamPETR (perspective pretraining) | 55.0 | 45.0 | not reported here |
| SparseBEV (900 queries) | 54.5 | 43.2 | not reported |
| **SparseBEV with perspective pretraining** | **55.8** | **44.8** | **23.5** |

**nuScenes val split (larger backbones):** SparseBEV with ResNet101, 1408x512 reaches 59.2 NDS / 50.1 mAP at 24 epochs, surpassing SOLOFusion (58.2 NDS / 48.3 mAP at 90 epochs + CBGS).

**nuScenes test split (V2-99 backbone, DD3D pretraining):**

| Method | NDS | mAP |
|---|---|---|
| BEVFormerV2 (InternImage-XL, future frames) | 64.8 | 58.0 |
| BEVDet-Gamma (Swin-B, future frames) | 66.4 | 58.6 |
| SparseBEV (single-branch) | 62.7 | 54.3 |
| SparseBEV (dual-branch) | 63.6 | 55.6 |
| **SparseBEV (with future frames)** | **67.5** | **60.3** |

Key ablations (val split, ResNet50):
- Replacing 3D reference points with BEV pillars: +0.5 NDS (55.1 -> 55.6).
- SASA vs. vanilla MHSA: +2.2 NDS, +4.0 mAP (53.4 -> 55.6 NDS).
- Removing temporal alignment entirely: NDS drops from 55.6 to 44.4 (-11.2); ego-only alignment recovers 54.2; ego + object alignment gives full 55.6 and cuts mAVE from 0.510 to 0.243.
- Adaptive mixing vs. attention-weight aggregation (DETR3D-style): +6.5 NDS; channel-then-point mixing beats point-then-channel.
- Performance improves monotonically with frames up to 8; 16 sampling points per frame is optimal.

## Limitations & Open Questions
- Heavy reliance on accurate ego-pose: removing ego-based temporal alignment costs roughly 10 NDS, and real-world IMU-derived poses may be noisier than the dataset-provided ones, threatening robustness.
- Inference latency scales linearly with the number of input frames because sampled features are stacked along the temporal dimension; long-horizon temporal context is not free.
- Dual-branch slow-fast design adds framework complexity and is not used by default; a more elegant decoupling of static appearance and temporal motion is left as future work.
- Evaluated only on nuScenes 3D detection; extension to BEV segmentation, occupancy prediction, and lane detection is mentioned as future work but not demonstrated.
