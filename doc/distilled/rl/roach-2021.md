---
paper_id: 2021-roach
title: "End-to-End Urban Driving by Imitating a Reinforcement Learning Coach"
authors: [Zhejun Zhang, Alexander Liniger, Dengxin Dai, Fisher Yu, Luc Van Gool]
year: 2021
venue: ICCV 2021
arxiv_id: "2108.08265"
url: https://arxiv.org/abs/2108.08265
primary_category: rl
secondary_categories: [e2e_planning]
keywords: [ppo, rl-coach, bev-input, beta-distribution, imitation-learning, dagger, carla, nocrash]
one_line_summary: PPO-trained BEV-input RL coach (Beta action dist + exploration loss) outperforms CARLA Autopilot, then supervises a camera-input IL student via action-distribution, value, and feature losses.
distilled_at: 2026-05-04
source_pdf: doc/papers/rl/roach-2021.pdf
---

# End-to-End Urban Driving by Imitating a Reinforcement Learning Coach

## Keywords
- ppo, rl-coach, bev-input, beta-distribution, imitation-learning, dagger, carla, nocrash

## TL;DR
End-to-end driving agents trained by imitation learning are bottlenecked by their experts: humans cannot provide on-policy supervision, and CARLA's hand-crafted Autopilot is suboptimal and emits only deterministic actions that carry little information. The authors train Roach, a PPO-based RL "coach" that maps ground-truth BEV semantic images to continuous low-level actions using a Beta action distribution and a novel exploration loss, surpassing the CARLA Autopilot. They then distill Roach into a single-camera IL student with action-distribution (KL), value, and latent-feature losses, reaching 78% success on NoCrash-dense new town & weather and an expert-level 88% driving score in the train-town busy setting.

## Problem & Motivation
Imitation learning for end-to-end urban driving suffers from two coupled problems:
- Human experts cannot easily supply on-policy labels, so IL agents (CIL, CILRS) suffer covariate shift; DAgger-style fixes require an expert that can be queried on arbitrary states.
- The standard automated expert in CARLA, the rule-based Autopilot/roaming agent, is hand-crafted and drives suboptimally; prior proxy experts (LBC's privileged agent, SAM, Chauffeurnet) are themselves IL-trained and inherit the Autopilot's ceiling. Existing RL agents on CARLA (CIRL, A3C, Rainbow-IQN-based Chen et al.) are sample-inefficient or underperform.
The paper argues that what's missing is an automated expert that (i) is trainable rather than rule-based, (ii) outperforms the Autopilot, and (iii) emits informative supervision (distributions, values, features) beyond a single deterministic action.

## Innovation Points
- **Roach RL coach** — PPO agent that ingests a BEV semantic image plus a measurement vector and outputs continuous low-level actions; trained from scratch and surpasses the CARLA Autopilot, setting a new performance upper-bound on CARLA.
- **Beta action distribution** — Beta(alpha, beta) over bounded steering and acceleration replaces the usual squashed Gaussian; bounded support removes clipping/tanh, enables exact entropy and KL, and its modality suits emergency-style maneuvers.
- **Exploration loss** — generalizes the entropy loss: when one of a defined terminal events (collision, red-light/stop infraction, route deviation, blocked) ends an episode, the last N_z=100 steps are pushed via KL toward a hand-set advice prior p_z (e.g. Beta(1, 2.5) on acceleration when about to collide) instead of the uniform prior; stabilizes training where vanilla PPO+entropy collapses.
- **Distillation losses for the IL student** — beyond the standard L1 action loss L_A, the authors add: (i) L_K, KL between Roach's predicted action distribution and the student's (soft targets); (ii) L_V, MSE on Roach's value estimate; (iii) L_F, L2 on Roach's latent feature j_RL vs. student's j_IL. The combination L_K + L_F(c) gives the best student.
- **Improved Autopilot baseline** — the authors' re-implementation of Autopilot already beats LBC/DA-RB Autopilots, giving a stronger baseline against which Roach's gains are measured fairly.

## Model Architecture
RL coach (Roach):
- Input 1: BEV semantic image i_RL in [0,1]^{W x H x C}, rendered from CARLA ground truth, with C channels covering drivable areas, desired route, lane boundaries, vehicles (K-frame temporal stack), pedestrians (K-frame), and lights/stops (red/yellow/green encoded by intensity, plus stop-sign trigger areas).
- Input 2: measurement vector m_RL in R^6 (steering, throttle, brake, gear, lateral & horizontal speed).
- Encoders: 6 conv layers for BEV + 2 FC layers for measurements, concatenated and processed by 2 FC layers into a latent j_RL.
- Heads: action head outputs Beta(alpha, beta) over a in [-1, 1]^2 (steering, acceleration where positive = throttle, negative = brake); value head outputs scalar v.
- Training: PPO-clip with policy loss L_ppo + entropy loss L_ent + exploration loss L_exp; reward from Toromanoff et al. plus a steering-change penalty and a high-speed infraction penalty; trajectories collected from 6 CARLA servers at 10 FPS, one per LeaderBoard map; A* desired routes between random start/goal pairs.
- Scale: ~1.7M PPO steps per server x 6 = 10M steps total; ~1 week on AWS EC2 g4dn.4xlarge or 4 days on a 2080 Ti / 12-core machine.

IL student (CILRS-style, supervised by Roach):
- Input: single wide-angle camera image i_IL in [0,1]^{900 x 256 x 3}, 100 deg FOV; measurement m_IL = speed (NoCrash) or speed + 2D vector to next desired waypoint (LeaderBoard).
- Image encoder: ImageNet-pretrained ResNet-34 producing a 1000-d feature; measurement encoder + 3 FC layers produce j_IL in R^256, same dimension as j_RL.
- Branched heads conditioned on the discrete navigation command (CILRS), each with action head and speed head.
- Training: DA-RB scheme = CILRS + DAgger over 5 iterations, with combined loss L_K + L_V + L_F (best variant L_K + L_F(c) on NoCrash); supervision targets come from Roach's action distribution, value, and latent feature.

## Benchmark Results

**Experts on NoCrash-dense (Success Rate %, mean +- std over 3 seeds; columns: train town & train weather / train town & new weather / new town & train weather / new town & new weather; LB-all = all 76 LeaderBoard routes with dynamic weather):**

| Expert | NCd-tt | NCd-tn | NCd-nt | NCd-nn | LB-all |
|--------|--------|--------|--------|--------|--------|
| PPO+exp (no Beta) | 86 +- 6 | 86 +- 6 | 79 +- 6 | 77 +- 5 | 67 +- 3 |
| PPO+beta (no exp loss) | 95 +- 3 | 96 +- 3 | 83 +- 5 | 87 +- 6 | 72 +- 5 |
| **Roach (PPO+beta+exp)** | 91 +- 4 | 90 +- 7 | 83 +- 3 | 83 +- 5 | 72 +- 6 |
| AP (authors' Autopilot) | 95 +- 3 | 95 +- 3 | 83 +- 5 | 81 +- 2 | 75 +- 8 |
| AP-lbc | 86 +- 3 | 83 +- 6 | 60 +- 3 | 59 +- 8 | N/A |
| AP-darb | 71 +- 4 | 72 +- 3 | 41 +- 2 | 43 +- 1 | N/A |

Roach and PPO+beta beat all prior Autopilots; on driving score (a stricter metric) Roach reaches 95 +- 2 / 95 +- 3 / 91 +- 3 / 90 +- 2 / 85 +- 3 vs. AP at 86 +- 2 / 86 +- 2 / 70 +- 2 / 70 +- 1 / 78 +- 3, because RL experts handle traffic lights better (Autopilots wait too long and miss the green).

**Camera-based IL students on NoCrash-dense (Success Rate %, DAgger iter 5, mean +- std over 3 seeds):**

| Method | NCd-tt | NCd-tn | NCd-nt | NCd-nn |
|--------|--------|--------|--------|--------|
| LBC (0.9.6) | 71 +- 5 | 63 +- 5 | 51 +- 3 | 39 +- 6 |
| SAM (0.8.4) | 54 +- 3 | 47 +- 5 | 29 +- 3 | 29 +- 3 |
| LSD (0.8.4) | N/A | N/A | 30 +- 4 | 32 +- 3 |
| DA-RB+(E) | 66 +- 5 | 56 +- 1 | 36 +- 3 | 35 +- 2 |
| DA-RB+ (0.8.4) | 62 +- 1 | 60 +- 1 | 34 +- 2 | 25 +- 1 |
| Authors' baseline L_A(AP) | 88 +- 4 | 29 +- 3 | 32 +- 11 | 28 +- 4 |
| **Authors' best L_K + L_F(c)** | 86 +- 5 | 82 +- 2 | 78 +- 5 | 78 +- 0 |

The best Roach-supervised student loses less than 10% success when generalizing to new town & weather, vs. catastrophic drops for the Autopilot-supervised baseline.

**Infraction analysis on NoCrash-busy, new town & new weather (per Km, mean +- std, 3 seeds; iter 5):**

| Agent | Success | Driv. Score | Route Compl. | Infrac. Pen. | Coll. Other | Coll. Ped. | Coll. Veh. | Red Light | Blocked |
|-------|---------|-------------|--------------|--------------|-------------|------------|------------|-----------|---------|
| L_A (AP) | 31 +- 7 | 43 +- 2 | 62 +- 6 | 77 +- 4 | 0.54 +- 0.53 | 0 +- 0 | 0.63 +- 0.50 | 3.33 +- 0.58 | 19.4 +- 14.4 |
| L_A (Roach) | 57 +- 7 | 66 +- 2 | 84 +- 5 | 76 +- 1 | 2.07 +- 1.37 | 0 +- 0 | 1.36 +- 1.10 | 1.4 +- 0.2 | 2.82 +- 1.45 |
| L_K | 74 +- 3 | 79 +- 0 | 91 +- 2 | 86 +- 1 | 0.50 +- 0.25 | 0 +- 0 | 0.53 +- 0.18 | 0.68 +- 0.08 | 3.39 +- 0.20 |
| **L_K + L_F(c)** | **87 +- 5** | **88 +- 3** | **96 +- 0** | **91 +- 3** | 0.08 +- 0.04 | 0.01 +- 0.01 | 0.23 +- 0.06 | 0.61 +- 0.23 | 0.84 +- 0.04 |
| Roach | 95 +- 2 | 96 +- 3 | 100 +- 0 | 96 +- 3 | 0 +- 0 | 0.11 +- 0.07 | 0.04 +- 0.05 | 0.16 +- 0.20 | 0 +- 0 |
| Autopilot | 91 +- 1 | 79 +- 2 | 98 +- 2 | 80 +- 2 | 0 +- 0 | 0 +- 0 | 0.18 +- 0.08 | 1.93 +- 0.23 | 0.18 +- 0.08 |

Key ablations:
- Switching the IL teacher from Autopilot to Roach (still L_A only) improves driving score by ~23% absolute, isolating the gain from a better expert under identical IL recipe.
- Adding L_K + L_F(c) on top of the Roach expert adds another ~22% absolute driving-score improvement, isolating the gain from richer supervision (soft action targets + latent features); final 88% is expert-level on NoCrash with a single camera.
- Without the exploration loss, vanilla PPO+entropy with Gaussian collapses to standing still (local minimum); PPO+exp recovers high return at slightly higher variance; Beta further stabilizes training (Fig. 4).
- Single-branch architecture with command as a one-hot in m_IL: L_K + L_F(c) and L_K + L_V + L_F(c) achieve the best driving score on NoCrash new town & weather, even outperforming the Autopilot.
- Value loss helps DAgger converge faster when paired with feature matching, but L_K + L_V alone (without L_F) does not.

## Limitations & Open Questions
- Even the best IL student does not saturate the offline LeaderBoard benchmark (gap to Roach is large in Fig. 5); larger model capacity is suggested as future work.
- Roach assumes ground-truth BEV (drivable area, routes, lights/stops, vehicles, pedestrians) at training time; real-world deployment as an on-policy labeller would require synthesizing the BEV from 3D detection + extra sensors, and the paper acknowledges sim-to-real gaps beyond photorealism (notably realistic road-user behavior).
- The exploration prior p_z is hand-designed per terminal-event class (collision, red light, route deviation, etc.); generalizing this advice prior is open.
- Evaluation is CARLA-only (NoCrash + offline LeaderBoard public routes); no real-world or even online LeaderBoard ranking is reported, and Autopilot training was on CARLA 0.9.10.1 with evaluation on 0.9.11.
