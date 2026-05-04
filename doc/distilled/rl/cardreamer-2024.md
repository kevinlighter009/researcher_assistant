---
paper_id: 2024-cardreamer
title: "CarDreamer: Open-Source Learning Platform for World Model based Autonomous Driving"
authors: [Dechen Gao, Shuangyu Cai, Hanchu Zhou, Hang Wang, Iman Soltani, Junshan Zhang]
year: 2024
venue: arXiv
arxiv_id: "2405.09111"
url: https://arxiv.org/abs/2405.09111
primary_category: rl
secondary_categories: [world_model, datasets]
keywords: [world-model, model-based-rl, dreamerv3, carla, gym-interface, v2v-communication, observability, bev]
one_line_summary: Open-source CARLA+Gym platform for world-model RL in driving with pluggable WM backbone (DreamerV2/V3/Plan2Explore), 13 built-in tasks, modular task-development suite, and observability/intention-sharing studies.
distilled_at: 2026-05-04
source_pdf: doc/papers/rl/cardreamer-2024.pdf
---

# CarDreamer: Open-Source Learning Platform for World Model based Autonomous Driving

## Keywords
- world-model, model-based-rl, dreamerv3, carla, gym-interface, v2v-communication, observability, bev

## TL;DR
World-model-based RL is promising for autonomous driving but lacks an open, reproducible training platform on a high-fidelity simulator. The authors release CarDreamer, a CARLA-based, Gym-interface platform with three components: a decoupled world-model backbone (DreamerV2, DreamerV3, Plan2Explore), 13 configurable built-in driving tasks with hand-tuned reward functions, and a modular task-development suite (World Manager, Multi-Modal Observer, Route Planners, visualization server). With an 18M-parameter DreamerV3, the platform reaches >90% success rate on most built-in tasks and is used to study the effect of observation modality, observability, and V2V intention sharing.

## Problem & Motivation
RL for AV suffers from high sample complexity, and prior world-model work for driving (GAIA-1, DriveDreamer, MILE, SEM2, Think2Drive) either targets video synthesis or builds bespoke pipelines that are hard to reproduce and extend. CARLA is a high-fidelity simulator but is generic; obtaining BEVs and structured observations for RL is cumbersome, and there is no standardized Gym-style suite of WM-based driving tasks. As a result, comparing WM algorithms on driving — and varying observability, modality, or vehicle communication — requires reimplementation each time. CarDreamer fills this gap as the first open-source platform purpose-built for WM-based AV RL.

## Innovation Points
- **Decoupled WM backbone** — DreamerV2, DreamerV3, and Plan2Explore are integrated and exposed via a single Gym interface, so swapping or adding a WM does not require touching task code.
- **13 hand-tuned built-in tasks** — Right/Left turn (simple/medium/hard), Overtake, Four-lane, Navigation, Lane merge, Roundabout, Traffic lights, Stop sign; each comes with empirically optimized reward `r = α·v_parallel − β·v_perp − γ·𝕀_collision` plus waypoint terms, addressing common RL pathologies (zigzag motion, premature convergence to standstill).
- **Task Development Suite** — modular World Manager (CARLA actor spawning/control), Multi-Modal Observer with per-modality data handlers (camera, BEV, LiDAR, radar, collision, custom), and pluggable Route Planners (random, fixed-path, A*-based fixed-ending).
- **Observability and intention-sharing knobs** — three V2V observability levels (FOV, SFOV, FULL) plus optional waypoint-intention sharing, enabling controlled studies of "what to communicate" and "with whom".
- **Visualization server** — HTTP-based real-time display of agent video and statistics for fast reward engineering and debugging.

## Model Architecture
CarDreamer is a platform, not a single network. Three components plug together via the Gym interface:

- **World Model Backbone (slot)**
  - Built-in: DreamerV2, DreamerV3, Plan2Explore; user can register custom WMs.
  - Reference setting: small DreamerV3 with 18M parameters (CNN multiplier 32, 512 GRU/MLP units, 2-layer MLP, RSSM with 2 hidden layers); ~22 GB GPU memory; trains on a single NVIDIA 4090 alongside CARLA.

- **Built-in Tasks (Gymnasium)**
  - 13 tasks; each is a Task Instance exposing reset/step.
  - Per-task configs control difficulty (traffic density), observation modality (camera / BEV / LiDAR / radar / collision / custom), observability (FOV, SFOV, FULL), and intention sharing.
  - Reward includes parallel-speed reward, perpendicular-speed penalty, collision indicator, and per-task waypoint terms.

- **Task Development Suite**
  - World Manager: spawns/destroys CARLA actors (vehicles, pedestrians, sensors), supports user-controlled or autopilot vehicles.
  - Multi-Modal Observer: orchestrates per-modality data handlers; each handler is independent and lifecycle-managed.
  - Route Planners: random / fixed-path / A* fixed-ending; subclass `init_route()` and `extend_route()` for custom planners.
  - Visualization Server: streams observations, trajectories, and reward stats to a browser.

- **Data flow per step:** policy action → CARLA step (via World Manager) → Multi-Modal Observer collects sensor/BEV data → Task computes reward and terminal flag → returned through Gym interface to the WM agent → observations/stats also pushed to visualization server.

## Benchmark Results
Backbone for all reported numbers: DreamerV3 (18M params). No external baseline RL algorithms are run; the experiments characterize the platform itself.

**Table 1 — Built-in task performance (Success Rate / Collision Rate / Avg. Speed m/s):**

| Task              | Success Rate     | Collision Rate    | Avg. Speed (m/s) |
|-------------------|------------------|-------------------|------------------|
| Right turn simple | 99.21 ± 0.49%    | 0.00 ± 0.00%      | 3.19 ± 0.01      |
| Right turn medium | 98.11 ± 0.22%    | 1.89 ± 0.22%      | 2.99 ± 0.02      |
| Right turn hard   | 99.58 ± 0.42%    | 0.42 ± 0.42%      | 2.92 ± 0.02      |
| Left turn simple  | 100.00 ± 0.00%   | 0.00 ± 0.00%      | 3.21 ± 0.01      |
| Left turn medium  | 97.58 ± 0.61%    | 2.42 ± 0.61%      | 3.04 ± 0.03      |
| Left turn hard    | 92.36 ± 3.03%    | 7.64 ± 3.03%      | 2.97 ± 0.01      |
| Overtake          | 100.00 ± 0.00%   | 0.00 ± 0.00%      | 3.12 ± 0.03      |
| Four lane         | 96.83 ± 3.17%    | 3.17 ± 3.17%      | 3.47 ± 0.00      |
| Navigation        | 80.95 ± 6.41%    | 7.58 ± 4.01%      | 3.97 ± 0.08      |
| Lane merge        | 90.61 ± 1.17%    | 9.39 ± 1.17%      | 5.17 ± 0.01      |
| Roundabout        | 96.00 ± 2.31%    | 4.00 ± 2.31%      | 3.58 ± 0.00      |
| Traffic lights    | 92.65 ± 0.85%    | 0.00 ± 0.00%      | 2.26 ± 0.03      |
| Stop sign         | 97.94 ± 1.09%    | 0.00 ± 0.00%      | 1.80 ± 0.01      |

Convergence: simpler tasks (e.g., right turn simple, lane merge) converge in ~50K steps (~1 hr); collision-heavy tasks need ~150K–200K steps (3–4 hr).

**Table 2 — Observability ablation on `right turn hard` (intention sharing on):**

| Setting          | Success Rate | Collision Rate | Avg. Speed |
|------------------|--------------|----------------|------------|
| Full Observability | 99.58 ± 0.42% | 0.42 ± 0.42%  | 2.92 ± 0.02 |
| FOV Observability  | 12.44 ± 1.79% | 87.56 ± 1.79% | 2.78 ± 0.01 |
| SFOV Observability | 29.52 ± 3.46% | 70.48 ± 3.46% | 2.86 ± 0.09 |

**Table 3 — Intention-sharing ablation on `right turn hard` (full observability):**

| Setting             | Success Rate | Collision Rate | Avg. Speed |
|---------------------|--------------|----------------|------------|
| Intention Sharing   | 99.58 ± 0.42% | 0.42 ± 0.42% | 2.92 ± 0.02 |
| No Intention Sharing| 90.71 ± 0.61% | 8.94 ± 0.58% | 3.08 ± 0.00 |

WM imagination quality is shown qualitatively (Figure 4) for BEV, camera, and LiDAR modalities up to 64-step rollouts; no quantitative prediction error is reported.

## Limitations & Open Questions
- Only DreamerV3 results are reported; DreamerV2 and Plan2Explore are integrated but not benchmarked here.
- No external baselines (e.g., model-free RL, IL methods, Think2Drive) are compared on the same task suite — absolute numbers are not contextualized.
- Quantitative WM prediction accuracy across modalities is not reported (only ground-truth vs. imagination images).
- All experiments run in CARLA only; no real-world or sim-to-real transfer is evaluated.
- Curriculum, continual, transfer, and meta-learning are flagged as future work but not provided.
