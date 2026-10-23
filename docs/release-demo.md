# AutoFrame 3D — release and technical demo

Prepared by Juwairiya, 2026-10-23. **Review candidate only. Submission blocked**
by Tasks 3–4, project licensing and final lead approval. No deployment or submission.

## Reproduce locally

Use [verified setup](setup-verification.md) for actual Windows tool versions and
Python interpreter/npm.cmd workarounds. From a reviewed checkout:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
npm.cmd ci --prefix frontend
```

If `python` selects a runtime downloader, use the explicit installed interpreter
as documented in the setup note. Keep the checkout including `demo_assets/`,
`audit_evidence/`, and `frontend/public/assets/`; no full dataset is needed.
Run these in separate terminals:

```powershell
$env:AUTOFRAME3D_SKIP_DOTENV='1'
Remove-Item Env:NEBIUS_API_KEY -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m uvicorn autoframe3d.api:app --host 127.0.0.1 --port 8000
```

```powershell
npm.cmd run dev --prefix frontend -- --port 5173 --strictPort
```

Open http://127.0.0.1:5173; health: http://127.0.0.1:8000/api/health.
Stop servers with Ctrl+C. This is editable checkout installation, not a verified
standalone wheel. Do not click optional baseline replay: it performs new compute
and needs excluded raw data. No full benchmark or evaluation suite is required.

## Technical recording sequence — target 2 minutes 45 seconds

Muskan owns narration/final recording and submission approval. Rehearse offline
now; replace the blocked live segment only with actual approved Task 4 evidence.
Do not publish a recording implying the blocked segment has succeeded.

| Time | Screen action | Narration/evidence |
| --- | --- | --- |
| 0:00–0:15 | Title and Recorded Benchmark tab | “A good geometric fit can still be the wrong pose. AutoFrame 3D helps investigate recorded evidence.” |
| 0:15–0:45 | Example A; point to acceptance and correctness, then enable Benchmark ground truth | “Fitness .922 and RMSE 1.79 mm pass geometric acceptance, while MSSD/diameter 1.4023 fails the .10 correctness threshold. GT is used for benchmark grading.” |
| 0:45–1:15 | Example B baseline, then reciprocal method; download recorded evidence | “This recorded experimental method lowers RMSE from 4.37 to 3.73 mm, but changes MSSD/diameter from .0853 to .1224: correct to wrong. We do not promote it.” Show saved source IDs/JSON download. |
| 1:15–1:40 | Pose Inspection; start five-second preview, pause/resume, then reset | “This separate synthetic animation moves an overlay toward a known reference. The arm stays stationary. It is not autonomous recovery or physical hardware.” |
| 1:40–2:15 | Copilot area / Task 4 evidence, depending on verified status | **Currently:** show disabled Live analysis unavailable; say live integration is unverified. **After approved PASS only:** show one real cited answer and explain live model prose versus deterministic metric cards. No mocked answer substitution. |
| 2:15–2:45 | Limits, attribution, repository/run instructions | “Recorded registration, synthetic visualization and live explanation are distinct. No validated GT-free detector or demonstrated wrong-to-correct recovery. Reproduction and source/asset notices accompany the project.” |

The historical example B comparison above is **PCA initialized**, not the newer
four saved-baseline refinements. If explaining Task 2, use its own report:
all four hypothetical choices prefer refinement, three worsen continuous GT
error, 0/3 recoveries, 0/1 threshold regressions. Do not mix those experiments.

## Current limitations to retain in release text

- GT instance masks and known object identities remain input dependencies;
  geometric acceptance is not correctness or calibrated confidence.
- Four selected saved pairs cannot establish a generally safe selector.
- Synthetic known-reference preview performs no registration or hardware control.
- The copilot explains saved evidence and cannot correct registration. Mocked
  transport tests do not measure model quality; live quality is unverified.
- Saved fitting reproduction needs raw inputs and the historical dirty adapter;
  those are not available in this checkout. Offline saved-pair diagnosis works.
- Tested Windows setup is documented; standalone wheels and other OSes are
  unverified. Production build retains a bundle-size advisory.

## Release gate

| Item | Current state / owner |
| --- | --- |
| Task 1 reproduction and credential-free browser smoke | PASS; Juwairiya |
| Task 2 saved-pair diagnostic and tests | PASS; lead scientific review pending |
| Fresh exported candidate assets/API downloads/missing-key behavior | See final smoke record in release-review note |
| Asset notices retained | Reviewed; see inventory below |
| Secret/raw-input exclusion | Candidate checks documented; not a full-history security audit |
| Project-level open-source license | BLOCKED; team must choose/authorize it |
| Task 3 account/eligibility/credit confirmation | BLOCKED; Muskan |
| Task 4 model compatibility, approved live run and human review | BLOCKED; Muskan/team + technical executor |
| Working judge URL/test build and availability | PENDING; no deployment performed |
| Concise PRs and reviewed merges | Local changes prepared; no commits/pushes/remote PRs yet |
| Final smoke on approved final commit | Repeat after live integration/license changes |
| Final recording, publication/submission approval | PENDING; Muskan |

## Asset inventory checked 2026-10-23

- T-LESS derived display bundles: `demo_assets/manifest.json` and
  `demo_assets/ATTRIBUTION.md`; preserved CC BY-SA 4.0, citation and conversion
  notice. Author's [dataset page](https://cmp.felk.cvut.cz/t-less/) says CC BY 4.0;
  the [toolkit dataset notice](https://github.com/thodan/t-less_toolkit/blob/master/LICENSE)
  says CC BY-SA 4.0. Preserve the existing stricter bundle notice; do not rewrite
  the historical source declaration. Asset checks verify publication hashes.
- Panda arm: `frontend/public/assets/industrial/NOTICE.md`, `PANDA-LICENSE`,
  `PANDA-README.md`, robot buffers/manifest; modified visual mesh attribution
  retained. The [pinned upstream license](https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/71f066ad0be9cd271f7ed58c030243ef157af9f4/franka_emika_panda/LICENSE)
  is Apache-2.0. The bundled model illustrates a stationary arm, not live robot use.
- HDR lighting: Poly Haven foundry, author/change notice and `FOUNDRY-CC0.txt`
  retained. [Poly Haven licensing](https://polyhaven.com/license) states its
  assets are CC0 and permits redistribution.
- Original local assets have `AUTOFRAME-ASSET-LICENSE` (MIT); Three.js notice
  remains in `THREE-LICENSE`. Keep all notices in the source/public assets.
- Asset licenses do not supply a project-wide software license. No blanket
  relicensing or legal eligibility certification was performed.

## Review handoff

Completed: offline setup, saved-pair selection diagnosis, release/demo preparation.
Evidence: setup/diagnostic reports, local screenshots/downloads, final smoke record.
Blockers: account/credits/usage approval, model compatibility/live quality, project
license and lead review. Next: Muskan resolves Task 3; execute the one approved
Task 4 item, review it, then perform final candidate smoke and record narration.
