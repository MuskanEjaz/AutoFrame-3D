# AutoFrame 3D — copy-ready submission fields

Updated 2026-10-30 from source, Git history and saved results. The earlier
release is already merged into main; this presentation update is on the release
branch. No Devpost form, video upload, deployment or automatic merge is performed.
[Requirements](hackathon-requirements.md) · [Evidence](final-release-verification.md)

## Project title

AutoFrame 3D

## Short tagline

Inspect the evidence behind a good geometric fit at the wrong pose.

## Inspiration

A low geometric residual can look reassuring even when an object's pose is
wrong. Registration reviewers need to distinguish a fit threshold from evidence
of pose correctness. We built an inspection workflow that places saved geometry,
metrics, ground truth and provenance together so those differences can be reviewed.

## What it does

AutoFrame 3D opens two curated recorded T-LESS cases, displays saved CAD/scan
alignments, compares available recorded methods, reveals benchmark ground truth
and exports the supporting evidence. One saved reciprocal refinement lowers
RMSE while worsening benchmark correctness. Opening the viewer runs no fitting.
A separate synthetic gripper workspace supports a known-reference preview,
pause/reset and state export. An experimental copilot can request bounded
read-only evidence and produce cited explanations; it cannot change registration.

## How it was built

The frontend uses React, TypeScript, Vite and Three.js. A Python/FastAPI backend
serves recorded geometry and metric cards. Deterministic code applies frozen
thresholds, retains source hashes, validates evidence IDs and exports records.
Pydantic schemas constrain investigation actions, while an offline evaluator
checks evidence, structured facts and trace integrity. Synthetic pose math and
classical registration experiments are separate from the recorded viewer.

## NVIDIA/Nebius usage

The configured default is NVIDIA `nvidia/Nemotron-3_5-Lightning`, called through
Nebius Token Factory's server-side chat-completions API. The model selects
approved catalogue, case, comparison and benchmark-summary tools, then explains
retrieved evidence or returns insufficient evidence. Application code controls
budgets and validates facts/citations; the model does not refit poses or read
arbitrary files. The key stays in the backend process. Investigations permit
at most three requests, six tools and 60 seconds, with no retries. Historical
calls are preserved; current grounded-answer quality remains unverified.

## Challenges

We had to separate geometric acceptance from benchmark-GT correctness, preserve
GT-mask dependence and distinguish a configured correspondence gate from a
measured metric. Schema/citation validity did not prevent scope omissions or
an unsupported gate claim in a separate answer. Other preserved failures were
an unavailable single-method comparison, truncation and HTTP 401; the latter's
underlying authorization cause is unresolved. A later user-run diagnostic
received one response but truncated at 128 completion tokens, so no investigations
ran. Full-suite research/raw-data failures and the T-LESS source-license
ambiguity remain explicit limitations rather than claimed fixes.

## Accomplishments supported by evidence

We demonstrated recorded case/method selection, geometry inspection, GT reveal,
evidence downloads and synthetic preview pause/reset/export in the actual
production UI. Desktop/mobile checks passed without console errors or remote
provider requests. The release-focused backend run recorded 122 passed and one
optional raw-data rebuild skipped; eight frontend tests and the production build
passed. Separate investigation-only repair checks recorded 122 relevant tests
passed. These are dated offline checks, not broad model-quality or full-suite
passes. We repaired completion scoring so unavailable comparison evidence cannot
satisfy a requested comparison, and added strict bounded validation orchestration.

## What we learned

Local geometric agreement and benchmark correctness answer different questions.
A correctly cited answer can still omit crucial recorded/GT qualifications.
Operational failure is not model abstention, and provider response receipt is
not valid output. Keeping frozen evidence, separate run histories and manual
prose review makes both successes and failures easier to assess.

## Future work

Complete the separately authorized bounded investigation validation and manual
review without retrying failed items; clarify the exact T-LESS source grant;
restore missing research fitting code and authorized raw-data reproduction;
then evaluate more representative cases before making broader capability claims.
Managed judge access and a compliant public video are immediate release tasks,
not features already delivered.

## Built With

Python, FastAPI, Pydantic, NumPy, SciPy, Pillow, React, TypeScript, Vite, Three.js,
NVIDIA Nemotron-3.5-Lightning, Nebius Token Factory, T-LESS/BOP recorded evidence.
The synthetic scene uses attributed Panda visual meshes and Poly Haven lighting.

## Judge testing instructions

From the approved Windows checkout root, install and launch the key-free views:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e '.[test]'
npm.cmd ci --prefix frontend
```

Backend terminal, with port 8000 free:

```powershell
$env:AUTOFRAME3D_SKIP_DOTENV='1'
Remove-Item Env:NEBIUS_API_KEY -ErrorAction SilentlyContinue
.venv/Scripts/python.exe -m uvicorn autoframe3d.api:app --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
npm.cmd run dev --prefix frontend -- --port 5173 --strictPort
```

Open <http://127.0.0.1:5173>. Select Recorded Benchmark, inspect case A and reveal
Benchmark ground truth. Select case B, switch recorded methods and download
evidence. Return to Pose Inspection; preview, pause, reset and export synthetic
state. Keep demo_assets/, audit_evidence/ and frontend/public/assets/ with the
checkout. No key/full dataset is needed for these views. Leave other services
untouched and use free ports with a matching proxy if necessary.

Live testing requires owner-managed access; do not distribute a provider key
to judges. The existing secure launcher with explicit `-InvestigationOnly`
selects only dev-01/dev-02/dev-13 once each, nine requests maximum, fresh output,
no retries and stops on operational rejection. It must not be rerun outside its
specific authorization. Review actual answers; an exit code is not a semantic
verdict. A managed judge-access URL/test build is still pending.

## Tool feedback

Nebius's structured-output examples should consistently show the accepted named
schema envelope. Sanitized HTTP status/category and field locations help diagnose
rejections without storing credentials or raw provider bodies. Nemotron selected
read-only evidence and produced supported numerical comparisons on the original
dev-01 result, but omitted recorded/GT scope. A separate response treated a
configured gate as measured. Truncation under the fixed token budget reinforced
the need to reject partial answers. We found strict local validation and manual
review necessary; provider benchmarks do not certify this application's quality.

## Significant hackathon-period updates

Git records Windows/saved-pose engineering handoff (`8e539ac`), provider diagnostics
(`02983c6`, `88a3e73`), named-envelope integration (`588f514`), evidence-scope and
grounding work (`8ea46fb`, `445444d`), recovered workflow/UI repairs (`61191f4`),
MIT/submission wording (`cf8b960`), stricter scoring and bounded orchestration
(`ceb5b60`), verified front page/product package (`dbb4208`), and explicit
investigation-only validation (`2f2ea0b`). This documentation update improves
presentation and copy-ready submission fields; it adds no application feature.
Repository authors are Muskan Ejaz and Juwairiya-Haroon; handoff records identify
Muskan as lead and Juwairiya as engineering contributor. Exact personal roles,
eligibility and representative authorization need owner confirmation. AI coding
assistance was used for release repair, tests and documentation.

## Links and declarations still requiring owner action

- Demo: [Watch the demo on Google Drive](https://drive.google.com/file/d/1qpVvW9SfT1RpIhEUCSIbKb80J4Md0DdW/view?usp=sharing).
  User-provided link; accessibility, duration and content were not verified.
- Required public YouTube URL: **pending**. Drive is not a substitute for the
  public YouTube upload required by the [official rules](https://nebiusglobalaihackathon.devpost.com/rules).
- Public source: [GitHub repository](https://github.com/MuskanEjaz/AutoFrame-3D).
  The previous release is merged into main; newer presentation changes require
  their own PR review before appearing on the default branch.
- Managed judge-access/test-build URL and testing availability: **pending**.
- Track choice (proposed Best Apps and Agents), team/representative/eligibility,
  final contribution disclosure and legal declarations: **owner confirmation pending**.
- Original code: [MIT](../LICENSE), approved by both owners. Third-party terms
  remain separate. [T-LESS permission review](data-permissions.md) identifies
  the unresolved governing-grant question for the two geometry bundles and
  recorded-geometry screenshots. No new permissions are asserted here.

## Reviewable narration plan

The plan below targets 2:45; it does not establish the actual Drive video's
length or content. If using Physical AI without hardware, show at least one
minute of key modules operating. Do not present interpolation as robot control.

## Demo script — 2 minutes 45 seconds

| Time | On-screen action and narration |
| --- | --- |
| 0:00–0:15 | Open Recorded Benchmark. “A low geometric residual can still hide a wrong pose. We make the evidence inspectable.” |
| 0:15–0:50 | Select A, orbit geometry, reveal Benchmark ground truth. “Fitness >=0.70 and RMSE <=10 mm define acceptance. MSSD/diameter <=0.10 defines benchmark correctness. GT instance masks were inputs and benchmark GT scores the pose.” |
| 0:50–1:25 | Select B; switch historical baseline/reciprocal; show comparison and download JSON. “Recorded RMSE falls from 4.37 to 3.73 mm while MSSD/diameter crosses 0.10. Both fits are accepted. This refinement is experimental, not promoted as a recovery.” |
| 1:25–1:45 | Open Pose Inspection; preview, pause, reset. “Known-reference synthetic interpolation only; no scanner acquisition, learned correction or physical robot control.” |
| 1:45–2:20 | Show preserved original three-item dev-01 capture clearly labelled recorded live output. “Nemotron through Token Factory selected read-only tools: three requests, two tools. Numerical RMSE comparison was correct; missing recorded-evidence and GT-mask/benchmark-GT qualifications remain defects. Other runs include a separate unsupported gate claim, truncation and later HTTP 401 failures. Current live validation remains unperformed.” Do not show offline fixtures as live. |
| 2:20–2:45 | Show key-free setup, exports, source/asset notices and limitations. “The contribution is evidence inspection and bounded explanation. We have not validated GT-free detection or autonomous recovery.” |

If an authorized new live run later succeeds, review its actual prose/cards and
label it separately before replacing the historical-output segment. Do not
substitute improved hand-authored text or omit a failed attempted item.
