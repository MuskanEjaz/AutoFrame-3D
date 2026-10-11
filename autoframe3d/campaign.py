"""Bounded campaign execution and equal-budget seeded random comparison."""

from __future__ import annotations

import random
import threading
from dataclasses import asdict
from typing import Callable

from autoframe3d.agent import MAX_EVALUATIONS, MAX_MODEL_CALLS, propose_next
from autoframe3d.experiment import ExperimentConfig, deterministic_configs, evaluate


def summarize(result: dict[str, object]) -> dict[str, object]:
    return {
        key: result[key]
        for key in (
            "config",
            "thresholds",
            "ground_truth_T_object_from_scan",
            "estimated_T_object_from_scan",
            "alignment_quality_metrics",
            "pose_errors",
            "classification",
            "initial_yaw_deg",
        )
    }


def _random_configs(seed: int, count: int) -> list[ExperimentConfig]:
    rng = random.Random(seed)
    return [
        ExperimentConfig(
            seed=rng.randrange(0, 1_000_000),
            visibility=rng.choice(("top", "front", "all")),
            yaw_deg=rng.uniform(-180.0, 180.0),
            noise_std_m=rng.uniform(0.0, 0.005),
            background_points=rng.randrange(0, 129),
        )
        for _ in range(count)
    ]


def run_campaign(
    budget: int = 12,
    mode: str = "auto",
    stop_event: threading.Event | None = None,
    on_event: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, object]:
    """Run agent and random arms with equal budgets and at most 12 evaluations total."""
    if not 2 <= budget <= MAX_EVALUATIONS or budget % 2:
        raise ValueError("budget must be an even number between 2 and 12")
    if mode not in {"auto", "deterministic", "live_ai"}:
        raise ValueError("mode must be auto, deterministic, or live_ai")
    arm_budget = budget // 2
    agent_configs = deterministic_configs(arm_budget)
    actions: list[dict[str, object]] = []
    events: list[dict[str, object]] = []
    results: dict[str, list[dict[str, object]]] = {"agent": [], "random": []}
    model_calls = 0
    model_details: dict[str, object] = {}
    requested_live = mode == "live_ai" or (mode == "auto" and bool(__import__("os").environ.get("NEBIUS_API_KEY")))
    campaign_mode = "ai_live" if requested_live else "deterministic"
    use_model = requested_live

    def emit(event: dict[str, object]) -> None:
        events.append(event)
        if on_event is not None:
            on_event(event)

    for arm_name in ("agent", "random"):
        if arm_name == "random":
            configs = _random_configs(20260927, arm_budget)
        else:
            configs = agent_configs
        for index in range(arm_budget):
            if stop_event is not None and stop_event.is_set():
                break
            if arm_name == "agent" and use_model and index > 0 and model_calls < MAX_MODEL_CALLS:
                try:
                    proposal, metadata = propose_next(results["agent"], model_calls)
                    configs[index] = proposal.to_config()
                    model_calls += 1
                    model_details = metadata
                    emit({"kind": "model_proposal", "number": model_calls, "proposal": proposal.model_dump(), **metadata})
                except Exception as error:
                    use_model = False
                    campaign_mode = "deterministic_fallback"
                    warning = f"Model proposal unavailable ({type(error).__name__}); deterministic proposals used for remaining evaluations."
                    emit({"kind": "agent_fallback", "message": warning})
            config = configs[index]
            emit({"kind": "experiment_started", "arm": arm_name, "index": index + 1, "parameters": asdict(config)})
            measured = evaluate(config)
            measured_summary = summarize(measured)
            results[arm_name].append(measured_summary)
            emit({"kind": "experiment_measured", "arm": arm_name, "index": index + 1, **measured_summary})
        if stop_event is not None and stop_event.is_set():
            break
    action_summary = {
        "agent_evaluations": len(results["agent"]),
        "random_evaluations": len(results["random"]),
        "registration_evaluations_total": len(results["agent"]) + len(results["random"]),
        "model_calls": model_calls,
        "model": model_details.get("model") if model_details else None,
        "agent_failures": sum(item["classification"] == "accepted_but_wrong" for item in results["agent"]),
        "random_failures": sum(item["classification"] == "accepted_but_wrong" for item in results["random"]),
        "budget_per_arm": arm_budget,
    }
    actions.append(action_summary)
    return {
        "mode": campaign_mode,
        "results": results,
        "events": events,
        "actions": actions,
        "summary": action_summary,
        "stopped": bool(stop_event and stop_event.is_set()),
    }