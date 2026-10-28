# Final release verification — 2026-10-28

Recovered clean `release/finish-20261028` at `cf8b960`; no applicable AGENTS.md
was found in the worktree. Implementation tested and committed as
`ceb5b60a78e3fc13257626fc004754e8251d3933`. Documentation/screenshots follow in a
separate commit. No sibling checkout/service was used or changed.
[Portable check record](../audit_evidence/release_verification_20261028/checks.json).

## What changed and why

- Unavailable-comparison cards now explicitly state that no recorded method
  comparison exists for the case; they contain no invented metrics.
- Completion scoring now fails when required evidence/facts, citations,
  provenance or trace integrity fail. Returning an unavailable card cannot
  satisfy a requested comparison. This tightens scoring, not the unchanged rubric.
- The existing one-request probe now uses `model_name()` rather than ignoring
  configured NVIDIA model overrides. Its CLI still reports creation, not quality.
- HTTP redirects are rejected; they cannot silently add requests or forward a key.
- `validate_release_live.py` reuses the probe then runs only development dev-01,
  dev-02 and dev-13 once each, with a global ten-attempt ceiling. No reserved
  question is selected for live execution. It stops after diagnostic failure or
  a later HTTP/configuration rejection and saves failures without retry.
- The direct PowerShell launcher uses hidden input, validates/normalizes only
  surrounding whitespace, sets a child-only credential, and cleans unmanaged
  memory/references in finally. It was parsed, not executed live.

## Actual checks and limits

| Check | Actual result |
| --- | --- |
| Release backend: investigation, evaluator, bounded runner, recorded demo/assets | 122 passed, 1 skipped; raw-source rebuild optional/unavailable |
| Frontend scope/pose tests | 8 passed |
| Production TypeScript + Vite 7.3.7 | Passed sequentially with explicit 384 MiB old heap / 2 MiB semi-space; existing >500 kB warning |
| Broader backend excluding saved reciprocal module | 168 passed, 1 skipped, 4 failed: raw T-LESS inputs absent |
| Full backend suite | Not passing: saved reciprocal tests require absent `_refine_icp`; initial broad run also exhausted host memory |
| Real Edge production UI | Recorded cases/geometry, method switching, acceptance vs correctness, GT reveal/qualifications and JSON export passed |
| Real synthetic UI | Known-reference labels, playback, pause/reset and synthetic state export passed |
| Intercepted error fixtures | Loading, duplicate prevention, citation navigation, provider error/timeout, HTTP failure and recovery passed |
| Desktop/mobile | 1440x1000 and 390x844; no mobile horizontal overflow, console errors, exceptions or remote requests |
| Provider calls this task | 0: credential unavailable at the single availability check |

[Browser results](../audit_evidence/release_verification_20261028/browser.json)
distinguish production checks from six intercepted fixture POSTs. No fixture
request reached inference. Screenshots were visually inspected before inclusion;
they show real recorded/synthetic modes, not a fake live answer.
Production services used isolated ports 8012/5192/9232 and a fresh browser profile.

The full-suite failures are not hidden by changing tests or adding skips.
`tests/test_saved_pose_reciprocal.py` assumes a missing research helper; raw-data
`tests/test_tless_api.py` needs unbundled scene/camera/model inputs. No fitting
algorithm was reconstructed, no raw dataset downloaded and no historical
registration rerun. The supported recorded viewer does not need those inputs.
Clean-install commands reuse prior setup evidence; no fresh OS/install was claimed.

## Current official integration comparison

Checked 2026-10-28 against Nebius's [API introduction](https://docs.tokenfactory.nebius.com/api-reference/introduction),
[structured outputs](https://docs.tokenfactory.nebius.com/ai-models-inference/json)
and [NVIDIA model page](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference).
The API introduction supports the fixed `/v1/chat/completions` endpoint and
bearer authentication. The model page names `nvidia/Nemotron-3_5-Lightning`.
Structured-output documentation includes the named `name`/`schema` envelope;
some examples still show bare schemas. The existing named envelope and strict
local schema validation remain; no speculative parameters/provider substitution.
These source checks do not establish current account authorization or inference.

## Preserved history and separate verdicts

| Run | Attempts and actual verdict |
| --- | --- |
| Original three-item batch | 3/15 development items, 9 model requests: dev-01 complete (3 requests/2 tools), supported numerical comparisons but missing recorded/GT qualifications and no measured-gate claim; dev-02 unavailable comparison (3/3); dev-13 turn-3 truncation (3/3) |
| Earlier separate dev-01 | 2 requests / 1 tool; unsupported measured 0.015 m gate claim; not the original batch result |
| Later two-item batch | 2/15 development items, 2 model requests: each HTTP 401, invalid_request_error category, zero tools/findings; underlying cause unresolved |
| This task | 0 diagnostic requests, 0 investigation requests; live/manual verification unperformed |

[Original three-item capture/report](../audit_evidence/grounding_three_20261028/capture.jsonl)
are published as byte-identical portable copies. The
[earlier standalone capture](../audit_evidence/evidence_grounding_20261028/capture.jsonl)
and [later 401 capture](../audit_evidence/grounding_two_20261028/capture.jsonl)
remain distinct. [Original hashes](../audit_evidence/release_verification_20261028/history-hashes.json)
were rechecked: original captures/reports, rubric, GT and dataset identities
were not changed. Existing report verdicts were not rewritten under the new scorer.

## One direct live launcher and manual review

Run from the checkout root only under the existing bounded authorization:

```powershell
& ./scripts/run_release_validation.ps1
```

It invokes the reviewed scripts in one credential-bearing child Python process.
The diagnostic permits 128 output tokens, 20 seconds and 32 KiB accepted response;
only `response_received` allows investigations. Each investigation retains
3 requests / 6 tools / 60 seconds, <=20 seconds/request, 1,200 output tokens,
32 KiB accepted response; no retries, no budget increase. Oversize detection
reads one extra byte. Fresh GUID paths avoid overwriting evidence. Do not repeat
this authorization after a failed attempt. The program summarizes counts and
writes captures/reports; exit zero is not a semantic quality pass.

Manual review for each attempted item must record the exact question, status,
retrieved cards and citations, correct case/method pairing, numerical values
and units, fitness/RMSE acceptance versus benchmark correctness, explicit
recorded/GT qualifications, configured gate versus observed metric, and
refusal to fabricate missing sensor/industrial measurements. Provider errors
are task failures, not evidence-supported abstention. Retain unattempted items
in the development denominator. No new answer exists for such review yet.

## Final package review

Changed local Markdown links/anchors, exact staged credential/path patterns,
image notices, original hashes, MIT text and whitespace were checked before
the docs commit: no missing local targets or selected-pattern hits.
Screenshots and portable JSON contain no browser profile, key, raw provider
body, local account path or credential header. Selected-pattern scans do not
certify all Git history. Third-party notices remain separate from project MIT;
[permission review](data-permissions.md) and [requirements](hackathon-requirements.md)
identify concrete remaining owner actions. No publication or submission here.
