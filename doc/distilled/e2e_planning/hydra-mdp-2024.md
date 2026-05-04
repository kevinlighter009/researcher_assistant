---
paper_id: 2024-hydra-mdp
title: "Hydra-MDP: End-to-end Multimodal Planning with Multi-target Hydra-Distillation"
authors: [Zhenxin Li, Kailin Li, Shihao Wang, Shiyi Lan, Zhiding Yu, et al.]
year: 2024
venue: "CVPR 2024 Autonomous Grand Challenge (NAVSIM track, 1st place)"
arxiv_id: "2406.06978"
url: https://arxiv.org/abs/2406.06978
primary_category: e2e_planning
secondary_categories: [perception]
keywords: [multi-target-distillation, hydra-decoder, planning-vocabulary, rule-based-teachers, navsim, pdm-score, transfuser]
one_line_summary: Multi-target hydra-distillation lets an end-to-end planner learn from both human log-replays and rule-based simulator teachers, winning NAVSIM with PDM 91.0.
distilled_at: 2026-05-02
source_pdf: doc/papers/e2e_planning/hydra-mdp-2024.pdf
---

# Hydra-MDP: End-to-end Multimodal Planning with Multi-target Hydra-Distillation

## Keywords
- multi-target-distillation, hydra-decoder, planning-vocabulary, rule-based-teachers, navsim, pdm-score, transfuser

## TL;DR
End-to-end driving planners trained only by imitating human log-replays underfit safety/comfort metrics, while rule-based planners depend on perfect perception and lean on non-differentiable post-processing. Hydra-MDP uses a multi-head ("hydra") trajectory decoder distilled from BOTH a human teacher (imitation softmax over a discrete planning vocabulary) and rule-based teachers (offline NAVSIM simulator scores per metric). The method achieved 1st place in the CVPR 2024 NAVSIM challenge with PDM 91.0 (vs. 89.1 for a privileged PDM-Closed baseline using ground-truth perception).

## Problem & Motivation
Existing end-to-end planners come in two flavors, both broken in different ways:
- **Single-modal + single-target imitation** (e.g. UniAD, VAD): regress one trajectory directly from sensors with limited supervision. Fails to enforce safety, drivable area, comfort beyond what shows up in human logs.
- **Multi-modal + post-processing** (e.g. Vadv2): predict K trajectories, then pick one with a hand-crafted cost function over predicted perception. The selection step is non-differentiable and degrades when perception is imperfect.

Hydra-MDP argues planning is intrinsically multi-target (NC, DAC, TTC, C, EP) and multi-modal (many valid trajectories per scene), so the planner should be supervised by a SET of differentiable, metric-aligned teachers in an end-to-end fashion.

## Innovation Points
- **Multi-target Hydra-Distillation** — a teacher-student KD scheme where each rule-based metric (No-at-fault Collisions, Drivable Area Compliance, Time-To-Collision, Comfort, Ego Progress) gets its own simulator-derived teacher signal, distilled into a dedicated student head via binary cross-entropy.
- **Hydra Prediction Heads** — multi-head MLP decoder on top of a transformer trajectory decoder; each head predicts a per-trajectory sub-score for one metric, plus an imitation head for human-likeness. Cleanly extensible to additional teachers.
- **Discrete planning vocabulary V_k** — 700K nuPlan trajectories clustered by K-means into k anchors (k ∈ {4096, 8192}), each a 40-step (10 Hz, 4 s) (x, y, heading) sequence. Reframes planning as classification over anchors instead of regression.
- **Offline rule-based supervision** — simulation scores for the entire vocabulary are precomputed once per scenario, so distillation is cheap during training and the simulator never enters the gradient path.
- **Weighted score ensembling at inference** — final cost combines log-imitation and log-metric heads with grid-searched weights {w_i}; rule-based weights ≥ 10× the imitation weight.

## Model Architecture
- **Inputs**: front-view camera (concatenation of center-cropped front, front-left, front-right) at 256x1024 by default; LiDAR splatted from 4 frames into a BEV density map.
- **Perception Network** (built on Transfuser baseline): image backbone (ResNet34 default; ViT-L or V2-99 for scaled variants) + LiDAR backbone, fused via stacked transformer layers. Auxiliary perception heads do 3D detection + BEV segmentation. Output: environment tokens F_env.
- **Trajectory Decoder** (Vadv2-style):
  - Planning vocabulary V_k (k anchors, each 40x3) encoded by MLP + transformer encoder layers, summed with ego-state embedding E.
  - Cross-attention transformer decoder with Q = vocabulary latents, K/V = F_env produces V_k''.
- **Hydra Prediction Heads** (per-anchor, k-way):
  - Imitation head: softmax score S^im trained against L2-distance softmax over log-replay trajectory T-bar (Eq. 8-9).
  - One MLP per rule-based metric m ∈ {NC, DAC, TTC, C, EP} producing S^m, distilled with BCE against precomputed simulator scores S-hat^m (Eq. 10).
- **Inference cost** (Eq. 11): f-tilde = -(w1 log S^im + w2 log S^NC + w3 log S^DAC + w4 log(5*S^TTC + 2*S^C + 5*S^EP)); pick argmin trajectory.
- **Training**: 8x NVIDIA A100, batch 256 across 20 epochs, lr 1e-4, weight decay 0.0.

## Benchmark Results
**NAVSIM Navtest split, PDM score (higher = better). PDM = NC * DAC * DDC * (5*TTC + 2*C + 5*EP)/12; DDC neglected per task.**

| Method | Inputs | NC | DAC | EP | TTC | C | PDM Score |
|---|---|---|---|---|---|---|---|
| PDM-Closed (privileged GT perception) | Perception GT | 94.6 | 99.8 | 89.9 | 86.9 | 99.9 | 89.1 |
| Transfuser | LiDAR & Camera | 96.5 | 87.9 | 73.9 | 90.2 | 100 | 78.0 |
| Vadv2-V_8192 | LiDAR & Camera | 97.2 | 89.1 | 76.0 | 91.6 | 100 | 80.9 |
| Hydra-MDP-V_8192-W-EP | LiDAR & Camera | 98.3 | 96.0 | 78.7 | 94.6 | 100 | **86.5** |

**Scaling + ensembling (Table 2):**

| Model | Backbones | NC | DAC | EP | TTC | C | PDM |
|---|---|---|---|---|---|---|---|
| Hydra-MDP-A | ViT-L (Depth-Anything init) | 98.4 | 97.7 | 85.0 | 94.5 | 100 | 89.9 |
| Hydra-MDP-B | V2-99 | 98.0 | 97.8 | 86.5 | 93.9 | 100 | 90.3 |
| Hydra-MDP-C (ensembled) | ViT-L + ViT-L (EVA) + V2-99 | 98.7 | 98.2 | 86.5 | 95.0 | 100 | **91.0** |

Notable points:
- Final ensembled model (PDM 91.0) BEATS the privileged PDM-Closed baseline (89.1) despite using only sensor inputs vs. ground-truth perception.
- Replacing post-processing with hydra-distillation: V_4096 jumps from 79.7 (Vadv2) to 82.6 (Hydra-MDP) at the same vocab size.
- Adding W (weighted confidence) and EP-distillation: +3.3 PDM (83.0 -> 86.5 at V_8192).
- Larger backbones give modest gains (+0.4 PDM ViT-L vs V2-99); ensembling adds ~0.7 PDM on top of best single model.

## Limitations & Open Questions
- Evaluated only on NAVSIM (open-loop with closed-loop-style metrics on nuPlan-derived data); no true closed-loop driving rollouts.
- The planning vocabulary is fixed (700K -> k clusters); coverage of rare maneuvers and behavior outside the vocabulary support is not analyzed.
- DDC sub-metric is neglected "due to an implementation problem" (footnote), so the optimization target is a slight reduction of full PDM.
- Inference cost of the ensembled multi-backbone model (ViT-L x2 + V2-99) is not reported and likely impractical for on-vehicle deployment.
- Teacher quality is bounded by the offline simulator's fidelity; failure modes when simulator scores disagree with real-world safety are not discussed.
- Confidence weighting parameters {w_i} require grid search per deployment, which the paper does not characterize for sensitivity.
