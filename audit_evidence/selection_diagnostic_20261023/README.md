# Saved-pair selection diagnosis — Juwairiya, 2026-10-23

**Finding:** applying the current geometry ranking to these exact four saved
baseline/refined pairs would retain the refinement in all four cases. All eight
poses pass geometric acceptance. Three selected refinements worsen GT-scored
MSSD/diameter. None of the three wrong baselines becomes correct; the one correct
control remains correct. This exposes a selection failure on saved examples;
it does not validate a general detector or establish safety.

## Scope and actual code path

Inspected checkout: `ccbb1045e9e0ca2205b948f1c887119f206dd398`.
The input experiment is only
[`saved_pose_reciprocal_20261014`](../saved_pose_reciprocal_20261014/README.md).
The older six-PCA-start reciprocal results, including object 7's 0.1224 result,
are a different experiment and are excluded from this analysis.

1. [`register_masked_scan`](../../autoframe3d/tless_adapter.py) fits its PCA-start
   candidates and retains the lexicographically largest `(fitness, -rmse)`.
   Higher fitness wins even if RMSE rises; RMSE breaks an exact fitness tie.
   A strict `>` comparison retains the earlier candidate on an exact double tie.
   Fitness/RMSE use scan-to-evaluation-model nearest neighbors within 15 mm;
   fitness divides inlier scan points by all scan points, and RMSE uses inliers.
2. [`evaluate_case`](../../autoframe3d/tless_benchmark.py) calls registration
   first, then loads GT and evaluates correctness. It does not use correctness
   to rank candidates. The frozen configuration uses six starts and eight
   iterations; the function signature's default iteration count is not that
   configured evaluation budget.
3. [`classify_result`](../../autoframe3d/tless_metrics.py) accepts fitness >=0.70
   AND RMSE <=10 mm. Correctness separately requires MSSD/diameter <=0.10.
   Acceptance does not require convergence or limit displacement from a prior pose.
4. [`evaluate_saved_pose_reciprocal.py`](../../scripts/evaluate_saved_pose_reciprocal.py)
   directly refines one supplied saved pose and records both results. It has no
   baseline-versus-refined selector. Therefore the choices below are **what the
   current ranking would retain if supplied these two candidates**, baseline
   first; they are not evidence of an existing automatic replacement feature.

GT scores and labels are used only after selection to grade it. The diagnostic
passes only fitness/RMSE scalars into its selector. Original fitting still
depended on GT instance masks and known object identities.

## Per-case evidence

Arrows are baseline -> refined. Deltas are refined minus baseline, computed at
full precision; displayed values are rounded. Fitness is a fraction, not percent.
Every pair has acceptance **yes -> yes**, and every hypothetical choice is **refined**.

| Exact case | Fitness before -> after (delta) | RMSE mm before -> after (delta) | Choice reason | MSSD/diameter before -> after (delta) | Post-hoc outcome |
| --- | --- | --- | --- | --- | --- |
| tless-s000001-i000001-g00-o02 | .921744 -> .921744 (+.000000) | 1.794620 -> 1.756626 (-.037994) | Tied fitness; lower RMSE | 1.402332 -> 1.409042 (+.006709) | Wrong -> wrong; error worsens |
| tless-s000002-i000003-g00-o05 | .942921 -> .945528 (+.002608) | 6.155854 -> 6.140493 (-.015361) | Higher fitness | .502130 -> .508932 (+.006803) | Wrong -> wrong; error worsens |
| tless-s000002-i000003-g01-o06 | .980254 -> .984918 (+.004664) | 3.665725 -> 3.478299 (-.187425) | Higher fitness | .542368 -> .540841 (-.001527) | Wrong -> wrong; error improves |
| tless-s000002-i000024-g02-o07 | .996384 -> .996565 (+.000181) | 4.371645 -> 4.282588 (-.089057) | Higher fitness | .085304 -> .086396 (+.001091) | Correct -> correct; error worsens |

Absolute MSSD changes are +0.443829, +0.739367, -0.165328 and +0.194957 mm,
respectively. Thus accepting a worsening pose means increasing continuous GT
error here; it does **not** mean a correct-to-wrong threshold crossing occurred.
Recoveries: 0/3; correctness regressions: 0/1; incomplete pairs: 0/4.

## Additional geometry-only diagnostics available

Saved camera-from-object matrices permit measuring change from the baseline
without consulting GT. Translation below is the distance between object origins
in the camera frame, not the translation component of a full relative transform.
Rotation uses the angle of `R_refined * transpose(R_baseline)`.

| Object / instance | Origin shift mm | Relative rotation degrees | Reciprocal fit correspondences min–max | Saved scan points |
| --- | ---: | ---: | ---: | ---: |
| 2 / g00 | .595236 | 2.426390 | 264–273 | 3,348 |
| 5 / g00 | 1.885518 | 4.058275 | 228–238 | 10,354 |
| 6 / g01 | 2.771101 | .946579 | 358–397 | 10,078 |
| 7 / g02 | 3.428788 | 4.590975 | 403–469 | 27,657 |

All four saved records report eight iterations and `iteration_limit`, not
convergence. The per-iteration reciprocal fitting counts are available, but
they are not the scan inlier counts used to calculate fitness: they use a
different correspondence definition and a subsampled model. They must not be
divided by the full scan count and relabeled fitness. Baseline scan-inlier
counts are saved in the manifest; acceptance margins can be computed from the
saved scalars. None of these observations establishes a safe rejection rule.

**Unavailable for all four pairs from these saved records:** per-point residual
arrays/quantiles, spatial inlier distribution, correspondence coordinates,
surface normals, occlusion/depth consistency, objective curvature/observability,
and per-iteration transforms/residual histories. Final matrices and counts do
not recover those fields. Raw scoring meshes/depth/masks are absent from this
clone. The two bundled display caches are display assets, not a substitute for
the four cases' hash-matched scoring inputs. No geometry was reloaded or rescored.

## Reproduce and review

```powershell
.\.venv\Scripts\python.exe scripts/diagnose_saved_pose_selection.py --output artifacts/selection-diagnostic.json
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_saved_pose_selection_diagnostic.py
```

The script uses Python's standard library only; it neither imports nor invokes
registration. It extracts the actual ranking and acceptance expressions from
current source with AST, restricts their allowed scalar inputs, and checks the
current thresholds against the frozen experiment manifest. It verifies the
manifest and four exact result-byte hashes against the saved summary, case
identities, initial pose hashes/matrices and baseline metrics (1e-9 tolerance).
This verifies integrity relative to the published evidence, not independent
historical execution or raw-data provenance.

[`analysis.json`](analysis.json) contains full precision metrics, choices,
diagnostics, counts and source/evidence SHA-256 identities. Verification:
**5 focused tests passed** (GT-label invariance, lexicographic/tie behavior,
deterministic saved output, corrupted-evidence rejection and rejection of a
ranking expression with additional GT input). No fitting, parameter tuning,
new cases, inference or benchmark execution occurred.

Historical reproduction caveat: the committed adapter lacks `_refine_icp`,
which the saved experiment runner calls. Its original manifest explicitly
records a dirty research adapter and embeds the refinement source. This
analysis does not restore or execute that uncommitted algorithm. Saved scalar
analysis remains reproducible; rerunning the original fitting is a separate
task with missing code/data dependencies.

## One next-step recommendation / lead decision gate

**Keep automatic refinement replacement disabled and present baseline/refined
poses only as an experimental comparison.** Ask Muskan to review these four
selection outcomes, including three worsening choices, before authorizing any new objective, algorithm or expanded
experiment. This follows the saved evidence; it does not propose thresholds
tuned on these four cases. No new algorithm, training or expanded experiment
should start without that discussion.

Lead update: completed saved-pair diagnosis; evidence is this table plus
hash-verified `analysis.json` and five tests; blocker is safe GT-free selection
remaining unvalidated; next action is lead review. Changes are local on
`juwairiya/selection-diagnostic`; no push, remote PR, deployment or submission.
