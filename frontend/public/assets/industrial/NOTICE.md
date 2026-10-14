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
These original asset designs/patterns are MIT-licensed: `AUTOFRAME-ASSET-LICENSE`.
They are fictional industrial components, not manufacturer CAD or captured scans.

## Reflection environment and geometry helpers

Three.js RoomEnvironment, PMREMGenerator, RoundedBoxGeometry and geometry utilities:
https://github.com/mrdoob/three.js (MIT; notice supplied in `THREE-LICENSE`).
Reflection lighting and fine surface textures are generated locally in the browser.
No HDR image, photograph, generated reference image or external runtime URL is used.
