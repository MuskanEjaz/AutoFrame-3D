# Industrial scene assets

## Panda robot

Original robot visual meshes: Franka Emika / Franka Robotics.
OBJ conversion and MuJoCo description: Google DeepMind MuJoCo Menagerie contributors.
Source: https://github.com/google-deepmind/mujoco_menagerie/tree/71f066ad0be9cd271f7ed58c030243ef157af9f4/franka_emika_panda
Licence: Apache-2.0, supplied in `PANDA-LICENSE`. Upstream description is retained in `PANDA-README.md`.

AutoFrame3D modifications: retained visual arm meshes only; omitted collision meshes,
hand and fingers; baked a stationary joint configuration; uniformly scaled by 1.08;
converted to metre-space position/normal/index buffers; reconstructed crease-aware
normals at millimetre scale; welded matching vertices; grouped into three finishes;
replaced upstream material assignments with local ivory paint, dark joint and steel
materials. No upstream textures are used. Geometry is packaged in `robot.bin`, with
offsets, source revision, scale and joint angles in `robot.json`.

The robot is an illustrative Panda, not the six-axis robot depicted in the reference
image, and not a robot dynamics or manufacturing-accuracy model.

## Original assets

Gripper, scanner, brackets, dress cables, workbench and surface patterns were authored
for AutoFrame3D in `frontend/src/industrialDetails.ts` and `PoseScene.tsx`.
The finite workcell geometry and background-only softening in `WorkcellBackdrop.ts`
are also original assets under the same MIT licence.
These original asset designs/patterns are MIT-licensed: `AUTOFRAME-ASSET-LICENSE`.
They are fictional industrial components, not manufacturer CAD or captured scans.

## Reflection environment and geometry helpers

Three.js HDRLoader, PMREMGenerator, RoundedBoxGeometry and geometry utilities:
https://github.com/mrdoob/three.js (MIT; notice supplied in `THREE-LICENSE`).
Fine surface textures and the visible 3D workcell are generated locally.
No supplied reference image or external runtime asset URL is used.

## Industrial reflection environment

Asset: Industrial Workshop Foundry, Poly Haven.
Source: https://polyhaven.com/a/industrial_workshop_foundry
Download: https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/industrial_workshop_foundry_1k.hdr
Authors: Dimitrios Savva (photography), Jarod Guest (processing).
Licence: CC0 1.0; Poly Haven explicitly permits redistribution:
https://polyhaven.com/license . Standard legal text is bundled as `FOUNDRY-CC0.txt`.

`foundry_1k.hdr` is the unmodified 1024x512, 1,701,301-byte source download.
MD5: d65e13e0b4aff7fd0a2fa32a7c0fd4e3 (verified against the published asset metadata).
At runtime its linear RGB is desaturated to 10% while preserving luminance, then
converted to PMREM for reflections. It is not displayed as a panorama or backplate.
Main and preview use the same reflection treatment. The original file is bundled
locally; asset preparation requires no credentials and the app makes no CDN request.
