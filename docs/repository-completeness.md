# Repository completeness audit — 2026-10-30

Compared the release worktree at `9640663` plus its existing README/cover edits
with the read-only source checkout at `ccbb104` plus its pre-existing dirty work.
No AGENTS.md was found in the audited project paths. The source worktree was
not changed. No secrets, raw datasets, environments or generated build trees
were copied, and no dataset download or paid inference occurred.

## Necessary missing files and repairs

| Path | Action / reason |
| --- | --- |
| `autoframe3d/tless_adapter.py` | Restored the reviewed source version's omitted array-only `_refine_icp`, correspondence-policy options and trace support; the existing saved-pose evaluator called this missing helper |
| `tests/test_tless_partial_icp.py` | Added the source's eight controlled synthetic regression cases; not a real-data accuracy claim |
| `scripts/evaluate_saved_pose_reciprocal.py` | Fixed a newly exposed guard leak: audit-hook activity and temporary GT/PCA overrides now end in finally, on success or exception |
| `tests/test_saved_pose_reciprocal.py` | Added cleanup assertions and exception-path regression; GT/network guards remain active during the worker |
| `tests/test_saved_pose_selection_diagnostic.py` | Preserved exact saved pairs/rules/results while validating current source hashes separately from historical source identity; no historical analysis was rewritten |

The helper/default loop was copied from actual available source, not reconstructed
from an embedded report. Default-policy outputs matched the pre-restoration
release on three small generated clouds within 1e-12. This is compatibility
evidence, not a new benchmark or evidence of improved registration accuracy.

## Differences intentionally not integrated

- `frontend/src/RecordedDemo.tsx`, `Scene.tsx`, `InvestigationPanel.tsx` and the
  source-only `recorded.css` form an alternate uncommitted UI. In particular,
  that copilot version removes newer operational diagnostics, scope notes and
  response download. The current release imports no `recorded.css`; preserve
  the working release rather than partially copying the prototype.
- The source `scripts/development_eligibility_audit.py` adds optional exclusion
  selection features; it is not a missing runtime dependency. Preserve its
  source checkout changes without adding unrelated research work here.
- Older source transport/investigation/evaluator tests, manifests and README
  do not replace the newer release implementations. Frontend package/lock
  differences retain the release's dependency patch.
- `README_For_Muskan.md`, `running_commands.txt` and `.vscode/` are local notes/
  settings, not referenced release requirements; not copied. Command notes may
  contain local or credential-bearing text and were not dumped into publication.
- `.env`, keys/credentials, virtual environments, node_modules, caches, logs,
  `.egg-info`, backup/duplicate checkouts, `frontend/dist`, the local MP4,
  bulk archive inventories, all-eligible manifests, summaries and search output
  are intentionally excluded. Use explicit runtime setup rather than uploading them.
- The selected conceptual cover remains local as `Images/autoframe3d-cover.png`
  pending affirmative redistribution-permission confirmation. Preserve the
  cover-oriented working README and narrow ignore exception locally; the
  published README uses an already tracked genuine application screenshot.
  No unconfirmed image or newly acquired dataset asset is added by this audit.

## Required-file and reference checks

All 62 release-local Python/frontend import references resolved. Python project
metadata, the frontend manifest and lockfile, Vite/index entry points, blank
server-side `.env.example`, configs, launch/evaluation/preparation scripts,
MIT license and third-party notices are present. Frontend root dependencies
match its lockfile. Both display geometries match the publication hashes in
[manifest.json](../demo_assets/manifest.json). This audit does not certify a
fresh-machine dependency installation or all research paths.

The bundled recorded/synthetic views need no full dataset or key. Keep
`demo_assets/`, `audit_evidence/` and `frontend/public/assets/` with the checkout.
[Quick Start](../README.md#quick-start) uses an editable install and `npm ci`;
standalone wheel data packaging remains unverified.

For research paths, obtain T-LESS inputs only after confirming appropriate
terms in the [permission review](data-permissions.md). The pinned data utility
supports `python scripts/tless_data.py download`, then `inspect` and `extract`;
those commands download/extract data and were not run here. Display-only rebuild
uses `python scripts/prepare_demo_assets.py --dataset <authorized-BOP-root>`
and verifies source hashes. Raw data/archives stay excluded. Missing credentials
must be configured securely in a process; never restore them by committing .env.

Implementation commit: `c4839fb5054347b779f09b5fc636990f519c0ae2`.

## Actual checks

- Focused restored-adapter/worker/metric/replay-contract/recorded-demo tests:
  **36 passed, 1 skipped**. Initial testing exposed the worker guard leak; the
  final result is after its cleanup repair.
- Backend excluding `tests/test_tless_api.py`: **189 passed, 1 skipped**.
  Four tests in that module need absent raw T-LESS inputs and were not executed
  in this run; no full-suite or fresh raw-data replay pass is claimed.
- Frontend tests: **8 passed**. TypeScript and Vite 7.3.7 production build passed
  with explicit 384 MiB old heap / 2 MiB semi-space; existing >500 kB advisory.
- Three generated-cloud comparisons retained default registration output within
  1e-12 of the earlier implementation. No historical GT/result/identity/rubric
  file was modified and no registration was run on raw benchmark data.
- Local documentation targets, image paths, selected secret/personal-path patterns,
  exact staged scope and git diff whitespace are checked before publication.

Third-party notices remain intact. The existing T-LESS governing-grant question
is unresolved; this audit adds no redistribution permission and changes no data
license. Current grounded live quality remains unverified; a previous user-run
128-token diagnostic truncated and did not run investigations. No deployment,
video upload or hackathon submission is performed.
