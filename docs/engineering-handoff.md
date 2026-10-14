# AutoFrame 3D: recorded-evidence engineering handoff

Reviewed 2026-10-14 at UI checkpoint `dce8f34a22dc35c596466201b42dc8f3965e4844` plus the existing dirty worktree. No applicable AGENTS.md was found. Visuals and unrelated edits are preserved; current research code does not prove historical execution identity.

## UI closure and verification

Visual/preview work is already committed; no defect or outstanding UI checkpoint was found. Current-worktree production build passed (768 MB Node heap; existing bundle warning). Focused installed-Chrome checks passed main/thumbnail play/pause/seek/reset synchronization, edited-original export/restoration, essential actions after sidebar scrolling at 1440×700, Recorded Benchmark opening and JSON evidence download; zero console/page errors. Helper: `.tools/handoff-ui-check.cjs` (ignored). Earlier endpoint/stationary/replay and five pose-test checks remain in the [committed UI report](workcell-lighting-review/verification.json). No registration replay or inference was launched, and no UI paths were staged.

## Capability boundaries

**Implemented and supported by recorded evidence:**

- [`tless_adapter.py`](../autoframe3d/tless_adapter.py), `load_registration_inputs` / `register_masked_scan`: recorded depth, intrinsics, known object identity and **GT-provided instance masks** yield metre-valued scan points. Historical fitting uses six diversity-ordered starts from 24 PCA rotations, centroid translation and eight model-to-scan ICP iterations (3,000 model fitting points; 15 mm correspondence distance). Candidate ranking maximizes scan-to-evaluation-model fitness, then minimizes inlier RMSE. No target GT pose is read during fitting; input selection remains GT-assisted.
- [`tless_benchmark.py`](../autoframe3d/tless_benchmark.py), `evaluate_case`, loads GT after fitting. [`tless_metrics.py`](../autoframe3d/tless_metrics.py), `classify_result`: acceptance is fitness >=0.70 and RMSE <=10 mm; correctness is **MSSD/diameter <=0.10**. `mssd_normalized` minimizes maximum surface displacement over GT-equivalent discrete/continuous symmetries, using model metadata and frozen 0.01 continuous-symmetry discretization. Correctness requires GT; acceptance does not establish correctness.
- [`recorded_demo.py`](../autoframe3d/recorded_demo.py) and [`api.py`](../autoframe3d/api.py) serve saved metrics/poses, validated display geometry and evidence without fitting; display transforms invert saved camera-from-object matrices. Optional `tless_cases.replay_record` refits raw inputs and evaluates a separate new result, preserving recordings; not rerun here.
- Actual baseline/experimental reciprocal and scan-to-model results exist. The [local search pilot](../audit_evidence/development_search_pilot_20261011T051807Z_289be02e/REPORT.md) made 126 evaluator calls: all five baselines were already wrong; deterministic/random arms showed no correct-to-wrong discovery advantage. Policies received no GT feedback, but masks and evaluator labels require GT. This does not validate detection or recovery.

**Implemented but unverified:** live Nebius/NVIDIA transport and bounded copilot/proposal loops. [`investigation.py`](../autoframe3d/investigation.py), `EvidenceTools`, recomputes labels/cards from saved scalars, not geometry; `investigate` explains evidence and cannot change registration. [`nebius.py`](../autoframe3d/nebius.py) implements provider transport. Mocked-provider tests and [hand-authored answer fixtures](../audit_evidence/INVESTIGATION_EVALUATION.md) verify harness behavior, not model quality. **Live integration/model quality remain UNVERIFIED.** `tless_search.py` live feedback is geometry-only; separate synthetic `agent.py` feedback contains GT-derived errors/labels, so is an offline adversary. No model calls contributed to curated results.

**Synthetic visualization only:** [`poseMath.ts`](../frontend/src/poseMath.ts), `correctionPreview`, interpolates translation/slerps rotation to a known synthetic reference over five seconds. `PoseInspection.tsx` synchronizes both views and preserves the original estimate. Scanner/robot animation is not hardware evidence or recovery. `experiment.py` performs actual yaw-grid/ICP on generated geometry, with generated-GT scoring; synthetic computations are not real-data evidence.

**Missing:** validated GT-free wrong-pose detection; validated correction of a wrong recorded pose without target GT; GT-free instance selection; a supported automatic “Fix pose” path. Geometry-derived ICP transforms exist, but genuine recovery is unproven. No curated wrong-to-correct transition exists.

## The two real recorded examples

Source of truth: [curated demo.json](../audit_evidence/recorded_benchmark_demo/demo.json), [publication manifest](../audit_evidence/recorded_benchmark_demo/COPY_MANIFEST.json), [baseline source copy](../audit_evidence/development_eligibility_audit_20261011T053002Z_963a0a93/results.jsonl), and [four-case reciprocal source copy](../audit_evidence/recorded_benchmark_demo/reciprocal_results.jsonl). Publication/source hashes and curated pose-metric correspondence were checked; originals and thresholds are unchanged.

| Case / method | Fitness (fraction) | Inlier RMSE (mm) | MSSD (mm) | MSSD/diameter | Outcome |
|---|---:|---:|---:|---:|---|
| A: object 2 baseline | 0.921744 | 1.794620 | 92.765965 | 1.402332 | Accepted, wrong |
| A: reciprocal (source artifact; not a curated UI variant) | 0.921744 | 1.690840 | 32.376127 | 0.489426 | Accepted, still wrong |
| B: object 7 baseline | 0.996384 | 4.371645 | 15.236642 | 0.085304 | Accepted, correct |
| B: reciprocal | 0.988827 | 3.727941 | 21.865101 | 0.122415 | Accepted, wrong |

- **A** UI ID `accepted-wrong`; case `tless-s000001-i000001-g00-o02`: scene 1, image 1, GT instance 0, object 2; diameter 66.1512 mm. PrimeSense scene `000001`, depth `000001.png`, visible mask `000001_000000.png`, `scene_camera.json`, CAD/evaluation `obj_000002.ply`, model-info symmetries; annotated GT pose from `scene_gt.json`. Saved estimate/GT matrices are in the baseline record. Reciprocal improves GT-scored displacement substantially but does **not** meet correctness. No successful correction.
- **B** UI ID `control-regression`; case `tless-s000002-i000024-g02-o07`: scene 2, image 24, GT instance 2, object 7; diameter 178.615 mm. PrimeSense scene `000002`, depth `000024.png`, visible mask `000024_000002.png`, camera metadata, CAD/evaluation `obj_000007.ply`, model-info symmetries and annotated GT pose. Reciprocal repeats six PCA starts with mutual-nearest-neighbor ICP correspondences and unchanged ranking/thresholds; it is not a refinement initialized from the saved baseline pose. RMSE improves by 0.643704 mm while GT correctness regresses across 0.10. It is experimental and rejected for promotion.

Both have hash-identified raw inputs/saved poses and bundled display geometry ([manifest](../demo_assets/manifest.json)): A 3,348 scan points / 41,063 CAD vertices; B 27,657 / 8,517. Display caches are not scoring/replay inputs or execution provenance; the older README's raw-only geometry wording is stale. B's reciprocal record joins the saved alternative pose/metrics to baseline GT. Publication hashes identify saved copies, not independent historical execution. The broader 24-correct/176-wrong count includes 21 rescored cases and 179 carried forward with three controls: not a full independent rescore or official BOP score. Selected examples establish no population success rate.

## Saved-baseline reciprocal evaluation (2026-10-14)

The authorized four-case evaluation is complete: [full table, configuration and reproduction](../audit_evidence/saved_pose_reciprocal_20261014/README.md), [pre-run manifest](../audit_evidence/saved_pose_reciprocal_20261014/manifest.json), [results/counts](../audit_evidence/saved_pose_reciprocal_20261014/summary.json), [validation](../audit_evidence/saved_pose_reciprocal_20261014/validation.json). Existing reciprocal results used PCA initialization and were not reused as this experiment. Four hash-verified baselines were reused; four new single-pose refinements ran, one attempt each, with eight iterations/15 mm gate/3,000 deterministic model fitting points/30-second hard timeout. GT pose access and PCA are blocked until refinement returns; GT masks remain an input dependency.

| Exact case | RMSE mm before → after | MSSD/diameter before → after | Outcome | Wall seconds |
|---|---:|---:|---|---:|
| tless-s000001-i000001-g00-o02 | 1.794620 → 1.756626 | 1.402332 → 1.409042 | Remained wrong | 5.122 |
| tless-s000002-i000003-g00-o05 | 6.155854 → 6.140493 | 0.502130 → 0.508932 | Remained wrong | 2.611 |
| tless-s000002-i000003-g01-o06 | 3.665725 → 3.478299 | 0.542368 → 0.540841 | Remained wrong | 2.460 |
| tless-s000002-i000024-g02-o07 | 4.371645 → 4.282588 | 0.085304 → 0.086396 | Remained correct | 5.919 |

**Recoveries 0/3; regressions 0/1; incomplete 0/4.** All poses remain geometrically accepted; correctness threshold remains ≤0.10. All attempts reached the iteration cap without convergence. RMSE improved everywhere while GT displacement worsened in three cases. Fourteen focused tests and post-run identity/transform/classification checks passed. No demonstrated recovery; no observed threshold regression, but no general safety or accuracy claim follows. Keep the method experimental; safe GT-free candidate selection is still unvalidated. Live Nebius/NVIDIA integration and quality remain UNVERIFIED.

**One next task:** an offline diagnostic of geometry-only selection using these saved before/after pairs, contrasting fitness/RMSE preference with GT-scored displacement, without refitting. Report acceptance of worsening candidates; use GT only for offline grading. Limited objective/selection investigation is justified; promotion or a “Fix pose” claim is not.

Preserved uncommitted work: `autoframe3d/tless_adapter.py`, `scripts/development_eligibility_audit.py`, `tests/test_tless_partial_icp.py`, `frontend/src/{InvestigationPanel.tsx,RecordedDemo.tsx,Scene.tsx,recorded.css}`, `artifacts/`, `data/tless/diagnostics/`, and `running_commands.txt`. The evaluation checkpoint contains only its runner, focused guard tests, compact evidence and documentation. No UI/research algorithm changes, inference, downloads, push or deployment.
