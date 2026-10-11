# Development-only failure-search pilot

Predeclared five cases, seeds 101/202/303, four existing proposals per method/case/seed. No remote proposals or GT feedback to either policy. GT-provided instance masks and GT-dependent offline correctness labels are used by the evaluator.

| Method | Candidate slots | Discovered case-seed pairs | Correct-to-wrong pairs | Already-wrong rediscoveries | Wall seconds |
|---|---:|---:|---:|---:|---:|
| deterministic | 60 | 15/15 | 0 | 15 | 114.26 |
| seeded_random | 60 | 15/15 | 0 | 15 | 113.62 |

## Shared unperturbed baselines

| Case | Category | MSSD/D |
|---|---|---:|
| tless-s000001-i000001-g00-o02 | accepted_but_wrong | 1.4023323138591388 |
| tless-s000002-i000003-g00-o05 | accepted_but_wrong | 0.5021295929132779 |
| tless-s000002-i000003-g01-o06 | accepted_but_wrong | 0.5423679550572418 |
| tless-s000002-i000003-g02-o07 | accepted_but_wrong | 0.6719126093016969 |
| tless-s000003-i000005-g01-o08 | accepted_but_wrong | 0.23501340037208715 |

Per-case/seed first-discovery indices, explicit null/no-discovery indicators and validity/timeout/failure counts are in case_seed_results.csv and summary.json. Candidate parameters, pose estimates, scoring and runtime are in results.jsonl. Noise standard deviation and dropout fraction are reported separately; no validated scalar severity exists.

Total execution wall time including shared baselines, export and one separate replay verification: 242.23 seconds (hard budget 900 seconds). Source and data hashes unchanged: True. Plan/source/config/manifests/seeds/dependencies/exact command in plan.json. Original held-out/source identity is not established by this provenance.

Representative selection prioritizes a correct-baseline transition, otherwise the first valid failure in the fixed schedule. Replay reloads saved ZIP parameters and performs one extra evaluator call, excluded from candidate comparison. See replay_result.json and representative_case.zip when present.

No claim of deployable ground-truth-free failure detection, training need, or generalization follows from this pilot.

## Interpretation and verification

Fails to support usefulness of the existing deterministic schedule over random search; inconclusive about ability to induce failures from correct baselines, because none were selected.

All five baselines were accepted-but-wrong; all 15 case-seed trials per method therefore start from a known failure. Zero correct-baseline opportunities; 0 transitions must not be interpreted as an estimated 0% transition rate.

First zero-noise/zero-dropout proposal with seed 101 on object 2. This duplicates its already-wrong baseline and establishes replay consistency, not new failure induction or perturbation robustness.

Actual evaluator calls: 5 shared baselines + 60 deterministic + 60 random + 1 separately counted replay = 126. Export made no registration call. The outer watchdog measured 243.28145719999975 seconds. Both methods had 60 valid results, no invalid proposals, timeouts or processing failures; 58/60 candidates were accepted-but-wrong in each arm. Every trial first rediscovered a failure at index 1; none had no discovery.

T-LESS local deterministic policy is fixed, not adaptive; both tested methods consume no GT feedback. Optional T-LESS live feedback is geometry-only. Separate synthetic live proposal code includes GT-derived pose_errors and classification; it was excluded and no model calls occurred.

No existing justified scalar severity; noise standard deviation (mm) and dropout fraction retained independently in results.jsonl. Deterministic ladder uses (0mm,0%), (1mm,5%), (3mm,10%), (5mm,20%); random uniformly samples the same allowed 0–5mm and 0–20% ranges.

Five outcome-blind development cases from three scenes; three seeds reuse proposal lists across cases and are not independent case samples. Four proposals per arm, within requested maximum ten. Runtime includes subprocess startup. No live/adaptive agent claim or generalization claim; no post-outcome tuning or rerun.

Four focused mocked tests passed. Initial pytest attempt had a sandbox temporary-directory error; retry passed. Exact commands and final integrity checks are recorded in interpretation.json. No further changes were committed or pushed.
