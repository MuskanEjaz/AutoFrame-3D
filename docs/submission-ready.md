# AutoFrame 3D submission brief

Prepared 2026-10-28. Local review candidate; no deployment, push or submission.

Latest grounding review: [review and three-item validation plan](evidence-grounding-validation.md).
The subsequent dev-01 run against 588f514 correctly compared metrics but omitted
GT limitations and misreported a configured matching gate as a measurement.
The panel now supplies a separate deterministic scope note; revised grounding
prompt quality remains unverified. Earlier verification below is historical.

## Project and contributions

AutoFrame 3D investigates why a good geometric CAD-to-scan fit can still be a
wrong pose. It combines reproducible registration research, a viewer for two
curated recorded T-LESS examples, evidence export, and a bounded NVIDIA
Nemotron explanation through Nebius Token Factory. It does not demonstrate
automatic pose recovery, GT-free error detection, or industrial reliability.

Documented contribution split: Muskan is project lead and owns research/product
review, final narration/recording and submission approval. Juwairiya's documented
work covers Windows reproduction, offline saved-pair selection diagnosis,
engineering handoff and release/demo preparation. This release follow-up adds
transport/envelope fixes, credential guards, prompt instructions, focused tests,
a Vite patch and evidence/submission documentation with coding-agent assistance.
Team members should confirm final authorship and submission-period attribution;
this brief does not assign all historical implementation to one person.

## Three distinct demonstrations

| Surface | What actually happens | Limits |
| --- | --- | --- |
| Recorded Benchmark | Loads saved geometry, poses and metric cards; compares recorded methods and exports evidence | Opening it runs no fitting; GT instance masks and known object identity were inputs; correctness uses benchmark GT |
| Pose Inspection | Synthetic five-second interpolation toward a known reference | Visualization, not pose recovery or robot hardware control |
| Live explanation | Nemotron selects read-only evidence tools and cites saved cards | Does not change poses or run registration; citations/schema do not prove prose correctness |

## Verified state and remaining blockers

The [reviewed live capture and verification](../audit_evidence/live_integration_20261028/verification.json)
record dev-01 only: complete, three model requests, two evidence tools,
12.3736 seconds; retrieval, citations, schema and structured numbers passed.
Fourteen development items were unattempted; no overall model-quality pass.
The successful run used **88a3e73 plus an uncommitted named-envelope patch**,
not this later release commit. The original answer omitted the RMSE acceptance
criterion and GT-mask/GT-scoring dependence. Updated general prompt instructions
are **UNVERIFIED until rerun**; evaluation expectations are unchanged.

Earlier failures remain local and hash-listed in that verification file.
Operator-confirmed diagnosis: malformed credentials contained control characters;
the named name/schema envelope resolved HTTP 422. Sanitized failure captures
alone do not identify the first HTTP-400 rejected field. Credentials now fail
locally before request construction and are never repaired or printed.
Budgets remain three model turns, six tools, 60 seconds total, 20 seconds per
request, 1200 output tokens per request; no retries or fallback answers.

Current release checks:

| Check | Result |
| --- | --- |
| Focused investigation/shared transport/evaluator/recorded evidence/asset tests | 112 passed, 1 skipped (optional raw-dataset rebuild unavailable) |
| Production build (TypeScript + Vite 7.3.7) | Passed; existing >500 kB bundle warning remains |
| npm audit after compatible Vite 7.3.6 to 7.3.7 patch | Zero vulnerabilities reported |
| Diff whitespace validation | Passed |
| New inference, registration, browser smoke, deployment or push | None |

The compatible Vite patch addresses the reported development-server advisories;
see [GHSA-587h-7wmj-h5pm](https://github.com/advisories/GHSA-587h-7wmj-h5pm),
which lists 7.3.7 as patched. Only Vite and its manifest/lockfile entry changed.

 Earlier Windows
setup/browser evidence remains historical in [setup verification](setup-verification.md)
and [live integration](live-integration.md); no new browser test or live run
was performed for this release follow-up. Standalone wheels, other operating
systems and historical fitting reproduction remain unverified/incomplete.

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

No hosted URL, public repository availability or free judge-access arrangement
is established here. Before submission, the lead must confirm eligibility,
track, required access duration and an approved judge-access plan. Judges can
reproduce the key-free views from an approved checkout; supplying managed live
access/credits remains an owner task. Account access does not prove eligibility.

## Outstanding submission tasks

- Team/owner chooses and authorizes the project-level open-source license;
  third-party asset notices do not license application code. Preserve notices.
- Validate updated prompt on dev-01 and review completeness manually; broader
  quality remains untested. Do not silently revise the original capture.
- Confirm eligibility, team attribution, repository visibility and judge access.
- Record/edit the final 2–3 minute video, check for secrets, upload it, and fill
  submission fields with real links. Final lead review/approval is pending.
- No deployment, publication, push or submission has been performed here.

## One-item updated-prompt validation (not run here)

With a valid key already configured in the environment, from the worktree:

```powershell
.venv\Scripts\python.exe -c "from pathlib import Path; from uuid import uuid4; from scripts.evaluate_investigation import main; p=Path('artifacts')/('prompt-dev01-'+uuid4().hex); p.mkdir(parents=True, exist_ok=False); main(['--live','--split','development','--item','dev-01','--capture',str(p/'capture.jsonl'),'--report',str(p/'report.json')])"
```

One investigation, at most three requests, no retries; new output directory.
Review the prose for all acceptance criteria/units and GT limitations even if
automated retrieval/citation/structured-number checks pass.
