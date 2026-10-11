import { useEffect, useState } from "react";
import { Archive, Crosshair, Eye, EyeOff, RotateCcw } from "lucide-react";
import Scene, { type GeometryPayload } from "./Scene";
import InvestigationPanel from "./InvestigationPanel";

type RecordedResult = {
  accepted: boolean; correct: boolean; category: string;
  alignment_quality_metrics: { fitness: number; inlier_rmse_m: number };
  pose_metrics: { mssd_over_diameter: number };
};
type Variant = { id: string; label: string; experimental: boolean; record: RecordedResult; method: string; evidence_source: string; publication_copy: string; source_sha256: string; execution_source_identity: string };
type Case = { id: string; title: string; case_id: string; object_id: number; variants: Variant[]; geometry_available: boolean; geometry_status: string };
type Catalogue = {
  label: string; cases: Case[]; config_sha256: string;
  config: { geometric_acceptance: { minimum_fitness: number; maximum_inlier_rmse_m: number; maximum_correspondence_distance_m: number }; pose_correctness: { maximum_normalized_mssd: number } };
  evidence: { heldout_corrected: { accepted_and_correct: number; accepted_but_wrong: number; affected_rescored: number; unaffected_carried_forward: number }; scope: string; pilot: string; experimental: string; AI: string; historical_provenance: string };
  publication: Record<string, unknown>;
};
const fmt = (n: number, digits = 3) => Number.isFinite(n) ? n.toFixed(digits) : "Unavailable";
async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Local API returned ${response.status}`);
  }
  return response.json();
}

export default function RecordedDemo() {
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null);
  const [caseId, setCaseId] = useState("accepted-wrong");
  const [variantId, setVariantId] = useState("baseline");
  const [geometry, setGeometry] = useState<GeometryPayload | null>(null);
  const [showTruth, setShowTruth] = useState(false);
  const [showScan, setShowScan] = useState(true);
  const [showEstimate, setShowEstimate] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [geometryError, setGeometryError] = useState<string | null>(null);
  const [replay, setReplay] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const selected = catalogue?.cases.find(c => c.id === caseId);
  const variant = selected?.variants.find(v => v.id === variantId);

  useEffect(() => {
    let cancelled = false;
    get<Catalogue>("/api/demo").then(data => { if (!cancelled) setCatalogue(data); })
      .catch(e => { if (!cancelled) setError(`Recorded evidence could not be loaded. Start the local API on port 8000. ${e.message}`); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setGeometry(null); setGeometryError(null); setLoading(false);
    if (!selected || !variant) return;
    if (!selected.geometry_available) { setGeometryError(selected.geometry_status); return; }
    setLoading(true);
    get<GeometryPayload>(`/api/demo/cases/${selected.id}/geometry?variant=${variant.id}`)
      .then(data => { if (!cancelled) setGeometry(data); })
      .catch(e => { if (!cancelled) setGeometryError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selected, variant]);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const job = await get<{ status: string; error: string | null; result: { passed: boolean } | null }>(`/api/jobs/${jobId}`);
        if (cancelled) return;
        if (["completed", "failed", "stopped"].includes(job.status)) {
          setReplay(job.result ? `New local replay ${job.result.passed ? "matched" : "did not match"} the saved baseline under replay tolerances. The recorded display remains unchanged.` : `Replay ${job.status}: ${job.error ?? "no result"}`);
          setJobId(null);
        }
      } catch (e) { if (!cancelled) { setReplay(`Replay status unavailable: ${(e as Error).message}`); setJobId(null); } }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 700);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [jobId]);

  async function startReplay() {
    if (!selected || !window.confirm("Run one new local baseline registration? This is new compute, not part of the recorded demonstration. No remote model is used.")) return;
    try {
      const job = await get<{ job_id: string }>(`/api/demo/cases/${selected.id}/replay`, { method: "POST" });
      setReplay("New local baseline replay running. Saved evidence remains on screen."); setJobId(job.job_id);
    } catch (e) { setReplay((e as Error).message); }
  }
  async function downloadEvidence() {
    if (!selected) return;
    try {
      const saved = await get<Record<string, unknown>>(`/api/demo/cases/${selected.id}/evidence`);
      const url = URL.createObjectURL(new Blob([JSON.stringify(saved, null, 2)], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url; link.download = `autoframe3d-${selected.id}-recorded-evidence.json`;
      link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) { setError(`Evidence download failed: ${(e as Error).message}`); }
  }
  const result = variant?.record;
  const thresholds = catalogue?.config.geometric_acceptance;
  const audit = catalogue?.evidence.heldout_corrected;

  return <div className="app-shell recorded-demo">
    <header className="topbar">
      <div className="brand-lockup"><div className="brand-mark"><Crosshair size={20} /></div><div className="brand-copy"><strong>AUTOFRAME 3D</strong><span>RECORDED BENCHMARK DEMO</span></div></div>
      <div className="tagline">Good geometric fit can hide a wrong pose.</div>
      <span className="connection-state">RECORDED · NO LIVE EVALUATION</span>
    </header>
    {error && <div className="error-banner" role="alert">{error} <button onClick={() => window.location.reload()}>Retry</button></div>}
    <main className="workbench">
      <aside className="scenario-panel panel">
        <span className="eyebrow">01 / SAVED EVIDENCE</span><h1>Recorded benchmark demo</h1>
        <p>Inspect an observed scan, a saved estimated CAD pose, and benchmark ground truth. Selecting a case does not run registration.</p>
        <label className="field-label" htmlFor="recorded-case">Saved example</label>
        <select id="recorded-case" value={caseId} disabled={!catalogue} onChange={e => { setCaseId(e.target.value); setVariantId("baseline"); setShowTruth(false); }}>
          {catalogue?.cases.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
        </select>
        {selected && <p className="case-identity">{selected.case_id}</p>}
        <label className="field-label" htmlFor="recorded-method">Recorded method</label>
        <select id="recorded-method" value={variantId} disabled={!selected} onChange={e => setVariantId(e.target.value)}>
          {selected?.variants.map(v => <option key={v.id} value={v.id}>{v.label}</option>)}
        </select>
        {variant && <p>{variant.method}</p>}
        {variant?.experimental && <div className="error-banner">Experimental result · rejected for production promotion.</div>}
        <div className="control-stack"><button className="button button-export" disabled={!selected} onClick={() => void downloadEvidence()}><Archive size={16} />Download recorded evidence</button></div>
        <details className="replay-details"><summary>Optional local replay · new compute</summary><p>Recomputes the historical baseline from local data. Experimental refinements are not replayed by this action.</p><button className="button button-secondary" disabled={!selected?.geometry_available || variantId !== "baseline" || Boolean(jobId)} onClick={() => void startReplay()}><RotateCcw size={15} />Run baseline replay</button></details>
        {replay && <p role="status">{replay}</p>}
      </aside>
      <section className="viewer-panel panel">
        <div className="viewer-header"><div><span className="eyebrow">02 / SAVED ALIGNMENT</span><h2>{selected ? `T-LESS object ${selected.object_id}` : "Loading recorded evidence"}</h2></div><span className="frame-badge">CAMERA FRAME · METRES</span></div>
        <div className="viewer-stage">
          {geometry ? <Scene data={geometry} showScan={showScan} showEstimate={showEstimate} showTruth={showTruth} /> : <div className="loading-state" role="status">{loading ? "Loading local geometry for the saved transforms…" : geometryError ?? "Waiting for recorded evidence…"}{geometryError && <span>Recorded metrics are still available. No geometry is fabricated.</span>}</div>}
          {geometry && <div className="viewer-legend">
            <button aria-pressed={showScan} onClick={() => setShowScan(!showScan)}><span className="legend-dot legend-scan" />Observed scan</button>
            <button aria-pressed={showEstimate} onClick={() => setShowEstimate(!showEstimate)}><span className="legend-dot legend-estimate" />Saved estimate</button>
            <button aria-pressed={showTruth} onClick={() => setShowTruth(!showTruth)}><span className="legend-dot legend-truth" />Benchmark ground truth {showTruth ? <Eye size={13} /> : <EyeOff size={13} />}</button>
          </div>}
        </div>
        <div className="viewer-footer"><span>{geometry ? "Drag to orbit · scroll to zoom" : "3D assets unavailable or loading"}</span><span>{geometry ? "Local source geometry · saved transforms · GT instance mask" : "Recorded metrics and evidence remain available"}</span></div>
      </section>
      <aside className="history-panel panel">
        <span className="eyebrow">03 / TWO SEPARATE DECISIONS</span><h2>Fit versus correctness</h2>
        {result && <>
          <div className="decision"><span>Geometric acceptance</span><strong>{result.accepted ? "Accepted" : "Rejected"}</strong></div>
          <div className={`decision ${!result.correct ? "wrong-pose" : ""}`}><span>Symmetry-aware pose correctness</span><strong>{result.correct ? "Correct" : "Incorrect"}</strong></div>
          <div className="metric-cell"><span>FITNESS · SCAN-POINT FRACTION</span><strong>{fmt(result.alignment_quality_metrics.fitness)}</strong><small>Acceptance ≥ {thresholds?.minimum_fitness}</small></div>
          <div className="metric-cell"><span>INLIER RMSE</span><strong>{fmt(result.alignment_quality_metrics.inlier_rmse_m * 1000, 2)} <i>mm</i></strong><small>Acceptance ≤ {fmt((thresholds?.maximum_inlier_rmse_m ?? NaN) * 1000, 1)} mm</small></div>
          <div className="metric-cell"><span>SYMMETRY-AWARE MSSD / DIAMETER</span><strong>{fmt(result.pose_metrics.mssd_over_diameter, 4)}</strong><small>Correctness ≤ {catalogue?.config.pose_correctness.maximum_normalized_mssd}</small></div>
          <p>Fitness uses scan points within {fmt((thresholds?.maximum_correspondence_distance_m ?? NaN) * 1000, 1)} mm of the model. Acceptance is not a correctness guarantee.</p>
        </>}
      </aside>
      {selected && selected.variants.length > 1 && <section className="panel recorded-evidence">
        <h2>Recorded control regression: lower RMSE, worse pose</h2>
        <p>Same case, inputs, thresholds and six starts. Reciprocal refinement reduced RMSE but crossed the correctness threshold. It is experimental, not an improvement.</p>
        <div className="table-scroll"><table><thead><tr><th>Saved method</th><th>Fitness</th><th>RMSE, mm</th><th>MSSD/D</th><th>Acceptance</th><th>Correctness</th></tr></thead><tbody>{selected.variants.map(v => <tr key={v.id}><td>{v.experimental ? "Reciprocal (experimental)" : "Historical baseline"}</td><td>{fmt(v.record.alignment_quality_metrics.fitness)}</td><td>{fmt(v.record.alignment_quality_metrics.inlier_rmse_m * 1000, 2)}</td><td>{fmt(v.record.pose_metrics.mssd_over_diameter, 4)}</td><td>{v.record.accepted ? "Accepted" : "Rejected"}</td><td>{v.record.correct ? "Correct" : "Incorrect"}</td></tr>)}</tbody></table></div>
      </section>}
      {catalogue && <section className="panel recorded-evidence">
        <span className="eyebrow">04 / EVIDENCE AND LIMITS</span><h2>What the recorded benchmark establishes</h2>
        <p><strong>{audit?.accepted_and_correct} accepted-and-correct · {audit?.accepted_but_wrong} accepted-but-wrong</strong> in the corrected held-out aggregate.</p>
        <p>{audit?.affected_rescored} affected records were rescored; {audit?.unaffected_carried_forward} unaffected labels were carried forward, including three independently checked controls. This was not a full independent rescore.</p>
        <p>{catalogue.evidence.scope}</p><p>{catalogue.evidence.pilot}</p><p>{catalogue.evidence.experimental}</p>
        <details><summary>Method, configuration and provenance</summary>
          <p>Versioned evidence copy: <code>{variant?.publication_copy}</code></p><p>Original evidence: <code>{variant?.evidence_source}</code></p><p>Source SHA-256: <code>{variant?.source_sha256}</code></p><p>Execution adapter SHA-256: <code>{variant?.execution_source_identity}</code></p><p>Frozen configuration SHA-256: <code>{catalogue.config_sha256}</code></p><p>{catalogue.evidence.historical_provenance}</p>
          <p>{catalogue.evidence.AI} The separate synthetic proposal path receives GT-derived pose errors and classifications; it is an offline benchmark adversary, not a GT-free detector.</p>
          <pre>{JSON.stringify(catalogue.publication, null, 2)}</pre>
        </details>
      </section>}
      <InvestigationPanel caseId={selected?.case_id} onSelect={(viewerId, methodId) => { setCaseId(viewerId); setVariantId(methodId); setShowTruth(false); }} />
    </main>
    <footer className="app-footer">Benchmark stress-testing and replay tool · not a validated industrial pose estimator · not a proven adaptive AI agent</footer>
  </div>;
}
