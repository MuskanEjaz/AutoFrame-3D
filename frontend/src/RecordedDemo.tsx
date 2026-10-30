import { useEffect, useState } from "react";
import { Archive, Crosshair, Eye, EyeOff, RotateCcw } from "lucide-react";
import Scene, { type GeometryPayload } from "./Scene";
import InvestigationPanel from "./InvestigationPanel";
import "./recorded.css";

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
  const [tab, setTab] = useState("results");
  const [viewCommand, setViewCommand] = useState({ id: 0, view: "fit" });
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
    setGeometryError(null); setLoading(false);
    if (!selected || !variant) return;
    if (!selected.geometry_available) { setGeometry(null); setGeometryError(selected.geometry_status); return; }
    setLoading(true);
    get<GeometryPayload>(`/api/demo/cases/${selected.id}/geometry?variant=${variant.id}`)
      .then(data => { if (!cancelled) setGeometry(data); })
      .catch(e => { if (!cancelled) { setGeometry(null); setGeometryError(e.message); } })
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

  return <div className="app-shell recorded-demo inspection">
    <header className="inspection-header">
      <div className="inspection-brand"><Crosshair size={24} /><div><h1>AutoFrame <span>3D</span></h1><p>Expose the wrong poses that pass your checks.</p></div></div>
      <span className="recorded-badge"><span />Recorded benchmark</span>
    </header>
    {error && <div className="error-banner" role="alert">{error} <button onClick={() => window.location.reload()}>Retry</button></div>}
    <div className="case-toolbar">
      <div className="case-field"><label htmlFor="recorded-case">Saved example</label><select id="recorded-case" value={caseId} disabled={!catalogue} onChange={e => { setCaseId(e.target.value); setVariantId("baseline"); setShowTruth(false); }}>{catalogue?.cases.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}</select></div>
      <div className="case-field"><label htmlFor="recorded-method">Recorded method</label><select id="recorded-method" value={variantId} disabled={!selected} onChange={e => setVariantId(e.target.value)}>{selected?.variants.map(v => <option key={v.id} value={v.id}>{v.label}</option>)}</select></div>
      <span className="case-identity">{selected?.case_id}</span>
      <button className="button download-button" disabled={!selected} onClick={() => void downloadEvidence()}><Archive size={16} /><span>Download recorded evidence</span></button>
    </div>
    <main className="inspection-workspace">
      <section className="inspection-viewport">
        <div className="inspection-view-heading"><div><span>Saved alignment</span><h2>{selected ? `T-LESS object ${selected.object_id}` : "Loading recorded evidence"}</h2></div><span className="coordinate-note">Camera frame · metres</span></div>
        <div className="inspection-canvas">
          <Scene data={geometry} showScan={showScan} showEstimate={showEstimate} showTruth={showTruth} viewCommand={viewCommand} />
          {(!geometry || loading || geometryError) && <div className="geometry-notice" role="status">{loading ? "Loading recorded geometry…" : geometryError ?? "Waiting for recorded evidence…"}{geometryError && <p>Metrics remain available. No geometry is fabricated.</p>}</div>}
          <div className="layer-controls" aria-label="Geometry layers">
            <button aria-pressed={showScan} onClick={() => setShowScan(!showScan)}><span className="layer-dot scan-dot" />Observed scan</button>
            <button aria-pressed={showEstimate} onClick={() => setShowEstimate(!showEstimate)}><span className="layer-dot metal-dot" />Estimated CAD</button>
            <button aria-pressed={showTruth} onClick={() => setShowTruth(!showTruth)}><span className="layer-dot gt-dot" />Benchmark ground truth {showTruth ? <Eye size={14} /> : <EyeOff size={14} />}</button>
          </div>
          <span className="viewport-caption">Actual CAD · saved pose<br />Floor/grid are display aids</span>
        </div>
        <div className="camera-toolbar"><span>Drag to orbit · scroll to zoom</span><div>{[["fit", "Fit view"], ["front", "Front"], ["side", "Side"], ["top", "Top"]].map(([view, label]) => <button key={view} disabled={!geometry} onClick={() => setViewCommand(v => ({ id: v.id + 1, view }))}>{view === "fit" && <RotateCcw size={13} />}{label}</button>)}</div></div>
      </section>
      <aside className="inspection-inspector">
        <div className="inspector-verdict"><span>Fit ≠ pose correctness</span>{result && <div className="verdict-pair"><div><small>Geometric fit</small><strong className={result.accepted ? "positive" : "negative"}>{result.accepted ? "Accepted" : "Rejected"}</strong></div><div><small>Benchmark pose</small><strong className={result.correct ? "positive" : "negative"}>{result.correct ? "Correct" : "Incorrect"}</strong></div></div>}<p>Correctness uses benchmark ground truth.</p></div>
        <div className="inspector-tabs" role="tablist" aria-label="Case inspector">{["results", "copilot", "evidence"].map(t => <button key={t} id={`tab-${t}`} role="tab" aria-selected={tab === t} aria-controls={`panel-${t}`} onClick={() => setTab(t)}>{t[0].toUpperCase() + t.slice(1)}</button>)}</div>
        <div className="inspector-content">
          <section id="panel-results" role="tabpanel" aria-labelledby="tab-results" hidden={tab !== "results"}>
            <h2>Recorded results</h2>
            {selected && selected.variants.length > 1 && <div className="regression-card"><h3>Better fit. Worse pose.</h3><p>Recorded reciprocal refinement crossed the correctness threshold.</p><div className="comparison-grid">{selected.variants.map(v => <div key={v.id} className={variantId === v.id ? "selected-method" : ""}><h4>{v.experimental ? "Reciprocal" : "Baseline"}</h4><span>RMSE</span><strong>{fmt(v.record.alignment_quality_metrics.inlier_rmse_m * 1000, 2)} <small>mm</small></strong><span>MSSD/D</span><strong>{fmt(v.record.pose_metrics.mssd_over_diameter, 4)}</strong><b className={v.record.correct ? "positive" : "negative"}>{v.record.correct ? "Correct" : "Incorrect"}</b><small>{v.record.accepted ? "Geometrically accepted" : "Rejected"}</small></div>)}</div><p>Experimental · rejected for production promotion. Same inputs, thresholds and six starts.</p></div>}
            {result && <div className="result-metrics">
              <div><label>Fitness <small>scan-point fraction</small></label><strong>{fmt(result.alignment_quality_metrics.fitness)}</strong><p>Acceptance ≥ {thresholds?.minimum_fitness}</p></div>
              <div><label>Inlier RMSE</label><strong>{fmt(result.alignment_quality_metrics.inlier_rmse_m * 1000, 2)} <small>mm</small></strong><p>Acceptance ≤ {fmt((thresholds?.maximum_inlier_rmse_m ?? NaN) * 1000, 1)} mm</p></div>
              <div><label>Symmetry-aware MSSD / diameter</label><strong className={!result.correct ? "negative" : ""}>{fmt(result.pose_metrics.mssd_over_diameter, 4)}</strong><p>Correctness ≤ {catalogue?.config.pose_correctness.maximum_normalized_mssd} · dimensionless</p></div>
            </div>}
            <p className="inspector-note">Fitness counts scan points within {fmt((thresholds?.maximum_correspondence_distance_m ?? NaN) * 1000, 1)} mm of the model. Geometric acceptance does not guarantee a correct pose.</p>

          </section>
          <section id="panel-copilot" role="tabpanel" aria-labelledby="tab-copilot" hidden={tab !== "copilot"}><InvestigationPanel caseId={selected?.case_id} onSelect={(viewerId, methodId) => { setCaseId(viewerId); setVariantId(methodId); setShowTruth(false); setTab("results"); }} /></section>
          <section id="panel-evidence" role="tabpanel" aria-labelledby="tab-evidence" hidden={tab !== "evidence"}>
            <h2>Evidence & limits</h2>
            {catalogue && <><div className="aggregate-card"><h3>Corrected held-out aggregate</h3><div><strong>{audit?.accepted_and_correct}</strong> accepted-and-correct<br /><strong>{audit?.accepted_but_wrong}</strong> accepted-but-wrong</div><p>{audit?.affected_rescored} rescored · {audit?.unaffected_carried_forward} labels carried forward, including three independently checked controls. Not a full independent rescore.</p></div><p>{catalogue.evidence.scope}</p>
              <details><summary>Method & experimental limits</summary><p>{variant?.method}</p><p>{catalogue.evidence.pilot}</p><p>{catalogue.evidence.experimental}</p></details>
              <details><summary>Configuration & provenance</summary><p>Versioned copy: <code>{variant?.publication_copy}</code></p><p>Original evidence: <code>{variant?.evidence_source}</code></p><p>Source SHA-256: <code>{variant?.source_sha256}</code></p><p>Execution adapter SHA-256: <code>{variant?.execution_source_identity}</code></p><p>Frozen configuration SHA-256: <code>{catalogue.config_sha256}</code></p><p>{catalogue.evidence.historical_provenance}</p><pre>{JSON.stringify(catalogue.config, null, 2)}</pre><pre>{JSON.stringify(catalogue.publication, null, 2)}</pre></details>
              <details><summary>AI & ground-truth dependence</summary><p>{catalogue.evidence.AI}</p><p>GT instance masks were used. Synthetic model proposals receive GT-derived pose errors and labels: an offline adversary, not a GT-free detector.</p></details>
            </>}
            <details className="replay-details"><summary>Optional local replay · new compute</summary><p>Requires original local dataset inputs; bundled display geometry is not a scoring input. Recomputes the historical baseline, not experimental refinements.</p><button className="button button-secondary" disabled={!selected?.geometry_available || variantId !== "baseline" || Boolean(jobId)} onClick={() => void startReplay()}>Run baseline replay</button>{replay && <p role="status">{replay}</p>}</details>
          </section>
        </div>
      </aside>
    </main>
    <footer className="inspection-footer"><span>Recorded registration · GT instance masks · no live evaluation</span><span>Benchmark inspection, not a validated industrial pose estimator or proven adaptive AI agent</span></footer>
  </div>;
}
