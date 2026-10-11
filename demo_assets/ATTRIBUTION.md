# T-LESS recorded display assets

T. Hodaň, P. Haluza, Š. Obdržálek, J. Matas, M. Lourakis, X. Zabulis,
*T-LESS: An RGB-D Dataset for 6D Pose Estimation of Texture-less Objects*,
IEEE WACV, 2017. No endorsement is implied.

These derived display JSON files are distributed under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Keep this attribution, license link, and change notice when sharing them.
No additional restrictions are imposed. License legal terms:
https://creativecommons.org/licenses/by-sa/4.0/legalcode.en

License evidence inspected 2026-10-11:
- Author's dataset page https://cmp.felk.cvut.cz/t-less/ expressly licenses
  the work under CC BY 4.0 and requests the citation above.
- Author's toolkit dataset notice
  https://github.com/thodan/t-less_toolkit/blob/master/LICENSE instead names
  CC BY-SA 4.0 (the toolkit software has a separate MIT license).
- Both permit redistribution and adaptation with attribution. The derived
  assets use the more restrictive CC BY-SA 4.0 terms, preserving ShareAlike.
  This does not rewrite the historical CC-BY-4.0 provenance records.
- The three actual local source ZIP directories were inspected; none contains
  a LICENSE, COPYING, or README notice. Sources came from the pinned BOP mirror
  https://huggingface.co/datasets/bop-benchmark/tless/tree/5fd309a04476a842d93abfb584fba9ee7caecdf1
  as documented in existing provenance. No dataset was downloaded here.

Changes: CAD millimetres converted to metres, all positive visible-mask depth
pixels projected through camera intrinsics into camera-frame metres, and
geometry serialized as compact sorted JSON. No decimation, sampling, smoothing,
registration, metric recomputation, or new poses. CAD coordinates remain in the
object frame. Saved transforms are read from the unchanged curated evidence at
runtime. These assets are visualization-only and cannot replace scoring inputs.

`manifest.json` maps each output to actual source files with their verified
hashes, generation parameters, counts, output byte sizes, and SHA-256 hashes.
Output hashes identify this publication, not the historical benchmark execution.

Rebuild offline: `python scripts/prepare_demo_assets.py --dataset <extracted BOP root>`.
Only four source inputs per case are read; no full dataset copy is needed.
