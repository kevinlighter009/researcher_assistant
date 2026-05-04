---
paper_id: 2024-drivedreamer-2
title: "DriveDreamer-2: LLM-Enhanced World Models for Diverse Driving Video Generation"
authors: [Guosheng Zhao, Xiaofeng Wang, Zheng Zhu, et al.]
year: 2024
venue: arXiv
arxiv_id: "2403.06845"
url: https://arxiv.org/abs/2403.06845
primary_category: world_model
secondary_categories: [diffusion_decoder, datasets]
keywords: [world-model, multi-view-video-generation, llm-trajectory, hdmap-diffusion, unimvm, svd, nuscenes]
one_line_summary: LLM converts user text into agent trajectories, a diffusion HDMap generator builds the road, and UniMVM produces multi-view driving videos with FID 11.2 / FVD 55.7 on nuScenes.
distilled_at: 2026-05-02
source_pdf: doc/papers/world_model/drivedreamer-2-2024.pdf
---

# DriveDreamer-2: LLM-Enhanced World Models for Diverse Driving Video Generation

## Keywords
- world-model, multi-view-video-generation, llm-trajectory, hdmap-diffusion, unimvm, svd, nuscenes

## TL;DR
Prior driving world models (DriveDreamer, GAIA-1, Drive-WM, Panacea) require structured conditions such as 3D boxes, HDMaps, or optical flow, which limits user-friendliness and diversity. DriveDreamer-2 finetunes a GPT-3.5 LLM over a curated trajectory-generation function library to turn free-text queries into agent trajectories, then uses a diffusion-based HDMap generator and a Unified Multi-View Video Model (UniMVM) built on Stable Video Diffusion to produce multi-view driving clips. On nuScenes it reaches FID 11.2 and FVD 55.7 — relative improvements of about 30% and 50% over the previous best — and synthetic data lifts StreamPETR detection / tracking by ~4% / ~8%.

## Problem & Motivation
World-model approaches such as DriveDreamer, Drive-WM, MagicDrive, Panacea, GAIA-1, and ADriver-I rely on dataset-specific or sophisticated annotations (3D boxes, HDMaps, optical flow, or real image frames) as conditioning. This dependence (i) blocks user-friendly generation of arbitrary scenarios such as "a vehicle cuts in on a rainy day" and (ii) constrains diversity, especially for uncommon long-tail events. Existing traffic simulators (LCTGen, CTG, CTG++) require detailed language descriptions or hand-designed loss functions, which is still cumbersome. The paper aims for the first user-friendly world model that takes only a text prompt and emits multi-view driving videos.

## Innovation Points
- **LLM-driven trajectory generation** — A trajectory function library of 18 functions (agent steering / acceleration / braking, pedestrian crossings, utilities) is used to manually curate Text-to-Python-Script pairs that finetune GPT-3.5; at inference the LLM emits a Python script that outputs an ego + agents trajectory array.
- **HDMap diffusion generator** — Reformulates background-element generation as conditional image synthesis: a 2D-conv stack encodes a BEV trajectory map into ControlNet-style features that condition an SD2.1 diffusion model to produce a 3-channel BEV HDMap (lane boundary, lane divider, pedestrian crossing) consistent with foreground trajectories.
- **UniMVM (Unified Multi-View Video Model)** — Concatenates the 6 surround views {FL, F, FR, BR, B, BL} into a single spatial patch and lets a single SVD-based diffusion model in-paint masked regions; one mask schedule unifies "no image", "first-frame multi-view", and "front-view video" conditioning while removing per-view cross-view attention parameters.
- **Direct image-plane projection of 3D boxes** — Unlike DriveDreamer, 3D-box conditions are projected directly onto the image plane and treated as a control signal, eliminating extra position/category embedding heads.
- **First user-friendly driving world model** — End-to-end pipeline (text -> trajectories -> HDMap -> multi-view video) supports uncommon scenarios such as cut-ins or night-time pedestrian crossings without structured user input.

## Model Architecture
- **Input**: a single user text query (e.g. "On a rainy day, there is a car cutting in").
- **Customized Traffic Simulation**:
  - Finetuned GPT-3.5 + function library -> Python script -> trajectory array (ego + other agents).
  - HDMap generator: BEV trajectory map T_b in R^{3 x H_b x W_b} -> diffusion model (SD2.1 backbone, ControlNet-style trainable layers, 55K iters, batch 24, resolution 512x512) -> BEV HDMap H_b in R^{3 x H_b x W_b}.
- **Conditioning tensors**: HDMap sequence H_i in R^{N x 3 x H x KW} and 3D-box sequence B_i in R^{N x C x H x KW} (C = number of categories, K = number of views) projected to the image plane.
- **UniMVM video generator**:
  - Backbone: Stable Video Diffusion (SVD); all params finetuned.
  - Three encoders embed HDMaps, 3D boxes, and (optionally) image frames into latent features y_H, y_B, y_I; concatenated with the noisy latent Z_t to form Z_in.
  - Spatial concatenation of K=6 views into a single patch (T x 3 x H x KW); cross-frame module operates on this patch; cross-view module is dropped.
  - A view/frame mask m selects the conditioning regime (no-image, first-frame multi-view, or front-view video).
- **Output**: multi-view driving videos at 6 views, N=8 frames per clip, resolution 256 x 448.
- **Training**: nuScenes (~700 train scenes, 12 Hz preprocessed), 200K iterations, batch size 1, AdamW, lr 5e-5, NVIDIA A800 80GB GPUs.

## Benchmark Results
**nuScenes validation set (FID / FVD, lower is better):**
| Method | Conditions | FID ↓ | FVD ↓ |
|---|---|---|---|
| DriveDreamer | none | 26.8 | 353.2 |
| **DriveDreamer-2** | none | **25.0** | **105.1** |
| Drive-WM | 3-view videos (generated) | 15.8 | 122.7 |
| **DriveDreamer-2** | 1-view video | 18.4 | **74.9** |
| DriveDreamer | 1st-frame multi-view image | 14.9 | 340.8 |
| DrivingDiffusion | 1st-frame multi-view image (gen.) | 15.8 | 332.0 |
| Panacea | 1st-frame multi-view image (gen.) | 16.9 | 139.0 |
| **DriveDreamer-2** | 1st-frame multi-view image | **11.2** | **55.7** |

Relative gains vs previous best: ~30% FID, ~50% FVD.

**Downstream perception with synthetic augmentation (StreamPETR, ResNet-50, 256 x 448):**
- 3D detection (Tab. 2): with initial frame + real + generated, mAP 32.6 / NDS 45.2 (vs real-only 31.7 / 43.5); without initial frame, mAP 32.9 / NDS 45.4. Reported relative improvements ~3.8% mAP, ~4.4% NDS.
- Multi-object tracking (Tab. 3): with initial frame, AMOTA 31.2 / AMOTP 1.396 / IDS 542; without, AMOTA 31.3 / AMOTP 1.387 / IDS 593 (real-only baseline AMOTA 28.9 / AMOTP 1.419 / IDS 687). Reported relative improvements ~8.0% AMOTA, ~1.6% AMOTP (initial-frame setting); ~8.3% / ~2.3% (no-image setting).

**Ablations (Tab. 4-5):**
- DriveDreamer (SD1.4) -> SVD backbone + cross-view module: FID 14.9 -> 17.2, FVD 340.8 -> 94.6 (~70% FVD gain from SVD prior).
- SVD + UniMVM (no cross-view module): FID 11.2, FVD 55.7 -> ~80% FVD improvement vs DriveDreamer baseline.
- Conditions for DriveDreamer-2: none 25.0 / 105.1; 1-view video 18.4 / 74.9; 1st-frame multi-view 11.2 / 55.7.

## Limitations & Open Questions
- Trajectory function library is hand-curated (18 functions); scaling to fully open-vocabulary maneuvers and multi-agent interactions is not addressed.
- Evaluation is open-loop on nuScenes only; no closed-loop driving or cross-dataset generalization is reported.
- Generated clips are short (N = 8 frames at 12 Hz, ~0.67 s) and low-resolution (256 x 448); long-horizon temporal coherence and high-resolution generation are not evaluated.
- Inference cost of the GPT-3.5 + HDMap diffusion + SVD pipeline is not reported.
- UniMVM concatenates 6 views into one patch — scaling behaviour to more cameras / larger K is not analyzed.
