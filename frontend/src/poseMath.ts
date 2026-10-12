import { Euler, Matrix4, Quaternion, Vector3 } from "three";
export type Pose = { p: number[]; q: number[] };
export const demoTolerance = { metres: 0.001, degrees: 1 };
// Physical poses in the fixed, right-handed Demo scan frame; +Z is up.
export const fixtureParent = new Matrix4().compose(
  new Vector3(0.02, 0.01, 0),
  new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), -0.08),
  new Vector3(1, 1, 1),
);
export const wristLocal = new Matrix4().makeTranslation(0.39, 0, 0.69);
export const gripperMatingLocal = new Matrix4().makeTranslation(-0.055, 0, 0);
export function matrix(p: Pose) {
  return new Matrix4().compose(
    new Vector3().fromArray(p.p),
    new Quaternion().fromArray(p.q).normalize(),
    new Vector3(1, 1, 1),
  );
}
export function poseFromMatrix(m: Matrix4): Pose {
  const p = new Vector3(),
    q = new Quaternion();
  m.decompose(p, q, new Vector3());
  return { p: p.toArray(), q: q.normalize().toArray() };
}
export function referencePose(parent = fixtureParent): Pose {
  return poseFromMatrix(
    parent
      .clone()
      .multiply(wristLocal)
      .multiply(gripperMatingLocal.clone().invert()),
  );
}
export function initialEstimate(): Pose {
  const r = referencePose();
  return {
    p: r.p.map((v, i) => v + [0.037, -0.019, 0.043][i]),
    q: new Quaternion()
      .setFromAxisAngle(new Vector3(0, 1, 0), -0.34)
      .multiply(new Quaternion().fromArray(r.q))
      .normalize()
      .toArray(),
  };
}
export function difference(estimate: Pose, reference = referencePose()) {
  const displacement = reference.p.map((v, i) => v - estimate.p[i]);
  const relative = new Quaternion()
    .fromArray(reference.q)
    .normalize()
    .multiply(new Quaternion().fromArray(estimate.q).normalize().invert());
  if (relative.w < 0)
    relative.set(-relative.x, -relative.y, -relative.z, -relative.w);
  const sin = Math.hypot(relative.x, relative.y, relative.z),
    angle = (2 * Math.atan2(sin, Math.max(0, relative.w)) * 180) / Math.PI;
  const axis =
    sin < 1e-10
      ? [0, 0, 0]
      : [relative.x / sin, relative.y / sin, relative.z / sin];
  const magnitude = Math.hypot(...displacement);
  return {
    displacement,
    axis,
    angle,
    magnitude,
    aligned:
      magnitude <= demoTolerance.metres && angle <= demoTolerance.degrees,
    rigidCorrection: matrix(reference)
      .multiply(matrix(estimate).invert())
      .toArray(),
  };
}
export function eulerDegrees(p: Pose) {
  const e = new Euler().setFromQuaternion(
    new Quaternion().fromArray(p.q),
    "XYZ",
  );
  return [e.x, e.y, e.z].map((v) => (v * 180) / Math.PI);
}
export function editEstimate(
  p: Pose,
  rotation: boolean,
  axis: number,
  text: string,
): Pose | null {
  if (
    !text.trim() ||
    !Number.isFinite(Number(text)) ||
    axis < 0 ||
    axis > 2 ||
    !Number.isInteger(axis)
  )
    return null;
  const values = rotation ? eulerDegrees(p) : p.p.map((v) => v * 1000);
  values[axis] = Number(text);
  return rotation
    ? {
        p: [...p.p],
        q: new Quaternion()
          .setFromEuler(
            new Euler(
              ...(values.map((v) => v * (Math.PI / 180)) as [
                number,
                number,
                number,
              ]),
              "XYZ",
            ),
          )
          .toArray(),
      }
    : { p: values.map((v) => v / 1000), q: [...p.q] };
}
export function correctionPreview(original: Pose, seconds: number): Pose {
  const t = referencePose(),
    u = Math.min(1, Math.max(0, seconds / 5));
  if (u === 1) return t;
  if (u === 0) return { p: [...original.p], q: [...original.q] };
  return {
    p: original.p.map((v, i) => v + (t.p[i] - v) * u),
    q: new Quaternion()
      .fromArray(original.q)
      .normalize()
      .slerp(new Quaternion().fromArray(t.q), u)
      .toArray(),
  };
}
export function exportSynthetic(estimate: Pose) {
  return {
    label: "Synthetic pose demo",
    schemaVersion: 1,
    provenance:
      "Original procedural gripper; known synthetic reference. No recorded scan, registration or inference.",
    frame: "Demo scan frame",
    units: {
      translation: "metres",
      rotation: "quaternion xyzw",
      axisAngle: "degrees; axis in Demo scan frame",
    },
    estimate,
    reference: referencePose(),
    originDisplacement: difference(estimate).displacement,
    relativeRotation: {
      axis: difference(estimate).axis,
      degrees: difference(estimate).angle,
    },
    rigidCorrectionColumnMajor: difference(estimate).rigidCorrection,
    application:
      "T_corrected = T_correction * T_estimate (left multiplication)",
    tolerances: demoTolerance,
  };
}
