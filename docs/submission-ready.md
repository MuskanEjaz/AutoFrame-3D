# AutoFrame 3D submission package

Prepared 2026-10-28. Local review candidate; no push, deployment, upload or
submission. [Current requirements](hackathon-requirements.md) and
[actual verification](final-release-verification.md) govern this package.
Public YouTube URL: **pending**. Judge access/test-build URL: **pending**.
Approved public repository URL/visibility: **owner confirmation pending**.

## Submission description

A geometrically accepted CAD-to-scan fit can still have the wrong pose.
AutoFrame 3D helps reviewers inspect that discrepancy: open two curated,
recorded T-LESS cases, compare saved methods and metrics, reveal benchmark
truth, and export the evidence. Registration inputs used GT instance masks;
correctness is scored against benchmark GT. Opening the viewer runs no fitting.

The experimental evidence copilot uses NVIDIA `nvidia/Nemotron-3_5-Lightning`
by default through Nebius Token Factory's server-side inference API. Nemotron
selects bounded read-only tools and explains retrieved cards; deterministic
application code validates IDs, citations, metrics, thresholds and provenance.
The model cannot modify registration. Scope notes remain separate from prose.
A synthetic gripper preview illustrates interpolation to a known reference,
with pause/reset/export; it is not learned pose recovery or hardware control.

The demonstrated value is reviewable evidence: an accepted-but-wrong pose,
a saved method whose RMSE improves while benchmark correctness worsens, and
exports that retain the distinction. Current inference is not verified without
a securely configured credential. Historical model results include omissions,
a separate unsupported gate claim, truncation and HTTP 401 failures. No broad
quality, industrial reliability or autonomous recovery claim is made.

## Track and tool role

Proposed track: **Best Apps and Agents**; final owner choice pending.
Physical AI is an alternative only if the team represents its inspection and
synthetic scope accurately. It has no physical hardware component. The script
below includes more than one minute of key inspection modules operating.
Token Factory provides actual optional inference, not frontend hosting.
NVIDIA Nemotron chooses tools/synthesizes; application logic supplies recorded
facts and rejects unsupported citations. Current runtime success remains a
submission dependency, not a box checked by installing the code.

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

## Reproducible judge setup

From an approved checkout root, keep `demo_assets/`, `audit_evidence/` and
`frontend/public/assets/`. Windows PowerShell:

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

Open <http://127.0.0.1:5173>. Recorded/synthetic views need no key or full dataset.
Use the [README walkthrough](../README.md#judge-walkthrough). Choose free ports
and a matching proxy if defaults conflict; never stop another checkout's service.
The [secure direct launcher](../scripts/run_release_validation.ps1) runs only the
approved diagnostic/three-item sequence, with no secret-file loading or retries.
Its captures need manual review, not merely an exit-code check. Do not distribute
a provider credential to judges; owners must arrange managed free access/test
instructions through the required judging period. A hosted plan is not yet established.

## Concrete tool feedback — prepared, not sent

- Nebius's named schema envelope worked in an earlier preserved integration;
  official structured-output examples mix bare schemas and named envelopes.
  Consistent examples and safe field-location errors would simplify diagnosis.
- The later two-item captures retain HTTP 401 and invalid_request_error, but
  provide no rejected parameter; no underlying authorization cause is proven.
  Status/category are useful without logging raw bodies or credentials.
- Nemotron selected evidence tools and produced supported numerical comparisons
  on one original dev-01 result. That answer omitted required recorded/GT scope.
  A separate answer treated configuration as measurement, so citations and
  schema validity must not be presented as factual verification.
- The fixed 1,200-token output budget produced a third-turn truncation on dev-13.
  We reject partial output and keep the failure, rather than calling it abstention.
  Model benchmarks do not establish this application's quality or latency.

## Submission-period contribution summary

Verified history includes saved-pose/Windows engineering handoff `8e539ac`,
transport diagnostics `02983c6`/`88a3e73`, named-envelope integration `588f514`,
recorded-scope/grounding work `8ea46fb`/`445444d`, recovered workflow/UI repairs
`61191f4`, and owner-approved MIT/submission wording `cf8b960`.
This release repairs completion scoring, uses the configured model in the
probe, rejects redirects, supplies bounded validation orchestration and expands
actual product verification and reproducible documentation.
Repository author names are Muskan Ejaz and Juwairiya-Haroon. Handoff records
identify Muskan as lead and Juwairiya as engineering contributor. Exact personal
contributions, eligibility and representative authorization need owner confirmation;
Git attribution alone is not proof. AI coding assistance was used in release
repair, tests and documentation. No invented individual contribution is assigned.

## License, evidence and owner actions

Original code: [MIT](../LICENSE), approved by both owners. Third-party licenses
and attribution remain separate. [Data permission review](data-permissions.md)
identifies the two T-LESS geometry bundles and unresolved governing-grant
question; no manufacturer/data permissions are inferred from project MIT.

Original histories: [three-item run](../audit_evidence/grounding_three_20261028/capture.jsonl),
[earlier standalone dev-01](../audit_evidence/evidence_grounding_20261028/capture.jsonl),
[later HTTP-401 run](../audit_evidence/grounding_two_20261028/capture.jsonl).
No capture, GT value, dataset identity or rubric was rewritten.

Priority owner actions: securely run the single bounded validation launcher
once and review all attempted answers; confirm data-distribution decision,
track/eligibility/representative and contribution disclosure; arrange approved
public repository/judge access; record/review/upload the 2:45 video and fill its
actual public YouTube URL; perform final owner submission review before the
verified deadline. None of those external actions was performed here.
