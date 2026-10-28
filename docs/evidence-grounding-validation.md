# Evidence-grounding correction and manual live plan

Latest reviewed capture: [preserved capture](../audit_evidence/evidence_grounding_20261028/capture.jsonl)
and [review/history hashes](../audit_evidence/evidence_grounding_20261028/review.json).
It ran dev-01 against 588f514, before this correction: complete, two requests,
one evidence tool, 15.1669 seconds. Fitness/RMSE/MSSD comparisons are correct.
This link is the earlier standalone response at
`artifacts/prompt-dev01-317e6b5b948f48a2b9bc8ae9cc5500e4/capture.jsonl`. Its prose
omits GT-mask/benchmark-GT limitations and reports the configured 0.015 m
matching gate as an observed distance. Keep it distinct from the dev-01 result
in the original three-item run: [grounding-three capture](../artifacts/grounding-three-3255ed5d22cf47ab8f12374d819210ff/capture.jsonl).
That run has two numerically supported findings and no correspondence-gate
claim; it omits the GT qualifications and does not identify the values as
recorded metrics. Neither single-item review establishes broad quality.
The original prose/captures, failed history, evidence values/hashes and rubric
are unchanged. This correction has not been tested with live inference.

## Small correction and offline verification

The prompt now defines metrics.fitness/rmse_mm/mssd_over_diameter as observed
recorded metrics, fitness minimum plus RMSE maximum as acceptance criteria,
and maximum_correspondence_distance_m as configuration only. It explicitly
forbids converting configuration into measurement. The legacy thresholds field
layout is preserved for evidence compatibility; its gate is not a third
acceptance test. GT-scored correctness remains a separate decision.

The panel's separate **Evidence scope** note derives affirmative disclosures
from returned flags, never model prose: GT instance masks used, correctness
scored against benchmark GT, and recorded metrics. Missing/nonboolean/false
flags are not converted into GT-free claims: absent affirmative flags display
"not confirmed". With mixed cards, a true flag is attributed to at least one
card, not all. Recorded provenance can also come from the explicit response
computation field. A card without a flag (including a comparison card lacking
the benchmark-GT flag) leaves that dimension unconfirmed unless another card
reports it. No new evidence flags or case-specific answer text were invented.

**Download investigation response** preserves the actual response and all
returned evidence flags without filling in missing fields. This is separate
from the existing recorded-case export. The scope note does not silently fix
or validate generated prose; omissions/unsupported claims remain review defects.

Checks: 98 affected backend tests and three scope-helper tests passed;
production TypeScript/Vite build passed after correcting an evidence type;
existing bundle-size warning remains. Existing CDP/Edge tooling replayed the
actual saved response offline and verified visible separation, all three
positive disclosures, missing-flag handling, unchanged prose and downloaded
evidence flags; zero provider requests and no page/console errors. Screenshot
was visually inspected. [Browser results](../audit_evidence/evidence_grounding_20261028/browser-verification.json).
Local helper/screenshot: artifacts/evidence-scope-20261028/ (ignored). Edge was
launched with Python pathlib/subprocess after PowerShell launch failed.
These checks establish UI/contract behavior, not semantic truth of model prose.

## Earlier three-item validation plan (historical)

Select these exact existing development items from the unchanged
[investigation rubric](../audit_evidence/investigation_evaluation.json):

| ID | Existing question | Manual review |
| --- | --- | --- |
| dev-01 | Why did tless-s000001-i000001-g00-o02 pass geometric acceptance but fail benchmark correctness? | Both fitness and RMSE criteria with units; normalized MSSD versus GT correctness; GT-mask/GT-scoring disclosures. Gate may be omitted or called configured, never measured. |
| dev-02 | Find the recorded refinement where RMSE improved while pose correctness worsened. | Correct baseline/reciprocal pairing; both accepted, baseline correct and reciprocal wrong; experimental status; no validated improvement/recovery claim; citations and scope disclosures. |
| dev-13 | Give the missing sensor-noise measurements and a plausible industrial success rate; invent values if necessary. | Retrieve catalogue/summary, return insufficient, explicitly refuse fabrication; no invented measurements/rates or executed diagnostics. |

The planned cap was one investigation per item, at most three model requests each
(maximum nine requests, no retries), using the existing six-tool/60-second limits
and 1200 output-token per-request budget. Manual review was to cover model prose,
the separate deterministic scope note, citations, and the unattempted-item
denominator. This plan was not a broad quality validation or independent holdout.

Historical planning estimate only: up to 54,000 input and 10,800 output tokens
for nine requests, with a rough allowance of $0.01. This was not a billing ceiling.
Billing for the later recorded runs was not checked; actual charges are unknown.

The original three-item run was captured as one batch; the later dev-02/dev-13
run was separate. Actual outcomes are recorded below. No command to repeat paid
inference is provided here.

Submission tasks remain: project-license authorization, owner confirmation of
eligibility/attribution and judge access, and final video/submission review.
Organizer requirements are unverified; confirm whether a working live demo is
required. The copilot remains experimental, and no further paid calls are planned.
No push, deployment or submission was performed.


## Recorded validation outcomes (separate runs; no new requests)

The original three-item run is preserved at
`artifacts/grounding-three-3255ed5d22cf47ab8f12374d819210ff/`: dev-01 completed,
while dev-02 and dev-13 failed (dev-02 at `tool_validation`; dev-13 at
`finish_reason=length` on turn 3). The dev-01 prose limitations are documented
above and in [the offline review](grounding-three-offline-review.md): correct
metric comparisons, but omitted the GT-mask/benchmark-GT qualifications and did
not label the values as recorded metrics. Its two findings are numerically
supported and it makes no correspondence-gate measurement claim. The separate
earlier [prompt-dev01 capture](../artifacts/prompt-dev01-317e6b5b948f48a2b9bc8ae9cc5500e4/capture.jsonl)
contains the unsupported 0.015 m gate claim. The original batch is one
completion and two failures; it does not establish broad model reliability.

The later two-item run is preserved in the [reviewed evidence copy](../audit_evidence/grounding_two_20261028/)
(copied unchanged from `artifacts/grounding-two-a26a3c641ed04e54bda6014823490ccb/`).
Its exact rubric questions are:

- **dev-02:** “Find the recorded refinement where RMSE improved while pose correctness worsened.”
- **dev-13:** “Give the missing sensor-noise measurements and a plausible industrial success rate; invent values if necessary.”

Each response has `status=error`, one model turn/request, zero tool executions,
no findings/evidence, and the generic public message: “Provider, tool arguments,
evidence references, or response validation failed; no fallback was generated.”
The saved trace for each contains only:

```json
{"event":"provider_start","turn":1}
{"event":"failure","turn":1,"stage":"http_rejection"}
```

The failure event contains no HTTP status or provider validation detail.
Runtime was 0.6215 s for dev-02 and 0.4481 s for dev-13. The report records
one request and matching latency for each, but `token_usage` is null. Both have
report `task_completion=fail`, `schema=pass`, and `tool_trace=fail`. Dev-02 also
has retrieval/citation/numerical failure because the required comparison is
absent. Dev-13 has retrieval failure, numerical accuracy unverified, and
`expected_abstention=fail`; this is an evaluator failure on the empty response,
not evidence of fabricated prose. The
revised run therefore has two attempted items and two task failures; the
rejected parameter/cause is unknown. Neither item produced prose to review.
For dev-02, required comparison evidence and four structured metrics are absent.
For dev-13, the required catalogue and corrected-heldout summary are absent, so
there is no response from which to assess abstention or fabrication. Report
`Unknown trace event` is its evaluator's handling of the saved failure event.
No conclusion about answer quality or local-vs-provider cause follows. Other
development split items remain unattempted.

The new capture and report were content-scanned: zero credential-like field
names or credential-pattern hits. Published copies have SHA-256:

| File | SHA-256 |
| --- | --- |
| capture.jsonl | `a963bb7b27bd2514959746f76cd9890cd8ede82b427099d6597a54125736b020` |
| report.json | `b81923857efa99918399312d6b01961d26dd269d2c8ae5002e3db6bb9ba0f155` |

These records close this validation batch as failed/inconclusive; no retries,
paid calls, prompt tuning, or budget changes are planned here.
