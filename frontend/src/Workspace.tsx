import { useState } from "react";
import PoseInspection from "./PoseInspection";
import RecordedDemo from "./RecordedDemo";
export default function Workspace() {
  const [tab, setTab] = useState("pose");
  return (
    <>
      <header className="workspace-header">
        <a href="/">
          AutoFrame <b>3D</b>
        </a>
        <nav aria-label="Workspace">
          <button aria-pressed={tab === "pose"} onClick={() => setTab("pose")}>
            Pose Inspection
          </button>
          <button
            aria-pressed={tab === "benchmark"}
            onClick={() => setTab("benchmark")}
          >
            Recorded Benchmark
          </button>
        </nav>
        <span>
          {tab === "pose" ? "Synthetic pose demo" : "Recorded benchmark"}
        </span>
      </header>
      {tab === "pose" ? <PoseInspection /> : <RecordedDemo />}
    </>
  );
}
