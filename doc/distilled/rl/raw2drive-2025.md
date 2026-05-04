---
paper_id: 2025-raw2drive
title: "Raw2Drive: Reinforcement Learning with Aligned World Models for End-to-End Autonomous Driving (in CARLA v2)"
authors: [Zhenjie Yang, Xiaosong Jia, Qifeng Li, Xue Yang, Maoqing Yao, Junchi Yan]
year: 2025
venue: NeurIPS 2025
arxiv_id: "2505.16394"
url: https://arxiv.org/abs/2505.16394
primary_category: rl
secondary_categories: [world_model, e2e_planning]
keywords: [mbrl, dual-stream-world-model, dreamer-v3, privileged-distillation, guidance-mechanism, carla-leaderboard-2, bench2drive]
one_line_summary: First model-based RL E2E driving system on raw sensor input; dual-stream world model with privileged-to-raw guidance achieves SOTA on CARLA v2 and Bench2Drive.
distilled_at: 2026-05-04
source_pdf: doc/papers/rl/raw2drive-2025.pdf
---

# Raw2Drive: Reinforcement Learning with Aligned World Models for End-to-End Autonomous Driving (in CARLA v2)

## Keywords
- mbrl, dual-stream-world-model, dreamer-v3, privileged-distillation, guidance-mechanism, carla-leaderboard-2, bench2drive

## TL;DR
Imitation learning dominates end-to-end autonomous driving but suffers from causal confusion and distribution shift, while model-free RL fails to converge from raw sensors and existing MBRL works (e.g. Think2Drive) require privileged ground-truth state. Raw2Drive introduces a dual-stream MBRL framework: a privileged world model + planner is trained first on low-dimensional BEV semantic masks, then a raw-sensor world model + policy is trained jointly via a Guidance Mechanism that aligns latent states and reuses the privileged reward/continuation heads. It is the first MBRL E2E method on CARLA Leaderboard 2.0 and reports SOTA among raw-sensor methods on CARLA v2 (DS 4.12 validation, 3.56 devtest) and Bench2Drive (DS 71.36, SR 50.24%, multi-ability mean 53.54%) using only 64 H800 GPU-days.

## Problem & Motivation
- Imitation-learning E2E stacks (UniAD, VAD, DriveTrans) hit fundamental limits: poor generalization to unseen scenes and causal confusion. None achieve satisfying scores on CARLA Leaderboard 2.0 (CARLA v2), which adds 39 real-world corner cases.
- Model-free RL (MaRLn) requires ~50M steps (~57 days) and still trails IL.
- Recent MBRL (Think2Drive) solves CARLA v2 but only with privileged input (ground-truth bounding boxes + HD-map), so it cannot run on raw sensors at inference.
- Training a world model directly on high-dimensional, noisy, redundant multi-view video is empirically unstable; no prior MBRL E2E work has succeeded with raw sensors. Raw2Drive bridges this gap.

## Innovation Points
- **Dual-stream MBRL** — parallel privileged and raw-sensor world models + policies; the structured privileged stream acts as an auxiliary teacher so the raw stream avoids learning a video world model from scratch.
- **Guidance Mechanism** — supervises the raw stream from the trained privileged stream via two parts: (I) Rollout Guidance and (II) Head Guidance.
- **Rollout Guidance** — Spatial-Temporal Alignment Loss on encoder states + Abstract-State Alignment Loss (L2 on deterministic state, KL on stochastic state); single-sample-from-raw trick eliminates cumulative randomness across the two streams during rollout.
- **Head Guidance** — discards the raw stream's reward and continuation heads (scalars fluctuate sharply on near-identical adjacent frames and hurt convergence), and reuses the privileged world model's heads to supervise raw policy training.
- **Decoder-only raw head** — keeps only the BEV-mask decoder on the raw side; ablation shows this beats also training reward/continue heads on raw.
- **Privileged-policy fine-tuning** — initialize raw policy from the privileged actor-critic, then fine-tune within the raw world model rather than zero-shot transfer.

## Model Architecture
- Backbone framework: dual-stream extension of DreamerV3 (Encoder + RSSM + heads, with deterministic h_t and stochastic s_t).
- **Privileged stream**
  - Input o_t: time-sequenced BEV semantic masks (objects, HD-map), as in Roach / Think2Drive.
  - Privileged World Model: Encoder, RSSM, three heads (Decoder, Reward, Continuation).
  - Privileged Policy: actor-critic trained by RL via rollouts inside the privileged world model.
- **Raw sensor stream**
  - Input o_hat_t: multi-view images + IMU.
  - Encoder: BEVFormer producing grid-shaped BEV features (chosen to align with privileged BEV space).
  - Raw World Model: same RSSM topology as privileged WM, but only the Decoder head (predicts BEV semantic masks) is trained; reward and continuation come via Head Guidance from the (frozen) privileged WM.
  - Raw Policy: actor-critic, initialized from the privileged policy and fine-tuned by rollouts in the raw world model.
- **Training pipeline**
  - Phase 1: train privileged WM + policy (supervised + RL in latent rollouts).
  - Phase 2: train raw WM with L_Rollout = β_e Σ MSE(e, ê) + Σ (β_s KL(s, ŝ) + β_h MSE(h, ĥ)); RSSM weights initialized from privileged WM; replay-buffer trajectories partly come from privileged policy and action distributions are distilled.
  - Inference: only the raw stream is used (raw sensors → BEVFormer → RSSM → policy).
- **Compute**: 64 H800 GPU-days end-to-end (40 H800 GPU-days if Think2Drive's privileged stage is reused). UniAD reportedly uses ~30 GPU-days.

## Benchmark Results
**CARLA Town13 Leaderboard 2.0 (Table 3)** — closed loop, raw-image methods only (privileged Think2Drive shown for reference):

| Method (Image, IL unless noted) | DS Val ↑ | DS Devtest ↑ | RC% Val | RC% Devtest | IS Val | IS Devtest |
|---|---|---|---|---|---|---|
| UniAD-Base | 0.15 | 0.00 | 0.51 | 0.07 | 0.23 | 0.04 |
| VAD | 0.17 | 0.00 | 0.49 | 0.06 | 0.31 | 0.04 |
| DriveTrans | 0.85 | 0.68 | 1.42 | 2.13 | 0.33 | 0.35 |
| ThinkTwice* | 0.50 | 0.64 | 1.23 | 1.78 | 0.35 | 0.43 |
| DriveAdapter* | 0.92 | 0.87 | 1.52 | 2.43 | 0.42 | 0.37 |
| **Raw2Drive (RL, raw)** | **4.12** | **3.56** | **9.32** | **6.04** | **0.43** | **0.42** |
| Think2Drive (RL, privileged) | 43.8 | 36.8 | 49.2 | 78.6 | 0.73 | 0.92 |

Authors note that long-route DS in Leaderboard 2.0 is dominated by a cumulative penalty mechanism and does not faithfully reflect driving capability — they prefer Bench2Drive.

**Bench2Drive Multi-Ability (Table 4, % ↑):**

| Method | Merging | Overtaking | Emergency Brake | Give Way | Traffic Sign | Mean |
|---|---|---|---|---|---|---|
| DriveTrans (IL) | 17.57 | 35.00 | 48.36 | 40.00 | 52.10 | 38.60 |
| **Raw2Drive (RL)** | **43.58** | **51.11** | **60.00** | **50.00** | **62.26** | **53.54** |
| Think2Drive (privileged) | 81.27 | 83.92 | 90.24 | 90.00 | 87.67 | 86.26 |

**Bench2Drive Closed-loop (Table 5):**

| Method | DS ↑ | SR% ↑ | Efficiency ↑ | Comfort ↑ |
|---|---|---|---|---|
| DriveTrans (IL) | 63.46 | 35.01 | 100.64 | 20.78 |
| MomAD (IL) | 44.54 | 16.71 | 170.21 | 48.62 |
| **Raw2Drive (RL)** | **71.36** | **50.24** | **214.17** | 22.42 |
| Think2Drive (privileged) | 91.85 | 83.41 | 269.14 | 25.97 |

**Key ablations on Dev10 (Tables 6–11, DS / SR out of 10):**
- Raw WM heads (Table 6): decoder-only 83.5 / 7.5; +reward 46.6 / 3.4; +reward+continue 34.5 / 2.2 → extra heads hurt.
- Abstract-state alignment (Table 7): all three (encoder + deterministic + stochastic) 83.5 / 7.5; encoder-only 36.4 / 2.4; none 0.0 / 0.0.
- Spatial-Temporal Alignment (Table 8): both on 83.5 / 7.5; spatial-only 13.6 / 1.2; temporal-only 9.24 / 0.8; neither 0.0 / 0.0.
- Head Guidance (Table 9): decoder + HG 83.5 / 7.5; full heads + HG 34.5 / 2.2; full heads no HG 26.4 / 1.6.
- Shared parameters (Table 10): full sharing 83.5 / 7.5; w/o shared RSSM 53.2 / 5.4; w/o shared head 65.6 / 6.1.
- Policy fine-tune (Table 11): fine-tuned 83.5 / 7.5; directly use privileged policy 58.4 / 5.6.
- Latency (Appendix G): WM and policy each <2 ms; bottleneck is BEVFormer vision encoder.

## Limitations & Open Questions
- Privileged input is ground-truth bounding boxes + HD-map; transfer to industry depends on having reliable perception/HD-map sources.
- Real-world RL is acknowledged as out of scope; authors gesture toward 3DGS or diffusion-based simulators as future enablers but do not evaluate.
- Absolute scores on CARLA Leaderboard 2.0 long routes remain low (DS 4.12 / 3.56) — even the SOTA gap to privileged Think2Drive is large; authors argue the long-route metric is unfair, but no alternative quantitative analysis is given on those routes.
- Big remaining gap to the privileged upper bound on Bench2Drive (DS 71.36 vs 91.85; SR 50.24 vs 83.41) suggests substantial information loss in the raw stream that guidance does not fully recover.
- Method depends on CARLA being the only viable closed-loop simulator; portability of the dual-stream design to other simulators or sensor stacks is not demonstrated.
