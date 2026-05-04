---
paper_id: 2021-nuplan
title: "nuPlan: A closed-loop ML-based planning benchmark for autonomous vehicles"
authors: [Holger Caesar, Juraj Kabzan, Kok Seang Tan, Whye Kit Fong, Eric Wolff, Alex Lang, Luke Fletcher, Oscar Beijbom, Sammy Omari]
year: 2021
venue: "arXiv (CVPR 2021 Workshop on Autonomous Driving; NeurIPS 2021 dataset release)"
arxiv_id: "2106.11810"
url: https://arxiv.org/abs/2106.11810
primary_category: datasets
secondary_categories: [e2e_planning]
keywords: [nuplan, closed-loop, planning-benchmark, motional, autolabeling, simulation, lidar, scenario-mining]
one_line_summary: First large-scale (1500h, 4 cities) ML-based motion planning benchmark with a lightweight closed-loop simulator and planning-specific metrics beyond L2.
distilled_at: 2026-05-02
source_pdf: doc/papers/datasets/nuplan-2021.pdf
---

# nuPlan: A closed-loop ML-based planning benchmark for autonomous vehicles

## Keywords
- nuplan, closed-loop, planning-benchmark, motional, autolabeling, simulation, lidar, scenario-mining

## TL;DR
Existing AV motion benchmarks (Argoverse, Lyft, Waymo Open Motion, nuScenes-Predict) target short-term *prediction* with open-loop L2-style metrics, which are ill-suited for evaluating long-horizon, multi-modal *planning*. The authors release nuPlan: 1500 hours of human driving data from 4 cities (Boston, Pittsburgh, Las Vegas, Singapore) with autolabeled tracks, semantic maps, raw sensor data on a subset, a lightweight closed-loop simulator with reactive and non-reactive agents, and planning-specific metrics (traffic-rule violation, human-similarity, vehicle dynamics, goal achievement, scenario-based). It is positioned as the first public real-world AV planning benchmark with a closed-loop evaluation protocol.

## Problem & Motivation
Prior AV datasets confuse prediction with planning: they evaluate short-horizon (3–8 s) trajectory forecasts in open-loop using L2-based metrics (minADE, minFDE, miss rate). The authors argue this is inadequate for planning because (a) the absence of a goal makes intersection turns ambiguous; (b) L2 distance penalizes valid but unobserved multi-modal options; and (c) open-loop evaluation cannot capture interactive decisions like overtake/merge that depend on consecutive ego actions. Existing planning datasets (CommonRoad: 5700 scenarios; no sensor data) do not scale to modern deep learning. Existing simulators (CARLA, AirSim) are synthetic and suffer from sim-to-real gap. nuPlan aims to fill the gap with real-world scale plus a closed-loop protocol.

## Innovation Points
- **Largest real-world planning corpus** — 1500 h across 4 cities with diverse traffic patterns (Las Vegas PUDOs, Boston double-parking, Pittsburgh left-turn precedence, Singapore left-hand traffic); ~5x larger than the next public dataset (Lyft 1118h).
- **Offline autolabeling pipeline** — non-causal multi-view fusion (PointPillars + CenterPoint + MVF++) yields near-human-quality tracks on 1500 h without online perception constraints.
- **Closed-loop simulation framework** — containerized planner submission against a hidden test set; ego is driven by a controller tracking the planned trajectory through a motion model. Two variants: *non-reactive closed-loop* (logged agents replay) and *reactive closed-loop* (all tracked agents driven by the same planner).
- **Planning-specific metric suite** — traffic-rule violation (collisions, off-road, time-to-collision), human-driving similarity (longitudinal/lateral errors, jerk match), vehicle dynamics (comfort + feasibility), goal achievement (route progress), and scenario-based metrics for tagged maneuvers.
- **Scenario mining** — automatic tagging of complex intervals (merges, lane changes, protected/unprotected turns, cyclist/pedestrian interactions, double-parked vehicles, stop-controlled intersections, construction zones) to enable targeted metrics.
- **Three task tiers** — open-loop, non-reactive closed-loop, reactive closed-loop, in increasing difficulty.

## Model Architecture
nuPlan is a dataset + benchmark, not a model. The pipeline:

- **Data collection** — 1500 h of human driving across Boston, Pittsburgh, Las Vegas, Singapore. Each log contains lidar point clouds, camera images, localization, and steering inputs. Raw sensor data released only for a subset (200+ TB total).
- **Autolabeling stack** — offline perception with PointPillars detector + CenterPoint head + MVF++ multi-view fusion + non-causal tracking; produces high-quality 3D tracks for ego and surrounding agents across the entire 1500 h.
- **Map API** — per-city semantic maps with an API for efficient queries (lane geometry, drivable area, traffic regulations).
- **Scenario tagger** — rule-based annotator marking intervals as merges, turns, interactions, etc., to support scenario-based metrics.
- **Simulation framework** — at each timestep, the planner is queried with current state and returns a planned ego position+heading; a provided controller follows the plan via a predefined motion model. Three modes: open-loop (score plan vs. log, no control), non-reactive closed-loop (controller drives ego through replayed agents), reactive closed-loop (planner controls all tracked agents too).
- **Evaluation server** — submitted planners are containerized and evaluated on a secret test split; metrics are computed and aggregated (single-metric form left to community feedback — weighted sum, threshold hierarchy, etc.).

Output of the benchmark per submission: scores on common metrics (rule, similarity, dynamics, goal) and scenario-based metrics (e.g. lane-change time-to-collision, agreement with human at unprotected turns).

## Benchmark Results
This is a benchmark-introduction paper (v4, Feb 2022). At submission time, the dataset and challenge had not yet been released, so **no baseline planner numbers are reported in the paper**. The only quantitative content is the comparative dataset table:

**Dataset comparison (Table 1):**
| Dataset    | Data   | Cities | Sensor Data | Type | Evaluation |
|------------|--------|--------|-------------|------|------------|
| Argoverse  | 320 h  | 2      | no          | Pred | OL         |
| nuPredict  | 5 h    | 2      | yes         | Pred | OL         |
| Lyft       | 1118 h | 1      | no          | Pred | OL         |
| Waymo      | 570 h  | 6      | no          | Pred | OL         |
| **nuPlan** | **1500 h** | **4** | **yes**   | **Plan** | **OL+CL** |

Baseline planner results, leaderboard scores, and per-scenario metrics: **not reported** in this paper (deferred to the 2022 challenge release).

## Limitations & Open Questions
- **No baseline numbers** — the paper introduces metrics and protocol but does not report any planner performance; empirical validation of the metric suite is left to the challenge.
- **Single-metric aggregation undecided** — authors explicitly note the headline metric (weighted sum, hierarchy of violations, etc.) is open to community feedback.
- **Sensor data only on a subset** — full 1500 h is autolabeled tracks + maps; raw sensors limited by 200+ TB scale, restricting end-to-end sensor-input planners.
- **Reactive closed-loop uses one planner for all agents** — assumes homogeneous policy; does not cover heterogeneous human behaviors.
- **No sim-to-real validation reported** — closed-loop scores on the simulator may not transfer to on-road performance; this gap is acknowledged for synthetic simulators (CARLA) but not measured for nuPlan itself.
