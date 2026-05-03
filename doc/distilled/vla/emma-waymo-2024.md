---
paper_id: 2024-emma
title: "EMMA: End-to-End Multimodal Model for Autonomous Driving"
authors: [Jyh-Jing Hwang, et al.]
year: 2024
venue: TMLR 2025
arxiv_id: "2410.23262"
url: https://arxiv.org/abs/2410.23262
primary_category: vla
secondary_categories: [e2e_planning, perception]
keywords: [vla, mllm, gemini, chain-of-thought, generalist, nuscenes, womd, wod]
one_line_summary: Gemini-based MLLM that recasts driving (planning, 3D detection, road graph, scene QA) as VQA over surround camera video; generalist co-training beats single-task specialists on nuScenes/WOMD/WOD.
distilled_at: 2026-05-02
source_pdf: doc/papers/vla/emma-waymo-2024.pdf
---

# EMMA: End-to-End Multimodal Model for Autonomous Driving

## Keywords
- vla, mllm, gemini, chain-of-thought, generalist, nuscenes, womd, wod

## TL;DR
Conventional autonomous-driving stacks split perception, prediction, and planning across modules with hand-defined interfaces, and existing VLM-augmented systems still treat the LLM as a side-car. The authors fine-tune Gemini directly as the driving policy: surround-view camera video and all non-sensor inputs/outputs (intent, ego state, waypoints, 3D boxes, road graphs) are encoded as text in a unified VQA formulation. EMMA reaches state-of-the-art on the nuScenes planning benchmark, competitive results on WOMD planning and WOD camera-primary 3D detection, and gains additional 1.4–5.5% by co-training planning, detection, and road-graph tasks in one generalist model.

## Problem & Motivation
Modular AD stacks suffer from limited inter-module communication and pre-defined interfaces that struggle in novel environments. Existing end-to-end systems (UniAD, VAD) are trained on narrow datasets and do not exploit the world knowledge that lives in pre-trained MLLMs. Concurrent VLM-augmented driving systems (DriveVLM, DriveGPT4, LMDrive) typically bolt an LLM onto a conventional pipeline rather than making the MLLM a "first-class citizen" of the driving system. EMMA's premise: a single MLLM, fine-tuned end-to-end, can serve as the driving policy and as a generalist that absorbs perception, road-graph, and scene-understanding tasks without specialized heads.

## Innovation Points
- **MLLM as first-class driving policy** — Gemini (Nano-1) directly maps raw surround camera video + text inputs to driving outputs, with no specialized perception/planning modules and no HD map.
- **Plain-text representation of 3D quantities** — waypoint (x,y), 3D boxes (x,y,z,l,w,h,θ,cls), and road-graph polylines are written as floating-point text so all tasks share Gemini's pre-trained language space (vs. RT-2-style discretized tokens).
- **Hierarchical chain-of-thought driving rationale** — model emits R1 scene description, R2 critical objects with 3D coords, R3 behavior description, and R4 meta-decision (12 categories) before predicting waypoints; +6.7% planning quality on internal benchmark.
- **Generalist co-training** — single model jointly trained on planning + 3D detection + road-graph estimation outperforms each single-task specialist by up to 5.5%; auto-labeled rationale captions from off-the-shelf experts keep the pipeline scalable.
- **Self-supervised, camera-only, HD-map-free planner** — the only required label is the future ego trajectory; no perception labels, no LiDAR/radar, no HD map.
- **Road-graph-as-text design choices** — dynamic-density polyline sampling, ego-origin alignment, padded targets with random shuffling, and language-like punctuation each contribute measurably (up to 70–90% lane-level metric swing for sampling).

## Model Architecture
- Inputs:
  - V: surround-view camera video, up to 4 frames history.
  - T_intent: high-level router command (e.g., "go straight", "turn left") as text.
  - T_ego: historical ego waypoints in BEV (x,y) as plain text; can include velocity/acceleration.
  - Task prompt T_task selects which output to emit (planning, detect 3D, estimate road graph, temporary blockage QA, etc.).
- Backbone: Gemini 1.0 Nano-1 (main experiments); also validated on PaLI-X (denoted EMMA†).
- Formulation: O = G(T, V) — autoregressive next-token decoding; for planning O_trajectory = G(T_intent, T_ego, V); with CoT, (O_rationale, O_trajectory) = G(T_intent, T_ego, V).
- Outputs (all text):
  - Planner waypoints {(x_t, y_t)} for T_f future timestamps in BEV.
  - 3D boxes {(x,y,z,l,w,h,θ,cls)} sorted by depth.
  - Road graph polylines `"(x1,y1 and ... and xn,yn);..."` with `valid`/`invalid` markers and dynamic point density per polyline curvature.
  - Driving rationale text (R1 scene description, R2 critical objects with 3D coords, R3 behavior description, R4 meta-decision from 12-category vocabulary).
  - Scene-understanding answers (e.g., "is the road ahead temporarily blocked?").
- Inference trick: top-K sampling (K=24) on WOMD then median-distance trajectory selection; ADE@5s drops 0.724 → 0.610 with 24 samples.
- Training data scales (Table 1): nuScenes 18,686 examples; WOMD 487,061; WOD 158,081; internal motion-planning 24.37M (≈355× WOMD); internal detection 11.77M; internal road-graph 8.30M.

## Benchmark Results

**nuScenes end-to-end motion planning (L2 in m, lower better):**
| Method | self-sup? | L2 1s | L2 2s | L2 3s | Avg L2 |
|---|---|---|---|---|---|
| UniAD | no | 0.42 | 0.64 | 0.91 | 0.66 |
| DriveVLM | no | 0.18 | 0.34 | 0.68 | 0.40 |
| VAD | no | 0.17 | 0.34 | 0.60 | 0.37 |
| OmniDrive | no | 0.14 | 0.29 | 0.55 | 0.33 |
| Ego-MLP | yes | 0.15 | 0.32 | 0.59 | 0.35 |
| BEV-Planner | yes | 0.16 | 0.32 | 0.57 | 0.35 |
| EMMA (random init) | yes | 0.15 | 0.33 | 0.63 | 0.37 |
| EMMA | yes | 0.14 | 0.29 | 0.54 | 0.32 |
| **EMMA+** | yes | **0.13** | **0.27** | **0.48** | **0.29** |

EMMA+ improves average L2 by 17.1% over self-supervised SOTA (BEV-Planner) and 12.1% over the supervised OmniDrive.

**WOMD planning (internal benchmark, L2 in m at 1s/3s/5s):**
| Method | L2 1s | L2 3s | L2 5s |
|---|---|---|---|
| MotionLM* | 0.045 | 0.266 | 0.696 |
| Wayformer* | 0.046 | 0.252 | 0.628 |
| EMMA† (PaLI) | 0.034 | 0.274 | 0.797 |
| EMMA+† (PaLI) | 0.031 | 0.239 | 0.680 |
| EMMA | 0.032 | 0.248 | 0.681 |
| EMMA (w/ CoT) | 0.030 | 0.241 | 0.664 |
| EMMA+ | 0.030 | 0.225 | 0.610 |
| **EMMA+ (w/ CoT)** | **0.027** | **0.203** | **0.543** |

EMMA+ (w/ CoT) surpasses Wayformer by 13.5% at 5s.

**Chain-of-thought ablation on internal planning benchmark (relative improvement vs. baseline e2e):**
| Scene desc | Critical obj | Meta dec | Behavior desc | Improvement |
|---|---|---|---|---|
| - | check | - | - | +0.0% |
| - | - | check | - | +1.5% |
| - | check | check | - | +3.0% |
| - | check | check | check | +5.7% |
| check | check | check | check | +6.7% |

**WOD camera-primary 3D detection (LET-3D-AP, F1):**
- Vehicle: EMMA F1=0.61; EMMA+ F1=0.85; baselines BEVFormer F1-max=0.82, MV-FCOS3D++ F1-max=0.82. EMMA+ achieves 16.3% relative precision gain at same recall vs. BEVFormer.
- Pedestrian: EMMA F1=0.25; EMMA+ F1=0.62; BEVFormer F1-max=0.70; MV-FCOS3D++ F1-max=0.63. EMMA+ comparable to MV-FCOS3D++ but below BEVFormer at long range.

**Generalist co-training (relative improvement over single-task models):**
| Tasks trained jointly | e2e plan | 3D det | road graph |
|---|---|---|---|
| det + roadgraph | — | +1.6% | +2.4% |
| plan + det | +1.4% | +5.6% | — |
| plan + roadgraph | -1.4% | — | +3.5% |
| **all three** | **+1.4%** | **+5.5%** | **+2.4%** |

**Scene understanding (temporary blockage detection accuracy):** direct fine-tuning 81.5%, naive mixture 67.0%, mix + short pretraining 81.6%, mix + long pretraining 82.5% (vs. human baseline 57.9%, human + filtering 82.0%).

**Road graph ablations (Figure 6):** dynamic→fixed sampling drops lane-level precision/recall by 70–90%; ego-origin→naively aligned drops 25–60%; semantic punctuation contributes <10%.

**Latency-optimized variant** (with SARA-RT, shorter actions, no CoT) reaches 3 FPS, 67% faster than UniAD's 1.8 FPS.

## Limitations & Open Questions
- **Memory/video horizon**: limited to 4 frames, restricting long-term temporal reasoning.
- **No LiDAR/radar fusion**: pre-trained MLLMs do not natively ingest 3D sensing; integrating it would require large-scale aligned 3D-encoder pre-training.
- **Open-loop only**: no closed-loop testing; nuScenes metrics are sensitive to hyperparameters and many scenarios can be solved by trajectory extrapolation (acknowledged via citations to AD-MLP/BEV-Planner critiques).
- **Onboard inference latency**: large-MLLM cost; only a preliminary 3 FPS variant shown (vs. UniAD 1.8 FPS), full deployment-ready cost not established.
- **Verification of predictions**: no intermediate symbolic outputs to verify; rationale and trajectory are not guaranteed consistent.
- **Long-range pedestrian detection**: EMMA+ trails BEVFormer beyond 30 m, attributed to lower input image resolution.
