"""Offline orchestration verification; hand-authored transport only."""
import json
import pytest
from autoframe3d import nebius
from scripts import validate_release_live as release


@pytest.fixture(autouse=True)
def configured_fixture(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "offline-fixture-not-a-key")


def completion():
    return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"kind": "tools", "calls": [{"name": "get_benchmark_summary", "arguments": {}}], "findings": []})}}]}


def test_diagnostic_rejection_stops_all_items(monkeypatch, tmp_path):
    calls = []
    def reject(payload, **limits):
        calls.append((payload, limits))
        raise nebius.ProviderError("http_rejection", http_status=401)
    monkeypatch.setattr(nebius, "chat_completion", reject)
    result = release.run_release(tmp_path / "run")
    assert result["provider_requests"] == len(calls) == 1
    assert not result["attempted_items"] and calls[0][0]["max_tokens"] == 128
    assert not (tmp_path / "run/capture.jsonl").exists()
    with pytest.raises(FileExistsError):
        release.run_release(tmp_path / "run")
    assert len(calls) == 1


def test_successful_diagnostic_then_rejection_stops_remaining_items(monkeypatch, tmp_path):
    calls = []
    def fake(payload, **limits):
        calls.append(payload)
        if len(calls) == 1:
            return completion()
        raise nebius.ProviderError("http_rejection", http_status=422)
    monkeypatch.setattr(nebius, "chat_completion", fake)
    result = release.run_release(tmp_path / "run")
    assert result["provider_requests"] == 2 and result["attempted_items"] == ["dev-01"]
    report = json.loads((tmp_path / "run/report.json").read_text())
    assert report["dimensions"]["task_completion"] == {"fail": 1, "missing": 14}


def test_three_turn_items_fit_ten_request_ceiling_without_retries(monkeypatch, tmp_path):
    calls = []
    def fake(payload, **limits):
        calls.append(payload)
        assert limits["timeout"] <= 20 and limits["max_response_bytes"] == 32768
        return completion()
    monkeypatch.setattr(nebius, "chat_completion", fake)
    result = release.run_release(tmp_path / "run")
    assert result["provider_requests"] == len(calls) == 10
    assert result["attempted_items"] == list(release.ITEMS)
    assert calls[0]["max_tokens"] == 128 and all(c["max_tokens"] == 1200 for c in calls[1:])
    rows = [json.loads(line) for line in (tmp_path / "run/capture.jsonl").read_text().splitlines()]
    assert all(r["response"]["status"] == "incomplete" for r in rows)
