# Task 4 — bounded live integration preparation

Prepared 2026-10-23. **Live integration: BLOCKED / NOT EXECUTED.**
Task 3's public-rule research is complete; private access, credit balance,
organizer follow-up and personal/team confirmations are still unresolved.
This preparation is not a model-quality result or an eligibility certificate.

## Implementation and official documentation review

- `autoframe3d/nebius.py` sends bearer-authenticated Chat Completions to fixed
  `https://api.tokenfactory.nebius.com/v1/chat/completions`, matching the
  [official quickstart](https://docs.tokenfactory.nebius.com/quickstart).
  There are no transport retries; provider bodies/errors are not exposed.
- `autoframe3d/investigation.py` bounds an investigation to three inference
  turns, six read-only tool attempts, 60 seconds overall, 20 seconds per request,
  1,200 output tokens per turn and 32 KiB response bodies. A timed-out worker
  may finish after the caller returns; caller timeout is not proof of cancellation.
- Default model is `nvidia/Nemotron-3_5-Lightning`; `NEBIUS_MODEL` can override
  it with an NVIDIA Nemotron identifier. The client validates spelling pattern,
  not model availability. The [public model catalog](https://tokenfactory.nebius.com/models)
  returned no readable model listing during this check; an exact-ID search
  yielded no results. Model availability, pricing and JSON support remain
  UNCONFIRMED; verify in the official console/catalog before execution. Do not
  silently switch model or provider.
- The request uses `response_format: {type: json_object}` plus `guided_json`.
  The [current structured-output guide](https://docs.tokenfactory.nebius.com/ai-models-inference/json)
  documents schema output through `response_format` with `json_schema`, and
  arbitrary JSON through `json_object`; support depends on model capability.
  No current documentation for `guided_json` was found in this review. This is
  a compatibility question, not an observed provider failure. Resolve against
  the chosen model's official documentation/support before spending; no
  speculative runtime change was made. Local Pydantic action/citation validation
  remains active regardless of provider formatting.

## Prepared first item and budget

Use existing `scripts/evaluate_investigation.py`, **development item `dev-01`
only**. It asks why object 2 passes acceptance but fails correctness. This
captures the response, deterministic evidence, tool trace, requested model,
runtime and provider token usage when available. It does not save raw provider
bodies or credentials. Review model-generated text before sharing the capture;
do not treat local artifacts as automatically redacted/publication-ready.

Maximum: one investigation, **up to three inference requests**, six tools,
no retries, at most 3,600 generated output tokens across the requests. Input
tokens depend on prompts/schema/tool results; 3,600 is not a total-token or
currency limit. Establish a monetary bound from actual model prices, input
budget and account controls before approval. Any paid provisioning/idle resources
would need separate consideration; this plan only uses Token Factory inference.

Before execution Muskan/team must record:

- [ ] Supported account access and card-free arrangement resolved.
- [ ] Credits actually present, remaining amount and expiry verified.
- [ ] Exact NVIDIA model ID, structured-output compatibility and prices verified.
- [ ] Maximum requests/cost and explicit team approval recorded privately.
- [ ] Choose a new capture/report path; preserve failures and do not retry automatically.

No request is authorized merely because a key exists. The command below is
prepared, **not executed**, and must wait for all prerequisites above.

## Secure local credentials and one-item command

Muskan can run this on her own machine with the reviewed checkout. Enter the
key through a masked prompt in a private local PowerShell terminal; never put
the literal key in the command, chat, screenshots or a committed file:

```powershell
$integrationKey = Read-Host 'Nebius API key' -AsSecureString
$env:NEBIUS_API_KEY = [System.Net.NetworkCredential]::new('', $integrationKey).Password
# Set NEBIUS_MODEL only after its exact identifier is verified and approved.
New-Item -ItemType Directory -Force artifacts/live-dev01-approved | Out-Null
try {
  .\.venv\Scripts\python.exe scripts/evaluate_investigation.py --live --split development --item dev-01 --capture artifacts/live-dev01-approved/capture.jsonl --report artifacts/live-dev01-approved/report.json
} finally {
  Remove-Item Env:NEBIUS_API_KEY -ErrorAction SilentlyContinue
  Remove-Variable integrationKey -ErrorAction SilentlyContinue
}
```

Run this in a dedicated terminal without a transcript or screen recording.
The existing script refuses to overwrite capture/report files and does not
load `.env`. For a later explicitly approved attempt choose another directory.
Do not additionally run `investigation_smoke.py --live`: that would consume
another investigation, beyond this single-item plan.

## Manual review and outcome record

Record PASS/FAIL/BLOCKED, tested commit, verified/requested model and provider
identity if returned, timestamps, trace, citations and usage when available.
The capture identifies the requested model; raw provider-returned model identity
is not preserved by the current dispatcher, so do not claim independently
verified serving identity from that field alone. Missing usage must be marked
unavailable, not zero.

For `dev-01`, a human reviewer checks support for fitness approximately .921744,
RMSE 1.794620 mm, MSSD/diameter 1.402332, and thresholds .70 / 10 mm / .10.
Required evidence ID: `case:tless-s000001-i000001-g00-o02:baseline`.
The answer should distinguish acceptance from correctness and acknowledge GT
masks/benchmark scoring. It must not infer a proven root cause, industrial
safety, GT-free detection or autonomous recovery. Unsupported hypotheses must
be qualified; insufficient evidence should produce appropriate abstention.

The evaluation report includes the whole development denominator with only one
attempt; do not present that as full-suite performance. Script exit zero only
means a report was written, not model quality PASS. Failure/incomplete results
are evidence to review before any separately approved larger evaluation.

## Verification actually completed

- **38 focused tests passed**: `tests/test_investigation.py` and
  `tests/test_answer_evaluation.py` (3.32 seconds). Mocked behavior verifies
  validation/budgets/harness handling, not live model quality.
- A separate credential-free check blocked socket connections and returned
  `unavailable`, zero model turns, zero tools and an empty trace. Local record:
  `artifacts/task4-preparation/missing-key.json` (ignored).
- No credentials were read or configured, no live request occurred, no provider
  was substituted, and no full evaluation suite was run.

Actual live response, live token usage/timing and human-reviewed live answer:
**UNAVAILABLE**. Task 4 preparation is ready for access/compatibility review;
Task 4 completion requires the approved live attempt and manual review above.
