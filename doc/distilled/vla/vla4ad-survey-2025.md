---
paper_id: 2025-vla4ad-survey
title: "A Survey on Vision-Language-Action Models for Autonomous Driving"
authors: [Sicong Jiang, Zilin Huang, Kangan Qian, et al.]
year: 2025
venue: arXiv
arxiv_id: "2506.24044"
url: https://arxiv.org/abs/2506.24044
primary_category: vla
secondary_categories: [misc, e2e_planning, datasets]
keywords: [vla, vla4ad, mllm, taxonomy, chain-of-thought, closed-loop, nuscenes, carla]
one_line_summary: First comprehensive survey of Vision-Language-Action models for autonomous driving (VLA4AD); proposes a four-wave taxonomy (Pre-VLA / Modular / End-to-End / Reasoning-Augmented) and consolidates 20+ models, datasets, and open challenges.
distilled_at: 2026-05-02
source_pdf: doc/papers/vla/vla4ad-survey-2025.pdf
---

# A Survey on Vision-Language-Action Models for Autonomous Driving

## Keywords
- vla, vla4ad, mllm, taxonomy, chain-of-thought, closed-loop, nuscenes, carla

## TL;DR
Conventional end-to-end driving stacks lack interpretability and long-tail reasoning, while VLM-augmented stacks reason about scenes but do not decide what to do. The authors present the first comprehensive survey of Vision-Language-Action models for autonomous driving (VLA4AD), formalizing the architectural building blocks (vision encoder, language processor, action decoder), tracing a four-stage evolution (explainer to reasoning-centric), and cataloguing 20+ representative models, 8 datasets/benchmarks, training paradigms, and open challenges. The survey delivers a unified taxonomy and terminology so that future VLA4AD work can be compared on shared axes (input modality, language role, output abstraction, evaluation suite).

## Problem & Motivation
The VLA-for-driving literature is fragmented and growing rapidly, with no shared vocabulary or taxonomy. Prior surveys cover LLMs/VLMs in autonomous driving, but none address VLA — where language and action are fused inside a single policy rather than language being a passive overlay. The community lacks: (i) a clear terminological boundary between "VLM4AD" (perception-centric, language as explanation) and "VLA4AD" (action-centric, language as control conditioning); (ii) consolidated knowledge of which models exist, on which datasets they are evaluated, with which training recipes; (iii) a structured map of open challenges (real-time inference, multimodal alignment, V2V language, formal verification). The survey is positioned as the first to close this gap.

## Innovation Points
- **First VLA4AD-specific survey** — defines the term VLA4AD and distinguishes it from VLM4AD (passive language) and pure end-to-end (no language).
- **Four-wave evolution taxonomy** — Pre-VLA (Explainer) → Modular VLA → End-to-End VLA → Reasoning-Augmented VLA, organizing 20+ models along a single axis of language-action coupling.
- **Three-block architectural decomposition** — Vision Encoder + Language Processor + Action Decoder, with sub-categorization of action heads (autoregressive tokens, diffusion, flow-matching, hierarchical).
- **Consolidated catalogue** — Table 1 lists 16 representative models (2023-2025) with input modality, dataset, vision/LLM backbones, output type, and core focus; Table 2 lists 8 datasets/benchmarks (BDD-X, nuScenes, Bench2Drive, Reason2Drive, DriveLM-Data, Impromptu VLA, NuInteract, DriveAction).
- **Six-front open-challenge map** — robustness, real-time, data bottlenecks, multimodal alignment, multi-agent social complexity, domain adaptation; followed by five future directions (foundation-scale driving models, neuro-symbolic safety kernels, fleet-scale continual learning, standardised traffic language, cross-modal social intelligence).
- **Evaluation framework** — articulates a "dual-objective" view (drive safely + communicate faithfully) with four metric pillars (closed-loop, open-loop, language competence, robustness).

## Model Architecture
Surveys do not have a model architecture; the organizing framework is described instead.

**Three-block VLA4AD reference architecture (Section 3):**
- **Vision Encoder** — large self-supervised backbones (DINOv2, ConvNeXt-V2, CLIP); often paired with BEV projection or 3D-aware encoders (PointVLA, 3D-VLA).
- **Language Processor** — pretrained LLM decoder (LLaMA-2, Vicuna, Qwen-2.5, Gemini); instruction-tuned or RAG-augmented; LoRA for efficient adaptation.
- **Action Decoder** — four flavours: (i) autoregressive trajectory/control tokens, (ii) diffusion heads (DiffVLA, Diffusion-VLA), (iii) flow-matching policies tuned via GRPO/DPO, (iv) hierarchical controllers (ORION) that emit sub-goals to a downstream PID/MPC.

**Four-wave evolution (Section 4 — Figure 3):**
1. **Pre-VLA (Explainer)** — frozen VLM narrates the scene; vehicle still controlled by classical PID. Examples: DriveGPT-4, TS-VLM.
2. **Modular VLA** — language inserted as an intermediate planning component (route instructions, action experts). Examples: OpenDriveVLA, CoVLA-Agent, DriveMoE, LangCoop, SafeAuto, RAG-Driver.
3. **End-to-End VLA** — single multimodal forward pass from sensors+text to controls/trajectory. Examples: EMMA, SimLingo, LMDrive, CarLLaVA, ADriver-I, DiffVLA.
4. **Reasoning-Augmented VLA** — long-horizon memory + CoT + tool-use; LLM is the central controller. Examples: ORION (QT-Former memory), Impromptu-VLA (CoT alignment), AutoVLA (unified token CoT + trajectory).

**Output abstraction levels:**
- Low-level actions (steer/throttle/brake tokens) — early systems.
- Trajectory / waypoint planning (BEV or ego-coords) — most current systems; consumed by MPC.

## Benchmark Results
The survey provides no head-to-head numerical leaderboard, only a catalogue of evaluation suites and isolated reported numbers from individual papers.

**Datasets and benchmarks covered (Table 2):**
| Name | Year | Domain | Scale | Modalities | Tasks |
|------|------|--------|-------|------------|-------|
| BDD100K / BDD-X | 2018 | Real (US) | 100k videos / 7k clips | RGB | Captioning, QA |
| nuScenes | 2020 | Real (Boston/SG) | 1k scenes (20s, 6 cams) | RGB, LiDAR, Radar | Detection, QA |
| Bench2Drive | 2024 | Sim (CARLA) | 220 routes / 44 scenarios | RGB | Closed-loop control |
| Reason2Drive | 2024 | Real (nuSc/Waymo) | 600k video-QA | RGB video | CoT-style QA |
| DriveLM-Data | 2024 | Real+Sim | 18k scene graphs | RGB, Graph | Graph QA |
| Impromptu VLA | 2025 | Real (multi-src) | 80k clips (30s) | RGB video, State | QA, Trajectory |
| NuInteract | 2025 | Real (nuScenes) | 1k scenes | RGB, LiDAR | Multi-turn QA |
| DriveAction | 2025 | Real (fleet) | 2.6k scenarios / 16.2k QA | RGB video | High-level QA |

**Meta-observations the survey reports (no head-to-head numbers reproduced):**
- DriveMoE tops the Bench2Drive leaderboard via Mixture-of-Experts specialists.
- TS-VLM achieves a ~10x inference speed-up via soft-attentive token pooling; reported BLEU-4 of 56 on DriveLM (cited from primary work, not a survey-run measurement).
- DiffVLA halves trajectory error on Navsim-v2 via mixed sparse+dense diffusion (cited).
- Impromptu VLA reports SOTA on NeuroNCAP via 80k corner-case clips (cited).

Aggregate cross-model leaderboard: **not reported in survey**.

**Four metric pillars proposed (Section 6.2):**
- **Closed-loop driving** — route success, infractions, rule compliance (CARLA / Bench2Drive).
- **Open-loop prediction** — trajectory L2, collision rate, goal reach (nuScenes).
- **Language competence** — BLEU/CIDEr (NuInteract), reason-chain consistency (Reason2Drive), human ratings (BDD-X).
- **Robustness & stress** — sensor perturbations, adversarial prompts, OOD events, language edge-cases.

## Limitations & Open Questions
The survey itself enumerates six open challenges (Section 7) and five future directions (Section 8):

- **Robustness & reliability** — LLM hallucinations, slang misparsing, formal verification of language-conditioned policies remains unexplored.
- **Real-time performance** — running ViT + LLM at >=30 Hz on automotive hardware is unsolved; token reduction (TS-VLM), MoE sparsity, and event-triggered reasoning are partial answers.
- **Data & annotation bottlenecks** — tri-modal (image + control + language) supervision is scarce; coverage of non-English dialects, traffic slang, and legally binding phrasings is thin.
- **Multimodal alignment** — current VLA4AD is camera-centric; LiDAR, radar, HD-maps, and temporal state are only partially fused; principled, temporally consistent fusion of heterogeneous modalities is missing.
- **Multi-agent social complexity** — V2V "traffic language" needs protocol, trust, and security; cryptographic V2V and gesture-to-text grounding are early threads.
- **Domain adaptation & evaluation** — sim-to-real, cross-region generalisation, continual learning without catastrophic forgetting; no regulatory "AI driver's licence" yet defined.
- **Survey-level meta-limitation** — provides no quantitative meta-analysis or unified leaderboard; readers must consult primary papers for numerical comparisons.
