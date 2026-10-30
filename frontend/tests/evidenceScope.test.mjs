import test from "node:test";
import assert from "node:assert/strict";
import { evidenceScope } from "../src/evidenceScope.ts";

test("scope reports affirmative flags independently of generated prose", () => {
  const cards = [{gt_instance_masks_used: true, correctness_uses_benchmark_gt: true, computation: "recorded"}];
  const before = JSON.stringify(cards);
  const notes = evidenceScope(cards);
  assert.match(notes[0], /GT instance masks used/);
  assert.match(notes[1], /Correctness evaluated against benchmark GT/);
  assert.equal(notes[2], "Metrics are recorded.");
  assert.equal(JSON.stringify(cards), before, "Evidence remains unchanged for export");
});

test("missing, false and nonboolean flags never imply GT-free evidence", () => {
  for (const cards of [[], [{}], [{gt_instance_masks_used: false}],
    [{gt_instance_masks_used: "true", correctness_uses_benchmark_gt: 1}],
    [{gt_instance_masks_used: null, correctness_uses_benchmark_gt: undefined}]]) {
    const notes = evidenceScope(cards);
    assert.match(notes[0], /not confirmed/);
    assert.match(notes[1], /not confirmed/);
    assert.match(notes[2], /not confirmed/);
    assert.doesNotMatch(notes.join(" "), /GT-free/);
    assert.doesNotMatch(JSON.stringify(cards), /"correctness_uses_benchmark_gt":false/);
  }
});

test("mixed evidence discloses affirmative use without claiming all cards have flags", () => {
  const notes = evidenceScope([{}, {gt_instance_masks_used: true}, {correctness_uses_benchmark_gt: true}], "recorded");
  assert.match(notes[0], /at least one evidence card/);
  assert.match(notes[1], /at least one evidence card/);
  assert.equal(notes[2], "Metrics are recorded.");
});
