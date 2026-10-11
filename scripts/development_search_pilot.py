"""Predeclared development-only comparison with isolated, killable evaluation calls."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SEEDS = (101, 202, 303)
TOTAL_SECONDS = 900.
CALL_SECONDS = 30.
RESERVE_SECONDS = 65.
METHODS = ("deterministic", "seeded_random")


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(paths):
    return {path.relative_to(ROOT).as_posix(): {"sha256": digest(path), "bytes": path.stat().st_size}
            for path in sorted(set(paths))}


def prepare():
    from autoframe3d.tless_search import deterministic_proposals, random_proposals, SEARCH_BUDGET
    dev_path = ROOT / "data/tless/manifests/development.json"
    heldout_path = ROOT / "data/tless/manifests/heldout200.json"
    development = json.loads(dev_path.read_text())["cases"]
    heldout = json.loads(heldout_path.read_text())["cases"]
    selected = []
    for case in development:
        if case["object_id"] not in {item["object_id"] for item in selected}:
            selected.append(case)
        if len(selected) == 5:
            break
    assert len(selected) == 5 and all(case["scene_id"] in {1, 2, 3, 4} for case in selected)
    assert not {case["case_id"] for case in selected} & {case["case_id"] for case in heldout}
    config_path = ROOT / "configs/tless_frozen.json"
    config = json.loads(config_path.read_text())
    assert config["execution"]["timeout_seconds"] == CALL_SECONDS
    assert SEARCH_BUDGET == 4  # Preserve existing strategies, rather than extending after observing results.
    paths = [dev_path, heldout_path, config_path, ROOT / "pyproject.toml", Path(__file__),
             ROOT / "data/tless/provenance.json", ROOT / "data/tless/bop/models_cad/models_info.json",
             ROOT / "tests/test_tless_replay_parameters.py"]
    paths.extend((ROOT / "autoframe3d").glob("*.py"))
    for case in selected:
        scene = ROOT / f"data/tless/bop/test_primesense/{case['scene_id']:06d}"
        paths += [scene / "scene_camera.json", scene / "scene_gt.json",
                  scene / f"depth/{case['image_id']:06d}.png",
                  scene / f"mask_visib/{case['image_id']:06d}_{case['gt_index']:06d}.png",
                  ROOT / f"data/tless/bop/models_cad/obj_{case['object_id']:06d}.ply",
                  ROOT / f"data/tless/bop/models_eval/obj_{case['object_id']:06d}.ply"]
    missing = [path.relative_to(ROOT).as_posix() for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing local inputs; no evaluation launched: {missing}")
    proposals = {method: {str(seed): [item.model_dump() for item in
                  (deterministic_proposals(seed) if method == "deterministic" else random_proposals(seed))]
                  for seed in SEEDS} for method in METHODS}
    schedule = []
    for case in selected:
        for seed in SEEDS:
            for index in range(SEARCH_BUDGET):
                order = METHODS if (index + SEEDS.index(seed)) % 2 == 0 else tuple(reversed(METHODS))
                for method in order:
                    schedule.append({"case": case, "method": method, "search_seed": seed,
                                     "evaluation_index": index + 1, "proposal": proposals[method][str(seed)][index]})
    out = ROOT / "artifacts" / ("development_search_pilot_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex[:8])
    out.mkdir(exist_ok=False)
    manifest = {"selection": "First five distinct object IDs in existing development manifest order; no result files or outcomes consulted.", "cases": selected, "heldout200_case_overlap": 0}
    write(out / "selected_manifest.json", manifest)
    source = inventory(paths)
    source["selected_manifest.json"] = {"sha256": digest(out / "selected_manifest.json"), "bytes": (out / "selected_manifest.json").stat().st_size}
    plan = {"prepared_at_utc": datetime.now(timezone.utc).isoformat(), "case_ids": [c["case_id"] for c in selected],
            "cases": selected, "seeds": list(SEEDS), "evaluations_per_case_seed_method": SEARCH_BUDGET,
            "planned_candidate_slots": len(schedule), "shared_baseline_calls": 5, "extra_replay_calls_max": 1,
            "export_calls_max": 1, "total_wall_budget_seconds": TOTAL_SECONDS, "outer_per_call_seconds": CALL_SECONDS,
            "evaluator_timeout_seconds": CALL_SECONDS, "initialization_and_scoring": config,
            "budget_accounting": "Every scheduled proposal consumes one slot, including invalids, timeouts and processing failures; no retries, no early-stop on success. Interleaved round order is fixed before outcomes.",
            "reserve_seconds_for_export_replay_report": RESERVE_SECONDS,
            "policy_feedback": "Local deterministic and random proposals are fixed before evaluation and consume no feedback. Optional live policy is not invoked; its existing feedback excludes GT. GT poses used only for offline evaluator labels and retrospective representative selection.",
            "severity": "No existing validated scalar severity measure. Report supplied noise_std_m (also mm) and point_dropout_fraction separately; do not rank mixtures by an invented scalar.",
            "proposals": proposals, "schedule": schedule, "file_inventory": source,
            "python": sys.version, "dependency_versions": {name: version(name) for name in ("numpy", "scipy", "Pillow", "pydantic")},
            "thread_environment": {name: "1" for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
            "base_commit": subprocess.check_output(["git", "--no-optional-locks", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "original_historical_source_identity": "Not established by this new pilot provenance.",
            "commands": [".\\.venv\\Scripts\\python.exe -B scripts/development_search_pilot.py --prepare",
                         f".\\.venv\\Scripts\\python.exe -B scripts/development_search_pilot.py --run {out.relative_to(ROOT).as_posix()}"]}
    write(out / "plan.json", plan)
    print(json.dumps({"directory": out.relative_to(ROOT).as_posix(), "case_ids": plan["case_ids"], "planned_candidates": len(schedule), "baseline_calls": 5, "hard_budget_seconds": TOTAL_SECONDS}, indent=2))


def worker():
    request = json.load(sys.stdin)
    # Never invoke compare_search_strategies(), which loads .env and may call a remote model.
    if request["operation"] == "evaluate":
        from autoframe3d.tless_benchmark import evaluate_case
        result = evaluate_case(request["case"], group=request["group"],
                               perturbation_override=request.get("proposal"), timeout_seconds=CALL_SECONDS)
    elif request["operation"] == "export":
        from autoframe3d.tless_cases import export_case_bundle
        result = {"bundle": str(export_case_bundle(request["record"], Path(request["output"])).relative_to(ROOT))}
    elif request["operation"] == "replay":
        import zipfile
        from autoframe3d.tless_cases import replay_record
        with zipfile.ZipFile(request["bundle"]) as archive:
            record = json.loads(archive.read("case.json"))["case_result"]
        result = replay_record(record)
    else:
        raise ValueError("Unsupported worker operation")
    print(json.dumps(result, allow_nan=False))


def isolated_call(request, deadline):
    started = time.monotonic()
    remaining = deadline - started
    if remaining <= 0:
        raise TimeoutError("Experiment deadline reached before call")
    environment = os.environ.copy()
    environment.update({name: "1" for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")})
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker"]
    try:
        result = subprocess.run(command, input=json.dumps(request), text=True, capture_output=True,
                                timeout=min(CALL_SECONDS, remaining), cwd=ROOT, env=environment,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if result.returncode:
            # Source/dataset paths are local; do not dump environment or credentials.
            actual = {"status": "processing_failure", "error": "Worker failed", "worker_exit_code": result.returncode,
                      "worker_stderr_tail": result.stderr[-2000:]}
        else:
            actual = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        # subprocess.run kills and reaps the child: a blocked NumPy/IO call cannot stall the pilot indefinitely.
        actual = {"status": "timeout", "error": "Hard wall-clock worker timeout; child killed and reaped"}
    actual["outer_call_seconds"] = time.monotonic() - started
    return actual


def run(out):
    from pydantic import ValidationError
    from autoframe3d.tless_search import TlessPerturbation
    started = time.monotonic()
    deadline = started + TOTAL_SECONDS
    plan = json.loads((out / "plan.json").read_text())
    assert not (out / "results.jsonl").exists(), "Refusing to rerun or overwrite an existing pilot"
    for relative, expected in plan["file_inventory"].items():
        path = out / relative if relative == "selected_manifest.json" else ROOT / relative
        assert digest(path) == expected["sha256"], f"Predeclared input/source changed: {relative}"
    baselines = []
    rows = []
    calls = []
    with (out / "results.jsonl").open("x", encoding="utf-8") as file:
        def record(row):
            file.write(json.dumps(row, allow_nan=False) + "\n")
            file.flush()
        for case in plan["cases"]:
            result = isolated_call({"operation": "evaluate", "case": case, "group": "original"}, deadline)
            result.update(case)
            result["role"] = "shared_baseline"
            baselines.append(result)
            calls.append({"operation": "baseline_evaluate", "case_id": case["case_id"], "wall_seconds": result["outer_call_seconds"], "status": result.get("status")})
            record(result)
            print(json.dumps({"baseline": case["case_id"], "category": result.get("category"), "status": result["status"]}), flush=True)
        for slot in plan["schedule"]:
            if deadline - time.monotonic() < RESERVE_SECONDS + CALL_SECONDS:
                break
            try:
                TlessPerturbation.model_validate(slot["proposal"])
            except ValidationError:
                result = {"status": "invalid_proposal", "error": "Proposal violates shared existing schema", "outer_call_seconds": 0.}
            else:
                result = isolated_call({"operation": "evaluate", "case": slot["case"], "group": "perturbed", "proposal": slot["proposal"]}, deadline)
                calls.append({"operation": "candidate_evaluate", "case_id": slot["case"]["case_id"], "method": slot["method"], "search_seed": slot["search_seed"], "evaluation_index": slot["evaluation_index"], "wall_seconds": result["outer_call_seconds"], "status": result.get("status")})
            result.update({key: slot[key] for key in ("method", "search_seed", "evaluation_index", "proposal")})
            result.update(slot["case"])
            result["role"] = "candidate"
            result["noise_std_mm"] = slot["proposal"]["noise_std_m"] * 1000
            result["dropout_fraction"] = slot["proposal"]["point_dropout_fraction"]
            rows.append(result)
            record(result)
            if len(rows) % 8 == 0:
                print(json.dumps({"candidate_slots": len(rows), "planned": len(plan["schedule"]), "elapsed_seconds": time.monotonic() - started}), flush=True)
    baseline_map = {row["case_id"]: row for row in baselines}
    discoveries = [row for row in rows if row.get("category") == "accepted_but_wrong"]
    new_failures = [row for row in discoveries if baseline_map[row["case_id"]].get("correct") is True]
    representative = (new_failures or discoveries or [None])[0]
    replay = {"status": "no_discovery", "extra_verification_calls": 0}
    if representative is not None and deadline - time.monotonic() >= 2 * CALL_SECONDS:
        write(out / "representative_case.json", representative)
        bundle = out / "representative_case.zip"
        export = isolated_call({"operation": "export", "record": representative, "output": str(bundle)}, deadline)
        calls.append({"operation": "export_no_registration", "wall_seconds": export["outer_call_seconds"], "status": export.get("status", "completed")})
        write(out / "export_result.json", export)
        if bundle.exists() and export.get("status") not in {"timeout", "processing_failure"}:
            replay = isolated_call({"operation": "replay", "bundle": str(bundle)}, deadline)
            calls.append({"operation": "extra_replay_evaluate", "wall_seconds": replay["outer_call_seconds"], "status": replay.get("status", "completed")})
            replay["extra_verification_calls"] = 1
            replay["representative_selection"] = "First correct-baseline discovery in predeclared schedule, otherwise first discovery (rediscovery disclosed). No extra candidate attempts."
        else:
            replay = {"status": "export_failed", "extra_verification_calls": 0}
    elif representative is not None:
        replay = {"status": "insufficient_reserved_time", "extra_verification_calls": 0}
    write(out / "replay_result.json", replay)
    runs = []
    method_summaries = []
    for method in METHODS:
        method_rows = [row for row in rows if row["method"] == method]
        for case in plan["cases"]:
            for seed in SEEDS:
                candidates = [row for row in method_rows if row["case_id"] == case["case_id"] and row["search_seed"] == seed]
                first = next((row["evaluation_index"] for row in candidates if row.get("category") == "accepted_but_wrong"), None)
                runs.append({"method": method, "case_id": case["case_id"], "seed": seed, "baseline_category": baseline_map[case["case_id"]].get("category"), "baseline_correct": baseline_map[case["case_id"]].get("correct"), "candidate_slots": len(candidates), "discovery": first is not None, "evaluations_to_first_discovery": first, "no_discovery": first is None, "budget_complete": len(candidates) == plan["evaluations_per_case_seed_method"], "correct_to_accepted_but_wrong": first is not None and baseline_map[case["case_id"]].get("correct") is True, "status_counts": dict(Counter(row["status"] for row in candidates)), "wall_seconds": sum(row["outer_call_seconds"] for row in candidates)})
        arm_runs = [item for item in runs if item["method"] == method]
        method_summaries.append({"method": method, "candidate_slots": len(method_rows), "actual_evaluator_calls": sum(item["operation"] == "candidate_evaluate" and item["method"] == method for item in calls), "valid_proposals": sum(row["status"] != "invalid_proposal" for row in method_rows), "status_counts": dict(Counter(row["status"] for row in method_rows)), "discovered_case_seed_pairs": sum(item["discovery"] for item in arm_runs), "total_case_seed_pairs": 15, "correct_to_wrong_case_seed_pairs": sum(item["correct_to_accepted_but_wrong"] for item in arm_runs), "already_wrong_case_seed_rediscoveries": sum(item["discovery"] and item["baseline_category"] == "accepted_but_wrong" for item in arm_runs), "failure_candidate_count": sum(row.get("category") == "accepted_but_wrong" for row in method_rows), "discoveries_at_fixed_budgets": {str(b): sum(item["evaluations_to_first_discovery"] is not None and item["evaluations_to_first_discovery"] <= b for item in arm_runs) for b in range(1, 5)}, "no_discovery_case_seed_pairs": sum(item["no_discovery"] for item in arm_runs), "wall_seconds": sum(row["outer_call_seconds"] for row in method_rows)})
    hashes_unchanged = all(digest(out / relative if relative == "selected_manifest.json" else ROOT / relative) == expected["sha256"] for relative, expected in plan["file_inventory"].items())
    summary = {"elapsed_seconds_including_baselines_export_replay": time.monotonic() - started, "total_budget_seconds": TOTAL_SECONDS,
               "complete": len(rows) == len(plan["schedule"]), "skipped_candidate_slots_due_to_deadline": len(plan["schedule"]) - len(rows),
               "baseline_results": baselines, "baseline_correct_cases": sum(row.get("correct") is True for row in baselines),
               "baseline_accepted_but_wrong_cases": sum(row.get("category") == "accepted_but_wrong" for row in baselines),
               "methods": method_summaries, "case_seed_results": runs, "call_ledger": calls,
               "replay": {key: value for key, value in replay.items() if key != "actual"},
               "source_and_input_hashes_unchanged": hashes_unchanged, "plan_sha256": digest(out / "plan.json"),
               "model_calls": 0, "heldout_evaluator_calls": 0,
               "interpretation": "Pilot only. The deterministic arm is a fixed schedule, not an adaptive agent. Baseline failures impose a discovery ceiling; rediscovery is not search improvement. No tuning/rerun after outcomes."}
    write(out / "summary.json", summary)
    with (out / "case_seed_results.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(runs[0])); writer.writeheader(); writer.writerows(runs)
    table = ["# Development-only failure-search pilot", "", "Predeclared five cases, seeds 101/202/303, four existing proposals per method/case/seed. No remote proposals or GT feedback to either policy. GT-provided instance masks and GT-dependent offline correctness labels are used by the evaluator.", "", "| Method | Candidate slots | Discovered case-seed pairs | Correct-to-wrong pairs | Already-wrong rediscoveries | Wall seconds |", "|---|---:|---:|---:|---:|---:|"]
    for method in method_summaries:
        table.append(f"| {method['method']} | {method['candidate_slots']} | {method['discovered_case_seed_pairs']}/15 | {method['correct_to_wrong_case_seed_pairs']} | {method['already_wrong_case_seed_rediscoveries']} | {method['wall_seconds']:.2f} |")
    table += ["", "## Shared unperturbed baselines", "", "| Case | Category | MSSD/D |", "|---|---|---:|"]
    for row in baselines:
        table.append(f"| {row['case_id']} | {row.get('category', row['status'])} | {row.get('pose_metrics', {}).get('mssd_over_diameter')} |")
    table += ["", "Per-case/seed first-discovery indices, explicit null/no-discovery indicators and validity/timeout/failure counts are in case_seed_results.csv and summary.json. Candidate parameters, pose estimates, scoring and runtime are in results.jsonl. Noise standard deviation and dropout fraction are reported separately; no validated scalar severity exists.", "", f"Total execution wall time including shared baselines, export and one separate replay verification: {summary['elapsed_seconds_including_baselines_export_replay']:.2f} seconds (hard budget 900 seconds). Source and data hashes unchanged: {hashes_unchanged}. Plan/source/config/manifests/seeds/dependencies/exact command in plan.json. Original held-out/source identity is not established by this provenance.", "", "Representative selection prioritizes a correct-baseline transition, otherwise the first valid failure in the fixed schedule. Replay reloads saved ZIP parameters and performs one extra evaluator call, excluded from candidate comparison. See replay_result.json and representative_case.zip when present.", "", "No claim of deployable ground-truth-free failure detection, training need, or generalization follows from this pilot."]
    (out / "REPORT.md").write_text("\n".join(table) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items()
                      if key not in {"call_ledger", "case_seed_results", "baseline_results"}}, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--run", type=Path)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        worker()
    elif args.prepare:
        prepare()
    elif args.run:
        run(args.run.resolve())
    else:
        parser.error("Use --prepare, --run DIRECTORY, or --worker")
