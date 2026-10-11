"""Bounded evaluator/runner checks without data loading or registration."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

from autoframe3d import tless_benchmark as benchmark


def test_evaluator_scores_only_after_registration(monkeypatch):
    events = []
    inputs = SimpleNamespace(object_id=1, model_info={"diameter": 1000},
                             evaluation_points_object_m=np.array([[0., 0., 0.]]))
    monkeypatch.setattr(benchmark, "load_registration_inputs", lambda case: inputs)
    def register(received, **kwargs):
        assert received is inputs
        events.append("register")
        return {"camera_from_object": np.eye(4), "fitness": 1., "inlier_rmse_m": 0.,
                "inlier_count": 1, "scan_point_count": 1, "max_correspondence_distance_m": .015,
                "initialization": "fixture", "registration_evaluations": 1,
                "selected_initialization_index": 0}
    def truth(case):
        assert events == ["register"]
        return SimpleNamespace(object_id=1, camera_from_object=np.eye(4))
    monkeypatch.setattr(benchmark, "register_masked_scan", register)
    monkeypatch.setattr(benchmark, "load_ground_truth", truth)
    result = benchmark.evaluate_case({"case_id": "fixture", "object_id": 1})
    assert result["status"] == "valid", result
    assert result["category"] == "accepted_and_correct"


def test_runner_records_verifies_and_preserves_checkpoints(tmp_path, monkeypatch):
    manifest_root = tmp_path / "manifests"
    manifest_root.mkdir()
    case = {"case_id": "fixture", "object_id": 1}
    (manifest_root / "fixture.json").write_text(json.dumps({"cases": [case]}))
    monkeypatch.setattr(benchmark, "MANIFEST_ROOT", manifest_root)
    monkeypatch.setattr(benchmark, "RESULT_ROOT", tmp_path / "results")
    monkeypatch.setattr(benchmark, "ROOT", tmp_path)
    dataset_root = tmp_path / "data" / "tless"
    dataset_root.mkdir(parents=True)
    (dataset_root / "provenance.json").write_text(json.dumps({"archives": []}))
    provenance = {"combined_sha256": "fixture-hash"}
    monkeypatch.setattr(benchmark, "build_provenance_manifest", lambda path: provenance)
    calls = []
    def evaluate(case, **kwargs):
        calls.append(case)
        return {**case, "status": "processing_failure", "runtime_seconds": 0., "error": "fixture"}
    monkeypatch.setattr(benchmark, "evaluate_case", evaluate)
    first = benchmark.run_manifest("fixture")
    checkpoint = tmp_path / "results" / "original" / "fixture.jsonl"
    assert json.loads(checkpoint.read_text())["provenance"] == provenance
    assert first["provenance"] == provenance
    benchmark.run_manifest("fixture")
    assert len(calls) == 1
    original = checkpoint.read_bytes()
    with pytest.raises(ValueError, match="existing checkpoint"):
        benchmark.run_manifest("fixture", resume=False)
    assert checkpoint.read_bytes() == original
    monkeypatch.setattr(benchmark, "build_provenance_manifest", lambda path: {"combined_sha256": "changed"})
    with pytest.raises(ValueError, match="provenance"):
        benchmark.run_manifest("fixture")
    assert checkpoint.read_bytes() == original
