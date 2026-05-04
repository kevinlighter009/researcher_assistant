---
paper_id: 2024-driveworld
title: "DriveWorld: 4D Pre-trained Scene Understanding via World Models for Autonomous Driving"
authors: [Chen Min, et al.]
year: 2024
venue: CVPR 2024
arxiv_id: "2405.04390"
url: https://arxiv.org/abs/2405.04390
primary_category: world_model
secondary_categories: [perception, e2e_planning]
keywords: [world-model, 4d-pretraining, bev, memory-state-space-model, 3d-occupancy, task-prompt, nuscenes, openscene]
one_line_summary: World-model-based 4D pre-training that predicts future 3D occupancy from multi-camera video, using a Memory State-Space Model with separate dynamic/static branches and task-conditioned prompts.
distilled_at: 2026-05-02
source_pdf: doc/papers/world_model/driveworld-2024.pdf
---

# DriveWorld: 4D Pre-trained Scene Understanding via World Models for Autonomous Driving

## Keywords
- world-model, 4d-pretraining, bev, memory-state-space-model, 3d-occupancy, task-prompt, nuscenes, openscene

## TL;DR
Existing vision-centric pre-training for autonomous driving relies on 2D or 3D pre-text tasks and ignores the temporal (4D) nature of driving scenes. DriveWorld pre-trains a multi-camera encoder by having a world model predict current and future 3D occupancy and ego-actions, using a Memory State-Space Model that splits temporal-aware dynamics (Dynamic Memory Bank) from spatial-aware statics (Static Scene Propagation), plus a Task Prompt that conditions features per downstream task. After fine-tuning on nuScenes, the same backbone improves 3D detection (+7.5% mAP), tracking AMOTA, online mapping, motion forecasting, occupancy, and planning (-0.34 m avg L2) over UniAD.

## Problem & Motivation
Vision-centric autonomous driving requires 4D scene understanding for perception, prediction and planning, but the dominant pre-training recipes only cover part of it: ImageNet-style 2D pre-text tasks (DD3D, depth) ignore 3D structure, and 3D-reconstruction pre-training (OccNet, UniScene, UniPAD) ignores temporal dynamics. None of these prior schemes jointly model both aleatoric uncertainty from the stochastic future and epistemic uncertainty from partial observability. The authors argue this 4D gap should be closed with a world-model pre-text task that predicts future 3D occupancy and actions from multi-camera video.

## Innovation Points
- **First world-model-based 4D pre-training for vision-centric AD** — pre-trains a BEV encoder by having a generative world model reconstruct current and future 3D occupancy and actions from multi-camera videos.
- **Memory State-Space Model (MSSM)** — probabilistic latent dynamics built on a Recurrent State-Space Model that explicitly factorises information into temporal-aware and spatial-aware streams.
- **Dynamic Memory Bank (DMB)** — propagates motion-aware latent dynamics with Motion-aware Layer Normalization (MLN) that injects per-object velocity/relative-time affine modulation, addressing aleatoric uncertainty about future states.
- **Static Scene Propagation (SSP)** — passes BEV features of a randomly chosen frame straight to the decoder as a spatial-aware static latent, addressing epistemic uncertainty by retaining global scene context.
- **Task Prompt** — text prompts encoded by BERT/CLIP and broadcast via AdaptiveInstanceNorm to decouple task-aware features (current scene for detection vs. future states for forecasting), avoiding negative transfer.
- **4D pre-training objective** — KL between posterior and prior latent distributions plus CE on past+future occupancy and L1 on past+future actions over T observed and L predicted steps.

## Model Architecture
- Inputs: T = 4 surround-view multi-camera frames (nuScenes, 6 cameras) plus expert actions a_{1:T}; LiDAR-derived 3D occupancy y_{1:T} as supervision; future horizon L = 4.
- Image encoder: ResNet101-DCN backbone shared with BEVFormer/UniAD, with 2D-to-3D view transform (Transformer/LSS-style) producing BEV feature b_t.
- BEV features b_t are flattened to a 1D vector x_t in R^{512}.
- MSSM latent dynamics: posterior state s_t ~ N(mu_phi, sigma_phi) from (h_t, a_{t-1}, x_t); prior state from (h_t, hat-a_{t-1}); deterministic history h_{t+1} = f_theta(tilde h_t, tilde s_t). MLN modulates s_t with affine vectors derived from object velocity v and relative time delta-t.
- Dynamic Memory Bank stores h_{1:t}; refined history tilde h_t obtained via cross-attention with the bank.
- Static Scene Propagation: pick random frame o', encode its BEV features b' to a static latent hat b = z_theta(b'), combined channel-wise with s_t.
- Decoders: 3D occupancy decoder y_hat_t = l_theta(m_theta(tilde h_t, s_t), hat b); action decoder pi_theta predicts velocity and steering for both observed and future steps.
- Task Prompt: text prompt p_text → text encoder g_phi → AdaIN/CNN expand to BEV size, fused into spatio-temporal features per task head.
- Voxel grid for occupancy: 16 x 200 x 200; pre-training 24 epochs, lr 2e-4, on 8 NVIDIA A100 GPUs.
- Pre-training datasets: nuScenes train set and OpenScene 3D occupancy dataset; fine-tuning on nuScenes downstream tasks via UniAD/BEVFormer heads.

## Benchmark Results
**3D object detection on nuScenes (Tab. 3):**
| Pre-training | mAP up | NDS up |
|---|---|---|
| BEVFormer + 2D ImageNet | 0.377 | 0.477 |
| + OccNet | 0.436 | 0.532 |
| + UniScene | 0.438 | 0.534 |
| + BEVDistill | 0.439 | 0.536 |
| + DriveWorld (nuScenes pre-train) | 0.442 (+2.1%) | 0.536 (+5.9%) |
| + DriveWorld (OpenScene pre-train) | **0.452 (+7.5%)** | **0.545 (+6.8%)** |

**Planning on nuScenes (Tab. 8, avg over 1/2/3 s):**
| Method | L2 (m) avg down | Col. Rate (%) avg down |
|---|---|---|
| ST-P3 | 2.11 | 0.71 |
| BEVGPT | 1.22 | not reported |
| UniAD | 1.03 | 0.31 |
| + OccNet | 1.02 | 0.31 |
| + UniScene | 1.05 | 0.28 |
| + BEVDistill | 0.99 | 0.29 |
| + DriveWorld (nuScenes) | 0.92 (-0.11) | 0.26 (-0.05) |
| + DriveWorld (OpenScene) | **0.69 (-0.34)** | **0.19 (-0.12)** |

Other downstream gains over UniAD (with OpenScene pre-training): tracking AMOTA 0.359 -> 0.412 (+5.3%), online mapping mIoU on Crossing 13.8 -> 17.2 (+3.4%), motion forecasting minADE 0.71 -> 0.61 m (-0.10), occupancy IoU-near 63.4 -> 66.2 (+2.8%).

Ablations (Tab. 1, on UniAD detection/tracking/mapping):
- Plain RSSM alone hurts detection (mAP 0.381 vs. 0.416 baseline) due to 1D latent losing context.
- Adding Static Scene Propagation recovers and gains ~1% over baseline.
- Adding Dynamic Memory Bank trades small detection drop for tracking gains; MLN lifts all perception tasks.
- Adding Task Prompt yields the best row across detection (mAP 0.436, NDS 0.534), tracking (AMOTA 0.379) and mapping (IoU-lane 0.329).
- Data scale (Tab. 2): fine-tuning on only 75% of nuScenes after 4D pre-training matches full-data baseline, suggesting ~25% annotation savings.

## Limitations & Open Questions
- 3D occupancy supervision is still LiDAR-derived; the authors flag self-supervised occupancy targets as future work for purely vision-centric pre-training.
- Validated only with the lightweight ResNet101 backbone; scaling to larger backbones and larger pre-training corpora is acknowledged as untested.
- Pre-training scope is nuScenes + OpenScene only; cross-domain / cross-sensor transfer (other cities, sensor rigs, weather) is not evaluated.
- Inference cost and latency of the MSSM + Task Prompt stack on top of UniAD-style heads are not reported.
