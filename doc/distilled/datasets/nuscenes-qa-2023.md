---
paper_id: 2024-nuscenes-qa
title: "NuScenes-QA: A Multi-Modal Visual Question Answering Benchmark for Autonomous Driving Scenario"
authors: [Tianwen Qian, Jingjing Chen, Linhai Zhuo, Yang Jiao, Yu-Gang Jiang]
year: 2024
venue: AAAI 2024
arxiv_id: "2305.14836"
url: https://arxiv.org/abs/2305.14836
primary_category: datasets
secondary_categories: [vla, perception]
keywords: [vqa, nuscenes, multi-modal, lidar-camera, scene-graph, bev, mcan, outdoor]
one_line_summary: First large-scale multi-modal VQA benchmark for autonomous driving with 34K nuScenes scenes and 460K QA pairs auto-generated via scene graphs and templates; baselines top out at 60.4% accuracy.
distilled_at: 2026-05-02
source_pdf: doc/papers/datasets/nuscenes-qa-2023.pdf
---

# NuScenes-QA: A Multi-Modal Visual Question Answering Benchmark for Autonomous Driving Scenario

## Keywords
- vqa, nuscenes, multi-modal, lidar-camera, scene-graph, bev, mcan, outdoor

## TL;DR
Existing VQA benchmarks are single-modal, single-frame, and indoor — none stress the multi-modal, multi-frame, outdoor demands of autonomous driving. The authors build NuScenes-QA, a 460K-QA-pair benchmark over 34K nuScenes scenes, generated automatically from 3D-detection-derived scene graphs and 66 manual templates spanning five question types (Existence, Counting, Object, Status, Comparison). Camera+LiDAR fusion baselines (MSMDFusion+MCAN) reach 60.4% top-1 accuracy versus 53.4% for a question-only blind model and 84.3% for a ground-truth-box upper bound, leaving substantial headroom.

## Problem & Motivation
Driving-scene understanding via VQA is a natural way to probe perception models and provide an interpretable user interface, but available benchmarks fall short on three axes simultaneously. Image-only sets such as VQA2.0, CLEVR, and GQA ignore depth and 3D structure. 3D VQA sets such as 3DQA and ScanQA cover only point clouds in static indoor scans. Driving-language efforts (Talk2Car, Refer-KITTI) focus on object referral or tracking, not high-level reasoning. None evaluate models on multi-modal (camera + LiDAR), multi-frame, outdoor, dynamic-foreground reasoning, which is precisely the regime self-driving systems must handle.

## Innovation Points
- **First multi-modal driving VQA benchmark** — 34,149 scenes and 459,941 QA pairs covering camera images and LiDAR point clouds across nuScenes train/val splits (377K train / 83K test).
- **Scene-graph-driven auto-annotation** — converts each nuScenes keyframe into a scene graph (object nodes with attributes, edges as one of six relative directions: front, back, front-left, front-right, back-left, back-right), enabling templated QA generation without per-pair labeling.
- **66 question templates across 5 categories** — Existence, Counting, Object (recognition), Status (moving/parked/stopped), and Comparison; each split into zero-hop (no spatial reasoning) and one-hop (one relational step) for difficulty stratification.
- **Post-processing rules** — strips degenerate combinations ("standing cars", "parked pedestrians"), caps counting answers at 10, and rewrites ego-as-object phrasing ("the me" → "me") to balance the answer distribution and avoid language shortcuts.
- **Baseline suite** — image-only (BEVDet), LiDAR-only (CenterPoint), fusion (MSMDFusion), each combined with BUTD or MCAN QA heads, plus a Q-Only blind baseline and a GroundTruth upper bound.

## Model Architecture
The released benchmark and the reference baseline both follow this flow:
- Inputs: 6-camera surround images and LiDAR point cloud per keyframe (2 Hz nuScenes annotation cadence); single-frame is supported, with multi-frame extensions left to users.
- Image branch: ResNet + FPN backbone -> per-pixel depth distribution and Lift-Splat-Shoot-style view transformer -> image BEV feature M_I in R^{H x W x d_m}.
- LiDAR branch: voxelization -> 3D sparse convolutional encoder -> Z-axis pooling -> point-cloud BEV feature M_P in R^{H x W x d_m}.
- Fused BEV: M = M_I + M_P (or single modality variant).
- Region proposals: 3D detector (BEVDet / CenterPoint / MSMDFusion) emits 3D boxes; boxes are projected to BEV with a heading-rotation formula and cross-product pixel-membership test, then mean-pooled to give object embeddings O in R^{N x d_m}.
- Question encoding: GloVe tokens -> single-layer biLSTM -> word features Q in R^{n_q x d}.
- QA head: MCAN (6-layer encoder-decoder, d_m = 512) — stacked self-attention over text and visual streams plus cross-attention; fused features go through MLP to predict the answer over a closed answer space.
- Training: Adam, lr 1e-4 with half-decay every 2 epochs, batch 256 on 2 RTX 3090 GPUs; standard cross-entropy loss.

## Benchmark Results
**NuScenes-QA test split, top-1 accuracy (%):**

| Model | Exist (All) | Count (All) | Object (All) | Status (All) | Comparison (All) | Acc |
|---|---|---|---|---|---|---|
| Q-Only (blind) | 79.6 | 17.2 | 42.0 | 51.3 | 66.9 | 53.4 |
| BEVDet+BUTD | 83.7 | 20.0 | 48.8 | 52.0 | 67.7 | 57.0 |
| CenterPoint+BUTD | 84.1 | 21.3 | 49.2 | 55.9 | 69.2 | 58.1 |
| MSMDFusion+BUTD | 85.1 | 23.2 | 52.3 | 59.5 | 65.8 | 59.8 |
| GroundTruth+BUTD | 92.6 | 57.5 | 76.0 | 87.6 | 78.1 | 79.2 |
| BEVDet+MCAN | 84.2 | 20.4 | 51.2 | 54.7 | 67.4 | 57.9 |
| CenterPoint+MCAN | 84.8 | 20.8 | 52.3 | 59.8 | 70.0 | 59.5 |
| **MSMDFusion+MCAN** | **85.4** | **22.2** | **54.3** | **60.6** | **69.7** | **60.4** |
| GroundTruth+MCAN | 97.4 | 46.2 | 88.2 | 96.8 | 90.2 | 84.3 |

Headline: best fusion baseline reaches 60.4% versus 53.4% Q-Only and 84.3% GT upper bound. LiDAR-only CenterPoint (59.5%) outperforms camera-only BEVDet (57.9%), reflecting the benchmark's emphasis on geometric/spatial reasoning over texture. Counting is the hardest category — best model achieves only 23.2%.

Ablations on CenterPoint+MCAN:
- Adding detected boxes to object embeddings: 59.5 -> 58.9 (slight drop, attributed to detector noise); adding GT boxes: 70.8 -> 84.3 (+13.5).
- BEV crop strategy: rotated box 59.5 vs. circumscribed rectangle 58.8.
- BEV pooling: mean 59.5 vs. max 58.9 (mean preserved overall structure better than texture-focused max).

## Limitations & Open Questions
- Baselines saturate well below the GroundTruth upper bound (60.4% vs. 84.3%), driven largely by 3D-detector immaturity — a dedicated QA-aware perception stack is left as future work.
- Counting remains a long-standing weak point (best 23.2%); no specialized counting module is offered.
- QA pairs are template-generated from scene graphs, so linguistic diversity and open-vocabulary reasoning are bounded by the 66 templates and the nuScenes label vocabulary.
- Despite multi-frame data being available, the released baselines are evaluated single-frame; temporal reasoning utility is not quantified.
- No evaluation of large vision-language models (e.g., LLaVA-style or driving VLMs) — the paper predates that wave; relative difficulty for modern VLMs is open.
