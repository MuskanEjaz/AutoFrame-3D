# AutoFrame 3D — recorded benchmark demo

The default page is a recorded benchmark stress-testing demo. Opening it, selecting examples, toggling benchmark ground truth, and downloading evidence do **not** run registration. The historical registration policy remains default; scan-to-model and reciprocal policies remain experimental.

From the repository root, use two PowerShell terminals with the existing environment:

```powershell
$env:AUTOFRAME3D_SKIP_DOTENV = '1'
Remove-Item Env:NEBIUS_API_KEY -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -B -m uvicorn autoframe3d.api:app --host 127.0.0.1 --port 8000
```

```powershell
npm run dev --prefix frontend -- --port 5173 --strictPort
```

Open **http://127.0.0.1:5173/**. The API serves bundled visualization geometry using unchanged saved transforms; no full dataset is required for recorded browsing. Missing or mismatched local inputs produce a readable geometry message while recorded metrics and evidence remain available. No downloads or installations happen automatically. The old experimental workbench remains available only through `?workbench=1`; it can compute samples and is outside this recorded flow.

## First-time Windows setup verification (2026-10-11)

An isolated Git export of commit `40937c9698a4e579694bb3415b7d7413ceb17ddf`
passed the corrected [README setup](README.md): `python -m venv .venv`, pip
upgrade, editable `.[test]` installation and fresh `npm ci --prefix frontend`.
The documented `py -3.12` command failed to discover the installed interpreter;
the README now checks and uses `python`, without requiring activation.

Tested: **Windows 11 x64 build 26200.0; Python 3.12.7; Node.js 24.14.1;
npm 11.11.0; pip 26.2.1; PowerShell 7.5.3**. Resolved runtime dependencies:
NumPy 2.5.4, SciPy 1.18.1, Pillow 12.3.0, FastAPI 0.143.0, Pydantic 2.14.0,
Uvicorn 0.54.0, huggingface_hub 2.2.0; locked frontend Vite 7.3.6.
`pip check` and the frontend production build passed. npm reported one existing
high-severity lockfile advisory; dependency-security remediation was outside this
installation check. The existing build-size advisory also remains.

The fresh API/frontend ran on documented ports 8000/5173, with dotenv disabled
and no Nebius key. Installed Edge verified API health, both bundled 3D examples,
GT reveal, baseline/reciprocal comparison, valid nonempty evidence download and
the disabled **Live analysis unavailable** state. Desktop and 390 px checks had
no console errors/exceptions, remote requests or POSTs. The export had no raw
dataset and imported its own application files. No inference or registration ran.

This verifies editable installation and launch **from a checkout**, including its
bundled geometry and evidence. It does not verify standalone wheel installation,
other Python versions or Linux compatibility. No runtime/dependency declaration
defect was found. Live Nebius/NVIDIA integration and model quality remain
**UNVERIFIED**. Local setup/browser evidence is preserved in ignored
`artifacts/install_check_40937c9/`, `artifacts/install_environment.json` and
`artifacts/install_runtime_results/`.

## Required assets and a fresh clone

The Python dependencies are declared in `pyproject.toml` (including Pillow for depth/mask images); frontend dependencies and lockfile are in `frontend/`. Launch commands above assume these dependencies already exist locally. Neither environments nor build output are versioned.

Metadata in `audit_evidence/recorded_benchmark_demo/` and two display geometries in `demo_assets/` are versioned. A clone includes both 3D examples. Geometry totals **1,259,164 bytes** compressed (946,182 + 312,982). Every CAD vertex/face and every positive GT-visible-mask depth pixel is retained; no decimation or sampling was performed. Object-frame CAD and camera-frame scans use metres. The runtime applies saved transforms from unchanged evidence. These assets are **visualization-only**, never benchmark scoring or replay inputs.

[Asset attribution and license evidence](demo_assets/ATTRIBUTION.md) preserve the authors' citation, change notice and CC BY-SA 4.0 terms. The [author's dataset page](https://cmp.felk.cvut.cz/t-less/) says CC BY 4.0, while the [author's toolkit dataset notice](https://github.com/thodan/t-less_toolkit/blob/master/LICENSE) says CC BY-SA 4.0. Both permit redistribution; the derived bundle preserves the stricter ShareAlike terms. Actual local ZIP directories contain no LICENSE/README/COPYING notices. Historical provenance is not rewritten. `demo_assets/manifest.json` records actual source hashes, mapping, parameters, counts, sizes and separate publication hashes.

Optional offline regeneration from an already extracted, user-supplied BOP root:

```powershell
.\.venv\Scripts\python.exe -B scripts/prepare_demo_assets.py --dataset data/tless/bop
```

Exactly four files per example are required, with hashes matching curated evidence:

| BOP-root location | Files |
| --- | --- |
| `test_primesense/000001/` | `scene_camera.json`, `depth/000001.png`, `mask_visib/000001_000000.png` |
| `test_primesense/000002/` | `scene_camera.json`, `depth/000024.png`, `mask_visib/000024_000002.png` |
| `models_cad/` | `obj_000002.ply`, `obj_000007.ply` |

No download occurs. Missing inputs name the path and required files. Output uses sorted compact float64 JSON and gzip level 9 with timestamp zero. Regeneration was byte-identical using the existing Python environment. Original full inputs, evaluation models, `models_info.json`, both `scene_gt.json` files, and frozen configuration are still required for separately authorized replay. Replay was not run here.

Choose example A, then reveal **Benchmark ground truth**. Choose example B and switch between the historical baseline and rejected reciprocal refinement. The comparison is recorded: RMSE decreases **4.37 → 3.73 mm**, but MSSD/D worsens **0.0853 → 0.1224**, crossing the unchanged **0.1** correctness threshold. Both poses remain geometrically accepted.

**Download recorded evidence** exports compact JSON for the selected case, including all its recorded methods, results, transforms, unchanged configuration, attribution, source/input hashes, and aggregate qualifications. It contains no raw scans, models, credentials, or executable reproduction script. Referenced versioned source records accompany the repository: the previously published eligibility results and the compact byte-identical `reciprocal_results.jsonl`. `COPY_MANIFEST.json` gives separate publication hashes; `demo.json` is a derived selection/join, not an original run artifact. Current publication hashes and Git identity do not establish historical execution provenance.

The expandable replay control runs **new local baseline computation** only after explicit confirmation; it does not overwrite the recorded display or replay experimental methods. Replay was mocked in the checkpoint tests and was not actually run. Live NVIDIA/Nebius integration is required for submission but remains unverified; its analysis does not change recorded registration results.

## Ninety-second script

**0–15 seconds — problem.** “AutoFrame 3D investigates a specific failure: a CAD alignment can pass geometric checks while its pose is wrong. This is a benchmark stress-testing and replay tool, not a validated industrial pose estimator.”

**15–35 seconds — wrong alignment and reveal.** “This is a saved T-LESS case, not a live computation. Its fitness is 0.922 and RMSE is 1.79 mm, so the fixed geometric rules accept it. Reveal benchmark ground truth. Symmetry-aware MSSD divided by diameter is 1.4023, well above the 0.1 correctness threshold. Acceptance and correctness are separate decisions.”

**35–55 seconds — misleading improvement.** “Now the recorded correct control. Reciprocal refinement lowers RMSE from 4.37 to 3.73 mm, yet MSSD/D worsens from 0.0853 to 0.1224. The pose becomes incorrect. We rejected that experimental change rather than presenting a nicer fit score as better registration.”

**55–75 seconds — reproducible evidence.** “The corrected held-out aggregate is 24 accepted-and-correct and 176 accepted-but-wrong. Twenty-one affected records were rescored; 179 labels were carried forward. This was not a full independent rescore. Export the recorded evidence: case identity, saved poses, thresholds and provenance are inspectable.”

**75–90 seconds — limits and value.** “GT instance masks were used. These results concern this tested baseline and configuration. Local search showed no advantage over random search. The new Nemotron copilot is tested with mocks; required live Nebius integration remains unverified. The practical value is exposing misleading geometric success and preserving reproducible failure evidence.”

## Historical recorded-demo checkpoint verification

- `$env:AUTOFRAME3D_SKIP_DOTENV='1'; .\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_recorded_demo.py`: **6 passed in 4.08 seconds**. Coverage includes real local geometry and saved-transform round trips, comparison labels/export, missing/mismatched assets, missing curated evidence, versioned source/publication hashes, and mocked replay. Browsing tests prohibit registration/model calls. Asset-absent API behavior is tested; no actual fresh clone or clean dependency installation was performed.
- `npm run build --prefix frontend`: passed, Vite **6.11 seconds**. Existing bundle-size advisory: JavaScript bundle 760.64 kB before gzip. No dependencies installed.
- `node artifacts/recorded_demo_checkpoint_20261011/browser.cjs`: installed headless Edge exercised both examples, reciprocal selection, GT reveal and a successful evidence file download. Desktop screenshot inspected; a **390 px** viewport had a 390 px document width, with a rendered canvas. No console errors/exceptions, remote page requests, or POST/live-compute requests were observed. Browser used an isolated temporary profile/download directory. This is a smoke test, not full device/browser coverage.
- Current browser evidence is in ignored `artifacts/recorded_demo_checkpoint_20261011/`; prior verification artifacts are preserved. No new registration, benchmark, training, model call, download, or deployment was executed. Earlier reported checks are not substituted for the checkpoint results above.

## Investigation copilot — Nebius × NVIDIA / Best Apps and Agents

Answer-quality evaluation now has a predeclared 15-question development set and
5-question reserved regression set. See [offline evaluation and training decision](audit_evidence/INVESTIGATION_EVALUATION.md)
for saved-response scoring, human-review requirements and bounded future live
capture. Evaluator fixtures are not Nemotron performance; no live model quality
has been measured.

The [official rules](https://nebiusglobalaihackathon.devpost.com/rules) require Nebius runtime usage and an NVIDIA model; these are submission requirements, not optional extras. Our route is Nemotron via Token Factory. A real runtime request has **not** been verified. Track selection does not establish overall eligibility or submission readiness. Recorded 3D portability is verified in a selected clean candidate using bundled assets; fresh dependency installation remains untested.

The new panel sends a request only when **Ask Nemotron · live inference** is clicked. GET availability checks do not invoke inference. Missing credentials show **Live analysis unavailable**, with no mock/cache fallback. Registration evidence stays recorded even when analysis is live. No registration, asset restoration, experimental ICP policy, or remote browsing is accessible to the copilot. It reads only versioned curated metadata and does not depend on the uncommitted adapter/audit changes.

Four allowlisted tools expose catalogue, case evidence, method comparison, and benchmark summary. Nemotron selects tools using a validated JSON action protocol over Chat Completions; this is an application-level tool dispatcher, not native SDK function calling. Up to **3 model turns / 6 tool attempts / 60 seconds**, **20 seconds per provider turn**, **1,200 output tokens**, and **32 KiB response bytes** are permitted; there are no retries. Invalid arguments/references, provider failures, and exhausted budgets return explicit error/incomplete states. Caller wait is bounded; a timed-out HTTP worker may finish afterward but cannot trigger retries or registration.

Numerical results, threshold comparisons, and recorded labels come from read-only deterministic tools and appear in authoritative evidence cards. Every model finding must cite retrieved stable IDs and distinguish observations, hypotheses, proposed checks, and limitations. **Schema/citation validity does not establish factual accuracy of prose.** Curated scope is two examples, not a searchable copy of the entire dataset. GT instance masks, benchmark GT, corrected **24/176** counts, and **21 rescored / 179 carried forward** qualifications remain explicit. No cache or mock runtime mode is shipped; test-injected providers are labelled mocked.

Provider configuration is server-side. `.env.example` contains an empty credential placeholder and the selected model. The existing API can load `.env` normally; setting `AUTOFRAME3D_SKIP_DOTENV=1` requires credentials already supplied through the server process environment. Do not put keys in frontend files, command-line arguments, or committed files. Endpoint is fixed to `https://api.tokenfactory.nebius.com/v1/chat/completions`; model defaults to **`nvidia/Nemotron-3_5-Lightning`**, configurable with `NEBIUS_MODEL` (NVIDIA Nemotron identifiers only). The model listing is verified against [Nebius's official model guide](https://github.com/nebius/token-factory-cookbook/blob/main/models/nemotron/README.md), endpoint/API usage against its [Chat Completions example](https://github.com/nebius/token-factory-cookbook/blob/main/api/api_native.ipynb), and `guided_json` plus `response_format: json_object` against its [guided JSON example](https://github.com/nebius/token-factory-cookbook/blob/main/guided_json.ipynb), inspected 2026-10-11. No SDK installation was needed: the shared existing urllib transport sends the equivalent JSON body. Account access, actual structured-output behavior for the selected Nemotron, latency, and factual model quality remain unverified.

Mocked verification commands:

```powershell
$env:AUTOFRAME3D_SKIP_DOTENV='1'
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_investigation.py tests/test_agent.py tests/test_recorded_demo.py
npm run build --prefix frontend
```

Current results: **30 tests passed in 3.40 seconds**; production build passed (**5.43 seconds**, existing bundle-size advisory). Tests cover invalid tools/cases/arguments, unknown or unretrieved citations, verdict-override rejection, provider absence/timeouts/output limits, tool/model/deadline budgets, known comparison values, and mocked API integration. No inference was made, and these are not model-quality results. Previous browser checks remain historical; current copilot results are below. The four-question factual rubric is `audit_evidence/investigation_evaluation.json`; use it for a separately authorized real-model evaluation rather than treating scripted mock responses as Nemotron evidence.

**Later live verification, explicit opt-in:** securely configure `NEBIUS_API_KEY` in the process environment using your local credential mechanism, set `NEBIUS_MODEL=nvidia/Nemotron-3_5-Lightning`, then run from the repository root:

```powershell
.\.venv\Scripts\python.exe -B scripts/investigation_smoke.py --live
```

This script does not load `.env`, and omitting `--live` sends no request. It runs one bounded investigation (at most three paid inference turns, six read-only tools, no retries) and prints only status, counters, current-input hashes, and validated evidence IDs. Exit 0 requires a completed response citing the recorded comparison. A failure must be investigated before claiming working live integration; even success is a connectivity/protocol smoke, not a factual-quality or eligibility certification. This command was **not** executed with `--live` during implementation. Assets do not need restoration for this metadata-only smoke.

## Current offline release verification (2026-10-11)

- **34 focused tests passed**: `tests/test_demo_assets.py`, `tests/test_recorded_demo.py`, `tests/test_investigation.py`, `tests/test_agent.py`. Use `--basetemp artifacts/release_pytest_<unique-name>` if the system temporary directory is restricted. Checks include saved-transform round trips, no registration/provider calls in recorded browsing, bundle corruption/missing errors, byte-identical local regeneration, and bounded mocked copilot behavior.
- `npm run build --prefix frontend` passed, with the existing JavaScript size advisory (764.33 kB before gzip). No dependencies were installed.
- A temporary candidate under ignored `artifacts/release_verification_20261011/candidate/` contains explicitly selected committed runtime/frontend/evidence/config files, release changes and the permitted display bundle. Experimental working-tree adapter/audit changes, datasets, backups, credentials and bulk artifacts were excluded. Its API imported from the candidate; its BOP directory did not exist, dotenv was disabled and no Nebius key was present. Existing Python dependencies and the generated production frontend were reused.
- Candidate focused tests also passed: **33 passed, 1 skipped** (the regeneration test correctly skips without a source dataset).
- Candidate headless Edge checks passed: metadata, both 3D examples, GT reveal, method comparison, valid nonempty JSON evidence download, and disabled inference with **Live analysis unavailable**. No POST occurred before interception.
- **Fixture-only checks:** CDP intercepted copilot availability and every investigation POST. Explicit `TEST FIXTURE` / `MOCKED ANALYSIS` responses checked all four questions, loading/disabled controls, duplicate prevention, cited-case/method navigation, provider timeout/error and HTTP failure presentation, and recovery. No production fake-success behavior was added. Backend failures are covered by mocked focused tests; browser fixtures do not verify a provider.
- Desktop (1440 px) and mobile (390 px) screenshots were inspected; mobile document width was 390 px. No console errors, exceptions or remote browser requests occurred. No concrete UI defect was found.
- Reusable browser harness: `node tests/browser_recorded_demo.cjs`. It expects isolated Edge CDP at `127.0.0.1:9224` and the candidate frontend/API proxy at `127.0.0.1:5180`. Override `AUTOFRAME_BROWSER_CDP`, `AUTOFRAME_BROWSER_URL`, or `AUTOFRAME_BROWSER_OUTPUT` for other local ports/output directories. Use a credential-free local API. Fixtures live in `tests/fixtures/investigation_browser.json`. Selection manifests, harnesses, results, screenshots and download are preserved under ignored `artifacts/release_verification_20261011/`.

This verifies selected release-file completeness and offline runtime behavior on this machine, **not** installation on a brand-new machine or model quality. Live Nebius/NVIDIA integration remains **UNVERIFIED**, blocked pending account support without a personal bank card. No inference, training, registration, benchmark rerun, deployment or push occurred. Submission readiness is not established.
