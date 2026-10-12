# Assembly Guide

The default workspace is **Assembly simulation**. Recorded Benchmark remains
available in the header with its existing evidence and copilot behavior. The
legacy live workbench remains at `?workbench=1`. Start the API and frontend using
the existing README commands. No runtime CDN resources are used.

## Assets and visual scope

Robot, gripper, keyed mating flanges, scanner, cable and workbench are original
procedural Three.js geometry; no downloaded manufacturer models or textures.
Lighting uses Three.js's bundled RoomEnvironment. This is an illustrative robot,
not a dimensionally accurate manufacturer model. It follows the reference's
palette and arrangement, but has simplified geometry and materials and does not
match the photograph's realism or factory environment.

## Pose convention

Internal lengths are metres. The fixed mounting frame has world-aligned axes:
+X points outward from the robot flange, +Z points upward, insertion follows −X.
The stationary mating frame is at (0.390, 0, 0.690) m with identity orientation.
The gripper's local mating frame is at (−0.055, 0, 0) m with identity orientation.
The target part transform is `mounting * inverse(localMating)`, placing the part
origin at (0.445, 0, 0.690) m. Mating planes coincide at the seated target. Pins
match six holes plus an asymmetric locating hole; these are illustrative fits.

Inspector positions are current part-origin coordinates relative to the target
part origin, in the fixed mounting frame (mm). Target displayed position is
(0, 0, 0) mm. Displayed current/target Euler orientations use XYZ order in that
frame. Numeric Euler entry rebuilds the quaternion; rotation nudges change the
selected displayed Euler component. The rotation gizmo operates about fixed
world/mounting axes. These Euler values are not a universal rotation correction.

Signed position correction is target minus current part position. Position error
is its Euclidean norm. Orientation error is the shortest quaternion angle, with
q and −q equivalent. Full-precision decisions require **both ≤1.0 mm and ≤1.0°**;
these configurable settings live in `assemblyPose.ts`. Rounding is display only.
Orbit never changes the part pose; gizmo dragging disables orbit. Reset restores
one deterministic misalignment. Invalid/nonfinite numeric entries are rejected.

The laser is decorative guidance: 15 rays aimed at the stationary flange stop
at the first mesh intersection, including an obstructing gripper. Its geometry
is independent of pose error and recorded evidence.

## Preview

The separate modal renders the same procedural assembly. It aligns orientation
using quaternion interpolation during seconds 0–2 at a 130 mm approach offset,
then approaches along −X over seconds 2–5 and ends exactly at target. It never
writes the manual pose. Timing uses elapsed animation-frame time, pauses while
the document is hidden, and stops at completion. Reduced motion shows the final
pose immediately. Replay and Close are available, with native dialog focus and
Escape handling.

No hardware control, scanner acquisition, ML training, live inference, physical
clearance calculation, collision validation or manufacturing calibration is
implemented. Pose alignment alone establishes none of these.

## Verification

`cd frontend; node --test tests/assembly.test.mjs` exercises offset target
composition, known translation/rotation errors, antipodal quaternions, either
side of both tolerance boundaries, deterministic reset, invalid input and
preview completion without manual-state mutation. `npm run build` checks strict
TypeScript and creates the production bundle (Vite reports a large bundle).

Headless installed Chrome with Playwright inspected desktop 1440×900 and mobile
390×844. Screenshots and the local browser runner are in
`artifacts/assembly-browser/`: `desktop-initial.png`, `manual-placement.png`,
`within-tolerance.png`, `preview-progress.png`, `preview-complete.png`,
`benchmark.png`, `benchmark-copilot.png`, `benchmark-evidence.png`, `mobile.png`.
Browser checks enter translation and rotation values, reach tolerance, reset,
watch/close the demo without overwriting the attempt, open benchmark tabs and
download real recorded evidence. A real translation-gizmo drag changes the pose;
reduced-motion preview immediately shows the seated target. No page errors;
mobile document width 390 px.
Screenshots are local generated artifacts, excluded from the implementation
commit. Existing unrelated working changes are preserved and excluded.
