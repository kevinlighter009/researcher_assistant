---
paper_id: 2025-anchdrive
title: "AnchDrive: Bootstrapping Diffusion Policies with Hybrid Trajectory Anchors for End-to-End Driving"
authors: [Jinhao Chai, Anqing Jiang, Hao Jiang, Shiyi Mu, Zichong Gu, Hao Sun, Shugong Xu]
year: 2025
venue: arXiv
arxiv_id: "2509.20253"
url: https://arxiv.org/abs/2509.20253
primary_category: diffusion_decoder
secondary_categories: [e2e_planning]
keywords: [diffusion-policy, truncated-diffusion, hybrid-trajectory-anchors, multi-head-decoder, bev, vlm-command, navsim]
one_line_summary: Truncated diffusion policy bootstrapped from a hybrid set of static and dynamic, multi-head-generated trajectory anchors; reaches 85.5 EPDMS on NAVSIM v2 navtest with only 2 denoising steps.
distilled_at: 2026-05-02
source_pdf: doc/papers/diffusion_decoder/anchdrive-2025.pdf
---

# AnchDrive: Bootstrapping Diffusion Policies with Hybrid Trajectory Anchors for End-to-End Driving

## Keywords
- diffusion-policy, truncated-diffusion, hybrid-trajectory-anchors, multi-head-decoder, bev, vlm-command, navsim

## TL;DR
Standard diffusion-based driving policies are accurate but slow because they denoise from pure noise; fixed-anchor variants like DiffusionDrive denoise from a static vocabulary that cannot adapt to the current scene. AnchDrive bootstraps a truncated diffusion policy from a hybrid anchor set: a static vocabulary of human-driving priors plus four dynamic anchors produced in real time by a multi-head decoder over BEV, object, map, and VLM-command features. With only 2 denoising steps, AnchDrive reaches 85.5 EPDMS on the NAVSIM v2 navtest split, beating DiffusionDrive (V2-99) by 0.5 and Hydra-MDP++ (V2-99) by 0.4.

## Problem & Motivation
Single-trajectory end-to-end planners (UniAD, VAD, Transfuser) collapse multi-modal driving behavior into one mean prediction and fail in ambiguous, long-tail scenes (intersections, lane changes). Fixed discrete-anchor methods (VADv2, Hydra-MDP) discretize a fundamentally continuous control space using a large pre-defined vocabulary (e.g. 8,192 anchors), constraining expressiveness. Diffusion-based planners model the multi-modal trajectory distribution well but pay a heavy iterative-denoising cost at inference. DiffusionDrive's truncated diffusion strategy reduces steps by anchoring on a fixed trajectory set, but those anchors are scene-agnostic and cannot adapt to the immediate context. AnchDrive directly targets this gap: keep the truncation speed-up while making the anchors context-aware.

## Innovation Points
- **Hybrid trajectory anchors** — fuse a pre-sampled static anchor set (human-driving prior, k-means over nuPlan) with a small set of dynamically generated, scene-aware anchors; combines broad coverage with local relevance.
- **Multi-head dynamic anchor generator** — four parallel trajectory heads each consume one input stream (BEV, sparse object features, sparse map features, VLM high-level command) so different heads can specialize (e.g. one obeys a "left lane change" command while another avoids a nearby obstacle).
- **Truncated diffusion as anchor refinement** — instead of denoising from pure noise, the diffusion decoder predicts a residual offset between the closest hybrid anchor and ground truth, analogous to YOLO-style anchor-box regression.
- **Hybrid dense+sparse perception** — dense BEV (128x128 over 64x64 m) for implicit scene context plus a sparse branch producing 3D detections and vectorized HD-map elements; sparse outputs feed the planner and also support explicit collision/drivable-area checks.
- **Aggressive anchor compression** — drops the trajectory-anchor count from VADv2's 8,192 to just 20 (~400x reduction) while still improving EPDMS by 8.9 over VADv2.

## Model Architecture
- Inputs: multi-view cameras (NAVSIM provides 8 cameras, fused 5-LiDAR cloud at 2 Hz; AnchDrive itself is reported as Camera-Only in the main result table).
- Image encoder feeds a Hybrid Perception module with two branches:
  - Dense branch — BEVFormer-style projection to a 128x128 BEV feature map over a 64x64 m ego-centric area.
  - Sparse branch — Sparse Aggregate + a Det Head (3D boxes: pose, size, heading, velocity) and a Map Head (vectorized lanes/edges/stop lines as point sequences); outputs MLP-encoded into object and map embeddings.
- A VLM produces high-level driving commands (e.g. "KEEP", "LEFT LANE CHANGE") encoded by a CMD encoder.
- Dynamic Anchor Generator — multi-head attention fuses {BEV feature, object instances, map instances, command embedding}; four parallel Trajectory Heads each emit one dynamic anchor (4 dynamic anchors total).
- Hybrid Trajectory Anchors = 4 dynamic anchors fused with the pre-sampled static anchor set (~16, since the final total is 20 per the experiments section); k-means-clustered over nuPlan human driving data.
- Diffusion Decoder — a conditional DDPM denoiser epsilon_theta(tau_t, t, z) with z = perception conditioning; uses truncated diffusion initialized from the hybrid anchors and predicts residual offsets.
- Output: refined ego trajectory; final model uses 2 denoising steps.
- Training data / total params: not reported. Backbone reported in headline result: V2-99 (with R34 variants for ablation comparisons).

## Benchmark Results
**NAVSIM v2 navtest (closed-loop, EPDMS-based):**

| Method            | Encoder | EPDMS |
|-------------------|---------|-------|
| Transfuser        | R34     | 76.7  |
| VADv2             | R34     | 76.6  |
| HydraMDP          | R34     | 79.8  |
| HydraMDP++        | R34     | 81.4  |
| Diffusiondrive    | R34     | 84.3  |
| DriveSuprim       | R34     | 83.1  |
| PRIX              | R34     | 84.2  |
| Diffusiondrive    | V2-99   | 85.0  |
| HydraMDP++        | V2-99   | 85.1  |
| **AnchDrive**     | V2-99   | **85.5** |
| Human Agent (ref) | -       | 90.3  |

Sub-score breakdown for AnchDrive: NC 98.0, DAC 97.2, DDC 99.6, TL 99.8, EP 87.2, TTC 97.1, LK 97.7, HC 98.3, EC 87.9.

Headline gains stated by the authors:
- +8.9 EPDMS over VADv2 while shrinking anchor count from 8,192 to 20 (~400x reduction).
- +5.7 over Hydra-MDP, +4.1 over Hydra-MDP++ (R34 backbones).
- +1.2 over DiffusionDrive (R34, the closest truncated-diffusion baseline) and surpasses it on every sub-score.

**Trajectory-head ablation (Table 2, V2-99):** EPDMS climbs 84.5 (no dynamic heads) -> 85.0 (+BEV head) -> 85.2 (+object head) -> 85.3 (+map head) -> 85.5 (+VLM-command head). Each branch contributes; the VLM command provides the final boost.

**Denoising-step ablation (Table 3):** EPDMS is essentially flat across 1-5 steps (85.43-85.49), confirming that with high-quality anchor initialization extra steps yield no monotonic gain; 2 steps chosen as the latency/quality trade-off.

## Limitations & Open Questions
- Wall-clock latency / FLOPs / parameter counts are not reported despite efficiency being the main motivation; only "denoising steps" is given as a proxy.
- Static anchor set size, the exact static/dynamic fusion rule, and the residual-offset training loss are not detailed in the paper text.
- Evaluation limited to a single benchmark (NAVSIM v2 navtest); no cross-dataset or real-vehicle generalization study despite the "strong generalizability" claim in the abstract.
- The VLM is treated as an off-the-shelf command source; which model is used, how commands are produced, and the failure modes when commands are wrong are not analyzed.
- Gap to the Human Agent reference (85.5 vs 90.3 EPDMS) remains substantial, especially on EP and EC sub-scores.
