# Release review record — 2026-10-23

**Task 5 preparation complete; public release/submission NOT READY.**
Lead: Muskan. Engineering execution: Juwairiya.
Technical sequence, limitations and run instructions:
[release/demo plan](release-demo.md).

## Candidate identity

Base application: `ccbb1045e9e0ca2205b948f1c887119f206dd398`.
Current local branch: `juwairiya/selection-diagnostic`.
No new commit, remote PR, push, deployment or submission was created.
Task 1 edits were preserved while later task deliverables were prepared;
they are still uncommitted and must be separated into logical PRs.

A fresh committed-file export plus an explicit overlay of the local review
deliverables was created in ignored
`artifacts/release-review-20261023-v2/checkout/`. It contains 206 files, no local
virtual environment/node_modules/raw dataset, and includes current asset notices.
The exact overlay and per-file SHA-256 inventory are in the adjacent
`manifest.json`, SHA-256:
`587a9e9c4eefa8b155ee8ddb3a261232cbbd0ce99a63ac424902d64da120aab9`.
This final review record was written after the export and is not in that manifest.

## Checks actually run

| Check | Result |
| --- | --- |
| Focused backend/diagnostic tests | 53 passed, 1 skipped, 9.00 seconds |
| Skip reason | Optional display-asset rebuild requires raw source dataset |
| Synthetic pose tests | 5 passed |
| Production frontend build | PASS, Vite 7.3.6; existing >500 kB bundle advisory |
| Final credential-free Edge browser smoke | 13 grouped checks passed; no mocked responses |
| Both recorded examples / method controls / GT reveal | PASS |
| Both recorded JSON downloads / synthetic JSON export | PASS |
| Five-second preview, pause/resume, replay, reset | PASS |
| Desktop 1440x1000 / mobile 390x844 | PASS; screenshots checked, no horizontal overflow |
| Browser errors / exceptions / remote requests / POSTs | None observed |
| Fresh exported candidate API import | PASS; asserted API imported from exported checkout |
| Fresh exported geometry | PASS: A baseline, B baseline and B reciprocal |
| Fresh exported evidence downloads | PASS: two nonempty attachment JSON responses |
| Fresh exported health and missing-key state | PASS; no key configured, live availability false |
| Candidate exclusion checks | No `.env`, environments, node_modules or raw dataset/cache/download paths |
| Candidate text credential-pattern scan | No matches after fixing scanner's newline false positive |
| Git diff whitespace check | PASS |

The scanner initially treated the next line after an empty `NEBIUS_API_KEY=`
placeholder as its value. Inspection identified only `.env.example`; restricting
assignment whitespace to spaces/tabs removed that false positive. No credential
was exposed. The first export was retained separately; the v2 export is the
candidate referenced above. The scan checks selected patterns in candidate text
files only; it does not certify all files or Git history secret-free.

The fresh export reused the installed Python dependencies; it did not repeat
dependency installation on a new OS. Browser/build checks ran on the working
checkout; current runtime sources/assets match the exported base. This does not
verify a deployed service, model quality or future release edits.

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -rs -p no:cacheprovider tests/test_demo_assets.py tests/test_recorded_demo.py tests/test_investigation.py tests/test_answer_evaluation.py tests/test_saved_pose_selection_diagnostic.py tests/test_api.py::test_health_endpoint_discloses_live_or_deterministic_mode
node --test frontend/tests/pose.test.mjs
npm.cmd run build --prefix frontend
```

Local technical evidence:

- `artifacts/juwairiya-release-browser/results.json`, screenshots and downloads.
- `artifacts/release-browser.cjs`: browser smoke harness, Edge CDP port 9224.
- `artifacts/release-review-20261023-v2/fresh-checkout-smoke.json`.
- `artifacts/prepare-release-review.py`: export/overlay/hash/exclusion/API check.
- `audit_evidence/selection_diagnostic_20261023/`: portable Task 2 report/results.

## Proposed separate PRs for lead review

1. **Verify Juwairiya's Windows setup and ignore generated installation files.**
   Files: `.gitignore`, `docs/setup-verification.md`. Records tested commit/tool
   versions, actual setup workarounds and offline app checks. No runtime change.
2. **Diagnose selection using four frozen saved reciprocal pairs.** Files:
   diagnostic script, its five focused tests and dated diagnostic evidence.
   Current geometry ranking prefers all refinements while GT error worsens in
   three; no refitting or tuned selector. Reproduction and limits are documented.
3. **Prepare access, integration and release handoff.** Files: access/eligibility,
   live-integration, release/demo and release-review documents plus the scoped
   `POSE_INSPECTION.md` correction. Replaces stale procedural-only attribution
   with current bundled Panda/Poly Haven provenance; no UI redesign or algorithm
   change. Live evidence remains explicitly BLOCKED.

These are local review descriptions, not remote PR links. Before pushing, fetch
main, confirm collaborator access and create separate reviewed commits/branches;
do not mix tasks or rewrite history. Raw local browser profiles/artifacts must
remain excluded. Share selected redacted technical screenshots only as needed.

## Remaining release blockers

Muskan/team must resolve access/credits and usage approval, confirm model/JSON
compatibility, review one real live answer, approve a project-level open-source
license, confirm eligibility/track and judge access, and review the final PRs.
Muskan owns final narration/recording and submission approval. Repeat the final
smoke against the final reviewed commit after those changes. No claim of
automatic pose recovery, general selector safety or verified live quality is
authorized by this record.
