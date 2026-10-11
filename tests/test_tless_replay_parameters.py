"""Replay/export regressions without real registration or dataset access."""
import io
import json
import zipfile
from dataclasses import dataclass

import numpy as np

from autoframe3d import tless_cases


def test_replay_passes_saved_perturbation_to_evaluator(monkeypatch):
    record = {
        "case_id": "fixture", "scene_id": 1, "image_id": 1, "gt_index": 0,
        "object_id": 1, "group": "perturbed", "status": "valid",
        "category": "accepted_but_wrong",
        "perturbation": {"seed": 101, "noise_std_m": .004, "point_dropout_fraction": .17},
        "alignment_quality_metrics": {"fitness": .9, "inlier_rmse_m": .003},
        "pose_metrics": {"mssd_over_diameter": .5},
    }
    def evaluate(case, **kwargs):
        assert kwargs["perturbation_override"] == record["perturbation"]
        assert kwargs["timeout_seconds"] == 30.
        return record
    monkeypatch.setattr(tless_cases, "evaluate_case", evaluate)
    assert tless_cases.replay_record(record)["passed"]


def test_export_contains_scan_from_saved_seed_and_parameters(tmp_path, monkeypatch):
    @dataclass
    class Inputs:
        object_id: int
        scan_points_camera_m: np.ndarray
        model_vertices_object_m: np.ndarray
    scan = np.arange(120, dtype=float).reshape(40, 3) / 1000
    inputs = Inputs(1, scan, scan)
    record = {"case_id": "fixture", "group": "perturbed", "perturbation": {
        "noise_std_m": .004, "point_dropout_fraction": .17, "seed": 101}}
    monkeypatch.setattr(tless_cases, "load_registration_inputs", lambda record: inputs)
    monkeypatch.setattr(tless_cases, "ROOT", tmp_path)
    model_root = tmp_path / "data/tless/bop/models_cad"
    model_root.mkdir(parents=True)
    (model_root / "obj_000001.ply").write_bytes(b"fixture-model")
    provenance = tmp_path / "data/tless/provenance.json"
    provenance.write_text(json.dumps({"repository": "fixture", "revision": "fixture", "license": "CC-BY-4.0"}))
    bundle = tless_cases.export_case_bundle(record, tmp_path / "bundle.zip")
    with zipfile.ZipFile(bundle) as archive:
        exported = np.loadtxt(io.BytesIO(archive.read("scan_camera.xyz")))
    expected = tless_cases._perturb_scan(inputs, record["perturbation"])
    np.testing.assert_allclose(exported, expected, atol=5e-9, rtol=0)
    assert len(exported) < len(scan)
