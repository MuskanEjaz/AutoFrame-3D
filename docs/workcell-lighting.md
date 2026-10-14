# Dark industrial workcell and synchronized correction preview

The current scene retains the licensed Panda arm and the current gripper, pose
conventions, synthetic labels, amber overlay and synchronized preview. The visible
background is now an original finite 3D workcell: vertical steel frames, recessed
panels, drawer equipment and restrained side illumination. The foundry panorama's
bright floor is never displayed. Its locally bundled CC0 HDR supplies reflections.
See [asset attribution](../frontend/public/assets/industrial/NOTICE.md).

Background appearance is controlled independently from foreground exposure and
reflections. Workcell materials/lighting and the background-only composite gain
produce subdued charcoal/steel-grey surfaces. The background scene renders with
the same inspection camera into half-resolution buffers, followed by gentle
five-tap softening. Robot, gripper, labels and CAD lines are rendered sharp afterward.
The finite frame/equipment geometry has real perspective and parallax during orbit;
the HDR is used only for illumination and provides no near-field parallax.

Both main and preview use the same desaturated linear HDR/PMREM reflections and
material finishes. Global ACES exposure stays at 1.0. The robot remains warm ivory;
neutral fill and subtle rim lighting preserve graphite joints and rubber cables.
Satin steel on the workbench uses controlled reflection intensity, increased
roughness, subtle machining grain and anisotropic texture filtering. Recessed holes
remain geometric. Static soft VSM shadows and small local contact-shadow textures
ground the mounting plate and scanner foot without casting a hard pole pattern.

The preview is a real 320x176 tool render using the existing renderer and shared
geometries/materials. Main and preview consume one playback state. Play/pause works
from either control; seeking pauses at the selected time; replay retains the original
estimate. Reset restores the original configured estimate. The background buffers
update only on camera/viewport/environment changes, not during ordinary playback.
There is no independent thumbnail animation or continuous idle drawing.

The ongoing task's compact boxed single-object/frame controls, preview card, seek
bar and essential actions are retained. Editing and long explanations remain
collapsed. No Recorded Benchmark, pose mathematics or research logic was changed.

## Review captures and checks

Run `node scripts/verify_visual_preview.cjs` with workspace-local Playwright and
installed Chrome. The default production-preview URL is `http://127.0.0.1:5176/`.
The script validates actual shared vertex positions, world-matrix coincidence,
stationary geometry, main/preview play/pause/seek/replay, estimate/camera reset,
edit-only gizmos, idle rendering, 390px mobile, Recorded Benchmark method controls,
GT reveal, evidence JSON and copilot missing-key state, without triggering inference.

Actual captures and the full measurements are retained in `workcell-lighting-review/`.
The before image is the HDR-background view captured during this ongoing task.
The final images show the dark workcell and satin bench under the preserved UI.

Reviewed captures: [before](workcell-lighting-review/before.png),
[initial full UI](workcell-lighting-review/initial.png),
[overlay-hidden close-up](workcell-lighting-review/gripper-closeup.png),
[aligned pose](workcell-lighting-review/aligned.png),
[preview card](workcell-lighting-review/preview.png),
[second orbit](workcell-lighting-review/orbit.png),
[390px mobile](workcell-lighting-review/mobile.png), and
[Recorded Benchmark](workcell-lighting-review/benchmark.png).
The [browser report](workcell-lighting-review/verification.json) contains all checks
and requests.

Production build passed with a 768 MB Node heap cap after a transient memory failure;
the existing large-bundle warning remains. All five existing frontend pose tests pass.
Chrome 154.0.8037.100, Intel UHD Graphics 620 / ANGLE Direct3D11, headless, 1440x900
at DPR 1: uninterrupted playback rendered 121 main frames and 121 thumbnail frames
over 5.2756 seconds, or 22.9 rendered frames/s. Animation-frame median was 41.7 ms,
p95 48.8 ms. This is a laptop-specific observation, not a portable frame-rate claim.
Shared-geometry comparison found zero unmatched vertices across 109,140 vertices.
Endpoint world matrices coincided exactly; stationary matrices and resets passed.
Play/pause/seek/replay synchronization, edit-only gizmos and idle rendering passed.
No console/page errors, external requests or inference POSTs were recorded. Recorded
Benchmark GT/method controls, valid JSON evidence download and missing-key state passed.

The robot asset remains 3,485,328 bytes / 126,562 triangles. Added HDR download is
1,701,301 bytes / 1024x512 and is CC0. Visible workcell geometry is generated locally;
there is no background-image download. Surface maps remain 256x256; the new local
contact texture is 128x128. Background render buffers are half the viewport dimensions;
the tool preview is 320x176. Replaced textures, render targets and geometry are disposed.

Remaining differences from the reference: the Panda arm has different proportions,
the procedural workcell/equipment is simplified, and the housing/gripper surfaces
are illustrative PBR materials rather than photographic scans. Background softening
is a cached image-space treatment, not a physically simulated lens. Contact shadows
include restrained static footprint textures rather than full ambient occlusion.
No exact photographic match or manufacturing accuracy is claimed.
