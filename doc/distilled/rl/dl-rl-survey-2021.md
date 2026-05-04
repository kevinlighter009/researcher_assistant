---
paper_id: 2021-drl-ad-survey
title: "Deep Reinforcement Learning for Autonomous Driving: A Survey"
authors: [B Ravi Kiran, Ibrahim Sobh, Victor Talpaert, Patrick Mannion, Ahmad A. Al Sallab, Senthil Yogamani, Patrick Perez]
year: 2021
venue: IEEE T-ITS 2021
arxiv_id: "2002.00444"
url: https://arxiv.org/abs/2002.00444
primary_category: rl
secondary_categories: [misc, e2e_planning]
keywords: [deep-rl, autonomous-driving, mdp, imitation-learning, inverse-rl, sim-to-real, safe-rl]
one_line_summary: Survey of deep RL applied to autonomous driving — MDP background, AD task taxonomy (lane-keep / change / merge / overtake / intersection / motion planning), simulators, and real-world deployment challenges.
distilled_at: 2026-05-04
source_pdf: doc/papers/rl/dl-rl-survey-2021.pdf
---

# Deep Reinforcement Learning for Autonomous Driving: A Survey

## Keywords
- deep-rl, autonomous-driving, mdp, imitation-learning, inverse-rl, sim-to-real, safe-rl

## TL;DR
The authors survey deep reinforcement learning (DRL) algorithms and their application to autonomous-driving (AD) tasks. They give a self-contained tutorial on RL (MDP formalism, value-/policy-/actor-critic methods, DQN, DDPG, A3C, TRPO, PPO), then organize AD applications into a taxonomy of subtasks (controller learning, motion planning, lane-keep / lane-change / ramp-merge / overtaking / intersections / driving policy) along with adjacent paradigms (behavior cloning, GAIL, inverse RL). The survey closes with the key real-world deployment challenges: validation, sim-to-real gap, sample efficiency, reward design, safety, and multi-agent coordination. No head-to-head benchmark numbers are presented — this is a literature survey, not a benchmarking study.

## Problem & Motivation
Classical AD stacks decompose into perception, scene understanding, planning, and control modules built largely on supervised learning and rule-based planners (A*, RRT, MPC, PID). These approaches struggle with high-dimensional state spaces, long-tail interactive scenarios (negotiation at intersections, merges, overtakes), and reward/cost-function design under uncertainty. RL is a natural fit because driving is a sequential decision-making problem under partial observability, but DRL for AD is an emergent field scattered across many sub-communities with no consolidated reference. The authors aim to (i) give the AD community a self-contained RL primer, (ii) catalog where DRL has been applied to driving subtasks, and (iii) surface the open challenges that block real-world deployment.

## Innovation Points
This is a survey, so the contributions are organizational rather than algorithmic:
- **Self-contained DRL tutorial for the AD community** — covers MDPs/POMDPs, value-based (Q-learning, DQN, dueling/double/prioritized variants, DRQN), policy-based (REINFORCE, TRPO, PPO, DPG), actor-critic (DDPG, A3C, ACER, SAC), plus extensions: reward shaping, IRL, GAIL, multi-objective RL, multi-agent RL, MAML/Reptile meta-learning, hierarchical RL with options.
- **AD-task taxonomy** — explicit mapping from AD subtasks to the DRL methods that have been tried (Table I): lane keeping (DQN/DDAC on TORCS), lane change (Q-learning), ramp merging (LSTM policies), overtaking (Double-Action Q-Learning), intersection negotiation (DQN with creep-go), motion planning (DQN-augmented A*).
- **Catalog of state/action/reward design choices** — survey of state representations (raw pixels vs. occupancy grid vs. BEV vs. structured features like TTC, lane id, curvature) and reward criteria (distance to goal, speed, collisions, infractions, comfort).
- **Simulator inventory** (Table II) — CARLA, TORCS, AirSim, GAZEBO, SUMO, DeepDrive, NVIDIA Constellation, MADRaS, Flow, Highway-env, Carcraft — with modality coverage.
- **Framework inventory** (Table III) — OpenAI Baselines, Unity ML-Agents, RL Coach, TF-Agents, rlpyt, bsuite.
- **Real-world challenge enumeration** — validation/reproducibility, bridging the sim-to-real gap (domain randomization, domain adaptation), sample efficiency (transfer learning, meta-learning, world models), exploration in IL (DAgger, SEARN, SMILE), intrinsic rewards / curiosity, safe RL (Safe DAgger, SORL, constrained MDPs), and multi-agent RL for negotiation and adversarial testing.

## Model Architecture
The "architecture" of the survey is its organizing taxonomy. Conceptual data flow:

- **Standard AD pipeline (Fig. 1)** — Sense (cameras / LiDAR / radar / ultrasonics) → Perceive & Localize (detection, lane detection, semantic segmentation, SLAM, HD maps) → Scene Representation (sensor fusion, behavior prediction, object map) → Plan & Decide (path / motion planning, trajectory optimization, driving policy) → Control (velocity profile, steering, accel/brake). RL is positioned to replace or augment the "Plan & Decide" and "Control" stages, and increasingly to learn end-to-end driving policies.

- **RL agent decomposition (Fig. 3)** — Environment (real-world or simulator) emits observation o_t and reward r_t → Agent with state s_t (continuous or discrete), function approximator (CNN), and RL method (value/policy/actor-critic, on/off-policy, model-based/free) → driving policy π: S → A producing discrete or continuous action a_t (steering / throttle / brake or discrete maneuvers).

- **Survey taxonomy axes**:
  - **RL family**: value-based / policy-based / actor-critic; model-based vs. model-free; on-policy vs. off-policy.
  - **AD subtask**: controller, lane-keep, lane-change, ramp-merge, overtaking, intersection, motion planning, end-to-end driving.
  - **Adjacent paradigm**: imitation learning (BC, DAgger), inverse RL, GAIL, hierarchical RL with options.
  - **Deployment-readiness axis**: validation, sim-to-real, sample efficiency, reward design, safety, multi-agent.

- **Section structure**: §II AD pipeline; §III RL fundamentals; §IV DRL extensions (PG, AC, model-based, IL/IRL); §V RL applied to AD tasks (state/action/reward design, motion planning, simulators, IRL/LfD); §VI real-world challenges; §VII conclusion. Appendix includes acronym table.

## Benchmark Results
Not reported in survey. The paper is a literature review and does not run head-to-head comparisons or report unified benchmark numbers across methods. Where individual cited works' results are mentioned (e.g. continuous-action DDAC giving smoother trajectories than discrete DQN for lane keeping; A3C with sim-to-real domain translation evaluated on a real driving dataset; DDPG combined with safety-based control on TORCS), the authors describe trends and trade-offs qualitatively rather than tabulating metrics.

The survey instead catalogs the evaluation infrastructure:

**Simulators (Table II):** CARLA, TORCS, AirSim, GAZEBO/ROS, SUMO, DeepDrive, NVIDIA DRIVE Constellation, MADRaS, Flow, Highway-env, Carcraft. CARLA Challenge is highlighted as a closed competition with NHTSA-derived pre-crash scenarios.

**Frameworks (Table III):** OpenAI Baselines, Unity ML-Agents, RL Coach, TF-Agents, rlpyt, bsuite.

## Limitations & Open Questions
The survey itself enumerates the open challenges (§VI) — these are the field's open questions as of 2021:
- **Validation & reproducibility** — RL results are highly sensitive to hyperparameters and seeds; top-k rollout estimation is unprincipled (Henderson et al.).
- **Sim-to-real gap** — domain randomization and domain adaptation help but no general solution; closed-loop on-vehicle evaluation rare.
- **Sample efficiency** — driving data is expensive/risky to collect; transfer learning, meta-learning (MAML, Reptile), and world models are partial answers.
- **Reward design** — explicit reward signals are absent in the real world; reward shaping, IRL, and intrinsic curiosity rewards remain open research.
- **Safety** — Safe DAgger, SORL (constrained MDPs with negative-avoidance), and hybrid DRL+safety controllers are early efforts; no consensus framework.
- **Multi-agent RL** — driving is inherently multi-agent (other vehicles, pedestrians, cyclists); MARL for negotiation and adversarial scenario generation is under-explored.
- **Survey-specific limitations** — no quantitative cross-method comparison; coverage skews toward simulator work; very little public real-world deployment data; the field has moved substantially since 2021 (no coverage of large-scale offline RL, transformer-based world models, or VLM-conditioned policies).
