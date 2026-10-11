"""Outcome-independent development baseline sampling; no perturbation search."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.development_search_pilot import isolated_call

PILOT = ROOT / "artifacts/development_search_pilot_20261011T051807Z_289be02e"
CATEGORIES = ("accepted_and_correct", "accepted_but_wrong", "rejected_and_correct", "rejected_and_wrong")


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def previous_pilot_review():
    plan = read(PILOT / "plan.json")
    summary = read(PILOT / "summary.json")
    rows = [json.loads(line) for line in (PILOT / "results.jsonl").read_text().splitlines()]
    artifact_hashes = read(PILOT / "output_hashes.json")
    integrity = all(sha(PILOT / name) == artifact_hashes[name]["sha256"]
                    for name in ("plan.json", "summary.json", "results.jsonl", "execution_guard.json"))
    inputs = all(sha(PILOT / p if p == "selected_manifest.json" else ROOT / p) == identity["sha256"]
                 for p, identity in plan["file_inventory"].items())
    environment = sys.version == plan["python"] and all(version(k) == v for k, v in plan["dependency_versions"].items())
    compatible = integrity and inputs and environment
    arms = {}
    for method in ("deterministic", "seeded_random"):
        arm = [row for row in rows if row.get("method") == method]
        zero = sum(row["proposal"]["noise_std_m"] == 0 and row["proposal"]["point_dropout_fraction"] == 0 for row in arm)
        arms[method] = {"candidate_calls": len(arm), "zero_perturbation_candidates": zero, "nonzero_perturbation_candidates": len(arm) - zero}
    assert plan["evaluations_per_case_seed_method"] == 4 and plan["planned_candidate_slots"] == 120
    assert summary["complete"] and summary["skipped_candidate_slots_due_to_deadline"] == 0
    assert all(result["candidate_slots"] == 4 for result in summary["case_seed_results"])
    historical = []
    for path in sorted((ROOT / "data/tless/results/original").glob("*.jsonl")):
        if path.stem == "heldout200":
            continue
        saved = [json.loads(line) for line in path.read_text().splitlines()]
        historical.append({"path": path.relative_to(ROOT).as_posix(), "records": len(saved),
                           "records_with_source_provenance": sum("provenance" in row for row in saved),
                           "classification": "Historical only; source/config/input identity for current execution not established. Not reused or mixed with fresh eligibility counts."})
    return {"declared_budget_per_case_seed_method": 4, "allowed_maximum": 10,
            "explanation": "At most ten was a ceiling, not a requirement. Existing policy supplied four proposals, fixed in plan before outcomes. 5 cases x 3 seeds x 4 = 60 per method; all slots ran; no discovery-based stopping or time truncation.",
            "arms": arms, "fairness_defect": "Equal calls but asymmetric no-op coverage: deterministic had 15 zero-perturbation baseline repetitions, random had zero. Nonzero perturbation counts were 45 versus 60. Deterministic first-discovery index one was guaranteed by already-wrong baselines; it is not evidence of search value or a perturbation-induced failure. Previous pilot remains unchanged.",
            "prior_pilot_baseline_compatibility": {"compatible": compatible, "artifact_hashes_match": integrity,
                "source_config_manifest_input_hashes_match": inputs, "python_dependencies_match": environment,
                "thread_policy": plan["thread_environment"], "compatible_records": 5 if compatible else 0,
                "reuse_decision": "Freshly evaluate all selected cases once; do not include prior baseline outcomes in new counts."},
            "historical_baseline_files": historical}


def prepare():
    dev = ROOT / "data/tless/manifests/development.json"
    heldout = ROOT / "data/tless/manifests/heldout200.json"
    development = read(dev)["cases"]
    buckets = defaultdict(list)
    for case in development:
        buckets[case["object_id"]].append(case)
    for cases in buckets.values():
        cases.sort(key=lambda case: case["case_id"])
    selected = []
    rank = 0
    while len(selected) < min(30, len(development)):
        for object_id in sorted(buckets):
            if rank < len(buckets[object_id]):
                selected.append(buckets[object_id][rank])
                if len(selected) == 30:
                    break
        rank += 1
    assert len(selected) == len({case["case_id"] for case in selected}) == 30
    assert all(case["scene_id"] in {1, 2, 3, 4} for case in selected)
    assert not {case["case_id"] for case in selected} & {case["case_id"] for case in read(heldout)["cases"]}
    out = ROOT / "artifacts" / ("development_eligibility_audit_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex[:8])
    out.mkdir(exist_ok=False)
    selection = {"procedure": "Round-robin ascending available object IDs; within each object lexicographic case ID order. Take first 30; no outcomes used, no early stopping on correctness. Two or three cases per each of 13 available objects.",
                 "development_pool_cases": len(development), "available_object_ids": sorted(buckets),
                 "selected_object_counts": dict(Counter(c["object_id"] for c in selected)), "heldout_overlap": 0, "cases": selected}
    write(out / "selected_manifest.json", selection)
    # Selection is persisted before looking at saved artifact compatibility or any fresh outcomes.
    review = previous_pilot_review()
    write(out / "previous_pilot_review.json", review)
    config = ROOT / "configs/tless_frozen.json"
    assert read(config)["execution"]["timeout_seconds"] == 30
    paths = [dev, heldout, config, Path(__file__), ROOT / "scripts/development_search_pilot.py", ROOT / "pyproject.toml",
             ROOT / "data/tless/provenance.json", ROOT / "data/tless/bop/models_cad/models_info.json"]
    paths += list((ROOT / "autoframe3d").glob("*.py"))
    paths += [PILOT / name for name in ("plan.json", "summary.json", "results.jsonl", "execution_guard.json", "output_hashes.json")]
    paths += list(PILOT.rglob("*.py"))
    paths += [ROOT / item["path"] for item in review["historical_baseline_files"]]
    for case in selected:
        scene = ROOT / f"data/tless/bop/test_primesense/{case['scene_id']:06d}"
        paths += [scene / "scene_camera.json", scene / "scene_gt.json",
                  scene / f"depth/{case['image_id']:06d}.png", scene / f"mask_visib/{case['image_id']:06d}_{case['gt_index']:06d}.png",
                  ROOT / f"data/tless/bop/models_cad/obj_{case['object_id']:06d}.ply", ROOT / f"data/tless/bop/models_eval/obj_{case['object_id']:06d}.ply"]
    missing = [str(p.relative_to(ROOT)) for p in paths if not p.is_file()]
    if missing:
        raise RuntimeError(f"Missing local inputs; no evaluations launched: {missing}")
    plan = {"prepared_at_utc": datetime.now(timezone.utc).isoformat(), "selection": selection,
            "selection_manifest_sha256": sha(out / "selected_manifest.json"), "evaluations": 30,
            "group": "original", "perturbation": None, "repeat_attempts": 0, "reuse_saved_baselines": False,
            "total_execution_limit_seconds": 900, "outer_watchdog_seconds": 895, "per_case_limit_seconds": 30,
            "reserve_report_seconds": 15, "config": read(config), "random_selection_seed": None,
            "thread_environment": {name: "1" for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
            "python": sys.version, "platform": platform.platform(),
            "dependency_versions": {name: version(name) for name in ("numpy", "scipy", "Pillow", "pydantic", "fastapi", "uvicorn", "huggingface_hub")},
            "input_and_source_inventory": {p.relative_to(ROOT).as_posix(): {"sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(set(paths))},
            "base_commit": subprocess.check_output(["git", "--no-optional-locks", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "commands": [".\\.venv\\Scripts\\python.exe -B scripts/development_eligibility_audit.py --prepare",
                         ".\\.venv\\Scripts\\python.exe -B scripts/development_eligibility_audit.py --run " + out.relative_to(ROOT).as_posix()]}
    write(out / "plan.json", plan)
    print(json.dumps({"directory": out.relative_to(ROOT).as_posix(), "selected_objects": selection["selected_object_counts"], "selected_cases": 30, "heldout_overlap": 0, "pilot_review": review}, indent=2))


def execute(out):
    import csv
    started = time.monotonic()
    plan = read(out / "plan.json")
    assert not (out / "results.jsonl").exists(), "Refusing to repeat or overwrite an audit"
    assert sha(out / "selected_manifest.json") == plan["selection_manifest_sha256"]
    for path, identity in plan["input_and_source_inventory"].items():
        assert sha(ROOT / path) == identity["sha256"], path
    cases = plan["selection"]["cases"]
    rows = []
    deadline = started + 880  # Preserve report time inside the 895-second outer watchdog.
    with (out / "results.jsonl").open("x", encoding="utf-8") as file:
        for case in cases:
            if deadline - time.monotonic() < 30:
                break
            result = isolated_call({"operation": "evaluate", "case": case, "group": "original"}, deadline)
            result.update(case)
            rows.append(result)
            file.write(json.dumps(result, allow_nan=False) + "\n"); file.flush()
            print(json.dumps({"completed": len(rows), "case_id": case["case_id"], "category": result.get("category"), "status": result["status"]}), flush=True)
    completed = {r["case_id"] for r in rows}
    unfinished = [c for c in cases if c["case_id"] not in completed]
    flat = []
    for case in cases:
        result = next((row for row in rows if row["case_id"] == case["case_id"]), {})
        metrics, pose = result.get("alignment_quality_metrics", {}), result.get("pose_metrics", {})
        flat.append({"case_id": case["case_id"], "object_id": case["object_id"], "fitness": metrics.get("fitness"),
                     "inlier_rmse_m": metrics.get("inlier_rmse_m"), "mssd_over_diameter": pose.get("mssd_over_diameter"),
                     "accepted": result.get("accepted"), "correct": result.get("correct"),
                     "category": result.get("category"), "status": result.get("status", "unfinished"),
                     "evaluator_runtime_seconds": result.get("runtime_seconds"), "wall_seconds": result.get("outer_call_seconds"),
                     "error": result.get("error")})
    eligible = [row for row in flat if row["status"] == "valid" and row["category"] == "accepted_and_correct"]
    unchanged = all(sha(ROOT / p) == identity["sha256"] for p, identity in plan["input_and_source_inventory"].items())
    summary = {"completed_calls": len(rows), "planned_cases": len(cases), "unfinished_cases": unfinished,
               "category_counts": {category: sum(r.get("category") == category for r in rows) for category in CATEGORIES},
               "status_counts": {status: sum(r["status"] == status for r in rows) for status in ("valid", "timeout", "processing_failure")},
               "eligible_case_ids": [row["case_id"] for row in eligible], "eligible_count": len(eligible),
               "five_case_pilot_decision": "GO" if len(eligible) >= 5 else "NO-GO: verified current eligible pool has fewer than five cases",
               "scope_limit": "Only the fixed 30-case sample was freshly evaluated, not all 768 development cases. This cannot establish absence of eligible cases elsewhere in the split.",
               "conditional_interpretation": "Selecting accepted-and-correct starts by baseline correctness is intentional. Future results estimate robustness conditional on initial success, not unconditional failure rate or generalization performance.",
               "next_step_if_insufficient": "Predeclare one further balanced batch of at most 30 previously unaudited development IDs, keeping registration and thresholds fixed; do not preferentially pick historically successful IDs.",
               "elapsed_execute_seconds": time.monotonic() - started, "source_config_inputs_and_previous_pilot_unchanged": unchanged,
               "model_calls": 0, "perturbed_evaluations": 0, "heldout_registration_calls": 0,
               "plan_sha256": sha(out / "plan.json"), "reused_saved_baseline_count": 0}
    write(out / "summary.json", summary)
    with (out / "eligibility_table.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(flat[0])); writer.writeheader(); writer.writerows(flat)
    write(out / "eligible_candidates.json", {"selection_by_baseline_correctness_intentional": True, "conditional_robustness_only": True, "cases": [case for case in cases if case["case_id"] in summary["eligible_case_ids"]]})
    lines = ["# Development baseline eligibility audit", "", summary["five_case_pilot_decision"], "", "All results below are fresh, unperturbed, once-only calls. Historical baseline artifacts are excluded; compatible previous pilot baselines are documented separately and deliberately not reused.", "", "## Complete selected-case table", "", "| Case | Object | Fitness | RMSE m | MSSD/D | Accepted | Correct | Category/status | Wall s |", "|---|---:|---:|---:|---:|---|---|---|---:|"]
    for row in flat:
        def number(value):
            return "—" if value is None else f"{value:.6g}"
        lines.append(f"| {row['case_id']} | {row['object_id']} | {number(row['fitness'])} | {number(row['inlier_rmse_m'])} | {number(row['mssd_over_diameter'])} | {row['accepted']} | {row['correct']} | {row['category'] or row['status']} | {number(row['wall_seconds'])} |")
    lines += ["", "Category counts: " + json.dumps(summary["category_counts"]) + ". Operational statuses: " + json.dumps(summary["status_counts"]) + ". Unfinished: " + str(len(unfinished)) + ".", "", summary["conditional_interpretation"], "", summary["scope_limit"], "", "If fewer than five eligible starts: " + summary["next_step_if_insufficient"], "", "GT-provided visible instance masks are used. Scoring is GT-dependent after geometry-only registration selection. Frozen configuration and corrected symmetry scoring remain unchanged. No perturbations, adaptive-agent experiment, training, remote calls, commits or pushes were performed.", "", "Selection, exact commands, source/config/manifest/raw input SHA-256 and dependency versions: plan.json. Prior pilot budget/no-op asymmetry and compatibility checks: previous_pilot_review.json. Full saved poses and metrics: results.jsonl. Initial success filtering does not establish deployable GT-free failure detection."]
    (out / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


def guarded_run(out):
    assert not (out / "execution_guard.json").exists(), "Refusing to repeat this audit"
    guard = {"command": ".\\.venv\\Scripts\\python.exe -B scripts/development_eligibility_audit.py --run " + out.relative_to(ROOT).as_posix(),
             "hard_process_tree_timeout_seconds": 895, "total_budget_seconds": 900,
             "timeout_action": "Kill only this spawned audit PID and descendants; no retries"}
    write(out / "execution_guard.json", guard)
    started = time.monotonic()
    child = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "--execute", str(out)], cwd=ROOT,
                             creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
    try:
        code = child.wait(timeout=895)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], capture_output=True, timeout=4)
        code = 124
    guard.update({"returncode": code, "elapsed_wall_seconds": time.monotonic() - started})
    write(out / "execution_guard.json", guard)
    if not (out / "summary.json").exists():
        records = []
        path = out / "results.jsonl"
        if path.exists():
            records = [json.loads(line) for line in path.read_text().splitlines()]
        done = {r["case_id"] for r in records}
        write(out / "unfinished_cases.json", {"execution_failed_or_timed_out": True, "unfinished": [c for c in read(out / "plan.json")["selection"]["cases"] if c["case_id"] not in done]})
    sys.exit(code)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--run", type=Path)
    parser.add_argument("--execute", type=Path)
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.run:
        guarded_run(args.run.resolve())
    elif args.execute:
        execute(args.execute.resolve())
    else:
        parser.error("Use --prepare or --run DIRECTORY")
