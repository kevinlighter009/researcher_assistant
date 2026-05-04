---
paper_id: 2023-motiondiffuser
title: "MotionDiffuser: Controllable Multi-Agent Motion Prediction using Diffusion"
authors: [Chiyu "Max" Jiang, Andre Cornman, Cheolho Park, Ben Sapp, Yin Zhou, Dragomir Anguelov]
year: 2023
venue: CVPR 2023 (Highlight)
arxiv_id: "2306.03083"
url: https://arxiv.org/abs/2306.03083
primary_category: diffusion_decoder
secondary_categories: [e2e_planning]
keywords: [diffusion-model, multi-agent-prediction, permutation-invariant, pca-latent, constrained-sampling, waymo-open-motion]
one_line_summary: Conditional diffusion head over PCA-compressed multi-agent trajectories with a permutation-invariant set denoiser and differentiable constraint guidance for controllable joint prediction.
distilled_at: 2026-05-02
source_pdf: doc/papers/diffusion_decoder/motiondiffuser-2023.pdf
---

# MotionDiffuser: Controllable Multi-Agent Motion Prediction using Diffusion

## Keywords
- diffusion-model, multi-agent-prediction, permutation-invariant, pca-latent, constrained-sampling, waymo-open-motion

## TL;DR
Multi-agent motion forecasting needs to model a multimodal joint distribution over interacting agents and to support test-time constraints (rules, physical priors, in-painting). The authors learn a conditional denoising diffusion model over multi-agent trajectories with a permutation-invariant transformer set denoiser, a PCA-compressed latent representation, and a generic differentiable cost-guidance scheme (with score thresholding). On the Waymo Open Motion Dataset Interactive split, MotionDiffuser achieves state-of-the-art minSADE (0.86) and minSFDE (1.95) versus prior anchor- and heatmap-based methods.

## Problem & Motivation
Motion prediction in driving must be (i) probabilistic and multimodal, (ii) jointly reasoned over multiple interacting agents (independent marginals yield conflicting futures), and (iii) controllable so that downstream simulation or planning can inject rules, physical priors or in-painting endpoints. Prior supervised regressors (MultiPath, MultiPath++, Wayformer) rely on hand-defined trajectory anchors or goal sets and only model marginals; generative alternatives (HP-GAN, CVAE, normalizing flows) struggle with sample quality or controllability; and concurrent diffusion work (CTG) requires inner-loop optimization at every denoising step. None offers a single permutation-invariant joint distribution that is also amenable to arbitrary differentiable constraints.

## Innovation Points
- **Permutation-invariant set denoiser** — transformer with self-attention across agents and cross-attention to per-agent scene tokens, with no positional encoding along the agent axis, yielding an equivariant denoiser and therefore an invariant joint set distribution p(S; C).
- **PCA latent trajectory diffusion** — trajectories (80x2 DoF) are diffused in a PCA-compressed space (10 components, 99.7% variance); faster inference, easier constraint sampling, and better accuracy than diffusing in raw space.
- **Differentiable constraint guidance for any cost** — approximates the constraint score by differentiating a cost L through the denoised trajectory D(S;C,sigma), enabling attractor (waypoint in-painting) and repeller (collision avoidance) costs without retraining.
- **Constraint score thresholding (ST)** — clips the guidance score to ±1/sigma, stabilising constrained sampling and avoiding the inner-optimization loop used by concurrent CTG.
- **Exact log-probability inference** — uses the instantaneous change-of-variables (FFJORD-style) on the diffusion ODE in PCA space to score samples, giving an O(n^2) (or O(n) with Hutchinson) likelihood usable for filtering.

## Model Architecture
- Inputs: agent histories, context agents, traffic-light states, road graph, encoded by a Wayformer scene encoder into per-agent condition tokens C in R^{N_a x N_c x ...}.
- Trajectories: per-agent future S_i in R^{N_t x N_f} (N_t = 80 steps, 2 features = (x,y)); represented in PCA latent space S in R^{N_a x N_p}, N_p = 10 components.
- Forward (training): sample noise level sigma ~ q(sigma), add eps ~ N(0, sigma^2 I) to GT trajectories; train preconditioned denoiser D_theta with L2 denoising-score-matching loss (Karras-style preconditioning c_skip, c_in, c_out, c_noise).
- Set denoiser block: noisy trajectory + Fourier-encoded sigma -> projection -> 2 repeated blocks of [self-attention across agents] + [cross-attention to condition tokens C] -> projection back to PCA features.
- Sampling: Heun 2nd-order ODE solver on the linear-schedule sigma(t)=t with 32 steps; samples drawn from N(0, sigma_max^2 I) and denoised to S_pred; inverse PCA gives waypoint trajectories.
- Optional guidance: at each step, add lambda * d/dS L(D(S;C,sigma)) to the score, with cost L = attractor (mask-weighted L1 to a target endpoint) or repeller (pairwise inter-agent distance below radius r=5 m), clipped via score thresholding.
- Sample clustering: trajectory aggregation (MultiPath++) is run jointly across agents to produce 6 representative joint futures for the WOMD Interactive metric.
- Backbone params / training data scale: not reported beyond "uses Wayformer encoder" trained on the Waymo Open Motion Dataset.

## Benchmark Results
**Waymo Open Motion Dataset, Interactive split (joint scene-level metrics, averaged over t = 3, 5, 8 s):**

| Method                  | minSADE down | minSFDE down | SMissRate down | mAP up |
|-------------------------|--------------|--------------|----------------|--------|
| LSTM baseline           | 1.91         | 5.03         | 0.78           | 0.05   |
| HeatIRm4                | 1.42         | 3.26         | 0.72           | 0.08   |
| SceneTransformer (J)    | 0.98         | 2.19         | 0.49           | 0.12   |
| M2I                     | 1.35         | 2.83         | 0.55           | 0.12   |
| DenseTNT                | 1.14         | 2.49         | 0.54           | 0.16   |
| MultiPath++             | 1.00         | 2.33         | 0.54           | 0.17   |
| JFP                     | 0.88         | 1.99         | **0.42**       | **0.21** |
| **MotionDiffuser (Test)** | **0.86**   | **1.95**     | **0.42**       | 0.20   |

Validation split numbers are similar (minSADE 0.86, minSFDE 1.92, mAP 0.19, Overlap 0.036 — best Overlap among reported methods).

**Constraint effectiveness (Table 2, validation):**
- Attractor (target final point): MotionDiffuser meanSFDE 0.007 vs. unconstrained 8.731; SR2m 0.952, SR5m 0.994, while keeping minSADE 0.533 and Overlap 0.040 — far more realistic than naive optimization (minSADE 4.563) and better than CTG (minSADE 1.18, Overlap 0.057).
- Removing score thresholding (Ours -ST): SR2m drops 0.952 -> 0.913 and constraint error rises (minSFDE 1.078 vs. 0.007); confirms ST is essential.
- Repeller (5 m radius): Overlap drops from 0.059 (no constraint) to 0.008 — about an order of magnitude reduction.

**Architecture / representation ablations (Table 3, WOMD Interactive Val):**
| Variant              | minSADE down | minSFDE down | SMissRate down |
|----------------------|--------------|--------------|----------------|
| Ours (-PCA)          | 1.03         | 2.29         | 0.53           |
| Ours (-Transformer)  | 0.93         | 2.08         | 0.47           |
| Ours (-SelfAttention)| 0.91         | 2.07         | 0.46           |
| MotionDiffuser       | **0.88**     | **1.97**     | **0.43**       |

PCA latent diffusion contributes the largest share of the gain; cross-agent self-attention is needed for consistent joint predictions.

PCA reconstruction analysis: 10 components capture 99.7% of explained variance; per-waypoint reconstruction error 0.06 m, well below SOTA prediction error.

## Limitations & Open Questions
- Evaluated only on the Waymo Open Motion Dataset Interactive split; no closed-loop driving or cross-dataset generalization (e.g. nuScenes, Argoverse) reported.
- Inference cost (32 ODE steps with a transformer denoiser, plus optional guidance) and total parameter count are not reported; deployment latency on vehicle hardware is unaddressed.
- Constraint costs demonstrated are simple (attractor on a target point, isotropic repeller at 5 m); scaling to richer rule sets (kinematics, traffic-law semantics) is left to future work.
- PCA basis is fitted on training trajectories with linear interpolation of missing steps; behaviour under distribution shift (rare manoeuvres, longer horizons) and 80-step truncation is not analysed.
- Authors flag extension to planning and scene generation as future work, implying current setup is prediction-only and does not couple with an ego planner.
