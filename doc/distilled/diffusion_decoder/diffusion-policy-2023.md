---
paper_id: 2023-diffusion-policy
title: "Diffusion Policy: Visuomotor Policy Learning via Action Diffusion"
authors: [Cheng Chi, Zhenjia Xu, Siyuan Feng, Eric Cousineau, Yilun Du, Benjamin Burchfiel, Russ Tedrake, Shuran Song]
year: 2023
venue: RSS 2023 (extended IJRR version, arXiv v5 2024)
arxiv_id: "2303.04137"
url: https://arxiv.org/abs/2303.04137
primary_category: diffusion_decoder
secondary_categories: [misc]
keywords: [diffusion-policy, ddpm, action-diffusion, visuomotor-policy, behavior-cloning, receding-horizon, robomimic, push-t]
one_line_summary: Visuomotor behavior-cloning policy that represents the action distribution as a conditional DDPM over action sequences, with receding-horizon control, FiLM/cross-attention visual conditioning, and a transformer denoiser; +46.9% average success across 15 manipulation tasks.
distilled_at: 2026-05-02
source_pdf: doc/papers/diffusion_decoder/diffusion-policy-2023.pdf
---

# Diffusion Policy: Visuomotor Policy Learning via Action Diffusion

## Keywords
- diffusion-policy, ddpm, action-diffusion, visuomotor-policy, behavior-cloning, receding-horizon, robomimic, push-t

## TL;DR
Imitation-learned visuomotor policies struggle with multimodal demonstrations, sequential correlation, and high-precision actions. The authors recast policy learning as a conditional Denoising Diffusion Probabilistic Model (DDPM) that generates a short sequence of robot actions conditioned on visual observations, sampled iteratively via stochastic Langevin dynamics at inference. Across 15 simulated and real-world manipulation tasks from 4 benchmarks, Diffusion Policy improves over the prior best behavior-cloning methods (LSTM-GMM, IBC, BET) by an average of 46.9% in success rate, while remaining stable to train.

## Problem & Motivation
Behavior cloning for robot manipulation is harder than ordinary regression because human demonstrations are often **multimodal** (multiple valid ways to achieve a goal), exhibit **sequential correlation**, and require **high precision**. Existing approaches each have a known failure mode:
- **Explicit policies** (direct regression, GMM, categorical/discretized actions) are mode-collapsing or scale poorly with action dimensionality.
- **Implicit policies / Energy-Based Models** (e.g. IBC) can in principle represent multimodal distributions, but training them via InfoNCE-style negative sampling is unstable, requires careful hyperparameter tuning, and yields oscillating success rates over training.
- Methods like BET and BC-RNN that sequence single-step actions can switch between modes mid-rollout, producing **jittery actions**, and tend to get stuck on **idle actions** in real-world data.

The authors argue the **policy structure itself**, not just the data or training pipeline, is a major performance bottleneck for behavior cloning, and that a diffusion-based action head fixes the above failure modes simultaneously.

## Innovation Points
- **Conditional action-diffusion formulation** — instead of directly outputting actions, the network predicts the noise / score of the conditional action-score, optimized via standard DDPM MSE loss; sampling uses K denoising steps of stochastic Langevin dynamics on the action.
- **Visual observation as conditioning, not joint variable** — observations $O_t$ are fed only as condition (FiLM or cross-attention), not added to the diffusion variable; this avoids paying for diffusion over future-state tokens and keeps the visual encoder a single-pass module per control step.
- **Closed-loop action-sequence prediction with receding horizon** — predicts $T_p$ future actions, executes $T_a$ of them, then re-plans. Combines temporal action consistency (less jitter, robustness to idle actions) with responsiveness; warm-starts the next inference with the previous prediction.
- **Time-series diffusion transformer** — a minGPT-style transformer denoiser with cross-attention to observation tokens and causal attention over action tokens, designed to mitigate the over-smoothing of CNN-based diffusion heads on high-frequency / velocity-control tasks.
- **End-to-end visual encoder for diffusion** — ResNet-18 trained from scratch with spatial softmax and GroupNorm (replacing global avg pool and BatchNorm), which the authors find empirically beats frozen ImageNet/CLIP backbones for diffusion-policy training.
- **Position-control action space** — empirically much better than velocity control for Diffusion Policy (figure 4), reversing the field-default choice; the authors attribute this to less compounding error and greater multimodality, both of which Diffusion Policy is well-suited to absorb.

## Model Architecture
- **Inputs**: a sliding window of the last $T_o$ observations $O_t$ (RGB images from one or more cameras + proprioceptive state). Real-world setups use 1 to 4 cameras (front, wrist, scene, top-down).
- **Visual encoder**: per-camera ResNet-18 from scratch, with spatial softmax in place of global average pooling and GroupNorm in place of BatchNorm; encodings concatenated into observation feature $O_t$. Trained end-to-end with the diffusion head.
- **Diffusion denoiser** $\varepsilon_\theta(O_t, A^k_t, k)$ — two interchangeable variants:
  - **CNN-based**: 1D temporal U-Net (adapted from Janner et al. 2022) over the action-sequence axis, with FiLM conditioning of $O_t$ injected channel-wise into every conv layer; diffusion step $k$ also fused via FiLM. Recommended default.
  - **Transformer-based**: minGPT-style decoder stack; noisy action tokens $A^k_t$ enter as input tokens (prepended by sinusoidal embedding of $k$); $O_t$ passed via multi-head cross-attention into each block; causal self-attention mask over actions. Predicts $\varepsilon$ per token. Recommended for high-rate / velocity-control tasks.
- **Noise schedule**: Square Cosine Schedule (iDDPM, Nichol & Dhariwal 2021); 100 training iterations, 10 inference iterations using DDIM (Song et al. 2021).
- **Output**: $T_p$ steps of actions (typically $T_p = 16$, action horizon $T_a = 8$ at $T_o = 2$). Action dimensionality ranges from 2 (Push-T) up to 14 (bimanual / Transport). Inference latency ~0.1 s on a single Nvidia 3080 GPU.
- **Training data scale**: 200–656 proficient-human demos per simulated task (Robomimic / Push-T / Kitchen / BlockPush); 90–284 real-world demos per task (e.g. 162 for Mat Unrolling, 284 for Shirt Folding). Trained for 4500 epochs (state) / 3000 epochs (image) per task.

## Benchmark Results
Headline: Diffusion Policy **outperforms LSTM-GMM, IBC, and BET on all 15 tasks across 4 benchmarks (Robomimic, Push-T, BlockPush, Franka Kitchen)** with an **average success-rate improvement of 46.9%**.

**Robomimic + Push-T, state-based policy (Table 1, success rate, max / avg-of-last-10-checkpoints):**
| Task          | LSTM-GMM (ph/mh) | IBC (ph/mh)   | BET (ph)    | DP-CNN (ph/mh) | DP-Transformer (ph/mh) |
|---------------|------------------|---------------|-------------|----------------|------------------------|
| Lift          | 1.00 / 1.00      | 0.79 / 0.15   | 1.00        | 1.00 / 1.00    | 1.00 / 1.00            |
| Can           | 1.00 / 1.00      | 0.00 / 0.01   | 1.00        | 1.00 / 1.00    | 1.00 / 1.00            |
| Square        | 0.95 / 0.86      | 0.00 / 0.00   | 0.76        | 1.00 / 0.97    | 1.00 / 0.95            |
| Transport     | 0.76 / 0.62      | 0.00 / 0.00   | 0.38        | 0.94 / 0.68    | 1.00 / 0.62            |
| ToolHang      | 0.67             | 0.00          | 0.58        | 0.50           | **1.00**               |
| Push-T        | 0.67             | 0.90          | 0.79        | **0.95**       | 0.95                   |

**Multi-stage tasks (Table 4):**
| Task / metric | LSTM-GMM | BET  | DP-CNN | DP-Transformer |
|---------------|----------|------|--------|----------------|
| BlockPush p2  | 0.01     | 0.71 | 0.11   | **0.94**       |
| Kitchen p4    | 0.34     | 0.24 | **0.99** | 0.96         |

(BlockPush p2 = pushing 2 blocks in any order; Kitchen p4 = completing 4 sub-tasks.)

**Real-world Push-T (Table 6, IoU / success% / duration):** Diffusion Policy end-to-end transformer reaches IoU 0.80 / success 95% / 22.9 s, vs IBC velocity 0.19 / 0% / 41.6 s and LSTM-GMM velocity 0.25 / 0% / 51.7 s. Human demo IoU is 0.84.

**Real-world bimanual / 6DoF tasks:** Egg Beater 55% (210 demos), Mat Unrolling 75% (162 demos), Shirt Folding 75% (284 demos), Mug Flipping 90% (vs 0% LSTM-GMM), 6DoF Sauce Pouring success 79% (vs 0% LSTM-GMM, human 100%), Sauce Spreading success 100%.

**Key ablations:**
- **Action horizon $T_a$** (Fig 5): success peaks around $T_a=8$; $T_a=1$ (single-step) and $T_a \geq 64$ both degrade — confirms the value of a moderate-length sequence.
- **Latency robustness** (Fig 5): Diffusion Policy with position control retains peak success up to ~4 steps of induced latency; velocity control degrades much faster.
- **Vision encoder** (Table 5, square-ph): ResNet-18 trained from scratch end-to-end = 0.94; frozen ImageNet ResNet-18 = 0.58; finetuned CLIP ViT-B/16 = **0.98** (with 10× lower LR than the policy network and only 50 epochs).
- **Velocity vs position control** (Fig 4): Diffusion Policy gains substantially from switching to position control on Square and Kitchen p4, while LSTM-GMM and BET regress — i.e. the gain is specific to diffusion's ability to represent multimodal action distributions.
- **Training stability** (Fig 6): IBC's success rate oscillates throughout training (forcing per-checkpoint evaluation); Diffusion Policy converges and stays stable.

## Limitations & Open Questions
- Inherits the structural limitations of behavior cloning — performance is bounded by demonstration quality and quantity; suboptimal/negative data is not exploited (the authors point at offline RL + diffusion, e.g. IDQL, as future work).
- **Computational cost**: K denoising iterations per inference step give higher latency than LSTM-GMM-style single-pass policies. Real-time at 10 Hz needs DDIM with 10 inference steps and a 3080-class GPU; tasks requiring very high-rate control may not fit. Future work points to faster solvers and consistency models.
- **Transformer denoiser is hyperparameter-sensitive** — only consistently wins on state-based / high-rate tasks; the authors recommend starting with the CNN-based variant.
- **Task-specific training**: each policy is trained per task on 100s of demos; cross-task generalization, language conditioning, and scaling laws are not explored in this paper.
- **Real-world bimanual success rates plateau around 55–75%**; primary failure modes are out-of-distribution initial states and missed grasps that the policy does not recover from.
