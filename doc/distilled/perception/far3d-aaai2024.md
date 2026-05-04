---
paper_id: 2024-far3d
title: "Far3D: Expanding the Horizon for Surround-view 3D Object Detection"
authors: [Xiaohui Jiang, Shuailin Li, Yingfei Liu, Shihao Wang, Fan Jia, Tiancai Wang, Lijin Han, Xiangyu Zhang]
year: 2024
venue: AAAI 2024
arxiv_id: "2308.09616"
url: https://arxiv.org/abs/2308.09616
primary_category: perception
secondary_categories: []
keywords: [long-range-3d-detection, sparse-query, 2d-to-3d-priors, perspective-aware-aggregation, 3d-denoising, argoverse2, surround-view]
one_line_summary: Sparse query-based surround-view 3D detector that expands range to 150 m by seeding 3D adaptive queries from 2D proposals, with perspective-aware aggregation and range-modulated denoising.
distilled_at: 2026-05-02
source_pdf: doc/papers/perception/far3d-aaai2024.pdf
---

# Far3D: Expanding the Horizon for Surround-view 3D Object Detection

## Keywords
- long-range-3d-detection, sparse-query, 2d-to-3d-priors, perspective-aware-aggregation, 3d-denoising, argoverse2, surround-view

## TL;DR
Surround-view camera 3D detectors mostly target ~50 m and degrade when scaled to long range due to query sparsity, weak distant-object recall, and unstable convergence. Far3D keeps a sparse query design but augments learnable global queries with 3D adaptive queries derived from high-quality 2D proposals plus predicted depths, adds a perspective-aware multi-scale/multi-view aggregation, and a range-modulated 3D denoising scheme. On Argoverse 2 (150 m, 26 categories) it reaches 0.244 mAP / 0.181 CDS with a VoV-99 camera-only model, beating prior surround-view methods and several LiDAR baselines.

## Problem & Motivation
Existing surround-view 3D detectors (BEVFormer, BEVDepth, PETR, StreamPETR, Sparse4D) focus on ~50 m perception (nuScenes-style). Naively scaling them to ~150 m has two failure modes:
- **Dense BEV methods** suffer quadratic compute growth as the BEV grid expands.
- **Sparse query methods** keep cost bounded but a fixed set of global queries cannot cover a much larger 3D volume; recall on distant objects collapses (paper Fig. 1 shows R@3D = 0.06 at 100–150 m vs. R@2D = 0.46).

Prior 2D-prior methods (SimMOD, MV2D) use 2D proposals only for close-range tasks and discard learnable queries. Directly lifting 2D proposals to 3D for long range is also fragile: depth errors and frustum-shaped error propagation grow with range, producing many noisy positives that destabilise training and make the model overfit close, dense objects while ignoring sparse distant ones.

## Innovation Points
- **3D adaptive queries from 2D priors** — a YOLOX-style 2D head plus a lightweight DepthNet produce reliable 2D boxes and per-pixel depths; reliable proposals (score > tau, default 0.1) are projected to 3D centers and encoded as positional + semantic queries that complement the learned 3D global queries.
- **Perspective-aware aggregation** — instead of attending to a single feature level (as in StreamPETR), each query learns 3D sampling offsets and pulls features across multiple FPN scales and camera views via 3D deformable attention with a squeeze-and-excitation gate, so distant queries can favour high-resolution features and close queries low-resolution context.
- **Range-modulated 3D denoising** — extends DN-DETR to 3D by injecting positive (inside-GT) and negative noisy queries whose noise magnitude scales with object distance and box size, mitigating range-imbalanced regression difficulty and frustum error propagation.
- **Long-range sparse design that beats LiDAR baselines** — first surround-view camera-only method to outperform CenterPoint, FSD and VoxelNeXt on Argoverse 2 at 150 m range.

## Model Architecture
- Inputs: 7 surround-view ring cameras (Argoverse 2) or 6 cameras (nuScenes), with temporal query propagation following StreamPETR.
- Backbone + FPN: VoVNet-99 (FCOS3D-pretrained) or ViT-Large (Objects365 + COCO-pretrained); FPN gives 4-level features at strides 1/8, 1/16, 1/32, 1/64.
- 2D branch: YOLOX-style anchor-free detector head + DepthNet that classifies discretised depth bins. Reliable 2D boxes (score > tau) and depths are combined with intrinsics/extrinsics to project box centres to 3D proposal centres c_3d.
- Adaptive query construction: Q = PosEmbed(c_3d) + SemEmbed(z_2d, s_2d), where z_2d is the sampled FPN feature at the 2D box centre and s_2d is the 2D confidence.
- Decoder: N transformer layers; each layer has self-attention over (global queries concatenated with adaptive queries), perspective-aware 3D deformable aggregation across FPN scales/views, and an FFN.
- Range-modulated denoising branch: per-GT, K paired positive/negative noisy queries are added during training; positive offsets are linear in box scale, negative offsets follow log/sqrt/linear/fixed schedules of GT distance (log + 2 negatives chosen as best).
- Output: 3D bounding boxes for 26 Argoverse 2 categories (or 10 nuScenes categories), with perception range 152.4 m x 152.4 m on Argoverse 2.
- Training: AdamW, weight decay 0.01, lr 2e-4, batch size 8, 6 epochs on Argoverse 2 (60 epochs and bs 32 on nuScenes with ResNet-101). Default 644 global queries.

## Benchmark Results
**Argoverse 2 val (150 m, 26 classes), camera-only:**

| Method        | Backbone | Image size | mAP up | CDS up | mATE down | mAOE down |
|---------------|----------|------------|--------|--------|-----------|-----------|
| BEVStereo     | VoV-99   | 960x640    | 0.146  | 0.104  | 0.847     | 0.901     |
| SOLOFusion    | VoV-99   | 960x640    | 0.149  | 0.106  | 0.934     | 0.779     |
| PETR          | VoV-99   | 960x640    | 0.176  | 0.122  | 0.911     | 0.819     |
| Sparse4Dv2    | VoV-99   | 960x640    | 0.189  | 0.134  | 0.832     | 0.723     |
| StreamPETR    | VoV-99   | 960x640    | 0.203  | 0.146  | 0.843     | 0.650     |
| **Far3D**     | VoV-99   | 960x640    | **0.244** | **0.181** | **0.796** | **0.538** |
| **Far3D**     | ViT-L    | 1536x1536  | **0.316** | **0.239** | 0.732     | 0.459     |

Camera Far3D (ViT-L) also surpasses LiDAR baselines on the same split: CenterPoint 0.274 mAP / 0.210 CDS, FSD 0.291 / 0.233, VoxelNeXt 0.307 / 0.225 vs. Far3D 0.316 / 0.239. LiDAR methods retain a lower mATE (better localisation), while Far3D has lower mAOE (better orientation).

**nuScenes generalisation:** Far3D ResNet-101 val 0.510 mAP / 0.594 NDS (vs. StreamPETR 0.504 / 0.592, Sparse4Dv2 0.505 / 0.594); ViT-L test 0.635 mAP / 0.687 NDS (vs. StreamPETR 0.620 / 0.676).

**Ablations (Argoverse 2 val, Table 3):**
- StreamPETR baseline: 20.3 mAP / 14.6 CDS.
- + Adaptive query: 22.4 / 16.1 (+2.1 / +1.5).
- + Perspective-aware aggregation: 23.4 / 17.3 (+1.0 / +1.2).
- + Range-modulated 3D denoising: 24.4 / 18.1 (+1.0 / +0.8); total +4.1 mAP / +3.5 CDS.
- 2D score threshold tau = 0.1 is optimal (Table 4).
- log noise + 2 negative samples is best for denoising (Table 5).
- Global-query count: StreamPETR fails to converge (NaN) at 100 queries and only works at 644; Far3D stays stable (23.5 mAP at 100, 24.4 at 644), showing adaptive queries compensate for fewer global queries (Table 6).

## Limitations & Open Questions
- Long-tail Argoverse 2 classes still have low per-class AP, dragging the 26-class mean down (acknowledged by authors).
- Authors argue a single mAP/CDS computed jointly over close and far objects may not be the right metric for long-range evaluation; better range-aware metrics are an open question.
- Compute / latency cost of the ViT-L 1536x1536 configuration is not reported.
- Depth quality remains the main bottleneck for distant objects; reliance on DepthNet means failure modes inherit from monocular depth estimation.
- No closed-loop or downstream planning evaluation; only open-loop detection metrics on Argoverse 2 and nuScenes.
