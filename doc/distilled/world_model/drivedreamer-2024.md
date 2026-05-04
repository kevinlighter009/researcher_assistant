---
paper_id: 2024-drivedreamer
title: "DriveDreamer: Towards Real-world-driven World Models for Autonomous Driving"
authors: [Xiaofeng Wang, Zheng Zhu, Guan Huang, Xinze Chen, Jiagang Zhu, Jiwen Lu]
year: 2024
venue: ECCV 2024
arxiv_id: "2309.09777"
url: https://arxiv.org/abs/2309.09777
primary_category: world_model
secondary_categories: [diffusion_decoder, e2e_planning]
keywords: [world-model, video-diffusion, auto-dm, actionformer, hdmap-conditioning, nuscenes]
one_line_summary: First diffusion-based world model trained on real driving data; jointly generates future multi-view videos and ego actions, conditioned on HDMap, 3D boxes, text, and past actions.
distilled_at: 2026-05-02
source_pdf: doc/papers/world_model/drivedreamer-2024.pdf
---

# DriveDreamer: Towards Real-world-driven World Models for Autonomous Driving

## Keywords
- world-model, video-diffusion, auto-dm, actionformer, hdmap-conditioning, nuscenes

## TL;DR
Prior driving world models were largely confined to simulators or BEV-segmentation latents, limiting realism. The authors propose DriveDreamer, a diffusion-based world model trained directly on real-world nuScenes videos that consumes HDMap, 3D-box, text, and action conditions to generate future driving videos and future driving actions via a two-stage pipeline (Auto-DM + ActionFormer). On nuScenes, DriveDreamer attains FID 14.9 / FVD 340.8 for video generation and a 0.29 m L2 trajectory error for open-loop planning, matching the multimodal VAD baseline.

## Problem & Motivation
Existing world models for driving (e.g., GameGAN, MILE, SEM2, ISO-Dream) are trained mostly in gaming or simulated environments, or operate in compressed BEV-segmentation latents — they do not capture the visual richness and structural constraints of real driving scenes. Pure pixel-space video prediction in driving is hard because the search space is enormous and structural cues (lane geometry, vehicle layout) are easily violated. The authors argue that a real-world driving world model must (a) be conditioned on structured traffic priors (HDMaps, 3D boxes), (b) controllable by text and ego actions, and (c) jointly predict future videos and future ego actions for downstream planning.

## Innovation Points
- **First real-world driving world model** — DriveDreamer is trained end-to-end on nuScenes (not simulator data) and produces high-fidelity multi-view driving videos consistent with real traffic constraints.
- **Auto-DM (Autonomous-driving Diffusion Model)** — a Stable-Diffusion-v1.4-based video diffusion network that ingests spatially-aligned HDMap conditions plus 3D-box position embeddings via gated self-attention, with text via cross-attention and temporal-attention layers for frame coherence.
- **Two-stage training pipeline** — Stage 1 trains Auto-DM on single-frame structured conditions (image supervision) so the model first masters traffic-structure constraints; Stage 2 adds temporal layers and trains video + action prediction jointly, accelerating convergence.
- **ActionFormer** — a recurrent latent-space module (self-attention + cross-attention + GRU) that, given an initial HDMap/3D-box and a sequence of driving actions, autoregressively predicts future structured traffic conditions in latent space, sidestepping pixel-level noise.
- **Joint future-video + future-action generation** — an action decoder consumes pooled multi-scale Auto-DM UNet features plus historical action embeddings to predict future ego actions, enabling open-loop planning from the same world model.
- **Controllable scenario style** — text prompts ("Sunny", "Rainy", "Night") modulate the generated videos via CLIP cross-attention while preserving structural constraints.

## Model Architecture
- Inputs: reference frame I0 (single image), HDMap H0 (3-channel: lane boundary, lane divider, pedestrian crossing, projected to image plane), 3D boxes B0 (8-corner projections + CLIP-encoded category labels), past driving actions A_{0:N-1} (yaw + velocity), and a text prompt.
- Auto-DM (video diffusion):
  - Backbone: Stable Diffusion v1.4 UNet (frozen original weights; trainable gated-self-attention, temporal-attention, cross-attention).
  - Spatially aligned HDMap conditions are encoded by conv layers and concatenated with the noisy latent Z_t.
  - 3D-box position embeddings H^p = MLP([CLIP(category), Fourier(box)]) are fused with visual tokens via gated self-attention.
  - Text → CLIP → cross-attention modulates style.
  - Temporal-attention layers operate after reshaping N×C×H×W → C×N×H×W to enforce inter-frame coherence; same architecture extends to multi-view via additional view-wise attention (supplement).
- ActionFormer (latent-space rollout):
  - Encodes initial H0, B0 into 1D latent; combines with action features via cross-attention; latent state s_t ~ N(μ, σ) parameterized by MLPs over cross-attended features; GRU iteratively updates hidden state h_{t+1} = GRU(h_t, s_t); decoded latents become future structured conditions fed back into Auto-DM.
- Action decoder: pools multi-scale Auto-DM UNet features + historical actions through MLPs to emit future driving actions A_{N:N+M}.
- Outputs: future driving videos {I_t}_{t=1..T} and future driving actions {A_t}_{t=N..T+N}.
- Training: Step 1 — 40 epochs, batch 16, single-frame conditions, no temporal attention (image supervision only). Step 2 — 10 epochs, batch 1, video length 32 at 448×256 spatial resolution, predicts 16 frames given 16 history frames; AdamW, LR 5e-5, A800 GPUs.
- Data: nuScenes (700 train / 150 val scenes; ~20 s clips, 6 surround cameras at 12 Hz, ~1M frames). 3D-box annotations supplemented from BEVerse (12 Hz) since nuScenes ships 2 Hz boxes.

## Benchmark Results

**Video generation quality on nuScenes validation (FID/FVD):**
| Method                                   | FID ↓ | FVD ↓ |
|------------------------------------------|-------|--------|
| DriveGAN                                 | 27.8  | 390.8  |
| DriveDreamer (no stage-1 training)       | 15.9  | 363.3  |
| DriveDreamer (stage-1 only)              | 15.3  | 349.6  |
| **DriveDreamer (stage-1 + stage-2 + ActionFormer)** | **14.9** | **340.8** |

**Synthetic-data augmentation for 3D detection on nuScenes:**
| Detector  | Resolution  | Data            | mAP ↑ | NDS ↑ |
|-----------|-------------|-----------------|-------|-------|
| FCOS3D    | 1600×900    | w/o synthetic   | 30.2  | 38.1  |
| FCOS3D    | 1600×900    | + 4K synthetic  | 30.9 (+0.7) | 38.3 (+0.2) |
| BEVFusion | 704×256     | w/o synthetic   | 32.8  | 37.6  |
| BEVFusion | 704×256     | + 4K synthetic  | 35.8 (+3.0) | 39.5 (+1.9) |

**Open-loop planning on nuScenes validation (ST-P3 protocol):**
| Method      | Visual | Action | L2 Avg. (m) ↓ | Col. Avg. (%) ↓ |
|-------------|:------:|:------:|---------------|------------------|
| ST-P3       | yes    |        | 2.11          | 0.71             |
| UniAD       | yes    |        | 1.65          | 0.31             |
| AD-MLP      |        | yes    | **0.29**      | 0.19             |
| VAD         | yes    | yes    | 0.37          | **0.14**         |
| DriveDreamer| yes    | yes    | **0.29**      | 0.15             |

Ablations: removing stage-1 training raises FID 14.9 → 15.9 and FVD 340.8 → 363.3, confirming the value of structure-first pretraining. Without ActionFormer (zero-padded future conditions) FID/FVD also degrade (15.3 / 349.6), showing iterative latent-space condition rollout helps over naive concatenation. DriveDreamer reduces collision rate by 21% relative to AD-MLP (paper-reported figure).

## Limitations & Open Questions
- All evaluation is on nuScenes only; no closed-loop driving test, no transfer to other datasets (Waymo, Argoverse, internal large-scale logs).
- Generation runs at modest spatial resolution (448×256) with short horizons (16 future frames at 12 Hz ≈ 1.3 s); long-horizon temporal consistency and high-resolution multi-view generation are not benchmarked head-to-head.
- Inference cost / FPS not reported; deployability of the full Auto-DM + ActionFormer + action decoder stack on a vehicle is unclear.
- Structured conditions depend on accurate HDMap and 3D-box annotations (12 Hz boxes had to be supplemented from BEVerse); robustness when these conditions are noisy or partially missing is not studied.
- Open-loop L2 / collision metrics on nuScenes are known to be weakly correlated with real driving performance — the planning result, while competitive, does not establish closed-loop safety gains.
