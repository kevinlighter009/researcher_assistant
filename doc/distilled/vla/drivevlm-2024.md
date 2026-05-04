---
paper_id: 2024-drivevlm
title: "DriveVLM: The Convergence of Autonomous Driving and Large Vision-Language Models"
authors: [Xiaoyu Tian, Junru Gu, Bailin Li, Yicheng Liu, Yang Wang, Zhiyong Zhao, Kun Zhan, Peng Jia, Xianpeng Lang, Hang Zhao]
year: 2024
venue: CoRL 2024
arxiv_id: "2402.12289"
url: https://arxiv.org/abs/2402.12289
primary_category: vla
secondary_categories: [e2e_planning, datasets]
keywords: [vlm, chain-of-thought, dual-system, meta-action, qwen-vl, sup-ad, nuscenes, orinx-deployment]
one_line_summary: A VLM-based driving stack with CoT scene description, scene analysis, and hierarchical planning, paired with a dual-system variant (DriveVLM-Dual) that fuses 3D perception and a fast classical planner for real-time onboard deployment.
distilled_at: 2026-05-02
source_pdf: doc/papers/vla/drivevlm-2024.pdf
---

# DriveVLM: The Convergence of Autonomous Driving and Large Vision-Language Models

## Keywords
- vlm, chain-of-thought, dual-system, meta-action, qwen-vl, sup-ad, nuscenes, orinx-deployment

## TL;DR
Conventional 3D-perception + prediction + planning stacks struggle on long-tail urban scenes (construction, gestures, weird-shaped vehicles). The authors propose DriveVLM, a VLM that runs a chain-of-thought over surround images to emit scene description, scene analysis, and a hierarchical plan (meta-actions to decision description to waypoints). To address VLM latency and weak spatial reasoning, they add DriveVLM-Dual, which fuses a traditional 3D detector and a high-frequency classical planner with the slow VLM trajectory. On the nuScenes planning task DriveVLM-Dual reaches L2 0.31 m and collision 0.10% (avg over 1/2/3 s), beating UniAD and VAD; the system is also deployed on a production vehicle with two OrinX chips at 410 ms inference.

## Problem & Motivation
Existing autonomous driving stacks decompose into 3D perception, motion prediction, and planning. These components have well-known scene-understanding gaps: perception ignores rare/unusual objects and their attributes, prediction reasons only at the trajectory level, and planning largely ignores decision-level interactions between objects and the ego vehicle. As a result they fail in long-tail urban scenes (road construction, gestures from traffic police, road debris, unusual animals). Pure VLM planners, on the other hand, are weak at precise 3D spatial reasoning and far too heavy for high-frequency onboard inference. The paper aims to bring VLM-style scene reasoning into driving while still meeting real-time, real-vehicle constraints.

## Innovation Points
- **Chain-of-Thought driving pipeline** — VLM reasons in three explicit stages: scene description, scene analysis (per critical object: static attributes, motion states, particular behaviors), and hierarchical planning (meta-actions to decision description to waypoints), mirroring perception/prediction/planning but at semantic granularity.
- **Hierarchical planning vocabulary** — 17-category meta-action set, plus a structured decision description (Action, Subject, Duration), then waypoints encoded as language tokens for autoregressive generation; enables interpretable, step-wise plan generation.
- **Critical-object focus** — instead of detecting all objects, DriveVLM identifies only the few critical objects whose category and bounding box are mapped to language token_ids, letting the VLM surface long-tail objects (debris, animals) that a 3D detector misses.
- **DriveVLM-Dual** — slow/fast hybrid: matches VLM-identified critical objects with a 3D detector via IoU on back-projected 2D boxes, then a classical planner refines the slow VLM trajectory W_slow into a high-frequency W_fast = Planner([W_slow, f]); the two branches run asynchronously.
- **SUP-AD task and dataset** — formal Scene Understanding for Planning task with a data-mining + annotation protocol (long-tail mining, challenging-scenario mining, keyframe selection 0.5-1 s before maneuver, 3-annotator verification) and matching scene-description / meta-action evaluation metrics that use an LLM judge with semantically equivalent ground-truth alternatives.
- **Onboard deployment recipe** — quantized Qwen-VL on dual OrinX chips with SigLIP-L-384 + PE interpolation for high-resolution input, LDPNetv2 visual-token compression (75% reduction), short-term memory bank for video, and Eagle speculative sampling for a 2.7x decode speedup; reaches 410 ms average inference.

## Model Architecture
- Inputs: sequence of surround camera frames at times T, T-1, T-2, T-3 (resized to 448x448 for the visual encoder).
- Backbone: vision transformer encoder produces image tokens; an attention-based extractor aligns tokens with the LLM. Default model is Qwen-VL (9.6 B total: 1.9 B visual encoder + 0.08 B vision-language adapter + 7.7 B Qwen LLM).
- Stage 1 - Scene Description: outputs E = {E_weather, E_time, E_road, E_lane} plus critical objects O_c = (category c, bbox b(x1,y1,x2,y2)) mapped to language token_ids.
- Stage 2 - Scene Analysis: per critical object outputs static attributes C_s, motion states C_m, particular behaviors C_b, and influence I on the ego vehicle, then a scene-level summary S.
- Stage 3 - Hierarchical Planning: meta-actions A (sequence from a 17-category vocabulary, e.g. accelerate/decelerate/turn/lane-change/wait), decision description D = (Action A, Subject S, Duration D), then waypoints W = {w_1,...,w_n}, w_i = (x_i, y_i) at fixed interval Delta t, generated as language tokens.
- DriveVLM-Dual additions:
  - 3D perception fusion: 3D detector outputs O_3D = {c_3D^i, b_3D^i}; back-project to 2D and IoU-match to critical objects with aIoU(b_c^j, b_2D^i) > tau and same category. Matched objects get 3D centers/orientations/trajectories injected as language prompts; unmatched objects rely on language only.
  - High-frequency trajectory refinement: a classical planner consumes W_slow (low-rate VLM trajectory) plus features f to produce W_fast = Planner([W_slow, f]); for an optimization planner W_slow is the initial solution, for a learned planner it is an input query.
- Onboard stack: two OrinX chips, with the high-frequency end-to-end pipeline on OrinX-1 and DriveVLM on OrinX-2, running asynchronously; quantized to q4f16 with SigLIP-L-384 + PE interpolation, LDPNetv2 token compression, SE-blocked temporal feature fusion, Eagle speculative sampling.

## Benchmark Results

**nuScenes planning (validation):**

| Method | L2 1s | L2 2s | L2 3s | L2 Avg | Coll 1s | Coll 2s | Coll 3s | Coll Avg |
|---|---|---|---|---|---|---|---|---|
| UniAD | 0.48 | 0.96 | 1.65 | 1.03 | 0.05 | 0.17 | 0.71 | 0.31 |
| VAD-Base | 0.17 | 0.34 | 0.60 | 0.37 | 0.07 | 0.10 | 0.24 | 0.14 |
| DriveVLM | 0.18 | 0.34 | 0.68 | 0.40 | 0.10 | 0.22 | 0.45 | 0.27 |
| **DriveVLM-Dual (w/ VAD)** | **0.15** | **0.29** | **0.48** | **0.31** | **0.05** | **0.08** | **0.17** | **0.10** |

**SUP-AD test set (proposed metrics):**

| Method | Scene Description | Meta-actions |
|---|---|---|
| Fine-tuning w/ Lynx | 0.46 | 0.15 |
| Fine-tuning w/ CogVLM | 0.49 | 0.22 |
| GPT-4V (in-context) | 0.38 | 0.19 |
| **DriveVLM w/ Qwen** | **0.71** | **0.37** |

Ablations (nuScenes val, DriveVLM-Dual design choices):
- Base hierarchical planning only: L2 avg 0.49, collision avg 0.36.
- + Critical-object analysis (CO): L2 avg 0.44, collision avg 0.35.
- + 3D perception prompt (3D): L2 avg 0.40, collision avg 0.27.

Generality of dual-system (nuScenes val): replacing the classical branch shows DriveVLM-Dual lifts UniAD from L2 1.03 / coll 0.31 to 0.39 / 0.20, MLP from 0.44 / 0.20 to 0.31 / 0.13, and VAD from 0.37 / 0.14 to 0.31 / 0.10.

Onboard deployment: average inference 410 ms on OrinX (dual-chip async); Eagle speculative sampling gives 2.7x decode speedup vs Medusa's 2.17x. Detailed throughput numbers per model in Tables 5-9 of the paper (not reproduced).

## Limitations & Open Questions
- VLMs remain weak at precise 3D spatial reasoning - the dual-system workaround needs a parallel classical perception/planning stack and an extra OrinX chip, so the "VLM-only" path is not viable today.
- nuScenes evaluation is open-loop (L2 displacement and collision rate), inheriting known critiques of the protocol; no closed-loop urban benchmark is reported.
- The 17-category meta-action vocabulary is hand-designed; how well it scales to truly open-vocabulary intents is not addressed.
- SUP-AD scene-description and meta-action scores depend on an LLM judge with semantically equivalent rewrites - reproducibility and judge bias not analyzed.
- 410 ms VLM-branch latency is reported but the slow/fast asynchronous control loop, fallback behavior, and safety case under VLM staleness are not detailed.
