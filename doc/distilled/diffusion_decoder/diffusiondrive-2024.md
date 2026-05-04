---
paper_id: 2024-diffusiondrive
title: "DiffusionDrive: Truncated Diffusion Model for End-to-End Autonomous Driving"
authors: [Bencheng Liao, Shaoyu Chen, Haoran Yin, Bo Jiang, Cheng Wang, Sixu Yan, Xinbang Zhang, Xiangyu Li, Ying Zhang, Qian Zhang, Xinggang Wang]
year: 2024
venue: CVPR 2025 (Highlight)
arxiv_id: "2411.15139"
url: https://arxiv.org/abs/2411.15139
primary_category: diffusion_decoder
secondary_categories: [e2e_planning]
keywords: [diffusion-policy, truncated-diffusion, anchored-gaussian, cascade-decoder, navsim, multi-mode-trajectory, real-time]
one_line_summary: "Truncated diffusion policy that denoises from K-Means trajectory anchors in 2 steps via a cascade transformer decoder; 88.1 PDMS at 45 FPS on NAVSIM with ResNet-34."
distilled_at: 2026-05-02
source_pdf: doc/papers/diffusion_decoder/diffusiondrive-2024.pdf
---

# DiffusionDrive: Truncated Diffusion Model for End-to-End Autonomous Driving

## Keywords
- diffusion-policy, truncated-diffusion, anchored-gaussian, cascade-decoder, navsim, multi-mode-trajectory, real-time

## TL;DR
Vanilla diffusion policies adapted from robotics to end-to-end driving suffer from mode collapse (Gaussian-noise samples converge to one trajectory) and heavy compute (~20 denoising steps). The authors replace the standard Gaussian prior with an *anchored Gaussian* — small noise added around K-Means-clustered trajectory anchors — and truncate the diffusion schedule so denoising takes only 2 steps. Combined with a transformer cascade decoder that interacts with BEV and agent/map context, DiffusionDrive reaches 88.1 PDMS on NAVSIM `navtest` with a ResNet-34 backbone at 45 FPS on an NVIDIA 4090, beating Hydra-MDP-V8192-W-EP (86.5) without post-processing.

## Problem & Motivation
Single-mode regression planners (Transfuser, UniAD, VAD) ignore the multi-modal nature of driving decisions and fail in ambiguous scenes. Fixed-vocabulary multi-mode methods (VADv2, Hydra-MDP) need very large anchor sets (4096–8192) and still cannot escape their discrete vocabulary, while incurring high scoring cost. Naively porting robotic diffusion policy (Diffusion Policy / DDIM) to driving — i.e., turning Transfuser's MLP head into a UNet conditional diffusion head ("TransfuserDP") — produces two new failures: (1) **mode collapse** — 20 random Gaussian noises denoise to nearly identical trajectories (mode-diversity score D = 11%); (2) **heavy denoising overhead** — 20 DDIM steps drop FPS from 60 to 7, infeasible for real-time driving. DiffusionDrive targets both issues with a driving-specific prior and a faster schedule.

## Innovation Points
- **Truncated diffusion policy** — denoises from an anchored Gaussian distribution centered on K=20 K-Means trajectory anchors instead of pure Gaussian noise, and truncates the diffusion schedule (50/1000 of standard); only 2 denoising steps are needed at inference (vs. 20 for vanilla), a 10× reduction.
- **Anchored Gaussian distribution** — partitions the prior into multiple sub-Gaussians around prior anchors to inject driving-pattern priors; avoids mode collapse without needing a 4096–8192-entry vocabulary as in VADv2/Hydra-MDP.
- **Cascade diffusion decoder** — transformer decoder with deformable spatial cross-attention (BEV/PV), agent/map cross-attention, FFN, timestep modulation, and an MLP head emitting both classification score and trajectory offset; the same decoder block is reused (weight-shared) across the 2 denoising steps in a cascaded manner.
- **Flexible inference** — can sample any N_infer ≤ N_anchor trajectories at run time, trading quality for compute without retraining (10/20/40 sampled noises ablated).
- **No post-processing** — beats Hydra-MDP variants that rely on rule-based-evaluator supervision and weighted-confidence post-processing, by directly learning from human demonstrations.

## Model Architecture
- **Inputs:** 3 forward-facing cameras concatenated to a 1024×256 image + rasterized BEV LiDAR (matches Transfuser's recipe).
- **Perception backbone:** ResNet-34 (NAVSIM) or ResNet-50 (nuScenes) image encoder + Transfuser-style fusion → BEV features and agent/map queries.
- **Diffusion decoder (cascaded, 2 layers):** for each noisy trajectory τᵢ, per layer:
  1. Deformable spatial cross-attention to BEV (and PV) features sampled at trajectory waypoint coordinates;
  2. Cross-attention to agent/map queries;
  3. FFN;
  4. Timestep modulation (sinusoidal + MLP);
  5. MLP heads → classification score ŝₖ + offset relative to current noisy waypoints.
- **Anchors:** N_anchor = 20 trajectories obtained by K-Means on the training set; positive sample = anchor closest to GT trajectory (yₖ=1), others negative.
- **Truncated diffusion schedule:** anchors are diffused only up to T_trunc ≪ T (50/1000) during training; inference also runs only 2 DDIM steps starting from the anchored Gaussian.
- **Loss:** Σₖ [ yₖ · L1(τ̂ₖ, τ_gt) + λ · BCE(ŝₖ, yₖ) ].
- **Output:** NAVSIM — 8-waypoint trajectory over 4 s (top-scored among N_infer); nuScenes — 3 s open-loop trajectory.
- **Scale:** 60M params; trained on NAVSIM `navtrain` for 100 epochs, AdamW, batch 512, lr 6e-4 on 8× NVIDIA 4090.

## Benchmark Results

**Closed-loop NAVSIM `navtest` (ResNet-34, C&L input):**
| Method | Anchors | NC↑ | DAC↑ | TTC↑ | Comf.↑ | EP↑ | PDMS↑ | FPS↑ |
|---|---|---|---|---|---|---|---|---|
| UniAD | 0 | 97.8 | 91.9 | 92.9 | 100 | 78.8 | 83.4 | — |
| Transfuser | 0 | 97.7 | 92.8 | 92.8 | 100 | 79.2 | 84.0 | 60 |
| VADv2-V8192 | 8192 | 97.2 | 89.1 | 91.6 | 100 | 76.0 | 80.9 | — |
| Hydra-MDP-V8192-W-EP | 8192 | 98.3 | 96.0 | 94.6 | 100 | 78.7 | 86.5 | — |
| **DiffusionDrive** | **20** | 98.2 | 96.2 | 94.7 | 100 | 82.2 | **88.1** | **45** |

**Open-loop nuScenes (ResNet-50, camera only):**
| Method | L2 avg (m) ↓ | Collision avg (%) ↓ | FPS↑ |
|---|---|---|---|
| VAD | 0.72 | 0.22 | 4.5 |
| SparseDrive | 0.61 | 0.08 | 9.0 |
| **DiffusionDrive** | **0.57** | **0.08** | **8.2** |
20.8% lower L2 and 63.6% lower collision than VAD; 1.8× faster.

**Roadmap ablation (Tab. 2) — Transfuser → DiffusionDrive:**
- Transfuser (MLP, 1 step, 0.2 ms): 84.0 PDMS, mode-diversity D = 0%, 60 FPS.
- TransfuserDP (UNet, 20 steps, 130 ms): +0.6 PDMS, D = 11%, 7 FPS.
- TransfuserTD (UNet, 2 steps, 13.8 ms): +1.7 PDMS, D = 70%, 27 FPS — confirms truncated schedule alone keeps quality and adds diversity.
- **DiffusionDrive** (cascade decoder, 2 steps, 7.6 ms): +4.1 PDMS over Transfuser, D = 74%, 45 FPS.

**Other ablations:**
- Removing spatial cross-attention drops PDMS from 87.1 → 55.1; ego/agent/map interactions all needed (Tab. 3).
- 1 → 2 → 3 denoising steps: 87.9 → 88.1 → 88.1 (Tab. 4); 1 step already strong.
- Cascade stages 1 → 2 → 4: 87.4 → 88.1 → 88.2 (Tab. 5); 2 stages chosen.
- N_infer = 10/20/40: 84.9 / 88.1 / 88.2 PDMS (Tab. 6) — diminishing returns past 20.

## Limitations & Open Questions
- Anchor set K = 20 is fixed (K-Means on `navtrain`); doesn't adapt to scene context, so out-of-distribution intents not in the K-Means clusters may be inaccessible.
- Closed-loop evaluation limited to NAVSIM non-reactive simulation; no on-vehicle or reactive closed-loop deployment is reported. Inference cost is benchmarked on a desktop NVIDIA 4090, not automotive hardware.
- Top-1 selection by predicted confidence may discard a safer lower-scored mode — paper shows examples where top-10 are needed for plausible lane-change behavior, but selection criterion is not learned end-to-end with safety.
- Only DDIM sampler explored; flow-matching / consistency models not compared, though they could further reduce step count.
- The two failure modes of vanilla diffusion (mode collapse, overhead) are diagnosed empirically on NAVSIM; theoretical guarantees about coverage of the anchored Gaussian are not provided.
