# AutoFrame 3D submission brief

Prepared 2026-10-28. Local review candidate; no deployment, push or submission.

Grounding review and separate run records: [validation history](evidence-grounding-validation.md).
An earlier dev-01 completion compared metrics correctly but omitted GT limitations
and treated a configured matching gate as a measurement. A later run attempted
dev-02 and dev-13; both stopped at HTTP-rejection stages before evidence tools.
The deterministic panel scope note is separate from model prose. Updated prompt
quality remains unverified.

## Project and contributions

AutoFrame 3D demonstrates inspection of two curated, recorded T-LESS CAD-to-scan
cases where geometric acceptance and benchmark-GT correctness differ. The viewer
compares saved methods and exports evidence; it does not run fitting when opened.
Separate reproducible synthetic experiments and a synthetic animation are
additional workflows. The live Nebius explanation is experimental. The project
does not demonstrate automatic pose recovery, GT-free error detection, or
industrial reliability.

Team contributions and submission-period attribution: [TEAM MEMBERS, ROLES,
AND CONTRIBUTIONS — confirm with the team]. Historical repository work spans
research, engineering, recorded-data inspection and release preparation; final
individual attribution and coding-assistance disclosure require owner review.

## Three distinct demonstrations

| Surface | What actually happens | Limits |
| --- | --- | --- |
| Recorded Benchmark | Loads saved geometry, poses and metric cards; compares recorded methods and exports evidence | Opening it runs no fitting; GT instance masks and known object identity were inputs; correctness uses benchmark GT |
| Pose Inspection | Synthetic five-second interpolation toward a known reference | Visualization, not pose recovery or robot hardware control |
| Experimental live copilot | When provider calls complete, Nemotron may select read-only evidence tools and cite saved cards | No pose changes or registration; the latest dev-02/dev-13 attempt stopped at HTTP-rejection stages before evidence tools. Citations/schema do not prove prose correctness |

## Verified state and remaining blockers

The [reviewed earlier live capture and verification](../audit_evidence/live_integration_20261028/verification.json)
record dev-01 as complete: three model requests, two evidence tools,
12.3736 seconds; retrieval, citations, schema and structured numbers passed.
This is one item only, and its prose was incomplete.
At the time of that run, fourteen development items were unattempted; the
later two-item attempt is reported separately below. No overall model-quality pass.
The successful run used **88a3e73 plus an uncommitted named-envelope patch**,
not this later release commit. The original answer omitted the RMSE acceptance
criterion and GT-mask/GT-scoring dependence. The later [two-item run](../audit_evidence/grounding_two_20261028/capture.jsonl)
attempted dev-02 and dev-13 once each; both returned status=error after one
request, zero tools, at trace stage http_rejection. No HTTP status, provider
validation detail or token counters were captured. No findings were generated.
The rejected field/cause is unknown. Updated prompt quality remains
**UNVERIFIED**; evaluation expectations are unchanged.

Earlier failures remain local and hash-listed in that verification file.
Operator-confirmed diagnosis: malformed credentials contained control characters;
the named name/schema envelope resolved HTTP 422. Sanitized failure captures
alone do not identify the first HTTP-400 rejected field. Credentials now fail
locally before request construction and are never repaired or printed.
Budgets remain three model turns, six tools, 60 seconds total, 20 seconds per
request, 1200 output tokens per request; no retries or fallback answers.

Previously recorded implementation checks (not rerun for this documentation-only package):

| Check | Result |
| --- | --- |
| Focused investigation/shared transport/evaluator/recorded evidence/asset tests | 112 passed, 1 skipped (optional raw-dataset rebuild unavailable) |
| Production build (TypeScript + Vite 7.3.7) | Passed; existing >500 kB bundle warning remains |
| npm audit after compatible Vite 7.3.6 to 7.3.7 patch | Zero vulnerabilities reported |
| Prior diff whitespace validation | Passed |
| This offline package: JSON integrity, saved-file hashes, secret scan, local Markdown links, and `git diff --check` | Passed |
| New inference, registration, browser smoke, deployment or push | None |

The compatible Vite patch addresses the reported development-server advisories;
see [GHSA-587h-7wmj-h5pm](https://github.com/advisories/GHSA-587h-7wmj-h5pm),
which lists 7.3.7 as patched. Only Vite and its manifest/lockfile entry changed.

 Earlier Windows
setup/browser evidence remains historical in [setup verification](setup-verification.md)
and [live integration](live-integration.md); no new browser test or live run
was performed for this release follow-up. Standalone wheels, other operating
systems and historical fitting reproduction remain unverified/incomplete.

## Draft submission description

AutoFrame 3D demonstrates recorded inspection of curated T-LESS CAD-to-scan
cases where geometric acceptance and benchmark-GT pose correctness can differ.
The recorded viewer compares saved methods, exposes the GT-dependent evaluation
scope, and exports evidence. Separate reproducible synthetic workflows support
registration experiments. The animated robot view is a synthetic known-reference
preview, not pose recovery or hardware control. The live evidence copilot is
experimental; one dev-01 answer had prose omissions, and the latest dev-02/dev-13
attempts failed before evidence retrieval. No broad model-quality claim is made.

Submission fields: [TEAM CONTRIBUTIONS — pending confirmation]; [PROJECT LICENSE —
team decision pending]; [VIDEO LINK — pending]; [HOSTED/JUDGE ACCESS LINK — pending];
[OFFICIAL TRACK/FORMAT REQUIREMENTS — pending confirmation].

## Demo script (2 minutes 45 seconds)

| Time | Action and narration |
| --- | --- |
| 0:00–0:15 | Open Recorded Benchmark: “A good geometric fit can still be the wrong pose.” |
| 0:15–0:50 | Show example A: fitness >=0.70 and inlier RMSE <=10 mm define acceptance; normalized MSSD <=0.10 defines GT-scored correctness. Reveal GT; disclose GT instance masks and benchmark scoring. |
| 0:50–1:20 | Show example B baseline/reciprocal and export evidence: lower RMSE can accompany worse GT pose error. This experimental method is not promoted as a recovery. |
| 1:20–1:45 | Show synthetic preview, pause/reset: known-reference interpolation only; no automatic recovery or physical robot. |
| 1:45–2:20 | Show the preserved dev-01 live capture, clearly labelled recorded live output. Explain three requests/two tools, valid citations and the original answer's missing RMSE/GT qualifications. Do not present an improved answer as tested. |
| 2:20–2:45 | Show setup, evidence/source notices and remaining limits. State no validated GT-free detector or demonstrated wrong-to-correct recovery. |

## Setup and judge access

From the approved source checkout on Windows (keep demo_assets/, audit_evidence/
and frontend/public/assets/):

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e '.[test]'
npm.cmd ci --prefix frontend
```

In separate terminals, start the backend and frontend:

```powershell
$env:AUTOFRAME3D_SKIP_DOTENV='1'
.venv\Scripts\python.exe -m uvicorn autoframe3d.api:app --host 127.0.0.1 --port 8000
```

```powershell
npm.cmd run dev --prefix frontend -- --port 5173 --strictPort
```

Open http://127.0.0.1:5173 (local only). Recorded/synthetic views require no
key or full dataset. For live explanation, the operator must securely configure
a valid NEBIUS_API_KEY in the backend process environment before launch; never
put it in frontend configuration, recordings, commands committed to Git or
judge instructions. Stop servers with Ctrl+C. Optional registration replay
requires raw inputs and performs new computation; omit it from this demo.
See [setup verification](setup-verification.md) for interpreter/npm workarounds.

Hosted demo: [HOSTED DEMO URL — pending]. Video: [VIDEO URL — pending].
Official requirements: [CONFIRMED TRACK, FORMAT, AND ACCESS REQUIREMENTS — pending].
No hosted URL, public repository availability or free judge-access arrangement
is established here. Before submission, the lead must confirm eligibility,
track, required access duration and an approved judge-access plan. Judges can
reproduce the key-free views from an approved checkout; supplying managed live
access/credits remains an owner task. Account access does not prove eligibility.

## Outstanding submission tasks

- Team/owner chooses and authorizes the project-level open-source license;
  third-party asset notices do not license application code. Preserve notices.
- Updated-prompt quality remains unverified; live validation stopped at HTTP
  rejection for dev-02/dev-13. No further calls are planned in this package.
- Confirm eligibility, team attribution, repository visibility and judge access.
- Record/edit the final 2–3 minute video, check for secrets, upload it, and fill
  submission fields with real links. Final lead review/approval is pending.
- Confirm official requirements and replace pending link/team/license
  placeholders with owner-approved information.
- No deployment, publication, push or submission has been performed here.

## Validation status

No prompt rerun is planned in this package. Updated prompt quality remains
unverified; both items in the later run failed before evidence retrieval.
