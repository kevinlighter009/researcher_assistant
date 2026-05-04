---
paper_id: 2022-cadre
title: "CADRE: A Cascade Deep Reinforcement Learning Framework for Vision-based Autonomous Urban Driving"
authors: [Yinuo Zhao, Kun Wu, Zhiyuan Xu, Zhengping Che, Qi Lu, Jian Tang, Chi Harold Liu]
year: 2022
venue: AAAI 2022
arxiv_id: "2202.08557"
url: https://arxiv.org/abs/2202.08557
primary_category: rl
secondary_categories: [perception, e2e_planning]
keywords: [deep-rl, ppo, co-attention, carla, nocrash, behavior-cloning, distributed-training]
one_line_summary: Cascade framework that pre-trains a frozen Co-attention Perception Module (CoPM) on multi-task BC, then trains a distributed PPO agent on its latent features for vision-based urban driving in CARLA.
distilled_at: 2026-05-04
source_pdf: doc/papers/rl/cadre-2022.pdf
---

# CADRE: A Cascade Deep Reinforcement Learning Framework for Vision-based Autonomous Urban Driving

## Keywords
- deep-rl, ppo, co-attention, carla, nocrash, behavior-cloning, distributed-training

## TL;DR
Vision-based urban driving with model-free DRL is brittle in dense traffic because reward signals are sparse and perception is hard to learn jointly with control. CADRE decouples the problem into two cascade stages: an offline-trained, frozen Co-attention Perception Module (CoPM) that fuses RGB + behavior-cloning information via co-attention, followed by a distributed PPO policy trained on top of CoPM latents with a carefully shaped reward. On the CARLA NoCrash benchmark CADRE outperforms IL (LBC) and DRL (IARL) baselines across all conditions, and it converges with 3.2M samples vs IARL's 20M.

## Problem & Motivation
Imitation learning (IL) for urban driving (CIL, CILRS, LBC, ChauffeurNet) suffers from biased expert data (mostly lane-following) and distribution shift at test time. Prior end-to-end DRL approaches (CIRL, IARL, DeRL) work in empty scenes but fail in dense urban traffic with many vehicles and pedestrians: (1) urban perception is too complex for a DRL agent to learn jointly with control, and (2) sparse reward signals make it hard to evaluate long-horizon driving behavior. Authors argue perception and control should be decoupled and that vision-only perception is insufficient — control/behavior information should also condition perception.

## Innovation Points
- **Cascade two-stage design** — offline supervised pre-training of perception (frozen CoPM), then online DRL of the policy; reduces sample complexity for the RL stage.
- **Co-attention Perception Module (CoPM)** — DANet-backbone two-branch network (visual branch + behavior-cloning branch) coupled by cross-branch co-attention, so visual features are conditioned on control-relevant cues and vice versa.
- **Multi-task BC pre-training** — CoPM is supervised on route-image reconstruction, semantic segmentation, traffic-light classification, and steer/throttle regression simultaneously.
- **Data-diversity augmentation** — adds Gaussian noise to autopilot actions (p=0.7) when collecting the CoPM dataset, exposing CoPM to off-policy states the PPO agent will encounter.
- **Distributed PPO with chief-worker** — N workers each run a CARLA server + local PPO; gradients aggregated by a chief process; combined with carefully shaped dense reward (deviation angle, deviation distance, velocity to a target band) and sparse event reward.
- **Sequential LSTM head** — 8-frame LSTM on CoPM latents captures temporal dependencies for long-term behavior.

## Model Architecture
- Inputs at time t: front-camera RGB c (3×H×W), measurement vector m (position, orientation, speed), waypoint sequence w from rule-based planner.
- Preprocessing: m and w rendered into a route image g (same size as c); concatenated channel-wise with c → fed to CoPM.
- CoPM (frozen after stage 1):
  - DANet backbone produces two feature streams: visual x_vis and behavior-cloning x_bc.
  - Co-attention block computes K/Q/V from each branch; visual attention queried by q_bc, behavior attention queried by q_vis (asymmetric, not self-attention).
  - Outputs latent z = [z_vis, z_bc] from attention-weighted sum.
  - Heads (training only): H_rou (route reconstruction, MSE), H_cam (semantic seg, CE), H_lig (traffic-light cls, CE), H_ste (steer regression, MSE), H_thro (throttle regression, MSE). Loss weights 0.5/1.0/0.1/0.1/0.1.
- Stage 2 PPO agent:
  - State = [m, z]; LSTM over 8 consecutive frames yields ẑ_t.
  - Discrete action: steer ∈ 33 bins over [-1,1]; throttle/brake collapsed to {accelerate, move_forward, decelerate}.
  - Clipped PPO surrogate; chief-worker distributed setup with 4 workers.
- Datasets: CoPM trained on 315,545 samples (256×144 RGB) collected via noisy autopilot in 25 NoCrash training routes; PPO trained on 112 augmented short routes plus 78+81 obstacle-avoidance scenarios.
- Total training samples for CADRE convergence: 3.2M (vs. ~20M for IARL).

## Benchmark Results
**CARLA NoCrash (success rate, CARLA 0.9.10):**
| Setting              | IARL | LBC | CoPM (BC only) | CADRE (Ours) |
|----------------------|------|-----|----------------|--------------|
| Train town/Train wx Empty   | 85   | 89  | 62 | **95** |
| Train/Train Regular         | 86   | 87  | 63 | **92** |
| Train/Train Dense           | 63   | 75  | 70 | **82** |
| Train/Test wx Empty         | -    | 60  | 62 | **94** |
| Train/Test Regular          | -    | 60  | 66 | **86** |
| Train/Test Dense            | -    | 54  | 72 | **76** |
| Test/Train Empty            | 77   | 86  | 86 | **92** |
| Test/Train Regular          | 66   | **79** | 70 | 78 |
| Test/Train Dense            | 33   | 53  | 39 | **61** |
| Test/Test Empty             | -    | 36  | 44 | **78** |
| Test/Test Regular           | -    | 36  | 44 | **72** |
| Test/Test Dense             | -    | 12  | 30 | **52** |

CADRE wins 11/12 cells; biggest gain on Test/Test Dense (+40 vs LBC).

**Obstacle-avoidance scenarios (success / total):**
| Method | Vehicle (/81) | Pedestrian (/78) |
|--------|---------------|------------------|
| LBC    | 55            | 73               |
| IARL   | 69            | 57               |
| CADRE  | **81**        | **76**           |

**Ablations (success rate on obstacle avoidance):**
- CoPM ablation: visual-only CoPM 75/39, CoPM w/o co-attention 76/68, full CoPM 81/76 — co-attention adds ~+5 vehicle, ~+8 pedestrian over no-attention.
- PPO ablation: Basic CADRE 51/51, +LSTM 71/61, full distributed 81/76 — both LSTM and distributed training contribute substantially.
- Sample efficiency: CADRE converges in 3.2M samples vs IARL ~20M.

## Limitations & Open Questions
- Evaluated only in CARLA 0.9.10; no real-world or other simulator validation.
- Action space is discretized (33-bin steer, 3-way throttle/brake) — limits smoothness and may hurt comfort metrics (not reported).
- Inference latency / compute cost of CoPM + LSTM-PPO per frame not reported.
- CoPM is frozen, so the perception module cannot adapt to corner-case states encountered only by the converged PPO policy; a single re-collection pass with noisy autopilot may not cover all such states.
- Reward shaping (deviation angle, distance, target-velocity band) is hand-designed and tuned to NoCrash route format; transferability to free-form navigation tasks unclear.
- No comparison against more recent IL/world-model methods (paper compares only to IARL and LBC).
