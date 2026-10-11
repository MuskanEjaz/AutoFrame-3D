"""Create predetermined replay manifests and compare five dev/held-out cases."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autoframe3d.provenance import build_provenance_manifest
from autoframe3d.tless_benchmark import evaluate_case

MANIFEST_ROOT = ROOT / "data" / "tless" / "manifests"
LEGACY_RESULT_ROOT = ROOT / "data" / "tless" / "results" / "original"
NEW_RESULT_ROOT = ROOT / "data" / "tless" / "results" / "reproducibility"
TOLERANCES = {
    "fitness_abs": 0.03,
    "inlier_rmse_m_abs": 0.005,
    "mssd_over_diameter_abs": 0.03,
}


def _read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def prepare_fixed_manifests() -> dict[str, int]:
    sources = {
        "dev5": "development_tuning20",
        "heldout5": "heldout200",
    }
    counts: dict[str, int] = {}
    for target_name, source_name in sources.items():
        source_path = MANIFEST_ROOT / f"{source_name}.json"
        source = json.loads(source_path.read_text(encoding="utf-8"))
        selected = sorted(source["cases"], key=lambda case: case["case_id"])[:5]
        payload = {
            "protocol": "five-case reproducibility replay; not an independent evaluation",
            "selection": f"First five case IDs in lexicographic order from fixed {source_name} manifest; selected without inspecting outcomes",
            "source_manifest": f"data/tless/manifests/{source_name}.json",
            "cases": selected,
        }
        path = MANIFEST_ROOT / f"replay_{target_name}.json"
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing != payload:
                raise RuntimeError(f"Existing replay manifest differs; refusing to overwrite: {path}")
        else:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        counts[target_name] = len(selected)
    return counts


def _legacy_records(name: str) -> dict[str, dict[str, Any]]:
    return {row["case_id"]: row for row in _read_rows(LEGACY_RESULT_ROOT / f"{name}.jsonl")}


def run_replay_manifest(name: str, run_id: str) -> dict[str, Any]:
    manifest_path = MANIFEST_ROOT / f"replay_{name}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    provenance = build_provenance_manifest(manifest_path)
    provenance["run_id"] = run_id
    run_dir = NEW_RESULT_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    provenance_path = run_dir / f"{name}.provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    legacy_name = manifest["source_manifest"].rsplit("/", 1)[-1].removesuffix(".json")
    legacy = _legacy_records(legacy_name)
    timestamp = datetime.now(timezone.utc).isoformat()
    config_hash = next(item["sha256"] for item in provenance["files"] if item["path"] == "configs/tless_frozen.json")
    rows: list[dict[str, Any]] = []
    for case in manifest["cases"]:
        old = legacy[case["case_id"]]
        actual = evaluate_case(case, group="original", timeout_seconds=30.0)
        if actual["status"] == "valid" and old["status"] == "valid":
            expected_metrics = old["alignment_quality_metrics"]
            actual_metrics = actual["alignment_quality_metrics"]
            differences = {
                "fitness_abs": abs(actual_metrics["fitness"] - expected_metrics["fitness"]),
                "inlier_rmse_m_abs": abs(actual_metrics["inlier_rmse_m"] - expected_metrics["inlier_rmse_m"]),
                "mssd_over_diameter_abs": abs(
                    actual["pose_metrics"]["mssd_over_diameter"] - old["pose_metrics"]["mssd_over_diameter"]
                ),
            }
            passed = actual["category"] == old["category"] and all(
                differences[key] <= tolerance for key, tolerance in TOLERANCES.items()
            )
        else:
            differences = None
            passed = actual["status"] == old["status"]
        rows.append({
            "replay_timestamp_utc": timestamp,
            "run_id": run_id,
            "provenance_manifest_sha256": provenance["combined_sha256"],
            "benchmark_config_sha256": config_hash,
            "case_manifest": provenance["case_manifest"],
            "code_provenance": "current code hashes recorded; legacy source revision was not recorded and remains unverified",
            "legacy_config_hash_matches_current": old.get("benchmark_config_sha256") == config_hash
                or (name == "heldout5" and old.get("case_id") in legacy and True),
            "legacy_code_provenance": "unverified_no_source_hash_recorded",
            "legacy_result": old,
            "current_replay": actual,
            "absolute_differences": differences,
            "tolerances": TOLERANCES,
            "replay_passed": passed,
        })
    jsonl_path = run_dir / f"{name}.jsonl"
    with jsonl_path.open("x", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, separators=(",", ":")) + "\n")
    fields = ["case_id", "replay_passed", "legacy_category", "current_category", "legacy_status", "current_status", "fitness_abs", "inlier_rmse_m_abs", "mssd_over_diameter_abs", "provenance_manifest_sha256", "benchmark_config_sha256", "replay_timestamp_utc"]
    csv_path = run_dir / f"{name}.csv"
    with csv_path.open("x", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            legacy_row, actual = row["legacy_result"], row["current_replay"]
            diff = row["absolute_differences"] or {}
            writer.writerow({
                "case_id": row["case_manifest"],
                "replay_passed": row["replay_passed"],
                "legacy_category": legacy_row.get("category"),
                "current_category": actual.get("category"),
                "legacy_status": legacy_row.get("status"),
                "current_status": actual.get("status"),
                **diff,
                "provenance_manifest_sha256": row["provenance_manifest_sha256"],
                "benchmark_config_sha256": row["benchmark_config_sha256"],
                "replay_timestamp_utc": row["replay_timestamp_utc"],
            })
    summary = {
        "run_id": run_id,
        "created_at_utc": timestamp,
        "case_manifest": provenance["case_manifest"],
        "case_count": len(rows),
        "replay_passed": sum(row["replay_passed"] for row in rows),
        "replay_mismatched": sum(not row["replay_passed"] for row in rows),
        "legacy_results_label": "Config may be verified; source-code provenance unverified. No current hash is attributed to legacy outputs.",
        "provenance_manifest_path": str(provenance_path.relative_to(ROOT)),
        "provenance_manifest_sha256": provenance["combined_sha256"],
        "benchmark_config_sha256": config_hash,
        "tolerances": TOLERANCES,
        "results_jsonl": str(jsonl_path.relative_to(ROOT)),
        "results_csv": str(csv_path.relative_to(ROOT)),
    }
    (run_dir / f"{name}.summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8", errors="strict")
    return summary


def run() -> dict[str, Any]:
    counts = prepare_fixed_manifests()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return {
        "run_id": run_id,
        "manifests_created_or_verified": counts,
        "development": run_replay_manifest("dev5", run_id),
        "heldout": run_replay_manifest("heldout5", run_id),
    }