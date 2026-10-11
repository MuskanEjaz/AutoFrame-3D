import { useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Archive,
  Bot,
  Box,
  Check,
  CircleHelp,
  Crosshair,
  Eye,
  EyeOff,
  FlaskConical,
  LoaderCircle,
  RotateCcw,
  ScanLine,
  Search,
  ShieldCheck,
  Square,
  Target,
} from "lucide-react";
import Scene, { type GeometryPayload } from "./Scene";

type Scenario = {
  object_kind: "near_symmetric" | "asymmetric_control";
  visibility: "top" | "front" | "all";
  seed: number;
  yaw_deg: number;
  noise_std_m: number;
  background_points: number;
};

type Measurement = {
  case_id?: string;
  source?: "synthetic" | "tless";
  config: Record<string, unknown>;
  classification: string;
  alignment_quality_metrics: { fitness: number; inlier_rmse_m: number };
  pose_errors: { translation_error_m: number; rotation_error_deg: number };
  pose_metrics?: { mssd_m: number; mssd_over_diameter: number };
};

type Event = Record<string, any>;
type Job = {
  job_id: string;
  type: string;
  status: string;
  progress: { completed: number; total: number };
  events: Event[];
  result: Record<string, any> | null;
  error: string | null;
};

const initialScenario: Scenario = {
  object_kind: "near_symmetric",
  visibility: "top",
  seed: 41,
  yaw_deg: 23,
  noise_std_m: 0.001,
  background_points: 0,
};

const number = (value: unknown, digits = 3) =>
  typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "--";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export default function App() {
  const [scenario, setScenario] = useState(initialScenario);
  const [health, setHealth] = useState<Record<string, any> | null>(null);
  const [sceneData, setSceneData] = useState<GeometryPayload | null>(null);
  const [measurement, setMeasurement] = useState<Measurement | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [history, setHistory] = useState<Event[]>([]);
  const [dataSource, setDataSource] = useState<"synthetic" | "tless">("synthetic");
  const [datasetCases, setDatasetCases] = useState<Event[]>([]);
  const [datasetManifest, setDatasetManifest] = useState("smoke20_frozen");
  const [datasetGroup, setDatasetGroup] = useState("original");
  const [selectedCase, setSelectedCase] = useState<string | null>(null);
  const [budget, setBudget] = useState(12);
  const [mode, setMode] = useState("deterministic");
  const [showScan, setShowScan] = useState(true);
  const [showEstimate, setShowEstimate] = useState(true);
  const [showTruth, setShowTruth] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const seenCases = useRef(new Set<string>());

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      request<Record<string, any>>("/api/health"),
      request<any>("/api/sample?object_kind=near_symmetric&visibility=top&seed=41&yaw_deg=23"),
    ])
      .then(([healthData, sample]) => {
        if (cancelled) return;
        setHealth(healthData);
        setSceneData(sample);
        setMeasurement({
          config: sample.config,
          classification: sample.classification,
          alignment_quality_metrics: sample.alignment_quality_metrics,
          pose_errors: sample.pose_errors,
        });
      })
      .catch((reason: Error) => !cancelled && setError(reason.message));
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (dataSource !== "tless") return;
    let cancelled = false;
    setError(null);
    request<{ cases: Event[]; group: string; manifest: string }>(
      `/api/tless/cases?group=${datasetGroup}&manifest=${datasetManifest}`,
    )
      .then((response) => {
        if (cancelled) return;
        setDatasetCases(response.cases);
        const firstValid = response.cases.find((item) => item.status === "valid");
        if (firstValid) void selectRecordedCase(firstValid.case_id, firstValid);
        else {
          setSceneData(null);
          setMeasurement(null);
          setSelectedCase(null);
        }
      })
      .catch((reason: Error) => !cancelled && setError(reason.message))
      .finally(() => !cancelled && setBusy(false));
    return () => { cancelled = true; };
  }, [dataSource, datasetGroup, datasetManifest]);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const current = await request<Job>(`/api/jobs/${jobId}`);
        if (cancelled) return;
        setJob(current);
        setHistory(current.events);
        for (const event of current.events) {
          if (event.case_id && !seenCases.current.has(event.case_id)) {
            seenCases.current.add(event.case_id);
            void selectRecordedCase(event.case_id, event);
          }
        }
        if (["completed", "stopped", "failed"].includes(current.status)) {
          setBusy(false);
          setJobId(null);
          if (current.error) setError(current.error);
        }
      } catch (reason) {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "Could not read job state");
          setBusy(false);
          setJobId(null);
        }
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 700);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [jobId]);

  async function selectRecordedCase(caseId: string, event?: Event) {
    setSelectedCase(caseId);
    if (event?.classification) setMeasurement(event as Measurement);
    try {
      if (dataSource === "tless") {
        const parameters = new URLSearchParams({ group: datasetGroup, manifest: datasetManifest });
        const [details, geometry] = await Promise.all([
          request<any>(`/api/tless/cases/${caseId}?${parameters}`),
          request<GeometryPayload>(`/api/tless/cases/${caseId}/geometry?${parameters}`),
        ]);
        setMeasurement({
          case_id: caseId,
          source: "tless",
          config: geometry.config,
          classification: details.category ?? details.status,
          alignment_quality_metrics: details.alignment_quality_metrics ?? { fitness: Number.NaN, inlier_rmse_m: Number.NaN },
          pose_errors: { translation_error_m: Number.NaN, rotation_error_deg: Number.NaN },
          pose_metrics: details.pose_metrics,
        });
        setSceneData(geometry);
        return;
      }
      const [details, geometry] = await Promise.all([
        request<any>(`/api/cases/${caseId}`),
        request<GeometryPayload>(`/api/cases/${caseId}/geometry`),
      ]);
      setMeasurement({ ...details, case_id: caseId });
      setSceneData(geometry);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load the selected case");
    }
  }

  function beginJob(id: string) {
    setJobId(id);
    setBusy(true);
    setJob(null);
    setError(null);
    seenCases.current.clear();
  }

  async function loadSample() {
    setError(null);
    setBusy(true);
    try {
      const sample = await request<any>(
        `/api/sample?${new URLSearchParams({ ...scenario, yaw_deg: String(scenario.yaw_deg), seed: String(scenario.seed), noise_std_m: String(scenario.noise_std_m), background_points: String(scenario.background_points) })}`,
      );
      setSceneData(sample);
      setMeasurement({ config: sample.config, classification: sample.classification, alignment_quality_metrics: sample.alignment_quality_metrics, pose_errors: sample.pose_errors });
      setSelectedCase(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load sample");
    } finally {
      setBusy(false);
    }
  }

  async function runBaseline() {
    try {
      setError(null);
      setDataSource("synthetic");
      const response = await request<{ job_id: string }>("/api/baseline", {
        method: "POST",
        body: JSON.stringify(scenario),
      });
      beginJob(response.job_id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Baseline could not start");
    }
  }

  async function startCampaign() {
    try {
      setError(null);
      setDataSource("synthetic");
      const response = await request<{ job_id: string }>("/api/campaigns", {
        method: "POST",
        body: JSON.stringify({ budget, mode }),
      });
      beginJob(response.job_id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Campaign could not start");
    }
  }

  async function stopCampaign() {
    if (!jobId) return;
    try {
      await request(`/api/jobs/${jobId}/stop`, { method: "POST" });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Stop request failed");
    }
  }

  async function runCaseAction(action: "simplify" | "replay") {
    if (!selectedCase) return;
    try {
      setError(null);
      const path = dataSource === "tless"
        ? `/api/tless/cases/${selectedCase}/${action}?group=${datasetGroup}&manifest=${datasetManifest}`
        : `/api/cases/${selectedCase}/${action}`;
      const response = await request<{ job_id: string }>(path, { method: "POST" });
      beginJob(response.job_id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : `Could not ${action} case`);
    }
  }

  async function exportCase() {
    if (!selectedCase) return;
    try {
      setError(null);
      const path = dataSource === "tless"
        ? `/api/tless/cases/${selectedCase}/export?group=${datasetGroup}&manifest=${datasetManifest}`
        : `/api/cases/${selectedCase}/export`;
      const response = await fetch(path);
      if (!response.ok) throw new Error(`Export failed (${response.status})`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `autoframe-${dataSource}-${selectedCase}.zip`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Export failed");
    }
  }

  async function selectHistory(event: Event) {
    if (event.case_id) await selectRecordedCase(event.case_id, event);
  }

  const classification = measurement?.classification ?? "awaiting sample";
  const acceptedWrong = classification === "accepted_but_wrong";
  const acceptedCorrect = classification === "accepted_correct" || classification === "accepted_and_correct";
  const running = busy && Boolean(jobId);
  const visibleHistory: Event[] = dataSource === "tless"
    ? datasetCases.map((item) => ({ ...item, classification: item.category, kind: "dataset_case", arm: "tless" }))
    : history;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark"><Crosshair size={20} strokeWidth={1.8} /></div>
          <div className="brand-copy"><strong>AUTOFRAME 3D</strong><span>REGISTRATION STRESS BENCH</span></div>
        </div>
        <div className="tagline">Break the pose before it breaks the robot.</div>
        <div className="connection-state">
          <span className={`status-dot ${health?.api_key_configured ? "live" : "local"}`} />
          <span>{health?.api_key_configured ? "NEBIUS READY" : "LOCAL · DETERMINISTIC"}</span>
          <CircleHelp size={14} aria-label="Model integration status" />
        </div>
      </header>

      <main className="workbench">
        <aside className="scenario-panel panel">
          <div className="panel-heading">
            <div><span className="eyebrow">01 / INPUT</span><h1>Scenario</h1></div>
            <ScanLine size={19} className="heading-icon" />
          </div>
          <div className="control-stack">
            <button className="button button-quiet" onClick={loadSample} disabled={busy}><Box size={16} />Load sample</button>
            <button className="button button-secondary" onClick={runBaseline} disabled={busy}><Crosshair size={16} />Run baseline</button>
            <button className="button button-primary" onClick={startCampaign} disabled={busy}><Search size={16} />Start stress test</button>
            {running && <button className="button button-stop" onClick={stopCampaign}><Square size={14} fill="currentColor" />Stop campaign</button>}
          </div>
          <label className="field-label" htmlFor="object-kind">CAD object</label>
          <select id="object-kind" value={scenario.object_kind} onChange={(event) => setScenario({ ...scenario, object_kind: event.target.value as Scenario["object_kind"] })}>
            <option value="near_symmetric">Near-symmetric body</option>
            <option value="asymmetric_control">Asymmetric control</option>
          </select>

          <label className="field-label" htmlFor="visibility">Scan visibility</label>
          <select id="visibility" value={scenario.visibility} onChange={(event) => setScenario({ ...scenario, visibility: event.target.value as Scenario["visibility"] })}>
            <option value="top">Top-facing partial</option>
            <option value="front">Front-facing partial</option>
            <option value="all">Full surface</option>
          </select>

          <div className="field-row"><label className="field-label" htmlFor="seed">Random seed</label><span className="field-unit">INT</span></div>
          <input id="seed" type="number" min="0" max="1000000" value={scenario.seed} onChange={(event) => setScenario({ ...scenario, seed: Number(event.target.value) })} />

          <div className="field-row slider-heading"><label className="field-label" htmlFor="yaw">Object yaw</label><span className="field-value">{scenario.yaw_deg}°</span></div>
          <input id="yaw" className="range-input" type="range" min="-180" max="180" step="1" value={scenario.yaw_deg} onChange={(event) => setScenario({ ...scenario, yaw_deg: Number(event.target.value) })} />

          <div className="field-row"><label className="field-label" htmlFor="noise">Point noise</label><span className="field-unit">METRES</span></div>
          <input id="noise" type="number" min="0" max="0.005" step="0.0005" value={scenario.noise_std_m} onChange={(event) => setScenario({ ...scenario, noise_std_m: Number(event.target.value) })} />

          <div className="section-rule" />
          <div className="panel-heading compact-heading"><div><span className="eyebrow">02 / SEARCH</span><h2>Experiment budget</h2></div></div>
          <div className="field-row budget-row">
            <label className="field-label" htmlFor="budget">Registration evaluations</label>
            <select id="budget" className="budget-select" value={budget} onChange={(event) => setBudget(Number(event.target.value))}>
              {[6, 8, 10, 12].map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </div>
          <div className="budget-split"><span>SEARCH ARM</span><b>{budget / 2}</b><span>SEEDED RANDOM</span><b>{budget / 2}</b></div>
          <label className="field-label" htmlFor="mode">Search mode</label>
          <select id="mode" value={mode} onChange={(event) => setMode(event.target.value)}>
            <option value="deterministic">Deterministic local</option>
            <option value="live_ai" disabled={!health?.api_key_configured}>Nemotron · live</option>
          </select>
          <div className="budget-note"><ShieldCheck size={14} /> Up to 4 model calls · {health?.api_key_configured ? health.model : "No API key configured"}</div>

        </aside>

        <section className="viewer-panel panel">
          <div className="viewer-header">
            <div><span className="eyebrow">03 / REGISTRATION VIEW</span><h2>{dataSource === "tless" ? `T-LESS object ${String(sceneData?.config?.object_id ?? "--")}` : sceneData?.config?.object_kind === "asymmetric_control" ? "Asymmetric control" : "Near-symmetric body"}</h2></div>
            <select
              className="source-select"
              aria-label="Registration data source"
              value={dataSource}
              onChange={(event) => {
                const next = event.target.value as "synthetic" | "tless";
                setDataSource(next);
                if (next === "synthetic") void loadSample();
              }}
            >
              <option value="synthetic">Synthetic sample</option>
              <option value="tless">T-LESS real · smoke 20</option>
            </select>
            <div className="viewer-badges"><span className="frame-badge">WORLD FRAME · METRES</span><span className="classification-badge" data-class={classification}>{classification.replaceAll("_", " ")}</span></div>
          </div>
          <div className="viewer-stage">
            {sceneData ? <Scene data={sceneData} showScan={showScan} showEstimate={showEstimate} showTruth={showTruth} /> : <div className="loading-state"><LoaderCircle className="spin" size={22} />Building sample geometry</div>}
            <div className="viewer-legend">
              <button className={showScan ? "legend-on" : "legend-off"} onClick={() => setShowScan(!showScan)} title="Toggle scan points"><span className="legend-dot legend-scan" />Scan {showScan ? <Eye size={13} /> : <EyeOff size={13} />}</button>
              <button className={showEstimate ? "legend-on" : "legend-off"} onClick={() => setShowEstimate(!showEstimate)} title="Toggle estimated pose"><span className="legend-dot legend-estimate" />Estimate {showEstimate ? <Eye size={13} /> : <EyeOff size={13} />}</button>
              <button className={showTruth ? "legend-on" : "legend-off"} onClick={() => setShowTruth(!showTruth)} title="Toggle ground truth"><span className="legend-dot legend-truth" />Ground truth {showTruth ? <Eye size={13} /> : <EyeOff size={13} />}</button>
            </div>
            <div className="axis-note">Z ↑ <span>Y ↗</span></div>
            {!sceneData && <div className="scene-empty"><FlaskConical size={26} /><span>{dataSource === "tless" ? "No real scan cases in this result group" : "Load a synthetic scan to begin"}</span></div>}
          </div>
          <div className="viewer-footer">
            <span><span className="live-indicator" />{sceneData ? `${sceneData.scan.length.toLocaleString()} scan points` : "No scan loaded"}</span>
            <span>{dataSource === "tless" ? "BOP camera frame · ground-truth instance mask" : "Drag to orbit · scroll to zoom"}</span>
            <span>{measurement?.case_id ? `CASE ${measurement.case_id.slice(0, 8).toUpperCase()}` : "SAMPLE SCENARIO"}</span>
          </div>
        </section>

        <aside className="history-panel panel">
          <div className="panel-heading history-heading">
            <div><span className="eyebrow">04 / {dataSource === "tless" ? "BOP19 TEST CASES" : "CAMPAIGN"}</span><h2>{dataSource === "tless" ? "T-LESS results" : "Experiment history"}</h2></div>
            <Activity size={18} className="heading-icon" />
          </div>
          <div className="campaign-state">
            <div className={`campaign-glyph ${running ? "is-running" : ""}`}>{running ? <LoaderCircle size={17} className="spin" /> : <Bot size={17} />}</div>
            <div><strong>{running ? `${job?.type === "campaign" ? "Stress test" : job?.type ?? "Experiment"} running` : job?.status === "completed" ? "Campaign complete" : dataSource === "tless" ? "Registration evaluation with GT instance masks" : "Ready"}</strong><span>{running ? `${job?.progress.completed ?? 0} / ${job?.progress.total ?? budget} registrations` : dataSource === "tless" ? "Custom internal evaluation · not official BOP" : health?.model_mode === "deterministic_only" ? "Deterministic search mode" : "Awaiting experiment"}</span></div>
            <span className="mode-tag">{job?.result?.mode === "ai_live" ? "LIVE AI" : mode === "live_ai" && health?.api_key_configured ? "AI READY" : "LOCAL"}</span>
          </div>
          {job?.result?.summary && <div className="comparison-strip"><span>SEARCH ARM <b>{job.result.summary.agent_failures}/{job.result.summary.agent_evaluations}</b></span><span>RANDOM <b>{job.result.summary.random_failures}/{job.result.summary.random_evaluations}</b></span></div>}
          {error && <div className="error-banner"><AlertTriangle size={15} /><span>{error}</span><button onClick={() => setError(null)} aria-label="Dismiss error">×</button></div>}
          {job?.result?.passed !== undefined && <div className={`replay-result ${job.result.passed ? "passed" : "failed"}`}>{job.result.passed ? <Check size={15} /> : <AlertTriangle size={15} />}{job.result.passed ? "Replay verified" : "Replay mismatch"}</div>}
          {dataSource === "tless" && <div className="dataset-history-controls">
            <select aria-label="T-LESS result manifest" value={datasetManifest} onChange={(event) => setDatasetManifest(event.target.value)}>
              <option value="smoke20_frozen">Frozen smoke · 20</option>
              <option value="development_tuning20">Development tuning · 20</option>
              <option value="smoke20">Initial smoke · 20</option>
              <option value="heldout200">Held-out · 200</option>
            </select>
            <select aria-label="T-LESS scan group" value={datasetGroup} onChange={(event) => setDatasetGroup(event.target.value)}>
              <option value="original">Original scans</option>
              <option value="perturbed">Perturbed scans</option>
            </select>
          </div>}
          <div className="history-list">
            {visibleHistory.length === 0 && !job ? <div className="empty-history"><div className="empty-mark"><Target size={21} /></div><strong>{dataSource === "tless" ? "No result manifest loaded" : "No experiments yet"}</strong><span>{dataSource === "tless" ? "Run the T-LESS smoke evaluation to load cases." : "Run the baseline or start a stress test."}</span></div> : null}
            {visibleHistory.length === 0 && job ? <div className="empty-history"><LoaderCircle size={20} className="spin" /><span>Preparing first evaluation</span></div> : null}
            {visibleHistory.map((event, index) => {
              const isMeasured = event.kind === "experiment_measured" || event.kind === "simplification_trial";
              const isModel = event.kind === "model_proposal";
              const isDataset = event.kind === "dataset_case";
              const title = isDataset
                ? `Scene ${event.scene_id} · object ${event.object_id} · ${String(event.category ?? event.status).replaceAll("_", " ")}`
                : isMeasured ? `${event.arm === "random" ? "Random search" : event.arm === "simplification" ? "Simplification" : event.arm === "agent" ? "Search agent" : "Baseline"} · ${String(event.classification ?? "").replaceAll("_", " ")}` : isModel ? `Nemotron proposal ${event.number}` : event.kind === "agent_fallback" ? "Deterministic fallback" : event.kind === "experiment_started" ? `${event.arm === "random" ? "Random" : "Search"} evaluation started` : event.kind === "simplification_trial" ? "Simplification trial" : event.kind ?? "Action";
              return (
                <button key={`${event.kind}-${index}`} className={`history-item ${event.case_id === selectedCase ? "selected" : ""} ${(isMeasured || isDataset) && event.classification === "accepted_but_wrong" ? "history-failure" : ""}`} onClick={() => void selectHistory(event)} disabled={!event.case_id || (isDataset && event.status !== "valid")}>
                  <span className={`history-marker ${isModel ? "marker-model" : (isMeasured || isDataset) && event.classification === "accepted_but_wrong" ? "marker-failure" : ""}`}>{isMeasured || isDataset ? <Target size={13} /> : isModel ? <Bot size={13} /> : <Activity size={13} />}</span>
                  <span className="history-copy"><strong>{title}</strong><span>{isDataset ? `Fit ${number(event.alignment_quality_metrics?.fitness, 2)} · RMSE ${number(event.alignment_quality_metrics?.inlier_rmse_m, 3)} m · MSSD/d ${number(event.pose_metrics?.mssd_over_diameter, 2)}` : isMeasured ? `Fit ${number(event.alignment_quality_metrics?.fitness, 2)} · RMSE ${number(event.alignment_quality_metrics?.inlier_rmse_m, 3)} m` : isModel ? JSON.stringify(event.proposal) : event.message ?? `Evaluation ${event.index ?? ""}`}</span></span>
                  {event.case_id && <span className="history-select"><Eye size={14} /></span>}
                </button>
              );
            })}
          </div>
          {job?.error && <div className="job-error">{job.error}</div>}
        </aside>

        <section className="metrics-panel panel">
          <div className="metrics-title"><span className="eyebrow">05 / MEASUREMENTS</span><strong>{acceptedWrong ? <><AlertTriangle size={15} /> ACCEPTED · POSE WRONG</> : acceptedCorrect ? <><ShieldCheck size={15} /> ACCEPTED · POSE CORRECT</> : <><Activity size={15} /> {classification.toUpperCase().replaceAll("_", " ")}</>}</strong></div>
          <div className="metric-cell"><span>ALIGNMENT FITNESS</span><strong>{number(measurement?.alignment_quality_metrics.fitness, 3)}</strong><small>alignment quality</small></div>
          <div className="metric-cell"><span>INLIER RMSE</span><strong>{number(measurement?.alignment_quality_metrics.inlier_rmse_m, 4)}<i> m</i></strong><small>alignment quality</small></div>
          <div className={`metric-cell ${acceptedWrong ? "metric-alert" : ""}`}><span>{dataSource === "tless" ? "MSSD / DIAMETER" : "TRANSLATION ERROR"}</span><strong>{dataSource === "tless" ? number(measurement?.pose_metrics?.mssd_over_diameter, 3) : number(measurement?.pose_errors.translation_error_m, 4)}{dataSource === "tless" ? "" : <i> m</i>}</strong><small>{dataSource === "tless" ? "BOP symmetry-aware" : "estimated vs ground truth"}</small></div>
          <div className={`metric-cell ${acceptedWrong ? "metric-alert" : ""}`}><span>{dataSource === "tless" ? "MSSD DISTANCE" : "ROTATION ERROR"}</span><strong>{dataSource === "tless" ? number(measurement?.pose_metrics?.mssd_m, 4) : number(measurement?.pose_errors.rotation_error_deg, 2)}<i>{dataSource === "tless" ? " m" : "°"}</i></strong><small>{dataSource === "tless" ? "symmetry-aware surface displacement" : "estimated vs ground truth"}</small></div>
          <div className="case-actions">
            <button className="button button-quiet" disabled={!selectedCase || busy} onClick={() => void runCaseAction("replay")}><RotateCcw size={15} />Replay</button>
            <button className="button button-quiet" disabled={!selectedCase || !acceptedWrong || busy || dataSource === "tless"} onClick={() => void runCaseAction("simplify")}><Search size={15} />Simplify failure</button>
            <button className="button button-export" disabled={!selectedCase || busy} onClick={() => void exportCase()}><Archive size={15} />Export case</button>
          </div>
        </section>
      </main>
      <footer className="app-footer"><span>AUTOFRAME 3D <i>·</i> SYNTHETIC REGISTRATION TESTING</span><span>Alignment quality metrics are not calibrated confidence probabilities.</span></footer>
    </div>
  );
}