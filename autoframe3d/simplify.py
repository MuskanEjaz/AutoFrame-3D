"""Greedy bounded simplification that keeps the measured failure condition."""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import Callable

from autoframe3d.experiment import ExperimentConfig, evaluate
from autoframe3d.campaign import summarize


def simplify_failure(
    failure: dict[str, object],
    budget: int = 8,
    on_trial: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, object]:
    if failure.get("classification") != "accepted_but_wrong":
        raise ValueError("simplification requires an accepted-but-wrong result")
    if not 1 <= budget <= 8:
        raise ValueError("simplification budget must be between 1 and 8")
    current = ExperimentConfig(**failure["config"])
    attempts = 0
    accepted_changes: list[dict[str, object]] = []
    candidates: list[tuple[str, object]] = [
        ("noise_std_m", 0.0),
        ("background_points", 0),
        ("visibility", "all"),
        ("yaw_deg", 0.0),
        ("translation_m", (0.0, 0.0, 0.0)),
    ]
    best_result = failure
    for name, value in candidates:
        if attempts >= budget:
            break
        if getattr(current, name) == value:
            continue
        candidate = replace(current, **{name: value})
        measured = evaluate(candidate)
        attempts += 1
        summary = summarize(measured)
        event = {
            "kind": "simplification_trial",
            "attempt": attempts,
            "removed_or_reduced": name,
            "value": value,
            **summary,
        }
        if on_trial is not None:
            on_trial(event)
        if summary["classification"] == "accepted_but_wrong":
            current = candidate
            best_result = summary
            accepted_changes.append({"parameter": name, "value": value})
    return {
        "result": best_result,
        "config": asdict(current),
        "evaluations": attempts,
        "budget": budget,
        "simplifications_kept": accepted_changes,
        "claim": "Simplest case found within this bounded greedy procedure; not a proof of minimality.",
    }