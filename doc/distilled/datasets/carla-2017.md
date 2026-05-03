---
paper_id: 2017-carla
title: "CARLA: An Open Urban Driving Simulator"
authors: [Alexey Dosovitskiy, German Ros, Felipe Codevilla, Antonio Lopez, Vladlen Koltun]
year: 2017
venue: CoRL 2017
arxiv_id: "1711.03938"
url: https://arxiv.org/abs/1711.03938
primary_category: datasets
secondary_categories: [e2e_planning]
keywords: [carla, simulator, urban-driving, unreal-engine, imitation-learning, reinforcement-learning, modular-pipeline, benchmark]
one_line_summary: Open-source Unreal-Engine-based urban driving simulator with server-client API, configurable sensors and weather, plus baselines (modular pipeline, IL, RL) on a goal-directed navigation benchmark.
distilled_at: 2026-05-02
source_pdf: doc/papers/datasets/carla-2017.pdf
---

# CARLA: An Open Urban Driving Simulator

## Keywords
- carla, simulator, urban-driving, unreal-engine, imitation-learning, reinforcement-learning, modular-pipeline, benchmark

## TL;DR
Autonomous-driving research in the physical world is bottlenecked by infrastructure cost and the inability to safely stage rare events, while existing simulators (TORCS, GTA V) lack urban complexity, sensor flexibility, or open access. The authors release CARLA, an open-source urban driving simulator built on Unreal Engine 4 with a Python server-client API, configurable RGB / depth / semantic-segmentation sensors, two hand-crafted towns, and 18 weather/illumination combinations. They benchmark a modular pipeline, conditional imitation learning, and A3C reinforcement learning on a goal-directed navigation suite of four increasing-difficulty tasks across training and unseen towns/weather.

## Problem & Motivation
Training and validating urban driving in the physical world is prohibitively expensive (instrumented cars, manpower, safety) and cannot cover the long tail of corner cases. Existing simulation alternatives are inadequate: open racing simulators such as TORCS lack pedestrians, intersections, traffic rules, and other urban complications; commercial games such as Grand Theft Auto V are closed-source, give little control over the environment, have severely limited sensor specification, and provide no detailed feedback on rule violations. There is no open platform that combines high-fidelity urban content, flexible sensor suites, scenario scripting, and rich metrics for benchmarking driving policies.

## Innovation Points
- **Open urban driving platform** — Unreal Engine 4 layer plus freely reusable digital assets (urban layouts, buildings, vehicles, pedestrians) created from scratch by a dedicated artist team.
- **Server-client architecture** — Python client API sends per-step commands (steer/throttle/brake) and meta-commands (reset, change weather, modify sensor suite); decouples the agent from rendering/physics.
- **Configurable sensor suite** — RGB cameras with arbitrary 3D pose / FOV / depth-of-field, plus pseudo-sensors for ground-truth depth and 12-class semantic segmentation; meant to control for the role of perception in policy evaluation.
- **Rich measurements & infractions** — exposes GPS-like pose, speed, acceleration, collision impulses, fraction of footprint on wrong-way lanes / sidewalks, traffic-light state, and bounding boxes of all dynamic objects.
- **Three reference baselines** — released alongside CARLA: a classic modular pipeline, a conditional imitation-learning network, and an A3C reinforcement-learning agent, providing the first apples-to-apples comparison of these paradigms in urban driving.
- **Goal-directed navigation benchmark** — four tasks of increasing difficulty (Straight, One-turn, Navigation, Navigation w/ dynamic obstacles) evaluated under four cross-conditions (training, new town, new weather, new town & new weather).

## Model Architecture
Simulator architecture:
- Engine layer: Unreal Engine 4 providing rendering, PhysX-based vehicle dynamics, basic NPC logic.
- Server: runs the simulation, renders the scene, and arbitrates the world state.
- Client (Python): communicates over sockets; sends control commands and meta-commands, receives sensor readings and measurements.
- Environment content: 3D models of static (buildings, vegetation, signs) and dynamic (vehicles, pedestrians) objects; library at writing time has 40 buildings, 16 vehicle models, 50 pedestrian models. Two towns are shipped: Town 1 (2.9 km of drivable roads, training) and Town 2 (1.4 km, testing).
- NPCs: vehicles use PhysXVehicles + a basic controller (lane following, traffic lights, speed limits, intersection decisions); pedestrians follow a town-specific cost map that prefers sidewalks/crossings, with random outfits/props for visual diversity.
- Weather/illumination: 2 lighting conditions (midday, sunset) x 9 weather presets (cloud cover, precipitation, puddles) = 18 combinations.
- Sensors: RGB cameras (configurable position, orientation, FOV, depth of field) and pseudo-sensors for ground-truth depth and 12-class semantic segmentation (road, lane-marking, traffic sign, sidewalk, fence, pole, wall, building, vegetation, vehicle, pedestrian, other).
- Measurements: vehicle pose (world frame), speed, acceleration, accumulated collision impulse, sidewalk/wrong-lane footprint percentage, traffic-light & speed-limit state, exact poses and bounding boxes of all dynamic objects.

Baseline driving stacks (all consume an A*-based topological planner that emits high-level commands left/right/straight/follow-lane; no metric maps):
- Modular pipeline (MP): perception (RefineNet semantic segmentation trained on 2,500 CARLA-labelled images, plus an AlexNet binary intersection classifier trained on 500 images) -> rule-based local planner state machine (road-following, left-turn, right-turn, intersection-forward, hazard-stop) emitting waypoints -> PID continuous controller targeting 20 km/h.
- Conditional imitation learning (IL): forward-facing camera + high-level command -> deep network predicts steering/throttle/brake; trained on ~14 hours of human driving with noise injection, data augmentation, dropout, Adam optimizer.
- Reinforcement learning (RL): A3C asynchronous actor-critic with 10 parallel actor threads, trained for 10 million simulation steps (~12 days of non-stop driving at 10 fps); reward is a weighted sum of speed and goal-progress (positive) and collision damage, sidewalk overlap, opposite-lane overlap (negative).

## Benchmark Results
Headline benchmark: percentage of successfully completed goal-directed navigation episodes (25 episodes per cell), four tasks x four conditions, three methods. Numbers reproduced from Table 1 of the paper.

**Success rate (%) — higher is better:**
| Task              | Train MP | Train IL | Train RL | New town MP | New town IL | New town RL | New weather MP | New weather IL | New weather RL | New town & weather MP | New town & weather IL | New town & weather RL |
|-------------------|----------|----------|----------|-------------|-------------|-------------|----------------|----------------|----------------|-----------------------|-----------------------|-----------------------|
| Straight          | 98       | 95       | 89       | 92          | 97          | 74          | 100            | 98             | 86             | 50                    | 80                    | 68                    |
| One turn          | 82       | 89       | 34       | 61          | 59          | 12          | 95             | 90             | 16             | 50                    | 48                    | 20                    |
| Navigation        | 80       | 86       | 14       | 24          | 40          | 3           | 94             | 84             | 2              | 47                    | 44                    | 6                     |
| Nav. dynamic      | 77       | 83       | 7        | 24          | 38          | 2           | 89             | 82             | 2              | 44                    | 42                    | 4                     |

Key findings:
- No method is perfect even on the simplest "Straight" task in training conditions, due to weather-induced sensory variability the policies fail to generalize over.
- MP and IL are roughly on par across most cells (typically <10% apart); RL substantially underperforms despite training on ~12 days of driving vs. ~14 hours for IL.
- Generalization to new weather is largely retained for MP and IL; generalization to a new town drops performance on the two hardest tasks by at least 2x.
- MP is "bimodal": when the perception stack works the whole system works, otherwise it fails completely; in "New weather" MP can beat IL because perception happens to transfer well.

Infractions (Table 2): average kilometers driven between infractions of five types (opposite lane, sidewalk, static collision, vehicle collision, pedestrian collision). MP generally has the longest mean distance for static and vehicle collisions; IL strays onto the opposite lane and sidewalk least; RL collides with pedestrians least often (attributed to the large negative reward) but is worst on opposite-lane and sidewalk metrics. Full numbers in paper Table 2.

## Limitations & Open Questions
- Sensor suite is limited to RGB cameras and pseudo-sensors (depth, semantic segmentation); no LiDAR, radar, or IMU at time of writing.
- Only two hand-crafted towns and a small asset library (40 buildings, 16 vehicle models, 50 pedestrian models); generalization claims are bounded by this limited diversity.
- Baselines deliberately ignore speed limits and traffic lights in the benchmark — a simplification that side-steps a core part of urban driving.
- RL underperforms badly; the authors attribute this to known A3C brittleness, infeasibility of large hyperparameter sweeps in a realistic simulator, and the absence of regularization (no augmentation/dropout). Whether RL can match IL/MP with more compute or better algorithms is left open.
- End-to-end approaches remain susceptible to rare events (e.g., avoiding a pedestrian); the authors note that further algorithmic and architectural advances — not just more simulation data — are likely needed.
