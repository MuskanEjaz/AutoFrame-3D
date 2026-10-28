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



def test_investigation_only_skips_probe_and_counts_nine_requests(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(release, "run_probe", lambda *a: pytest.fail("Diagnostic forbidden in investigation-only mode"))
    def fake(payload, **limits):
        calls.append(payload)
        assert payload["max_tokens"] == 1200
        assert 0 < limits["timeout"] <= 20 and limits["max_response_bytes"] == 32768
        return completion()
    monkeypatch.setattr(nebius, "chat_completion", fake)
    directory = tmp_path / "run"
    result = release.run_release(directory, investigation_only=True)
    assert result["mode"] == "investigation_only" and result["max_provider_requests"] == 9
    assert result["provider_requests"] == len(calls) == 9
    assert result["attempted_items"] == ["dev-01", "dev-02", "dev-13"]
    assert result["diagnostic"]["stage"] == "not_run" and not (directory / "diagnostic").exists()
    rows = [json.loads(line) for line in (directory / "capture.jsonl").read_text().splitlines()]
    assert [r["item_id"] for r in rows] == list(release.ITEMS)
    assert all(r["response"]["status"] == "incomplete" for r in rows)
    assert json.loads((directory / "report.json").read_text())["dimensions"]["task_completion"] == {"fail": 3, "missing": 12}
    with pytest.raises(FileExistsError):
        release.run_release(directory, investigation_only=True)
    assert len(calls) == 9


@pytest.mark.parametrize("http_status", [401, 402, 403, 422])
def test_investigation_only_stops_on_rejection_without_retry(monkeypatch, tmp_path, http_status):
    calls = []
    def reject(payload, **limits):
        calls.append(payload)
        raise nebius.ProviderError("http_rejection", http_status=http_status)
    monkeypatch.setattr(nebius, "chat_completion", reject)
    result = release.run_release(tmp_path / "run", investigation_only=True)
    assert result["provider_requests"] == len(calls) == 1
    assert result["attempted_items"] == ["dev-01"]
    assert result["stop_reason"] == "operational_rejection_no_further_items"
    rows = [json.loads(line) for line in (tmp_path / "run/capture.jsonl").read_text().splitlines()]
    assert rows[0]["response"]["status"] == "error" and rows[0]["response"]["findings"] == []


def test_investigation_only_hard_ceiling_prevents_tenth_transport_call(monkeypatch, tmp_path):
    calls = []
    def fake(payload, **limits):
        calls.append(payload)
        return completion()
    def excessive(*args, **kwargs):
        for _ in range(10):
            nebius.chat_completion({"max_tokens": 1200}, timeout=20, max_response_bytes=32768)
    monkeypatch.setattr(nebius, "chat_completion", fake)
    monkeypatch.setattr(release.investigation, "investigate", excessive)
    with pytest.raises(RuntimeError, match="request limit"):
        release.run_release(tmp_path / "run", investigation_only=True)
    assert len(calls) == 9
    assert nebius.chat_completion is fake
    assert json.loads((tmp_path / "run/summary.json").read_text())["provider_requests"] == 9


def test_default_diagnostic_truncation_remains_failure(monkeypatch, tmp_path):
    calls = []
    def truncated(payload, **limits):
        calls.append(payload)
        raise nebius.ProviderError("finish_reason", finish_reason="length", usage={"completion_tokens": 128})
    monkeypatch.setattr(nebius, "chat_completion", truncated)
    result = release.run_release(tmp_path / "run")
    assert result["provider_requests"] == len(calls) == 1 and calls[0]["max_tokens"] == 128
    assert result["diagnostic"]["finish_reason"] == "length"
    assert result["stop_reason"] == "diagnostic_did_not_succeed" and result["attempted_items"] == []


def test_cli_forwards_explicit_mode_without_implicit_live_authorization(monkeypatch, tmp_path):
    seen = []
    def run(directory, **kwargs):
        seen.append(kwargs)
        return {"stop_reason": None}
    monkeypatch.setattr(release, "run_release", run)
    with pytest.raises(SystemExit):
        release.main(["--investigation-only", "--output", str(tmp_path / "run")])
    assert not seen
    assert release.main(["--live", "--investigation-only", "--output", str(tmp_path / "run")]) == 0
    assert seen == [{"investigation_only": True}]



def test_later_rejection_retains_completed_item_and_skips_last(monkeypatch, tmp_path):
    calls = []
    def fake(payload, **limits):
        calls.append(payload)
        if len(calls) == 1:
            return completion()
        if len(calls) == 2:
            action = {"kind": "final", "calls": [], "findings": [{"kind": "limitation",
                "text": "Hand-authored fixture; not model-quality evidence.",
                "evidence_ids": ["summary:corrected-heldout"]}]}
            return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(action)}}]}
        raise nebius.ProviderError("http_rejection", http_status=402)
    monkeypatch.setattr(nebius, "chat_completion", fake)
    result = release.run_release(tmp_path / "run", investigation_only=True)
    assert result["provider_requests"] == len(calls) == 3
    assert result["attempted_items"] == ["dev-01", "dev-02"]
    assert result["stop_reason"] == "operational_rejection_no_further_items"
    rows = [json.loads(line) for line in (tmp_path / "run/capture.jsonl").read_text().splitlines()]
    assert [r["response"]["status"] for r in rows] == ["complete", "error"]
