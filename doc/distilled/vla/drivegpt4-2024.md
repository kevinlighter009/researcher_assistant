---
paper_id: 2024-drivegpt4
title: "DriveGPT4: Interpretable End-to-end Autonomous Driving via Large Language Model"
authors: [Zhenhua Xu, Yujia Zhang, Enze Xie, et al.]
year: 2024
venue: IEEE RA-L 2024
arxiv_id: "2310.01412"
url: https://arxiv.org/abs/2310.01412
primary_category: vla
secondary_categories: [e2e_planning]
keywords: [vla, mllm, llama2, video-tokenizer, control-signal-prediction, instruction-tuning, bdd-x]
one_line_summary: An LLaMA2-based multimodal LLM that ingests front-camera video and text queries to jointly produce vehicle action descriptions, justifications and next-step low-level control (speed, turning angle) on BDD-X.
distilled_at: 2026-05-02
source_pdf: doc/papers/vla/drivegpt4-2024.pdf
---

# DriveGPT4: Interpretable End-to-end Autonomous Driving via Large Language Model

## Keywords
- vla, mllm, llama2, video-tokenizer, control-signal-prediction, instruction-tuning, bdd-x

## TL;DR
End-to-end driving stacks predict controls but cannot explain them, and prior caption networks (e.g. ADAPT) only emit fixed action/justification labels. DriveGPT4 is an LLaMA2-based multimodal LLM that ingests an 8-frame front-camera video plus free-form text queries, then jointly produces (a) natural-language answers about the ego vehicle's action and reasoning and (b) the next-step low-level control signal (speed, turning angle) using a shared text de-tokenizer. Trained with 56K BDD-X-derived video QAs (16K BDD-X + 40K ChatGPT-generated) mixed with 223K LLaVA/Valley general instruction data, it beats ADAPT on BDD-X across CIDEr/BLEU4/ROUGE and cuts speed RMSE from 3.02 to 1.30 m/s.

## Problem & Motivation
Conventional end-to-end driving systems (e.g. CNN policies on monocular images) are black boxes — they output paths or controls with no human-interpretable rationale, hindering trust and commercialization. Earlier "interpretable driving" attempts either (i) visualize attention maps that lay users cannot read, or (ii) train small caption networks like ADAPT that produce vehicle-action descriptions but are limited to fixed prompts and rigid label formats; small LMs lack the capacity for free-form Q&A. Existing multimodal LLMs (MiniGPT-4, Video-LLaMA, Valley) can understand video but have no autonomous-driving domain knowledge and cannot output low-level controls. DriveGPT4 is positioned as the first MLLM that simultaneously grounds free-form QA and predicts numeric control signals for driving.

## Innovation Points
- **Unified text+control tokenization (RT-2-style)** — speed and turning angle are embedded as plain text tokens decoded by the same LLaMA tokenizer, so a single LLM head produces both linguistic answers and numerical control without a separate regression head.
- **BDD-X visual instruction-tuning dataset** — ChatGPT is given privileged info (BDD-X captions, control sequences, YOLOv8 boxes) and prompted LLaVA-style to generate 40K extra video QAs about traffic lights, lane changes, surrounding objects, on top of the 16K reformulated BDD-X QAs (Q_a/Q_j/Q_c).
- **Two-stage mix-finetune training** — Stage 1 freezes CLIP+LLM and trains only the projector on 593K CC3M images + 703K WebVid-2M videos; Stage 2 jointly fine-tunes projector+LLM on the 56K driving QAs mixed with 223K general LLaVA/Valley instruction data to retain general visual QA ability and curb hallucination.
- **Valley-based video tokenizer** — per-frame CLIP features are split into a global token (channel 0) and 256 patch tokens; temporal feature T concatenates per-frame globals while spatial feature S pools all patch tokens, giving a compact representation of an 8-frame clip.
- **Zero-shot transfer demonstrated** — qualitative QA generalization shown on nuScenes clips and even video-game footage without retraining.

## Model Architecture
- Input: front-view monocular video V = [I_1, ..., I_N] uniformly sampled to 8 frames + textual user query.
- Visual encoder: frozen CLIP (ViT). Per-frame feature F_i is 257x4096; channel 0 is the global token F_i^G, the remaining 256 channels are patch tokens F_i^P.
- Video tokenizer (Valley-style): temporal feature T = concat(F_0^G, ..., F_N^G); spatial feature S = Pooling(F_0^P, ..., F_N^P). Both are projected to LLM token space by a learned projector.
- LLM: LLaMA2 (size not stated). Stage 1 frozen, Stage 2 trained. Receives concatenated video tokens and tokenized text (including current ego speed and clip duration in the prompt).
- Output head: standard LLaMA tokenizer/de-tokenizer reused for both natural-language answers and control signals; predicted control is (v_{N+1}, Delta_{N+1}) = (next-step speed, relative turning angle), embedded in output text in a fixed extractable format.
- Training data: Stage 1 — 593K CC3M images + 703K WebVid-2M videos (alignment). Stage 2 — 16K BDD-X QAs + 40K ChatGPT QAs + 223K LLaVA/Valley general instruction data (mix-finetune).
- Total params, exact LLaMA2 size, and inference latency: not reported.

## Benchmark Results
Evaluation is on the BDD-X test set (filtered for consistent control/text), split into Easy / Medium / Hard / All by scene difficulty (1202 / 295 / 312 clips). All methods use 8-frame video.

**BDD-X full-text generation (description + justification combined), all splits:**
| Method      | CIDEr | BLEU4 | ROUGE |
|-------------|-------|-------|-------|
| ADAPT       | 85.38 | 17.40 | 43.04 |
| Video-LLaMA | 8.90  | 1.52  | 10.86 |
| Valley      | 20.91 | 4.75  | 14.54 |
| DriveGPT4   | 99.10 | 18.32 | 44.73 |

**BDD-X separate description / justification (whole test set):**
| Metric                      | ADAPT  | DriveGPT4 |
|-----------------------------|--------|-----------|
| Description CIDEr           | 227.93 | 256.03    |
| Description BLEU4           | 32.99  | 35.41     |
| Description ROUGE           | 61.82  | 63.77     |
| Justification CIDEr         | 80.00  | 98.71     |
| Justification BLEU4         | 9.25   | 10.02     |
| Justification ROUGE         | 30.79  | 31.52     |

**Open-loop control prediction on BDD-X (whole test set):**
| Metric                  | ADAPT | DriveGPT4 |
|-------------------------|-------|-----------|
| Speed RMSE (m/s) ↓      | 3.02  | **1.30**  |
| Speed A_0.1 ↑           | 9.56  | 30.09     |
| Speed A_1.0 ↑           | 37.07 | 79.92     |
| Turning RMSE (deg) ↓    | 11.98 | **8.98**  |
| Turning A_0.1 ↑         | 27.93 | 59.23     |
| Turning A_1.0 ↑         | 75.13 | 79.59     |

**Additional ChatGPT-generated open QA (CIDEr / BLEU4 / ROUGE / ChatGPT-score):** DriveGPT4 56.34 / 22.94 / 31.70 / 81.62; Valley 11.37 / 5.01 / 11.09 / 43.23; ADAPT cannot answer these.

**Ablations (Tab. VIII) — full configuration is BQ + CQ + MF (BDD-X QAs + ChatGPT QAs + Mix-finetune):**
- Removing ChatGPT QAs: BDD-X CIDEr 95.75 (vs 99.10), Speed RMSE 1.69 (vs 1.30) — extra QAs help both QA and control.
- Removing BDD-X QAs: BDD-X CIDEr collapses to 10.40 — domain QAs are essential for driving description.
- Removing Mix-finetune (no general instruction data): BDD-X CIDEr 76.51, Speed RMSE 4.67 — general data is critical for both QA quality and control accuracy.

Qualitative comparison vs GPT-4V: GPT-4V cannot output numerical controls and mishandles dynamic actions like turning/accelerating.

## Limitations & Open Questions
- 8-frame input cap (vs ADAPT's 32-frame) chosen for memory/inference reasons; longer temporal context may further help — explicitly flagged by the authors as a limitation.
- Evaluation is open-loop on BDD-X only; no closed-loop / simulator test, no nuScenes planning numbers (only qualitative zero-shot examples).
- Domain data (56K driving QAs) is acknowledged as still insufficient — hallucination (non-existent vehicles / lights) noted, and authors plan to extend with CARLA-generated tuning data.
- Exact LLaMA2 size, parameter count, and inference latency are not reported.
- Predicts only next-step (speed, turning angle), not a multi-second trajectory or vehicle-level control commands needed for deployment.
