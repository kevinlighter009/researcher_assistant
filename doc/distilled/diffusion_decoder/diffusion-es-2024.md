---
paper_id: 2024-diffusion-es
title: "Diffusion-ES: Gradient-free Planning with Diffusion for Autonomous Driving and Zero-Shot Instruction Following"
authors: [Brian Yang, Huangyuan Su, Nikolaos Gkanatsios, Tsung-Wei Ke, Ayush Jain, Jeff Schneider, Katerina Fragkiadaki]
year: 2024
venue: arXiv
arxiv_id: "2402.06559"
url: https://arxiv.org/abs/2402.06559
primary_category: diffusion_decoder
secondary_categories: [e2e_planning, vla]
keywords: [diffusion-policy, evolutionary-search, gradient-free-planning, truncated-denoising, llm-reward-shaping, nuplan, closed-loop]
one_line_summary: Combines unconditional trajectory diffusion with evolutionary search using truncated noise-denoise mutations to optimize black-box (and LLM-shaped) rewards in nuPlan closed-loop driving.
distilled_at: 2026-05-02
source_pdf: doc/papers/diffusion_decoder/diffusion-es-2024.pdf
---

# Diffusion-ES: Gradient-free Planning with Diffusion for Autonomous Driving and Zero-Shot Instruction Following

## Keywords
- diffusion-policy, evolutionary-search, gradient-free-planning, truncated-denoising, llm-reward-shaping, nuplan, closed-loop

## TL;DR
Reward-gradient guided denoising for trajectory diffusion requires differentiable reward functions fitted to noisy samples, blocking generic black-box objectives. The authors propose Diffusion-ES, an evolutionary search that scores clean trajectories sampled from an unconditional diffusion model and mutates elites via a truncated noise-then-denoise step, keeping mutations on the data manifold without ever needing to score noisy samples. On nuPlan Val14 closed-loop reactive driving it matches PDM-Closed (driving score 92) and, when paired with LLM-generated reward shaping code, follows free-form natural-language driving instructions zero-shot.

## Problem & Motivation
Prior reward-guided denoising methods (e.g., classifier guidance, gradient-guided diffusion) require a reward function that is both differentiable and well-defined on noisy intermediate trajectories — typically necessitating a re-trained noise-aware reward regressor. This restricts these methods to a narrow class of objectives and rules out many real driving rewards built from non-differentiable simulators, rule-based traffic compliance heuristics, or LLM-emitted Python reward shapers. Conditional diffusion policies can encode rewards as conditioning, but lose expressiveness and OOD generalization (the conditioning narrows the sampled distribution). Conventional gradient-free optimizers (CEM, MPPI) explore via Gaussian perturbations that ignore the data manifold, so a great deal of compute is wasted on unrealistic candidates. Diffusion-ES targets the gap: optimize arbitrary black-box rewards while staying on the trajectory manifold learned from data.

## Innovation Points
- **Diffusion-ES algorithm** — population-based evolutionary search where the diffusion model both initializes the population and acts as the mutation operator; rewards are evaluated only on clean denoised samples, so no noisy-sample reward model is needed.
- **Truncated diffusion-denoising mutation** — at iteration k, elites are noised for t_k forward steps then denoised back, producing on-manifold mutations whose strength is controlled by t_k (linearly decayed from 5 to 1 over 20 search steps in their setup).
- **Unconditional trajectory model + test-time guidance** — by deliberately not conditioning on scene, the diffusion prior remains broad and supports OOD behaviors (lane weaving, aggressive overtaking) that conditional diffusion policies cannot reach.
- **LLM-to-reward-shaping pipeline** — natural-language driving instructions are mapped via few-shot LLM prompting to executable Python *generator functions* (stateful across calls) that reshape a base nuPlan reward; Diffusion-ES then optimizes the shaped, non-differentiable reward zero-shot.
- **First evolutionary search with diffusion for closed-loop driving** — to the authors' knowledge, the first work coupling evolutionary search with diffusion models, and the first to apply diffusion-based generative models to closed-loop nuPlan planning.

## Model Architecture
- **Trajectory diffusion model p_theta** — operates over ego-vehicle action sequences only (no scene conditioning in the main variant). Trajectory representation: 8-second future of 2D pose (x, y, theta) at 2 Hz, action dimension 48. Trained with T = 100 denoising steps.
- **Population search loop (Algorithm 1):**
  - Initial proposals X^0 of M = 128 samples drawn from full reverse-diffusion of p_theta.
  - Score each x_i with black-box reward R(x_i) (clean samples only).
  - Resample elites E^k via softmax weights q(x) = exp(tau * R(x)) / Z (temperature tau).
  - Renoise elites for t_k forward steps: bar_E^k = sqrt(alpha_bar) * x + sqrt(1 - alpha_bar) * eps.
  - Denoise back through the last t_k reverse steps to get clean X^{k+1}.
  - Repeat for K search steps; return argmax R(x).
- **Reward function for closed-loop nuPlan** — modified PDM-Closed scoring: predicted trajectory is converted to controls via an LQR tracker, propagated through a kinematic bicycle model, simulated with constant-velocity other agents, and scored with the nuPlan benchmark metrics plus auxiliary terms (lead-vehicle proximity penalty, speed-limit enforcement). Non-differentiable due to tracker and rule-based traffic-violation heuristics.
- **Language-shaped reward path** — LLM (few-shot prompted) emits Python generator functions calling a scene-API (e.g., `get_vehicle`, `get_right_lane`, `add_lane_follow_reward`) that *modify* the base reward rather than replace it; supports temporally sequenced instructions via retained generator state.
- **Real-time variant** — fewer denoising steps (T = 10), M = 32, K = 2 → 2 Hz inference matching simulator rate.
- **Total params / training data scale** — not reported.

## Benchmark Results
**Closed-loop driving on nuPlan Val14 (reactive agent track, driving score, higher is better):**

| Class | Method | Driving Score |
|---|---|---|
| Train-then-test | UrbanDriverOL | 65 |
| Train-then-test | PlanCNN | 72 |
| Train-then-test | Diffusion Policy | 50 |
| Test-time optimize | IDM | 77 |
| Test-time optimize | PDM-Closed (prior SOTA) | 92 |
| Test-time optimize | **Diffusion-ES (ours)** | **92** |

Matches the engineered SOTA (PDM-Closed) while substantially outperforming all learned reactive policies.

**Lane following (differentiable reward, 14 scenarios, lower is better):**

| Method | Lane Error | Speed Error |
|---|---|---|
| CEM | 2.34 | 2.05 |
| MPPI | 3.29 | 2.74 |
| Reward-gradient guidance | 1.22 | 0.96 |
| **Diffusion-ES (ours)** | **0.61** | **0.79** |

Beats reward-gradient guidance even though the reward is differentiable — the authors attribute this to gradient guidance being unreliable on intermediate noisy trajectories.

**Language instruction following (8 tasks, success rate, see Figure 4):** Diffusion-ES outperforms PDM-Closed, PDM-Closed-Multilane, and Conditional Diffusion-ES on the majority of tasks (4 of 8 vs PDM-Closed-Multilane). Per-task numerical success rates not reported in tabular form; only bar chart provided.

**Runtime (Table 3, wallclock seconds per inference):**

| Method | Wallclock (s) |
|---|---|
| Diffusion (single sample) | 1.11 +- 0.02 |
| Diffusion-ES | 5.85 +- 0.11 |
| Diffusion-ES (optimized: T=10, M=32, K=2) | 0.50 +- 0.01 |

Optimized variant runs at 2 Hz with driving score dropping only from 92 to 91.

**Key ablations:**
- Conditional Diffusion-ES (scene-conditioned model) significantly underperforms the unconditional variant on language instruction tasks — confirming the inference-speed vs OOD-generalization trade-off the authors identify.
- Both diffusion-based methods substantially outperform CEM/MPPI sampling-based search, validating the manifold-aware mutation operator.

## Limitations & Open Questions
- Computational overhead — vanilla Diffusion-ES is ~5x slower than a single diffusion forward pass; the optimized variant works but loses 1 point of driving score.
- Reward function assumes constant-velocity other agents and no reaction to ego — known weakness of nuPlan-style planners in self-driving evaluations.
- Language instructions currently require a human teacher; authors flag memory-prompted analogical reward shaping for autonomous long-tail handling as future work.
- Closed-loop evaluation only on nuPlan Val14 (one benchmark); no real-vehicle deployment, no closed-loop evaluation on harder benchmarks.
- Per-task numerical success rates for language instruction following are presented only as a bar chart — exact values not reported.
- Total parameter count of the diffusion model and dataset scale used for training are not reported in the main paper.
