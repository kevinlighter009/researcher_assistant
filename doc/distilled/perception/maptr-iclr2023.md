---
paper_id: 2023-maptr
title: "MapTR: Structured Modeling and Learning for Online Vectorized HD Map Construction"
authors: [Bencheng Liao, et al.]
year: 2023
venue: ICLR 2023
arxiv_id: "2208.14437"
url: https://arxiv.org/abs/2208.14437
primary_category: perception
secondary_categories: [e2e_planning]
keywords: [hd-map, vectorized-mapping, bev, detr, permutation-equivalent, hierarchical-matching, nuscenes]
one_line_summary: End-to-end DETR-like Transformer for online vectorized HD map construction with permutation-equivalent point-set modeling and hierarchical bipartite matching, real-time at 25.1 FPS on nuScenes.
distilled_at: 2026-05-02
source_pdf: doc/papers/perception/maptr-iclr2023.pdf
---

# MapTR: Structured Modeling and Learning for Online Vectorized HD Map Construction

## Keywords
- hd-map, vectorized-mapping, bev, detr, permutation-equivalent, hierarchical-matching, nuscenes

## TL;DR
Online HD map construction had been split between rasterized BEV-segmentation (no instance-level vectors) and slow auto-regressive vectorized methods (e.g. VectorMapNet). The authors propose MapTR, a one-stage DETR-style Transformer that models each map element as a point set with a group of equivalent permutations, and supervises it via hierarchical (instance-then-point) bipartite matching with point2point and edge-direction losses. On nuScenes, MapTR-tiny reaches 58.7 mAP at 11.2 FPS and MapTR-nano runs at 25.1 FPS while still beating prior camera-only SOTA by 5.0 mAP.

## Problem & Motivation
HD maps must be reconstructed online from on-vehicle sensors instead of relying on offline SLAM pipelines. Prior approaches each have a clear failure mode:

- BEV-segmentation methods (HDMapNet and others) produce only rasterized maps, lacking instance-level vector structure needed for downstream planning/prediction; HDMapNet additionally needs heavy heuristic post-processing to recover instances.
- VectorMapNet, the first end-to-end vectorized framework, uses a coarse-to-fine cascade with an auto-regressive decoder that emits points sequentially, leading to slow inference and ambiguity about point ordering.
- Map elements (lane dividers, pedestrian crossings, road boundaries) lack a canonical point ordering: a polyline can be traversed from either endpoint and a polygon can be ordered from any vertex in either direction. Imposing a fixed permutation as the supervision target conflicts with these equivalent permutations and destabilizes training.

## Innovation Points
- **Permutation-equivalent modeling** — each map element is represented as a point set V plus a group Gamma of equivalent permutations (2 for polylines, 2*N_v for polygons), removing ordering ambiguity and stabilizing training.
- **Hierarchical bipartite matching** — first match instances (DETR-style Hungarian assignment with Focal + position cost), then perform point-level matching by selecting the lowest-cost permutation in Gamma using Manhattan distance.
- **Hierarchical query embedding** — every point query q^hie_ij = q^ins_i + q^pt_j combines an instance query with a shared point query, so a single Transformer decoder predicts all instances and all points in parallel.
- **Point2point + edge-direction loss** — Manhattan point2point loss supervises vertex positions and a cosine-similarity edge-direction loss supervises the polyline/polygon edges, yielding shape supervision at both vertex and edge level.
- **Structured one-stage parallel decoder** — replaces VectorMapNet's two-stage auto-regressive pipeline, giving real-time inference (25.1 FPS) without per-point sequential decoding.

## Model Architecture
- Input: 6 surround-view camera images (also compatible with LiDAR/RADAR; reported results use camera-only).
- Map encoder:
  - Backbone: ResNet-50 (MapTR-tiny) or ResNet-18 (MapTR-nano).
  - 2D-to-BEV transform: GKT by default (LSS, Deformable Attention, IPM also tested in ablations).
  - Output: BEV feature map B in R^{H x W x C}.
- Map decoder:
  - Hierarchical queries: N instance queries x N_v point queries; each point query is q^hie_ij = q^ins_i + q^pt_j (point queries shared across instances).
  - Cascaded Transformer decoder layers; each layer applies MHSA across hierarchical queries (inter- and intra-instance) and Deformable Attention (BEVFormer-style) to the BEV features around predicted reference points.
  - Hierarchical bipartite matching: instance-level Hungarian assignment, then point-level selection of the optimal permutation in Gamma.
- Heads: classification branch (instance class score) and point-regression branch outputting a 2N_v vector of normalized BEV (x, y) coordinates per element.
- Output: vectorized HD map covering pedestrian crossing, lane divider, road boundary over [-15, 15] m (X) and [-30, 30] m (Y).
- Training loss: L = lambda * L_cls + alpha * L_p2p + beta * L_dir, with beta = 5e-3.
- Training: 8x RTX 3090, AdamW + cosine annealing, batch size 32 (6 views each), 110 epochs default (24-epoch schedule also reported). Total parameter counts not stated for the full model, but the BEV transform module alone is ~36 M (GKT).

## Benchmark Results
Headline: on nuScenes val (Table 1), MapTR-tiny (camera, R50, 110 epochs) reaches 58.7 mAP at 11.2 FPS, +13.5 mAP over the strongest multi-modality baseline (VectorMapNet C&L, 45.2 mAP). MapTR-nano (R18) runs at real-time 25.1 FPS, 8x faster than the best prior camera-only method while still 5.0 mAP higher.

**nuScenes val, 3 map-element classes, AP at Chamfer thresholds {0.5, 1.0, 1.5} m:**
| Method                | Modality | Backbone           | Epochs | AP_ped | AP_div | AP_bnd | mAP  | FPS  |
|-----------------------|----------|--------------------|--------|--------|--------|--------|------|------|
| HDMapNet              | C        | Effi-B0            | 30     | 14.4   | 21.7   | 33.0   | 23.0 | 0.8  |
| HDMapNet              | C & L    | Effi-B0+PointPillars | 30  | 16.3   | 29.6   | 46.7   | 31.0 | 0.5  |
| VectorMapNet          | C        | R50                | 110    | 36.1   | 47.3   | 39.3   | 40.9 | 2.9  |
| VectorMapNet          | C & L    | R50+PointPillars   | 110    | 37.6   | 50.5   | 47.5   | 45.2 | -    |
| MapTR-nano            | C        | R18                | 110    | 39.6   | 49.9   | 48.2   | 45.9 | 25.1 |
| MapTR-tiny (24 ep)    | C        | R50                | 24     | 46.3   | 51.5   | 53.1   | 50.3 | 11.2 |
| **MapTR-tiny**        | C        | R50                | 110    | **56.2** | **59.8** | **60.1** | **58.7** | 11.2 |

Key ablations (MapTR-tiny on nuScenes val):
- Permutation-equivalent vs. fixed-order modeling (Table 2): 50.3 vs. 44.4 mAP -> +5.9 mAP, with the largest gain on pedestrian crossing (polygon class) at +11.9 AP.
- Edge-direction loss weight beta (Table 3): beta = 0 gives 48.2 mAP; beta = 5e-3 gives best 50.3 mAP; beta = 1e-2 drops to 48.3.
- 2D-to-BEV module (Table 4): IPM 46.2, LSS 49.5, Deformable Attention 49.7, GKT 50.3 mAP -- MapTR is robust across transforms; GKT chosen for deployment efficiency.

## Limitations & Open Questions
- Evaluated only on nuScenes val with 3 map-element classes (pedestrian crossing, lane divider, road boundary); generalization to more classes and other datasets (Argoverse, internal logs) not reported.
- Open-loop only -- no closed-loop driving or downstream planning evaluation; the paper merely conjectures MapTR as a building block for prediction/planning.
- Total parameter count of the full model is not reported (only the 2D-to-BEV module is sized), so deployment cost is partly opaque.
- Permutation group Gamma is enumerated explicitly (2 for polylines, 2*N_v for polygons); scaling to map elements with richer topological structure (e.g. multi-branch lane graphs, intersections with explicit connectivity) is not addressed.
- N_v (points per element) is fixed; how performance degrades for very long, curvy boundaries that need denser sampling is not characterized.
