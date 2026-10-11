import time

from fastapi.testclient import TestClient

from autoframe3d.api import app


def test_health_endpoint_discloses_live_or_deterministic_mode():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_mode"] in {"live_ai_available", "deterministic_only"}
    assert body["campaign_budget_max"] == 12
    assert body["model_calls_max"] == 4


def test_campaign_requires_equal_strategy_budgets():
    response = TestClient(app).post("/api/campaigns", json={"budget": 3, "mode": "deterministic"})
    assert response.status_code == 422


def test_baseline_job_events_are_json_serializable_and_complete():
    client = TestClient(app)
    started = client.post(
        "/api/baseline",
        json={"object_kind": "near_symmetric", "visibility": "all", "seed": 41, "yaw_deg": 0},
    )
    assert started.status_code == 200
    job_id = started.json()["job_id"]
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] == "completed":
            break
        time.sleep(0.05)
    assert job["status"] == "completed"
    assert job["progress"] == {"completed": 1, "total": 1}
    assert job["events"][0]["classification"] == "accepted_correct"
    case_id = job["events"][0]["case_id"]
    details = client.get(f"/api/cases/{case_id}")
    geometry = client.get(f"/api/cases/{case_id}/geometry")
    assert details.status_code == 200
    assert geometry.status_code == 200
    assert len(geometry.json()["estimated_T_object_from_scan"]) == 4