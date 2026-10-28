import { useEffect, useState } from "react";
import { evidenceScope, type ScopeEvidence } from "./evidenceScope";

type Evidence = ScopeEvidence & { id: string; viewer_id?: string; case_id?: string; metrics?: { method_id: string }; [key: string]: unknown };
type Answer = {
  status: string; analysis_mode: string; evidence_computation: string; message: string;
  question: string; selected_case_id: string | null;
  findings: { kind: string; text: string; evidence_ids: string[] }[];
  evidence: Evidence[]; model_turns: number; tool_executions: number; prose_verification: string;
};
const examples = [
  "Why did the selected alignment pass geometric acceptance but fail benchmark correctness?",
  "Find the recorded refinement where RMSE improved while pose correctness worsened.",
  "What does the corrected held-out aggregate support, and what can it not establish?",
  "Can the available evidence establish that sensor noise caused the wrong poses?",
];

export default function InvestigationPanel({ caseId, onSelect }: {
  caseId?: string; onSelect: (viewerId: string, methodId: string) => void;
}) {
  const [question, setQuestion] = useState(examples[0]);
  const [available, setAvailable] = useState(false);
  const [availability, setAvailability] = useState("Checking live analysis availability…");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetch("/api/investigation/status").then(async r => {
      if (!r.ok) throw Error("Local API unavailable");
      const status = await r.json();
      if (!cancelled) { setAvailable(status.available); setAvailability(status.message); }
    }).catch(() => { if (!cancelled) setAvailability("Live analysis unavailable: start/configure the local API"); });
    return () => { cancelled = true; };
  }, []);

  async function ask() {
    setLoading(true); setError(null); setAnswer(null);
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 65000);
    try {
      const response = await fetch("/api/investigation", {
        method: "POST", headers: { "Content-Type": "application/json" }, signal: controller.signal,
        body: JSON.stringify({ question, selected_case_id: caseId ?? null }),
      });
      if (!response.ok) throw Error(`Investigation API returned ${response.status}`);
      setAnswer(await response.json());
    } catch { setError("Analysis failed or timed out. No mock or cached answer was substituted."); }
    finally { window.clearTimeout(timer); setLoading(false); }
  }

  function downloadResponse() {
    if (!answer) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(answer, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url; link.download = "autoframe3d-investigation-response.json";
    link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 5000);
  }

  return <section className="panel recorded-evidence investigation-panel">
    <span className="eyebrow">05 / INVESTIGATION COPILOT</span>
    <h2>Ask about recorded evidence</h2>
    <p>{availability}. Live NVIDIA Nemotron analysis through Nebius Token Factory; underlying registration results remain recorded. No registration runs from this panel.</p>
    <div className="investigation-examples">{examples.map(q => <button key={q} className="button button-secondary" disabled={loading} onClick={() => setQuestion(q)}>{q}</button>)}</div>
    <label className="field-label" htmlFor="investigation-question">Evidence question · selected case {caseId ?? "none"}</label>
    <textarea id="investigation-question" maxLength={1500} rows={3} value={question} disabled={loading} onChange={e => setQuestion(e.target.value)} />
    <button className="button button-export" disabled={!available || loading || !question.trim()} onClick={() => void ask()}>{loading ? "Investigating recorded evidence…" : "Ask Nemotron · live inference"}</button>
    <p>Explicit inference request: at most three model turns and six read-only tool executions, with a 60-second deadline. Numerical verdicts are deterministic. GT instance masks and benchmark GT were used.</p>
    {error && <p role="alert">{error}</p>}
    {answer && <div role="status">
      <p><strong>{answer.analysis_mode.toUpperCase()} ANALYSIS · {answer.status}</strong> · RECORDED REGISTRATION EVIDENCE</p>
      <p>Question: {answer.question} · case context: {answer.selected_case_id ?? "no selected case"}</p>
      <p>{answer.message}</p><p>{answer.prose_verification}</p>
      <aside aria-label="Evidence scope" className="investigation-scope">
        <h3>Evidence scope</h3>
        <p>Deterministic note from returned evidence flags, separate from the model-generated explanation.</p>
        <ul>{evidenceScope(answer.evidence, answer.evidence_computation).map(note => <li key={note}>{note}</li>)}</ul>
      </aside>
      <h3>Model-generated explanation</h3>
      {answer.findings.map((f, i) => <div key={i}><strong>{f.kind}</strong><p>{f.text}</p><p>Evidence: {f.evidence_ids.join(", ")}</p></div>)}
      <p>{answer.model_turns} model turns · {answer.tool_executions} tool executions</p>
      <button className="button button-secondary" onClick={downloadResponse}>Download investigation response</button>
      <h3>Authoritative evidence · generated by read-only tools</h3>
      {answer.evidence.map(e => <details key={e.id} open><summary>{e.id}</summary>
        {e.viewer_id && <button className="button button-secondary" onClick={() => onSelect(e.viewer_id!, e.metrics?.method_id ?? "baseline")}>View cited case</button>}
        <pre>{JSON.stringify(e, null, 2)}</pre>
      </details>)}
    </div>}
  </section>;
}
