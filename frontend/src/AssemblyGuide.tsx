import { useEffect, useRef, useState } from "react";
import {
  Crosshair,
  Play,
  RotateCcw,
  ScanLine,
  Move,
  Rotate3D,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";
import AssemblyScene from "./AssemblyScene";
import {
  angles,
  editPose,
  errors,
  initialPose,
  previewPose,
} from "./assemblyPose";
import "./assembly.css";
import "./assembly-polish.css";
function Preview({ close }: { close: () => void }) {
  const [time, setTime] = useState(0),
    [run, setRun] = useState(0);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    dialog.current?.showModal();
    return () => dialog.current?.close();
  }, []);
  useEffect(() => {
    let id = 0,
      last = performance.now(),
      elapsed = 0;
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    setTime(reduced ? 5 : 0);
    if (reduced) return;
    const frame = (now: number) => {
      if (!document.hidden) {
        elapsed = Math.min(5, elapsed + (now - last) / 1000);
        setTime(elapsed);
      }
      last = now;
      if (elapsed < 5) id = requestAnimationFrame(frame);
    };
    id = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(id);
  }, [run]);
  return (
    <dialog className="assembly-preview" ref={dialog} onCancel={close}>
      <header>
        <div>
          <small>ILLUSTRATIVE PREVIEW</small>
          <h2>5-second simulated placement</h2>
        </div>
        <button onClick={close}>Close</button>
      </header>
      <div className="preview-stage">
        <AssemblyScene
          pose={previewPose(time)}
          mode="translate"
          laser={false}
          preview
        />
      </div>
      <progress max={5} value={time} />
      <footer>
        <span>
          {time.toFixed(1)} / 5.0 sec ·{" "}
          {time < 2
            ? "Align orientation"
            : time < 5
              ? "Approach along −X"
              : "Seated at target"}
        </span>
        <button onClick={() => setRun((v) => v + 1)}>Replay</button>
      </footer>
      <p>
        Illustrative motion; physical clearance and collision-free insertion are
        not validated. Reduced motion shows the final pose.
      </p>
    </dialog>
  );
}
export default function AssemblyGuide() {
  const [pose, setPose] = useState(initialPose),
    [mode, setMode] = useState<"translate" | "rotate">("translate"),
    [laser, setLaser] = useState(true),
    [step, setStep] = useState(1),
    [view, setView] = useState(0),
    [preview, setPreview] = useState(false),
    [message, setMessage] = useState("");
  const e = errors(pose),
    rot = mode === "rotate",
    values = rot
      ? angles(pose)
      : pose.p.map((v, i) => (v - [0.445, 0, 0.69][i]) * 1000);
  const edit = (axis: number, value: string) => {
    const next = editPose(pose, rot, axis, value);
    if (next) {
      setPose(next);
      setMessage("");
    } else setMessage("Enter a finite number. Pose unchanged.");
  };
  return (
    <main className="assembly">
      <section className="assembly-stage">
        <div className="assembly-select">
          <label>
            Assembly{" "}
            <select aria-label="Assembly">
              <option>Robot wrist + gripper</option>
            </select>
          </label>
          <span>
            Frame: <b>Mounting frame</b>
          </span>
        </div>
        <AssemblyScene
          pose={pose}
          onChange={setPose}
          mode={mode}
          laser={laser}
          resetView={view}
        />
        <div className="scene-caption">
          <small>PROCEDURAL ASSEMBLY / 01</small>
          <strong>Precision starts at the interface.</strong>
          <span>Orbit to inspect · drag the gizmo to place the gripper</span>
        </div>
        <div className="scene-key">
          <i /> Target outline <span>+X approach · −X insertion</span>
        </div>
        <div className="assembly-toolbar">
          <button onClick={() => setMode("translate")} aria-pressed={!rot}>
            <Move size={17} />
            Move part
          </button>
          <button onClick={() => setMode("rotate")} aria-pressed={rot}>
            <Rotate3D size={17} />
            Rotate part
          </button>
          <button onClick={() => setLaser((v) => !v)} aria-pressed={laser}>
            <ScanLine size={17} />
            <span className="laser-label">Illustrative laser guide</span>
          </button>
          <button onClick={() => setView((v) => v + 1)}>
            <RotateCcw size={17} />
            Reset view
          </button>
        </div>
      </section>
      <aside className="assembly-inspector">
        <div className="inspector-title">
          <small>ASSEMBLY SIMULATION</small>
          <h2>Placement guidance</h2>
        </div>
        <div className={"alignment-status " + (e.ok ? "good" : "")}>
          {e.ok ? <CheckCircle size={22} /> : <AlertTriangle size={22} />}
          <strong>{e.ok ? "Within demo tolerance" : "Needs adjustment"}</strong>
        </div>
        <div className="error-metrics">
          <div>
            <small>POSITION ERROR</small>
            <strong>
              {(e.position * 1000).toFixed(2)} <em>mm</em>
            </strong>
          </div>
          <div>
            <small>ORIENTATION ERROR</small>
            <strong>
              {e.orientation.toFixed(2)}
              <em>°</em>
            </strong>
          </div>
        </div>
        <h3>Correction to target</h3>
        <div className="corrections">
          {e.correction.map((v, i) => (
            <div key={i}>
              <span>Δ{"XYZ"[i]}</span>
              <strong>
                {v >= 0 ? "+" : ""}
                {(v * 1000).toFixed(2)} mm
              </strong>
            </div>
          ))}
        </div>
        <p className="assembly-hint">
          Align orientation, then approach the mount along −X.
        </p>
        <h3>Try placement</h3>
        <p className="pose-frame">
          Current pose · Mounting frame
          <br />
          Target: X/Y/Z 0 mm · Rx/Ry/Rz 0°
        </p>
        <div className="mode-switch">
          <button aria-pressed={!rot} onClick={() => setMode("translate")}>
            Translation
          </button>
          <button aria-pressed={rot} onClick={() => setMode("rotate")}>
            Rotation
          </button>
        </div>
        <div className="pose-inputs">
          {values.map((v, i) => (
            <label key={`${mode}${i}`}>
              <span>
                {rot ? "R" : ""}
                {"XYZ"[i]} <small>{rot ? "°" : "mm"}</small>
              </span>
              <input
                aria-label={`${rot ? "Rotation" : "Position"} ${"XYZ"[i]}`}
                type="number"
                step="any"
                value={Number(v.toFixed(3))}
                onChange={(event) => edit(i, event.target.value)}
              />
              <div>
                <button
                  aria-label={`Decrease ${"XYZ"[i]}`}
                  onClick={() => edit(i, String(v - step))}
                >
                  −
                </button>
                <button
                  aria-label={`Increase ${"XYZ"[i]}`}
                  onClick={() => edit(i, String(v + step))}
                >
                  +
                </button>
              </div>
            </label>
          ))}
        </div>
        <label className="step-select">
          Nudge step{" "}
          <select
            value={step}
            onChange={(event) => setStep(Number(event.target.value))}
          >
            {[0.1, 1, 5, 10].map((n) => (
              <option key={n} value={n}>
                {n} {rot ? "°" : "mm"}
              </option>
            ))}
          </select>
        </label>
        <button
          className="alignment-button"
          onClick={() =>
            setMessage(
              e.ok
                ? "Both checks pass at full precision."
                : "Outside demo tolerance. Continue adjusting the gripper.",
            )
          }
        >
          <Crosshair size={18} />
          Check alignment
        </button>
        <div className="check-results">
          <span>
            Position ≤ 1.0 mm <b>{e.position <= 0.001 ? "PASS" : "OUTSIDE"}</b>
          </span>
          <span>
            Orientation ≤ 1.0° <b>{e.orientation <= 1 ? "PASS" : "OUTSIDE"}</b>
          </span>
        </div>
        <p className="feedback" role="status">
          {message}
        </p>
        <button className="demo-button" onClick={() => setPreview(true)}>
          <Play size={18} />
          Watch placement demo · 5 sec
        </button>
        <button
          className="reset-button"
          onClick={() => {
            setPose(initialPose());
            setMessage("Attempt reset.");
          }}
        >
          <RotateCcw size={17} />
          Reset attempt
        </button>
        <details>
          <summary>Pose & simulation details</summary>
          <p>
            Fixed mounting frame: +X outward, +Z up. Values are relative to
            target part origin; target position 0, 0, 0 mm. Current XYZ Euler
            orientation:{" "}
            {angles(pose)
              .map((v) => v.toFixed(2))
              .join(", ")}
            °. Target: 0, 0, 0°. Euler order XYZ in the fixed frame. Rotation
            error uses the shortest quaternion angle.
          </p>
          <p>
            Metres internally. Robot mating frame (390, 0, 690) mm; local
            gripper mating offset (−55, 0, 0) mm. Target part origin (445, 0,
            690) mm. Demo settings: ≤1 mm AND ≤1°. Illustrative laser guide,
            independent of pose calculations.
          </p>
        </details>
        <p className="simulation-note">
          Pose alignment does not establish physical clearance, collision-free
          insertion, or safe hardware operation.
        </p>
      </aside>
      {preview && <Preview close={() => setPreview(false)} />}
    </main>
  );
}
