import numpy as np
import pytest

from autoframe3d.experiment import ExperimentConfig, evaluate, generate_scan


def test_seeded_scan_is_reproducible():
    config = ExperimentConfig(scan_points=120, target_points=512)
    first, first_truth = generate_scan(config)
    second, second_truth = generate_scan(config)
    np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(first_truth, second_truth)


def test_classification_requires_both_geometric_acceptance_and_pose_error():
    result = evaluate(ExperimentConfig())
    assert result["classification"] == "accepted_but_wrong"
    metrics = result["alignment_quality_metrics"]
    assert 0.0 <= metrics["fitness"] <= 1.0
    assert metrics["inlier_rmse_m"] >= 0.0


def test_budget_rejects_more_than_twelve_evaluations():
    from autoframe3d.experiment import bounded_search

    with pytest.raises(ValueError):
        bounded_search(13)