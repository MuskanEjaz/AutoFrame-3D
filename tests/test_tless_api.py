import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from autoframe3d.api import app
from autoframe3d.tless_cases import list_result_records, replay_record


pytestmark = pytest.mark.skipif(
    not list_result_records("original", "smoke20_frozen"),
    reason="Run the pinned T-LESS subset and frozen smoke manifest first",
)


def test_tless_results_and_real_geometry_are_available_to_dashboard():
    client = TestClient(app)
    listing = client.get("/api/tless/cases?group=original&manifest=smoke20_frozen")
    assert listing.status_code == 200
    body = listing.json()
    assert body["protocol"].startswith("Custom internal evaluation")
    assert body["mask_protocol"].startswith("Registration evaluation with ground-truth instance masks")
    assert len(body["cases"]) == 20

    selected = next(case for case in body["cases"] if case["status"] == "valid")
    geometry = client.get(f"/api/tless/cases/{selected['case_id']}/geometry")
    assert geometry.status_code == 200
    payload = geometry.json()
    assert payload["config"]["units"] == "metres"
    assert len(payload["scan"]) > 20
    assert len(payload["estimated_T_object_from_scan"]) == 4
    assert len(payload["ground_truth_T_object_from_scan"]) == 4


def test_tless_case_export_has_dataset_attribution():
    client = TestClient(app)
    case = next(case for case in list_result_records("original", "smoke20_frozen") if case["status"] == "valid")
    response = client.get(f"/api/tless/cases/{case['case_id']}/export?group=original&manifest=smoke20_frozen")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert len(response.content) > 100_000
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        bundle = json.loads(archive.read("case.json"))
    assert bundle["dataset_attribution"]["license"] == "CC-BY-4.0"
    assert bundle["dataset_attribution"]["revision"]


def test_real_case_replay_recomputes_and_matches_recorded_metrics():
    case = next(case for case in list_result_records("original", "smoke20_frozen") if case["status"] == "valid")
    replay = replay_record(case)
    assert replay["passed"] is True
    assert replay["actual_category"] == case["category"]


def test_perturbed_result_group_serves_perturbed_scan_points():
    case = next(case for case in list_result_records("perturbed", "heldout200") if case["status"] == "valid")
    client = TestClient(app)
    query = f"manifest=heldout200&group="
    original = client.get(f"/api/tless/cases/{case['case_id']}/geometry?{query}original").json()
    perturbed = client.get(f"/api/tless/cases/{case['case_id']}/geometry?{query}perturbed").json()
    assert len(perturbed["scan"]) < len(original["scan"])