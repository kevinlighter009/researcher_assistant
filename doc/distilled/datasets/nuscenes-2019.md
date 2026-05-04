---
paper_id: 2019-nuscenes
title: "nuScenes: A multimodal dataset for autonomous driving"
authors: [Holger Caesar, Varun Bankiti, Alex H. Lang, Sourabh Vora, Venice Erin Liong, Qiang Xu, Anush Krishnan, Yu Pan, Giancarlo Baldan, Oscar Beijbom]
year: 2019
venue: CVPR 2020
arxiv_id: "1903.11027"
url: https://arxiv.org/abs/1903.11027
primary_category: datasets
secondary_categories: [perception]
keywords: [nuscenes, multimodal, lidar, radar, 3d-detection, 3d-tracking, av-benchmark, nds]
one_line_summary: First public AV dataset with full 360-degree surround sensor suite (6 cameras, 5 radars, 1 lidar) and 1.4M 3D box annotations across 1000 scenes; defines NDS detection metric and tracking baselines.
distilled_at: 2026-05-02
source_pdf: doc/papers/datasets/nuscenes-2019.pdf
---

# nuScenes: A multimodal dataset for autonomous driving

## Keywords
- nuscenes, multimodal, lidar, radar, 3d-detection, 3d-tracking, av-benchmark, nds

## TL;DR
Prior 3D driving benchmarks (KITTI, H3D) provided either limited camera/lidar coverage or no radar, making it hard to study the full sensor stack a real AV uses. The authors release nuScenes: 1000 20-second scenes recorded in Boston and Singapore with 6 cameras, 5 radars, 1 spinning lidar, GPS/IMU, and human-annotated semantic maps, fully 3D-box labelled at 2 Hz (1.4M boxes, 23 classes, 8 attributes). They also introduce the nuScenes Detection Score (NDS) and AMOTA tracking metric, and report baselines (PointPillars, MonoDIS, OFT, Megvii) — top lidar method Megvii reaches 63.3 NDS / 52.8 mAP on the test set.

## Problem & Motivation
At the time of release, available AV datasets had clear gaps. KITTI offered only forward-facing stereo cameras and a single lidar with 200k boxes over 22 scenes; image-only datasets (Cityscapes, BDD100k, Mapillary Vistas) provided no range data; H3D was 360-degree but contained no radar and no map. None of them captured the *full* sensor configuration (lidar + cameras + radar + maps) that production AV stacks rely on, nor exhibited diverse weather, nighttime, and dense urban driving. Without such data, multimodal fusion methods could not be benchmarked fairly, attribute prediction (pedestrian pose, vehicle state) had no labels, and rare classes were severely under-represented. nuScenes was built to fill this gap.

## Innovation Points
- **First full-suite 360-degree AV dataset** — 6 cameras, 5 radars and 1 lidar fully synchronised, captured by an AV approved for public roads in two cities (Boston and Singapore).
- **Radar in a public AV benchmark** — at release, the only annotated AV dataset providing radar returns alongside lidar and camera, encouraging radar/sensor-fusion research.
- **Scale and diversity** — 1000 hand-curated 20s scenes, 1.4M 3D cuboids, 40k annotated keyframes, 23 object classes with 8 attributes; nighttime and rainy splits explicitly included.
- **Semantic and HD maps** — 11-layer human-annotated vector map (drivable area, lanes, crosswalks, stop lines, etc.) plus 10 cm-accurate localisation, enabling map-conditioned perception/prediction research.
- **nuScenes Detection Score (NDS)** — a single scalar combining mAP (computed by 2D centre-distance matching, not IoU) with five True-Positive errors (translation, scale, orientation, velocity, attribute), avoiding the brittleness of IoU on small objects.
- **AMOTA / sAMOTA tracking metrics** — recall-integrated MOTA variants to handle the difficulty of tracking on a much harder benchmark than KITTI.

## Model Architecture
This is a dataset paper; the "architecture" is the data-collection rig and annotation pipeline.

Sensor rig (Renault Zoe; identical setup in both cities):
- 6 cameras at 12 Hz, 1600x900, JPEG, 70-degree FOV (front/sides at 55-degree offsets) plus a 110-degree rear camera
- 1 spinning lidar, 32 beams, 20 Hz, 360-degree horizontal / -30-deg to +10-deg vertical, range <=70 m, ~1.4 M points/s
- 5 FMCW radars at 13 Hz, range <=250 m, 77 GHz, +/-0.1 km/h velocity accuracy
- GPS + IMU + AHRS at 1000 Hz, 20 mm RTK, 0.2-degree heading
- CAN bus exposed for velocities, steering, torque

Capture and curation pipeline:
- Drive planning: 84 logs, 15 h driving, 242 km, average 16 km/h, across diverse neighbourhoods, weather (sun/rain/clouds), and day/night.
- Localisation: offline HD lidar map plus Monte-Carlo localisation, achieving <=10 cm error.
- Sensor sync: each camera exposure triggered when the top lidar sweep crosses the camera FOV center, giving sub-frame cross-modal alignment.
- Scene selection: human curation of 1000 "interesting" 20 s windows targeting dense traffic, rare classes, dangerous situations, and varied weather/lighting; each scene gets a textual caption.
- Maps: high-resolution rasterised maps (10 px/m) plus an 11-layer vector map expansion.
- Annotation (Scale.ai): keyframes sampled at 2 Hz; for each keyframe every instance of 23 classes is given a 7-DoF cuboid (x,y,z,w,l,h,yaw), semantic class, attributes (visibility, activity, pose), and tracked across the scene if visible to lidar/radar; multiple validation passes ensure quality.
- Public release: detection (10-class subset) and tracking benchmarks, devkit, eval code, taxonomy, and database schema all open-sourced (CC BY-NC-SA 4.0).

## Benchmark Results

**3D Detection — nuScenes test set (Table 4):**

| Method     | Modality | NDS  | mAP  | mATE (m) | mASE (1-IoU) | mAOE (rad) | mAVE (m/s) | mAAE (1-acc) |
|------------|----------|------|------|----------|--------------|------------|------------|--------------|
| OFT        | Camera   | 21.2 | 12.6 | 0.82     | 0.36         | 0.85       | 1.73       | 0.48         |
| SSD+3D     | Camera   | 26.8 | 16.4 | 0.90     | 0.33         | 0.62       | 1.31       | 0.29         |
| MonoDIS    | Camera   | 38.4 | 30.4 | 0.74     | 0.26         | 0.55       | 1.55       | 0.13         |
| PointPillars | Lidar  | 45.3 | 30.5 | 0.52     | 0.29         | 0.50       | 0.32       | 0.37         |
| Megvii     | Lidar    | **63.3** | **52.8** | 0.30 | 0.25     | 0.38       | 0.25       | 0.14         |

(Image baselines OFT and SSD+3D were re-implemented by the authors; MonoDIS and Megvii are the top 2019 challenge submissions.)

**3D Tracking — val set (text):**
- sAMOTA: Megvii 17.9%, PointPillars 3.5%, MonoDIS 4.5%
- AMOTP: Megvii 1.50 m, PointPillars 1.69 m, MonoDIS 1.79 m
- Better detectors give better trackers; MonoDIS shows the lowest LGD despite low sAMOTA (image methods less likely to miss an object for long stretches).

**Ablations (Table 3, PointPillars val):**
- Lidar sweep accumulation: 1 sweep -> 31.8 NDS / 21.9 mAP; 5 sweeps -> 42.9 / 27.7; 10 sweeps -> 44.8 / 28.8 (with KITTI pre-train) — diminishing returns past 5 sweeps.
- Pre-training: KITTI 44.8 NDS, ImageNet 44.9, none 44.2 — pre-training source matters only marginally on a dataset of this size.
- Data scale: training PointPillars vs SSD+3D vs OFT at varying fractions of nuScenes (Fig. 6) shows PointPillars only pulls clearly ahead once a KITTI-sized fraction is exceeded, motivating the larger benchmark.

**Matching function:** with KITTI-style IoU matching, pedestrian and bicycle AP collapse to near 0, making class ranking impossible; centre-distance matching (2 m for TP metrics) keeps all classes scorable and changes the ordering between camera and lidar methods on thin objects (e.g. MonoDIS beats both lidar baselines on bicycle under CD).

## Limitations & Open Questions
- Severe class imbalance (1:10k between rarest and most common annotated class) — long-tail learning largely left to the community.
- Annotation rate of 2 Hz; faster motions (e.g. fine-grained pedestrian gait) require interpolation. Waymo Open Dataset later annotates at 10 Hz.
- Two cities only (Boston, Singapore); generalisation to other geographies, weather extremes, and right-/left-hand mixes not directly evaluated.
- No prediction/planning benchmark in the original release (added later as the prediction challenge); the paper itself only ships detection + tracking tasks.
- Radar baselines are absent — the authors note their preliminary PointPillars-on-radar study did not produce promising results, leaving radar-only and radar-fusion baselines as open work.
