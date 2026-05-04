---
paper_id: 2024-think2drive
title: "Think2Drive: Efficient Reinforcement Learning by Thinking with Latent World Model for Autonomous Driving (in CARLA-v2)"
authors: [Qifeng Li, Xiaosong Jia, Shaobo Wang, Junchi Yan]
year: 2024
venue: ECCV 2024
arxiv_id: "2402.16720"
url: https://arxiv.org/abs/2402.16720
primary_category: rl
secondary_categories: [world_model]
keywords: [model-based-rl, dreamerv3, latent-world-model, carla-v2, neural-planner, rssm, cornercaserepo]
one_line_summary: First model-based RL planner (DreamerV3-style RSSM in latent space) to solve all 39 CARLA Leaderboard v2 corner-case scenarios within 3 days on a single A6000.
distilled_at: 2026-05-04
source_pdf: doc/papers/rl/think2drive-2024.pdf
---

# Think2Drive: Efficient Reinforcement Learning by Thinking with Latent World Model for Autonomous Driving (in CARLA-v2)

## Keywords
- model-based-rl, dreamerv3, latent-world-model, carla-v2, neural-planner, rssm, cornercaserepo

## TL;DR
CARLA Leaderboard v2 introduces 39 quasi-realistic urban corner-case scenarios on which prior rule-based experts (autopilot) and model-free RL experts (Roach) both fail. The authors adapt DreamerV3's RSSM-based latent world model to AD: a compact world model is learned from BEV-rasterized privileged inputs and the planner is trained purely by "thinking" (rolling out) in latent space, plus seven engineering "bricks" (reset technique, automated scenario generation, termination-priority replay, steering cost, warm-up curriculum, asymmetric train-ratio, async CARLA wrapper). Think2Drive trains in 3 days on a single A6000 GPU and reaches 56.8 Driving Score / 91.7 Weighted Driving Score / 98.6% route completion on the official CARLA Leaderboard v2 test routes versus 0.7 / 0.6 / 1.0 for a PPO baseline.

## Problem & Motivation
Rule-based planners and existing model-free RL experts (Roach, autopilot) saturate on CARLA v1 but produce ~zero score on CARLA v2 because v2 introduces 39 long-tail corner-case scenarios (TwoWays construction, dense junction merges, opposite-lane invasion, etc.) on long 7–10 km routes. Imitation learning is impractical because expert demonstrations are scarce and behaviors are highly multimodal. Pure model-free RL is too sample-inefficient given CARLA's slow simulator (>40 s per reset). No team had reported success on CARLA v2 prior to this paper; the authors take the first model-based RL approach to AD on this benchmark, exploiting that the BEV transition function is comparatively easy to learn (vs. Atari/MineCraft) and that latent rollouts amortize the simulator cost.

## Innovation Points
- **Latent-world-model planner for AD** — first reported model-based RL system applied to CARLA v2; planner is trained entirely by rolling out in a learned latent state, decoupling sample generation from CARLA's slow physics.
- **Reset technique (Brick 1)** — periodically re-initialize all planner weights mid-training while keeping the world model fixed, escaping policy-degradation local optima caused by contradictory optimal actions across scenarios.
- **Automated scenario generation + CornerCaseRepo (Brick 2)** — auto-splits a route into many short single-scenario segments (1,600 train / 390 eval routes, <300 m each) so each of the 39 scenario types is densely sampled and individually evaluable.
- **Termination-priority replay (Brick 3)** — sample with equal probability either uniformly or from the K frames preceding episode termination, prioritizing valuable transitions where the world model has the most to learn.
- **Steering-cost reward + warm-up curriculum (Bricks 4,5)** — explicit penalty on steer-delta stabilizes vehicle heading; pre-training on simple lane-following before all-scenario training avoids over-conservative local optima.
- **Asymmetric train ratio + async CARLA wrapper (Bricks 6,7)** — planner is trained 4× more than the world model to speed convergence; CARLA is wrapped as an RL env with async reload and parallel execution to amortize >40 s resets.

## Model Architecture
- Inputs (privileged): BEV semantic-segmentation masks i_RL ∈ {0,1}^{H×W×C}; static channels (route, lanes, lane markings) collapsed to one mask, dynamic channels (vehicles, pedestrians) span T time-steps; ego speed/control/relative-height vector v_RL ∈ R^K appended.
- World model: DreamerV3 RSSM. Sequence model h_t = f_θ(h_{t-1}, z_{t-1}, a_{t-1}); encoder z_t ~ q_θ(z_t | h_t, x_t); dynamics predictor ẑ_t ~ p_θ(ẑ_t | h_t); reward r̂_t and termination ĉ_t predictors; image decoder reconstructs BEV. Trained with prediction CE loss + KL dynamics/representation losses + symlog reward loss.
- Planner: actor–critic over latent state s_t = (h_t, z_t). Actor π_η(a | s) trained on T=15-step latent rollouts; critic v_ψ uses two-hot symlog bucket-sorted return regression following DreamerV3.
- Output: continuous control discretized into 30 actions (throttle / steer / brake combinations).
- Reward: r = r_speed + α_tr·r_travel + α_de·p_deviation + α_st·c_steer.
- Hardware/scale: 3 days on a single NVIDIA A6000 GPU + AMD EPYC 7542 (128 logical cores). Total parameter count not reported.

## Benchmark Results

**Official CARLA Leaderboard test routes (Tab. 3):**
| Benchmark | Method | Driving Score ↑ | Weighted DS ↑ | Route Completion % ↑ |
|---|---|---|---|---|
| CARLA Leaderboard v1 | Roach (Expert) | 84.0 | – | 95.0 |
| CARLA Leaderboard v1 | **Think2Drive** | **90.2** | **90.2** | **99.7** |
| CARLA Leaderboard v2 | PPO (Expert) | 0.7 | 0.6 | 1.0 |
| CARLA Leaderboard v2 | **Think2Drive** | **56.8** | **91.7** | **98.6** |

**CornerCaseRepo benchmark (Tab. 1, mean ± std over 3 runs, privileged input):**
| Method | Driving Score ↑ | Weighted DS ↑ | Route Completion ↑ |
|---|---|---|---|
| Roach | 57.5 ± 9 | 54.8 ± 0.5 | 96.4 ± 1.1 |
| **Think2Drive** | **83.8 ± 1** | **89.0 ± 0.2** | **99.6 ± 0.1** |
| Think2Drive + TCP (raw sensors, distilled student) | 36.40 ± 12.23 | 29.6 ± 0.2 | 85.88 ± 8.26 |

**Per-scenario success rates (Tab. 2, 39 scenarios):** range from 0.61 (AccidentTwoWays) and 0.65 (SignalizedRightTurn) up to 1.00 (HighwayCutIn, HardBrake); majority lie in 0.75–0.95.

Ablations (Fig. 3, 500K steps, success rate over training):
- Removing Brick 1 (reset) or Brick 5 (warm-up) collapses success rate to ~0.15 — most damaging.
- Removing Brick 3 (termination-priority replay) gives a slow ascent to ~0.40.
- Removing Brick 4 (steering cost) or Brick 6 (asymmetric train ratio) reaches ~0.55–0.60 vs. ~0.72 full.

## Limitations & Open Questions
- Uses privileged BEV input (bounding boxes, HD-Map, traffic-light states); transferring to raw-sensor perception is unsolved — the distilled TCP student loses ~50 Driving Score.
- CARLA v2 Driving Score is still 56.8 (route completion 98.6% but penalty multiplications dominate); per-scenario success on TwoWays variants and signalized-junction merges is 0.61–0.76.
- Total model parameter count, latent dimensions, and inference latency are not reported.
- Real-world transfer is not evaluated; results are simulator-only.
- After arXiv release a rule-based planner (PDM-lite) also solved v2, but with heavy per-scenario hyper-parameter tuning — the relative advantage of learning-based vs. tuned rules in this regime remains open.
