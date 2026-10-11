"""Independent saved-pose scoring audit. Never loads scans or runs registration."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT))
from autoframe3d.tless_metrics import bop_symmetry_transforms, mssd_normalized

INPUTS: dict[str, dict] = {}


def input_bytes(path):
    path = Path(path)
    data = path.read_bytes()
    INPUTS[path.relative_to(ROOT).as_posix()] = {
        "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)
    }
    return data


def read_json(path):
    return json.loads(input_bytes(path))


def finite(value, shape=None):
    value = np.asarray(value, dtype=np.float64)
    if not np.isfinite(value).all() or (shape is not None and value.shape != shape):
        raise ValueError(f"Invalid/nonfinite array: expected {shape}, got {value.shape}")
    return value


def pose(value):
    value = finite(value, (4, 4))
    np.testing.assert_allclose(value[3], [0, 0, 0, 1], atol=1e-10, rtol=0)
    # Rounded local GT matrices have measured residuals up to 1.38e-6.
    # This input-validation tolerance does not change poses or scoring thresholds.
    np.testing.assert_allclose(value[:3, :3].T @ value[:3, :3], np.eye(3), atol=1e-5, rtol=0)
    assert abs(np.linalg.det(value[:3, :3]) - 1) < 1e-5
    return value


def rotation(axis, angle):
    """Rodrigues formula, independent of production SciPy Rotation."""
    axis = finite(axis, (3,))
    norm = np.linalg.norm(axis)
    if norm == 0:
        raise ValueError("Zero symmetry axis")
    x, y, z = axis / norm
    cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + math.sin(angle) * cross + (1 - math.cos(angle)) * (cross @ cross)


def transform(r=None, t=None):
    result = np.eye(4)
    if r is not None:
        result[:3, :3] = r
    if t is not None:
        result[:3, 3] = t
    return result


def reference_symmetries(info, step, metre_consistent=True):
    if not math.isfinite(step) or step <= 0:
        raise ValueError("Invalid symmetry discretization step")
    scale = .001 if metre_consistent else 1.
    discrete = [np.eye(4)]
    for raw in info.get("symmetries_discrete", []):
        item = pose(np.asarray(raw).reshape(4, 4)).copy()
        item[:3, 3] *= scale
        discrete.append(item)
    continuous = []
    # Preserve the original rule exactly: ceil(pi / step) samples per axis,
    # then continuous @ discrete. Multiple continuous declarations form a union.
    count = math.ceil(math.pi / step)
    for raw in info.get("symmetries_continuous", []):
        offset = finite(raw["offset"], (3,)) * scale
        for index in range(count):
            r = rotation(raw["axis"], index * 2 * math.pi / count)
            continuous.append(transform(r, offset - r @ offset))
    return [c @ d for d in discrete for c in continuous] if continuous else discrete


def reference_mssd(estimate, truth, vertices_m, symmetries, diameter_m):
    """Object symmetry first, then GT camera transform; corresponding vertices."""
    if not math.isfinite(diameter_m) or diameter_m <= 0:
        raise ValueError("Invalid diameter")
    points = finite(vertices_m)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) == 0:
        raise ValueError("Missing/invalid evaluation vertices")
    homogeneous = np.column_stack((points, np.ones(len(points))))
    estimated_camera = (estimate @ homogeneous.T)[:3].T
    best = math.inf
    for symmetry in symmetries:
        gt_camera = (truth @ symmetry @ homogeneous.T)[:3].T
        best = min(best, float(np.sqrt(np.sum((estimated_camera - gt_camera) ** 2, axis=1)).max()))
    return best / diameter_m


def ply_vertices(path):
    """Independent reader of all local PLY vertex coordinates, in metres."""
    data = input_bytes(path)
    end = data.index(b"\n", data.index(b"end_header")) + 1
    header = data[:end].decode("ascii").splitlines()
    fmt = next(line.split()[1] for line in header if line.startswith("format "))
    count = 0
    section = None
    properties = []
    types = {"float": "f4", "float32": "f4", "double": "f8", "float64": "f8",
             "char": "i1", "uchar": "u1", "short": "i2", "ushort": "u2", "int": "i4", "uint": "u4"}
    for line in header:
        parts = line.split()
        if parts[:1] == ["element"]:
            section = parts[1]
            if section == "vertex":
                count = int(parts[2])
        elif parts[:1] == ["property"] and section == "vertex":
            if len(parts) != 3:
                raise ValueError("Unsupported list vertex property")
            properties.append((parts[2], parts[1]))
    names = [name for name, _ in properties]
    if fmt == "binary_little_endian":
        dtype = np.dtype([(name, "<" + types[kind]) for name, kind in properties])
        values = np.frombuffer(data, dtype=dtype, count=count, offset=end)
        points = np.column_stack([values[name] for name in ("x", "y", "z")]).astype(np.float64)
    elif fmt == "ascii":
        lines = data[end:].decode("ascii").splitlines()[:count]
        points = np.array([[float(line.split()[names.index(name)]) for name in ("x", "y", "z")] for line in lines])
    else:
        raise ValueError(f"Unsupported PLY format {fmt}")
    return finite(points) * .001


def compare(info, step, estimate, truth, vertices, diameter):
    reference = reference_mssd(estimate, truth, vertices, reference_symmetries(info, step), diameter)
    production = mssd_normalized(estimate, truth, vertices, bop_symmetry_transforms(info, step), diameter)["mssd_over_diameter"]
    assert math.isfinite(reference) and math.isfinite(production)
    if abs(reference - production) > 1e-10:
        raise AssertionError(f"Reference/production disagreement: {reference} vs {production}")
    return reference, production


def analytical_tests(step):
    results = []
    points = np.array([[.3, 0, 0], [0, .3, 0], [0, 0, .2]])
    identity = np.eye(4)
    def check(name, info, estimate, truth, vertices, diameter, expected):
        ref, prod = compare(info, step, estimate, truth, vertices, diameter)
        assert abs(ref - expected) < 1e-10, (name, ref, expected)
        results.append({"name": name, "reference": ref, "production": prod, "expected": expected, "passed": True})
    check("identity", {}, identity, identity, points, 1., 0.)
    check("known_nonequivalent_translation", {}, transform(t=[.2, 0, 0]), identity, points, 1., .2)
    r = rotation([0, 0, 1], math.pi)
    offset = np.array([.1, .2, 0])
    symmetry = transform(r, offset - r @ offset)
    raw = symmetry.copy()
    raw[:3, 3] *= 1000
    info = {"symmetries_discrete": [raw.reshape(-1).tolist()]}
    gt = transform(rotation([1, 1, 0], .4), [.15, -.2, .7])
    check("translated_discrete_symmetry_nonidentity_GT", info, gt @ symmetry, gt, points, 1., 0.)
    legacy = reference_mssd(gt @ symmetry, gt, points, reference_symmetries(info, step, False), 1.)
    assert legacy > .1
    results.append({"name": "translated_symmetry_legacy_units_negative_control", "legacy": legacy, "passed": True})
    continuous_info = {"symmetries_continuous": [{"axis": [0, 0, 1], "offset": (offset * 1000).tolist()}]}
    count = math.ceil(math.pi / step)
    angle = 2 * math.pi * 37 / count
    r = rotation([0, 0, 1], angle)
    circle = offset + np.array([[.3, 0, 0], [-.3, 0, 0], [0, .3, 0]])
    check("offset_axis_continuous_on_grid", continuous_info, gt @ transform(r, offset - r @ offset), gt, circle, 1., 0.)
    angle = 2 * math.pi * 37.5 / count
    r = rotation([0, 0, 1], angle)
    check("offset_axis_continuous_half_grid", continuous_info, gt @ transform(r, offset - r @ offset), gt, circle, 1., 2 * .3 * math.sin(math.pi / (2 * count)))
    # Composition order must stay continuous @ discrete, even when noncommuting.
    discrete_rotation = rotation([1, 0, 0], math.pi)
    discrete_offset = np.array([.05, .02, .08])
    noncommuting_discrete = transform(discrete_rotation, discrete_offset - discrete_rotation @ discrete_offset)
    noncommuting_raw = noncommuting_discrete.copy()
    noncommuting_raw[:3, 3] *= 1000
    both = {**continuous_info, "symmetries_discrete": [noncommuting_raw.reshape(-1).tolist()]}
    r = rotation([0, 0, 1], 2 * math.pi * 11 / count)
    continuous = transform(r, offset - r @ offset)
    assert not np.allclose(continuous @ noncommuting_discrete, noncommuting_discrete @ continuous)
    check("continuous_discrete_composition", both, gt @ continuous @ noncommuting_discrete, gt, points, 1., 0.)
    return results


def category(accepted, correct):
    return ("accepted" if accepted else "rejected") + ("_and_correct" if correct else "_but_wrong" if accepted else "_and_wrong")


def main():
    config_path = ROOT / "configs/tless_frozen.json"
    config = read_json(config_path)
    step = config["pose_correctness"]["continuous_symmetry_max_vertex_travel_over_diameter"]
    threshold = config["pose_correctness"]["maximum_normalized_mssd"]
    info_path = ROOT / "data/tless/bop/models_cad/models_info.json"
    metadata = read_json(info_path)
    affected = {}
    for object_id, info in metadata.items():
        translations = [finite(s, (16,)).reshape(4, 4)[:3, 3].tolist() for s in info.get("symmetries_discrete", [])]
        offsets = [finite(s["offset"], (3,)).tolist() for s in info.get("symmetries_continuous", [])]
        if any(any(t != 0 for t in value) for value in translations + offsets):
            affected[int(object_id)] = {"discrete_translations_mm": translations, "continuous_offsets_mm": offsets}
    validation = analytical_tests(step)
    model_cache = {}
    gt_cache = {}
    details = []
    run_summaries = []
    issues = []
    gt_max_delta = 0.
    rotation_residuals = {"estimate": 0., "ground_truth": 0.}
    for result_path in sorted((ROOT / "data/tless/results").glob("*/*.jsonl")):
        run = result_path.relative_to(ROOT).as_posix()
        rows = [json.loads(line) for line in input_bytes(result_path).decode("utf-8").splitlines()]
        summary = read_json(result_path.with_suffix(".summary.json"))
        input_bytes(result_path.with_suffix(".csv"))
        frozen = summary["frozen_config"]
        assert frozen["pose_correctness"] == config["pose_correctness"], run
        assert frozen["geometric_acceptance"] == config["geometric_acceptance"], run
        manifest = read_json(ROOT / f"data/tless/manifests/{summary['manifest']}.json")
        cases = {case["case_id"]: case for case in manifest["cases"]}
        assert len(cases) == len(manifest["cases"])
        assert len({row["case_id"] for row in rows}) == len(rows)
        assert set(row["case_id"] for row in rows) <= cases.keys()
        valid = [row for row in rows if row["status"] == "valid"]
        controls = sorted((row for row in valid if row["object_id"] not in affected), key=lambda r: r["case_id"])[:3]
        continuous_control = next((row for row in sorted(valid, key=lambda r: r["case_id"]) if row["object_id"] not in affected and metadata[str(row["object_id"])].get("symmetries_continuous")), None)
        if continuous_control and continuous_control not in controls:
            controls.append(continuous_control)
        control_ids = {r["case_id"] for r in controls}
        updated = Counter(row["category"] for row in valid)
        transitions = Counter()
        affected_records = [r for r in rows if r["object_id"] in affected]
        scored = 0
        for row in rows:
            case_id = row["case_id"]
            case = cases[case_id]
            assert row["group"] == summary["group"]
            for field in ("scene_id", "image_id", "gt_index", "object_id"):
                assert row[field] == case[field], (run, case_id, field)
            assert case_id == f"tless-s{row['scene_id']:06d}-i{row['image_id']:06d}-g{row['gt_index']:02d}-o{row['object_id']:02d}"
            if row["status"] != "valid":
                issues.append({"run": run, "case_id": case_id, "status": row["status"], "affected_object": row["object_id"] in affected, "note": "No historical correctness label or saved estimate to rescore; original status carried forward."})
                continue
            estimate = pose(row["camera_from_object_estimate"])
            truth = pose(row["camera_from_object_ground_truth"])
            for name, matrix in (("estimate", estimate), ("ground_truth", truth)):
                rotation_residuals[name] = max(rotation_residuals[name], float(np.abs(matrix[:3, :3].T @ matrix[:3, :3] - np.eye(3)).max()))
            info = metadata[str(row["object_id"])]
            diameter = float(info["diameter"]) * .001
            assert math.isfinite(diameter) and diameter > 0
            assert abs(row["diameter_m"] - diameter) < 1e-12
            gt_path = ROOT / f"data/tless/bop/test_primesense/{row['scene_id']:06d}/scene_gt.json"
            if gt_path not in gt_cache:
                gt_cache[gt_path] = read_json(gt_path)
            annotation = gt_cache[gt_path][str(row["image_id"])][row["gt_index"]]
            assert annotation["obj_id"] == row["object_id"]
            annotation_truth = transform(finite(annotation["cam_R_m2c"], (9,)).reshape(3, 3), finite(annotation["cam_t_m2c"], (3,)) * .001)
            delta = float(np.abs(truth - annotation_truth).max())
            gt_max_delta = max(gt_max_delta, delta)
            assert delta < 1e-10, (run, case_id, delta)
            historical = float(row["pose_metrics"]["mssd_over_diameter"])
            assert math.isfinite(historical)
            assert abs(row["pose_metrics"]["mssd_m"] / diameter - historical) < 1e-12
            assert row["correct"] == (historical <= threshold)
            assert row["category"] == category(row["accepted"], row["correct"])
            metrics = row["alignment_quality_metrics"]
            assert math.isfinite(metrics["fitness"]) and math.isfinite(metrics["inlier_rmse_m"])
            acceptance = config["geometric_acceptance"]
            assert row["accepted"] == (metrics["fitness"] >= acceptance["minimum_fitness"] and metrics["inlier_rmse_m"] <= acceptance["maximum_inlier_rmse_m"])
            if row["object_id"] not in affected and case_id not in control_ids:
                continue
            if row["object_id"] not in model_cache:
                model_cache[row["object_id"]] = ply_vertices(ROOT / f"data/tless/bop/models_eval/obj_{row['object_id']:06d}.ply")
            vertices = model_cache[row["object_id"]]
            corrected, production = compare(info, step, estimate, truth, vertices, diameter)
            legacy = reference_mssd(estimate, truth, vertices, reference_symmetries(info, step, False), diameter)
            assert abs(legacy - historical) < 1e-10, (run, case_id, "saved metric differs from independent legacy-unit reference", legacy, historical)
            correct = corrected <= threshold
            new_category = category(row["accepted"], correct)
            detail = {"run": run, "case_id": case_id, "object_id": row["object_id"], "role": "affected" if row["object_id"] in affected else "unaffected_control", "historical_mssd_over_diameter": historical, "historical_label": row["category"], "corrected_mssd_over_diameter": corrected, "corrected_label": new_category, "outcome_changed": new_category != row["category"], "accepted_preserved": row["accepted"], "production_mssd_over_diameter": production, "production_reference_abs_delta": abs(production - corrected), "legacy_reference_abs_delta": abs(legacy - historical), "evaluation_vertex_count": len(vertices)}
            details.append(detail)
            if row["object_id"] in affected:
                scored += 1
                transitions[row["category"] + " -> " + new_category] += 1
                updated[row["category"]] -= 1
                updated[new_category] += 1
            else:
                assert not detail["outcome_changed"]
                assert abs(corrected - historical) < 1e-10
        assert scored == sum(r["status"] == "valid" for r in affected_records)
        run_summaries.append({"run": run, "records": len(rows), "manifest_cases": len(cases), "valid_records": len(valid), "affected_records": len(affected_records), "affected_valid_rescored": scored, "affected_without_label": len(affected_records) - scored, "unaffected_controls_rescored": len(controls), "unaffected_valid_carried_forward": len(valid) - scored, "statuses_preserved": dict(Counter(r["status"] for r in rows)), "historical_categories": dict(Counter(r["category"] for r in valid)), "corrected_categories": dict(updated), "affected_label_transitions": dict(transitions), "complete_for_saved_valid_records": True, "aggregate_method": "All affected valid records rescored; unaffected valid labels carried forward, with deterministic controls. Not a full independent rescore."})
    # Source hashes describe audit-time code ONLY, never historical execution.
    for relative in ("autoframe3d/tless_metrics.py", "autoframe3d/geometry.py", "autoframe3d/tless_adapter.py", "autoframe3d/tless_benchmark.py", "pyproject.toml", "data/tless/provenance.json"):
        input_bytes(ROOT / relative)
    input_bytes(Path(__file__))
    versions = {}
    for package in ("numpy", "scipy", "Pillow", "fastapi", "pydantic", "uvicorn", "huggingface_hub"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = None
    command = f".\\.venv\\Scripts\\python.exe {Path(__file__).relative_to(ROOT).as_posix()}"
    report = {"audit_timestamp_utc": datetime.now(timezone.utc).isoformat(), "scope": "All five JSONL run files present under data/tless/results/original and perturbed; archives/backups/search/replay outputs excluded.", "units_and_direction": "Saved estimates and GT are camera-from-object, translations in metres; GT independently matched local annotation obj_id/instance and mm-to-m translation for every valid record. Evaluation vertices/diameter and metadata translations/offsets converted mm to m. Symmetry applied in object coordinates before GT camera transform.", "affected_objects": affected, "continuous_nonzero_offset_objects": [k for k, v in affected.items() if any(any(x != 0 for x in offset) for offset in v["continuous_offsets_mm"])], "frozen_threshold": threshold, "symmetry_step": step, "symmetry_samples_per_continuous_axis": math.ceil(math.pi / step), "analytical_validation": validation, "run_summaries": run_summaries, "issues": issues, "missing_or_invalid_valid_record_inputs": [], "maximum_saved_GT_annotation_abs_delta": gt_max_delta, "maximum_production_reference_abs_delta": max(r["production_reference_abs_delta"] for r in details), "maximum_historical_legacy_reference_abs_delta": max(r["legacy_reference_abs_delta"] for r in details), "provenance": {"python": sys.version, "executable": sys.executable, "platform": platform.platform(), "dependency_versions": versions, "commands": [command], "sampling": "No randomness or seed: first three unaffected valid case IDs lexicographically per run, plus first unaffected continuous-symmetry case when available.", "original_run_provenance": "Original execution source hashes and complete dependency identities unavailable; historical counts/poses/metrics audited as saved. No current source hash attributed to historical runs.", "inputs_and_audit_current_sources": INPUTS}}
    # Confirm read-only inputs have not changed during the audit.
    for relative, identity in INPUTS.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == identity["sha256"], relative
    (OUT / "audit_summary.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    with (OUT / "rescored_records.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(details[0]))
        writer.writeheader()
        writer.writerows(details)
    (OUT / "rescored_records.json").write_text(json.dumps(details, indent=2, allow_nan=False), encoding="utf-8")
    report["input_rotation_orthogonality_residuals"] = rotation_residuals
    report["input_validation_note"] = "Initial audit stopped on GT orthogonality residual 1.09e-6 at 1e-6 validation tolerance. Read-only inspection measured maximum 1.38e-6 in rounded GT matrices. Final validation tolerance is 1e-5; no pose matrix projected, altered, or re-estimated; scoring threshold remains 0.10. Initial failure retained in audit_failure.json."
    report["provenance"]["commands"] = [
        {"command": command, "outcome": "Initial attempt failed on rounded GT matrix orthogonality validation; audit_failure.json retained."},
        {"command": command, "outcome": "Passed after correcting input-validation tolerance; no scoring-threshold changes."},
        {"command": command.replace("python.exe ", "python.exe -B "), "outcome": "Final reproducibility run; bytecode writing disabled."},
        {"command": command.replace("python.exe ", "python.exe -B "), "outcome": "Final run after strengthening analytical composition fixture to noncommuting axes; bytecode writing disabled."},
    ]
    (OUT / "audit_summary.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    lines = [
        "# Independent historical T-LESS scoring audit", "",
        "One saved heldout200 label changes. Estimated poses and geometric acceptance are unchanged.", "",
        "Scope: five existing JSONL run files under data/tless/results; results are reported separately, since smoke/development runs overlap. All 30 object metadata entries inspected. Affected objects: 8, 10, 11, 12, 25, 26; translated discrete symmetries only. No nonzero continuous offsets in local metadata.", "",
        "All affected valid records have finite poses/metrics, matching object/instance IDs and manifests. All 256 saved valid GT transforms match local cam_R_m2c/cam_t_m2c after mm-to-m conversion exactly. Raw saved estimates are used without alteration. Eight initial smoke timeouts have no saved estimate or correctness label, including two object-8 records; statuses retained, not scored.", "",
        "Independent reference uses Rodrigues rotations, a separate PLY vertex reader, and homogeneous matrix multiplication GT @ symmetry @ object_point. MSSD is minimum over symmetries of maximum corresponding-point displacement, divided by diameter. Frozen threshold: 0.10 inclusive. Original continuous rule: ceil(pi / 0.01) = 315 samples; continuous @ discrete composition preserved.", "",
        "Seven analytical checks passed: identity, known non-equivalent translation, translated discrete symmetry with nonidentity GT, legacy-unit negative control, continuous offset axis on-grid, continuous half-grid with analytic residual, and combined composition. Corrected production/reference maximum normalized difference on rescored records: " + str(report["maximum_production_reference_abs_delta"]) + ". Independent legacy-unit scorer reproduces historical MSSD within " + str(report["maximum_historical_legacy_reference_abs_delta"]) + ". Fifteen deterministic unaffected controls retain metrics and labels.", "",
        "| Run | Affected valid rescored | Affected timeout | Correct before → after | Wrong before → after |",
        "|---|---:|---:|---:|---:|",
    ]
    for run in run_summaries:
        old, new = run["historical_categories"], run["corrected_categories"]
        lines.append(f"| {run['run']} | {run['affected_valid_rescored']} | {run['affected_without_label']} | {old.get('accepted_and_correct', 0)} → {new.get('accepted_and_correct', 0)} | {old.get('accepted_but_wrong', 0)} → {new.get('accepted_but_wrong', 0)} |")
    lines += ["", "Heldout original corrected aggregate: 24 accepted-and-correct, 176 accepted-but-wrong (88.0%), zero rejected/timeouts/failures. All 21 affected records rescored; 179 unaffected labels carried forward, including three scored controls. This is not a full independent rescore. Previous 23/177 and 88.5% figures remain historical recorded values; corrected-score claims must use 24/176 and 88.0%.", "", "## Every affected valid record", "", "| Run | Case ID | Object | Historical MSSD/D | Historical label | Corrected MSSD/D | Corrected label | Changed |", "|---|---|---:|---:|---|---:|---|---|"]
    for row in details:
        if row["role"] == "affected":
            lines.append(f"| {row['run']} | {row['case_id']} | {row['object_id']} | {row['historical_mssd_over_diameter']:.12g} | {row['historical_label']} | {row['corrected_mssd_over_diameter']:.12g} | {row['corrected_label']} | {row['outcome_changed']} |")
    lines += ["", "Affected records without historical labels/estimates: tless-s000003-i000005-g01-o08 and tless-s000004-i000000-g01-o08 in original/smoke20.jsonl (timeouts). No missing/invalid/nonfinite inputs among historical valid records.", "", "## Execution and provenance", "", "Final command (repository root):", "", "```powershell", report["provenance"]["commands"][-1]["command"], "```", "", report["input_validation_note"], "", "audit_summary.json hashes 60 exact inputs/current sources, including historical JSONL/CSV/summary files, all five manifests, relevant model PLYs and metadata, local GT annotations, frozen config, dataset provenance, and audit/current scoring source. Input hashes rechecked unchanged at end. Dependencies and execution environment recorded. These are audit-time identities; original-run source identity and complete dependency versions remain unavailable. No current hash is attributed to historical execution.", "", "Historical evaluation uses GT-provided visible instance masks. Held-out aggregate results have already been inspected; this audit provides scoring correction, not untouched generalization evidence. No registration, training, threshold tuning, downloads, installations, or remote/model calls occurred. Other historical result files, backups and reports were not changed."]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"affected_objects": list(affected), "validation_passed": len(validation), "runs": run_summaries, "maximum_production_reference_abs_delta": report["maximum_production_reference_abs_delta"], "issues": issues}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        (OUT / "audit_failure.json").write_text(json.dumps({"type": type(error).__name__, "error": str(error), "input_hashes": INPUTS}, indent=2), encoding="utf-8")
        raise
