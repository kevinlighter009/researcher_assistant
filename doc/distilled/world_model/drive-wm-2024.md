---
paper_id: 2024-drive-wm
title: "Driving into the Future: Multiview Visual Forecasting and Planning with World Model for Autonomous Driving"
authors: [Yuqi Wang, Jiawei He, Lue Fan, Hongxin Li, Yuntao Chen, Zhaoxiang Zhang]
year: 2024
venue: CVPR 2024
arxiv_id: "2311.17918"
url: https://arxiv.org/abs/2311.17918
primary_category: world_model
secondary_categories: [e2e_planning, diffusion_decoder]
keywords: [multiview-video-diffusion, world-model, factorized-generation, tree-rollout, image-based-reward, nuscenes]
one_line_summary: First multiview driving world model — latent video diffusion factorized across views — used for tree-based planning rollouts evaluated by image-based rewards on nuScenes.
distilled_at: 2026-05-02
source_pdf: doc/papers/world_model/drive-wm-2024.pdf
---

# Driving into the Future: Multiview Visual Forecasting and Planning with World Model for Autonomous Driving

## Keywords
- multiview-video-diffusion, world-model, factorized-generation, tree-rollout, image-based-reward, nuscenes

## TL;DR
End-to-end planners trained on expert trajectories (e.g. VAD) generalize poorly to out-of-distribution ego states because they cannot foresee consequences of candidate actions. The authors propose Drive-WM, the first multiview latent-video-diffusion world model for driving, which jointly models temporal and view dimensions and factorizes the multiview joint distribution into reference views plus stitched views conditioned on neighbors. Drive-WM is plugged onto VAD as a tree-based rollout-and-reward planner, achieving 0.80 m avg L2 / 0.26% avg collision on nuScenes (vs. 1.02 m / 0.93% with VAD + random commands) and recovering planning quality under 0.5 m lateral OOD shifts.

## Problem & Motivation
- End-to-end planners (UniAD, VAD) imitate expert trajectories and degrade silently on OOD ego states; Figure 2 shows VAD producing irrational trajectories when shifted 0.5 m from the lane center.
- Classical world-model lines of work (Dreamer, MILE, GAIA-1, DriveDreamer) operate in vectorized state space, in simulators, in lab robotics, or on single-view video — none gives the full multiview pixel observation a BEV planner consumes.
- Three open challenges in driving world models: (1) high-resolution pixel modeling, (2) multiview consistency, (3) flexible conditioning on heterogeneous inputs (text, ego action, 3D box, BEV map, reference view).

## Innovation Points
- **Multiview latent video diffusion** — first world model that jointly generates all 6 surround views over time by adding *temporal encoding layers* and *multiview encoding layers* on top of a frozen image diffusion backbone (Stable Diffusion).
- **Factorized multiview generation** — partitions views into reference views {F, BL, BR} and stitched views {FL, B, FR}; models p(x) = p(x_r | x_pre) p(x_s | x_r, x_pre), boosting KPM consistency from 45.8% to 94.4% over joint modeling.
- **Unified conditional interface** — concatenates d-dim embeddings of initial context image, 3D boxes/HD map (perspective-projected), CLIP text, and per-frame ego action (Δx, Δy via MLP) into one cross-attention condition c_t ∈ R^((n+k+m+2)×d).
- **Tree-based rollout planning** — at each step, samples trajectories from VAD under three commands (straight/left/right), rolls them out through Drive-WM, and selects via an image-based reward.
- **Image-based reward function** — combines a *map reward* (centerline / drivable-area distance from online HD-map predictor) and an *object reward* (3D-detector-based collision distance) on the *generated* future frames.
- **KPM metric** — Key-Points Matching score for multiview consistency, using a pre-trained matcher to compare matched-keypoint counts in generated vs. real overlapping views.

## Model Architecture
- Inputs: 6 surround camera views at 384×192 (cropped/resized from nuScenes 1600×900); initial context image; 3D boxes + HD map projected to perspective; text (weather/lighting/view); per-frame ego action (Δx, Δy).
- Backbone: VAE encoder E + Denoising 3D UNet (Stable Diffusion init) + VAE decoder D. UNet block stack = Spatial Conv → Temporal Conv → Frame-wise Cross-Attention → View Attention → Temporal Attention.
- Latent z ∈ R^(T·K×C×H̃×W̃) reshaped (TK)CHW → KCTHW for 3D temporal conv, then (KHW)TC for self-attention along T (φ params), then (THW)KC for self-attention along K (ψ params).
- Training: image-only stage trains θ; then freeze θ, fine-tune temporal layers φ + multiview layers ψ on nuScenes train video.
- Factorized inference (Eq. 4): generate reference views x_r conditioned on previous frames x_pre; then generate stitched views x_s conditioned on adjacent reference views + previous frames (masked-out placeholder for absent view).
- Planning loop (Sec. 4): VAD samples candidate trajectories under three commands → Drive-WM rolls each forward in pixel space → reward = map_reward × object_reward computed on generated frames via a 3D detector and HD-map predictor → argmax trajectory accepted, rollout extends iteratively.
- Hardware: A40 (48 GB) GPUs.

## Benchmark Results
**Multi-view video generation on nuScenes (Table 1a):**

| Method        | Multi-view | Video | FID ↓ | FVD ↓ |
|---------------|-----------|-------|-------|-------|
| BEVGen        | yes       | no    | 25.54 | -     |
| BEVControl    | yes       | no    | 24.85 | -     |
| MagicDrive    | yes       | no    | 16.20 | -     |
| **Ours (img)**| yes       | no    | **12.99** | - |
| DriveGAN      | no        | yes   | 73.4  | 502.3 |
| DriveDreamer  | no        | yes   | 52.6  | 452.0 |
| **Ours (vid)**| yes       | yes   | **15.8** | **122.7** |

**Generation controllability on nuScenes (Table 1b)** — Ours: mAP_obj 20.66, mAP_map 37.68, mIoU_fg 27.19, mIoU_bg 65.07 (best across all four metrics vs. BEVGen / LayoutDiffusion / GLIGEN / BEVControl / MagicDrive).

**Planning on nuScenes (Table 3):**

| Method            | L2 1s/2s/3s/Avg (m) ↓        | Collision 1s/2s/3s/Avg (%) ↓ |
|-------------------|------------------------------|-------------------------------|
| VAD (GT cmd)      | 0.41 / 0.70 / 1.05 / 0.72    | 0.07 / 0.17 / 0.41 / 0.22     |
| VAD (rand cmd)    | 0.51 / 0.97 / 1.57 / 1.02    | 0.34 / 0.74 / 1.72 / 0.93     |
| **Drive-WM tree** | **0.43 / 0.77 / 1.20 / 0.80**| **0.10 / 0.21 / 0.48 / 0.26** |

**Out-of-domain planning, 0.5 m lateral shift (Table 5):** baseline VAD avg L2 = 1.02 / collision = 1.59%; with Drive-WM world-model fine-tune: 0.82 / 0.91% (vs. clean 0.72 / 0.22%).

**Ablations:**
- Factorized vs. joint multiview (Table 2c): KPM 45.8% → 94.4%, FVD 122.7 → 116.6, FID 15.8 → 16.4.
- Removing layout condition (Table 2a): FID 18.9 → 15.8 with full unified condition; KPM 44.6% → 45.8%.
- Reward ablation (Table 4): map-only avg L2 0.85 / coll 0.39%; object-only 0.80 / 0.27%; both 0.80 / 0.26%.

## Limitations & Open Questions
- Evaluated only on nuScenes (700 train / 150 val), open-loop L2 + collision metrics; no closed-loop CARLA / NAVSIM benchmark.
- Inference cost of running a multiview latent-video diffusion world model per planning candidate is not reported; tree-based rollout is unlikely to be real-time.
- Image-based reward depends on off-the-shelf 3D detector and HD-map predictor on synthesized frames — robustness to generation artifacts is not quantified.
- Planning tree is only three driving commands wide and uses VAD-sampled trajectories; broader action sampling and longer horizons are open.
- Authors note the model could in principle exploit foundation models (GPT-4V) on non-vectorized rewards, but this is not implemented.
