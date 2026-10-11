"""Recorded demo must load saved evidence without running registration or models."""
import os
os.environ.setdefault("AUTOFRAME3D_SKIP_DOTENV", "1")

import numpy as np
from fastapi.testclient import TestClient

from autoframe3d import api, recorded_demo, tless_cases, tless_benchmark, agent


def test_recorded_case_geometry_export_and_regression_without_compute(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Recorded browsing must not register or call models")
    monkeypatch.setattr(api, "evaluate", forbidden)
    monkeypatch.setattr(api, "replay_record", forbidden)
    monkeypatch.setattr(tless_cases, "evaluate_case", forbidden)
    monkeypatch.setattr(tless_benchmark, "register_masked_scan", forbidden)
    monkeypatch.setattr(agent, "propose_next", forbidden)
    client = TestClient(api.app)
    response = client.get("/api/demo")
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "Recorded benchmark demo"
    assert body["evidence"]["heldout_corrected"]["accepted_but_wrong"] == 176
    assert body["evidence"]["heldout_corrected"]["full_independent_rescore"] is False
    wrong, control = body["cases"]
    assert wrong["variants"][0]["record"]["accepted"] and not wrong["variants"][0]["record"]["correct"]
    baseline, experimental = control["variants"]
    assert baseline["record"]["pose_metrics"]["mssd_over_diameter"] <= .1 < experimental["record"]["pose_metrics"]["mssd_over_diameter"]
    assert experimental["record"]["alignment_quality_metrics"]["inlier_rmse_m"] < baseline["record"]["alignment_quality_metrics"]["inlier_rmse_m"]
    for case in body["cases"]:
        exported = client.get(f"/api/demo/cases/{case['id']}/evidence")
        assert exported.status_code == 200
        assert "attachment" in exported.headers["content-disposition"]
        assert len(exported.json()["cases"]) == 1
        if not case["geometry_available"]:
            assert client.get(f"/api/demo/cases/{case['id']}/geometry").status_code == 503
            continue  # A clone without separately restored raw assets still supports evidence.
        for variant in case["variants"]:
            response = client.get(f"/api/demo/cases/{case['id']}/geometry?variant={variant['id']}")
            assert response.status_code == 200
            geometry = response.json()
            assert len(geometry["scan"]) > 20 and len(geometry["mesh"]["faces"]) > 0
            np.testing.assert_allclose(np.linalg.inv(geometry["estimated_T_object_from_scan"]), variant["record"]["camera_from_object_estimate"], atol=1e-12)
            np.testing.assert_allclose(np.linalg.inv(geometry["ground_truth_T_object_from_scan"]), variant["record"]["camera_from_object_ground_truth"], atol=1e-12)


def test_missing_or_changed_geometry_keeps_recorded_metrics_available(monkeypatch):
    def missing(case):
        raise FileNotFoundError("Local geometry input missing: fixture. Recorded metrics remain available.")
    monkeypatch.setattr(recorded_demo, "display_asset", missing)
    client = TestClient(api.app)
    listing = client.get("/api/demo").json()
    assert not listing["cases"][0]["geometry_available"]
    assert listing["cases"][0]["variants"][0]["record"]["pose_metrics"]
    response = client.get("/api/demo/cases/accepted-wrong/geometry")
    assert response.status_code == 503 and "Recorded metrics" in response.json()["detail"]
    def changed(case):
        raise ValueError("Local input differs from recorded evidence")
    monkeypatch.setattr(recorded_demo, "display_asset", changed)
    assert client.get("/api/demo/cases/accepted-wrong/geometry").status_code == 409


def test_explicit_replay_uses_saved_baseline_and_does_not_replace_recording(monkeypatch):
    monkeypatch.setattr(recorded_demo, "check_inputs", lambda *args, **kwargs: None)
    calls = []
    monkeypatch.setattr(api, "replay_record", lambda record: calls.append(record) or {"passed": True})
    monkeypatch.setattr(api, "_start_worker", lambda job, run: run())
    client = TestClient(api.app)
    before = client.get("/api/demo").json()
    response = client.post("/api/demo/cases/control-regression/replay")
    assert response.status_code == 200
    assert calls[0]["correct"] is True and calls[0]["pose_metrics"]["mssd_over_diameter"] < .1
    job = client.get("/api/jobs/" + response.json()["job_id"]).json()
    assert job["type"] == "recorded_baseline_replay" and job["result"]["passed"]
    assert client.get("/api/demo").json() == before
    assert client.get("/api/demo/cases/no-such-case/geometry").status_code == 404
    assert client.get("/api/demo/cases/accepted-wrong/geometry?variant=reciprocal").status_code == 404


def test_real_input_guards_and_assets_absent_clone(monkeypatch):
    import pytest
    with pytest.raises(ValueError, match="differs from recorded evidence"):
        recorded_demo.check_inputs({"inputs": {"pyproject.toml": "invalid-hash"}}, verify_hashes=True)
    monkeypatch.setattr(recorded_demo, "ROOT", recorded_demo.ROOT / "nonexistent-demo-assets-fixture")
    client = TestClient(api.app)
    listing = client.get("/api/demo").json()
    assert all(not case["geometry_available"] for case in listing["cases"])
    for case in listing["cases"]:
        assert client.get(f"/api/demo/cases/{case['id']}/geometry").status_code == 503
        assert client.get(f"/api/demo/cases/{case['id']}/evidence").status_code == 200


def test_absent_curated_evidence_returns_actionable_error(monkeypatch):
    monkeypatch.setattr(recorded_demo, "EVIDENCE_PATH", recorded_demo.ROOT / "nonexistent-demo-evidence-fixture.json")
    client = TestClient(api.app)
    for route in ("/api/demo", "/api/demo/cases/accepted-wrong/evidence"):
        response = client.get(route)
        assert response.status_code == 503 and "restore audit_evidence" in response.json()["detail"]


def test_versioned_sources_support_curated_records_and_publication_hashes():
    import hashlib
    import json
    data = recorded_demo.evidence()
    for case in data["cases"]:
        for variant in case["variants"]:
            raw = (recorded_demo.ROOT / variant["publication_copy"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == variant["source_sha256"]
            rows = [json.loads(line) for line in raw.decode().splitlines()]
            saved = next(r for r in rows if (r.get("case", {}).get("case_id") or r.get("case_id")) == case["case_id"])
            if variant["id"] == "baseline":
                assert saved == variant["record"]
            else:
                assert saved["result"]["camera_from_object"] == variant["record"]["camera_from_object_estimate"]
                assert saved["result"]["mssd_over_diameter"] == variant["record"]["pose_metrics"]["mssd_over_diameter"]
                assert saved["result"]["inlier_rmse_m"] == variant["record"]["alignment_quality_metrics"]["inlier_rmse_m"]
    manifest = json.loads((recorded_demo.EVIDENCE_PATH.parent / "COPY_MANIFEST.json").read_text())
    for name, entry in manifest["files"].items():
        raw = (recorded_demo.EVIDENCE_PATH.parent / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["publication_sha256"]
        assert len(raw) == entry["publication_size_bytes"]
