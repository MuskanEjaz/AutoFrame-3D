# AutoFrame 3D

**Break the pose before it breaks the robot.** AutoFrame 3D generates seeded synthetic CAD-to-scan registration experiments, measures alignment quality separately from true pose error, searches for accepted-but-wrong alignments, and exports cases that can be recomputed and replayed.

## Windows setup

Open PowerShell in the repository root. Python 3.10 or newer and Node.js 20.19+ or 22.12+ are required. The verified environment was Windows 11, Python 3.12.7, and Node.js 24.14.1.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
npm install --prefix frontend
```

Start the backend in one PowerShell terminal:

```powershell
python -m uvicorn autoframe3d.api:app --host 127.0.0.1 --port 8000
```

Start the dashboard in another:

```powershell
npm run dev --prefix frontend
```

Open <http://127.0.0.1:5173>. The local API health check is <http://127.0.0.1:8000/api/health>.

PowerShell may block local activation scripts. For that terminal only, either run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` before activation, or use `.\.venv\Scripts\python.exe -m pip install -e ".[test]"` and `.\.venv\Scripts\python.exe -m uvicorn ...` without activating.

## Core experiment

Run the successful full-visibility control:

```powershell
python -m autoframe3d.cli run --object near_symmetric --visibility all --seed 41 --yaw 0 --output artifacts/control
```

Run the fixed 12-registration deterministic search:

```powershell
python -m autoframe3d.cli search --budget 12 --output artifacts/search
```

The search command writes a mesh, scan, result/config/transforms/metrics, and environment metadata per case. Search results can be inspected in `artifacts/search/case-*/result.json`.

Run the end-to-end demonstration (one successful control, one failure, bounded simplification, export, and actual replay):

```powershell
python scripts/demo.py
```

## T-LESS Benchmark

The T-LESS benchmark is a **custom internal evaluation** on the public BOP19 PrimeSense test subset, not an official BOP score. Registration uses BOP-provided visible instance masks and is not end-to-end object detection. Dataset inputs and their pinned SHA-256 provenance are excluded from git; reviewable manifests, benchmark results, report, and one diagnostic overlay are retained.

Download only the pinned base metadata, CAD/evaluation models, and PrimeSense BOP19 test subset. CRCs/checksums and archive contents are recorded before extraction:

```powershell
python scripts/tless_data.py download
python scripts/tless_data.py inspect
python scripts/tless_data.py extract
```

Generate fixed scene-separated manifests and inspect the annotation-only CAD/depth overlay:

```powershell
python scripts/tless_benchmark.py manifests
python scripts/tless_benchmark.py diagnostic
```

Run the bounded smoke, frozen development tuning subset, and 200-case held-out evaluation:

```powershell
python scripts/tless_benchmark.py evaluate smoke20_frozen --group original --workers 1
python scripts/tless_benchmark.py evaluate development_tuning20 --group original --workers 1
python scripts/tless_benchmark.py evaluate heldout200 --group original --workers 1
```

Each command checkpoints JSONL results and can be rerun to resume without redoing completed cases. Original and additional noise/dropout scans are stored separately:

```powershell
python scripts/tless_benchmark.py evaluate heldout200 --group perturbed --limit 4 --workers 1
```

Run the separate equal-budget deterministic/seeded-random search comparison (the optional live arm requires `NEBIUS_API_KEY` in `.env` or the process environment):

```powershell
python scripts/tless_search.py
```

Run all eligible instances explicitly, only when the measured runtime fits your window:

```powershell
python scripts/tless_benchmark.py all --group original --workers 1
```

The measured held-out throughput estimated the full 6,562-instance original pass at about 2 h 20 min on this machine. The dashboard can browse completed T-LESS cases under the `T-LESS real` source; exports include dataset revision/license attribution and replay recomputes registration from the local source data. See [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md) for thresholds, detailed outcomes, per-object results, provenance, and limitations.

Run tests and build the dashboard:

```powershell
python -m pytest -q -p no:cacheprovider
npm run build --prefix frontend
```

## Optional live Nemotron mode

The deterministic mode works without credentials and is identified as such in the API/UI. To enable live model proposals, copy `.env.example` to `.env` and set `NEBIUS_API_KEY` there. Keep `.env` private; it is git-ignored. `NEBIUS_MODEL` defaults to `nvidia/Nemotron-3_5-Lightning` and can be overridden server-side. Restart the API after changing environment values. The credential was not available during this implementation, so live requests and model usage remain unverified. The backend validates strict JSON-schema output, permits at most four model calls and 12 total campaign registrations, and never executes generated code or shell commands.

Official references checked 2026-09-27:

- [Nebius Token Factory quickstart](https://docs.tokenfactory.nebius.com/quickstart): OpenAI-compatible base URL `https://api.tokenfactory.nebius.com/v1/`.
- [Nebius structured JSON output](https://docs.tokenfactory.nebius.com/ai-models-inference/json.md): `response_format` supports strict JSON schema on compatible models.
- [Nebius current model catalog](https://tokenfactory.nebius.com/models): lists the default model ID `nvidia/Nemotron-3_5-Lightning`.

## Architecture

- `autoframe3d/geometry.py`: procedural CAD-like meshes, area-weighted seeded surface sampling, rigid transforms, and declared rotational-symmetry-aware pose error.
- `autoframe3d/experiment.py`: partial scan generation and the ground-truth-blind fixed-yaw-sweep plus point-to-point ICP baseline. A candidate grid and iteration limit make work bounded and reproducible.
- `autoframe3d/agent.py`, `campaign.py`, `simplify.py`: strict bounded proposal schema, optional server-side Nebius requests, equal-budget seeded-random comparison, deterministic fallback, and greedy failure-preserving simplification.
- `autoframe3d/cases.py`: self-contained ZIP case bundles and replay that regenerates and re-registers rather than loading saved measurements as results.
- `autoframe3d/api.py`: FastAPI health/scenario/job/campaign/case endpoints. Registrations run on worker threads; the React client polls progress and requests cancellation between evaluations.
- `autoframe3d/tless_adapter.py`, `tless_metrics.py`, `tless_benchmark.py`, `tless_cases.py`, `tless_search.py`: BOP depth/model units, GT-masked adapter, symmetry-aware MSSD, fixed manifests, resumable results, attribution-bearing exports/replay, and separate bounded search comparison.
- `frontend/src/`: React/TypeScript dashboard and direct Three.js CAD/scan view.
- `tests/`: focused geometry, classification, budget, API, schema, and replay tests.

## Scientific assumptions and limitations

Coordinates are right-handed metres. Scan arrays are in the generated world/sensor frame; homogeneous transforms use column-vector convention, and a transform named `T_object_from_scan` maps scan-frame coordinates into object CAD coordinates. Registration estimates the CAD-from-scan transform. Its initializer is computed only from scan/CAD geometry: a fixed 30-degree yaw grid, centroid alignment, and then point-to-point ICP, capped at 20 iterations. It is not initialized from ground truth or from an intentionally wrong pose.

Acceptance is fixed before searching: fitness >= 0.70 and inlier RMSE <= 0.075 m. An accepted pose is wrong if translation error > 0.08 m or rotation error > 12 degrees. Fitness is the fraction of scan points with a CAD neighbor within 0.18 m; RMSE uses those inliers. These are **alignment quality metrics**, not calibrated confidence probabilities. Synthetic geometry, noise, visibility, and the acceptance limits do not establish real sensor or production-system behavior.

The supplied objects include a small asymmetric side feature and an asymmetric control. Their declared exact rotational symmetry order is one. The pose-error API can minimize over a declared integer-order rotational symmetry about object Z; no undeclared approximate symmetry is discounted. The simplified failure is only the simplest found by the recorded bounded greedy procedure, not a mathematical minimum. The measured 6-vs-6 seeded search comparison found six failures per arm and no deterministic-agent advantage; search performance should not be inferred from this small fixture.

Background points are uniform synthetic outliers. The registration is a classical point-to-point ICP baseline, not a substitute for production CAD registration, robust feature matching, sensor calibration, or uncertainty estimation. Meshes are procedural test objects, not imported customer CAD.

## Status

Completed implementation and measured results are tracked in [PROJECT_STATUS.md](PROJECT_STATUS.md) and [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md). Known blocker: live Nebius calls need the user's API key. Browser rendering, responsive layout, and interaction checks are performed against the running local app where available; see the status file for checks actually run.
## Corrected historical scoring audit

The saved held-out run originally reported **23 accepted-and-correct and 177 accepted-but-wrong**. A subsequent independent scoring audit corrected one label after fixing BOP symmetry translations from millimetres to metres: **24 accepted-and-correct and 176 accepted-but-wrong (88.0%)**. Registration estimates and geometric acceptance did not change.

The audit rescored all 21 affected held-out records and carried forward 179 unaffected labels, including three independently checked controls. This was **not a full independent rescore**. Audit provenance does not establish the original execution source identity. Historical reports and result files retain their original values; use the separate [audit evidence](audit_evidence/symmetry_scoring_audit_20261011_02a10626368f/README.md) for corrected scoring.

The repository includes source, tests, frozen configuration, bounded manifests, compact historical results, and portable audit evidence. Raw dataset/model files, downloaded archives, local environments, backups, and bulk generated inventories/summaries remain local. Reproduction commands requiring those inputs need the separately restored dataset; no new benchmark or test execution was performed while preparing this publication.

## Development search and eligibility findings

The [development pilot](audit_evidence/development_search_pilot_20261011T051807Z_289be02e/README.md) did not demonstrate added value over random search. Both tested local policies were feedback-free; all five starting poses were already accepted-but-wrong. Four candidates per case/seed/method were predeclared, giving 60 evaluations per method within the permitted maximum of 150. All planned slots ran. Deterministic search included **15 no-op candidates; random included none**, so equal call budgets did not provide equal perturbation coverage. Rediscovering those failures is not evidence of failure induction or an adaptive agent.

The [fresh eligibility audit](audit_evidence/development_eligibility_audit_20261011T053002Z_963a0a93/README.md) found **1 accepted-and-correct and 29 accepted-but-wrong** cases among 30 outcome-independent, balanced development selections, with no operational failures. This verified pool is insufficient for the proposed five-case pilot, but does not prove the full development split lacks five eligible starts. Future correctness-selected experiments measure robustness **conditional on initial success**, not unconditional failure rate or generalization performance. These evaluations use ground-truth instance masks and ground-truth-dependent correctness labels.

The perturbation replay/export repair preserves saved parameters and exports the perturbed scan. Replay verification (a no-op baseline repeat) and four focused mocked tests passed as previously recorded; they were **not rerun for this publication**. These findings do not establish improved registration accuracy. Original artifacts, historical reports and frozen configuration remain unchanged.
