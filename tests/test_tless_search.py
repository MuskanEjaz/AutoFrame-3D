import pytest
from pydantic import ValidationError

from autoframe3d.tless_search import TlessPerturbation, deterministic_proposals, random_proposals, _feedback


def test_search_proposals_share_declared_parameter_bounds():
    proposals = deterministic_proposals(123) + random_proposals(456)
    assert len(proposals) == 8
    assert all(0.0 <= proposal.noise_std_m <= 0.005 for proposal in proposals)
    assert all(0.0 <= proposal.point_dropout_fraction <= 0.2 for proposal in proposals)
    with pytest.raises(ValidationError):
        TlessPerturbation(noise_std_m=0.01, point_dropout_fraction=0.1, seed=5)


def test_search_policy_feedback_never_receives_gt_pose_metric_or_correctness():
    feedback = _feedback({
        "status": "valid",
        "category": "accepted_but_wrong",
        "pose_metrics": {"mssd_m": 0.4, "mssd_over_diameter": 0.8},
        "alignment_quality_metrics": {"fitness": 0.98, "inlier_rmse_m": 0.004},
    }, TlessPerturbation(noise_std_m=0.002, point_dropout_fraction=0.05, seed=9))
    assert set(feedback) == {"perturbation", "status", "fitness", "inlier_rmse_m"}
    assert "category" not in feedback
    assert "mssd_over_diameter" not in feedback