"""Dataset-attributed T-LESS case loading, recomputing replay, and ZIP export."""

from __future__ import annotations

import json
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from autoframe3d.tless_adapter import ROOT, load_registration_inputs, load_model
from autoframe3d.tless_benchmark import _perturb_scan, evaluate_case

REPLAY_TOLERANCES = {
    "fitness_abs": 0.03,
    "inlier_rmse_m_abs": 0.005,
    "mssd_over_diameter_abs": 0.03,
}


def load_result_record(case_id: str, group: str, manifest: str) -> dict[str, Any]:
    if group not in {"original", "perturbed"}:
        raise ValueError("group must be original or perturbed")
    path = ROOT / "data" / "tless" / "results" / group / f"{manifest}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"No {group} results for manifest {manifest}")
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record.get("case_id") == case_id:
            return record
    raise KeyError(case_id)


def list_result_records(group: str = "original", manifest: str = "smoke20_frozen") -> list[dict[str, Any]]:
    path = ROOT / "data" / "tless" / "results" / group / f"{manifest}.jsonl"
    if not path.exists():
        return []
    records: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        records[record["case_id"]] = record
    return [records[key] for key in sorted(records)]


def geometry_payload(record: dict[str, Any]) -> dict[str, Any]:
    inputs = load_registration_inputs(record)
    if record.get("group") == "perturbed" and record.get("perturbation"):
        inputs = replace(inputs, scan_points_camera_m=_perturb_scan(inputs, record["perturbation"]))
    model = load_model(inputs.object_id, "cad")
    estimate = np.asarray(record["camera_from_object_estimate"], dtype=np.float64)
    truth = np.asarray(record["camera_from_object_ground_truth"], dtype=np.float64)
    return {
        "config": {
            "object_kind": "T-LESS object",
            "object_id": inputs.object_id,
            "scene_id": inputs.scene_id,
            "image_id": inputs.image_id,
            "gt_index": inputs.gt_index,
            "units": "metres",
        },
        "mesh": {"vertices": model.vertices_m.tolist(), "faces": model.faces.tolist()},
        "scan": inputs.scan_points_camera_m.tolist(),
        "ground_truth_T_object_from_scan": np.linalg.inv(truth).tolist(),
        "estimated_T_object_from_scan": np.linalg.inv(estimate).tolist(),
    }


def replay_record(record: dict[str, Any]) -> dict[str, Any]:
    """Reload the dataset case and recompute registration and MSSD."""
    case = {key: record[key] for key in ("case_id", "scene_id", "image_id", "gt_index", "object_id")}
    actual = evaluate_case(case, group=record["group"], timeout_seconds=30.0)
    if actual["status"] != "valid" or record["status"] != "valid":
        return {"passed": False, "expected_status": record["status"], "actual": actual, "tolerances": REPLAY_TOLERANCES}
    actual_metrics = actual["alignment_quality_metrics"]
    expected_metrics = record["alignment_quality_metrics"]
    differences = {
        "fitness_abs": abs(actual_metrics["fitness"] - expected_metrics["fitness"]),
        "inlier_rmse_m_abs": abs(actual_metrics["inlier_rmse_m"] - expected_metrics["inlier_rmse_m"]),
        "mssd_over_diameter_abs": abs(
            actual["pose_metrics"]["mssd_over_diameter"] - record["pose_metrics"]["mssd_over_diameter"]
        ),
    }
    passed = actual["category"] == record["category"] and all(
        differences[key] <= tolerance for key, tolerance in REPLAY_TOLERANCES.items()
    )
    return {
        "passed": passed,
        "case_id": record["case_id"],
        "expected_category": record["category"],
        "actual_category": actual["category"],
        "absolute_differences": differences,
        "tolerances": REPLAY_TOLERANCES,
        "actual": actual,
    }


def export_case_bundle(record: dict[str, Any], output_path: Path) -> Path:
    """Bundle geometry, metrics, transforms, and CC-BY-4.0 dataset attribution."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    inputs = load_registration_inputs(record)
    provenance = json.loads((ROOT / "data" / "tless" / "provenance.json").read_text(encoding="utf-8"))
    provenance = {
        key: value for key, value in provenance.items()
        if key in {"repository", "revision", "license", "source_url", "archives"}
    }
    temporary = output_path.with_suffix(".work")
    temporary.mkdir(parents=True, exist_ok=True)
    (temporary / "case.json").write_text(json.dumps({
        "dataset_attribution": provenance,
        "evaluation_note": "Custom internal evaluation on the public BOP test subset; registration evaluation with ground-truth instance masks; not an official BOP score.",
        "case_result": record,
    }, indent=2), encoding="utf-8")
    np.savetxt(temporary / "scan_camera.xyz", inputs.scan_points_camera_m, fmt="%.8f")
    np.savetxt(temporary / "model_object.xyz", inputs.model_vertices_object_m, fmt="%.8f")
    model_path = ROOT / "data" / "tless" / "bop" / "models_cad" / f"obj_{inputs.object_id:06d}.ply"
    (temporary / "model_cad.ply").write_bytes(model_path.read_bytes())
    (temporary / "REPRODUCE.md").write_text(
        "# Reproduce this T-LESS case\n\n"
        f"This is {record['case_id']} from {provenance['repository']} at revision {provenance['revision']} "
        f"({provenance['license']}). Restore the three bounded dataset archives using `python scripts/tless_data.py download` "
        "and `python scripts/tless_data.py extract`, then rerun the recorded manifest/group with `python scripts/tless_benchmark.py evaluate <manifest> --group <group>`. "
        "Replay recomputes registration and symmetry-aware MSSD from the source depth/mask files; saved metric values are not used as replay outputs.\n",
        encoding="utf-8",
    )
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ("case.json", "scan_camera.xyz", "model_object.xyz", "model_cad.ply", "REPRODUCE.md"):
            archive.write(temporary / name, arcname=name)
    for item in temporary.iterdir():
        item.unlink()
    temporary.rmdir()
    return output_path