---
paper_id: 2024-drivelm
title: "DriveLM: Driving with Graph Visual Question Answering"
authors: [Chonghao Sima, Katrin Renz, Kashyap Chitta, Li Chen, Hanxue Zhang, Chengen Xie, Jens Beißwenger, Ping Luo, Andreas Geiger, Hongyang Li]
year: 2024
venue: ECCV 2024 (Oral)
arxiv_id: "2312.14150"
url: https://arxiv.org/abs/2312.14150
primary_category: datasets
secondary_categories: [vla, e2e_planning]
keywords: [graph-vqa, gvqa, drivelm-nuscenes, drivelm-carla, blip-2, trajectory-tokenization, pdm-lite]
one_line_summary: A graph-structured VQA task and dataset (DriveLM-nuScenes/CARLA) plus a BLIP-2 baseline (DriveLM-Agent) that chains perception/prediction/planning QAs as context for end-to-end driving with strong zero-shot sensor-config generalization.
distilled_at: 2026-05-02
source_pdf: doc/papers/vla/drivelm-2024.pdf
---

# DriveLM: Driving with Graph Visual Question Answering

## Keywords
- graph-vqa, gvqa, drivelm-nuscenes, drivelm-carla, blip-2, trajectory-tokenization, pdm-lite

## TL;DR
Existing VLM-for-driving approaches use single-round VQA, which doesn't mirror how humans chain perception → prediction → planning when driving. The authors propose Graph Visual Question Answering (GVQA), a task in which QA pairs are connected as a directed acyclic graph reflecting logical reasoning stages, and instantiate it as two datasets (DriveLM-nuScenes, DriveLM-CARLA) plus a BLIP-2-based baseline (DriveLM-Agent) that uses graph-structured prompting and a learned trajectory tokenizer. On nuScenes open-loop planning, DriveLM-Agent matches UniAD-Single (ADE 1.39 vs 4.16, Col 1.67 vs 9.31), and shows much stronger zero-shot transfer to Waymo than UniAD-Single.

## Problem & Motivation
Prior language-grounded driving work falls into two camps that both fail to mimic human reasoning:
- **Scene-level VQA** (e.g. ADAPT) describes an action with one or two reasons in a single round.
- **Single object-level VQA** explains the ego decision relative to one object via a "what-which-where-how-why" chain.
Neither captures the multi-object, multi-stage chain humans use (identify key objects → predict their actions → plan ego action). Existing driving QA datasets are also small in scale and lack logical structure between QA pairs (Table 1: nuScenes-QA, HAD, BDD-X, LingoQA, DRAMA all marked "None" or "Chain" for logic, never "Graph"). Furthermore, end-to-end driving stacks like UniAD generalize poorly to unseen sensor configurations.

## Innovation Points
- **Graph VQA (GVQA) task** — formulates driving QAs as a directed acyclic graph G=(V,E) where vertices are (q,a) pairs and edges encode logical dependencies, both at the object level (one object's prediction conditions another's planning) and at the task level (perception P1 → prediction P2 → planning P3 → behavior B → motion M).
- **DriveLM-nuScenes** — 4,871 keyframes with 91.4 QAs/frame on average (144k perception, 153k prediction, 146k planning), built via a semi-rule-based pipeline using nuScenes/OpenLane-V2 ground truth plus 5-domain-expert templates and multi-round human quality checks.
- **DriveLM-CARLA + PDM-Lite** — A new rule-based privileged expert (PDM-Lite, IDM-driven, 2-proposal cost function) that achieves 44% Driving Score on CARLA Leaderboard 2.0 (vs 2% for TransFuser++ expert), used to fully-automatically generate 1.6M QAs across 38 scenarios at 4 FPS.
- **Behavior abstraction (B = (B_sp, B_st))** — Trajectories are discretized into 5 speed bins {fast2, fast1, moderate, slow1, slow2} and 5 steering bins {left2, left1, straight, right1, right2}, providing a natural-language interface between P1-3 and continuous motion M.
- **DriveLM-Agent** — A BLIP-2-based GVQA baseline that does context-augmented prompting (parent-node QAs prepended as "Context:") plus a trajectory tokenizer that re-defines 256 BLIP-2 vocabulary tokens as waypoint-coordinate bins (RT-2 style).
- **DriveLM-Metrics** — SPICE + GPT Score for P1-3 QA evaluation; classification accuracy for behavior; ADE/FDE/collision rate for motion.

## Model Architecture
Pipeline (Fig. 3):
- Input: a single front-view scene image + question text with "Context:" prefix.
- Backbone VLM: BLIP-2 (frozen image encoder + Q-Former + frozen LLM), fine-tuned with LoRA. 3.955B total params, 12.9M trainable.
- Stage 1 — Perception/Prediction/Planning (P1-3): VLM answers each QA, with parent-node answers concatenated as context per the GVQA edges.
- Stage 2 — Behavior (B): VLM consumes all P1-3 QAs as context, emits a natural-language description of intended movement (mapped to (B_sp, B_st)).
- Stage 3 — Motion (M): Same BLIP-2 architecture with independent LoRA weights, takes image + behavior description, outputs a trajectory tokenized into 256 bins (per-coordinate quantization based on training-set statistics).
- Inference graph is a heuristic-sampled subgraph (training is on full graph).
Training: nuScenes split — 10 epochs, batch 2, 8× V100, ~7 h. CARLA — 6 epochs, 4× A100, ~6 h.

## Benchmark Results
**Open-loop planning on DriveLM-nuScenes (Table 2), evaluated on annotated keyframes:**

| Method                      | B Acc ↑ | B Speed ↑ | B Steer ↑ | M ADE ↓ | M Col ↓ |
|-----------------------------|---------|-----------|-----------|---------|---------|
| Command Mean                | -       | -         | -         | 4.57    | 5.72    |
| UniAD-Single                | -       | -         | -         | 4.16    | 9.31    |
| BLIP-RT-2                   | -       | -         | -         | 2.63    | 2.77    |
| DriveLM-Agent (None ctx)    | 61.45   | 72.20     | 84.73     | **1.39**| **1.67**|
| DriveLM-Agent (Chain ctx)   | 50.43   | 60.32     | 75.34     | 2.07    | 2.08    |
| DriveLM-Agent (Graph ctx)   | 57.49   | 69.89     | 80.63     | 1.74    | 1.89    |
| UniAD (full, video, privileged) | -   | -         | -         | 0.80    | 0.17    |

**Zero-shot transfer to Waymo (1k frames, Table 2):** UniAD-Single ADE 9.31 → DriveLM-Agent (Graph) ADE 6.17; speed accuracy rises from 43.90 (no context) to 54.29 (full graph) — chain context only reaches 41.28.

**P1-3 QA quality (Table 4, SPICE / GPT):**

| Context | BLIP-2 nuSc | DriveLM-Agent nuSc | BLIP-2 CARLA | DriveLM-Agent CARLA |
|---------|-------------|--------------------|--------------|---------------------|
| None    | 4.34 / 42.97 | 42.56 / 71.39    | 10.46 / 46.37 | 72.71 / 79.67     |
| Graph   | 7.71 / 45.21 | 49.54 / 72.51    | 10.30 / 55.04 | 75.26 / 81.78     |
| GT ctx  | 8.19 / 41.10 | 50.29 / 72.94    | 16.18 / 57.98 | 79.07 / 83.13     |

**Question-wise ablation (Table 3):** adding Prediction QAs as behavior context lifts behavior accuracy from 54.69 (perception-only, ID 1) to 58.82 (ID 4). Adding Planning QAs (ID 7-9) gives no further gain over Prediction.

**Efficiency (Table 5):** DriveLM-Agent has 3.955B params (12.9M trainable) vs UniAD-Single 131.9M (58.8M trainable); 24.2 TFLOPs vs 1.7 TFLOPs; 0.16 FPS vs 1.8 FPS — about 10× slower; LLM throughput 8.5 tokens/s.

## Limitations & Open Questions
- **Inference cost.** ~10× slower than UniAD; 8.5 tokens/s decoding limits practical deployment.
- **Sensor coverage.** Single low-resolution front-view image only; no LiDAR, no surround cameras, no temporal frames in the baseline (graph formulation supports them in principle, left to future work).
- **Open-loop only.** No closed-loop CARLA evaluation; ego status is intentionally excluded since it would inflate open-loop metrics without real-world transfer.
- **Behavior vocabulary.** 5×5 speed/steer bins are simple and hand-defined; richer behaviors (lane change, overtake) are mentioned but unused.
- **Chain context underperforms None and Graph** on motion ADE — suggests the graph structure (rather than mere multi-step reasoning) carries the benefit, but a clean explanation isn't given.
