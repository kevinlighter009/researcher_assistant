---
paper_id: 2024-genad-opendv
title: "Generalized Predictive Model for Autonomous Driving"
authors: [Jiazhi Yang, Shenyuan Gao, Yihang Qiu, Li Chen, Tianyu Li, Bo Dai, Kashyap Chitta, Penghao Wu, Jia Zeng, Ping Luo, Jun Zhang, Andreas Geiger, Yu Qiao, Hongyang Li]
year: 2024
venue: CVPR 2024 Highlight
arxiv_id: "2403.09630"
url: https://arxiv.org/abs/2403.09630
primary_category: world_model
secondary_categories: [datasets]
keywords: [video-prediction, latent-diffusion, opendv-2k, youtube-driving, causal-temporal-attention, action-conditioned, zero-shot]
one_line_summary: Two-stage latent-diffusion video predictor (GenAD) trained on 2059-hr OpenDV-2K YouTube+public driving corpus; cuts FVD on nuScenes 44.5% vs DrivingDiffusion and supports action/text conditioning and planning.
distilled_at: 2026-05-02
source_pdf: doc/papers/world_model/genad-opendv-2024.pdf
---

# Generalized Predictive Model for Autonomous Driving

## Keywords
- video-prediction, latent-diffusion, opendv-2k, youtube-driving, causal-temporal-attention, action-conditioned, zero-shot

## TL;DR
Public driving datasets are too small and too narrow to train a generalized driving video predictor. The authors curate OpenDV-2K (2059 hours, 60M+ front-view frames from YouTube + 7 public datasets, paired with VLM/LLM-generated captions) and train GenAD, a two-stage latent diffusion model with causal temporal attention and decoupled spatial attention. GenAD reaches FID 15.4 / FVD 184 on nuScenes (44.5% FVD reduction vs DrivingDiffusion without 3D layouts), generalizes zero-shot to Waymo/KITTI/Cityscapes, and adapts to action-conditioned simulation and open-loop planning with a frozen-encoder MLP head.

## Problem & Motivation
Existing driving video predictors (DriveGAN, DriveDreamer, DrivingDiffusion, DMVFN, etc.) are trained on small, restricted datasets (nuScenes 5.5h, KITTI 1.4h, Cityscapes 0.5h) collected in a few cities with fixed sensor rigs. They overfit to one visual pattern and fail to transfer zero-shot. Generic Internet video models (I2VGen-XL, VideoCrafter1) ignore the past-frame conditioning and produce inconsistent futures. Standard bidirectional temporal attention also leaks future information, blocking causal reasoning needed for driving. The paper asks: (1) where to get scalable diverse data, (2) how to formulate a predictor that handles drastic view shift and causal dynamics, (3) how to reuse it for downstream simulation/planning.

## Innovation Points
- **OpenDV-2K dataset** — 2059 hours (1747h YouTube from 43 curated YouTubers + 312h merged public datasets), 65.1M front-view frames spanning 40+ countries and 244+ cities; 374x larger than nuScenes; paired with BLIP-2 frame contexts and a Honda-HDD-Action-trained classifier producing 14-class command labels.
- **Two-stage learning** — Stage 1 fine-tunes SDXL text-to-image on OpenDV-2K still frames to transfer the image domain to driving; Stage 2 inserts and trains only Temporal Reasoning Blocks while keeping the image UNet frozen, separating photorealism from temporal modeling.
- **Causal Temporal Attention (TA)** — masked attention along the time axis so future frames cannot attend forward, regularizing predictions to be coherent with past observations.
- **Decoupled Spatial Attention (SA)** — two linear-complexity self-attentions along the horizontal and vertical axes that propagate features for the temporal layer to consume, addressing drastic per-pixel motion in driving views.
- **Zero-init interleaving** — Temporal Reasoning Blocks are interleaved between SDXL spatial / cross-attention / FFN blocks with zero-initialized output layers to preserve the pre-trained image prior at start of stage 2.
- **Plug-in extensions** — (a) action-conditioning via Fourier-embedded waypoints injected through the conditional cross-attention; (b) planning by freezing the GenAD UNet encoder and training only an MLP waypoint head on nuScenes, 3400x faster training than UniAD.

## Model Architecture
- Inputs: T consecutive frames at 2 Hz, resized to 256x448; m=past clean latents + n=future noisy latents; text condition c = concat(context caption, command).
- Latent space: SDXL VAE encoder (frozen).
- UNet: SDXL UNet, fine-tuned in stage 1 (per-image denoising), then frozen in stage 2.
- Temporal Reasoning Block (inserted before each frozen SDXL transformer block in stage 2):
  - Causal Temporal Attention (with relative position bias on time axis, causal mask).
  - Two Decoupled Spatial Attentions (along x and y axes, linear complexity).
  - Each block ends with a zero-initialized layer.
- Conditioning: CLIP text encoder (frozen), classifier-free guidance with p=0.1 text-drop.
- Outputs: 4-second video clips at 2 Hz (model trained on 4s clips); supports interpolation by switching condition-frame indices.
- Extensions:
  - GenAD-act: 6 future waypoints encoded via Fourier features + linear projection, added to the conditioning stream; predicts 6 future frames.
  - Planner: frozen GenAD UNet encoder features of 2 history frames -> MLP -> future ego waypoints.
- Training scale: stage 1, 300K iters on 32x A100 (batch 256); stage 2, 112.5K iters on 64 GPUs (batch 64).

## Benchmark Results

**nuScenes video generation (Table 2):**
| Method                                | Train data  | Pred. | FID (down) | FVD (down) |
|---------------------------------------|-------------|-------|------------|------------|
| DriveGAN                              | nuScenes    | yes   | 73.4       | 502        |
| DriveDreamer (3D layout in)           | nuScenes    | yes   | 52.6       | 452        |
| DrivingDiffusion (3D layout in)       | nuScenes    | no    | 15.8       | 332        |
| GenAD-nus (ours, no 3D layout)        | nuScenes    | yes   | 15.4       | 244        |
| GenAD (ours)                          | OpenDV-2K   | yes   | 15.4       | 184        |

GenAD reduces FVD by 44.5% vs DrivingDiffusion without using 3D layout inputs.

**Ablation on YouTube subset (Table 3):**
| Variant                       | FID (down) | FVD (down) | CLIPSIM (up) |
|-------------------------------|------------|------------|--------------|
| Baseline (plain temporal attn)| 18.32      | 244.44     | 0.8405       |
| + Deep Interaction            | 17.96      | 201.69     | 0.8409       |
| + Temporal Causality          | 16.54      | 207.45     | 0.8550       |
| + Decoupled Spatial Attn      | 17.67      | 189.54     | 0.8652       |

Interleaving temporal with spatial blocks alone cuts FVD by 17%; causality + decoupled SA push CLIPSIM from 0.8405 to 0.8652.

**Action-conditioned prediction (Table 4, nuScenes):**
| Method      | Condition    | Action Prediction Error (down) |
|-------------|--------------|--------------------------------|
| Ground truth| -            | 0.90                           |
| GenAD       | text         | 2.54                           |
| GenAD-act   | text + traj  | 2.02                           |

GenAD-act reduces action prediction error by 20.4% over text-only conditioning.

**Open-loop planning on nuScenes (Table 5):**
| Method        | Trainable params | ADE (down) | FDE (down) |
|---------------|------------------|------------|------------|
| ST-P3* (multi-view) | 10.9M       | 2.65       | 3.73       |
| UniAD* (multi-view) | 58.8M       | 1.03       | 1.65       |
| GenAD (front-view)  | 0.8M        | 1.23       | 2.31       |

GenAD's frozen-encoder + MLP planner uses 73x fewer trainable parameters than UniAD with single-view input, and adaptation training takes 10 minutes on one V100 (3400x faster than UniAD).

## Limitations & Open Questions
- Authors note increased model capacity hurts training efficiency and real-time deployment; inference latency and memory not reported.
- Front-view-only; surround / multi-camera generalization not evaluated.
- Output horizon is short (4s at 2 Hz, 8 frames); long-horizon coherence not characterized.
- OpenDV-2K poses are unavailable for the YouTube portion; planning eval is restricted to nuScenes where ego poses exist.
- Action-conditioning is fine-tuned on nuScenes only; cross-dataset action transfer not shown.
- GenAD is open-loop; no closed-loop driving simulator integration is reported.
