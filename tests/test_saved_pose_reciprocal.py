"""Focused evaluation risks: GT isolation, failed-fit accounting, no retries."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location("saved_pose_eval", Path(__file__).resolve().parents[1] / "scripts/evaluate_saved_pose_reciprocal.py")
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


@pytest.mark.parametrize("has_correspondences", [True, False])
def test_supplied_pose_only_gt_guard_and_incomplete_accounting(monkeypatch, tmp_path, has_correspondences):
    from autoframe3d import tless_adapter as adapter
    model = np.column_stack((np.linspace(0, .1, 30), np.zeros(30), np.zeros(30)))
    initial = np.eye(4)
    initial[0, 3] = .1
    scan = model + [.1, 0, 0]
    annotation = tmp_path / "scene_gt.json"
    annotation.write_text("{}")
    def gt(case):
        annotation.read_text()  # Permitted only after refinement has returned.
        return SimpleNamespace(object_id=2, camera_from_object=initial.copy())
    monkeypatch.setattr(adapter, "load_ground_truth", gt)
    monkeypatch.setattr(adapter, "pca_initial_rotations", lambda *a: pytest.fail("PCA called"))
    monkeypatch.setattr(adapter, "load_registration_inputs", lambda case: SimpleNamespace(
        scan_points_camera_m=scan, evaluation_points_object_m=model, object_id=2, model_info={"diameter": 1000}))
    def fit(scan_arg, fit_arg, model_arg, pose, **kwargs):
        np.testing.assert_array_equal(pose, initial)
        assert kwargs["icp_correspondence_policy"] == "reciprocal"
        assert kwargs["max_iterations"] == 8 and kwargs["correspondence_distance_m"] == .015
        with pytest.raises(RuntimeError, match="GT"):
            adapter.load_ground_truth({})
        with pytest.raises(RuntimeError, match="GT"):
            annotation.read_text()
        if has_correspondences:
            kwargs["iteration_trace"].append({"camera_from_object": pose.copy(), "correspondence_count": 30})
        return pose.copy()
    monkeypatch.setattr(adapter, "_refine_icp", fit)
    # worker installs temporary guards; make pytest restore those attributes too.
    plan = {"per_case_hard_timeout_seconds": 30, "cases": [{"case": {"case_id": "test"},
        "initial_camera_from_object": initial.tolist(), "saved_baseline": {
            "alignment_quality_metrics": {"fitness": 1., "inlier_rmse_m": 0.},
            "pose_metrics": {"mssd_m": 0., "mssd_over_diameter": 0.}}}]}
    row = evaluation.worker(plan, 0)
    assert row["outcome"] == ("remained_correct" if has_correspondences else "incomplete")
    assert row["status"] == ("completed" if has_correspondences else "insufficient_correspondences")


def test_existing_start_marker_prevents_second_attempt(monkeypatch, tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    evaluation.write_new(output / "manifest.json", {"cases": []})
    evaluation.write_new(output / "started.json", {"already_started": True})
    monkeypatch.setattr(evaluation, "ROOT", tmp_path)
    monkeypatch.setattr(evaluation, "verify", lambda plan: None)
    monkeypatch.setattr(evaluation.subprocess, "run", lambda *a, **k: pytest.fail("Repeated attempt"))
    with pytest.raises(FileExistsError):
        evaluation.run(output)
