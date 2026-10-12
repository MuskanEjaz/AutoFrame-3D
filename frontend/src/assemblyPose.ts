import { Euler, Matrix4, Quaternion, Vector3 } from "three";
export type Pose = { p: number[]; q: number[] };
export const tolerance = { position: 0.001, orientation: 1 };
// Fixed mounting frame: +X outward/insertion approach, +Z up. SI metres.
export const mounting = new Matrix4().makeTranslation(0.39, 0, 0.69);
export const localMating = new Matrix4().makeTranslation(-0.055, 0, 0);
export function targetPose(): Pose {
  const m = mounting.clone().multiply(localMating.clone().invert());
  const p = new Vector3(),
    q = new Quaternion();
  m.decompose(p, q, new Vector3());
  return { p: p.toArray(), q: q.toArray() };
}
export function initialPose(): Pose {
  return {
    p: [0.61, -0.018, 0.714],
    q: new Quaternion()
      .setFromEuler(new Euler(0.18, -0.12, 0.22, "XYZ"))
      .toArray(),
  };
}
export function angles(p: Pose) {
  const e = new Euler().setFromQuaternion(
    new Quaternion().fromArray(p.q),
    "XYZ",
  );
  return [e.x, e.y, e.z].map((v) => (v * 180) / Math.PI);
}
export function editPose(
  p: Pose,
  rotation: boolean,
  axis: number,
  value: string,
): Pose | null {
  if (!value.trim() || !Number.isFinite(Number(value))) return null;
  const values = rotation
    ? angles(p)
    : p.p.map((v, i) => (v - targetPose().p[i]) * 1000);
  values[axis] = Number(value);
  return rotation
    ? {
        p: [...p.p],
        q: new Quaternion()
          .setFromEuler(
            new Euler(
              ...(values.map((v) => (v * Math.PI) / 180) as [
                number,
                number,
                number,
              ]),
              "XYZ",
            ),
          )
          .toArray(),
      }
    : { p: values.map((v, i) => targetPose().p[i] + v / 1000), q: [...p.q] };
}
export function errors(p: Pose) {
  const t = targetPose(),
    correction = t.p.map((v, i) => v - p.p[i]);
  const position = new Vector3(
    ...(correction as [number, number, number]),
  ).length();
  const orientation =
    (new Quaternion().fromArray(p.q).angleTo(new Quaternion().fromArray(t.q)) *
      180) /
    Math.PI;
  return {
    correction,
    position,
    orientation,
    ok: position <= tolerance.position && orientation <= tolerance.orientation,
  };
}
export function previewPose(seconds: number): Pose {
  const start = initialPose(),
    t = targetPose(),
    approach = t.p.map((v, i) => v + (i === 0 ? 0.13 : 0));
  const u = Math.min(1, Math.max(0, seconds / 2));
  const q = new Quaternion()
    .fromArray(start.q)
    .slerp(new Quaternion().fromArray(t.q), u);
  const v = Math.min(1, Math.max(0, (seconds - 2) / 3));
  const smooth = v * v * (3 - 2 * v);
  return {
    p: approach.map((x, i) => x + (t.p[i] - x) * smooth),
    q: q.toArray(),
  };
}
