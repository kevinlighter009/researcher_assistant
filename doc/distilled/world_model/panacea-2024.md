---
paper_id: 2024-panacea
title: "Panacea: Panoramic and Controllable Video Generation for Autonomous Driving"
authors: [Yuqing Wen, et al.]
year: 2024
venue: CVPR 2024
arxiv_id: "2311.16813"
url: https://arxiv.org/abs/2311.16813
primary_category: world_model
secondary_categories: [perception, datasets]
keywords: [video-generation, multi-view, bev-conditioned, controlnet, 4d-attention, diffusion, nuscenes]
one_line_summary: Two-stage latent-diffusion generator producing BEV-controlled, panoramic 6-view driving videos via decomposed 4D attention; synthetic data lifts StreamPETR NDS by +2.3 on nuScenes.
distilled_at: 2026-05-02
source_pdf: doc/papers/world_model/panacea-2024.pdf
---

# Panacea: Panoramic and Controllable Video Generation for Autonomous Driving

## Keywords
- video-generation, multi-view, bev-conditioned, controlnet, 4d-attention, diffusion, nuscenes

## TL;DR
BEV perception models for autonomous driving need large annotated multi-view video datasets that are expensive to collect and label. The authors propose Panacea, a latent-diffusion video generator conditioned on BEV layout sequences and text prompts, using a decomposed 4D attention (intra-view, cross-view, cross-frame) and a two-stage image-then-video pipeline. On nuScenes the generated samples reach FVD 139 / FID 16.96 and, when used as augmentation, raise StreamPETR's NDS from 46.9 to 49.2 (+2.3).

## Problem & Motivation
Cutting-edge BEV perception methods such as StreamPETR are trained on multi-view video logs, but assembling diverse, well-annotated driving video at scale is costly and risky. Prior synthetic-data work (BEVGen, BEVControl) generates only single-frame multi-view street images; the Video Latent Diffusion Model (VLDM) handles temporal video but is single-view. No prior method jointly delivers (1) panoramic multi-view coverage, (2) temporal coherence, and (3) precise BEV-layout controllability — the three properties needed to bolster video-based BEV perception with synthetic data.

## Innovation Points
- **Decomposed 4D attention** — replaces intractable HWVT (height-width-view-time) attention with three lighter modules: intra-view spatial attention, cross-view attention restricted to adjacent views, and cross-frame attention on spatially aligned patches; achieves multi-view + temporal consistency at feasible memory cost.
- **Two-stage generation pipeline** — first stage trains a multi-view image generator; second stage extends it to video by concatenating a conditioning image (first frame only, zero-padded thereafter) with the diffused input. Decouples spatial and temporal synthesis, sharply boosting fidelity.
- **BEV-layout ControlNet conditioning** — encodes BEV sequences into 19-channel layout images (10 depth + 3 box + 3 road-map + 3 camera-pose channels) and injects them via ControlNet for fine-grained per-frame, per-view layout control.
- **Coarse + fine controllability** — global text prompts (weather, time, scene) via frozen CLIP combined with fine-grained BEV layouts, enabling rare-condition synthesis (rain, snow, sandstorm, night).
- **Gen-nuScenes synthetic dataset** — fully generated multi-view video set planned for release; standalone training on it reaches 77 percent of real-data NDS, and combined with real data improves StreamPETR.

## Model Architecture
- Built on Stable Diffusion 2.1 latent diffusion backbone (spatial layers initialized from pretrained weights).
- Input latent z of shape H x (W x V) x T x C, formed by concatenating V views along the width axis (panoramic layout), with T frames in time.
- UNet uses decomposed 4D attention:
  - Intra-view attention: original SD spatial self-attention (per view, per frame).
  - Cross-view attention: queries from view v attend to keys/values from views v-1, v+1 only.
  - Cross-frame attention (VLDM-style): attention on spatially aligned patches across the T temporal axis.
- Conditioning paths:
  - Text prompt -> frozen CLIP -> cross-attention.
  - BEV sequence -> 19-channel layout images (boxes / depth / road-map / camera-pose) -> ControlNet branch.
  - Image condition (stage 2) -> frozen VAE encoder -> concatenated to diffused latent (only at frame 1; zero-padded for the rest).
- Two-stage training: stage 1 trains multi-view image generation (56k steps); stage 2 trains the temporal extension (40k steps) using ground-truth conditioning frames.
- Inference: 25-step DDIM at 256 x 512 spatial resolution, T = 8 frames, V = 6 surround cameras.

## Benchmark Results
Evaluation dataset: nuScenes (700 train / 150 val / 150 test scenes, 6 cameras, ~360 deg FOV).

**Generation quality on nuScenes val (Tab. 1):**
| Method        | Multi-View | Multi-Frame | FVD down | FID down |
|---------------|------------|-------------|----------|----------|
| BEVGen        | yes        | -           | -        | 25.54    |
| BEVControl    | yes        | -           | -        | 24.85    |
| DriveDreamer  | -          | yes         | 452      | 52.6     |
| **Panacea**   | yes        | yes         | **139**  | **16.96**|

**Controllability via downstream perception (StreamPETR, Tab. 2/3):**
- StreamPETR trained on real nuScenes only: NDS 46.9.
- Trained on Panacea-generated only: NDS 36.1 (relative 72 percent of real, multi-frame; single-frame Panacea S1 reaches NDS 24.7 = 72 percent of the 34.3 image baseline).
- Trained on real + Panacea-generated (Tab. 3): NDS 49.2 (+2.3), mAP 37.1 (+2.6).
- Elevating image-only data to video via Panacea (Tab. 4): NDS 40.1 (+5.8) over the image-only 34.3 baseline; mAP -2.3.
- Across real-data ratios (25/50/75/100 percent) Panacea augmentation consistently improves NDS (Fig. 4).

**Ablations (Tab. 5):**
- Remove cross-view attention: FVD +108 (139 -> 247), FID +5.11; VMS view-consistency drops 0.8 pts.
- Remove cross-frame attention: FVD +75 (139 -> 214); temporal consistency lost.
- Remove two-stage pipeline (single-stage video training): FVD +166 (139 -> 305), FID +19.65 — the largest single quality lever.

## Limitations & Open Questions
- Evaluated only on nuScenes; generalization to other geographies/sensor rigs (Waymo, Argoverse) not shown.
- Generated-only training still trails real-only by ~10 NDS points; pure-synthetic training is not yet competitive.
- Augmenting an image-only set with Panacea-elevated video improves NDS but reduces mAP by 2.3, attributed by the authors to a domain gap between generated training data and real validation data.
- Resolution capped at 256 x 512 with only T = 8 frames; longer-horizon, higher-resolution video generation and inference cost are not reported.
- Closed-loop driving simulation use cases are mentioned as future work but not demonstrated.
