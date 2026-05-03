---
paper_id: 2025-diffusion-planner
title: "Diffusion-Based Planning for Autonomous Driving with Flexible Guidance"
authors: [Yinan Zheng, Ruiming Liang, Kexin Zheng, Jinliang Zheng, Liyuan Mao, Jianxiong Li, Weihao Gu, Rui Ai, Shengbo Eben Li, Xianyuan Zhan, Jingjing Liu]
year: 2025
venue: ICLR 2025
arxiv_id: "2501.15564"
url: https://arxiv.org/abs/2501.15564
primary_category: diffusion_decoder
secondary_categories: [e2e_planning]
keywords: [diffusion-planner, dit, classifier-guidance, closed-loop-planning, joint-prediction, nuplan, training-free-guidance]
one_line_summary: A DiT-based diffusion planner that jointly models ego planning and neighbor prediction with classifier-guided trajectory refinement; SOTA closed-loop performance on nuPlan without rule-based post-processing.
distilled_at: 2026-05-02
source_pdf: doc/papers/diffusion_decoder/diffusion-planner-2025.pdf
---

# Diffusion-Based Planning for Autonomous Driving with Flexible Guidance

## Keywords
- diffusion-planner, dit, classifier-guidance, closed-loop-planning, joint-prediction, nuplan, training-free-guidance

## TL;DR
Existing learning-based planners struggle to model multi-modal human driving behavior and rely heavily on rule-based post-processing for safety. The authors propose *Diffusion Planner*, a DiT-based diffusion model that jointly generates ego trajectories and neighbor predictions, conditioned on scene + navigation, and supports training-free classifier guidance for safety/comfort/speed. On nuPlan closed-loop benchmarks (Val14, Test14, Test14-hard), it reaches state-of-the-art among learning-based planners and, with an off-the-shelf refinement module, surpasses rule-based and hybrid baselines.

## Problem & Motivation
Rule-based planners (IDM, PDM-Closed) are interpretable but brittle to novel situations. Pure imitation-learning planners (UrbanDriver, PlanTF, GameFormer) suffer three named failure modes: (1) behavior cloning lacks theoretical guarantees for multi-modal distributions, leading to error accumulation in closed loop; (2) out-of-distribution handling forces fallback to rule-based refinement (e.g., GameFormer/PLUTO post-processing) that re-imports rule-based limitations; (3) auxiliary safety losses create multi-objective conflicts and poor recovery from mistakes. Existing diffusion-for-planning works (Hu et al. 2024; Yang et al. 2024) only sprinkle diffusion loss on top of standard frameworks and still depend on heavy post-processing. The authors argue diffusion's expressiveness and classifier-guidance flexibility have not been properly exploited for closed-loop autonomous planning.

## Innovation Points
- **DiT-based joint planning + prediction** — A single diffusion transformer denoises a trajectory tensor stacking ego and M nearest neighbors, removing the need for a dedicated prediction sub-module or auxiliary losses; cooperative behaviors emerge from joint score modeling.
- **Vehicle Information Integration via concatenation** — Future trajectories are concatenated with current vehicle states as the diffusion input; this fixes a clear starting point and notably *excludes* ego velocity/acceleration from the decoder to avoid learning shortcuts (informed by Cheng et al. 2023).
- **MLP-Mixer scenario encoder** — A unified MLP-Mixer encodes information-sparse vector inputs (neighbors, lanes, navigation, static obstacles), replacing the more complex bespoke encoders used by GameFormer/PlanTF.
- **Adaptive-LayerNorm navigation conditioning** — Navigation tokens are fused with the diffusion timestep via adaptive LayerNorm (DiT-style) and broadcast across all trajectory tokens, enabling controllable route following.
- **Training-free classifier guidance for behavior alignment** — Uses diffusion posterior sampling so the gradient of a differentiable energy (collision, comfort, target speed, drivable area) modifies the score *at inference*, no extra classifier training required; energies are composable.
- **Engineering recipe for closed-loop training** — State-perturbation augmentation, quintic-polynomial interpolation back to GT, ego-centric coordinate transform, and per-axis z-score normalization (μ=10, σ=20 on x; y scaled to same magnitude). DPM-Solver and low-temperature sampling enable 20 Hz inference.

## Model Architecture
- **Inputs (within 100 m of ego, last 2 s of history):**
  - Neighbors (up to 32 vehicles): `S_neighbor ∈ R^{L×D_neighbor}`, L=21 past timesteps, D_neighbor=11 (coords, heading, vel, size, category).
  - Lanes (up to 70): `S_lane ∈ R^{P×D_lane}`, P=20 points/polyline, D_lane=12 (coords, traffic light, speed limit).
  - Navigation: route lanes (up to 25) `S_route ∈ R^{K×P×D_route}` (coordinate-only).
  - Static objects: MLP-encoded.
- **Encoder:**
  - Two MLP-Mixer towers (one for neighbors, one for lanes) → pooled tokens.
  - MLP for static obstacles.
  - Concatenated tokens fed to a vanilla transformer self-attention encoder, producing scenario representation `Q_f`.
- **Conditioning:**
  - Navigation tokens encoded by another MLP-Mixer → `Q_n`, added to diffusion timestep embedding `Q_t` → adaLN modulation in DiT blocks.
- **Diffusion Decoder (DiT, 3 blocks; hidden dim 192; 6 heads):**
  - Target `x^{(0)}` is a tensor stacking ego trajectory + M=10 neighbor trajectories; per-step state = (x, y, sin θ, cos θ) — sufficient for downstream LQR controller.
  - Self-attention over vehicle tokens + multi-head cross-attention to scenario `Q_f`; FFN; scale-shift modulation.
  - Trained with x0-prediction loss (Eq. 5).
- **Output:** 8 s future ego trajectory at 10 Hz (80 waypoints, 4D each) + neighbor predictions; produced at ~20 Hz inference on a single A6000 GPU.
- **Sampling:** DPM-Solver++ with VP noise schedule, 10 denoising steps, low-temperature 0.5 (0.1 when refinement is appended).
- **Training:** 8× A100 80GB GPUs, batch 2048, 5 epochs warmup, AdamW lr 5e-4.
- **Classifier guidance energies (training-free, composable):** collision avoidance (signed-distance based), target speed maintenance, comfort (longitudinal jerk), staying within drivable area (Euclidean SDF map).

## Benchmark Results
**Closed-loop nuPlan (final score, 0–100, higher better; NR = non-reactive, R = reactive):**

| Type             | Planner                       | Val14 NR | Val14 R | Test14-hard NR | Test14-hard R | Test14 NR | Test14 R |
|------------------|-------------------------------|----------|---------|----------------|---------------|-----------|----------|
| Expert           | Log-replay                    | 93.53    | 80.32   | 85.96          | 68.80         | 94.03     | 75.86    |
| Rule/Hybrid      | PDM-Closed                    | 92.84    | 92.12   | 65.08          | 75.19         | 90.05     | 91.63    |
| Rule/Hybrid      | PLUTO                         | 92.88    | 76.88   | 80.08          | 76.88         | 92.23     | 76.88    |
| **Rule/Hybrid**  | **Diffusion Planner w/ refine.** | **94.26** | **92.90** | **78.87**     | **82.00**     | **94.80** | **91.75** |
| Learning         | PlanTF                        | 84.27    | 76.95   | 69.70          | 61.61         | 85.62     | 79.58    |
| Learning         | PLUTO w/o refine.*            | 88.89    | 78.11   | 70.03          | 59.74         | 89.90     | 78.62    |
| **Learning**     | **Diffusion Planner (Ours)**  | **89.87** | **82.80** | **75.99**     | **69.22**     | **89.19** | **82.93** |

(* = uses pre-searched reference lines as input.)

**Closed-loop on 200-h Haomo.AI delivery-vehicle dataset (Diffusion Planner score 92.08 vs. PLUTO hybrid 83.49, GameFormer 51.35, PlanTF 90.89), demonstrating transfer to a different vehicle type / driving style.**

**Selected ablations (Test14, score):**
| Variant                       | Score  |
|-------------------------------|--------|
| Diffusion Planner (base)      | 89.19  |
| w/o z-score normalization     | 85.02  |
| w/o trajectory interpolation  | 83.07  |
| w/o data augmentation         | 76.53  |
| w/ ego state in decoder (SDE) | 82.90  |
| w/ ego state (kept fully)     | 78.65  |
| w/o current state             | 81.11  |

Inference grid search (Fig. 7) shows scores fairly robust to denoise steps (5–25) and temperature (0.1–1.0). M=10 predicted neighbors is near-optimal; M=32 hurts by injecting noise (Fig. 6).

## Limitations & Open Questions
- **Vectorized inputs only** — the planner consumes processed map + detection vectors, not raw images; not an end-to-end pipeline. The authors propose swapping the encoder for image-based inputs as future work.
- **Lateral flexibility** — learning-based planners (including this one) underperform rule-based methods on lane changes / large lateral maneuvers, because nuPlan training data is dominated by straight-driving; data augmentation only partially helps.
- **Sample efficiency / inference cost** — diffusion needs multiple denoising steps; achieves 20 Hz with DPM-Solver but consistency-model or distillation acceleration is left for future work.
- **Reliance on downstream LQR controller** — the model emits trajectories rather than control signals, leaving a planner-controller gap that may produce OOD behavior in scenarios needing fine-grained actuation.
- **Best closed-loop number on nuPlan still requires post-processing** — the pure learning-only Diffusion Planner is SOTA among learning baselines but only beats hybrid baselines once an off-the-shelf refinement module is appended.
