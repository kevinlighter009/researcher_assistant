---
paper_id: 2024-lmdrive
title: "LMDrive: Closed-Loop End-to-End Driving with Large Language Models"
authors: [Hao Shao, Yuxuan Hu, Letian Wang, Steven L. Waslander, Yu Liu, Hongsheng Li]
year: 2024
venue: CVPR 2024
arxiv_id: "2312.07488"
url: https://arxiv.org/abs/2312.07488
primary_category: vla
secondary_categories: [e2e_planning, datasets]
keywords: [llm-driving, closed-loop, instruction-following, carla, q-former, langauto, llava]
one_line_summary: First closed-loop end-to-end driving framework that consumes multi-view RGB+LiDAR and natural-language instructions through a frozen LLM to emit control signals; introduces 64K-clip dataset and LangAuto CARLA benchmark.
distilled_at: 2026-05-02
source_pdf: doc/papers/vla/lmdrive-2024.pdf
---

# LMDrive: Closed-Loop End-to-End Driving with Large Language Models

## Keywords
- llm-driving, closed-loop, instruction-following, carla, q-former, langauto, llava

## TL;DR
Prior LLM-for-driving work evaluates only open-loop and ignores cumulative error, temporal consistency, and human-in-the-loop instructions. LMDrive is the first language-guided, closed-loop end-to-end driving framework: a multi-view camera + LiDAR vision encoder produces BEV/waypoint/traffic-light visual tokens, a Q-Former compresses them, and a frozen 7B LLM (LLaVA-v1.5) consumes the tokens together with navigation and notice instructions to emit waypoints and an instruction-completion flag. On the new LangAuto CARLA benchmark, LLaVA-v1.5 backbone reaches Driving Score 36.2 / Route Completion 46.5 / Infraction Score 0.81.

## Problem & Motivation
Modular AV stacks rely on hand-crafted interfaces and struggle in long-tail urban scenarios. Existing end-to-end methods (UniAD, InterFuser, TCP, LAV) consume fixed-format inputs (sensor data, target waypoints, action commands), which restricts the agent's ability to comprehend multi-modal information or interact with humans. Earlier LLM-for-driving works (DriveGPT4, GPT-Driver, LanguageMPC, LLM-Driver) operate open-loop on textualized scenes, so they ignore cumulative error, temporal action consistency, and execution feedback, and they cannot be deployed in actual closed-loop driving. The paper claims to be the first to leverage LLMs for closed-loop end-to-end autonomous driving.

## Innovation Points
- **Closed-loop language-conditioned LLM driver** — first framework that ingests raw multi-view multi-modal sensor data plus natural-language navigation/notice instructions and outputs control signals inside a closed-loop simulator.
- **Multi-view multi-modality vision encoder with three token types** — a ResNet+PointPillars+BEV-decoder produces H x W BEV tokens, N waypoint tokens, and 1 traffic-light token; pre-trained on object detection, future waypoint prediction, and traffic-light classification, then frozen for LLM use.
- **Q-Former visual-token compression** — BLIP-2-style Q-Former with M=4 learnable queries cuts ~406 visual tokens per frame down to M tokens, making sequence-level history feasible inside the LLM context.
- **Notice-instruction channel** — an optional second instruction stream (e.g. "watch for walkers up front") lets passengers/side-assistance systems inject real-time advisories during adversarial events; misleading-instruction labels train the model to reject unsafe commands after ~1 s.
- **64K language-driving dataset and LangAuto benchmark** — public CARLA dataset of ~64K instruction-following clips (3M raw frames) with diversified ChatGPT-rewritten instructions, plus LangAuto benchmark with three tracks (LangAuto / LangAuto-Notice / LangAuto-Sequential) and length sub-tracks (Short, Tiny).

## Model Architecture
- **Inputs:** 4 RGB cameras (left, front, rear, right at 60 deg side angle) + a center-cropped focus-view front image + 1 LiDAR (64 channels, 600K pts/s); per-frame at ~10 Hz; sequence length T_max for cumulative-error control.
- **Vision encoder (frozen after pre-training):**
  - 2D backbone: ResNet-50 (ImageNet-pretrained) per view; features flattened to 1D tokens, fused by K_enc-layer Transformer encoder (multi-head self-attn + MLP + LayerNorm).
  - 3D backbone: PointPillars (trained from scratch) over a 0.25 m x 0.25 m pillar grid, aggregated by PointNet to a C x H x W BEV feature map (C=256, H=W=50).
  - BEV decoder: K_dec-layer Transformer where H x W BEV queries cross-attend to image+LiDAR tokens, producing BEV tokens; N=5 learnable waypoint queries and 1 traffic-light query are decoded similarly.
  - Pre-training heads (discarded later): one-stage CenterPoint detection, GRU waypoint regression (l1 loss), 2-layer MLP traffic-light classifier (cross-entropy).
- **LLM stack:**
  - Tokenizer: LLaMA tokenizer for navigation and optional notice instructions.
  - Q-Former: BLIP-2-style with M=4 learnable queries per frame; cross-attends to (BEV + waypoint + traffic-light) tokens to produce M visual tokens per frame.
  - Adapter: 2-layer MLP aligning visual tokens to LLM token dim.
  - LLM backbone (frozen): 7B parameters; default LLaVA-v1.5; alternatives tested: LLaMA, LLaMA2, Vicuna, Vicuna-v1.5.
- **Outputs (per latest frame, predicted every frame at training time):**
  - Action MLP: 2-layer MLP head emitting N=5 future waypoints.
  - Completion flag MLP: 2-layer MLP indicating whether the current instruction is finished.
  - Two PID controllers (LBC-style) convert waypoints into steering / throttle / brake.
- **Training losses:** l1 waypoint loss + cross-entropy completion-flag loss; only Q-Former and adapters are trained in the instruction-finetuning stage. Frames sampled at fixed interval 2 with random temporal augmentation; 75% of clips randomly drop notice instructions to avoid over-conservative behaviour.
- **Data scale:** vision encoder pre-train on ~3M frames; instruction-finetune on 64K parsed clips / 464K total frames; environments cover 8 CARLA towns, 2.5K routes, 7 weather conditions x 3 daylight conditions.

## Benchmark Results
**LangAuto CARLA benchmark (closed-loop, 3 evaluation runs, mean +/- std):**

| LLM Backbone | DS up | RC up | IS up |
|---|---|---|---|
| Random Init. | 10.7 +/- 3.8 | 16.2 +/- 4.9 | 0.63 +/- 0.04 |
| LLaMA | 31.3 +/- 1.5 | 37.1 +/- 1.6 | 0.82 +/- 0.01 |
| LLaMA2 | 32.8 +/- 2.1 | 40.1 +/- 2.2 | 0.81 +/- 0.02 |
| Vicuna | 33.5 +/- 1.9 | 39.3 +/- 1.9 | 0.83 +/- 0.02 |
| Vicuna-v1.5 | 34.0 +/- 3.8 | 39.0 +/- 3.3 | 0.85 +/- 0.06 |
| **LLaVA-v1.5** | **36.2 +/- 2.3** | **46.5 +/- 4.3** | 0.81 +/- 0.03 |

Headline: LLaVA-v1.5 backbone is best (DS 36.2, RC 46.5); on the easier LangAuto-Tiny track it reaches DS 66.5 / RC 77.9. Multi-modal-pretrained LLMs beat text-only LLMs (LLaVA-v1.5 > Vicuna-v1.5 ~ Vicuna > LLaMA), and instruction-tuned LLMs beat base LLMs.

**Module-design ablations (Table 3):**
- w/o Q-Former (direct 4 x 4 BEV downsample): DS 31.7 (vs 36.2).
- w/o BEV tokens (waypoint + traffic-light tokens only): IS drops 0.81 to 0.72.
- w/o visual pre-training (encoder trained from scratch in the finetuning stage): DS collapses to 16.9.

**LangAuto-Notice (notice instructions added during adversarial events):** with LLaVA-v1.5, infraction score rises 0.81 to 0.87, and per-km vehicle / pedestrian / layout collisions and red-light violations all decrease vs the no-notice setting.

**LangAuto-Sequential (2-3 consecutive instructions merged):** small DS / RC drop (LLaVA-v1.5 36.2 to 34.0 DS; 46.5 to 43.7 RC), reflecting added difficulty of tracking instruction completion over time.

Metrics follow CARLA LeaderBoard: Driving Score (DS) = Route Completion x Infraction Score; primary ranking metric.

## Limitations & Open Questions
- Absolute closed-loop scores remain low (DS 36.2 on full LangAuto), so the system is far from deployable; the paper does not benchmark against non-LLM closed-loop baselines (UniAD, InterFuser, TCP) on LangAuto.
- Evaluation is CARLA-only; no real-world deployment, no inference-cost / latency analysis for the 7B LLM (T_max sequence length and per-frame token budget critical for real-time control).
- Q-Former compresses each frame to only M=4 tokens — a strong information bottleneck whose impact on long-horizon reasoning is not analyzed beyond a single value.
- Misleading-instruction handling is supervised by a binary "completed" flip after ~1 s; richer rationales for instruction rejection (and behaviour during the 1 s lag) are not evaluated.
- Notice-instruction vocabulary is limited to 56 templated instructions (with ChatGPT paraphrasing); open-vocabulary advisories from arbitrary passengers are untested.
