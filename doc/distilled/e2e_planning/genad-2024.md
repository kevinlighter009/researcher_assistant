---
paper_id: 2024-genad-e2e
title: "GenAD: Generative End-to-End Autonomous Driving"
authors: [Wenzhao Zheng, Ruiqi Song, Xianda Guo, Chenming Zhang, Long Chen]
year: 2024
venue: ECCV 2024
arxiv_id: "2402.11502"
url: https://arxiv.org/abs/2402.11502
primary_category: e2e_planning
secondary_categories: [perception]
keywords: [generative-planning, instance-centric, vae-trajectory-prior, gru-rollout, bev, nuscenes]
one_line_summary: Recasts end-to-end driving as generative trajectory rollout in a VAE-learned latent space over instance-centric BEV scene tokens, with joint motion+ego prediction.
distilled_at: 2026-05-02
source_pdf: doc/papers/e2e_planning/genad-2024.pdf
---

# GenAD: Generative End-to-End Autonomous Driving

## Keywords
- generative-planning, instance-centric, vae-trajectory-prior, gru-rollout, bev, nuscenes

## TL;DR
Conventional end-to-end driving stacks (UniAD, VAD) chain perception → prediction → planning serially, ignoring the future ego–agent interaction loop and the structural prior of realistic trajectories. GenAD recasts driving as a generative problem: an instance-centric scene representation feeds a VAE that learns a latent trajectory prior, and a GRU autoregressively rolls out joint futures for the ego vehicle and surrounding agents in this latent space. On nuScenes the model reaches an avg L2 of 0.91 m and 0.43% collision rate at 6.7 FPS, beating VAD-Base while running faster.

## Problem & Motivation
Existing camera-based end-to-end planners (ST-P3, UniAD, VAD) factorize the task into perception, motion prediction, and ego planning executed in series. Two structural problems result:
1. The serial pipeline cannot model the bidirectional, high-order interaction between ego and other agents — e.g. an ego lane change should affect the predicted motion of trailing cars, but ego planning happens *after* motion prediction is frozen.
2. Most decoders directly regress trajectories from latent features and ignore the strong structural prior of real driving trajectories (mostly straight or smoothly curved, rarely zig-zag), producing implausible plans.
GenAD addresses both by jointly modeling agent and ego futures as samples from a learned trajectory distribution conditioned on a shared scene representation.

## Innovation Points
- **Instance-centric scene representation** — Adds an ego token to BEV-derived agent tokens, runs self-attention across `{ego, agents}` to capture high-order ego–agent interaction, then cross-attends with map tokens for map awareness; prediction and planning operate on the same instance set.
- **VAE trajectory prior modeling (TPM)** — A future-trajectory encoder maps ground-truth trajectories of agents and ego to Gaussian distributions in a structural latent space `Z`, capturing the realistic-trajectory prior shared across instances.
- **Latent future trajectory generation (LFTG)** — Instead of decoding the whole trajectory at once, a GRU autoregresses through latent states `z_t → z_{t+1}` and a shared MLP waypoint decoder emits one BEV waypoint per step; this factorizes `p(T|z)` along time and respects structural priors.
- **Unified prediction + planning as distribution matching** — At inference an instance encoder maps each instance token to `N(μ_i, σ_i)`; training imposes KL between this and the trajectory-prior distribution, so motion prediction and ego planning are one sampling operation in the learned latent space.

## Model Architecture
- **Inputs**: 6 surround cameras (nuScenes), 2 s history (5 frames at 2 Hz), 640×360 resolution.
- **Image backbone**: ResNet-50 + FPN multi-scale features.
- **BEV encoder**: 100×100 BEV tokens (256-d) initialized as queries; deformable cross-attention to image features (BEVFormer-style); past `p` BEV frames aligned to current ego frame.
- **BEV → map / agent**: Cross-attention produces 100 map tokens (each = 20 point tokens, 3 categories: divider, boundary, crossing) and 300 agent tokens (256-d).
- **Instance-centric tokens `I`**: Concatenate learnable ego token `e` with agent tokens `A`, apply self-attention for ego–agent interaction, then cross-attention with map tokens `M`.
- **Trajectory prior (training only)**: Future-trajectory encoder `e_f` maps GT trajectories to `N(μ_f, σ_f)` over latent `Z` (dim 512).
- **Future trajectory generator (inference)**: Instance encoder `e_i` maps each instance token to `N(μ_i, σ_i)`; sample `z^T`, then GRU `g` (hidden 512) rolls forward; MLP waypoint decoder `d_w` decodes each `z^t` to a 2-D BEV waypoint.
- **Auxiliary heads**: Map decoder, 3D object detector (bipartite matching, VAD-style), per-agent class decoder.
- **Training**: 60 epochs, 8× RTX 3090, batch size 8; AdamW, cosine LR, init 2e-4, weight decay 0.01; losses = `J_prior` (L1 trajectory + focal class) + `J_plan` (KL) + `J_map` + `J_det`, with 3 attention layers per block.
- **Output**: 3 s future ego trajectory plus joint agent trajectories at 2 Hz.

## Benchmark Results
**nuScenes val planning (camera-only, ResNet-50 backbone):**

| Method | L2 1s | L2 2s | L2 3s | L2 Avg ↓ | CR 1s | CR 2s | CR 3s | CR Avg ↓ | FPS |
|---|---|---|---|---|---|---|---|---|---|
| ST-P3 | 1.33 | 2.11 | 2.90 | 2.11 | 0.23 | 0.62 | 1.27 | 0.71 | 1.6 |
| UniAD | 0.48 | 0.96 | 1.65 | 1.03 | **0.05** | **0.17** | 0.71 | **0.31** | 1.8 |
| VAD-Tiny | 0.60 | 1.23 | 2.06 | 1.30 | 0.31 | 0.53 | 1.33 | 0.72 | 6.9 |
| VAD-Base | 0.54 | 1.15 | 1.98 | 1.22 | 0.04 | 0.39 | 1.17 | 0.53 | 3.6 |
| **GenAD** | **0.36** | **0.83** | **1.55** | **0.91** | 0.06 | 0.23 | 1.00 | 0.43 | **6.7** |

GenAD posts the best L2 average (0.91 m) and second-best collision rate (0.43%) while running 3.7× faster than UniAD. With averaged-frame metric (`†` row, avg of all predicted frames), GenAD reports L2 0.52 m / CR 0.19% vs. VAD-Base† 0.72 m / 0.22%.

**Auxiliary tasks (Table 2)**: detection mAP 0.29 (VAD 0.27); map mAP@1.5 0.71 (VAD 0.61); motion EPA car 0.59 / ped 0.34 (VAD 0.56 / 0.29).

**Ablations:**
- *Instance-centric scene representation* (Table 3): adding ego→agent self-attention to VAD lifts L2 avg 1.30 → 1.10 and CR avg 0.72 → 0.63; removing it from full GenAD degrades L2 0.91 → 1.02 and CR 0.43 → 1.22 — confirms the high-order interaction is critical.
- *Generative framework* (Table 4): TPM alone gives L2 1.02 / CR 0.60; LFTG alone 1.02 / 0.56; both combined 0.91 / 0.43 — the factorized rollout in latent space is complementary to learning the prior.

## Limitations & Open Questions
- Evaluated only on nuScenes open-loop with L2 / collision rate — both metrics are known to be weakly correlated with closed-loop driving quality; no NAVSIM, Bench2Drive, or CARLA closed-loop results.
- 3 s planning horizon, 2 Hz output; longer horizons and higher control rates are not demonstrated.
- VAE prior is learned per-instance with diagonal Gaussians — joint multi-agent dependencies are captured only through the shared scene tokens, not in the latent distribution itself, so multi-modal interactive futures may collapse.
- Authors flag generative alternatives (GANs, diffusion) as future work; GenAD itself does not benchmark against a diffusion-based action head.
- No analysis of long-tail or rare scenarios (cut-ins, jaywalkers); collision-rate gap to UniAD at 1–2 s horizons (0.06 vs. 0.05; 0.23 vs. 0.17) suggests the cheaper supervision (no track/occupancy labels) costs some short-horizon safety margin.
