# AutoFrame 3D — recorded benchmark demo

The default page is a recorded benchmark stress-testing demo. Opening it, selecting examples, toggling benchmark ground truth, and downloading evidence do **not** run registration. The historical registration policy remains default; scan-to-model and reciprocal policies remain experimental.

From the repository root, use two PowerShell terminals with the existing environment:

```powershell
$env:AUTOFRAME3D_SKIP_DOTENV = '1'
.\.venv\Scripts\python.exe -B -m uvicorn autoframe3d.api:app --host 127.0.0.1 --port 8000
```

```powershell
npm run dev --prefix frontend -- --port 5173 --strictPort
```

Open **http://127.0.0.1:5173/**. The API serves local geometry using saved transforms; raw inputs are not packaged into the frontend bundle. Missing or mismatched local inputs produce a readable geometry message while recorded metrics and evidence remain available. No downloads or installations happen automatically. The old experimental workbench remains available only through `?workbench=1`; it can compute samples and is outside this recorded flow.

## Required assets and a fresh clone

The Python dependencies are declared in `pyproject.toml` (including Pillow for depth/mask images); frontend dependencies and lockfile are in `frontend/`. Launch commands above assume these dependencies already exist locally. Neither environments nor build output are versioned.

Metadata in `audit_evidence/recorded_benchmark_demo/` is versioned. **A fresh clone cannot show the complete 3D demo until T-LESS inputs are restored separately.** Under ignored `data/tless/bop/`, the required files are:

| Location | Files |
| --- | --- |
| `test_primesense/000001/` | `scene_camera.json`, `depth/000001.png`, `mask_visib/000001_000000.png` |
| `test_primesense/000002/` | `scene_camera.json`, `depth/000024.png`, `mask_visib/000024_000002.png` |
| `models_cad/` | `obj_000002.ply`, `obj_000007.ply`, `models_info.json` |
| `models_eval/` | `obj_000002.ply`, `obj_000007.ply` |

Expected hashes are in `demo.json`; geometry requests verify all of them before rendering. GT reveal uses saved benchmark poses, and scans use **GT instance masks**, not inferred segmentation. Optional replay additionally needs `scene_gt.json` in both scene directories and the unchanged `configs/tless_frozen.json`.

The existing setup utility is `scripts/tless_data.py`: `download` retrieves three explicitly named archives from `bop-benchmark/tless` at pinned revision `5fd309a04476a842d93abfb584fba9ee7caecdf1`; `extract` checks archive sizes/hashes against `data/tless/provenance.json` before extraction. Existing local archives can be extracted offline. The supported commands, **not executed for this checkpoint**, are:

```powershell
.\.venv\Scripts\python.exe -B scripts/tless_data.py download
.\.venv\Scripts\python.exe -B scripts/tless_data.py extract
```

Raw assets are neither bundled nor published here. The utility records dataset attribution and a license string; this checkpoint does not independently verify redistribution permission. Without restored assets, recorded metrics and evidence export remain usable, with an explicit unavailable-geometry message.

Choose example A, then reveal **Benchmark ground truth**. Choose example B and switch between the historical baseline and rejected reciprocal refinement. The comparison is recorded: RMSE decreases **4.37 → 3.73 mm**, but MSSD/D worsens **0.0853 → 0.1224**, crossing the unchanged **0.1** correctness threshold. Both poses remain geometrically accepted.

**Download recorded evidence** exports compact JSON for the selected case, including all its recorded methods, results, transforms, unchanged configuration, attribution, source/input hashes, and aggregate qualifications. It contains no raw scans, models, credentials, or executable reproduction script. Referenced versioned source records accompany the repository: the previously published eligibility results and the compact byte-identical `reciprocal_results.jsonl`. `COPY_MANIFEST.json` gives separate publication hashes; `demo.json` is a derived selection/join, not an original run artifact. Current publication hashes and Git identity do not establish historical execution provenance.

The expandable replay control runs **new local baseline computation** only after explicit confirmation; it does not overwrite the recorded display or replay experimental methods. Replay was mocked in the checkpoint tests and was not actually run. Optional live NVIDIA/Nebius integration remains unverified and is outside the recorded demo's claims.

## Ninety-second script

**0–15 seconds — problem.** “AutoFrame 3D investigates a specific failure: a CAD alignment can pass geometric checks while its pose is wrong. This is a benchmark stress-testing and replay tool, not a validated industrial pose estimator.”

**15–35 seconds — wrong alignment and reveal.** “This is a saved T-LESS case, not a live computation. Its fitness is 0.922 and RMSE is 1.79 mm, so the fixed geometric rules accept it. Reveal benchmark ground truth. Symmetry-aware MSSD divided by diameter is 1.4023, well above the 0.1 correctness threshold. Acceptance and correctness are separate decisions.”

**35–55 seconds — misleading improvement.** “Now the recorded correct control. Reciprocal refinement lowers RMSE from 4.37 to 3.73 mm, yet MSSD/D worsens from 0.0853 to 0.1224. The pose becomes incorrect. We rejected that experimental change rather than presenting a nicer fit score as better registration.”

**55–75 seconds — reproducible evidence.** “The corrected held-out aggregate is 24 accepted-and-correct and 176 accepted-but-wrong. Twenty-one affected records were rescored; 179 labels were carried forward. This was not a full independent rescore. Export the recorded evidence: case identity, saved poses, thresholds and provenance are inspectable.”

**75–90 seconds — limits and value.** “GT instance masks were used. These results concern this tested baseline and configuration. Local search showed no advantage over random search, and optional live model proposals remain unverified. The practical value is exposing misleading geometric success and preserving reproducible failure evidence.”

## Verification performed for this local checkpoint

- `$env:AUTOFRAME3D_SKIP_DOTENV='1'; .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_recorded_demo.py`: **6 passed in 4.08 seconds**. Coverage includes real local geometry and saved-transform round trips, comparison labels/export, missing/mismatched assets, missing curated evidence, versioned source/publication hashes, and mocked replay. Browsing tests prohibit registration/model calls. Asset-absent API behavior is tested; no actual fresh clone or clean dependency installation was performed.
- `npm run build --prefix frontend`: passed, Vite **6.11 seconds**. Existing bundle-size advisory: JavaScript bundle 760.64 kB before gzip. No dependencies installed.
- `node artifacts/recorded_demo_checkpoint_20261011/browser.cjs`: installed headless Edge exercised both examples, reciprocal selection, GT reveal and a successful evidence file download. Desktop screenshot inspected; a **390 px** viewport had a 390 px document width, with a rendered canvas. No console errors/exceptions, remote page requests, or POST/live-compute requests were observed. Browser used an isolated temporary profile/download directory. This is a smoke test, not full device/browser coverage.
- Current browser evidence is in ignored `artifacts/recorded_demo_checkpoint_20261011/`; prior verification artifacts are preserved. No new registration, benchmark, training, model call, download, or deployment was executed. Earlier reported checks are not substituted for the checkpoint results above.

Remaining submission considerations: 3D viewing needs separately restored local T-LESS assets; the compact evidence alone supports metrics-only viewing. Optional live integration is implemented but unverified and is not part of the demo claims. Hackathon eligibility requirements have not been supplied or verified; no competition outcome is claimed.
