"""Four-case, one-attempt reciprocal ICP from immutable saved baseline poses.

Prepare freezes identities before execution; run refuses any second attempt.
No PCA search, GT pose initialization, network access, or threshold changes.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASE = "audit_evidence/development_eligibility_audit_20261011T053002Z_963a0a93"
RECIPROCAL = "audit_evidence/recorded_benchmark_demo/reciprocal_results.jsonl"
IDS = (
    "tless-s000001-i000001-g00-o02", "tless-s000002-i000003-g00-o05",
    "tless-s000002-i000003-g01-o06", "tless-s000002-i000024-g02-o07",
)
THREADS = {k: "1" for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}
CODE = ("autoframe3d/tless_adapter.py", "autoframe3d/tless_metrics.py",
        "autoframe3d/geometry.py", "scripts/evaluate_saved_pose_reciprocal.py")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def file_identity(path):
    data = (ROOT / path).read_bytes()
    return {"sha256": digest(data), "bytes": len(data)}


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()


def dependencies():
    return {x: importlib.metadata.version(x) for x in ("numpy", "scipy", "Pillow")}


def prepare(output):
    from autoframe3d import tless_adapter as adapter
    historical = read(ROOT / BASE / "plan.json")
    copies = read(ROOT / BASE / "COPY_MANIFEST.json")["files"]
    for name in ("plan.json", "results.jsonl"):
        assert file_identity(f"{BASE}/{name}")["sha256"] == copies[name]["publication_sha256"]
    pub = read(ROOT / "audit_evidence/recorded_benchmark_demo/COPY_MANIFEST.json")
    assert file_identity(RECIPROCAL)["sha256"] == pub["files"]["reciprocal_results.jsonl"]["publication_sha256"]
    old = [json.loads(x) for x in (ROOT / RECIPROCAL).read_text().splitlines()]
    assert tuple(x["case"]["case_id"] for x in old) == IDS
    baselines = [json.loads(x) for x in (ROOT / BASE / "results.jsonl").read_text().splitlines()]
    config = read(ROOT / "configs/tless_frozen.json")
    assert config == historical["config"]
    cases, inventory = [], {}
    for entry in old:
        case = entry["case"]
        rows = [x for x in baselines if x["case_id"] == case["case_id"]]
        assert len(rows) == 1
        row = rows[0]
        assert row["status"] == "valid" and row["group"] == "original"
        assert all(row[k] == v for k, v in case.items())
        s = f"data/tless/bop/test_primesense/{case['scene_id']:06d}"
        files = [f"{s}/scene_camera.json", f"{s}/depth/{case['image_id']:06d}.png",
                 f"{s}/mask_visib/{case['image_id']:06d}_{case['gt_index']:06d}.png",
                 f"data/tless/bop/models_cad/obj_{case['object_id']:06d}.ply",
                 f"data/tless/bop/models_eval/obj_{case['object_id']:06d}.ply",
                 "data/tless/bop/models_cad/models_info.json", f"{s}/scene_gt.json"]
        for path in files:
            identity = file_identity(path)  # Missing data is a blocker, never substituted.
            assert identity == historical["input_and_source_inventory"][path], path
            inventory[path] = identity
        cases.append({"case": case, "input_files": files,
                      "initial_camera_from_object": row["camera_from_object_estimate"],
                      "initial_pose_sha256": digest(canonical(row["camera_from_object_estimate"])),
                      "baseline_record_sha256": digest(canonical(row)),
                      "saved_baseline": {"alignment_quality_metrics": row["alignment_quality_metrics"],
                                         "pose_metrics": row["pose_metrics"], "correct": row["correct"],
                                         "accepted": row["accepted"]}})
    assert [x["saved_baseline"]["correct"] for x in cases] == [False, False, False, True]
    plan = {
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(), "base_commit": git("rev-parse", "HEAD"),
        "existing_evidence_review": "Saved reciprocal results use six PCA starts, not saved baseline initialization. Diagnostic GT starts and synthetic fixtures also do not match. No matching saved experiment found in reviewed local refinement/diagnosis evidence.",
        "initialization": "Exactly one saved baseline camera-from-object pose per case; no candidate selection/PCA",
        "method": {"icp_correspondence_policy": "reciprocal", "max_iterations": 8,
                   "correspondence_distance_m": .015, "model_registration_points_max": 3000,
                   "sampling": "np.linspace(0, len(evaluation_model)-1, min(3000,len(model)), dtype=int64)",
                   "minimum_correspondences": 20, "translation_stop_m": 1e-5,
                   "random_seed": None, "randomness": "None; deterministic vertex subsampling and nearest neighbors"},
        "scoring": {"pose_correctness": config["pose_correctness"], "geometric_acceptance": config["geometric_acceptance"],
                    "units": "transforms/distances metres; fitness and MSSD/diameter dimensionless",
                    "baseline_verification_tolerance": 1e-9},
        "per_case_hard_timeout_seconds": 30, "attempts_per_case": 1, "thread_environment": THREADS,
        "gt_dependency": "GT instance masks and known object identities; target GT pose and symmetry scoring only after refinement",
        "cases": cases, "input_inventory": inventory,
        "evidence_inventory": {p: file_identity(p) for p in (f"{BASE}/plan.json", f"{BASE}/results.jsonl", RECIPROCAL, "configs/tless_frozen.json")},
        "code_identity": {p: {**file_identity(p), "head_blob": git("rev-parse", f"HEAD:{p}") if p != CODE[-1] else None,
                              "uncommitted": bool(git("diff", "HEAD", "--", p)) if p != CODE[-1] else True} for p in CODE},
        "existing_refinement_source": inspect.getsource(adapter._refine_icp),
        "research_adapter_diff_sha256": digest(subprocess.check_output(["git", "diff", "HEAD", "--", CODE[0]], cwd=ROOT)),
        "python": sys.version, "dependencies": dependencies(),
    }
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / "manifest.json", plan)
    print(json.dumps({"prepared": str(output), "cases": IDS, "input_hashes_verified": True}))


def verify(plan):
    for section in ("input_inventory", "evidence_inventory", "code_identity"):
        for path, expected in plan[section].items():
            assert file_identity(path)["sha256"] == expected["sha256"], f"Changed identity: {path}"
    assert dependencies() == plan["dependencies"] and sys.version == plan["python"]
    for item in plan["cases"]:
        assert digest(canonical(item["initial_camera_from_object"])) == item["initial_pose_sha256"]


def worker(plan, index):
    import numpy as np
    from scipy.spatial import cKDTree
    from autoframe3d import tless_adapter as adapter
    from autoframe3d.geometry import invert_transform, transform_points
    from autoframe3d.tless_metrics import bop_symmetry_transforms, mssd_normalized, classify_result
    item = plan["cases"][index]
    started = time.monotonic()
    # Guard annotation access throughout input loading and refinement. Symmetry
    # metadata loaded by the adapter is not passed to the array-only ICP function.
    phase = {"refinement": True}
    def audit(event, args):
        if event == "socket.connect":
            raise RuntimeError("Network forbidden")
        if event == "open" and phase["refinement"] and str(args[0]).endswith("scene_gt.json"):
            raise RuntimeError("GT pose access during refinement forbidden")
    sys.addaudithook(audit)
    def forbidden(*args, **kwargs):
        raise RuntimeError("GT initializer/PCA search forbidden")
    original_gt = adapter.load_ground_truth
    adapter.load_ground_truth = forbidden
    adapter.pca_initial_rotations = forbidden
    inputs = adapter.load_registration_inputs(item["case"])
    initial = np.asarray(item["initial_camera_from_object"], dtype=np.float64)
    model, scan = inputs.evaluation_points_object_m, inputs.scan_points_camera_m
    ids = np.linspace(0, len(model)-1, min(3000, len(model)), dtype=np.int64)
    trace = []
    fit_started = time.monotonic()
    refined = adapter._refine_icp(scan, model[ids], model, initial,
        correspondence_distance_m=.015, max_iterations=8, icp_correspondence_policy="reciprocal",
        deadline=started+plan["per_case_hard_timeout_seconds"], iteration_trace=trace)
    fit_seconds = time.monotonic()-fit_started
    last = initial if len(trace) == 1 else trace[-2]["camera_from_object"] if trace else initial
    delta = refined @ invert_transform(last)
    converged = bool(trace) and np.linalg.norm(delta[:3, 3]) < 1e-5
    termination = "translation_convergence" if converged else "iteration_limit" if len(trace) == 8 else "insufficient_correspondences"
    phase["refinement"] = False
    truth = original_gt(item["case"])
    assert truth.object_id == inputs.object_id
    syms = bop_symmetry_transforms(inputs.model_info, max_symmetry_step=.01)
    tree = cKDTree(model)
    def metrics(pose):
        distances, _ = tree.query(transform_points(scan, invert_transform(pose)), k=1, workers=1)
        inliers = distances <= .015
        rmse = float(np.sqrt(np.mean(distances[inliers]**2))) if inliers.any() else None
        pose_metrics = mssd_normalized(pose, truth.camera_from_object, model, syms, float(inputs.model_info["diameter"])*.001)
        accepted, correct, category = classify_result(float(inliers.mean()), rmse if rmse is not None else float("inf"), pose_metrics["mssd_over_diameter"])
        return {"fitness": float(inliers.mean()), "inlier_rmse_m": rmse, "inlier_rmse_mm": None if rmse is None else rmse*1000,
                **pose_metrics, "accepted": accepted, "correct": correct, "category": category}
    baseline, after = metrics(initial), metrics(refined)
    saved = item["saved_baseline"]
    assert all(abs(baseline[k]-saved["alignment_quality_metrics"][k]) <= 1e-9 for k in ("fitness", "inlier_rmse_m"))
    assert all(abs(baseline[k]-saved["pose_metrics"][k]) <= 1e-9 for k in ("mssd_m", "mssd_over_diameter"))
    status = "completed" if termination != "insufficient_correspondences" else "insufficient_correspondences"
    outcome = (("remained_correct" if after["correct"] else "regression") if baseline["correct"] else
               ("recovery" if after["correct"] else "remained_wrong")) if status == "completed" else "incomplete"
    return {"case_id": item["case"]["case_id"], "status": status, "outcome": outcome,
            "initial_camera_from_object": initial.tolist(), "refined_camera_from_object": refined.tolist(),
            "baseline": baseline, "refined": after, "baseline_metrics_verified": True,
            "gt_access_guard": "Passed: no annotation access/PCA permitted until refinement returned",
            "termination": termination, "iterations": len(trace),
            "correspondence_counts": [x["correspondence_count"] for x in trace],
            "refinement_seconds": fit_seconds, "worker_seconds": time.monotonic()-started}


def run(output):
    plan = read(output / "manifest.json")
    verify(plan)
    manifest_hash = file_identity(str((output / "manifest.json").relative_to(ROOT)))["sha256"]
    # An atomic, immutable start marker prevents retries even after interruption.
    write_new(output / "started.json", {"manifest_sha256": manifest_hash, "started_at_utc": datetime.now(timezone.utc).isoformat()})
    results = []
    for index, item in enumerate(plan["cases"]):
        started = time.monotonic()
        try:
            child = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--worker", str(index), "--output", str(output)],
                cwd=ROOT, env={**os.environ, **THREADS}, capture_output=True, text=True,
                timeout=plan["per_case_hard_timeout_seconds"])
            if child.returncode:
                raise RuntimeError(child.stderr[-2000:] or f"Worker exit {child.returncode}")
            row = json.loads(child.stdout)
        except Exception as error:
            row = {"case_id": item["case"]["case_id"], "status": "timeout" if isinstance(error, subprocess.TimeoutExpired) else "failed",
                   "outcome": "incomplete", "error": str(error), "initial_camera_from_object": item["initial_camera_from_object"],
                   "refined_camera_from_object": None, "saved_baseline": item["saved_baseline"]}
        row.update(manifest_sha256=manifest_hash, wall_seconds=time.monotonic()-started)
        write_new(output / f"case-{index+1}.json", row)
        results.append(row)
        print(json.dumps({k: row[k] for k in ("case_id", "status", "outcome", "wall_seconds")}), flush=True)
    verify(plan)
    summary = {"manifest_sha256": manifest_hash, "attempted": len(results), "reused_baselines": 4,
               "reused_refinements": 0, "initially_wrong": 3, "initially_correct": 1,
               "recoveries": sum(r["outcome"] == "recovery" for r in results),
               "regressions": sum(r["outcome"] == "regression" for r in results),
               "incomplete": [r["case_id"] for r in results if r["outcome"] == "incomplete"],
               "source_and_inputs_unchanged": True, "result_sha256": {f"case-{i+1}.json": file_identity(str((output/f'case-{i+1}.json').relative_to(ROOT)))["sha256"] for i in range(4)}}
    write_new(output / "summary.json", summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--worker", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT)
    if args.worker is not None:
        print(json.dumps(worker(read(output/"manifest.json"), args.worker), allow_nan=False))
    elif args.prepare:
        prepare(output)
    elif args.run:
        run(output)
    else:
        parser.error("Choose --prepare or --run")
