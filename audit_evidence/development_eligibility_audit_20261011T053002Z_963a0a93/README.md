# Development eligibility audit evidence

The fresh, once-only audit found 1 accepted-and-correct and 29 accepted-but-wrong cases among 30 preselected development cases, with no operational failures or unfinished cases. This verified pool is insufficient for the proposed five-case conditional pilot; it does not prove the full 768-case development split lacks five eligible starts.

Selecting starts by baseline correctness is intentional. Future experiments on them measure robustness conditional on initial success, not unconditional failure rate or generalization. GT instance masks and GT-dependent symmetry-aware correctness are disclosed in the report. Registration and frozen scoring thresholds were unchanged.

These are byte-identical compact copies of the original local experiment artifacts, which remain unchanged. `COPY_MANIFEST.json` records separate original and publication SHA-256 fields. No artifact sanitization was needed. This README is new publication documentation, not an original experiment artifact.

Plans record the actual commands, seeds (where used), dependencies and source/config/manifest/input hashes. Those hashes describe experiment inputs at execution time, not this publication commit or original historical held-out execution. Raw scans, models, environments and replay ZIPs are excluded. Hash inventories may reference excluded local inputs; this evidence directory alone cannot reproduce registration.

The root `scripts/development_search_pilot.py` and `scripts/development_eligibility_audit.py` are the reproduction drivers. With the original local data restored, `--prepare` saves a new uniquely named plan before evaluation; `--run NEW_DIRECTORY` executes it. Do not execute commands against this evidence directory or overwrite completed artifact directories. The eligibility driver also expects the previous pilot artifacts at their recorded `artifacts/` path. Restore byte-identical published copies to that path only if it is absent; preserve any existing local artifacts. Replay requires the excluded original ZIP. The archived pilot `run_with_deadline.py` is execution-source evidence: its output-directory-relative behavior requires a new planned experiment directory, not this published evidence directory.

No tests, replay, registration or experiments were rerun for publication. Previously recorded results retain their original execution provenance.
