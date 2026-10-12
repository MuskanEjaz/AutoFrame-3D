import test from "node:test";
import assert from "node:assert/strict";
import { Matrix4, Quaternion, Vector3 } from "three";
import {
  targetPose,
  localMating,
  mounting,
  initialPose,
  errors,
  editPose,
  previewPose,
} from "../src/assemblyPose.ts";
test("target aligns nonzero local mating frame", () => {
  const p = targetPose();
  const actual = new Matrix4()
    .compose(
      new Vector3().fromArray(p.p),
      new Quaternion().fromArray(p.q),
      new Vector3(1, 1, 1),
    )
    .multiply(localMating);
  actual.elements.forEach((v, i) =>
    assert.ok(Math.abs(v - mounting.elements[i]) < 1e-12),
  );
  assert.ok(Math.abs(p.p[0] - 0.445) < 1e-12);
});
test("known translation and quaternion angle, antipodal equivalence", () => {
  const p = editPose(targetPose(), false, 0, "3");
  assert.ok(Math.abs(errors(p).position - 0.003) < 1e-12);
  assert.ok(Math.abs(errors(p).correction[0] + 0.003) < 1e-12);
  const r = editPose(targetPose(), true, 2, "30");
  assert.ok(Math.abs(errors(r).orientation - 30) < 1e-10);
  assert.equal(
    errors({ ...r, q: r.q.map((v) => -v) }).orientation,
    errors(r).orientation,
  );
});
test("both tolerance boundaries require both checks", () => {
  for (const mm of [0.999, 1.001]) {
    assert.equal(
      errors(editPose(targetPose(), false, 1, String(mm))).ok,
      mm < 1,
    );
  }
  for (const deg of [0.999, 1.001]) {
    assert.equal(
      errors(editPose(targetPose(), true, 0, String(deg))).ok,
      deg < 1,
    );
  }
  assert.equal(
    errors(editPose(editPose(targetPose(), false, 0, "2"), true, 1, "0")).ok,
    false,
  );
});
test("deterministic reset and invalid numeric entry", () => {
  assert.deepEqual(initialPose(), initialPose());
  for (const s of ["", " ", "NaN", "Infinity", "oops"])
    assert.equal(editPose(initialPose(), false, 0, s), null);
});
test("preview seats exactly and preserves manual attempt", () => {
  const attempt = initialPose(),
    copy = structuredClone(attempt);
  assert.deepEqual(previewPose(5), targetPose());
  assert.deepEqual(previewPose(7), targetPose());
  assert.deepEqual(attempt, copy);
  assert.ok(errors(previewPose(2)).orientation < 1e-8);
  assert.ok(errors(previewPose(2)).position > 0.1);
});
