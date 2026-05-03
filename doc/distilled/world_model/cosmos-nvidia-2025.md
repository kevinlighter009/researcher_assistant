---
paper_id: 2025-cosmos
title: "Cosmos World Foundation Model Platform for Physical AI"
authors: [NVIDIA]
year: 2025
venue: arXiv
arxiv_id: "2501.03575"
url: https://arxiv.org/abs/2501.03575
primary_category: world_model
secondary_categories: [datasets, e2e_planning]
keywords: [world-foundation-model, video-tokenizer, diffusion-transformer, autoregressive-transformer, physical-ai, video-generation, post-training]
one_line_summary: Open-weight platform of pre-trained video world foundation models (diffusion + autoregressive transformers, 4B-14B) with causal video tokenizers, data curator and guardrail for Physical AI.
distilled_at: 2026-05-02
source_pdf: doc/papers/world_model/cosmos-nvidia-2025.pdf
---

# Cosmos World Foundation Model Platform for Physical AI

## Keywords
- world-foundation-model, video-tokenizer, diffusion-transformer, autoregressive-transformer, physical-ai, video-generation, post-training

## TL;DR
Physical AI (robots, AVs) needs a digital twin of the world to safely scale training data, but no general-purpose video world model exists. NVIDIA releases Cosmos, an open-weight platform comprising a video data curation pipeline, a family of causal continuous/discrete video tokenizers, two families of pre-trained transformer-based World Foundation Models (diffusion and autoregressive, 4B-14B params, trained on ~100M curated video clips with 10K H100s for 3 months), and post-training recipes for camera control, robotic manipulation, and autonomous driving. Cosmos tokenizers achieve SOTA reconstruction (e.g. PSNR 35.85 on DAVIS at 4x8x8 compression vs CogVideoX 29.29) and the WFMs produce 3D-consistent video (Sampson error 0.355 vs VideoLDM 0.841).

## Problem & Motivation
Physical AI lags behind language/vision AI because real-world data collection is expensive, slow, and dangerous (exploratory actions can damage hardware and the world). Authors argue that a general-purpose **World Foundation Model** — a pretrained generative model of physical-world video that can be specialized via post-training — is the analogue of an LLM for Physical AI: it enables policy evaluation, policy initialization, RL reward modeling, model-predictive planning, and synthetic data generation. Prior video generators (CogVideoX, VideoLDM, Sora-class) are not designed around the Physical AI use case (causal token compression, conditioning on actions/trajectories/cameras, multi-view, guardrails) and most are closed-weight. Cosmos targets that gap with an open-weight platform.

## Innovation Points
- **Pre-train + post-train paradigm for WFMs** — one expensive generalist `pre-trained WFM` is fine-tuned into small specialized `post-trained WFMs` per Physical AI setup, mirroring the LLM playbook.
- **Video data curator** — Ray-orchestrated pipeline turning 20M hours of raw video into ~100M filtered, shot-split, VLM-captioned high-dynamics clips (2-60s).
- **Cosmos Tokenizer family** — causal encoder-decoder tokenizers in continuous (CV) and discrete (DV via FSQ) forms at multiple compression rates (4x8x8, 8x8x8, 8x16x16); causality enables joint image+video training.
- **Two parallel WFM families** — diffusion (7B/14B, EDM in latent space) and autoregressive (4B/12B base, 5B/13B Video2World) Llama3-style with T5 cross-attention for text.
- **AR-to-diffusion decoder bridge** — `Cosmos-Predict1-7B-Decoder-DV8x16x16ToCV8x8x8` maps heavily compressed AR tokens back to high-quality continuous tokens, mitigating AR distortion.
- **Post-training recipes + guardrail** — sample post-trained WFMs for camera-pose control, robotic manipulation (instruction or action+video), and multi-view / trajectory AV; pre-Guard and post-Guard block harmful I/O.

## Model Architecture
Platform components (Fig. 4): `Video Curator -> Tokenizers -> Pre-trained WFMs -> Post-Training Samples -> Guardrail`.

WFM definition (Fig. 3): `W(x_{0:t}, c_t) -> x_{t+1}`, where `x_{0:t}` is past RGB video and `c_t` is the perturbation (text, action, trajectory, camera pose, or random).

- **Tokenizer.** Attention-based causal encoder-decoder. Trained with L1 + VGG-19 perceptual + optical-flow + Gram-matrix + adversarial losses. Variants: image (CI/DI) at 8x8 and 16x16; video (CV/DV) at 4x8x8, 8x8x8, 8x16x16; resolutions up to 720p/360p with 49-121 frames. Discrete variant uses FSQ instead of VQ.
- **Diffusion WFM.** Latent diffusion transformer over `Cosmos-Tokenize1-CV8x8x8-720p` continuous tokens. EDM-style score matching with uncertainty-weighted multi-noise-level loss. Two stages: Text2World (text -> video) then Video2World (past-video + text -> future video). Sizes: 7B, 14B. A separate `Cosmos-UpsamplePrompt1-12B-Text2World` (Mistral-NeMo-12B-Instruct based) rewrites human prompts into the WFM's preferred prompt style.
- **Autoregressive WFM.** Llama3-style GPT over `Cosmos-Tokenize1-DV8x16x16-720p` discrete tokens. Two stages: vanilla next-token foresight generation (4B, 12B base), then text-conditioned Video2World via cross-attention to T5 text embeddings (5B, 13B). Output is decoded to pixels via the AR-to-diffusion bridge decoder.
- **Compute / scale.** All WFMs trained on a single 10,000 NVIDIA H100 GPU cluster over ~3 months. Pre-training corpus ~100M clips from ~20M hours of video, captioned every 256 frames by a VLM.
- **Outputs.** Variable-length 720p video rollouts conditioned on text, image, video, action, trajectory, or camera pose, depending on the post-trained variant.

## Benchmark Results
**Tokenizer (continuous video, DAVIS / TokenBench):**
| Tokenizer | Compression | DAVIS PSNR ↑ | DAVIS rFVD ↓ |
|---|---|---|---|
| CogVideoX-Tokenizer | 4x8x8 | 29.29 | 19.58 |
| Cosmos-Tokenize1-CV4x8x8-360p | 4x8x8 | **35.85** | **10.06** |
| Cosmos-0.1-Tokenizer-CV8x16x16 | 8x16x16 | 27.60 | 93.82 |

Runtime (Table 9): Cosmos-CI 8x8 is 62.7 ms/img vs FLUX-Tokenizer 242 ms; Cosmos-DI 8x8 is 64.2 ms/img vs LlamaGen 475 ms — reported as 2x-12x faster at smaller param count.

**3D consistency of base WFMs (RealEstate10K subset, vs VideoLDM):**
| Method | Sampson err ↓ | Pose-est success ↑ | View-synth PSNR ↑ |
|---|---|---|---|
| VideoLDM | 0.841 | 4.4% | 26.23 |
| Cosmos-Predict1-7B-Text2World | **0.355** | 62.6% | **33.02** |
| Cosmos-Predict1-7B-Video2World | 0.473 | **68.4%** | 30.66 |
| Real Videos (reference) | 0.431 | 56.4% | 35.38 |

**Physics alignment (PhysX/Isaac Sim, 8 scenarios, Table 20):** with prompt + 9 conditioning frames, Cosmos-Predict1-7B-Video2World achieves PSNR 21.06 / SSIM 0.691 / object-IoU 0.592; the 14B variant reaches object-IoU 0.598. Larger model size does not consistently improve physics adherence.

**AR failure rate (Table 18, 9-frame video conditioning):** 4B 1%, 5B-Video2World 2%, 12B 1%, 13B-Video2World 0%.

Post-training experiments are demonstrated qualitatively for camera control, robotic manipulation (instruction- and action-conditioned), and multi-view AV; quantitative downstream-task scores are largely `not reported` at platform-paper level.

## Limitations & Open Questions
- Authors explicitly state the WFM problem is "far from being solved"; physics adherence is weak — failure modes include object impermanence, deformation, gravity violations.
- Larger 14B/13B models do not consistently beat 7B on physics IoU, suggesting scaling alone is insufficient without better data curation and inductive biases.
- The "Future Cosmos" use cases (policy evaluation, RL reward, MPC, Sim2Real synthetic data) are listed as motivations but **not empirically validated** in this paper.
- AR variant requires an extra diffusion decoder to recover quality from heavy DV8x16x16 compression; raw AR rollouts can be visibly distorted.
- Inference cost / latency for downstream closed-loop Physical AI deployment is not addressed.
- TokenBench and the physics benchmark are newly introduced by NVIDIA; cross-lab head-to-head comparison is therefore limited.
