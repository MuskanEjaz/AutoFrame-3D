> Derived publication copy. Original artifacts remain unchanged locally. Original and publication hashes are recorded in COPY_MANIFEST.json. The original audit_failure.json is retained locally, outside this versioned evidence directory.

# Independent historical T-LESS scoring audit

One saved heldout200 label changes. Estimated poses and geometric acceptance are unchanged.

Scope: five existing JSONL run files under data/tless/results; results are reported separately, since smoke/development runs overlap. All 30 object metadata entries inspected. Affected objects: 8, 10, 11, 12, 25, 26; translated discrete symmetries only. No nonzero continuous offsets in local metadata.

All affected valid records have finite poses/metrics, matching object/instance IDs and manifests. All 256 saved valid GT transforms match local cam_R_m2c/cam_t_m2c after mm-to-m conversion exactly. Raw saved estimates are used without alteration. Eight initial smoke timeouts have no saved estimate or correctness label, including two object-8 records; statuses retained, not scored.

Independent reference uses Rodrigues rotations, a separate PLY vertex reader, and homogeneous matrix multiplication GT @ symmetry @ object_point. MSSD is minimum over symmetries of maximum corresponding-point displacement, divided by diameter. Frozen threshold: 0.10 inclusive. Original continuous rule: ceil(pi / 0.01) = 315 samples; continuous @ discrete composition preserved.

Seven analytical checks passed: identity, known non-equivalent translation, translated discrete symmetry with nonidentity GT, legacy-unit negative control, continuous offset axis on-grid, continuous half-grid with analytic residual, and combined composition. Corrected production/reference maximum normalized difference on rescored records: 2.220446049250313e-16. Independent legacy-unit scorer reproduces historical MSSD within 2.220446049250313e-16. Fifteen deterministic unaffected controls retain metrics and labels.

| Run | Affected valid rescored | Affected timeout | Correct before → after | Wrong before → after |
|---|---:|---:|---:|---:|
| data/tless/results/original/development_tuning20.jsonl | 8 | 0 | 1 → 1 | 19 → 19 |
| data/tless/results/original/heldout200.jsonl | 21 | 0 | 23 → 24 | 177 → 176 |
| data/tless/results/original/smoke20.jsonl | 4 | 2 | 1 → 1 | 11 → 11 |
| data/tless/results/original/smoke20_frozen.jsonl | 6 | 0 | 0 → 0 | 20 → 20 |
| data/tless/results/perturbed/heldout200.jsonl | 0 | 0 | 0 → 0 | 4 → 4 |

Heldout original corrected aggregate: 24 accepted-and-correct, 176 accepted-but-wrong (88.0%), zero rejected/timeouts/failures. All 21 affected records rescored; 179 unaffected labels carried forward, including three scored controls. This is not a full independent rescore. Previous 23/177 and 88.5% figures remain historical recorded values; corrected-score claims must use 24/176 and 88.0%.

## Every affected valid record

| Run | Case ID | Object | Historical MSSD/D | Historical label | Corrected MSSD/D | Corrected label | Changed |
|---|---|---:|---:|---|---:|---|---|
| data/tless/results/original/development_tuning20.jsonl | tless-s000003-i000010-g01-o08 | 8 | 0.7832964123 | accepted_but_wrong | 0.758767144031 | accepted_but_wrong | False |
| data/tless/results/original/development_tuning20.jsonl | tless-s000004-i000010-g01-o08 | 8 | 0.661691572735 | accepted_but_wrong | 0.661691572735 | accepted_but_wrong | False |
| data/tless/results/original/development_tuning20.jsonl | tless-s000003-i000010-g02-o11 | 11 | 0.652113933033 | accepted_but_wrong | 0.652113933033 | accepted_but_wrong | False |
| data/tless/results/original/development_tuning20.jsonl | tless-s000003-i000010-g03-o12 | 12 | 0.679528521603 | accepted_but_wrong | 0.672069269633 | accepted_but_wrong | False |
| data/tless/results/original/development_tuning20.jsonl | tless-s000001-i000017-g01-o25 | 25 | 1.06932412468 | accepted_but_wrong | 0.693993749511 | accepted_but_wrong | False |
| data/tless/results/original/development_tuning20.jsonl | tless-s000004-i000010-g02-o26 | 26 | 0.187200781946 | accepted_but_wrong | 0.187200781946 | accepted_but_wrong | False |
| data/tless/results/original/development_tuning20.jsonl | tless-s000003-i000016-g01-o08 | 8 | 0.264508929587 | accepted_but_wrong | 0.227573990461 | accepted_but_wrong | False |
| data/tless/results/original/development_tuning20.jsonl | tless-s000004-i000025-g01-o08 | 8 | 1.07464781997 | accepted_but_wrong | 0.713267764023 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000011-i000004-g01-o08 | 8 | 0.443789572442 | accepted_but_wrong | 0.0656688170063 | accepted_and_correct | True |
| data/tless/results/original/heldout200.jsonl | tless-s000005-i000007-g03-o10 | 10 | 0.580816307421 | accepted_but_wrong | 0.580816307421 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000011-i000004-g03-o10 | 10 | 1.01250834115 | accepted_but_wrong | 0.115538586207 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000016-i000008-g00-o10 | 10 | 1.01053881013 | accepted_but_wrong | 0.117431937358 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000006-i000002-g02-o11 | 11 | 0.977676610334 | accepted_but_wrong | 0.978654271094 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000016-i000008-g01-o11 | 11 | 0.14286527063 | accepted_but_wrong | 0.14286527063 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000006-i000002-g04-o12 | 12 | 0.159965389549 | accepted_but_wrong | 0.159965389549 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000016-i000008-g02-o12 | 12 | 0.130431257922 | accepted_but_wrong | 0.134949838238 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000015-i000001-g00-o25 | 25 | 0.253958830408 | accepted_but_wrong | 0.253958830408 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000015-i000001-g01-o26 | 26 | 0.618009947525 | accepted_but_wrong | 0.618009947525 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000011-i000012-g01-o08 | 8 | 0.0943412189978 | accepted_and_correct | 0.0943412189978 | accepted_and_correct | False |
| data/tless/results/original/heldout200.jsonl | tless-s000005-i000020-g03-o10 | 10 | 0.259142190642 | accepted_but_wrong | 0.259142190642 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000011-i000012-g03-o10 | 10 | 1.0127461592 | accepted_but_wrong | 0.103749029953 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000016-i000014-g00-o10 | 10 | 0.62913476947 | accepted_but_wrong | 0.62913476947 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000006-i000002-g03-o11 | 11 | 0.914288444739 | accepted_but_wrong | 0.914288444739 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000016-i000014-g01-o11 | 11 | 0.130328346224 | accepted_but_wrong | 0.12894306658 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000006-i000011-g04-o12 | 12 | 0.110131476083 | accepted_but_wrong | 0.110131476083 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000016-i000014-g02-o12 | 12 | 0.20815629282 | accepted_but_wrong | 0.18703483083 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000015-i000012-g00-o25 | 25 | 1.01144807208 | accepted_but_wrong | 1.01144807208 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000015-i000012-g01-o26 | 26 | 1.08279809474 | accepted_but_wrong | 1.0500416888 | accepted_but_wrong | False |
| data/tless/results/original/heldout200.jsonl | tless-s000011-i000023-g01-o08 | 8 | 0.0607722602133 | accepted_and_correct | 0.0607722602133 | accepted_and_correct | False |
| data/tless/results/original/smoke20.jsonl | tless-s000003-i000005-g02-o11 | 11 | 0.807242679243 | accepted_but_wrong | 0.806728245779 | accepted_but_wrong | False |
| data/tless/results/original/smoke20.jsonl | tless-s000003-i000005-g03-o12 | 12 | 0.599396214683 | accepted_but_wrong | 0.599396214683 | accepted_but_wrong | False |
| data/tless/results/original/smoke20.jsonl | tless-s000001-i000001-g01-o25 | 25 | 0.915750745177 | accepted_but_wrong | 0.844930518471 | accepted_but_wrong | False |
| data/tless/results/original/smoke20.jsonl | tless-s000004-i000000-g02-o26 | 26 | 0.999111705743 | accepted_but_wrong | 0.999111705743 | accepted_but_wrong | False |
| data/tless/results/original/smoke20_frozen.jsonl | tless-s000003-i000005-g01-o08 | 8 | 0.252293308322 | accepted_but_wrong | 0.235013400372 | accepted_but_wrong | False |
| data/tless/results/original/smoke20_frozen.jsonl | tless-s000004-i000000-g01-o08 | 8 | 0.682181942372 | accepted_but_wrong | 0.682181942372 | accepted_but_wrong | False |
| data/tless/results/original/smoke20_frozen.jsonl | tless-s000003-i000005-g02-o11 | 11 | 0.729990884246 | accepted_but_wrong | 0.728523631784 | accepted_but_wrong | False |
| data/tless/results/original/smoke20_frozen.jsonl | tless-s000003-i000005-g03-o12 | 12 | 0.730765070191 | accepted_but_wrong | 0.722034429378 | accepted_but_wrong | False |
| data/tless/results/original/smoke20_frozen.jsonl | tless-s000001-i000001-g01-o25 | 25 | 1.08686756035 | accepted_but_wrong | 0.758097291965 | accepted_but_wrong | False |
| data/tless/results/original/smoke20_frozen.jsonl | tless-s000004-i000000-g02-o26 | 26 | 1.08723006569 | accepted_but_wrong | 1.02208035728 | accepted_but_wrong | False |

Affected records without historical labels/estimates: tless-s000003-i000005-g01-o08 and tless-s000004-i000000-g01-o08 in original/smoke20.jsonl (timeouts). No missing/invalid/nonfinite inputs among historical valid records.

## Execution and provenance

Final command (repository root):

```powershell
.\.venv\Scripts\python.exe -B artifacts/symmetry_scoring_audit_20261011_02a10626368f/audit.py
```

Initial audit stopped on GT orthogonality residual 1.09e-6 at 1e-6 validation tolerance. Read-only inspection measured maximum 1.38e-6 in rounded GT matrices. Final validation tolerance is 1e-5; no pose matrix projected, altered, or re-estimated; scoring threshold remains 0.10. Initial failure retained in audit_failure.json.

audit_summary.json hashes 60 exact inputs/current sources, including historical JSONL/CSV/summary files, all five manifests, relevant model PLYs and metadata, local GT annotations, frozen config, dataset provenance, and audit/current scoring source. Input hashes rechecked unchanged at end. Dependencies and execution environment recorded. These are audit-time identities; original-run source identity and complete dependency versions remain unavailable. No current hash is attributed to historical execution.

Historical evaluation uses GT-provided visible instance masks. Held-out aggregate results have already been inspected; this audit provides scoring correction, not untouched generalization evidence. No registration, training, threshold tuning, downloads, installations, or remote/model calls occurred. Other historical result files, backups and reports were not changed.
