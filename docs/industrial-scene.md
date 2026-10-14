# Industrial inspection scene

The synthetic Pose Inspection viewport now uses a locally bundled Panda visual
model instead of capsule arm links. The UI palette, synthetic disclosure, pose
math, five-second playback and Recorded Benchmark implementation are unchanged.

## Assets and reproduction

See `frontend/public/assets/industrial/NOTICE.md` for authors, pinned source URL,
licences and modifications. The Panda licence was verified in the upstream
model directory, not inferred from a free-download label.

Available tools inspected: Node, Python, Three.js and SciPy; Blender and trimesh
were unavailable. Conversion uses existing Three.js OBJLoader and SciPy for an
offline stationary joint configuration. This is asset preparation, not runtime
pose inference. To reproduce with those dependencies available:

```
python scripts/prepare_industrial_robot.py
node scripts/pack_industrial_robot.mjs
cd frontend
npm run build
```

Raw source downloads: 32,248,371 bytes of OBJ visual meshes (49 parts).
Bundled robot buffer: 3,485,328 bytes; 126,562 triangles; three material groups.
The unchanged silhouette is preserved during vertex welding and normal smoothing.
Raw downloads and workspace-local browser automation are in `.tools/`, excluded
from this task's commit. No global tools or runtime asset CDN dependencies were added.

`robot.json` and `robot.bin` load concurrently from local `assets/industrial/`.
Host these files beside the built frontend and preserve their relative paths.
Failed loading displays an explicit error; it never substitutes the old robot.
Pending loading is cancellable; late geometry and unmounted resources are disposed.
Materials and repeated geometries are reused; stationary gripper details are merged
by finish, and both overlays share merged fill/feature-edge buffers. Rendering is
requested only for changes and orbit damping, with no continuous idle frame loop.

## Registration and surfaces

All geometry uses metres and +Z up. Robot scaling (1.08) and joint transforms are
baked into the asset, independently of `fixtureParent`. Offline mounting error
was below 1e-6. The robot's local wrist mounting frame is `[0.39, 0, 0.69]`, with
the tool along +X. Gripper mating face remains at local X=-0.055. Existing
`gripperMatingLocal`, reference, correction matrices and quaternion math are intact.

Observed geometry generates the CAD buffers directly with its local transforms.
Only the estimated group receives changing pose state; the observed geometry,
robot, scanner and bench remain stationary. Feature edges omit jaw grooves,
cables and tiny socket triangles. Overlay depth handling prevents aligned flicker.

New gripper detail includes bevelled side plates, a separate actuator cover,
linear guide rods, retainers, shaped jaws, dark grooved inserts, recessed hex sockets
and a connector/cable. Scanner detail includes optical glass, bezel, side plates,
fasteners, connector, mounting yoke and stand. The workbench has real bevelled holes.

Ivory paint, satin aluminium, darker steel, rubber and optical glass use distinct
PBR finishes. Three deterministic 256x256 RGBA linear-data grain textures provide
restrained roughness/bump variation; imported arm UVs use metre-based planar
coordinates, with approximately 12.5 mm grain tiles and sub-millimetre pattern detail.
Bench grain tiles are approximately 40 mm. Bump amplitudes are 0.025–0.06 mm.
The gripper label is a 512x128 sRGB canvas texture. RoomEnvironment produces a local
PMREM reflection texture; there is no downloaded environment image. Broad key/fill,
an edge light and a 1024-square shadow map reveal housing shapes and table contact.
Output is sRGB with ACES filmic tone mapping and exposure 1.0.

## Validation and visual acceptance

Production build passes (existing large-bundle warning remains). All five frontend
pose tests and 26 Python geometry/investigation/recorded-demo tests pass. Python
reported only an unwritable pytest-cache warning.

`scripts/verify_industrial_scene.cjs` uses workspace-local Playwright and installed
Chrome. Run with `SCENE_URL` pointing to the production preview. Screenshots and
the full measurement report are saved under `artifacts/industrial-scene/`:
initial wrong pose, overlay-hidden gripper close-up, mid-playback, aligned endpoint,
another orbit angle, 390px mobile, and Recorded Benchmark with downloaded evidence.
The reviewed production captures and report are retained in
[industrial-scene-review](industrial-scene-review/verification.json):
[initial](industrial-scene-review/initial.png),
[overlay-hidden close-up](industrial-scene-review/gripper-closeup.png),
[playback](industrial-scene-review/playback.png),
[aligned](industrial-scene-review/aligned.png),
[orbit](industrial-scene-review/orbit.png),
[mobile](industrial-scene-review/mobile.png), and
[benchmark](industrial-scene-review/benchmark.png).

The report verifies an exact world-matrix match at the endpoint, a stationary
observed transform, original-estimate restoration, mobile width, console errors
and external requests. Performance uses a separate uninterrupted replay to avoid
including screenshot capture stalls; interaction is also measured during orbit.

Final measurement: installed Chrome 154.0.8037.100, headless, 1600x1000 at DPR 1,
ANGLE Intel UHD Graphics 620 / Direct3D11. Playback rendered 167 frames in 5.1036 s:
32.7 rendered frames/s. Sampled animation-frame median was 28.0 ms and p95 34.8 ms.
Orbit interaction rendered 105 frames over 2.4599 s (including a one-second damping
settle and screenshot). Initial renderer statistics: 69 draw calls, 219,372 reported
triangles/frame, 55 geometries and eight textures. This triangle statistic includes
the displayed CAD fill and renderer passes; the robot asset itself has 126,562.
Idle rendering stopped. Endpoint world-matrix error was exactly zero; camera and
estimate resets passed. Mobile had no horizontal overflow. Recorded evidence
download passed. Console/page errors and external requests were both empty.
These are measurements on this laptop, not a general 60 fps claim.

Visual review: the arm silhouette now has shaped cast housings and real seams;
the gripper has a plausible actuator/guide/jaw structure; paint, metal and rubber
are distinguishable; reflections and table shadows reveal form; wrist inspection
is clearly visible and orbit establishes actual 3D geometry. The result remains
an illustrative PBR rendering, visibly short of the photographic reference.
Remaining limits include the Panda's different proportions, simplified fictional
gripper/scanner internals, restrained procedural surfaces rather than photographic
material scans, hard-edged directional shadows and a sparse workshop background.
No photographic match, live capture or manufacturing accuracy is claimed.
