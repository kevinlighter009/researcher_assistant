---
paper_id: 2020-waymo-open-dataset
title: "Scalability in Perception for Autonomous Driving: Waymo Open Dataset"
authors: [Pei Sun, Henrik Kretzschmar, Xerxes Dotiwalla, et al.]
year: 2020
venue: CVPR 2020
arxiv_id: "1912.04838"
url: https://arxiv.org/abs/1912.04838
primary_category: datasets
secondary_categories: [perception]
keywords: [waymo-open-dataset, lidar, multi-camera, 3d-detection, multi-object-tracking, domain-gap, pointpillars, aph]
one_line_summary: Large-scale multimodal driving dataset with 1150 20s scenes, 5 LiDARs + 5 cameras, ~12M LiDAR and ~9.9M 2D camera boxes; releases 3D detection/tracking baselines and a domain-gap study across SF/PHX/MTV.
distilled_at: 2026-05-02
source_pdf: doc/papers/datasets/waymo-open-dataset-2020.pdf
---

# Scalability in Perception for Autonomous Driving: Waymo Open Dataset

## Keywords
- waymo-open-dataset, lidar, multi-camera, 3d-detection, multi-object-tracking, domain-gap, pointpillars, aph

## TL;DR
Existing self-driving datasets (KITTI, nuScenes, Argoverse, ApolloScape) are limited in scale, sensor quality, or geographical diversity, making it hard to study generalization. The authors release the Waymo Open Dataset: 1150 scenes of 20 s each, recorded by 5 high-resolution LiDARs and 5 cameras across San Francisco, Phoenix, and Mountain View, with ~12M 3D LiDAR boxes and ~9.9M 2D camera boxes plus consistent track IDs. They also introduce a heading-aware AP variant (APH) and report PointPillars / Faster R-CNN / Tracktor baselines, plus an explicit cross-city domain-gap study.

## Problem & Motivation
Public AV datasets at the time were either small (KITTI: 22 scenes, 1.5 hours), single-region (most), or had low-quality LiDAR (nuScenes: 34K points/frame). None combined high-quality multi-LiDAR + multi-camera readings at scale across multiple geographies. This made it hard to (1) study cross-region generalization, (2) train data-hungry LiDAR models like LaserNet, and (3) evaluate sensor-fusion approaches that need accurate cross-modal synchronization.

## Innovation Points
- **Scale + sensor quality** — 1150 scenes, 6.4 hours, ~177K avg points/frame from 5 LiDARs + 5 1920x1280 cameras; 15.2x larger geographical coverage than the largest prior camera+LiDAR dataset.
- **Multi-city collection** — San Francisco, Phoenix, Mountain View, with explicit train/eval splits letting researchers quantify domain gap (cross-city APH drops of 7.6-19.8 documented).
- **Cross-modal label consistency** — exhaustive 7-DoF 3D LiDAR boxes and 4-DoF 2D camera boxes for vehicles, pedestrians, signs, cyclists; both share unique tracking IDs across frames, enabling fusion and tracking research.
- **APH metric** — average precision weighted by heading-error (min(|theta_hat - theta|, 2pi - |theta_hat - theta|)/pi), incorporating orientation accuracy into a familiar AP form.
- **Range-image LiDAR format** — releases LiDAR as range images with range/intensity/elongation/no-label-zone/vehicle-pose channels for the first two returns, encouraging research beyond raw point sets.
- **Tight LiDAR-camera synchronization** — rolling-shutter-aware projection with synchronization error bounded in [-6 ms, 7 ms] at 99.7% confidence.

## Model Architecture
This is a dataset paper; the "architecture" is the data-collection pipeline plus released baselines.

Sensor suite (per vehicle):
- 1 TOP LiDAR: VFOV [-17.6 deg, +2.4 deg], 75 m range, 2 returns/shot.
- 4 surround LiDARs (Front, Side-Left, Side-Right, Rear): VFOV [-90 deg, 30 deg], 20 m range.
- 5 pinhole cameras (Front, Front-Left, Front-Right, Side-Left, Side-Right): 1920x1280 (front trio) or 1920x1040 (side pair), HFOV +/-25.2 deg, rolling shutter, 10 Hz.
- Coordinate frames: Global (ENU), Vehicle, per-Sensor extrinsics, plus a LiDAR Spherical (range, azimuth, inclination) frame.

Annotation pipeline:
- Human labelers create 3D 7-DoF (cx, cy, cz, l, w, h, theta) LiDAR boxes for vehicles, pedestrians, signs, cyclists, with track IDs over the 20 s segment.
- Separate exhaustive 4-DoF 2D camera image boxes (cx, cy, l, w) with their own track IDs.
- Two difficulty levels (LEVEL_1 / LEVEL_2); LEVEL_2 includes hard examples or those with <=5 LiDAR points.

Released splits: 798 train + 202 validation + 150 test scenes; ~12M 3D objects, ~113K LiDAR track IDs, ~12M 2D camera objects, ~254K image track IDs.

Baselines:
- 3D detection: PointPillars (single-frame, all LiDARs, 512x512 BEV pseudo-image, voxel 0.33 m) for vehicles and pedestrians.
- 2D detection: Faster R-CNN with ResNet-101, COCO-pretrained, fine-tuned per-camera.
- 3D tracking: tracking-by-detection on PointPillars + Hungarian matching + Kalman filter (constant-velocity, 10-D state).
- 2D tracking: Tracktor on the fine-tuned Faster R-CNN.

## Benchmark Results

**3D detection baseline (PointPillars), LEVEL_1 / LEVEL_2 APH and AP, overall + by range:**

| Class      | View | Overall APH (L1/L2) | Overall AP (L1/L2) |
|------------|------|---------------------|---------------------|
| Vehicle    | BEV  | 79.1 / 71.0         | 80.1 / 71.9         |
| Vehicle    | 3D   | 62.8 / 55.1         | 63.3 / 55.6         |
| Pedestrian | BEV  | 56.1 / 51.1         | 70.0 / 63.8         |
| Pedestrian | 3D   | 50.2 / 45.1         | 62.1 / 55.9         |

(IoU thresholds: 0.7 vehicles, 0.5 pedestrians.)

**2D detection baseline (Faster R-CNN, ResNet-101):**
- Vehicle AP: 63.7 (LEVEL_1), 53.3 (LEVEL_2).
- Pedestrian AP: 55.8 (LEVEL_1), 52.7 (LEVEL_2).

**3D multi-object tracking baseline (PointPillars + Hungarian + Kalman), MOTA / MOTP overall (L1/L2):**

| Class      | MOTA (L1/L2) | MOTP (L1/L2) | Miss (L1/L2) | FP (L1/L2)    |
|------------|--------------|--------------|--------------|---------------|
| Vehicle 3D | 42.5 / 40.1  | 18.6 / 18.6  | 40.0 / 43.4  | 17.3 / 16.4   |
| Pedestrian | 38.9 / 37.7  | 34.0 / 34.0  | 48.6 / 50.2  | 12.0 / 11.6   |

Mismatch percentages are 0.14 / 0.13 (vehicles) and 0.49 / 0.47 (pedestrians) - very low, suggesting the IoU+Hungarian assignment is reasonable and most error is detection (recall / box shape).

**2D tracking (Tracktor, vehicles only):** MOTA 34.8 (LEVEL_1), 28.3 (LEVEL_2).

**Domain-gap study (3D LiDAR detection, LEVEL_2 APH on validation):**
- Vehicle, train SF -> eval SUB: APH drops 8.0 vs. train SUB -> eval SUB.
- Vehicle, train SUB -> eval SF: APH drops 7.6 vs. train SF -> eval SF.
- Pedestrian, train SF -> eval SF: training on ALL data costs 2.4 APH vs. SF-only; training on SUB-only and evaluating on SF costs 19.8 APH (limited pedestrian count in MTV+PHX).

**Dataset-size ablation (PointPillars, LEVEL_2 AP/APH on validation):**

| %-age      | 10%        | 30%        | 50%        | 100%       |
|------------|------------|------------|------------|------------|
| Vehicle    | 29.7/28.9  | 41.4/41.0  | 46.3/45.8  | 49.8/49.4  |
| Pedestrian | 39.5/27.7  | 45.7/35.7  | 50.3/40.4  | 53.0/43.0  |

Both classes still improving at 100%, supporting the "more data helps" motivation.

## Limitations & Open Questions
- No HD maps released (unlike nuScenes/Argoverse), limiting motion-forecasting / behavior-prediction research at release time; the authors flag map data as future work.
- LiDAR range restricted to 75 m for the TOP sensor and 20 m for surround LiDARs; only first two returns released.
- Cyclists and signs are annotated but baselines are reported only for vehicles and pedestrians.
- No semantic / instance segmentation labels; only object boxes.
- Domain-gap is only descriptive (SF vs. PHX+MTV); no method is proposed to close it - left as an open research direction.
- Weather diversity is limited; the paper notes adverse-weather data as future work.
