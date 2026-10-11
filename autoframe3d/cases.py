"""Self-contained case bundles and recomputing replay verification."""

from __future__ import annotations

import json
import platform
import sys
import zipfile
from pathlib import Path

import numpy as np

from autoframe3d.experiment import ExperimentConfig, evaluate, generate_scan
from autoframe3d.geometry import TriangleMesh, make_object_mesh

REPLAY_TOLERANCES = {
    "fitness_abs": 0.03,
    "inlier_rmse_m_abs": 0.01,
    "translation_error_m_abs": 0.02,
    "rotation_error_deg_abs": 2.0,
}


def _write_obj(mesh: TriangleMesh, path: Path) -> None:
    with path.open("w", encoding="ascii") as file:
        for vertex in mesh.vertices:
            file.write("v %.8f %.8f %.8f\n" % tuple(vertex))
        for face in mesh.faces + 1:
            file.write("f %d %d %d\n" % tuple(face))


def _json_value(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def export_case(
    case_id: str,
    config: dict[str, object],
    measured: dict[str, object],
    output_path: Path,
) -> Path:
    """Regenerate scan geometry and bundle it with the actually measured result."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(".work")
    temporary.mkdir(parents=True, exist_ok=True)
    typed_config = ExperimentConfig(**config)
    mesh = make_object_mesh(typed_config.object_kind)
    scan, truth = generate_scan(typed_config, mesh)
    _write_obj(mesh, temporary / "cad_mesh.obj")
    np.savetxt(temporary / "scan.xyz", scan, fmt="%.8f")
    case_data = {
        "case_id": case_id,
        "config": config,
        "thresholds": measured.get("thresholds", {}),
        "ground_truth_T_object_from_scan": measured.get(
            "ground_truth_T_object_from_scan", truth
        ),
        "estimated_T_object_from_scan": measured.get(
            "estimated_T_object_from_scan", np.eye(4)
        ),
        "alignment_quality_metrics": measured.get("alignment_quality_metrics", {}),
        "pose_errors": measured.get("pose_errors", {}),
        "classification": measured.get("classification", "unknown"),
    }
    (temporary / "case.json").write_text(json.dumps(_json_value(case_data), indent=2), encoding="utf-8")
    environment = {"python": sys.version, "platform": platform.platform()}
    (temporary / "environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
    (temporary / "REPRODUCE.md").write_text(
        "# Reproduce this AutoFrame 3D case\n\n"
        "Install the project dependencies, then run `autoframe3d replay case_bundle.zip`. "
        "Replay regenerates the seeded scan and reruns registration. It compares the new "
        "classification and measurements with the recorded values using the tolerances "
        "documented in the replay output. The saved values are not used as replay results.\n",
        encoding="utf-8",
    )
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ("cad_mesh.obj", "scan.xyz", "case.json", "environment.json", "REPRODUCE.md"):
            archive.write(temporary / name, arcname=name)
    for path in temporary.iterdir():
        path.unlink()
    temporary.rmdir()
    return output_path


def replay_bundle(path: Path) -> dict[str, object]:
    """Rerun registration and verify the recomputed result against bundle tolerances."""
    with zipfile.ZipFile(path, "r") as archive:
        case_data = json.loads(archive.read("case.json").decode("utf-8"))
    config = ExperimentConfig(**case_data["config"])
    actual = evaluate(config)
    actual_summary = {
        "classification": actual["classification"],
        "alignment_quality_metrics": actual["alignment_quality_metrics"],
        "pose_errors": actual["pose_errors"],
    }
    expected_metrics = case_data["alignment_quality_metrics"]
    actual_metrics = actual_summary["alignment_quality_metrics"]
    expected_pose = case_data["pose_errors"]
    actual_pose = actual_summary["pose_errors"]
    differences = {
        "fitness_abs": abs(actual_metrics["fitness"] - expected_metrics["fitness"]),
        "inlier_rmse_m_abs": abs(actual_metrics["inlier_rmse_m"] - expected_metrics["inlier_rmse_m"]),
        "translation_error_m_abs": abs(
            actual_pose["translation_error_m"] - expected_pose["translation_error_m"]
        ),
        "rotation_error_deg_abs": abs(
            actual_pose["rotation_error_deg"] - expected_pose["rotation_error_deg"]
        ),
    }
    passed = actual_summary["classification"] == case_data["classification"] and all(
        differences[key] <= tolerance for key, tolerance in REPLAY_TOLERANCES.items()
    )
    return {
        "passed": passed,
        "case_id": case_data.get("case_id"),
        "expected_classification": case_data["classification"],
        "actual": actual_summary,
        "absolute_differences": differences,
        "tolerances": REPLAY_TOLERANCES,
    }