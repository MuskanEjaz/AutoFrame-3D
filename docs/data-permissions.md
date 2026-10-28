# Third-party data and asset permissions

Verified against primary upstream sources on 2026-10-28. Original project code
is [MIT](../LICENSE); that grant does not cover third-party material.

## T-LESS: exact affected files and remaining question

The [authors' dataset page](https://cmp.felk.cvut.cz/t-less/) states CC BY 4.0.
The [authors' toolkit dataset notice](https://raw.githubusercontent.com/thodan/t-less_toolkit/master/LICENSE)
states CC BY-SA 4.0 for the dataset, separately from its MIT toolkit code.
These primary statements still disagree. Neither is merely a citation or a
repository-availability inference. No upstream clarification was obtained.

Affected redistributed geometry:

| File | Underlying inputs |
| --- | --- |
| `demo_assets/accepted-wrong.json.gz` | CAD object 2; scene 1/image 1 depth, visible instance mask 0 and camera intrinsics |
| `demo_assets/control-regression.json.gz` | CAD object 7; scene 2/image 24 depth, visible instance mask 2 and camera intrinsics |

[manifest.json](../demo_assets/manifest.json) maps exact source names and hashes.
[ATTRIBUTION.md](../demo_assets/ATTRIBUTION.md) supplies authors, citation,
conversion/change notice and the existing CC BY-SA 4.0 bundle terms.
`audit_evidence/recorded_benchmark_demo/demo.json` contains saved metrics,
transforms, provenance and source references; it is not raw mesh/depth data.
Raw dataset archives, CAD PLYs, depth and mask PNGs are not bundled here.
Screenshots of recorded geometry are also subject to underlying attribution;
see [screenshot notices](screenshots/NOTICE.md).

The specific unresolved question is which of the two dataset grants governs
the pinned BOP source revision and these two converted CAD/depth bundles.
[CC BY](https://creativecommons.org/licenses/by/4.0/legalcode.en) and
[CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/legalcode.en) both
permit sharing/adaptation subject to their conditions. The existing attribution,
change notice and ShareAlike treatment are retained; this is not an assertion
that one upstream statement supersedes the other, nor a new permissions grant.
Owner review of the exact source/version remains a publication action.

### Alternative if the team cannot approve bundled-data distribution

Do not silently remove the current viewer assets. A separately reviewed
source-only distribution can retain the MIT application, notices and source
preparation instructions while letting each reviewer acquire authorized
T-LESS inputs under upstream terms. With the exact eight inputs listed in the
manifest available in an extracted BOP root, regenerate locally:

```powershell
.venv/Scripts/python.exe -B scripts/prepare_demo_assets.py --dataset <authorized-extracted-BOP-root> --output demo_assets
```

The script validates input hashes before writing the two geometries. This
path needs external data and is not the key-free bundled quick start. Its
missing-input behavior is tested; a new raw-data rebuild was unavailable here.
The synthetic preview requires no T-LESS inputs and remains a separate demo.
A source-only distribution has not been created or published in this task.

## Other bundled material

- Panda visual meshes: [NOTICE](../frontend/public/assets/industrial/NOTICE.md),
  [Apache-2.0](../frontend/public/assets/industrial/PANDA-LICENSE), upstream
  revision and changes retained. No new manufacturer permission is asserted.
- Poly Haven foundry HDR: same notice identifies authors and the unmodified
  local file; [CC0 text](../frontend/public/assets/industrial/FOUNDRY-CC0.txt) retained.
- Original local scene designs: existing [asset MIT notice](../frontend/public/assets/industrial/AUTOFRAME-ASSET-LICENSE).
- Three.js: [MIT notice](../frontend/public/assets/industrial/THREE-LICENSE).
  Other dependencies retain upstream licenses; no blanket relicensing.
