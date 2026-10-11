"""Equal-budget T-LESS perturbation search comparison on fixed dev starts."""

from __future__ import annotations

import csv
import json
import os
import random
import os
import urllib.request
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from autoframe3d.agent import DEFAULT_MODEL, NEBIUS_BASE_URL
from autoframe3d.tless_benchmark import RESULT_ROOT, evaluate_case

ROOT = Path(__file__).resolve().parent.parent
STARTS_PATH = ROOT / "data" / "tless" / "manifests" / "search_start.json"
OUTPUT_ROOT = ROOT / "data" / "tless" / "search"
SEARCH_BUDGET = 4
REGISTRATION_STARTS_PER_EVALUATION = 6


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


class TlessPerturbation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    noise_std_m: float = Field(ge=0.0, le=0.005)
    point_dropout_fraction: float = Field(ge=0.0, le=0.2)
    seed: int = Field(ge=0, le=2_000_000)


def deterministic_proposals(seed: int) -> list[TlessPerturbation]:
    points = ((0.0, 0.0), (0.001, 0.05), (0.003, 0.10), (0.005, 0.20))
    return [
        TlessPerturbation(noise_std_m=noise, point_dropout_fraction=dropout, seed=seed + index)
        for index, (noise, dropout) in enumerate(points)
    ]


def random_proposals(seed: int) -> list[TlessPerturbation]:
    rng = random.Random(seed)
    return [
        TlessPerturbation(
            noise_std_m=rng.uniform(0.0, 0.005),
            point_dropout_fraction=rng.uniform(0.0, 0.2),
            seed=rng.randrange(0, 2_000_001),
        )
        for _ in range(SEARCH_BUDGET)
    ]


def live_proposal(
    prior_feedback: list[dict[str, Any]],
    *,
    model_calls_used: int,
) -> tuple[TlessPerturbation, dict[str, Any]]:
    api_key = os.environ.get("NEBIUS_API_KEY")
    if not api_key:
        raise RuntimeError("NEBIUS_API_KEY is not configured")
    if model_calls_used >= SEARCH_BUDGET:
        raise RuntimeError("T-LESS live proposal call budget exhausted")
    model = os.environ.get("NEBIUS_MODEL", DEFAULT_MODEL)
    schema = TlessPerturbation.model_json_schema()
    schema["additionalProperties"] = False
    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 160,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "tless_perturbation", "strict": True, "schema": schema},
        },
        "messages": [
            {
                "role": "system",
                "content": (
                    "Propose one bounded scan perturbation to stress CAD-to-depth registration. "
                    "Return only the required JSON object. You may use only observed geometric "
                    "alignment fitness/RMSE and prior perturbation parameters. Do not request, infer, "
                    "or use ground-truth pose, MSSD, correctness labels, or case pose errors."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "previous_geometry_only_measurements": prior_feedback,
                    "allowed_bounds": {
                        "noise_std_m": [0.0, 0.005],
                        "point_dropout_fraction": [0.0, 0.2],
                        "seed": [0, 2_000_000],
                    },
                }),
            },
        ],
    }
    request = urllib.request.Request(
        NEBIUS_BASE_URL + "chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        completion = json.loads(response.read().decode("utf-8"))
    proposal = TlessPerturbation.model_validate_json(completion["choices"][0]["message"]["content"])
    usage = completion.get("usage", {})
    return proposal, {
        "model": model,
        "usage": {key: usage[key] for key in ("prompt_tokens", "completion_tokens", "total_tokens") if key in usage},
    }


def _feedback(result: dict[str, Any], proposal: TlessPerturbation) -> dict[str, Any]:
    """Only geometric metrics and action parameters cross back into the search policy."""
    metrics = result.get("alignment_quality_metrics", {})
    return {
        "perturbation": proposal.model_dump(),
        "status": result["status"],
        "fitness": metrics.get("fitness"),
        "inlier_rmse_m": metrics.get("inlier_rmse_m"),
    }


def _run_arm(
    strategy: str,
    starts: list[dict[str, int]],
    proposals_by_start: dict[str, list[TlessPerturbation]],
    *,
    model_metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in starts:
        for evaluation_index, proposal in enumerate(proposals_by_start[case["case_id"]], start=1):
            result = evaluate_case(
                case,
                group="perturbed",
                perturbation_override=proposal.model_dump(),
                timeout_seconds=30.0,
            )
            rows.append({
                **result,
                "strategy": strategy,
                "evaluation_index": evaluation_index,
                "search_budget": SEARCH_BUDGET,
                "registration_starts_per_evaluation": REGISTRATION_STARTS_PER_EVALUATION,
                "proposal": proposal.model_dump(),
                "search_uses_ground_truth_feedback": False,
                "model_metadata": model_metadata,
            })
    return rows


def compare_search_strategies() -> dict[str, Any]:
    _load_dotenv()
    start_manifest = json.loads(STARTS_PATH.read_text(encoding="utf-8"))
    starts = start_manifest["cases"]
    if not starts:
        raise ValueError("The fixed T-LESS search-start manifest is empty")
    random_by_start = {case["case_id"]: random_proposals(20260928) for case in starts}
    deterministic_by_start = {
        case["case_id"]: deterministic_proposals(260_928 + int(case["image_id"]))
        for case in starts
    }
    arms = {
        "deterministic": _run_arm("deterministic", starts, deterministic_by_start),
        "seeded_random": _run_arm("seeded_random", starts, random_by_start),
    }
    key_configured = bool(os.environ.get("NEBIUS_API_KEY"))
    model_calls = 0
    model_usage: list[dict[str, Any]] = []
    if key_configured:
        live_rows: list[dict[str, Any]] = []
        for case in starts:
            feedback: list[dict[str, Any]] = []
            proposals: list[TlessPerturbation] = []
            metadata: dict[str, Any] = {}
            for _ in range(SEARCH_BUDGET):
                proposal, metadata = live_proposal(feedback, model_calls_used=model_calls)
                model_calls += 1
                model_usage.append(metadata)
                proposals.append(proposal)
                candidate = evaluate_case(
                    case, group="perturbed", perturbation_override=proposal.model_dump(), timeout_seconds=30.0,
                )
                feedback.append(_feedback(candidate, proposal))
                live_rows.append({
                    **candidate, "strategy": "live_nemotron", "evaluation_index": len(proposals),
                    "search_budget": SEARCH_BUDGET,
                    "registration_starts_per_evaluation": REGISTRATION_STARTS_PER_EVALUATION,
                    "proposal": proposal.model_dump(), "search_uses_ground_truth_feedback": False,
                    "model_metadata": metadata,
                })
        arms["live_nemotron"] = live_rows
    else:
        arms["live_nemotron"] = []

    summary: dict[str, Any] = {
        "label": "Development-only search comparison on the same fixed start case(s); not a model training run.",
        "start_manifest": str(STARTS_PATH.relative_to(ROOT)),
        "starting_case_ids": [case["case_id"] for case in starts],
        "starting_case_count": len(starts),
        "search_evaluations_per_start_per_arm": SEARCH_BUDGET,
        "registration_starts_per_evaluation": REGISTRATION_STARTS_PER_EVALUATION,
        "total_registration_starts_per_arm": len(starts) * SEARCH_BUDGET * REGISTRATION_STARTS_PER_EVALUATION,
        "perturbation_bounds": {"noise_std_m": [0.0, 0.005], "point_dropout_fraction": [0.0, 0.2]},
        "model_calls": model_calls,
        "model_usage": model_usage,
        "live_status": "pending_no_api_key" if not key_configured else "completed",
        "arms": {},
    }
    for name, rows in arms.items():
        if not rows:
            summary["arms"][name] = {"status": "pending", "discovery_rate": None, "evaluations_to_first_failure": None}
            continue
        start_summaries: list[dict[str, Any]] = []
        for case in starts:
            case_rows = [row for row in rows if row["case_id"] == case["case_id"]]
            first = next((row["evaluation_index"] for row in case_rows if row.get("category") == "accepted_but_wrong"), None)
            start_summaries.append({
                "case_id": case["case_id"],
                "discovered_failure": first is not None,
                "evaluations_to_first_failure": first,
                "evaluations": len(case_rows),
                "runtime_seconds": sum(row["runtime_seconds"] for row in case_rows),
            })
        failures = sum(item["discovered_failure"] for item in start_summaries)
        firsts = [item["evaluations_to_first_failure"] for item in start_summaries if item["evaluations_to_first_failure"] is not None]
        summary["arms"][name] = {
            "status": "completed",
            "discovered_start_cases": failures,
            "discovery_rate": failures / len(starts),
            "mean_evaluations_to_first_failure": sum(firsts) / len(firsts) if firsts else None,
            "evaluations_to_first_failure_by_start": [item["evaluations_to_first_failure"] for item in start_summaries],
            "mean_runtime_seconds_per_start": sum(item["runtime_seconds"] for item in start_summaries) / len(starts),
            "start_results": start_summaries,
        }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "search_comparison.json").write_text(json.dumps({"summary": summary, "results": arms}, indent=2), encoding="utf-8")
    with (OUTPUT_ROOT / "search_comparison.csv").open("w", newline="", encoding="utf-8") as file:
        fields = ["strategy", "case_id", "evaluation_index", "status", "category", "noise_std_m", "point_dropout_fraction", "fitness", "inlier_rmse_m", "mssd_over_diameter", "runtime_seconds", "model_calls"]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for name, rows in arms.items():
            for row in rows:
                metrics, pose = row.get("alignment_quality_metrics", {}), row.get("pose_metrics", {})
                writer.writerow({
                    "strategy": name, "case_id": row["case_id"],
                    "evaluation_index": row["evaluation_index"], "status": row["status"],
                    "category": row.get("category"),
                    "noise_std_m": row["proposal"]["noise_std_m"],
                    "point_dropout_fraction": row["proposal"]["point_dropout_fraction"],
                    "fitness": metrics.get("fitness"), "inlier_rmse_m": metrics.get("inlier_rmse_m"),
                    "mssd_over_diameter": pose.get("mssd_over_diameter"),
                    "runtime_seconds": row["runtime_seconds"], "model_calls": model_calls if name == "live_nemotron" else 0,
                })
    return summary