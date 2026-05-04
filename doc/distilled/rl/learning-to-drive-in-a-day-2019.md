---
paper_id: 2019-l2diad
title: "Learning to Drive in a Day"
authors: [Alex Kendall, Jeffrey Hawke, David Janz, Przemyslaw Mazur, Daniele Reda, John-Mark Allen, Vinh-Dieu Lam, Alex Bewley, Amar Shah]
year: 2019
venue: ICRA 2019
arxiv_id: "1807.00412"
url: https://arxiv.org/abs/1807.00412
primary_category: rl
secondary_categories: [e2e_planning]
keywords: [ddpg, model-free-rl, lane-following, vae-state-encoding, monocular-rgb, prioritized-replay, real-vehicle]
one_line_summary: First on-vehicle model-free deep RL (DDPG with VAE-encoded monocular image) learning lane-following on a real car in ~11 episodes, using distance-to-disengagement as reward.
distilled_at: 2026-05-04
source_pdf: doc/papers/rl/learning-to-drive-in-a-day-2019.pdf
---

# Learning to Drive in a Day

## Keywords
- ddpg, model-free-rl, lane-following, vae-state-encoding, monocular-rgb, prioritized-replay, real-vehicle

## TL;DR
Modular driving stacks and imitation learning both struggle to scale: the former needs hand-engineered components and HD maps, the latter cannot cover every long-tail scenario and lacks a corrective mechanism. The authors cast lane following as an MDP with a sparse reward (distance travelled before safety-driver disengagement) and learn a continuous policy with DDPG from a single forward-facing monocular image plus speed/steering. With a Variational Autoencoder pre-trained online to compress the image, an on-vehicle Renault Twizy learns a 250 m country-road lane-following policy in 11 training episodes (~15 min of optimisation), demonstrating the first deep RL agent driving a real car.

## Problem & Motivation
Commercial autonomous-driving stacks rely on detailed 3D maps and many separately tuned components (perception, localisation, planning, control), which is brittle and expensive to scale. Imitation learning is end-to-end but cannot enumerate every scenario and offers no corrective signal when the demonstrator's distribution is exited. Prior on-vehicle RL work (Riedmiller et al. 2007) used dense GPS-tracking-error rewards and non-image inputs; RL in driving simulators (e.g. video games) leverages privileged ground truth (e.g. lane angle) unavailable on a real car. The authors want a generic, image-based, sparse-reward, on-vehicle RL setup that does not depend on maps, hand-coded rules, or expert trajectories.

## Innovation Points
- **First deep-RL real-car demonstration** — model-free DDPG learns a lane-following policy directly on a Renault Twizy from raw monocular video plus speed/steering, with all exploration and optimisation done on-vehicle.
- **Disengagement-distance reward** — sparse reward = forward speed each step, episode terminated by safety-driver intervention; eliminates the need for lane-classification supervision, HD maps, or GPS tracking error.
- **Online VAE state encoding** — a small VAE is trained from five purely random exploration episodes (KL + L2 reconstruction) and used to compress images into a low-dim latent for DDPG, dramatically improving sample efficiency over end-to-end pixel DDPG.
- **Stateful task-based training architecture** — a four-task state machine (train / test / undo / done) lets the safety driver discard contaminated episodes (e.g. other road users) and gracefully end runs, making the on-vehicle interactive loop tractable.
- **Sim-to-real hyperparameter transfer** — Unreal-Engine-4 procedurally generated country-road simulator is used purely to tune RL hyperparameters (learning rate, gradient steps per episode, termination policy), and the same settings transfer directly to the real car with only the exploration-noise model rescaled.
- **Continuous action space + Ornstein-Uhlenbeck exploration** — 2-D continuous action (steering in [-1, 1] and speed set-point in km/h) found smoother than discrete actions; OU noise added to the actor for exploration; prioritised experience replay weights TD-error-large transitions.

## Model Architecture
- Inputs: single forward-facing monocular RGB frame + scalar vehicle speed and steering angle.
- Image encoder (shared by actor and critic): 4 conv layers, 3x3 kernels, stride 2, 16 feature dimensions.
- Actor head: flatten encoder output, concatenate scalar state, one fully-connected layer (size 8), regress to the 2-D action (steering, speed set-point).
- Critic head: same trunk, additionally concatenates the action, one FC layer (size 8), regresses to a scalar Q value.
- VAE variant (used for the real-car experiments): encoder of the same shape with a transposed-convolution decoder; trained online from 5 random episodes with KL + L2 reconstruction loss; latent feeds the DDPG actor/critic in place of raw pixels.
- Algorithm: DDPG with prioritised experience replay (TD-error-proportional sampling, new samples given infinite weight) and OU exploration noise added to the actor's optimal policy.
- On-vehicle execution loop: RL Model at 10 Hz emits action, downstream Controller at 100 Hz tracks it, drive-by-wire sends throttle/steer/brake to the Twizy. All compute on a single NVIDIA Drive PX2.
- Training data scale: 11 on-vehicle episodes (~195.5 m driven, ~15 min of optimisation) for the VAE variant; 35 episodes (~298.8 m, ~37 min) for raw-pixel DDPG.

## Benchmark Results

**Real-world 250 m private-road lane-following (Renault Twizy):**
| Model              | Train episodes | Train distance | Train opt. time | Meters per disengagement (test, higher is better) | # Disengagements |
|--------------------|----------------|----------------|-----------------|---------------------------------------------------|------------------|
| Random Policy      | -              | -              | -               | 7.35                                              | 34               |
| Zero Policy (straight, constant speed) | - | -    | -               | 22.7                                              | 11               |
| Deep RL from Pixels | 35            | 298.8 m        | 37 min          | 143.2                                             | 1                |
| **Deep RL from VAE** | **11**       | **195.5 m**    | **15 min**      | not reported (best test run completed full 250 m route) | **0**            |

(Numbers from Table I; the VAE-variant test column reports 0 disengagements, i.e. the agent completed the 250 m route — meters-per-disengagement value not stated.)

**Simulation (UE4 country-road):**
- Lane-follow learnable from raw images "within 10 training episodes".
- VAE state representation accelerates DDPG (Fig. 4): autonomous distance climbs to ~250 m for `ddpg+vae` by ~10 episodes; raw `ddpg` only reaches ~150 m by ~40 episodes.
- Hyperparameters that transferred to real: discount = 0.9, OU noise half-life = 250 episodes, theta = 0.6, sigma = 0.4, 250 optimisation steps per episode, batch 64, gradient clipping 0.005.

Ablations / qualitative findings:
- Continuous action space outperforms discrete (discrete -> jerky policy).
- VAE-compressed state vs. raw pixels: VAE far more data-efficient and the only reliable variant in the real world.

## Limitations & Open Questions
- Sparse reward becomes weaker as the policy improves (interventions get rarer); the authors expect to need a richer reward to learn a "super-human" driving agent and flag this is open.
- Reward conditions only on staying on the road; no navigation goal, no lane-change command, no obstacle / right-of-way reasoning; the paper acknowledges command-conditional rewards as future work.
- Evaluation is a single 250 m private rural road in fair conditions with one car; no traffic, intersections, weather, or night driving.
- VAE compression alone is insufficient for richer scenes; the authors point to semi-supervised state representations (depth, ego-motion, segmentation) and domain transfer as needed next steps.
- The reward function does not encode traffic rules (e.g. drive-on-correct-side), so agents may learn awkward manoeuvres (e.g. turning right in the UK).
- Safety: the experimental loop relies entirely on a human safety driver to terminate / reset episodes; no formal safety case.
