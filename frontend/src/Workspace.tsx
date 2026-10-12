import { useState } from "react";
import AssemblyGuide from "./AssemblyGuide";
import RecordedDemo from "./RecordedDemo";
export default function Workspace() {
  const [tab, setTab] = useState("assembly");
  return (
    <>
      <header className="workspace-header">
        <a href="/">
          AutoFrame <b>3D</b>
        </a>
        <nav aria-label="Workspace">
          <button
            aria-pressed={tab === "assembly"}
            onClick={() => setTab("assembly")}
          >
            Assembly Guide
          </button>
          <button
            aria-pressed={tab === "benchmark"}
            onClick={() => setTab("benchmark")}
          >
            Recorded Benchmark
          </button>
        </nav>
        <span>Assembly simulation</span>
      </header>
      {tab === "assembly" ? <AssemblyGuide /> : <RecordedDemo />}
    </>
  );
}
