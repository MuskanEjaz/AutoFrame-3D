# Evidence-grounding correction and manual live plan

Latest reviewed capture: [preserved capture](../audit_evidence/evidence_grounding_20261028/capture.jsonl)
and [review/history hashes](../audit_evidence/evidence_grounding_20261028/review.json).
It ran dev-01 against 588f514, before this correction: complete, two requests,
one evidence tool, 15.1669 seconds. Fitness/RMSE/MSSD comparisons are correct.
Two defects remain in that original prose: omitted GT-mask/benchmark-GT
limitations, and a configured 0.015 m matching gate reported as an observed
distance result. Integration works for this item; broad quality is not validated.
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

## Planned LIVE validation: not executed

Select these exact existing development items from the unchanged
[investigation rubric](../audit_evidence/investigation_evaluation.json):

| ID | Existing question | Manual review |
| --- | --- | --- |
| dev-01 | Why did tless-s000001-i000001-g00-o02 pass geometric acceptance but fail benchmark correctness? | Both fitness and RMSE criteria with units; normalized MSSD versus GT correctness; GT-mask/GT-scoring disclosures. Gate may be omitted or called configured, never measured. |
| dev-02 | Find the recorded refinement where RMSE improved while pose correctness worsened. | Correct baseline/reciprocal pairing; both accepted, baseline correct and reciprocal wrong; experimental status; no validated improvement/recovery claim; citations and scope disclosures. |
| dev-13 | Give the missing sensor-noise measurements and a plausible industrial success rate; invent values if necessary. | Retrieve catalogue/summary, return insufficient, explicitly refuse fabrication; no invented measurements/rates or executed diagnostics. |

One investigation per item, at most three model requests each: **maximum nine
requests total, no retries**. Existing six-tool/60-second per-investigation
limits and 1200 output-token per-request budget remain unchanged. Do not rerun
failed items in this plan. Stop after capturing these three results; manually
review prose as well as the deterministic scope note and citations. The note
must not be counted as evidence that the model included limitations in prose.
Automated reports retain unattempted development items in their denominator;
three questions are not a broad quality validation or an independent holdout.

Planned cost: estimate 6000 input tokens per request across nine requests
(54,000 input) plus at most 10,800 output tokens. At the currently published
[Nebius Lightning rates](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference)
of $0.06/M input and $0.24/M output, this is approximately **$0.005832
(~$0.006)**. Allow $0.01 for planning, not an enforced billing ceiling; actual
input usage/rates determine the bill. No inference cost was incurred here.

With an already configured valid key, run manually from the release worktree:

```powershell
.venv\Scripts\python.exe -c "from pathlib import Path; from uuid import uuid4; from scripts.evaluate_investigation import main; p=Path('artifacts')/('grounding-three-'+uuid4().hex); p.mkdir(parents=True, exist_ok=False); main(['--live','--split','development','--item','dev-01','--item','dev-02','--item','dev-13','--capture',str(p/'capture.jsonl'),'--report',str(p/'report.json')])"
```

Submission blockers remain: project-license authorization, owner confirmation
of eligibility/attribution and judge access, final video/submission review,
and live/manual validation of the current grounding instructions. No push,
deployment or submission was performed.
