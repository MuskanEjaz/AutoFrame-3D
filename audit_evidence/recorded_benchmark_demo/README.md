# Curated recorded demo evidence

`demo.json` is a **derived curated copy**, not an original execution artifact. Original audit and refinement artifacts are unchanged. Source file hashes, configuration identity and required local geometry input hashes are recorded in the file; `COPY_MANIFEST.json` separately records this publication's hash.

`reciprocal_results.jsonl` is a byte-identical, 4,454-byte copy of the original four-case reciprocal verification results, including the demonstrated correct-control regression. Each curated variant identifies its versioned source copy through `publication_copy`; baseline records are in the previously versioned eligibility evidence. Original artifact paths remain recorded separately. These copies establish the saved numbers and transforms, not the original execution environment or source identity.

Example A is the accepted-but-wrong object-2 baseline from the fresh eligibility audit. Example B joins the saved reciprocal object-7 estimate/metrics to that same case's saved baseline GT annotation. Identical raw inputs and frozen thresholds were checked before this derived join. Both estimated transforms are saved; the API loads existing local scan/CAD geometry and applies them without registration. No geometric data was fabricated.

Current recorded outcomes: object 2 baseline MSSD/D 1.402332; object 7 baseline 0.085304 versus reciprocal 0.122415. Object-7 RMSE improves from 4.371645 to 3.727941 mm, while correctness regresses. Reciprocal is explicitly experimental and rejected for promotion.

Raw scans/models remain local and are not embedded here or in the frontend bundle. The metadata/evidence export works without those files; the 3D view checks required local input hashes. Publication/source hashes do not establish original historical held-out execution identity. See the separate preserved scoring audit for its partial-rescore caveats, and [../../DEMO.md](../../DEMO.md) for launch and presentation instructions.
