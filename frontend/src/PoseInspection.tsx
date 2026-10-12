import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Eye,
  MousePointer2,
  Pause,
  Play,
  RotateCcw,
  ScanLine,
} from "lucide-react";
import PoseScene from "./PoseScene";
import {
  correctionPreview,
  difference,
  editEstimate,
  eulerDegrees,
  exportSynthetic,
  initialEstimate,
  type Pose,
} from "./poseMath";
import "./pose-inspection.css";
type Playback = { original: Pose; elapsed: number; running: boolean };
export default function PoseInspection() {
  const [estimate, setEstimate] = useState(initialEstimate),
    [playback, setPlayback] = useState<Playback | null>(null);
  const [showEstimate, setShowEstimate] = useState(true),
    [showReference, setShowReference] = useState(false),
    [scanner, setScanner] = useState(true),
    [view, setView] = useState(0),
    [edit, setEdit] = useState(false),
    [mode, setMode] = useState<"translate" | "rotate">("translate"),
    [error, setError] = useState("");
  const running = playback?.running ?? false;
  useEffect(() => {
    if (!running) return;
    let id = 0,
      last = performance.now();
    const tick = (now: number) => {
      const dt = (now - last) / 1000;
      last = now;
      setPlayback((p) => {
        if (!p || !p.running) return p;
        const elapsed = Math.min(5, p.elapsed + dt);
        return { ...p, elapsed, running: elapsed < 5 };
      });
      id = requestAnimationFrame(tick);
    };
    const visibility = () => {
      cancelAnimationFrame(id);
      if (!document.hidden) {
        last = performance.now();
        id = requestAnimationFrame(tick);
      }
    };
    visibility();
    document.addEventListener("visibilitychange", visibility);
    return () => {
      cancelAnimationFrame(id);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, [running]);
  const displayed = playback
      ? correctionPreview(playback.original, playback.elapsed)
      : estimate,
    d = difference(displayed);
  const play = (replay = false) => {
    setShowEstimate(true);
    setEdit(false);
    setError("");
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    setPlayback((p) => ({
      original: p?.original ?? structuredClone(estimate),
      elapsed: replay || !p || p.elapsed >= 5 ? 0 : p.elapsed,
      running: true,
    }));
    if (reduced)
      setPlayback((p) => (p ? { ...p, elapsed: 5, running: false } : p));
  };
  const reset = () => {
    setPlayback(null);
    setEstimate(initialEstimate());
    setError("");
  };
  const change = (p: Pose) => {
    setPlayback(null);
    setEstimate(p);
    setError("");
  };
  const numeric = (axis: number, value: string) => {
    const next = editEstimate(estimate, mode === "rotate", axis, value);
    if (next) change(next);
    else setError("Enter a finite number. Estimate unchanged.");
  };
  const values =
    mode === "rotate"
      ? eulerDegrees(estimate)
      : estimate.p.map((v) => v * 1000);
  const exportState = () => {
    const state = {
      ...exportSynthetic(displayed),
      originalEstimate: estimate,
      preview: playback ? { elapsedSeconds: playback.elapsed, running } : null,
    };
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(state, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "autoframe-synthetic-pose.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return (
    <main className="pose-workspace">
      <section
        className="pose-stage"
        aria-label="Interactive synthetic pose scene"
      >
        <div className="pose-scene-heading">
          <label>
            Object{" "}
            <select aria-label="Demo object">
              <option>Robot gripper</option>
            </select>
          </label>
          <span>
            Frame: <b>Demo scan frame</b>
          </span>
        </div>
        <PoseScene
          pose={displayed}
          onChange={change}
          mode={mode}
          laser={scanner}
          resetView={view}
          editable={edit && !playback}
          showEstimate={showEstimate}
          showReference={showReference}
        />
        <div className="pose-labels">
          <span>
            <i className="observed-dot" />
            Simulated observed geometry
          </span>
          {showEstimate && (
            <span>
              <i className={d.aligned ? "reference-dot" : "estimate-dot"} />
              {d.aligned ? "Aligned CAD overlay" : "Estimated CAD pose"}
            </span>
          )}
          {showReference && (
            <span>
              <i className="reference-dot" />
              Known reference overlay
            </span>
          )}
        </div>
        <div className="pose-source">
          <small>POSE SOURCE</small>
          <span>Procedural estimate → known synthetic reference</span>
        </div>
        <div className="pose-toolbar">
          <span>
            <MousePointer2 size={15} />
            Orbit · scroll to zoom
          </span>
          <button aria-pressed={scanner} onClick={() => setScanner((v) => !v)}>
            <ScanLine size={16} />
            Illustrative scanner
          </button>
          <button
            aria-pressed={showEstimate}
            onClick={() => setShowEstimate((v) => !v)}
          >
            <Eye size={16} />
            CAD overlay
          </button>
          <button
            aria-pressed={showReference}
            onClick={() => setShowReference((v) => !v)}
          >
            <Eye size={16} />
            Reference
          </button>
          <button onClick={() => setView((v) => v + 1)}>
            <RotateCcw size={16} />
            Reset view
          </button>
        </div>
      </section>
      <aside className="pose-inspector">
        <small className="pose-eyebrow">SYNTHETIC POSE DEMO</small>
        <h1>Pose investigation</h1>
        <div
          className={"pose-status " + (d.aligned ? "aligned" : "")}
          role="status"
        >
          {d.aligned ? <CheckCircle2 size={22} /> : <AlertTriangle size={22} />}
          <strong>
            {d.aligned
              ? "Aligned to synthetic reference"
              : "Wrong pose · reference known"}
          </strong>
        </div>
        <h2>Correction to reference</h2>
        <div className="pose-correction-grid">
          <div className="pose-deltas">
            {d.displacement.map((v, i) => (
              <div key={i}>
                <span>Δ{"XYZ"[i]}</span>
                <strong data-testid={`delta-${i}`}>
                  {(v * 1000).toFixed(2)} <em>mm</em>
                </strong>
              </div>
            ))}
          </div>
          <div className="pose-angle">
            <div>
              <span>Angle</span>
              <strong data-testid="rotation-angle">
                {d.angle.toFixed(2)}°
              </strong>
            </div>
            <div>
              <span>Axis</span>
              <strong data-testid="rotation-axis">
                [{d.axis.map((v) => v.toFixed(2)).join(", ")}]
              </strong>
            </div>
            <small>
              Axis in Demo scan frame
              <br />
              {d.angle < 1e-8
                ? "Zero rotation; axis undefined"
                : "Shortest relative rotation"}
            </small>
          </div>
        </div>
        <p className="pose-reference-note">
          Reference: <b>Known synthetic reference</b>
          <br />Δ values describe origin displacement.
        </p>
        <hr />
        <h2>Inspect overlay</h2>
        <div className="pose-overlay-switch">
          <button
            aria-pressed={showEstimate}
            onClick={() => setShowEstimate((v) => !v)}
          >
            Estimated overlay
          </button>
          <button
            aria-pressed={showReference}
            onClick={() => setShowReference((v) => !v)}
          >
            Reference overlay
          </button>
        </div>
        <p className="pose-warning">
          <AlertTriangle size={17} />
          Low RMSE does not prove a correct pose
        </p>
        <button
          className="pose-primary"
          onClick={() =>
            running
              ? setPlayback((p) => (p ? { ...p, running: false } : p))
              : play()
          }
        >
          {running ? <Pause size={19} /> : <Play size={19} />}
          <span>
            {running
              ? "Pause correction"
              : playback && playback.elapsed < 5
                ? "Resume correction"
                : "Preview correction · 5 sec"}
          </span>
        </button>
        <div className="pose-progress">
          <progress
            aria-label="Correction preview progress"
            max={5}
            value={playback?.elapsed ?? 0}
          />
          <div>
            <span>
              {(playback?.elapsed ?? 0).toFixed(1)} / 5.0 sec ·{" "}
              {running
                ? "Playing"
                : playback?.elapsed === 5
                  ? "Complete"
                  : playback
                    ? "Paused"
                    : "Animation preview"}
            </span>
            <button onClick={() => play(true)}>
              <RotateCcw size={13} />
              Replay
            </button>
          </div>
        </div>
        <p className="pose-playback-note">
          Animation preview · original estimate preserved.
        </p>
        <div className="pose-actions">
          <button onClick={reset}>
            <RotateCcw size={17} />
            Reset estimate
          </button>
          <button onClick={exportState}>
            <Download size={17} />
            Export synthetic state
          </button>
        </div>
        <details
          className="pose-edit"
          onToggle={(event) => {
            if (!event.currentTarget.open) setEdit(false);
          }}
        >
          <summary>Perturb estimated overlay</summary>
          <p>
            Inputs use Demo scan coordinates; orientation is XYZ Euler entry.
            Rotation difference above uses quaternions.
          </p>
          {playback && (
            <button onClick={() => setPlayback(null)} disabled={running}>
              Restore original estimate to edit
            </button>
          )}
          <fieldset disabled={!!playback}>
            <div className="pose-edit-mode">
              <button
                aria-pressed={mode === "translate"}
                onClick={() => setMode("translate")}
              >
                Translation
              </button>
              <button
                aria-pressed={mode === "rotate"}
                onClick={() => setMode("rotate")}
              >
                Rotation
              </button>
              <button aria-pressed={edit} onClick={() => setEdit((v) => !v)}>
                Gizmo
              </button>
            </div>
            <div className="pose-numeric">
              {values.map((v, i) => (
                <label key={`${mode}${i}`}>
                  {mode === "rotate" ? "R" : ""}
                  {"XYZ"[i]} ({mode === "rotate" ? "°" : "mm"})
                  <input
                    type="number"
                    step="any"
                    aria-label={`Estimate ${mode === "rotate" ? "rotation" : "position"} ${"XYZ"[i]}`}
                    value={Number(v.toFixed(3))}
                    onChange={(event) => numeric(i, event.target.value)}
                  />
                </label>
              ))}
            </div>
          </fieldset>
          <p role="alert">{error}</p>
        </details>
        <details className="pose-details">
          <summary>Coordinate convention & limits</summary>
          <p>
            Fixed right-handed Demo scan frame, +Z up; metres internally,
            quaternion xyzw orientations. Robot has a non-identity parent
            transform and local gripper offset. Reference and estimate are
            expressed in the same scan frame.
          </p>
          <p>
            Relative rotation Rreference × Restimateᵀ; full rigid correction
            Treference × Testimate⁻¹, applied on the left. Its translation
            differs from origin displacement.
          </p>
          <p>
            Configurable synthetic demo tolerances: ≤1 mm AND ≤1°. These do not
            establish manufacturing accuracy, collision clearance or benchmark
            correctness. This demo computes no RMSE or registration.
          </p>
          <p>
            Synthetic geometry and known reference. No live scanner acquisition
            or automatic pose recovery. Recorded T-LESS evidence is in the
            separate benchmark workspace.
          </p>
        </details>
      </aside>
    </main>
  );
}
