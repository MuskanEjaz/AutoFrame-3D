# Juwairiya setup verification

Checked 2026-10-23. Workspace: `D:\University\AutoFrame\AutoFrame-3D`.
Muskan's handoff path is her machine's path, not a prerequisite.
Task 1 application reproduction is complete. The setup changes are available
locally on `juwairiya/setup`; no remote PR or push has been made. Cloning proves
read access, not that a collaborator invitation was accepted or write access exists.

## Source and environment

- PASS: cloned `https://github.com/MuskanEjaz/AutoFrame-3D.git`; fetched main
  is exactly `ccbb1045e9e0ca2205b948f1c887119f206dd398`.
- Working branch: `juwairiya/setup`. No committed AGENTS.md was found.
- Read README.md, DEMO.md, POSE_INSPECTION.md and docs/engineering-handoff.md.
- Windows 10 build 19045; Windows PowerShell 5.1.19041.6456;
  Git 2.51.0.windows.1; Python 3.11.9; Node 24.15.0; npm 11.12.1;
  environment pip 24.0. These differ from the lead's tested environment.
- `python` resolves to Python Install Manager and attempted a runtime download.
  Used the installed interpreter explicitly instead:

```powershell
& 'C:\Users\m\AppData\Local\Programs\Python\Python311\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
npm.cmd ci --prefix frontend --cache artifacts/npm-cache --no-audit --no-fund
```

PowerShell blocks npm.ps1 under the local execution policy. `npm.cmd` works
without changing that policy. Dependency downloads required network approval.
The first restricted npm attempt failed; the approved installation completed.
Editable installation creates `autoframe3d.egg-info/`; the setup change ignores
that generated metadata and the first attempt's local `.npm-cache/`.

## Verification

| Check | Result |
| --- | --- |
| Isolated editable Python installation | PASS |
| Frontend lockfile installation | PASS, 79 packages |
| pip check after installation | PASS |
| Frontend production build | PASS; existing >500 kB chunk advisory |
| Synthetic pose math/preview/reset tests | PASS, 5 tests |
| Focused backend checks below | PASS, 28 passed / 1 skipped |
| Running API `/api/health` | PASS, status ok, deterministic_only, api_key_configured false |
| Running frontend HTTP response | PASS, HTTP 200 |
| Visual examples, GT/method controls and downloads in browser | PASS, both bundled examples and valid downloaded JSON |
| Missing-key copilot state in browser | PASS, live analysis unavailable and inference button disabled |
| Synthetic replay, preview and reset in browser | PASS, including pause/resume and five-second endpoint |
| Desktop and 390px mobile layouts | PASS, screenshots inspected; no horizontal overflow |
| Live Nebius integration | BLOCKED: account, credits and explicit team usage approval unresolved |
| Raw T-LESS subset | Unavailable, as expected; no dataset download attempted |

Commands used after installation:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_demo_assets.py tests/test_recorded_demo.py tests/test_investigation.py tests/test_api.py::test_health_endpoint_discloses_live_or_deterministic_mode
node --test frontend/tests/pose.test.mjs
npm.cmd run build --prefix frontend
```

Backend tests exercise bundled geometry, recorded examples/evidence exports and
copilot behavior, including mocked provider behavior. They do not establish
live model quality. The skipped test is
`test_preparation_reproducible_and_matches_publication`: it requires the optional
raw source dataset to rebuild display assets. A targeted rerun with `-rs`
confirmed the reason (3 passed, 1 skipped); bundled asset checks passed.

## Browser evidence

An isolated headless Microsoft Edge 155.0.4283.62 session checked the real local
frontend/backend with no response interception, provider fixtures or API key.
Thirteen grouped checks passed. Both recorded examples rendered actual bundled
3D geometry. Ground-truth reveal and baseline/reciprocal controls worked; the
object 7 display changed from MSSD/diameter 0.0853 to 0.1224 and RMSE 4.37 to
3.73 mm. Both evidence downloads parsed as JSON containing saved case variants.

Synthetic preview progressed, paused without elapsed-time drift, resumed to
the known reference at five seconds, replayed and reset to the original mismatch.
Both the main scene and thumbnail rendered; initial/aligned screenshots were
inspected. Synthetic state export also parsed successfully. Desktop 1440x1000
and mobile 390x844 screenshots were inspected. No browser console errors,
uncaught exceptions, remote requests or POST requests were observed. A first
comparison screenshot was taken while geometry was loading; the harness was
tightened to wait for the canvas and rerun successfully before marking PASS.

Local evidence (ignored, not part of a commit):

- `artifacts/juwairiya-task1/results.json`: all check outcomes and browser identity.
- `artifacts/juwairiya-task1/*.png`: desktop/mobile screenshots.
- `artifacts/juwairiya-task1/*.json`: downloaded recorded and synthetic exports.
- `artifacts/task1-browser.cjs`: CDP check harness; run with `node` after launching
  an isolated Edge CDP session on port 9224 and the documented servers.

No application runtime defect was found. The only repository maintenance fix is
excluding generated install/cache files. Live inference is outside Task 1.

## Local launch

From this checkout, run in separate terminals:

```powershell
$env:AUTOFRAME3D_SKIP_DOTENV='1'
Remove-Item Env:NEBIUS_API_KEY -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m uvicorn autoframe3d.api:app --host 127.0.0.1 --port 8000
```

```powershell
npm.cmd run dev --prefix frontend -- --port 5173 --strictPort
```

Open http://127.0.0.1:5173. Both servers were started during verification.

## Next bounded work

Task 2: diagnose only the four frozen saved pairs in
`audit_evidence/saved_pose_reciprocal_20261014/`. Do not execute the refinement
runner. Compare current geometry ranking/acceptance to post-hoc GT scoring and
report unavailable diagnostics explicitly. Discuss findings with Muskan before
new algorithms or experiments. Organizer correspondence and the exact current
competition URL are needed for the access/eligibility task. No inference,
registration, benchmark rerun, paid usage, push or publication was performed.
