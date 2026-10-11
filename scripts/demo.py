"""Short measured control/failure/simplify/export/replay demonstration."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autoframe3d.cases import export_case, replay_bundle
from autoframe3d.experiment import ExperimentConfig, evaluate
from autoframe3d.simplify import simplify_failure


def main() -> None:
    artifact_dir = ROOT / "artifacts" / "demo"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    control = evaluate(ExperimentConfig(visibility="all", yaw_deg=0.0))
    failure = evaluate(ExperimentConfig())
    simplified = simplify_failure(failure, budget=8)
    bundle = export_case(
        "demo-failure",
        simplified["config"],
        simplified["result"],
        artifact_dir / "demo-failure.zip",
    )
    replay = replay_bundle(bundle)
    summary = {
        "control": {
            "classification": control["classification"],
            "alignment_quality_metrics": control["alignment_quality_metrics"],
            "pose_errors": control["pose_errors"],
        },
        "failure": {
            "classification": failure["classification"],
            "alignment_quality_metrics": failure["alignment_quality_metrics"],
            "pose_errors": failure["pose_errors"],
        },
        "simplification_evaluations": simplified["evaluations"],
        "simplifications_kept": simplified["simplifications_kept"],
        "simplification_claim": simplified["claim"],
        "replay": replay,
        "bundle": str(bundle),
    }
    print(json.dumps(summary, indent=2))
    if control["classification"] != "accepted_correct" or not replay["passed"]:
        raise SystemExit("Demonstration acceptance check failed")


if __name__ == "__main__":
    main()