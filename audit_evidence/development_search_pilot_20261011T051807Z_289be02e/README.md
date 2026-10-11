# Development search pilot evidence

The pilot did not demonstrate added value over random search. Both tested local policies were feedback-free, and all five starting poses were already accepted-but-wrong. The predeclared four-candidate budget produced 60 evaluations per method; ten was the permitted maximum. All planned slots ran.

Equal evaluation budgets concealed a coverage limitation: deterministic search included 15 no-op candidates; random included none. First-candidate deterministic rediscovery therefore does not establish failure induction. The representative replay was also a no-op baseline repeat. Replay verification and four focused mocked tests passed as previously recorded, not rerun now. See the later eligibility audit for the fairness review.

These are byte-identical compact copies of the original local experiment artifacts, which remain unchanged. `COPY_MANIFEST.json` records separate original and publication SHA-256 fields. No artifact sanitization was needed. This README is new publication documentation, not an original experiment artifact.

Plans record the actual commands, seeds (where used), dependencies and source/config/manifest/input hashes. Those hashes describe experiment inputs at execution time, not this publication commit or original historical held-out execution. Raw scans, models, environments and replay ZIPs are excluded. Hash inventories may reference excluded local inputs; this evidence directory alone cannot reproduce registration.

The root `scripts/development_search_pilot.py` and `scripts/development_eligibility_audit.py` are the reproduction drivers. With the original local data restored, `--prepare` saves a new uniquely named plan before evaluation; `--run NEW_DIRECTORY` executes it. Do not execute commands against this evidence directory or overwrite completed artifact directories. The eligibility driver also expects the previous pilot artifacts at their recorded `artifacts/` path. Restore byte-identical published copies to that path only if it is absent; preserve any existing local artifacts. Replay requires the excluded original ZIP. The archived pilot `run_with_deadline.py` is execution-source evidence: its output-directory-relative behavior requires a new planned experiment directory, not this published evidence directory.

No tests, replay, registration or experiments were rerun for publication. Previously recorded results retain their original execution provenance.
