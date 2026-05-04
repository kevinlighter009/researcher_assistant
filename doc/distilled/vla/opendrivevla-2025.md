---
paper_id: 2025-opendrivevla
title: "OpenDriveVLA: Towards End-to-end Autonomous Driving with Large Vision Language Action Model"
authors: [Xingcheng Zhou, Xuyuan Han, Feng Yang, Yunpu Ma, Volker Tresp, Alois Knoll]
year: 2025
venue: arXiv
arxiv_id: "2503.23463"
url: https://arxiv.org/abs/2503.23463
primary_category: vla
secondary_categories: [e2e_planning]
keywords: [vla, qwen2.5, hierarchical-alignment, agent-env-ego-interaction, bev-tokens, autoregressive-trajectory, nuscenes]
one_line_summary: Open-source 0.5B/3B/7B VLA built on Qwen2.5 that fuses 3D instance/scene/map tokens via hierarchical alignment and agent-env-ego interaction for autoregressive ego-trajectory planning on nuScenes.
distilled_at: 2026-05-02
source_pdf: doc/papers/vla/opendrivevla-2025.pdf
---

# OpenDriveVLA: Towards End-to-end Autonomous Driving with Large Vision Language Action Model

## Keywords
- vla, qwen2.5, hierarchical-alignment, agent-env-ego-interaction, bev-tokens, autoregressive-trajectory, nuscenes

## TL;DR
Existing VLM-based driving stacks rely on 2D-image-language priors and tend to hallucinate or miss 3D spatial structure. OpenDriveVLA builds a Vision-Language-Action model on top of open-source Qwen2.5 LLMs (0.5B/3B/7B), feeding it instance-aware 3D tokens (scene, agent, map) from a BEV perception module and aligning them to the LLM word-embedding space via a hierarchical, multi-stage training recipe that includes an explicit agent-environment-ego interaction objective. On the nuScenes open-loop benchmark it reaches 0.33m average L2 (ST-P3 metrics) for the 3B/7B versions and matches/beats prior autoregressive driving LLMs while also leading on nuCaption, nuScenesQA and Nu-X VQA tasks.

## Problem & Motivation
Existing end-to-end driving stacks suffer from limited long-tail generalization, weak semantic understanding and rigid task reasoning. Naively reusing pretrained VLMs (GPT-4V, LLaVA, Qwen-VL) is unsatisfactory because they are optimized for static 2D image-language tasks and have poor 3D spatial reasoning, while instance-agnostic VLMs are prone to hallucinations and overconfident-but-wrong outputs that are unsafe in driving. The paper asks: how to harness emergent VLM capabilities to produce safe, spatially-grounded driving actions in dynamic 3D environments while balancing inference speed and planning effectiveness.

## Innovation Points
- **3D instance-aware visual tokens** — three query modules (Global SceneSampler, Agent QueryTransformer, Map QueryTransformer) extract scene, per-agent and map tokens from BEV features so the LLM consumes structured 3D representations rather than raw 2D patches.
- **Hierarchical Vision-Language Alignment** — token-specific projectors are trained against detailed captions (with BEV coordinates for agents, scene-level captions for scene/map tokens) to bridge structured visual tokens and the LLM word embedding space.
- **Agent-Environment-Ego interaction modeling (Stage 2.5)** — an auxiliary conditional agent-trajectory-forecasting task forces the LLM to internalize multi-agent dynamics and ego-relative interactions before trajectory tuning, making predicted ego trajectories more behaviorally grounded.
- **Multi-stage training pipeline** — Stage 1 hierarchical feature alignment, Stage 2 driving instruction tuning (perception/motion-prediction/action-reasoning QA), Stage 2.5 agent-env-ego interaction, Stage 3 end-to-end trajectory planning tuning; ablations show each stage incrementally lowers L2 and collision rate.
- **Open-source LLM scaling** — same recipe instantiated at 0.5B / 3B / 7B (Qwen2.5-Instruct), with the 0.5B model already outperforming most prior autoregressive driving LLMs.

## Model Architecture
- Inputs: multi-view camera images, ego state Sego (textual), driver command Xdri (e.g. "Please Turn Right"); no LiDAR.
- 3D Visual Perception (frozen ResNet-101 backbone after Stage 3): multi-view 2D features f2D lifted to BEV f_bev (200x200 spatial resolution), pretrained on detection/tracking/map segmentation.
- Token extraction:
  - Global SceneSampler Q_scene over f2D -> scene token v_scene
  - Agent QueryTransformer Q_agent over f_bev -> {v_agent^i} for Na detected agents
  - Map QueryTransformer Q_map over f_bev -> map token v_map
- Visual Projector: per-token-type two-layer MLP+GeLU (Phi_scene, Phi_agent, Phi_map) maps each token to LLM word-embedding space.
- LLM backbone: Qwen2.5-Instruct (0.5B / 3B / 7B), fully fine-tuned during driving stages; 2D backbone frozen in Stage 3.
- Auxiliary head (Stage 2.5): per-agent future motion W_a^i conditioned on V_env, S_ego and Phi_agent(v_agent^i).
- Output: ego waypoints W_ego = {w1...wT} for T = 6 waypoints over 3 seconds at 0.5s intervals; tokenized as discrete text via Tokenizer, autoregressively decoded by the LLM, then Decoder maps tokens back to 2D coordinates.
- Training compute: 4x NVIDIA H100, batch size 1, ~2 days; deterministic decoding (temperature 0) at inference.
- Training data: nuScenes plus TOD3Cap, nuCaption, nuScenesQA, nuX, GPT-Driver-derived QA.

## Benchmark Results
**Open-loop trajectory planning on nuScenes (lower is better):**

ST-P3 metrics (L2 m / Collision %, Avg over 1/2/3s):
| Method                | L2 Avg | Coll. Avg | LLM        |
|-----------------------|--------|-----------|------------|
| ST-P3                 | 2.11   | 1.27      | -          |
| UniAD                 | 0.69   | 0.34      | -          |
| GPT-Driver            | 0.44   | 0.17      | GPT-3.5    |
| OmniDrive             | 0.33   | 0.30      | LLaVA-7B   |
| EMMA                  | 0.32   | -         | Gemini     |
| **OpenDriveVLA-0.5B** | 0.35   | 0.09      | Qwen2.5-0.5B |
| **OpenDriveVLA-3B**   | **0.33** | **0.10** | Qwen2.5-3B |
| **OpenDriveVLA-7B**   | **0.33** | **0.10** | Qwen2.5-7B |

UniAD metrics (L2 Avg / Coll. Avg over 1/2/3s):
- OpenDriveVLA-0.5B: 0.63 / 0.26
- OpenDriveVLA-3B: 0.67 / 0.70
- OpenDriveVLA-7B: 0.66 / 0.66 (text states "average L2 error of 0.66m" for 7B on UniAD metrics)

**Driving QA (Table II/III):**
- nuCaption: OpenDriveVLA-7B BLEU-4 27.6, BERT-S 92.2 (best vs LLaVA1.5 5.4 / 85.0, LiDAR-LLM 19.3 / 91.3).
- nuScenesQA Acc: 0.5B 58.4, 3B 58.5, 7B 58.2; vs BEVDet+BUTD 57.0.
- Nu-X CIDER: 0.5B 32.3 (best), beating Hint-UniAD 21.7 and Gemini 17.6; surprisingly 0.5B > 7B here.

**Ablations (0.5B):**
- Inputs (Table IV): adding ego state cuts L2 from 1.34 -> 0.77 and collision from 0.24 -> 0.10; adding history then command further drops L2 to 0.68 and collision to 0.09 (ST-P3).
- Training stages (Table V): Stage 3 only -> ST-P3 collision 0.13; +Stage 1 -> 0.12; +Stages 1+2 -> 0.11; full Stages 1+2+2.5+3 -> 0.09 (with L2 0.35).

## Limitations & Open Questions
- Open-loop nuScenes only — no closed-loop or CARLA / NAVSIM evaluation; ego-state shortcut on nuScenes is well-known and may inflate L2/collision numbers (the input ablation confirms ego state is the single largest contributor).
- Inference cost / latency for 3B and 7B variants on a vehicle is not reported despite the paper's stated focus on balancing speed and planning effectiveness.
- 7B does not outperform 0.5B on Nu-X VQA, suggesting scaling is not yet monotone and instruction-tuning data may be the bottleneck.
- Vision encoder is frozen and trained on nuScenes-only perception tasks; cross-dataset / cross-sensor transfer is untested.
- Captions used for hierarchical alignment are partly post-processed from existing datasets (TOD3Cap, nuCaption) and ground-truth map annotations; sensitivity to caption noise is not analyzed.
