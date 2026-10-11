# Symmetry scoring audit evidence

Historical held-out result: **23 accepted-and-correct, 177 accepted-but-wrong**.
Corrected aggregate: **24 accepted-and-correct, 176 accepted-but-wrong (88.0%)**.
One label changed due to symmetry translation unit correction. Registration estimates and geometric acceptance did not change.

All 21 affected held-out records were rescored. The 179 unaffected labels were carried forward, including three independently checked controls. This was not a full independent rescore. Audit provenance does not establish the original execution source identity. Ground-truth instance masks were used in the historical registration evaluation; the held-out aggregates have already been inspected.

`REPORT.md` and `audit_summary.json` are explicitly derived publication copies. The summary redacts one absolute local Python executable path. `audit.py` and `rescored_records.csv` are byte-identical copies. `COPY_MANIFEST.json` records both original and publication SHA-256 hashes; never substitute publication hashes for original artifact hashes.

The independent reference source and analytical checks are in `audit.py`; no registration is performed. Its original output-directory behaviour is preserved. To reproduce, copy it to a new unique two-level directory under the repository (such as `artifacts/new_audit_id/audit.py`) before running it with `python -B`. Do not run it inside this versioned evidence directory: it writes its outputs beside itself. Local dataset models/annotations and all historical summaries are required; raw dataset files and bulk generated summaries are intentionally excluded from the repository. The recorded command and environment describe the original audit, not a fresh test execution during publication.
