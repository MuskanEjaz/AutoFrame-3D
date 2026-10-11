from dataclasses import asdict

import pytest
from pydantic import ValidationError

from autoframe3d.agent import ExperimentProposal, MAX_MODEL_CALLS, propose_next
from autoframe3d.campaign import run_campaign
from autoframe3d.experiment import ExperimentConfig


def test_proposal_schema_rejects_out_of_range_and_extra_fields():
    proposal = ExperimentProposal(
        seed=10,
        visibility="front",
        yaw_deg=25.0,
        noise_std_m=0.001,
        background_points=0,
    )
    assert proposal.to_config().visibility == "front"
    with pytest.raises(ValidationError):
        ExperimentProposal.model_validate({**proposal.model_dump(), "shell": "not allowed"})
    with pytest.raises(ValidationError):
        ExperimentProposal.model_validate({**proposal.model_dump(), "noise_std_m": 1.0})


def test_model_call_budget_is_enforced_before_network_request(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
    with pytest.raises(RuntimeError, match="budget exhausted"):
        propose_next([], MAX_MODEL_CALLS)


def test_campaign_spends_exact_equal_registration_budgets(monkeypatch):
    import autoframe3d.campaign as campaign

    evaluations = []

    def fake_evaluate(config):
        evaluations.append(config)
        return {
            "config": asdict(config),
            "thresholds": {},
            "ground_truth_T_object_from_scan": [],
            "estimated_T_object_from_scan": [],
            "alignment_quality_metrics": {"fitness": 1.0, "inlier_rmse_m": 0.01},
            "pose_errors": {"translation_error_m": 0.0, "rotation_error_deg": 0.0},
            "classification": "accepted_correct",
            "initial_yaw_deg": 0.0,
        }

    monkeypatch.setattr(campaign, "evaluate", fake_evaluate)
    result = run_campaign(budget=4, mode="deterministic")
    assert len(evaluations) == 4
    assert result["summary"]["agent_evaluations"] == 2
    assert result["summary"]["random_evaluations"] == 2
    assert result["summary"]["registration_evaluations_total"] == 4
    assert result["mode"] == "deterministic"


def test_live_request_requires_credentials():
    import os

    os.environ.pop("NEBIUS_API_KEY", None)
    with pytest.raises(RuntimeError, match="NEBIUS_API_KEY"):
        propose_next([], 0)


def test_rejects_campaign_budget_above_limit():
    with pytest.raises(ValueError, match="between 2 and 12"):
        run_campaign(budget=14, mode="deterministic")


def test_simplification_keeps_only_measured_failures(monkeypatch):
    from autoframe3d.simplify import simplify_failure

    initial = ExperimentConfig()

    def fake_evaluate(config):
        classification = "accepted_but_wrong" if config.noise_std_m == 0 else "rejected"
        return {
            "config": asdict(config),
            "thresholds": {},
            "ground_truth_T_object_from_scan": [],
            "estimated_T_object_from_scan": [],
            "alignment_quality_metrics": {"fitness": 1.0, "inlier_rmse_m": 0.01},
            "pose_errors": {"translation_error_m": 0.2, "rotation_error_deg": 30.0},
            "classification": classification,
            "initial_yaw_deg": 0.0,
        }

    monkeypatch.setattr("autoframe3d.simplify.evaluate", fake_evaluate)
    result = simplify_failure({"classification": "accepted_but_wrong", "config": asdict(initial)}, budget=1)
    assert result["evaluations"] == 1
    assert result["simplifications_kept"] == [{"parameter": "noise_std_m", "value": 0.0}]