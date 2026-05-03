---
paper_id: 2024-carllava
title: "CarLLaVA: Vision language models for camera-only closed-loop driving"
authors: [Katrin Renz, et al.]
year: 2024
venue: "arXiv (CARLA Autonomous Driving Challenge 2024 — Outstanding Champion & Innovation Award)"
arxiv_id: "2406.10165"
url: https://arxiv.org/abs/2406.10165
primary_category: vla
secondary_categories: [e2e_planning]
keywords: [vla, llava-next, camera-only, carla-leaderboard-2, semi-disentangled-output, llama-decoder, closed-loop]
one_line_summary: Camera-only VLM driver built on LLaVA-NeXT vision encoder + LLaMA decoder with a semi-disentangled path/waypoint output; first place on CARLA Leaderboard 2.0 sensor track.
distilled_at: 2026-05-02
source_pdf: doc/papers/vla/carllava-2024.pdf
---

# CarLLaVA: Vision language models for camera-only closed-loop driving

## Keywords
- vla, llava-next, camera-only, carla-leaderboard-2, semi-disentangled-output, llama-decoder, closed-loop

## TL;DR
Most CARLA Leaderboard entrants rely on LiDAR and expensive auxiliary labels (BEV semantics, depth, segmentation). The authors build CarLLaVA, a camera-only driving model that reuses the LLaVA-NeXT vision encoder (CLIP ViT-L-336px with `anyres` patching) and a LLaMA-style transformer decoder, predicting a semi-disentangled output of space-conditioned path waypoints (lateral) and time-conditioned waypoints (longitudinal). It ranks first on the CARLA Autonomous Driving Challenge 2.0 sensor track, beating the previous SOTA by 458% in Driving Score (5.18 → 6.87) and the best concurrent submission by 32.6%.

## Problem & Motivation
- Top CARLA Leaderboard 1.0 entries rely on LiDAR and expensive auxiliary labels (BEV semantics, depth, semantic segmentation), which are hard to obtain at scale on real cars and obstruct sim-to-real transfer.
- Prior closed-loop CARLA methods using foundation models (DriveMLM, LMDrive) either use customized encoders or focus on instruction following rather than pure closed-loop driving performance.
- Standard CLIP/LLaVA input resolution (336×336) is too low to perceive distant traffic lights and small pedestrians needed for safe driving.
- Common output choices are flawed: predicting raw control performs worse on collision avoidance, while pure waypoint outputs perform poorly in turns; existing fixes (e.g. Interfuser) require hand-designed heuristics.

## Innovation Points
- **Camera-only, label-free recipe** — drops LiDAR and all auxiliary labels (BEV, depth, segmentation), relying only on camera frames and trajectories; a top Leaderboard 2.0 entry built without these crutches.
- **LLaVA-NeXT `anyres` patching for high-res driving input** — splits each front view into multiple 336×336 patches encoded independently by CLIPViT-L-336px, then concatenates feature maps to recover small-object detail (traffic lights, distant pedestrians).
- **Semi-disentangled output representation** — predicts space-conditioned path waypoints (used by a PID for steering) plus time-conditioned waypoints (used by a PID for throttle/brake); decouples lateral from longitudinal control and improves turn behavior.
- **Bucketed training recipe** — partitions the 2.9M-sample dataset into six interest buckets (acceleration/stop, steering, vehicle hazards, stop sign / red light / walker, swerving, and a small uniform bucket); reduces samples per epoch to 650K and avoids wasting compute on trivial straight-line driving.
- **Learnable path/WP queries on a LLaMA decoder** — additional learnable queries (20 path, 10 WP) attend to the visual token stream; an MLP on top emits waypoint differences whose cumulative sum gives final waypoints, supervised with MSE.
- **Optional language commentary head** — auto-regressively generates driving commentary (e.g., "ego vehicle remains stopped due to a pedestrian crossing"), trained with rule-based expert labels and a standard LM loss.

## Model Architecture
- Inputs: front camera (split into two 336×336 patches via LLaVA-NeXT `anyres`); optional rear camera (variant C2T1) and 1-step temporal history (variant C1T2); next two GPS target points; ego speed.
- Vision encoder: LLaVA-NeXT CLIPViT-L-336px (~305M params), each patch encoded independently and concatenated spatially; flattened then downsampled (halves token count) and linearly projected into the LLM embedding space.
- Conditioning tokens: target points (MLP + normalization) and ego speed (MLP) appended; per-camera and per-timestep encodings added in C2T1 / C1T2.
- Decoder: LLaMA architecture (configurations tested: LLaMA-50M, LLaMA-350M from scratch, and 1B TinyLLaMA with QLoRA); 20 learnable path queries and 10 learnable waypoint queries attached.
- Output heads: per-query MLPs producing waypoint differences; cumulative sum yields final 20-step path (space-conditioned) and 10-step waypoints (time-conditioned).
- Controllers: separate PID controllers — path → steering (lateral); waypoints → throttle/brake (longitudinal).
- Optional language head: auto-regressive sampling using the Tiny-LLaMA tokenizer/LM-head after the path/WP outputs.
- Training: 2.9M samples at 5 fps from CARLA Town 12/13 expert PDM-Lite; 30 epochs (~650K effective samples per epoch via bucket sampling); AdamW, lr 3e-5 cosine, weight decay 0.1; DeepSpeed v2 on 8×A100 40GB; the base C1T1 configuration trains in ~27 hours.
- Total params: 350M–1.3B across configurations.

## Benchmark Results
**Headline — CARLA Leaderboard 2.0 (sensor track):**

| Method        | Sensors | Aux. Labels        | DS ↑ | RC ↑  | IS ↑ |
|---------------|---------|--------------------|------|-------|------|
| TF++          | L+C     | SS, D, OD, BS      | 5.18 | 11.34 | 0.48 |
| CaRINA hybrid | L+C     | IS, OD             | 1.23 | 9.56  | 0.31 |
| Zero-shot TF++| L+C     | SS, D, OD, BS      | 0.58 | 8.53  | 0.38 |
| CARLA baseline| priv.   | priv.              | 0.25 | 15.20 | 0.10 |
| **CarLLaVA**  | **C**   | **—**              | **6.87** | **18.08** | **0.42** |

CarLLaVA outperforms the previous SOTA by 458% in DS and the best concurrent submission by 32.6% (per abstract). Leaderboard variance: re-submitting the C1T1 model three times under early-stopping thresholds 2100 / 2400 yielded mean DS 5.87 ± 0.81 and 5.8 ± 0.87 respectively.

**Ablations (Tab. 2 — DS on Leaderboard):**
- Output representation (Tab. 2a): waypoints-only 3.21 DS (collisions w/ static layout = 0.68); +Path 4.49 DS (collisions = 0.0).
- Vision encoder (Tab. 2b): LLaVA pretrained 6.87; LLaVA from scratch 0.45; ResNet-34 ImageNet 2.71 → confirms the value of internet-scale VL pretraining.
- Early-stopping distance (Tab. 2c): 1300m → 3.93; 1800m → 4.49; 2100m → 6.87 (default); 2400m → 6.35.

**Ablations (Tab. 3 — DS_S on 10xShort local benchmark):**
- Scale (Tab. 3a): 50M → 90.40; 350M → 92.49; 1B pretrained + LoRA → 90.03; 1B from scratch + LoRA → 89.57.
- Input variants (Tab. 3b): default 90.40; +temporal 90.37; +back camera 88.81; –pretraining 75.43.

Failure cases: most common are rear-end collisions, partly addressed by the temporal C1T2 variant; merging at high speeds remains hard.

## Limitations & Open Questions
- Evaluated only in CARLA simulation (Leaderboard 2.0 + 10xShort); no sim-to-real or real-vehicle results reported.
- Inference cost / latency for the 350M–1.3B models on a vehicle compute budget is not reported.
- Adding rear camera or temporal history did not improve overall DS_S despite clear qualitative improvements — suggests the output supervision and scoring metric are not fully aligned with these signals.
- Language commentary is generated post-hoc and "not always aligned with the actions the model takes"; commentary as actual grounded explanation is left for future work.
- Scaling to 1B with LoRA underperforms the 350M dense model; the authors attribute this to undertuned hyperparameters and suspect proper full fine-tuning would help, but this is unverified.
- Bucket sampling is hand-designed (six rule-based buckets); generalizing data curation beyond CARLA scenarios is open.
