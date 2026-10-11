"""Fixed-manifest custom internal evaluation for T-LESS BOP19 PrimeSense data."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np

from autoframe3d.tless_adapter import (
    BOP_ROOT,
    ROOT,
    RegistrationInputs,
    load_ground_truth,
    load_registration_inputs,
    register_masked_scan,
    write_ground_truth_diagnostic,
)
from autoframe3d.provenance import build_provenance_manifest
from autoframe3d.tless_metrics import bop_symmetry_transforms, classify_result, mssd_normalized

CONFIG_PATH = ROOT / "configs" / "tless_frozen.json"
MANIFEST_ROOT = ROOT / "data" / "tless" / "manifests"
RESULT_ROOT = ROOT / "data" / "tless" / "results"


def load_frozen_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _interleave(cases: list[dict[str, int]]) -> list[dict[str, int]]:
    buckets: dict[tuple[int, int], list[dict[str, int]]] = {}
    for case in cases:
        buckets.setdefault((case["object_id"], case["scene_id"]), []).append(case)
    for values in buckets.values():
        values.sort(key=lambda item: (item["image_id"], item["gt_index"]))
    ordered: list[dict[str, int]] = []
    keys = sorted(buckets)
    while keys:
        remaining: list[tuple[int, int]] = []
        for key in keys:
            ordered.append(buckets[key].pop(0))
            if buckets[key]:
                remaining.append(key)
        keys = remaining
    return ordered


def eligible_target_cases() -> list[dict[str, int]]:
    """Select IDs from BOP19 targets/visibility metadata; ignore all pose values."""
    targets = json.loads((BOP_ROOT / "tless" / "test_targets_bop19.json").read_text(encoding="utf-8"))
    scene_ids = sorted({int(target["scene_id"]) for target in targets})
    scene_gt: dict[int, dict[str, list[dict[str, Any]]]] = {}
    scene_info: dict[int, dict[str, list[dict[str, Any]]]] = {}
    for scene_id in scene_ids:
        scene_root = BOP_ROOT / "test_primesense" / f"{scene_id:06d}"
        scene_gt[scene_id] = json.loads((scene_root / "scene_gt.json").read_text(encoding="utf-8"))
        scene_info[scene_id] = json.loads((scene_root / "scene_gt_info.json").read_text(encoding="utf-8"))
    cases: list[dict[str, int]] = []
    target_keys = {(int(item["scene_id"]), int(item["im_id"]), int(item["obj_id"])) for item in targets}
    minimum_visible = float(load_frozen_config()["minimum_visible_fraction_for_manifest"])
    for scene_id, image_id, object_id in sorted(target_keys):
        annotations = scene_gt[scene_id][str(image_id)]
        pose_info = scene_info[scene_id][str(image_id)]
        for gt_index, (annotation, info) in enumerate(zip(annotations, pose_info)):
            if (
                int(annotation["obj_id"]) == object_id
                and int(info.get("px_count_visib", 0)) > 0
                and float(info.get("visib_fract", 0.0)) >= minimum_visible
            ):
                case_id = f"tless-s{scene_id:06d}-i{image_id:06d}-g{gt_index:02d}-o{object_id:02d}"
                cases.append({
                    "case_id": case_id, "scene_id": scene_id, "image_id": image_id,
                    "gt_index": gt_index, "object_id": object_id,
                })
    return _interleave(cases)


def generate_manifests() -> dict[str, int]:
    cases = eligible_target_cases()
    development = [case for case in cases if case["scene_id"] in {1, 2, 3, 4}]
    heldout = [case for case in cases if case["scene_id"] not in {1, 2, 3, 4}]
    if len(development) < 20 or len(heldout) < 200:
        raise ValueError("Downloaded BOP19 targets do not contain enough eligible instances")
    MANIFEST_ROOT.mkdir(parents=True, exist_ok=True)
    reports = {
        "development.json": development,
        "smoke20.json": development[:20],
        "smoke20_frozen.json": development[:20],
        "development_tuning20.json": development[20:40],
        "heldout200.json": heldout[:200],
        "all_eligible.json": cases,
    }
    for name, items in reports.items():
        payload = {
            "protocol": "custom_internal_tless_test_primesense_bop19",
            "selection": "BOP19 target IDs plus visible-instance metadata; no registration outcomes or GT pose values used",
            "scene_partition": {"development_scene_ids": [1, 2, 3, 4], "heldout_scene_ids": list(range(5, 21))},
            "cases": items,
        }
        (MANIFEST_ROOT / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {name: len(items) for name, items in reports.items()}


def _perturb_scan(inputs: RegistrationInputs, perturbation: dict[str, Any]) -> np.ndarray:
    points = inputs.scan_points_camera_m.copy()
    rng = np.random.default_rng(int(perturbation["seed"]))
    noise_std = float(perturbation.get("noise_std_m", 0.0))
    if noise_std:
        points += rng.normal(0.0, noise_std, points.shape)
    dropout = float(perturbation.get("point_dropout_fraction", 0.0))
    if dropout:
        points = points[rng.random(len(points)) >= dropout]
    return points


def _inputs_with_scan(inputs: RegistrationInputs, points: np.ndarray) -> RegistrationInputs:
    from dataclasses import replace

    return replace(inputs, scan_points_camera_m=points)


def evaluate_case(
    case: dict[str, int], *, group: str = "original", timeout_seconds: float = 30.0,
    perturbation_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Register without truth, then reveal annotation to the evaluator for MSSD."""
    started = time.perf_counter()
    deadline = time.monotonic() + timeout_seconds
    try:
        config = load_frozen_config()
        inputs = load_registration_inputs(case)
        perturbation = None
        if group == "perturbed":
            perturb_config = {**config["perturbed_group"], **(perturbation_override or {})}
            perturbation = {
                **perturb_config,
                "seed": int(perturb_config.get(
                    "seed",
                    case["scene_id"] * 100_000 + case["image_id"] * 100 + case["gt_index"] + perturb_config["seed_offset"],
                )),
            }
            inputs = _inputs_with_scan(inputs, _perturb_scan(inputs, perturbation))
        registration = register_masked_scan(
            inputs,
            correspondence_distance_m=config["geometric_acceptance"]["maximum_correspondence_distance_m"],
            max_iterations=config["registration"]["max_iterations_per_start"],
            registration_evaluations=config["registration"]["max_registration_evaluations"],
            registration_points_max=config["registration"]["model_registration_points_max"],
            deadline=deadline,
        )
        if time.monotonic() > deadline:
            raise TimeoutError("Per-instance evaluation deadline exceeded")
        ground_truth = load_ground_truth(case)
        if ground_truth.object_id != inputs.object_id:
            raise ValueError("Manifest object ID does not match evaluator annotation")
        symmetries = bop_symmetry_transforms(
            inputs.model_info,
            max_symmetry_step=config["pose_correctness"]["continuous_symmetry_max_vertex_travel_over_diameter"],
        )
        metric = mssd_normalized(
            registration["camera_from_object"], ground_truth.camera_from_object,
            inputs.evaluation_points_object_m, symmetries,
            float(inputs.model_info["diameter"]) * 0.001,
        )
        thresholds = config["geometric_acceptance"]
        accepted, correct, category = classify_result(
            registration["fitness"], registration["inlier_rmse_m"], metric["mssd_over_diameter"],
            minimum_fitness=thresholds["minimum_fitness"],
            maximum_rmse_m=thresholds["maximum_inlier_rmse_m"],
            maximum_mssd_over_diameter=config["pose_correctness"]["maximum_normalized_mssd"],
        )
        return {
            **case, "group": group, "status": "valid", "accepted": accepted,
            "correct": correct, "category": category,
            "alignment_quality_metrics": {
                "fitness": registration["fitness"],
                "inlier_rmse_m": registration["inlier_rmse_m"],
                "inlier_count": registration["inlier_count"],
                "scan_point_count": registration["scan_point_count"],
                "max_correspondence_distance_m": registration["max_correspondence_distance_m"],
            },
            "pose_metrics": metric,
            "diameter_m": float(inputs.model_info["diameter"]) * 0.001,
            "camera_from_object_estimate": registration["camera_from_object"].tolist(),
            "camera_from_object_ground_truth": ground_truth.camera_from_object.tolist(),
            "registration_initialization": registration["initialization"],
            "registration_evaluations": registration["registration_evaluations"],
            "selected_initialization_index": registration["selected_initialization_index"],
            "perturbation": perturbation,
            "runtime_seconds": time.perf_counter() - started,
            "evaluation_note": "Registration evaluation with ground-truth instance masks; not end-to-end detection.",
        }
    except TimeoutError as error:
        return {**case, "group": group, "status": "timeout", "error": str(error), "runtime_seconds": time.perf_counter() - started}
    except Exception as error:
        return {
            **case, "group": group, "status": "processing_failure",
            "error": f"{type(error).__name__}: {error}", "runtime_seconds": time.perf_counter() - started,
        }


def verify_or_read_checkpoint(checkpoint_path: Path, current_manifest_path: Path) -> dict[str, dict[str, Any]]:
    """Read checkpoint lines; reject legacy outputs or mismatched provenance without modifying them."""
    done: dict[str, dict[str, Any]] = {}
    if not checkpoint_path.exists():
        return done
    current_prov = build_provenance_manifest(current_manifest_path)
    current_hash = current_prov["combined_sha256"]
    with checkpoint_path.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                record = json.loads(line)
                record_prov = record.get("provenance")
                if not record_prov or record_prov.get("combined_sha256") != current_hash:
                    raise ValueError(
                        f"Checkpoint provenance mismatch or missing provenance for case {record.get('case_id')}. "
                        "Legacy outputs without provenance or mismatched runs cannot be silently appended."
                    )
                if (record_prov.get("package_versions") != current_prov.get("package_versions")
                        or record_prov.get("python") != current_prov.get("python")):
                    raise ValueError("Checkpoint provenance environment mismatch; use a separate result directory.")
                done[record["case_id"]] = record
            except (json.JSONDecodeError, KeyError) as error:
                if "Checkpoint provenance" in str(error):
                    raise
                continue
    return done


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row["status"] == "valid"]
    accepted = [row for row in valid if row["accepted"]]
    category_names = (
        "accepted_and_correct", "accepted_but_wrong", "rejected_and_correct", "rejected_and_wrong",
    )
    categories = {name: sum(row["category"] == name for row in valid) for name in category_names}
    wrong = categories["accepted_but_wrong"]
    by_object: dict[str, Any] = {}
    for object_id in sorted({row["object_id"] for row in valid}):
        object_rows = [row for row in valid if row["object_id"] == object_id]
        object_wrong = sum(row["category"] == "accepted_but_wrong" for row in object_rows)
        object_accepted = sum(row["accepted"] for row in object_rows)
        by_object[str(object_id)] = {
            "valid_cases": len(object_rows), "accepted_but_wrong": object_wrong,
            "accepted_but_wrong_over_valid": object_wrong / len(object_rows) if object_rows else None,
            "accepted_but_wrong_over_accepted": object_wrong / object_accepted if object_accepted else None,
            "median_normalized_mssd": float(np.median([row["pose_metrics"]["mssd_over_diameter"] for row in object_rows])),
            "median_runtime_seconds": float(np.median([row["runtime_seconds"] for row in object_rows])),
        }
    return {
        "evaluated_cases": len(rows), "valid_cases": len(valid),
        "timeouts": sum(row["status"] == "timeout" for row in rows),
        "processing_failures": sum(row["status"] == "processing_failure" for row in rows),
        "categories": categories,
        "accepted_but_wrong_over_valid": wrong / len(valid) if valid else None,
        "accepted_but_wrong_over_accepted": wrong / len(accepted) if accepted else None,
        "median_runtime_seconds": float(np.median([row["runtime_seconds"] for row in rows])) if rows else None,
        "mean_runtime_seconds": float(np.mean([row["runtime_seconds"] for row in rows])) if rows else None,
        "by_object": by_object,
    }


def run_manifest(
    manifest_name: str, *, group: str = "original", limit: int | None = None,
    workers: int = 1, resume: bool = True,
) -> dict[str, Any]:
    if group not in {"original", "perturbed"}:
        raise ValueError("group must be original or perturbed")
    if not 1 <= workers <= 4:
        raise ValueError("workers must be between 1 and 4")
    manifest = json.loads((MANIFEST_ROOT / f"{manifest_name}.json").read_text(encoding="utf-8"))
    cases = manifest["cases"][:limit]
    output_dir = RESULT_ROOT / group
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / f"{manifest_name}.jsonl"
    manifest_path = MANIFEST_ROOT / f"{manifest_name}.json"
    if not resume and checkpoint_path.exists():
        raise ValueError("Refusing to append a fresh run to an existing checkpoint; use a separate result directory.")
    completed = verify_or_read_checkpoint(checkpoint_path, manifest_path) if resume else {}
    run_provenance = build_provenance_manifest(manifest_path)
    pending = [case for case in cases if case["case_id"] not in completed]
    frozen = load_frozen_config()
    provenance = json.loads((ROOT / "data" / "tless" / "provenance.json").read_text(encoding="utf-8"))
    provenance["archives"] = [
        {key: value for key, value in archive.items() if key != "entries"}
        for archive in provenance.get("archives", [])
    ]
    started = time.perf_counter()
    with checkpoint_path.open("a", encoding="utf-8") as checkpoint:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(evaluate_case, case, group=group, timeout_seconds=frozen["execution"]["timeout_seconds"]): case
                for case in pending
            }
            for future in as_completed(futures):
                result = future.result()
                result["provenance"] = run_provenance
                checkpoint.write(json.dumps(result, separators=(",", ":")) + "\n")
                checkpoint.flush()
                completed[result["case_id"]] = result
                print(json.dumps({
                    "completed": len(completed), "requested": len(cases),
                    "case_id": result["case_id"], "status": result["status"],
                    "category": result.get("category"), "runtime_seconds": result["runtime_seconds"],
                }), flush=True)
    rows = [completed[case["case_id"]] for case in cases if case["case_id"] in completed]
    csv_path = output_dir / f"{manifest_name}.csv"
    fields = ["case_id", "scene_id", "image_id", "gt_index", "object_id", "group", "status", "category", "accepted", "correct", "fitness", "inlier_rmse_m", "mssd_m", "mssd_over_diameter", "runtime_seconds", "error"]
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            metrics, pose = row.get("alignment_quality_metrics", {}), row.get("pose_metrics", {})
            writer.writerow({
                **{key: row.get(key) for key in fields if key in row},
                "fitness": metrics.get("fitness"), "inlier_rmse_m": metrics.get("inlier_rmse_m"),
                "mssd_m": pose.get("mssd_m"), "mssd_over_diameter": pose.get("mssd_over_diameter"),
            })
    summary = {
        "manifest": manifest_name, "group": group,
        "custom_internal_evaluation": True, "official_bop_score": False,
        "attribution": provenance,
        "provenance": run_provenance,
        "frozen_config": frozen, "summary": _summary(rows),
        "frozen_config_sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        "environment": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__},
        "wall_runtime_seconds_this_invocation": time.perf_counter() - started,
        "case_results_jsonl": str(checkpoint_path.relative_to(ROOT)),
        "case_results_csv": str(csv_path.relative_to(ROOT)),
        "resume_command": f"python scripts/tless_benchmark.py evaluate {manifest_name} --group {group} --workers {workers}",
    }
    (output_dir / f"{manifest_name}.summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def write_diagnostic(manifest_name: str = "smoke20") -> Path:
    manifest = json.loads((MANIFEST_ROOT / f"{manifest_name}.json").read_text(encoding="utf-8"))
    case = manifest["cases"][0]
    inputs = load_registration_inputs(case)
    truth = load_ground_truth(case)
    return write_ground_truth_diagnostic(
        inputs, truth, ROOT / "data" / "tless" / "diagnostics" / f"{case['case_id']}_gt_overlay.png",
    )