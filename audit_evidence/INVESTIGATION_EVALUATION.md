# Investigation answer-quality evaluation

No live Nemotron model quality has been measured. This harness evaluates saved
responses offline; hand-authored fixtures verify the evaluator, not the model.
The runtime prompt and frozen registration evidence are unchanged.

The versioned rubric has **15 development** and **5 reserved regression** items,
declared before evaluation changes. They cover acceptance/correctness, recorded
method regression, aggregate/selective-rescore scope, units and boundary rules,
GT dependence, provenance, unknown cases, unavailable measurements, misleading
premises, fabrication/omission requests, and comparisons across records. Reserved
questions use the **same corpus**; they are not an independent scientific holdout.
Keep them reserved while developing prompts; reporting them does not establish
scientific generalization. IDs and split membership are stable.

## Offline scoring

```powershell
.\.venv\Scripts\python.exe -B scripts/evaluate_investigation.py --responses artifacts/saved_answers.jsonl --split development --report artifacts/dev_report.json
```

Omit `--responses` to report all selected items missing, without any request.
Reports and live captures refuse overwrites. A saved JSONL row contains:

```json
{"item_id":"dev-01","response":{},"trace":[],"fixture_label":"optional fixture disclosure","numerical_claims":[]}
```

`response` is the complete investigation response, not the empty placeholder
above. `trace` is the caller-owned list populated by
`investigate(request, trace=trace)`: provider starts/results and actual tool
attempts/results, without credentials or raw provider bodies. Old responses
without traces can be scored, but retrieval and request counts remain unverified.
These traces are self-recorded execution observations, not signed provenance.
Question text, evidence identity, allowlisted arguments, event order, counters,
tool outputs, three-turn/six-tool budgets, per-turn timeout and recorded runtime
are checked. The runtime check allows one second of bookkeeping beyond its
60-second deadline; it cannot prove externally measured service timing.

Reports separate schema, completion status, retrieval coverage, citation validity,
evidence-card integrity, numerical accuracy, tool trace, expected abstention,
and unsupported-claim review. Missing responses and provider failures stay in
the full selected-split denominator, even with `--item`. No overall score is
computed. A `status_pass_review_required` is only a protocol result, not task
success. Empty evidence, invented IDs and citations to unretrieved records are
not accepted as successful grounded answers.

Complete structured cards are compared against deterministic tools. Optional
**manually extracted** numerical claims can additionally be supplied as
`{evidence_id,path,value,unit}`; only rubric-listed facts are accepted. Explicit
units must match, with the per-fact tolerances recorded in the rubric. Counts and
thresholds are exact; two-decimal millimetre claims allow 0.005 mm and four-decimal
ratios allow 0.00005, representing half the last displayed digit. Structured
cards themselves must match to 1e-9 absolute. These checks do **not** extract or
certify numerical claims in prose. Correct cards can accompany false prose.

Every response therefore retains human-review requirements for prose entailment,
completeness, overgeneralization/forbidden conclusions and appropriate abstention.
Review against each item's required facts/prose and forbidden conclusions.
Do not infer semantic correctness from keywords, schema, citations or status.
The GT-free overclaim fixture intentionally passes structural checks but remains
flagged for human review. Request counts come from observed provider starts;
latency comes from captured runtime; token usage is reported per provider return
only when present, with completeness indicated. Missing usage is not zero.
Fixture telemetry is synthetic and explicitly labelled.

Fixtures in `tests/fixtures/answer_evaluation/` cover supported answers, wrong
numbers/units, unretrieved citations, fabricated cases, GT-free overclaims,
appropriate insufficiency, provider failure and incomplete investigations.
Focused verification:

```powershell
$env:AUTOFRAME3D_SKIP_DOTENV='1'
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp artifacts/answer_eval_tests_new tests/test_answer_evaluation.py tests/test_investigation.py
```

Current result: **38 passed in 1.95 seconds**. No browser/build rerun was needed;
frontend code is unchanged. No inference, downloads, registration or training ran.

## Later untuned live baseline — explicit opt-in only

Not executed in this task. Supply `NEBIUS_API_KEY` securely through the process
environment; the evaluation runner never loads `.env`. Existing server-side
Nemotron configuration is used. Do not put credentials in arguments or captures.
Start with one development item, then review the result before a full baseline:

```powershell
.\.venv\Scripts\python.exe -B scripts/evaluate_investigation.py --live --split development --item dev-01 --capture artifacts/baseline_one.jsonl --report artifacts/baseline_one_report.json
```

This permits **at most 3 API calls**, 6 read-only tool attempts and a 60-second
investigation deadline (20 seconds per provider turn, no retries). Its report
still has a 15-item denominator, with 14 items missing. For the full development
baseline, omit `--item` and choose new capture/report paths: **15 investigations,
at most 45 API calls, 90 tool attempts, 900 seconds of investigation budgets**.
`--split reserved` permits 5 investigations / at most 15 calls / 30 tool attempts;
`--split all` permits 20 investigations / at most 60 calls / 120 tool attempts.
Runs are sequential and failures remain saved; no automatic retries occur.
These bounds derive from `MAX_TURNS=3`, `MAX_TOOLS=6`, and the selected item count.
Timed-out transport workers may finish afterward, as in the existing integration.
No LLM judge, extra provider, downloads or training are introduced.

## Training decision

Registration is classical PCA/ICP, not a trained network. Registration-model
training and Nemotron fine-tuning are separate tasks; raw T-LESS assets are not
a ready-made copilot instruction dataset. Establish an untuned live baseline
first. Fix retrieval, evidence structure or prompt problems before considering
fine-tuning. Consider it only after recurring measured failures and enough
suitable training examples justify it. Never train on reserved evaluation
questions and then report their results as generalization. Current evidence
does not justify fine-tuning. Live Nebius/NVIDIA integration remains UNVERIFIED.
