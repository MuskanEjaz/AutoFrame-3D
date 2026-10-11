# PoseBreak Benchmark Report

**Status:** custom internal evaluation on the public BOP T-LESS PrimeSense BOP19 test subset. This is **not an official BOP score**. Registration uses provided visible instance masks, so this is **registration evaluation with ground-truth instance masks**, not end-to-end detection.

## Synthetic Result Audit

The synthetic near-symmetric mesh bounds are **2.00 × 2.05 × 2.00 m**; the largest vertex-to-vertex distance is **2.8284 m**. Internal geometry and translations use metres. The pose transform is named `T_object_from_scan` and maps scan/world-frame coordinates into CAD/object coordinates; registration reports its inverse, `T_scan_from_object` in the experiment's original camera/world naming, as the estimated CAD placement. The synthetic evaluator alone compares the result against known truth.

For the reproducible failing control, the recorded alignment metrics were fitness **1.000** and inlier RMSE **0.05121 m**, while pose error was **0.24863 m / 67.65°**. RMSE/object-diameter = **0.01810 (1.81%)**. Every scan point found a CAD neighbor inside the **0.18 m** correspondence gate; that gate is **6.36% of object diameter**. The predeclared geometric acceptance limits were fitness >= **0.70** and RMSE <= **0.075 m** (2.65% of this object's diameter). Pose wrong was predeclared as translation > **0.08 m** or rotation > **12°**.

This discrepancy is expected for these metrics: fitness and RMSE measure local nearest-surface proximity, not global pose uniqueness. The top-visible partial scan is dominated by the round, approximately rotationally symmetric body; a large yaw/position error can still map its observed surface points close to some part of the full CAD surface. The maximum correspondence distance and RMSE threshold are permissive relative to this 2.83 m mesh, but they were fixed before the bounded search and were not relaxed to obtain this case. They are engineering demonstration thresholds, not calibrated confidence values. There is no unit mismatch: the same metre units are used by scan, CAD, ICP, thresholds, and pose error.

Initialization is ground-truth-blind: centroid placement plus a fixed 30° CAD-frame yaw grid, followed by point-to-point ICP. Candidate ranking uses only measured fitness and RMSE. The selected starting yaw for case 00 was **270°**; ground truth was not supplied to initialization, ICP, or candidate ranking. It is a coarse baseline, but it was not manufactured by seeding ICP with a known-wrong transform.

## Dataset And Adapter

Only the three requested archives were downloaded from Hugging Face via `huggingface_hub` at immutable revision `5fd309a04476a842d93abfb584fba9ee7caecdf1`, licensed **CC-BY-4.0**. All 15,958 ZIP members passed CRC verification before extraction; extraction was 940,996,842 bytes. The complete member inventory is in `data/tless/archive_contents.json`; compact source provenance and local SHA-256 checksums are in `data/tless/provenance.json`.

| Archive | Bytes | SHA-256 |
|---|---:|---|
| `tless_base.zip` | 49,597 | `dd70ca884b7c471a530a952f70c5ab2c212f3d2c2f371be86397442b97d70a7e` |
| `tless_models.zip` | 33,468,762 | `6a29c59766b8d2af05e62e71739f0ca7243ad81bc3c7f9a24925504a8cb37928` |
| `tless_test_primesense_bop19.zip` | 825,276,992 | `1a18f6bbfb5ac4ced8529f7a35225adfed88c0f62ef38067933e2b541ef1d00b` |

The adapter uses per-frame `scene_camera.cam_K` and `depth_scale`, not the root calibration. T-LESS frames are cropped 720×540 images; for scene 1/frame 1, per-frame principal point is (374.07, 255.72), versus (641.07, 507.72) in the root sensor calibration. The BOP format explicitly allows per-image intrinsics for such crops. Depth is camera-Z in uint16 units; `depth_scale=0.1` converts each depth unit to **0.1 mm**, then the adapter converts depth to metres and back-projects `(u,v,z)` through that frame's K. PLY CAD/evaluation model vertices and GT `cam_t_m2c` are millimetres and are converted to metres. Estimated pose is camera-from-object; the dashboard receives its inverse alongside the inverse GT transform so both CAD poses overlay the scan in the same camera frame.

Registration uses `models_cad` and BOP-provided `mask_visib` by image/GT-instance index. Evaluation uses the matching `models_eval` points and `models_info` diameter/symmetries. Registration inputs do not contain a GT pose. The evaluator reads `scene_gt` only after the estimate is fixed. A GT-only diagnostic overlay is saved at `data/tless/diagnostics/tless-s000001-i000001-g00-o02_gt_overlay.png`: projected CAD bounds are 65.3×67.8 px versus 64×65 px for the visible mask, with 3,348 valid mask/depth points. This verifies crop/intrinsic alignment for that case; it does not imply every CAD surface matches sensor depth. No GT-based alignment correction was applied.

## Frozen Protocol

The BOP19 target IDs were joined to `scene_gt_info` visibility metadata before registration outcomes were inspected. The fixed development manifest uses scenes 1–4; held-out uses scenes 5–20. `heldout200.json` has exactly 200 cases and zero overlap with development. The frozen configuration SHA-256 is **`ca60a2fe5c667bce40c85c75f11fc0e65d0f8db36281945f94b6dd422155577a`**.

Geometric acceptance was frozen at fitness >= **0.70**, inlier RMSE <= **0.010 m**, and maximum correspondence distance **0.015 m**. Fitness is the proportion of masked scan points within that surface distance; RMSE is over those inliers. The 15 mm correspondence gate matches the BOP dataset's documented 15 mm visibility tolerance used for `scene_gt_info`; the 10 mm RMSE limit is tighter than that gate, and the 70% minimum requires most visible-mask depth points to match. These are fixed internal engineering screens, not official BOP thresholds and not calibrated probabilities. Pose correctness is **BOP MSSD / object diameter <= 0.10** using BOP's discrete symmetries and continuous symmetry discretized to at most 1% diameter surface travel. All four categories, timeouts, and processing failures are recorded separately. Both accepted-but-wrong denominators are reported.

The baseline uses six geometry-ranked, maximum-geodesic-diverse starts from 24 proper PCA signed-axis/permutation alignments; each runs up to eight point-to-point ICP iterations on at most 3,000 uniform BOP evaluation-model points. Candidate ranking and geometric acceptance see only fitness/RMSE. The per-instance timeout is 30 seconds. The 200-case run used one CPU worker; no GPU or model training was involved.

## Results

The first 20-instance implementation smoke exposed a compute-budget problem: 12 valid, 8 timeouts, 0 processing failures; 11/12 valid were accepted-but-wrong and 1/12 accepted-and-correct. This unsuccessful run is retained at `data/tless/results/original/smoke20.jsonl`. Tuning used development scenes only. The tuned 20-case development set had 20 valid, no timeouts/failures, 19 accepted-but-wrong and 1 accepted-and-correct (75.5 seconds total).

The frozen 20-case smoke then had 20 valid, no timeouts/failures, **20 accepted-but-wrong**, median runtime **4.22 s**. The held-out 200-case evaluation had **200 valid**, **0 timeouts**, **0 processing failures**:

| Outcome | Count |
|---|---:|
| Accepted and correct | 23 |
| Accepted but wrong | 177 |
| Rejected and correct | 0 |
| Rejected and wrong | 0 |

Accepted-but-wrong / all valid = **177/200 = 88.5%**. Accepted-but-wrong / accepted = **177/200 = 88.5%** (all 200 passed geometric acceptance). Held-out median fitness was **0.9684**, median RMSE **0.00409 m**, median MSSD/D **0.7168**, and 90th-percentile MSSD/D **1.1268**. Median per-instance runtime was **1.14 s**; held-out wall time was **257.1 s**.

| Object | Valid | Accepted-but-wrong | Median MSSD / D |
|---:|---:|---:|---:|
| 1 | 18 | 18 | 0.833 |
| 2 | 9 | 9 | 0.778 |
| 3 | 12 | 12 | 1.037 |
| 4 | 15 | 14 | 1.046 |
| 5 | 3 | 3 | 0.664 |
| 6 | 3 | 3 | 0.607 |
| 7 | 12 | 9 | 0.166 |
| 8 | 3 | 1 | 0.094 |
| 9 | 15 | 10 | 0.120 |
| 10 | 6 | 6 | 0.820 |
| 11 | 4 | 4 | 0.529 |
| 12 | 4 | 4 | 0.145 |
| 13 | 6 | 6 | 0.916 |
| 14 | 6 | 6 | 1.038 |
| 15 | 6 | 6 | 0.159 |
| 16 | 6 | 6 | 0.814 |
| 17 | 6 | 2 | 0.077 |
| 18 | 4 | 4 | 0.962 |
| 19 | 8 | 8 | 1.048 |
| 20 | 8 | 8 | 0.907 |
| 21 | 6 | 6 | 0.965 |
| 22 | 6 | 4 | 0.396 |
| 23 | 8 | 7 | 0.318 |
| 24 | 8 | 8 | 0.154 |
| 25 | 2 | 2 | 0.633 |
| 26 | 2 | 2 | 0.850 |
| 27 | 4 | 1 | 0.067 |
| 28 | 4 | 4 | 0.908 |
| 29 | 2 | 0 | 0.044 |
| 30 | 4 | 4 | 1.040 |

Small per-object counts are descriptive only. Held-out per-case JSONL and CSV are `data/tless/results/original/heldout200.jsonl` and `.csv`; summary JSON records the config hash, environment, attribution, denominators, and per-object results. The 6,562-instance all-eligible manifest was not run. At the measured 1.284 s mean held-out throughput, a one-worker exhaustive original-scan pass is estimated at about **2 h 20 min**, excluding startup and filesystem variance.

## Search Comparison

On one fixed development accepted-correct start (`tless-s000002-i000024-g02-o07`), deterministic and seeded-random each received four perturbation evaluations with six registration starts each (24 starts per strategy), the same noise range [0, 5 mm], dropout range [0, 20%], and the same starting scan. Both discovered an accepted-but-wrong perturbation on evaluation **4/4**: discovery **1/1 starting case** for each. Measured arm runtime was 6.10 s deterministic and 3.45 s random. This is a one-start development comparison, so the timings/discovery rate do not establish superiority.

The optional live Nemotron arm is **pending**: `NEBIUS_API_KEY` was absent and **zero paid/model calls** were made. The implementation validates strict bounded JSON output and withholds GT pose, MSSD, and correctness labels from the live proposal feedback. Running the search does not train Nemotron or the registration model.

## Reproduction And Limitations

```powershell
python scripts/tless_data.py download
python scripts/tless_data.py inspect
python scripts/tless_data.py extract
python scripts/tless_benchmark.py manifests
python scripts/tless_benchmark.py diagnostic
python scripts/tless_benchmark.py evaluate smoke20_frozen --group original --workers 1
python scripts/tless_benchmark.py evaluate heldout200 --group original --workers 1
python scripts/tless_benchmark.py evaluate heldout200 --group perturbed --limit 4 --workers 1
python scripts/tless_search.py
```

Evaluation commands resume from JSONL checkpoints and can be rerun without repeating completed instances. To run all 6,562 eligible instances explicitly, use `python scripts/tless_benchmark.py all --group original --workers 1`; the measured runtime estimate is about 2 h 20 min. Dataset downloads/extractions are git-ignored; manifests, provenance, source, and reviewable result tables are retained.

Limitations: this is a small-budget PCA/ICP baseline with oracle visible masks, not detection or a production pose estimator. T-LESS CAD/sensor surface mismatch remains possible despite the checked overlay. The custom MSSD threshold is fixed but internal, and the 200 cases are from the public challenge test subset. Search-agent comparison has only one starting case; live Nemotron is unmeasured without credentials. The highest-value next step is a second, independent multi-start development campaign across more accepted-correct starts, then a stronger geometry-only global registration baseline (for example feature/RANSAC or robust correspondence registration) selected on development scenes only.