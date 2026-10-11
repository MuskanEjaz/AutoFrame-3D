from pathlib import Path

from autoframe3d.cases import export_case, replay_bundle
from autoframe3d.experiment import ExperimentConfig, evaluate


def test_successful_control_is_accepted_and_pose_correct():
    result = evaluate(ExperimentConfig(visibility="all", yaw_deg=0.0))
    assert result["classification"] == "accepted_correct"
    assert result["pose_errors"]["translation_error_m"] < 0.08
    assert result["pose_errors"]["rotation_error_deg"] < 12.0


def test_exported_failure_recomputes_and_replays(tmp_path: Path):
    result = evaluate(ExperimentConfig())
    assert result["classification"] == "accepted_but_wrong"
    bundle = export_case("test-failure", result["config"], result, tmp_path / "failure.zip")
    replay = replay_bundle(bundle)
    assert replay["passed"] is True
    assert replay["actual"]["classification"] == "accepted_but_wrong"
    assert all(value == 0.0 for value in replay["absolute_differences"].values())