# Pose Inspection — synthetic demo

This workspace supersedes the earlier assembly-placement UI. Open
http://127.0.0.1:5173/ using the existing README launch commands. The robot's
solid gripper is attached flush to its flange and stays stationary. Only the
estimated CAD overlay moves. The amber mismatch, restrained cyan reference
overlay, axis–angle correction, scanner toggle and five-second animation are
synthetic illustrations, not evidence of automatic pose recovery.

Recorded Benchmark remains in its own top-level tab: actual saved T-LESS
geometry, methods, metrics, ground-truth reveal, missing-key copilot state and
recorded evidence exports. Synthetic state exports explicitly identify the
procedural robot and known reference; no benchmark metric describes this robot.
The legacy experimental workbench remains at `?workbench=1`.

## Coordinate convention and correction

`poseMath.ts` defines a fixed right-handed **Demo scan frame**, +Z up. Physical
lengths are metres; UI translations are millimetres. Orientations are unit
quaternions in xyzw order. Numeric rotation entry uses XYZ Euler angles in the
scan frame, while rotation differences use quaternion relative rotation.

The robot fixture has a non-identity parent: translation (0.02, 0.01, 0) m and
−0.08 rad rotation around scan Z. Its local wrist transform is translation
(0.39, 0, 0.69) m; the local gripper mating offset is (−0.055, 0, 0) m. The known
reference part transform is:

`T_reference = T_fixture * T_wristLocal * inverse(T_gripperMatingLocal)`.

Observed geometry uses the fixture parent plus local part transform; overlay
poses use scan-frame transforms. They share the exact same mesh buffers and
local mesh transforms, so they genuinely coincide. No render-only rescaling
changes the physical coordinates.

The inspector shows **origin displacement** `t_reference − t_estimate`, and
the shortest **relative rotation** `R_reference * transpose(R_estimate)`.
Its axis is expressed in the scan frame. Quaternion sign equivalence is handled
by choosing the nonnegative-w representative. A zero-angle axis is undefined
and displayed as [0, 0, 0] with an explicit note.

Synthetic JSON export separately includes the column-major **full rigid
correction** `T_reference * inverse(T_estimate)` and specifies left multiplication:
`T_corrected = T_correction * T_estimate`. Its translation is not the origin
displacement when the estimate rotates about a nonzero scan-frame origin.

Configurable synthetic demo tolerances in `poseMath.ts` are ≤1 mm and ≤1°,
both evaluated at full precision. They establish no manufacturing accuracy,
collision clearance or benchmark correctness. The synthetic demo computes no
RMSE, registration, live scanner acquisition or inference.

## Playback and interaction

The main viewport interpolates the user's current estimate to the known
reference over five elapsed seconds, using linear translation and quaternion
SLERP. Play/Pause, Resume, Replay and Reset are available. The original estimate
is retained separately; restoring it explicitly enables editing again. Reset
restores the deterministic initial mismatch. Conflicting edits are disabled
throughout preview; camera and visibility controls remain available.

Hidden-document visibility events suspend animation-frame work and timing;
visible playback resumes without counting hidden time. Reduced motion shows
the aligned result immediately. The render loop avoids rendering unchanged
scenes and suspends when hidden. Optional transform gizmos affect only the
estimate and disable orbit while dragging. Numeric entry rejects blank,
nonfinite and invalid values without changing the estimate.

## Assets and visual limitations

The stationary arm uses locally bundled Panda visual meshes converted from
MuJoCo Menagerie (Apache-2.0). Gripper, scanner, workcell and surface patterns
are original local assets. Reflections use the bundled Poly Haven Industrial
Workshop Foundry HDR environment (CC0), with a local fallback. See the current
[asset notices](frontend/public/assets/industrial/NOTICE.md) for authors,
source revisions, modifications and licenses. Runtime assets load locally;
this workspace makes no paid-service or model calls. The scanner is
decorative: nine bounded rays aimed at the solid gripper terminate at first
surface intersections and never produce measurements or affect pose errors.

The geometry is illustrative, not an accurate manufacturer's model. Camera,
palette, flange construction and amber/cyan overlay composition follow the
approved reference, but procedural surfaces and workshop context are visibly
simpler than its photographic robot, reflections and factory background.

## Verification

Run `node --test tests/pose.test.mjs` in `frontend` and `npm run build`.
Five focused tests cover rotated parents and local offsets, known displacement
and rotation, full correction left multiplication, q/−q equivalence, near-zero
axis handling, tolerance boundaries, preview endpoints, original-estimate
preservation, deterministic reset, invalid numeric input and synthetic export.

Installed Chrome with the existing temporary Playwright tooling inspected
1440×900 desktop and 390×844 mobile. Generated artifacts are in
`artifacts/pose-browser/`: `initial.png`, `mid-preview.png`, `aligned.png`,
`reference-overlay.png`, `mobile.png`, benchmark screenshots and evidence
downloads, plus `results.json`. These are local artifacts excluded from the
implementation commit. Browser checks compare actual rendered object matrices,
verify stationary observed geometry, displayed origin corrections, coincident
preview completion, pause/resume/replay/reset, overlay toggles, numeric edits,
invalid input, reduced motion, synthetic export and mobile width. A simulated
hidden-document visibility event verifies that preview timing suspends. Recorded
examples, methods, GT reveal, evidence download and copilot remain separate.
No inference, research computation, dataset download, hardware control, push or
deployment is part of this task.

## Visual polish

Pose-scoped CSS tokens provide neutral graphite surfaces, saturated cyan actions,
amber status/edges, tabular correction values and consistent interaction states.
The active pose header uses the same tokens; the benchmark's styles remain
separate. Secondary explanations are collapsed, keeping playback, progress and
reset visible at 1440×900; shorter inspectors can scroll.

Ivory paint, satin aluminium, graphite, matte rubber and darker steel now have
separate material responses. Broad key/fill area lights, restrained rim light,
local RoomEnvironment reflections and a low-energy shadow light use only bundled
Three.js capabilities. Explicit sRGB output and ACES exposure preserve controlled
highlights; guidance lines bypass tone mapping to retain their amber/cyan hues.
The camera focuses more closely on the wrist without changing physical objects
or pose conventions. Geometry remains procedural rather than photographic.

Actual Chrome screenshots were inspected at 1440×900 and 390×844. The local
`artifacts/polish-browser/` directory contains `before-initial.png`,
`after-initial.png`, `after-aligned.png`, `after-mobile.png`, `benchmark.png` and
`results.json`. Playback, pause/resume/reset, overlay controls, stationary observed
geometry, desktop button visibility, mobile overflow and benchmark opening passed
with no console errors, remote requests or POST/inference calls. The production
build passed with Vite's bundle-size advisory. No CSS-string tests were added.
