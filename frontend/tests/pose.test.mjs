import test from "node:test";
import assert from "node:assert/strict";
import { Matrix4, Quaternion, Vector3 } from "three";
import {
  referencePose,
  fixtureParent,
  wristLocal,
  gripperMatingLocal,
  matrix,
  difference,
  initialEstimate,
  correctionPreview,
  editEstimate,
  exportSynthetic,
} from "../src/poseMath.ts";
const close = (a, b) =>
  a.forEach((v, i) =>
    assert.ok(Math.abs(v - b[i]) < 1e-10, `${i}: ${v} vs ${b[i]}`),
  );
test("shared observed/reference pose includes rotated parent and nonzero local offset", () => {
  const r = referencePose();
  close(
    matrix(r).multiply(gripperMatingLocal).elements,
    fixtureParent.clone().multiply(wristLocal).elements,
  );
  const parent = new Matrix4().compose(
    new Vector3(0.8, -0.4, 0.2),
    new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), 0.7),
    new Vector3(1, 1, 1),
  );
  close(
    matrix(referencePose(parent)).multiply(gripperMatingLocal).elements,
    parent.clone().multiply(wristLocal).elements,
  );
});
test("origin displacement and scan-frame axis angle for known perturbations", () => {
  const r = referencePose(),
    estimate = {
      p: r.p.map((v, i) => v + [0.012, -0.006, 0.003][i]),
      q: new Quaternion()
        .setFromAxisAngle(new Vector3(0, 1, 0), 0.4)
        .multiply(new Quaternion().fromArray(r.q))
        .toArray(),
    },
    d = difference(estimate);
  close(d.displacement, [-0.012, 0.006, -0.003]);
  assert.ok(Math.abs(d.angle - (0.4 * 180) / Math.PI) < 1e-10);
  close(d.axis, [0, -1, 0]);
  close(
    new Matrix4().fromArray(d.rigidCorrection).multiply(matrix(estimate))
      .elements,
    matrix(r).elements,
  );
  assert.notDeepEqual(d.rigidCorrection.slice(12, 15), d.displacement);
});
test("antipodal quaternions and zero angle are stable", () => {
  const e = initialEstimate();
  close(difference({ ...e, q: e.q.map((v) => -v) }).axis, difference(e).axis);
  assert.equal(
    difference({ ...e, q: e.q.map((v) => -v) }).angle,
    difference(e).angle,
  );
  const d = difference(referencePose());
  assert.ok(d.angle < 1e-8);
  assert.deepEqual(d.axis, [0, 0, 0]);
  assert.equal(d.aligned, true);
});
test("both synthetic tolerance boundaries", () => {
  const r = referencePose();
  for (const mm of [0.999, 1.001])
    assert.equal(
      difference({ ...r, p: r.p.map((v, i) => v + (i === 0 ? mm / 1000 : 0)) })
        .aligned,
      mm < 1,
    );
  for (const deg of [0.999, 1.001])
    assert.equal(
      difference({
        ...r,
        q: new Quaternion()
          .setFromAxisAngle(new Vector3(1, 0, 0), (deg * Math.PI) / 180)
          .multiply(new Quaternion().fromArray(r.q))
          .toArray(),
      }).aligned,
      deg < 1,
    );
});
test("preview endpoints preserve current estimate; reset deterministic; invalid inputs rejected", () => {
  const original = editEstimate(initialEstimate(), false, 0, "480"),
    copy = structuredClone(original);
  assert.deepEqual(correctionPreview(original, 0), original);
  assert.deepEqual(correctionPreview(original, 5), referencePose());
  assert.deepEqual(correctionPreview(original, 10), referencePose());
  assert.ok(
    difference(correctionPreview(original, 2.5)).magnitude <
      difference(original).magnitude,
  );
  assert.deepEqual(original, copy);
  assert.deepEqual(initialEstimate(), initialEstimate());
  for (const value of ["", " ", "NaN", "Infinity", "x"])
    assert.equal(editEstimate(original, false, 0, value), null);
  assert.equal(exportSynthetic(original).label, "Synthetic pose demo");
});
