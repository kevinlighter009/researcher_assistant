---
paper_id: 2024-streammapnet
title: "StreamMapNet: Streaming Mapping Network for Vectorized Online HD Map Construction"
authors: [Tianyuan Yuan, Yicheng Liu, Yue Wang, Yilun Wang, Hang Zhao]
year: 2024
venue: WACV 2024
arxiv_id: "2308.12570"
url: https://arxiv.org/abs/2308.12570
primary_category: perception
secondary_categories: [e2e_planning]
keywords: [hd-map, vectorized-map, bev, streaming-temporal-fusion, multi-point-attention, nuscenes, argoverse2]
one_line_summary: Online vectorized HD-map model that streams memory features (queries + BEV) across frames and uses Multi-Point Attention to handle elongated map elements at 100x50m range, 14.2 FPS.
distilled_at: 2026-05-02
source_pdf: doc/papers/perception/streammapnet-wacv2024.pdf
---

# StreamMapNet: Streaming Mapping Network for Vectorized Online HD Map Construction

## Keywords
- hd-map, vectorized-map, bev, streaming-temporal-fusion, multi-point-attention, nuscenes, argoverse2

## TL;DR
Prior online vectorized HD map methods (VectorMapNet, MapTR) only consume single frames and break under occlusions or when the perception range is enlarged from 60x30 m to 100x50 m. The authors propose StreamMapNet, which (1) replaces deformable DETR cross-attention with Multi-Point Attention that uses all predicted polyline points as reference points to capture long, irregular map elements, and (2) streams temporal information by propagating top-k object queries and a GRU-fused, ego-warped BEV memory across frames. On a re-balanced Argoverse2 split at 100x50 m, StreamMapNet reaches 51.2 mAP vs 40.2 for MapTR while running at 14.2 FPS.

## Problem & Motivation
Online vectorized HD-map construction is dominated by single-frame DETR-style models (VectorMapNet, MapTR, BeMapNet). The authors flag two concrete failure modes: (1) Small perception range — these models are typically trained at 60x30 m; pushing to 100x50 m causes large mAP drops because conventional deformable attention assigns one local reference point per query, which mismatches the elongated, non-local geometry of lane dividers and road boundaries. (2) No temporal information — single-frame inputs cannot recover map elements that are momentarily occluded (e.g. by a passing truck) and produce temporally inconsistent maps that are problematic for downstream planning. Additionally, the authors find the standard nuScenes train/val split has more than 84% location overlap (and 54% on Argoverse2), which lets models memorize rather than generalize, biasing the benchmark.

## Innovation Points
- **Multi-Point Attention** — replaces the single per-query reference point of deformable DETR with N_p reference points, one per predicted polyline vertex from the previous decoder layer; preserves O(N_p) complexity while covering elongated, non-local map shapes.
- **Streaming Query Propagation** — propagates top-k highest-confidence queries (and their predicted points, transformed into the new ego frame via a 4x4 matrix, then refined by an MLP) from frame t-1 into frame t, concatenated with N_q - k fresh queries; an auxiliary L_trans loss supervises the transformation.
- **Streaming BEV Fusion** — warps the previous BEV feature with ego pose and fuses it with the current BEV via a GRU plus LayerNorm, providing dense temporal memory in addition to sparse query memory.
- **Direct point regression** — predicts absolute polyline coordinates with a shared regression branch instead of residual offsets, matching the Multi-Point Attention design.
- **Re-split benchmarks** — releases new non-overlapping train/val splits for nuScenes (Roddick & Cipolla) and Argoverse2 to address the train/val location overlap that inflates prior numbers.

## Model Architecture
- Inputs: synchronized surround-view camera images (6 on nuScenes, 7 on Argoverse2 at 1550x2048; downsampled to 480x800 / 608x608 for the model). Argoverse2 frame rate set to 2 Hz to match nuScenes.
- Image backbone: ResNet-50 + FPN, shared across views.
- BEV encoder: single-layer BEVFormer to lift 2D features to F_BEV in R^{C x H x W}.
- Decoder: DETR-style transformer with N_q = 100 map queries; cross-attention replaced by Multi-Point Attention (N_off = 1 sampling offsets per point, N_p = 20 polyline points per query). Each query outputs class score + N_p 2D points (one of pedestrian crossing / lane divider / road boundary).
- Temporal fusion (streaming): (a) Query Propagation — top k = 33 queries from t-1 are ego-transformed and concatenated after the first decoder layer (Fig. 4); (b) BEV Fusion — F_BEV(t-1) is warped to t and fused with F_BEV(t) via GRU + LayerNorm (Fig. 5). Memory features are detached (no gradient through time).
- Losses: line SmoothL1 loss with permutation matching (from MapTR), Focal classification loss, transformation auxiliary loss; weights lambda_1 = 50.0, lambda_2 = 5.0, lambda_3 = 5.0.
- Training: 8 GTX3090 GPUs, batch size 32, AdamW, lr 5e-4, 24 epochs on nuScenes / 30 on Argoverse2, first 4 epochs trained single-frame to stabilize streaming; each training sequence is randomly split into 2 halves per epoch for diversity.

## Benchmark Results
**Argoverse2 new split (100x50 m, AP / mAP):**

| Method            | AP_ped | AP_div | AP_bound | mAP   | FPS  |
|-------------------|--------|--------|----------|-------|------|
| VectorMapNet      | 32.4   | 20.6   | 24.3     | 25.7  | 5.5  |
| MapTR             | 46.3   | 36.3   | 38.0     | 40.2  | 18.0 |
| **StreamMapNet**  | **60.5** | **44.4** | **48.6** | **51.2** | 14.2 |

Argoverse2 new split (60x30 m): StreamMapNet 58.1 mAP vs MapTR 51.1, VectorMapNet 36.1.

**nuScenes new split:** at 30 m, StreamMapNet 33.9 mAP vs MapTR 20.9 (+13.0); at 50 m, 23.0 vs 14.8 (+8.2). All methods drop substantially vs. Argoverse2, attributed to fewer/lower-resolution cameras and only two cities of training data.

**Original splits:** Argoverse2 50 m — StreamMapNet 57.7 vs MapTR 47.5 vs VectorMapNet 30.2. nuScenes 30 m — StreamMapNet 62.9 vs BeMapNet 59.8 vs MapTR 48.7. Moving from original to new splits costs ~50% mAP for all methods, evidencing the overfitting problem.

**Ablations (Argoverse2 new split, 50 m, mAP):**
- (a) Single-frame baseline w. relative predict: 33.7
- (b) - Multi-Point Attention (replaced with conventional deformable): not reported (model fails to converge)
- (c) + Direct predict: 41.7
- (d) + Query propagation (no transformation loss): 42.8
- (e) + Transformation loss: 43.7
- (f) + BEV fusion: 46.1
- (g) + Image size 608x608: 51.2

## Limitations & Open Questions
- nuScenes results lag Argoverse2 by a wide margin even with the streaming design — capacity / camera setup of nuScenes may limit the approach; not addressed in the paper.
- Memory features are propagated without gradient through time (detached), so very long-horizon temporal credit assignment is not learned.
- Hyperparameters such as k = 33 propagated queries and N_p = 20 polyline points are fixed; sensitivity is not reported.
- Authors note the model can still emit false predictions in challenging scenes and HD-map data raises privacy/legal concerns; closed-loop or downstream planning evaluation is not provided.
