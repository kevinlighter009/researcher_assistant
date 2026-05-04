---
paper_id: 2024-navsim
title: "NAVSIM: Data-Driven Non-Reactive Autonomous Vehicle Simulation and Benchmarking"
authors: [Daniel Dauner, et al.]
year: 2024
venue: NeurIPS 2024 D&B
arxiv_id: "2406.15349"
url: https://arxiv.org/abs/2406.15349
primary_category: datasets
secondary_categories: [e2e_planning]
keywords: [navsim, pdms, non-reactive-simulation, openscene, navtrain, navtest, end-to-end-planning]
one_line_summary: Non-reactive data-driven AV simulator that scores end-to-end planners with the PDM Score on filtered OpenScene splits (navtrain 103k / navtest 12k), better aligned with closed-loop than ADE.
distilled_at: 2026-05-02
source_pdf: doc/papers/datasets/navsim-2024.pdf
---

# NAVSIM: Data-Driven Non-Reactive Autonomous Vehicle Simulation and Benchmarking

## Keywords
- navsim, pdms, non-reactive-simulation, openscene, navtrain, navtest, end-to-end-planning

## TL;DR
Open-loop driving benchmarks (e.g. nuScenes ADE) misrank planners and reward "blind" ego-status extrapolators, while closed-loop simulators (CARLA, nuPlan) suffer from sensor-domain gap and high cost. NAVSIM splits the difference: the planner emits a 4-second trajectory from one real sensor frame, then a non-reactive bird's-eye-view rollout scores it with the rule-based PDM Score (PDMS). On the curated navtest split, sensor-based stacks (TransFuser, UniAD, PARA-Drive) reach PDMS around 83-84, with TransFuser (PDMS 84.0) matching much heavier UniAD (83.4) and PARA-Drive (84.0).

## Problem & Motivation
Existing AV planning benchmarks have four named failure modes the authors call out: (1) datasets like nuScenes were built for perception, so most frames have a trivial extrapolation solution and "blind" MLPs on ego status reach SOTA ADE; (2) ADE/displacement metrics penalize safe but multimodal trajectories that deviate from the human log; (3) realistic interactive evaluation requires a simulator, but graphics-based simulators (CARLA, MetaDrive) introduce a sensor domain gap and data-driven sensor sim is still poor; (4) ad-hoc planning metrics differ across papers, making numbers incomparable. NAVSIM targets all four with a single standardized pipeline and an evaluation server.

## Innovation Points
- **Non-reactive simulation horizon** - the agent commits to a 4 s trajectory from one initial real sensor frame; other agents are unrolled in BEV without reacting, sidestepping sensor synthesis while still enabling collision/progress metrics.
- **PDM Score (PDMS)** - reuses nuPlan's Predictive Driver Model scoring (no-at-fault collision NC, drivable area compliance DAC as multiplicative penalties; ego progress EP, time-to-collision TTC, comfort C as a weighted average) as a single scalar in [0, 1].
- **Challenging-scene filtering** - drops frames where a constant-velocity baseline already scores >0.8 PDMS or where the human trajectory scores <0.8, isolating the non-trivial driving decisions and dropping the constant-velocity baseline from PDMS 79 to 22.
- **Standardized splits and server** - releases navtrain (103k samples) and navtest (12k samples) on top of OpenScene (a 2 Hz, 2 TB redistribution of nuPlan), plus a HuggingFace evaluation server that hosted the CVPR 2024 challenge (143 teams, 463 submissions).
- **Apples-to-apples re-implementation** - re-trains TransFuser, LTF, UniAD, PARA-Drive, Constant Velocity, and Ego Status MLP under one protocol, the first head-to-head comparison of CARLA-lineage and nuScenes-lineage end-to-end stacks.

## Model Architecture
NAVSIM is an evaluation framework, not a network; the "architecture" is its pipeline:

- Input per scene: one current frame (and optionally 3 past frames at 2 Hz, 1.5 s history) of 8 surround cameras at 1920x1080, merged 5-LiDAR point cloud, ego speed/acceleration, and a one-hot navigation goal in {left, straight, right}.
- Agent under test outputs a future trajectory of horizon h = 4 s.
- An LQR controller tracks the trajectory and a kinematic bicycle model propagates the ego at 10 Hz over the 4 s horizon.
- Background agents are replayed non-reactively from the log over the same horizon in BEV.
- Subscores computed per frame and averaged: NC, DAC (multiplicative penalties); EP, TTC, C (weighted average with weights 5, 5, 2).
- Aggregation: PDMS = (prod_{m in {NC,DAC}} score_m) * (sum_w weight_w * score_w / sum_w weight_w), in [0, 1].
- Data source: OpenScene (a 2 Hz, ~2 TB redistribution of nuPlan with 120 hours of driving). Filtering produces navtrain (103k samples) and navtest (12k samples), totaling 450 GB. A navmini split (396 scenarios) is used for the open-loop vs closed-loop alignment study against nuPlan's CLS.

## Benchmark Results
**Navtest leaderboard (Table 1, PDMS and subscores in %):**

| Method            | NC ↑ | DAC ↑ | TTC ↑ | Comf. ↑ | EP ↑ | PDMS ↑ |
|-------------------|------|-------|-------|---------|------|--------|
| Constant Velocity | 68.0 | 57.8  | 50.0  | 100     | 19.4 | 20.6   |
| Ego Status MLP    | 93.0 | 77.3  | 83.6  | 100     | 62.8 | 65.6   |
| LTF               | 97.4 | 92.8  | 92.4  | 100     | 79.0 | 83.8   |
| TransFuser        | 97.7 | 92.8  | 92.8  | 100     | 79.2 | 84.0   |
| UniAD             | 97.8 | 91.9  | 92.9  | 100     | 78.8 | 83.4   |
| PARA-Drive        | 97.9 | 92.4  | 93.0  | 100     | 79.3 | 84.0   |
| Human             | 100  | 100   | 100   | 99.9    | 87.5 | 94.8   |

**NAVSIM 1.1 Leaderboard (Table 3, post-challenge, navtest):**

| Method            | PDMS ↑       |
|-------------------|--------------|
| Constant Velocity | 20.6         |
| Ego Status MLP    | 66.4 ± 0.9   |
| LTF               | 83.5 ± 0.6   |
| TransFuser        | 83.9 ± 0.4   |
| Hydra-MDP (challenge winner) | 91.3 |

Headline finding: under one protocol the heavy nuScenes stacks (UniAD 83.4 trained on 80 GPUs x 3 days; PARA-Drive 84.0) do not surpass the much lighter TransFuser (84.0, 1 GPU x 1 day) or even the camera-only LTF (83.8). DAC and EP are the hardest subscores; humans still lead by ~10 PDMS.

Key alignment study (Fig. 3, navmini, 37 rule-based + 114 learned planners against nuPlan CLS): PDMS is more rank- and Pearson-correlated with nuPlan's closed-loop score than the open-loop OLS for every planner type considered (Fig. 4) - the central justification for the non-reactive simplification.

Key TransFuser ablations (Table 2): dropping ego status to "goal only" lowers PDMS by 1.5-2.6; restricting to a single 60° front camera drops PDMS to 80.3 vs 84.1 default; removing BEV segmentation supervision drops PDMS by ~2.4. Multi-seed std on PDMS is ±0.56.

CVPR 2024 challenge: 463 submissions from 143 teams; the winning entry (Hydra-MDP) extended TransFuser with VADv2-style trajectory-sample scoring, while several teams attempted VLM-based planners and failed to beat the TransFuser baseline.

## Limitations & Open Questions
- Non-reactive: PDMS does not capture compounding errors or interactive long-horizon decisions; the authors recommend pairing with CARLA for full closed-loop testing.
- "At-fault" collision rules ignore certain rear-end hits into the ego, downplaying risky behavior behind the ego vehicle.
- PDMS inherits nuPlan CLS gaps: no stop-sign / traffic-light / transit / fuel-efficiency reasoning.
- Underlying nuPlan/OpenScene labels still have missing classes, camera-parameter errors, and 3D annotation noise; no road elevation in the BEV abstraction.
- Sensor-based driving simulation with realistic image / LiDAR synthesis remains an open problem the framework explicitly does not solve.
