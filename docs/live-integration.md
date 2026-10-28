# Task 4 â€” bounded live integration preparation

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
- Reviewed 2026-10-28: the [official structured-output guide](https://docs.tokenfactory.nebius.com/ai-models-inference/json) documents `response_format` with `type: json_schema` and a `json_schema` field containing the schema (Python example). Investigation now uses that documented form instead of undocumented `guided_json` plus `json_object`. Schema remains in the prompt; local Pydantic action/citation validation and all limits remain unchanged. Mocked request assertions cover the exact schema, absence of guided_json, output cap and transport limits. This resolves request syntax against documentation, not actual model compatibility. The public catalog still returned no readable listing; the configured model ID is preserved and exact-model JSON support remains UNVERIFIED.

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

## Current release preparation — 2026-10-28

The user reports active billing, a $25 balance, a public NVIDIA Nemotron-3.5-Lightning endpoint, and displayed per-million-token prices of $0.06 input, $0.03 cached input and $0.24 output. These supersede the earlier unknown-balance context; no console access or inference was performed here. Keep live integration/model quality UNVERIFIED.

Cost preparation for dev-01: three requests maximum, six read-only tools total, 60 seconds overall, 20 seconds/request, 1,200 output tokens/request (3,600 total), 32 KiB provider body/request and 12,000 content characters/request. Question input is capped at 1,500 characters; tools expose only finite committed cards. Largest serialized card measured here: 1,460 bytes. A deliberately loose input proxy counts both prior responses at 48,000 UTF-8 bytes each, all six cards at every turn, and 2,000 bytes per turn for framing, yielding 334,020 input bytes over three requests. Assuming at most one billed input token per byte gives about $0.02091 including maximum output; budget $0.03 for this one attempt with no cache discount. This is a conservative estimate, not an enforced currency/token bound: exact tokenizer, provider framing/accounting, reasoning billing and price changes are uncertain. No retry or provider swap is allowed.

Use a fresh GUID directory for capture/report, explicitly set the preserved model ID, and use the masked-key command below only after live execution is authorized. The script never loads dotenv and refuses existing output files.

```powershell
$env:AUTOFRAME3D_SKIP_DOTENV = '1'
$env:NEBIUS_MODEL = 'nvidia/Nemotron-3_5-Lightning'
$livePath = Join-Path 'artifacts' ('live-dev01-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $livePath -ErrorAction Stop | Out-Null
$integrationKey = Read-Host 'Nebius API key' -AsSecureString
try {
  $env:NEBIUS_API_KEY = [System.Net.NetworkCredential]::new('', $integrationKey).Password
  & .\.venv\Scripts\python.exe -B scripts/evaluate_investigation.py --live --split development --item dev-01 --capture (Join-Path $livePath 'capture.jsonl') --report (Join-Path $livePath 'report.json')
} finally {
  Remove-Item Env:NEBIUS_API_KEY -ErrorAction SilentlyContinue
  Remove-Variable integrationKey -ErrorAction SilentlyContinue
}
```

The reported `--splitdevelopment` typo is absent from this merged checkout; existing examples already use `--split development`. No historical evidence was changed. The committed adapter lacks `_refine_icp`, required by the historical saved-pose fitting runner. Do not reconstruct it from embedded source or run registration. Saved selection diagnosis remains reproducible from hash-verified records; fitting reproduction additionally needs missing research code and raw data. No project-level LICENSE or license declaration exists in pyproject.toml; owner license selection remains a release blocker. Third-party notices remain intact. Synthetic playback is a reference-guided animation, not automatic pose recovery.
