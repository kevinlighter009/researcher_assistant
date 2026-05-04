---
paper_id: 2024-bench2drive
title: "Bench2Drive: Towards Multi-Ability Benchmarking of Closed-Loop End-To-End Autonomous Driving"
authors: [Xiaosong Jia, Zhenjie Yang, Qifeng Li, Zhiyuan Zhang, Junchi Yan]
year: 2024
venue: NeurIPS 2024 D&B
arxiv_id: "2406.03877"
url: https://arxiv.org/abs/2406.03877
primary_category: datasets
secondary_categories: [e2e_planning]
keywords: [closed-loop-benchmark, carla, e2e-ad, multi-ability, think2drive-expert, short-routes, driving-score]
one_line_summary: A CARLA-based closed-loop benchmark for E2E autonomous driving with a 2M-frame official training set and 220 short single-skill routes covering 44 interactive scenarios for granular multi-ability evaluation.
distilled_at: 2026-05-02
source_pdf: doc/papers/datasets/bench2drive-2024.pdf
---

# Bench2Drive: Towards Multi-Ability Benchmarking of Closed-Loop End-To-End Autonomous Driving

## Keywords
- closed-loop-benchmark, carla, e2e-ad, multi-ability, think2drive-expert, short-routes, driving-score

## TL;DR
Existing E2E autonomous driving (E2E-AD) evaluations are either open-loop on nuScenes (poor proxy for driving) or use very long CARLA routes whose driving-score metric has high variance and conflates skills. Bench2Drive provides an official 2M-frame CARLA training set collected by the Think2Drive RL expert from 13638 clips spanning 44 interactive scenarios, 23 weathers and 12 towns, plus a 220-route closed-loop test set where each ~150 m route isolates one scenario for per-skill scoring. Implemented baselines (UniAD, VAD, TCP, ThinkTwice, DriveAdapter, AD-MLP) achieve at most 33.08% Success Rate and 64.22 Driving Score, with mean per-ability score of 42.08% (DriveAdapter).

## Problem & Motivation
- Open-loop nuScenes evaluation (L2 / collision) is a weak proxy: the validation set is small and ~75% of frames just require driving straight, so even an MLP on ego state is competitive with sensor-based models.
- Closed-loop CARLA benchmarks (Town05Long, Longest6, Leaderboard v2) use 7-10 km routes whose Driving Score is the product of route completion and an exponentially-decaying infraction penalty; this gives high variance and on Leaderboard v2 participating methods score under 10/100, making cross-method comparison meaningless.
- Existing closed-loop methods collect their own training data, so reported gains conflate algorithmic improvement with data quality, blocking fair algorithm-level comparison.
- CARLA Leaderboard v2 ships no official expert demonstrations, so different teams cannot reproduce a common training distribution.

## Innovation Points
- **Official large-scale CARLA training set** -- 2M annotated frames from 13638 clips at 10 Hz, balanced across 44 scenarios, 23 weathers, 12 towns; mini (10), base (1000), full (10000) clip splits are provided for different compute budgets.
- **Think2Drive RL teacher** -- the only expert reported able to clear all 44 Bench2Drive scenarios; its value estimates and features are released for distillation experiments.
- **Short-route protocol (220 routes, ~150 m each)** -- one specific scenario per route in a fixed (location, weather) pair; brevity damps the exponential infraction penalty so Driving Score becomes more discriminative.
- **Multi-ability evaluation** -- the 44 scenarios are bucketed into 5 abilities (Merging, Overtaking, Emergency Brake, Give Way, Traffic Sign), each scored separately, exposing per-skill strengths/weaknesses instead of a single average.
- **Augmented metrics** -- Efficiency uses 20 in-route checkpoints (not 4 as in CARLA Leaderboard) for a smoother speed-percentage estimate; Comfortness adapts nuPlan smoothness using segment-level (n=20) windows so a single justified hard brake does not poison the whole trajectory.
- **nuScenes-compatible sensor rig** -- 1 LiDAR (64 ch, 85 m), 6 surround cameras (900x1600), 5 radars, IMU/GNSS, BEV camera, HD-Map; annotations cover 3D boxes, depth, semantic/instance segmentation, point cloud, lane detection.

## Model Architecture
Bench2Drive is a dataset and benchmark, not a model. Pipeline:

- **Expert / data collector**: Think2Drive, a model-based RL agent given CARLA privileged information (locations, intents, traffic-light states), drives all 44 scenarios under varied weathers/towns; rule-based PDM-Lite is mentioned as a later open-source alternative.
- **Clip generation**: 13638 clips uniformly distributed across 44 scenarios x 23 weathers x 12 towns, each ~150 m, segmented into mini/base/full subsets (10 / 1000 / 10000 clips); 2M frames at 10 Hz with full annotations and the expert's value/feature outputs.
- **Sensor configuration** (nuScenes-style for re-implementation compatibility): 1x 64-ch LiDAR, 6x cameras (900x1600), 5x radars, IMU+GNSS, BEV debug camera, HD-Map.
- **Closed-loop evaluation harness**: 220 short routes (44 scenarios x 5 (location, weather) instances), each defining (x_src, y_src) -> (x_dst, y_dst); the AD model must drive the ego from source to destination using raw sensors + waypoints.
- **Metrics emitted per route and aggregated per ability**:
  - Success Rate = successful routes / total routes (no infractions, reaches destination in time).
  - Driving Score = mean over routes of route_completion * product(infraction penalties).
  - Efficiency = mean speed-percentage vs nearby vehicles over 20 checkpoints.
  - Comfortness (Smoothness) = fraction of n=20 segments whose longitudinal/lateral accel, yaw rate, yaw accel, jerk all stay within nuPlan-style human bounds.
- **Implemented baselines** (all trained on the 1000-clip base subset, 950 train / 50 open-loop val): UniAD-Tiny, UniAD-Base (transformer queries on BEV), VAD (vectorized scene), AD-MLP (ego-state MLP), TCP (front camera + ego, joint trajectory & control), ThinkTwice (coarse-to-fine planning with expert distillation), DriveAdapter (decoupled perception/planning with expert distillation). UniAD/VAD/ThinkTwice/DriveAdapter trained on 8x A100; AD-MLP and TCP on 1x A6000.

## Benchmark Results
Bench2Drive reports its own baseline leaderboard, not comparison to an external method. Numbers below are from Tables 3 and 4 of the paper, all using the base (1000-clip) training subset.

**Open-loop and closed-loop results (Table 3):**

| Method                  | Avg L2 down | Driving Score up | Success Rate (%) up | Efficiency up | Comfortness up |
|-------------------------|-------------|------------------|---------------------|---------------|----------------|
| AD-MLP                  | 3.64        | 18.05            | 0.00                | 48.45         | 22.63          |
| UniAD-Tiny              | 0.80        | 40.73            | 13.18               | 123.92        | 47.04          |
| UniAD-Base              | **0.73**    | 45.81            | 16.36               | 129.21        | 43.58          |
| VAD                     | 0.91        | 42.35            | 15.00               | **157.94**    | **46.01**      |
| TCP*                    | 1.70        | 40.70            | 15.00               | 54.26         | 47.80          |
| TCP-ctrl*               | not reported| 30.47            | 7.27                | 55.97         | 51.51          |
| TCP-traj*               | 1.70        | 59.90            | 30.00               | 76.54         | 18.08          |
| TCP-traj w/o distillation | 1.96      | 49.30            | 20.45               | 78.78         | 22.96          |
| ThinkTwice*             | **0.95**    | 62.44            | 31.23               | 69.33         | 16.22          |
| DriveAdapter*           | 1.01        | **64.22**        | **33.08**           | 70.22         | 16.01          |

`*` denotes expert-feature distillation.

**Multi-ability scores (Table 4, % per ability and mean):**

| Method        | Merging | Overtaking | Emergency Brake | Give Way | Traffic Sign | Mean   |
|---------------|---------|------------|-----------------|----------|--------------|--------|
| AD-MLP        | 0.00    | 0.00       | 0.00            | 0.00     | 4.35         | 0.87   |
| UniAD-Tiny    | 8.89    | 9.33       | 20.00           | 20.00    | 15.43        | 14.73  |
| UniAD-Base    | 14.10   | 17.78      | 21.67           | 10.00    | 14.21        | 15.55  |
| VAD           | 8.11    | 24.44      | 18.64           | 20.00    | 19.15        | 18.07  |
| TCP*          | 16.18   | 20.00      | 20.00           | 10.00    | 6.99         | 14.63  |
| TCP-ctrl*     | 10.29   | 4.44       | 10.00           | 10.00    | 6.45         | 8.23   |
| TCP-traj*     | 8.89    | 24.29      | **51.67**       | 40.00    | 46.28        | 34.22  |
| TCP-traj w/o distillation | 17.14 | 6.67 | 40.00         | **50.00**| 28.72        | 28.51  |
| ThinkTwice*   | 27.38   | 18.42      | 35.82           | **50.00**| 54.23        | 37.17  |
| DriveAdapter* | **28.82**| **26.38** | 48.76           | **50.00**| **56.43**    | **42.08**|

Key takeaways the authors highlight:
- AD-MLP attains low L2 but 0% Success Rate and 0% on every interactive ability; open-loop L2 fails as a proxy for closed-loop driving once models are well-fit.
- UniAD-Base has lower L2 than VAD (0.73 vs 0.91) yet worse closed-loop Driving Score (45.81 vs ... actually higher; VAD is 42.35), confirming open-loop ranking does not match closed-loop ranking.
- Expert-feature distillation matters: TCP-traj with vs without distillation goes 59.90 to 49.30 Driving Score; methods using distillation (TCP / ThinkTwice / DriveAdapter) dominate the leaderboard.
- All methods are weak on interactive abilities (Merging, Overtaking, Emergency Brake), attributed to long-tail interactive frames within each clip and to imitation-learning training paradigms.

## Limitations & Open Questions
- CARLA rendering still has a sim-to-real gap ("cartoon style"); the authors note real-world datasets (e.g., NAVSIM) are complementary and suggest diffusion-based generative rendering as a future direction (with caveats about hallucinations).
- Baselines were trained only on the base 1000-clip subset (8x A100 ceiling); the full 10000-clip subset is provided but no scaling-law results are reported in the main paper.
- Per-ability scoring of 5 buckets is coarse; the 44 scenarios are still grouped, and within-bucket scenario design choices are not validated.
- The expert (Think2Drive) uses privileged information; how much of the residual gap to expert behavior is due to perception vs. planning is not isolated.
- No real-vehicle deployment study; the benchmark explicitly is intended to "complement, not replace" on-road testing.
