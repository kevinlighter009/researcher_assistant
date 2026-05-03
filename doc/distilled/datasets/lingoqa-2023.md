---
paper_id: 2023-lingoqa
title: "LingoQA: Visual Question Answering for Autonomous Driving"
authors: [Ana-Maria Marcu, Long Chen, Jan Hünermann, Alice Karnsund, Benoit Hanotte, et al.]
year: 2023
venue: ECCV 2024
arxiv_id: "2312.14115"
url: https://arxiv.org/abs/2312.14115
primary_category: datasets
secondary_categories: [vla]
keywords: [video-vqa, lingo-judge, vicuna-7b, q-former, late-fusion, wayve, free-form-qa, action-justification]
one_line_summary: A 419.9K free-form video-QA benchmark for autonomous driving with a learned Lingo-Judge metric (0.95 Spearman vs human) and a CLIP+Q-Former+Vicuna-7B baseline.
distilled_at: 2026-05-02
source_pdf: doc/papers/datasets/lingoqa-2023.pdf
---

# LingoQA: Visual Question Answering for Autonomous Driving

## Keywords
- video-vqa, lingo-judge, vicuna-7b, q-former, late-fusion, wayve, free-form-qa, action-justification

## TL;DR
Existing autonomous-driving VQA datasets are small, single-word, and lack reasoning; existing text metrics (BLEU/METEOR/CIDEr) correlate weakly with human judgements. The authors release LingoQA — 28K 4-second video scenarios with 419.9K free-form QA pairs covering driving behaviour, scenery and reasoning — together with Lingo-Judge, a learned DeBERTa-V3 classifier that achieves 0.95 Spearman correlation with humans (vs. 0.853 for CIDEr, 0.932 for GPT-4-CoT). A baseline VLM (CLIP + Q-Former + Vicuna-1.5-7B with late video fusion over 5 frames) reaches 60.8% Lingo-Judge accuracy versus 96.6% for humans, and 59.6% for the strongest zero-shot model GPT-4V.

## Problem & Motivation
Driving stacks rely on opaque deep nets, but trust hinges on the system being able to *explain* its reasoning. Prior driving QA datasets either (a) are too small (Rank2Tell 118 scenarios, BDD-X 6.9K) or (b) only contain short single-word answers grounded in object detection (NuScenesQA averages 1.0 word/answer, no causal reasoning). Existing automated metrics (BLEU, METEOR, ROUGE, CIDEr) are n-gram-based and align poorly with human ratings; GPT-4-as-judge correlates well but takes 13–50 min per evaluation run, making it impractical for development. The authors target the joint gap: a free-form video-QA benchmark for driving plus a fast metric that mirrors human judgement.

## Innovation Points
- **LingoQA dataset** — 28K 4-second front-camera video scenarios with 419.9K QA pairs, ~10x larger than BDD-X, with average 17.2-word free-form answers covering 9 competencies (action, justification, attention, identification, localisation, description, counting, anticipation, counterfactuals).
- **Two-part training corpus** — *Action* (24.5K scenarios, 267.8K pairs from operator-labelled driving events rephrased by GPT-3.5) and *Scenery* (3.5K scenarios, 152.5K pairs from densely ELAN-annotated 30-min sessions, GPT-4-CoT generated).
- **Lingo-Judge metric** — DeBERTa-V3 LoRA-fine-tuned binary classifier scoring `(prediction, ground_truth)` pairs, with `S = max_j F(pred, gt[j])` over the two annotated answers; 0.950 Spearman / 0.993 Pearson with human ratings, 95% held-out accuracy, 10.5 s per full eval (vs 3016 s for GPT-4-CoT).
- **Curated 1000-answer eval set** — 500 questions × 2 diverse correct answers each, 100 scenarios, hand-checked through multiple relabelling rounds.
- **LingoQA Baseline VLM** — CLIP-ViT + Q-Former + Vicuna-1.5-7B with two-stage training (GQA+SVIT alignment then LingoQA fine-tune) and late video fusion of 5 frames; serves as the reference open-source baseline.

## Model Architecture
- Input: front-camera video snippet, T = 5 frames over 4 s at ~1 Hz, plus question and chat history (text).
- Vision encoder: CLIP ViT (OpenCLIP weights) on each frame, images squashed to 224×224 to keep full context.
- Q-Former (BLIP-2 init) per frame translates vision features into LLM token space; a linear projection lifts to LLM embedding dim. Tokens from all 5 frames are concatenated → late fusion.
- LLM: Vicuna v1.5 7B (Llama-2 base), autoregressive next-token prediction; loss masked over question/history tokens.
- Output: free-form text answer.
- Training: Stage 1 pre-train QKV self-attention of LLM + vision encoder + full Q-Former + projection on GQA (22M Q over 113K img) and SVIT (4.2M QA over 108.1K img). Stage 2 fine-tune same params with vision encoder frozen on LingoQA Action+Scenery.

## Benchmark Results
**Headline (LingoQA evaluation set, 1000 answers / 500 questions):**
| Method                     | Frames | Lingo-Judge ↑ | BLEU ↑ | METEOR ↑ | CIDEr ↑ |
|----------------------------|:------:|:-------------:|:------:|:--------:|:-------:|
| Human                      | 5      | 96.6          | 81.04  | 52.92    | 361.77  |
| Human (single frame)       | 1      | 81.8          | 10.64  | 15.01    | 64.45   |
| GPT-4V (zero-shot)         | 5      | 59.6          | 6.30   | 12.35    | 42.82   |
| **LingoQA Baseline**       | 5      | **60.8**      | 15.00  | 18.56    | 65.61   |
| LingoQA Baseline (1 frame) | 1      | 57.0          | 14.21  | 18.40    | 59.46   |
| LLaVA fine-tuned           | 1      | 59.0          | 12.5   | 18.5     | 57.0    |
| BLIP-2 fine-tuned          | 1      | 52.2          | 13.0   | 17.4     | 60.1    |
| Vicuna-7B (text-only)      | 0      | 38.8          | 10.1   | 15.2     | 51.0    |

**Lingo-Judge metric correlation with humans (Table 1):** Pearson 0.993 / Spearman 0.950 / 95.0% val accuracy / 10.5 s; vs. GPT-4-CoT 0.990 / 0.932 / 91.2% / 3016 s; CIDEr 0.878 / 0.853.

**Key ablations (Table 4, Lingo-Judge %):**
- No fine-tuning: 33.60 (vs 60.80 baseline) — fine-tuning roughly doubles accuracy.
- No pre-training: 56.60 — pre-training contributes ~4 pts.
- Action only: 53.80; Scenery only: 55.40 — both subsets needed.
- Single frame: 57.00; 7 frames: 60.60 — 5 frames sweet spot.
- Early fusion: 48.40; mid-fusion: 59.20 — late fusion strongest.
- LLM swap: OPT-7B 50.00; Llama-2-7B-Chat 59.20; Mistral-7B-Instruct 58.00.

## Limitations & Open Questions
- Dataset only uses a single front-facing camera and 4-second clips; no LiDAR/radar, no longer temporal context.
- Lingo-Judge is tailored to LingoQA's response style — TruthfulQA-style specialised classifiers are not expected to generalise to new question distributions; cannot rank between two equally-correct phrasings (only factual correctness).
- No closed-loop or actual driving-decision evaluation — pure QA metric, not action-prediction.
- Models capped at 7B parameters; scaling not studied.
- 37% gap between best zero-shot model (GPT-4V 59.6) and human multi-frame (96.6); 23% gap between single-frame LLaVA and single-frame human, suggesting both single-frame perception and video fusion need progress.
