---
paper_id: 2024-senna
title: "Senna: Bridging Large Vision-Language Models and End-to-End Autonomous Driving"
authors: [Bo Jiang, Shaoyu Chen, Bencheng Liao, Xingyu Zhang, Wei Yin, Qian Zhang, Chang Huang, Wenyu Liu, Xinggang Wang]
year: 2024
venue: arXiv
arxiv_id: "2410.22313"
url: https://arxiv.org/abs/2410.22313
primary_category: vla
secondary_categories: [e2e_planning]
keywords: [vla, lvlm, meta-action, surround-view, planning-oriented-qa, drivex, nuscenes, vadv2]
one_line_summary: Decouples driving into Senna-VLM (natural-language meta-actions from surround-view) + Senna-E2E (low-level trajectories conditioned on meta-action features), trained with planning-oriented QAs.
distilled_at: 2026-05-02
source_pdf: doc/papers/vla/senna-2024.pdf
---

# Senna: Bridging Large Vision-Language Models and End-to-End Autonomous Driving

## Keywords
- vla, lvlm, meta-action, surround-view, planning-oriented-qa, drivex, nuscenes, vadv2

## TL;DR
End-to-end driving stacks scale on data but lack commonsense, while LVLMs reason well over scenes but predict numerical trajectories poorly. Senna decouples the two: Senna-VLM (Vicuna-1.5-7B + ViT-L/14) emits high-level meta-actions in natural language from surround-view inputs, and Senna-E2E (extends VADv2) predicts the final trajectory conditioned on meta-action features. Pre-trained on the 800K-clip DriveX dataset and fine-tuned on nuScenes, Senna cuts L2 planning error by 27.12% and collision rate by 33.33% versus a no-pretraining variant, and beats DriveVLM by 29.03% L2 / 20.00% collision.

## Problem & Motivation
Two prior approaches both fall short. (1) Pure end-to-end planners (UniAD, VAD, VADv2) directly regress trajectories from sensor data; they have no commonsense and silently fail on long-tail semantic scenes (e.g., misreading traffic cones on a truck as a roadblock). (2) LVLM-based planners (DriveGPT4, DriveMLM, DriveVLM) ask the LVLM to predict numeric trajectory points or control signals, which is a poor fit because LVLMs are bad at precise mathematical computation. Existing LVLMs are also typically front-view-only and not designed for surround-view driving inputs. Senna's framing: let the LVLM do what it is good at (high-level natural-language decisions) and let the end-to-end model do what it is good at (precise, high-frequency trajectory regression).

## Innovation Points
- **Structured high-level / low-level decoupling** — Senna-VLM outputs natural-language meta-actions; Senna-E2E consumes meta-action embeddings and produces the trajectory. Avoids asking the LVLM to predict numbers.
- **Meta-action vocabulary** — Lateral {Left, Straight, Right} x Longitudinal {Accelerate, Keep, Decelerate, Stop}; derived automatically from ground-truth future trajectories, no manual annotation.
- **Surround-view multi-image encoding with view prompts** — A Driving Vision Adapter (MHSA over learnable image queries) compresses each of 6 views to a small token budget (best at 128 tokens/view); per-view text prompts (`<FRONT VIEW>:\n<image>\n`, etc.) give the LLM spatial awareness.
- **Planning-oriented QA suite** — Six auto-labelable QA types (Scene Description, Traffic Signal Detection, VRU Identification, Motion Intention Prediction, Meta-action Planning, Planning Explanation) generated via 3D detection / tracking pipelines + GPT-4o, scaling supervision without human labels.
- **Three-stage training** — (1) Mix Pre-training of the Driving Vision Adapter on single-image data, (2) Driving Fine-tuning on planning-oriented QAs (excluding meta-action), (3) Planning Fine-tuning on meta-action QAs only. Shown to beat the standard general-then-driving recipe.
- **Plug-and-play meta-action conditioning** — Meta-action features are an embedding token injected into VADv2 via attention, so the structured-decision interface is portable to other end-to-end backbones.

## Model Architecture
- Inputs: 6 surround-view images (ViT-L/14, each resized to 224x224 -> 576 raw image tokens), user instruction text, navigation command.
- Senna-VLM components:
  - Vision Encoder: ViT-L/14 from CLIP.
  - Driving Vision Adapter: MHSA over learnable image queries Q_img, with MLPs (linear+GELU); compresses each view to M_img tokens (best M_img = 128).
  - Text Encoder: tokenizes user instruction + navigation command, plus per-view prompt tokens.
  - LLM: Vicuna-1.5-7B; consumes concatenated image + text tokens; emits natural-language high-level decision.
  - Meta-action Encoder phi: maps the LLM's discrete meta-action output to a learned embedding e_act in R^D via a 1-to-1 lookup over N_act learnable embeddings.
- Senna-E2E (extends VADv2):
  - Modules: Perception (dynamic objects + local map), Motion Prediction (futures of dynamic objects), Planning (planning-token attention over scene features + e_act).
  - Output: trajectory V in R^{T x 2}, V = Phi(I, e_nav, e_act).
- Training data: DriveX (1000K clips, 3 s each; 800K train / 200K val), then fine-tune on nuScenes (1000 scenes). Ground-truth meta-actions are used as Senna-E2E input during training; predicted meta-actions are used at inference.

## Benchmark Results
**nuScenes trajectory planning (Table II):**
| Method                  | L2 1s | L2 2s | L2 3s | L2 Avg | Coll 1s | Coll 2s | Coll 3s | Coll Avg |
|-------------------------|------:|------:|------:|-------:|--------:|--------:|--------:|---------:|
| UniAD                   | 0.48  | 0.96  | 1.65  | 1.03   | 0.05    | 0.17    | 0.71    | 0.31     |
| VAD-Base*               | 0.17  | 0.34  | 0.60  | 0.37   | 0.07    | 0.10    | 0.24    | 0.14     |
| DriveVLM*               | 0.15  | 0.29  | 0.48  | 0.31   | 0.05    | 0.08    | 0.17    | 0.10     |
| **Senna\*** (w/ ego status) | **0.11** | **0.21** | **0.35** | **0.22** | **0.04** | **0.08** | **0.13** | **0.08** |
| VAD-Base                | 0.41  | 0.70  | 1.05  | 0.72   | 0.07    | 0.17    | 0.41    | 0.22     |
| Senna (no ego status)   | 0.37  | 0.54  | 0.86  | 0.59   | 0.09    | 0.12    | 0.33    | 0.18     |
| **Senna**+DriveX pre-training | 0.26 | 0.42 | 0.61 | **0.43** | 0.05 | 0.11 | 0.21 | **0.12** |

Without ego-status features and with DriveX pre-training, Senna improves L2 by 40.28% and collision by 45.45% over VAD-Base, and overall the pre-train+fine-tune pipeline cuts L2 by 27.12% and collision by 33.33% vs no-pretrain.

**DriveX trajectory planning (Table III):** Senna L2 Avg = (0.49, 1.27, 2.62) at 1/2/3 s; vs DriveVLM (0.61, 1.44, 3.00) — 14.27% L2 improvement. VADv2 with G.T. meta-action gives an upper bound (0.37, 1.08, 2.24).

**DriveX meta-action planning + scene description (Table I):** Senna Acc = 71.21% (best fine-tuned baseline LLaVA-1.5: 64.68%, +10.44% relative on planning accuracy). Deceleration F1 rises from 52.68 (LLaVA-1.5) to 61.99 (+17.67%). BLEU-4 / CIDEr / METEOR also lead.

**Key ablations:**
- Surround vs front-view (Table V): Acc 64.91 -> 71.21 with surround.
- Image-token budget (Table VI): 128 tokens/view is optimal; >=256 leads to decoding failure / model collapse.
- Training data scale (Table VII): 100K -> 800K clips: Acc 57.45 -> 71.21 (no saturation observed).
- Training pipeline (Table IX): proposed 3-stage Mix-pretrain + Driving FT + Planning FT (71.21) beats general-then-driving baselines.
- Inference latency (Table VIII): Senna-128 decode latency 0.58 s; Senna-32 = 0.35 s on RTX 4090, comparable or faster than single-image LLaVA-1.5 despite 6 input views.

## Limitations & Open Questions
- LVLM inference latency (~0.35-0.58 s decode for Senna-VLM on RTX 4090) may be too slow for real-time vehicle deployment; the authors suggest sub-2B distillation + hardware optimization as future work.
- Meta-action vocabulary is fixed/discrete (3 lateral x 4 longitudinal); finer-grained or open-vocabulary natural-language instructions for controlled trajectory planning are deferred to future work.
- Closed-loop evaluation is not reported; results are open-loop displacement / collision metrics on nuScenes and DriveX.
- DriveX dataset is internal (not publicly released as of the paper); reproducibility of pre-training scale is limited.
- Senna-E2E uses ground-truth meta-actions during training but predicted ones at inference, leaving a train/test distribution gap that is not explicitly quantified.
