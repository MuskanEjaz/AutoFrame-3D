# PoseBreak Project Status

## Plan and environment

- M1: implement deterministic CAD-like geometry, synthetic scans, ground-truth-blind registration, bounded search, and reproducible CLI artifacts.
- M2: add the bounded experiment agent, optional Nebius integration, failure simplification, and a same-budget random-search comparison.
- M3: add the local API and responsive interactive dashboard with live experiment state.
- M4: make exported cases replayable, add focused tests and documentation, and verify the Windows run path.

Environment observed 2026-09-27: Windows 11 Pro x64, Python 3.12.7, Node.js 24.14.1, 0.6 GB free RAM, 15.1 GB free disk. NumPy, SciPy, FastAPI, Pydantic, pytest, and httpx are installed; Open3D is not. The implementation will use the installed NumPy/SciPy stack and avoid a GPU or local model.

## Milestone 1

Status: complete. Baseline hypothesis was confirmed by measured computation. The baseline uses a ground-truth-blind fixed 30-degree CAD-frame yaw sweep, centroid initialization, then point-to-point ICP (20 iterations maximum); ground truth is consulted only after registration for scoring. This is not an intentionally wrong initial pose.

Checks/results: `python -m pytest -q -p no:cacheprovider` passed (4 tests). The 12-evaluation deterministic search produced 12 accepted-but-wrong cases. Search case 00: fitness 1.000, inlier RMSE 0.05121 m, translation error 0.24863 m, rotation error 67.65 degrees. The clean accepted-correct control (`near_symmetric`, full visibility, yaw 0 degrees, seed 41) measured fitness 1.000, RMSE 0.04336 m, translation error 0.00686 m, rotation error 0.668 degrees. All thresholds were fixed before search: fitness >= 0.70, RMSE <= 0.075 m, translation error > 0.08 m or rotation error > 12 degrees classifies accepted-but-wrong. Both saved under `artifacts/` with mesh, scan, config, transforms, metrics, and environment metadata.

Nebius documentation checked 2026-09-27: official quickstart base URL is `https://api.tokenfactory.nebius.com/v1/`; current catalog lists `nvidia/Nemotron-3_5-Lightning` and `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`. Structured output uses `response_format` with `json_schema`. No API key has been checked or used yet.

## Remaining milestones

M2: complete in deterministic mode; live-call verification is credential-blocked. Proposals use strict Pydantic validation and are bounded to 4 model calls. Campaigns are capped at 12 registrations total, split evenly between the search arm and seeded-random arm. A real campaign measured 6/6 accepted-but-wrong cases in each arm; the deterministic arm did not outperform random. A real simplification used 4 evaluations and preserved the failure while setting noise to zero and reducing yaw/translation to zero. The result is described as the simplest found within the bounded greedy procedure, not a mathematical minimum.

Nebius live setup: official docs were checked at `https://docs.tokenfactory.nebius.com/quickstart`, `https://docs.tokenfactory.nebius.com/ai-models-inference/json.md`, and the live catalog `https://tokenfactory.nebius.com/models`. Base URL: `https://api.tokenfactory.nebius.com/v1/`. Default current Nemotron ID: `nvidia/Nemotron-3_5-Lightning`. No `NEBIUS_API_KEY` is configured, so no live request, API usage, or live model output has been claimed. To enable it, set `NEBIUS_API_KEY` in `.env` or the server environment; the model can be overridden with `NEBIUS_MODEL`.

M3: complete. The responsive React/Vite dashboard and Three.js viewer are running locally at `http://127.0.0.1:5173/`, with FastAPI at `http://127.0.0.1:8000/`. Controls cover sample load, baseline, stress campaign, stop, simplify, export, and replay. Geometry, estimates, ground truth, job state, action history, comparison results, errors, and progress are served by the API; there are no decorative result charts. The default viewer sample matches its top-visible, 23-degree scenario controls and reports measured results. Scan, estimate, and truth visibility toggles are wired to the Three.js scene.

M4: complete except live Nebius request verification. ZIP exports contain CAD OBJ, seeded scan XYZ, configuration, truth/estimate transforms, measured metrics/classification, environment metadata, and reproduction instructions. Replay regenerates and re-registers; numerical tolerances are fitness 0.03, RMSE 0.01 m, translation 0.02 m, rotation 2 degrees, with matching classification required. A real failure bundle replayed successfully with exact measured values on this environment.

## Final checks actually run

- `python -m pytest -q -p no:cacheprovider`: 29 passed.
- `npm run build --prefix frontend`: passed after final UI changes. Vite reports a >500 kB uncompressed JavaScript chunk due to Three.js; build succeeds.
- `python scripts/demo.py`: passed; produced an accepted-correct control, accepted-but-wrong partial scan, four-evaluation failure-preserving simplification, exported ZIP, and passing recomputed replay.
- `python -m posebreak.cli search --budget 12 --output artifacts/search`: 12/12 measured accepted-but-wrong cases, including reproducible `artifacts/search/case-00`.
- `run_campaign(budget=12, mode='deterministic')`: 12 registrations total; 6/6 failures in deterministic and 6/6 in seeded random. No performance advantage was measured.
- `GET /api/health`: 200, deterministic-only mode accurately disclosed, 12 registration / 4 model-call limits.
- Real asynchronous baseline through HTTP polling: completed, one serializable measured event, accepted-correct classification. Case detail and geometry routes also return JSON-safe transforms and regenerated points.
- Export/replay integration test and demo both passed; replay recomputed measurements rather than trusting the saved values.
- Browser opened the local dashboard and showed both the default accepted-but-wrong sample and a real T-LESS case. The T-LESS case rendered 3,348 masked scan points and its MSSD/D metrics; replay completed as “Replay verified.” WebGL pixel probes found nonzero geometry/background pixels at desktop (222,165 sampled pixels) and mobile (33,553 sampled pixels); mobile width 375 px had no horizontal overflow.
- Editor diagnostics: no errors in the checked backend modules or frontend source.

## Remaining setup

Live model calls require the user to set `NEBIUS_API_KEY` in `.env` or the process environment. No live request, token usage, or live-model result has been reported. The all-eligible 6,562-instance pass remains unrun; at measured held-out throughput it is estimated at about 2 h 20 min on one worker.

## T-LESS Benchmark (2026-09-28)

Dataset pinned to `bop-benchmark/tless@5fd309a04476a842d93abfb584fba9ee7caecdf1` (CC-BY-4.0). Only `tless_base.zip`, `tless_models.zip`, and `tless_test_primesense_bop19.zip` were downloaded; all 15,958 ZIP members passed CRC validation before safe extraction. Archive sizes/checksums are in `data/tless/provenance.json`, the full archive inventory is in `data/tless/archive_contents.json`, and raw dataset bytes are git-ignored.

The adapter uses per-image `cam_K`, depth scale 0.1 mm/unit, visible masks, CAD PLY and matching evaluation PLY. A GT-only overlay verified the projected CAD bounds and visible mask agree within about 1.3 px for the selected diagnostic frame. Registration receives no GT pose; evaluator-only symmetry-aware BOP MSSD uses GT after estimate selection. Development scenes 1–4 and held-out scenes 5–20 are disjoint.

The initial 24-start smoke was preserved: 20 attempted, 12 valid, 8 timeouts; 11 accepted-but-wrong and 1 accepted-and-correct among valid. After development-only compute tuning, frozen smoke20 was 20/20 valid, 0 timeouts/failures, 20 accepted-but-wrong. The held-out 200 ran once with config SHA-256 `ca60a2fe5c667bce40c85c75f11fc0e65d0f8db36281945f94b6dd422155577a`: 200 valid, 0 timeouts/failures, 23 accepted-and-correct, 177 accepted-but-wrong, 0 rejected; accepted-but-wrong is 88.5% of valid and 88.5% of accepted. Median fitness 0.9684, RMSE 4.09 mm, normalized MSSD 0.7168; 90th-percentile normalized MSSD 1.1268. Median runtime 1.14 s; total wall time 257.1 s. Exact per-object counts and all case records are in `data/tless/results/original/heldout200.*`.

Four additional perturbed cases are stored separately under `data/tless/results/perturbed/heldout200.*`; all four were valid and accepted-but-wrong. The development-only search comparison used one fixed accepted-correct start and four perturbations per arm: deterministic and seeded random both discovered a failure on evaluation four. This one-start comparison cannot establish superiority. Live Nemotron remains pending; no API key was configured and zero model calls were made.

Additional actual checks: `python -m pytest -q -p no:cacheprovider` passed 29 tests; `npm run build --prefix frontend` passed with the Three.js bundle-size advisory. The real dashboard lists T-LESS smoke/dev/held-out records, overlays estimated and GT poses in the camera frame, distinguishes BOP MSSD from synthetic pose errors, and exports/replays attribution-bearing T-LESS bundles. Live Nebius remains the only credential-dependent blocker. Full all-eligible evaluation was not run; measured throughput estimates roughly 2 h 20 min for 6,562 original cases at one worker.