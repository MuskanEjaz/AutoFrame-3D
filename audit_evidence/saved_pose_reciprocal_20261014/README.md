# Reciprocal ICP from saved baseline poses: four-case evaluation

This is a new, bounded evaluation prepared before fitting, not a rerun of the saved six-PCA-start experiment. Four historical baselines were reused; exactly four new refinements were attempted, once each. Inputs matched the baseline audit's published hashes. Original evidence, algorithms, thresholds and UI are unchanged.

Reproducible evidence: [frozen manifest](manifest.json), [start marker](started.json), [summary/result hashes](summary.json), [focused validation](validation.json), and [runner](../../scripts/evaluate_saved_pose_reciprocal.py). Results include complete initial/refined **camera-from-object** matrices (translation in metres), fitness, RMSE in metres/mm, symmetry-aware MSSD in metres and normalized by diameter, classification, correspondence counts and measured runtime. The manifest includes raw input paths/hashes, saved-pose/record hashes, baseline provenance, code/dependency identity, the existing ICP source and uncommitted adapter identity.

| Case (result link) | Fitness before → after | RMSE mm before → after | MSSD/diameter before → after | Correct before → after | Outcome | Wall / ICP seconds |
|---|---:|---:|---:|---|---|---:|
| [tless-s000001-i000001-g00-o02](case-1.json) | 0.921744 → 0.921744 | 1.794620 → 1.756626 | 1.402332 → 1.409042 | No → No | Remained wrong | 5.122 / 0.145 |
| [tless-s000002-i000003-g00-o05](case-2.json) | 0.942921 → 0.945528 | 6.155854 → 6.140493 | 0.502130 → 0.508932 | No → No | Remained wrong | 2.611 / 0.375 |
| [tless-s000002-i000003-g01-o06](case-3.json) | 0.980254 → 0.984918 | 3.665725 → 3.478299 | 0.542368 → 0.540841 | No → No | Remained wrong | 2.460 / 0.308 |
| [tless-s000002-i000024-g02-o07](case-4.json) | 0.996384 → 0.996565 | 4.371645 → 4.282588 | 0.085304 → 0.086396 | Yes → Yes | Remained correct | 5.919 / 0.613 |

Correctness threshold remains **MSSD/diameter ≤0.10**; all baseline/refined poses pass the unchanged fitness ≥0.70 / RMSE ≤10 mm acceptance criteria. **Recoveries: 0/3 initially wrong; regressions: 0/1 initially correct; incomplete: 0/4.** These are threshold transitions: continuous GT error increased in objects 2, 5 and 7 despite lower RMSE in every case. All four terminated at the eight-iteration cap; none met the existing convergence test. Completing a bounded attempt does not mean converging or recovering a correct pose.

Configuration: reciprocal mutual-nearest-neighbor correspondences; one saved baseline pose; no PCA starts/ranking; eight iterations; 15 mm gate; up to 3,000 deterministic linspace-selected evaluation-model vertices; at least 20 correspondences; translation-update stop <0.01 mm; one attempt and 30-second subprocess timeout per case; single-threaded nearest-neighbor queries/BLAS; no random sampling/seed. Model-to-camera transforms are refined directly, never inverted into the display frame for fitting.

GT pose access and PCA initialization are blocked while loading inputs/refining; only measured point arrays and the saved baseline transform reach `_refine_icp`. GT poses/symmetries are used after it returns, through the existing scoring utilities. Baseline metrics recomputed during post-run scoring matched saved values to 1e-9. **GT instance masks and known object identities remain dependencies**, so this is not fully GT-free. Safe GT-free selection between original/refined poses remains unvalidated.

Fourteen focused tests passed before real execution, including existing reciprocal fixtures/scoring tests and new evaluation guards for GT isolation, incomplete correspondence accounting and retry prevention. Independent post-run checks verified identities, all four records/hashes, exact initial matrices, rigid transforms, units/classifications, caps and hard timeouts. No inference, training, downloads, tuning, additional cases or evaluation retries occurred. Live Nebius/NVIDIA integration/model quality remain **UNVERIFIED**.

## Reproduction

From the project root, use the recorded local Python dependencies and matching input/source hashes. Preparation refuses missing/mismatched data and requires a new output directory. Run creates an exclusive start marker and refuses to retry even after interruption. Do not execute these commands against the preserved evidence directory:

```powershell
.\.venv\Scripts\python.exe -B scripts/evaluate_saved_pose_reciprocal.py --prepare --output artifacts/saved_pose_reciprocal_reproduction
.\.venv\Scripts\python.exe -B scripts/evaluate_saved_pose_reciprocal.py --run --output artifacts/saved_pose_reciprocal_reproduction
```

`manifest.json` was frozen at HEAD `1d51354482b11087be8b28ee6899463055e4394e` plus the hash-identified dirty adapter. File-byte/dependency checks deliberately block silent substitution. Timings are machine-specific. The saved evidence is not an independent historical execution attestation; it records this local run, and four selected cases support no general accuracy claim.

## Conclusion and one next step

No recovery was demonstrated and no correctness-threshold regression was observed; one correct control is too little evidence of safety. Lower RMSE alongside worsening GT error argues against automatic application or promotion. Further investigation is justified only as a limited diagnostic, not another tuned run or a “Fix pose” claim.

**Next:** use these saved before/after pairs for an offline diagnostic of geometry-only candidate selection, contrasting fitness/RMSE preference with GT-scored displacement, without refitting. Report which worsening candidates a proposed rule would accept; keep GT solely in offline grading. This can expose selection failures but cannot validate general safety on four selected cases.
