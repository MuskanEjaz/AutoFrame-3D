# Three-item grounding run: offline review

Reviewed 2026-10-28 in the release worktree only. Expected and verified branch:
release/finish-20261028; HEAD 8ea46fbeb4d375be7e1feb4e7bd8b8a6faab3ae4.
Initial status: clean. No applicable AGENTS.md found in the worktree or parent
chain. No sibling checkout access, inference, push, deployment, submission,
licensing change or commit. Repairs below are an uncommitted review candidate.

## Preserved inputs

Read [submission brief](submission-ready.md), [grounding plan](evidence-grounding-validation.md),
and both files under artifacts/grounding-three-3255ed5d22cf47ab8f12374d819210ff/.
Capture lines 1/2/3 correspond to dev-01/dev-02/dev-13, respectively.

| File | SHA-256, unchanged after diagnosis/tests |
| --- | --- |
| capture.jsonl | 1534df08f8ef99ba482d71e207eb94d5f672a5f7cafd1bad2f8fb68c00080719 |
| report.json | ee3f786110e6936191be60cf53979f212fb8db9714b52dacac04ef39cbd030f0 |

No existing captures, evidence values/hashes, fixtures or rubric were rewritten.

## dev-02: confirmed unsupported comparison, not a schema mismatch

Sanitized saved trace excerpt (capture line 2):

```json
{"event":"tool_attempt","attempt":3,"call":{"name":"compare_recorded_methods","arguments":{"case_id":"tless-s000001-i000001-g00-o02"}}}
{"event":"failure","turn":3,"stage":"tool_validation"}
```

Offline replay of this exact call passes both ToolCall and CompareArgs strict
validation. CompareArgs.case_id is a required string of length 1..100; extra
fields are forbidden, and there is no case-specific enum. All constraints pass.
See [schema](../autoframe3d/investigation.py#L51) and
[validation/precondition](../autoframe3d/investigation.py#L109).

The selected case exists but its catalogue methods are only [baseline]. The
application precondition len(case["variants"]) >= 2 fails at line 111, raising
ValueError("No recorded method comparison for case") at line 112. No Pydantic
ValidationError occurs. The catalogue already identified the other approved
case as having baseline and reciprocal methods. This is a model-selected
unsupported operation on a validly encoded case ID, not malformed JSON, an
argument-shape defect, or evidence of a local schema/validation disagreement.
The complete raw Action text is not retained, but execution reached tool_attempt
only after Action validation. Invalid attempted tools correctly consume budget.

Three requests, three tool attempts, 3.4812 seconds. The third request returned
139 completion tokens; output truncation was not its failure. The required
comparison evidence was never retrieved. Even a valid comparison requested on
the last model turn would leave no later model turn for synthesis.

The report's generic "Malformed trace or invalid tool arguments" comes from
[re-executing attempts](../autoframe3d/answer_evaluation.py#L163) and catching
the above ValueError at line 194. It does not establish malformed model output;
that early exception also leaves the report's dev-02 telemetry null. The saved
trace, not that summary wording, establishes the actual path.

## dev-13: confirmed non-stop truncation; exact token cause unresolved

Sanitized saved trace excerpt (capture line 3):

```json
{"event":"provider_result","turn":1,"usage":{"prompt_tokens":947,"completion_tokens":233,"total_tokens":1180}}
{"event":"provider_result","turn":2,"usage":{"prompt_tokens":1160,"completion_tokens":227,"total_tokens":1387}}
{"event":"provider_start","turn":3,"timeout_seconds":20.0}
{"event":"failure","turn":3,"stage":"finish_reason","finish_reason":"length"}
```

The first two returns total 2107 prompt + 460 completion = 2567 recorded tokens.
Third-turn usage is absent, not zero. Configured limits are max_tokens=1200 per
request, max_response_bytes=32768, 20 seconds per request, 60 seconds total,
three turns/six tools; see [request](../autoframe3d/investigation.py#L209).
The observed runtime is 7.9896 seconds; this was not a timeout, six-tool limit,
or dispatcher deadline failure.

Retrieved context before turn 3: the catalogue, followed by both baseline case
cards (three tools total), plus system/schema, the question and prior assistant
tool actions. The turn-2 tool-results message advertises one remaining model
turn and three tools. The requested summary had not been fetched, despite the
existing unanswerable-question instructions. The cards do not contain sensor
noise measurements or an industrial success rate. The final exact prompt
text/token count and assistant action JSON are not saved, so context content
can be inferred from code/trace but not reconstructed byte-for-byte.

The provider reports length, consistent with a generation limit, but the capture
cannot establish that exactly 1200 tokens were used, a reasoning/visible-token
split, context exhaustion, the partial answer's content, fabrication, or that
more tokens would produce a correct abstention. Increasing budgets is unjustified.

[Transport validation](../autoframe3d/nebius.py#L92) rejects non-stop completions
before returning a body to investigate, so no provider_result/usage is emitted
for turn 3. The investigation returns explicit error with empty findings, not
an abstention or a fabricated success. The report's token_usage.complete=false
is appropriate; its "Unknown trace event" reflects the evaluator not recognizing
failure events at [line 176](../autoframe3d/answer_evaluation.py#L176), not an
additional demonstrated provider defect. Evaluator/rubric behavior is unchanged.

## dev-01: every substantive prose claim reviewed

Complete; three requests/two tools, 6.4861 seconds. Both findings cite the
baseline case card retrieved on turn 2; the report confirms retrieval/citations.

| Claim in generated prose | Returned evidence and review |
| --- | --- |
| Fitness 0.9217 >= 0.7 | Recorded 0.9217443249701314 and minimum_fitness 0.7; rounding and comparison correct, dimensionless |
| RMSE 1.7946 mm = 0.0017946 m <= 0.01 m | Recorded 1.7946198167643792 mm; conversion, rounding and threshold comparison correct |
| These criteria pass geometric acceptance | Both required conditions hold; accepted=true |
| Normalized MSSD 1.4023 > 0.1, so correctness fails | Recorded ratio 1.4023323138591388, maximum 0.1, correct=false; rounding/comparison correct. Ratio is normalized, no incorrect length unit asserted |

Acceptance and correctness are separated accurately. The prose makes no
configured-gate/observed-distance claim: omission of the gate is appropriate
because it is not an additional acceptance criterion. No causal, recovery,
industrial-safety or fabricated measurement claim appears.

Prose completeness still fails the rubric's GT qualification: it does not say
GT instance masks were used or that correctness was scored against benchmark
GT, although both returned flags are true. It also does not explicitly label
metrics as recorded in the findings. A valid citation/structured-number check
is not an overall semantic pass.

Separately, the [deterministic scope helper](../frontend/src/evidenceScope.ts#L8)
would disclose GT instance masks, benchmark-GT scoring and recorded metrics for
these returned flags. The [panel](../frontend/src/InvestigationPanel.tsx#L74)
labels this note separately from generated prose. That does not repair the
model's omission. The JSONL captures API output, not a browser screenshot, so
this review does not establish that a particular live screen displayed it.

## Minimal uncommitted repair and checks

- investigation.py: state the existing multi-method comparison precondition;
  request catalogue/summary together for unanswerable questions instead of
  unrelated case metrics, and reserve the last turn for synthesis. General
  instructions only; no case-specific answer, automatic routing or guarantee.
- nebius.py: preserve only the three allowlisted bounded nonnegative integer
  token counters on rejected non-stop completions, if supplied. Partial content,
  reasoning, arbitrary usage fields, prompts and credentials remain excluded.
  This fixes future diagnostic loss, not the unobserved reason for truncation.
- tests/test_investigation.py: reproduce the exact dev-02 semantic rejection
  while confirming strict schema validation, and exercise truncated transport
  replies with valid/missing/malicious usage fields. Failures remain errors,
  findings empty, no retries or automatic comparison substitution.
- This report documents diagnosis; no evaluator, frontend, tool output, request
  cap, provenance, allowlist, schema or rubric changes were made.

Actual check: python -m pytest tests/test_investigation.py tests/test_agent.py
 tests/test_answer_evaluation.py -q: **109 passed in 2.50 seconds**.
Diff whitespace checks passed. No frontend change, so no production build or
browser run was needed. These tests do not certify model prose quality.

## Recommendation and blockers

After reviewing the uncommitted diff, one bounded diagnostic rerun of dev-02
and dev-13 is justified: at most six requests total, same per-request/output/
time limits, one attempt per item, no retries. It would test the clarified
precondition/routing and preserve available length-failure usage. Do not repeat
the old three-item batch merely to seek a better result. No live rerun was
executed or authorized by this offline task. Dev-01 is not an overall quality
pass and its prose omission remains documented; broad quality is unvalidated.

Remaining submission blockers: live/manual validation of the revised instructions,
GT completeness review, project-license authorization, owner eligibility/team
attribution confirmation, judge access, and final video/submission approval.
No licensing decision, commit, push, deployment or submission was performed.


## Follow-up release repair (2026-10-28)

The actual `tests/test_investigation.py` is intact; the suspected duplicated
`def truncated(...)` was a paste/copy artifact. The already-present repair and
focused tests were retained. The system prompt now requires final findings to
identify retrieved metrics/counts as recorded and to disclose case-card
GT-mask/benchmark-GT flags when true. The deterministic panel scope note remains
separate; evaluator expectations and strict local validation are unchanged.

Requested dev-02/dev-13 live rerun was **not attempted**: the configured
process-environment credential check returned false. No secret files were
opened. Billing/credit status could not be checked from the available local
evidence and remains unverified. No captures/reports were created or modified;
prior failure and success records remain preserved. Thus there are no new
live response findings or manual prose verdicts for these two items.

After the prompt repair: `pytest tests/test_investigation.py tests/test_agent.py
tests/test_answer_evaluation.py -q` passed, **109 passed in 2.29 seconds**;
`git diff --check` passed. No frontend/build changes were made. The requested
live validation, dev-01 completeness issue, license authorization, owner
eligibility/attribution confirmation, judge access and final video/submission
approval remain blockers. Do not treat this offline follow-up as live validation.


## Resume attempt (2026-10-28)

Started from clean release branch `release/finish-20261028` at
`445444dd872758eba388b2d893cb045edb18fee3`. Credential availability was
checked without reading files or displaying values: both PowerShell and the
Python process returned unavailable. Per the bounded-run instruction, the live
step stopped before starting either item. No provider requests were made, no
new capture/report directory was created, and all prior captures remain intact.
Billing was not checked. No live outcomes or manual response verdicts exist for
this resume attempt. The requested dev-02/dev-13 run remains blocked on a
credential available to the evaluator process; configure it there, then run
exactly the two existing item IDs once each with the existing limits.
