"""Bounded experiment proposals with an optional server-side Nebius model."""

from __future__ import annotations

import json
import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autoframe3d.experiment import ExperimentConfig
from autoframe3d.nebius import DEFAULT_MODEL, NEBIUS_BASE_URL, chat_completion

MAX_EVALUATIONS = 12
MAX_MODEL_CALLS = 4


class ExperimentProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    seed: int = Field(ge=0, le=1_000_000)
    visibility: Literal["top", "front", "all"]
    yaw_deg: float = Field(ge=-180.0, le=180.0)
    noise_std_m: float = Field(ge=0.0, le=0.005)
    background_points: int = Field(ge=0, le=128)

    def to_config(self) -> ExperimentConfig:
        return ExperimentConfig(
            seed=self.seed,
            visibility=self.visibility,
            yaw_deg=self.yaw_deg,
            noise_std_m=self.noise_std_m,
            background_points=self.background_points,
        )


def _proposal_schema() -> dict[str, object]:
    schema = ExperimentProposal.model_json_schema()
    schema["additionalProperties"] = False
    return {
        "type": "json_schema",
        "json_schema": {"name": "experiment_proposal", "strict": True, "schema": schema},
    }


def propose_next(
    measured_results: list[dict[str, object]],
    model_calls_used: int,
) -> tuple[ExperimentProposal, dict[str, object]]:
    """Request one strictly validated proposal, bounded by four calls per campaign."""
    api_key = os.environ.get("NEBIUS_API_KEY")
    if not api_key:
        raise RuntimeError("NEBIUS_API_KEY is not configured")
    if model_calls_used >= MAX_MODEL_CALLS:
        raise RuntimeError("model call budget exhausted")
    model = os.environ.get("NEBIUS_MODEL", DEFAULT_MODEL)
    prompt = {
        "evaluations_remaining": max(0, MAX_EVALUATIONS - len(measured_results)),
        "already_tested_seeds": [item["config"]["seed"] for item in measured_results],
        "measured_results": [
            {
                "config": item["config"],
                "alignment_quality_metrics": item["alignment_quality_metrics"],
                "pose_errors": item["pose_errors"],
                "classification": item["classification"],
            }
            for item in measured_results
        ],
        "allowed_ranges": {
            "seed": [0, 1_000_000],
            "visibility": ["top", "front", "all"],
            "yaw_deg": [-180, 180],
            "noise_std_m": [0, 0.005],
            "background_points": [0, 128],
        },
    }
    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 256,
        "response_format": _proposal_schema(),
        "messages": [
            {
                "role": "system",
                "content": (
                    "Propose one bounded synthetic CAD-to-scan experiment. Use the measured data to "
                    "seek a registration accepted by geometric metrics but wrong by pose error. "
                    "Return only the required JSON object; do not claim results or propose code."
                ),
            },
            {"role": "user", "content": json.dumps(prompt)},
        ],
    }
    result = chat_completion(payload, timeout=45)
    content = result["choices"][0]["message"]["content"]
    proposal = ExperimentProposal.model_validate_json(content)
    usage = result.get("usage", {})
    return proposal, {
        "model": model,
        "usage": {
            key: usage[key]
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
            if key in usage
        },
    }
