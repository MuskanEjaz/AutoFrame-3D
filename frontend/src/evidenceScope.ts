/** Deterministic disclosures from returned flags; no inference from prose. */
export type ScopeEvidence = {
  gt_instance_masks_used?: unknown;
  correctness_uses_benchmark_gt?: unknown;
  computation?: unknown;
};

export function evidenceScope(evidence: ScopeEvidence[], computation?: unknown): string[] {
  return [
    evidence.some(e => e.gt_instance_masks_used === true)
      ? "GT instance masks used (reported for at least one evidence card)."
      : "GT instance-mask use not confirmed by returned flags.",
    evidence.some(e => e.correctness_uses_benchmark_gt === true)
      ? "Correctness evaluated against benchmark GT (reported for at least one evidence card)."
      : "Benchmark-GT scoring not confirmed by returned flags.",
    computation === "recorded" || evidence.some(e => e.computation === "recorded")
      ? "Metrics are recorded."
      : "Recorded metric provenance not confirmed by returned flags.",
  ];
}
