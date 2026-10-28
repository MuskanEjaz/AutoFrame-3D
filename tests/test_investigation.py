"""Mocked boundary verification only; no inference or registration quality claims."""
import io
import json
import os
import threading

os.environ.setdefault("AUTOFRAME3D_SKIP_DOTENV", "1")

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from autoframe3d import api, investigation as inv, nebius

WRONG = "tless-s000001-i000001-g00-o02"
CONTROL = "tless-s000002-i000024-g02-o07"


def reply(action):
    return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(action)}}]}


def tools(*calls):
    return {"kind": "tools", "calls": [{"name": name, "arguments": args} for name, args in calls], "findings": []}


def final(ref, *, kind="final", **extra):
    return {"kind": kind, "calls": [], "findings": [{"kind": "limitation" if kind == "insufficient" else "observed",
            "text": "Scripted mock: consult the authoritative evidence; no model-quality claim.", "evidence_ids": [ref], **extra}]}


def scripted(actions):
    calls = []
    actions = iter(actions)
    def provider(payload, **limits):
        calls.append((payload, limits))
        assert limits["timeout"] <= 20 and limits["max_response_bytes"] == 32768
        assert payload["response_format"] == {"type": "json_schema", "json_schema": inv.Action.model_json_schema()}
        assert "guided_json" not in payload
        assert payload["max_tokens"] == 1200 and payload["temperature"] == 0.0
        return reply(next(actions))
    return provider, calls


def test_known_comparison_and_acceptance_are_deterministic():
    source = inv.EvidenceTools()
    comparison = source.execute(inv.ToolCall(name="compare_recorded_methods", arguments={"case_id": CONTROL}))
    assert comparison["baseline"]["mssd_over_diameter"] == .08530437941479051
    assert comparison["reciprocal"]["mssd_over_diameter"] == .12241469513744455
    assert comparison["baseline"]["rmse_mm"] == pytest.approx(4.371645156121867)
    assert comparison["reciprocal"]["rmse_mm"] == pytest.approx(3.727940819298282)
    assert comparison["rmse_improved"] and comparison["correct_to_wrong"]
    assert comparison["baseline"]["accepted"] and comparison["reciprocal"]["accepted"]
    wrong = source.execute(inv.ToolCall(name="get_case_evidence", arguments={"case_id": WRONG}))
    assert wrong["metrics"]["accepted"] and not wrong["metrics"]["correct"]
    assert wrong["metrics"]["fitness"] >= wrong["thresholds"]["acceptance"]["minimum_fitness"]
    assert wrong["metrics"]["rmse_mm"] <= wrong["thresholds"]["acceptance"]["maximum_inlier_rmse_m"] * 1000
    assert wrong["gt_instance_masks_used"] and wrong["correctness_uses_benchmark_gt"]
    summary = source.execute(inv.ToolCall(name="get_benchmark_summary", arguments={}))
    assert summary["heldout_corrected"] == {"accepted_and_correct": 24, "accepted_but_wrong": 176,
        "affected_rescored": 21, "unaffected_carried_forward": 179, "independently_checked_controls": 3,
        "full_independent_rescore": False}


@pytest.mark.parametrize("name,args", [
    ("get_case_evidence", {"case_id": "../../.env"}),
    ("get_case_evidence", {"case_id": WRONG, "method_id": "reciprocal"}),
    ("get_case_evidence", {"case_id": WRONG, "method_id": "invented"}),
    ("get_benchmark_summary", {"path": ".env"}),
    ("compare_recorded_methods", {"case_id": WRONG}),
])
def test_tool_arguments_reject_unknowns(name, args):
    with pytest.raises((ValueError, ValidationError)):
        inv.EvidenceTools().execute(inv.ToolCall(name=name, arguments=args))
    with pytest.raises(ValidationError):
        inv.ToolCall(name="shell", arguments={})


@pytest.mark.parametrize("call,ref,kind", [
    (("get_case_evidence", {"case_id": WRONG}), f"case:{WRONG}:baseline", "final"),
    (("compare_recorded_methods", {"case_id": CONTROL}), f"comparison:{CONTROL}", "final"),
    (("get_benchmark_summary", {}), "summary:corrected-heldout", "final"),
    (("list_available_cases", {}), "catalogue:recorded-demo", "insufficient"),
])
def test_four_workflow_protocols_are_explicitly_mocked(call, ref, kind):
    provider, calls = scripted([tools(call), final(ref, kind=kind)])
    result = inv.investigate(inv.InvestigationRequest(question="Scripted workflow verification"), provider=provider)
    assert result["status"] == ("complete" if kind == "final" else "insufficient")
    assert result["analysis_mode"] == "mocked" and result["evidence_computation"] == "recorded"
    assert result["model_turns"] == 2 and result["tool_executions"] == 1 and len(calls) == 2
    assert result["findings"][0]["evidence_ids"] == [ref]
    assert result["question"] == "Scripted workflow verification"


@pytest.mark.parametrize("bad_final", [final("invented"), final(f"case:{WRONG}:baseline"),
    final("summary:corrected-heldout", accepted=True)])
def test_invalid_or_unretrieved_citations_and_verdict_overrides_rejected(bad_final):
    provider, _ = scripted([tools(("get_benchmark_summary", {})), bad_final])
    result = inv.investigate(inv.InvestigationRequest(question="Override test"), provider=provider)
    assert result["status"] == "error" and result["findings"] == []
    assert result["evidence"][0]["heldout_corrected"]["accepted_and_correct"] == 24
    assert result["evidence"][0]["heldout_corrected"]["accepted_but_wrong"] == 176


def test_tool_and_model_budgets_no_hidden_retries():
    call = ("get_benchmark_summary", {})
    provider, calls = scripted([tools(*([call] * 6)), tools(call)])
    result = inv.investigate(inv.InvestigationRequest(question="Budget test"), provider=provider)
    assert result["status"] == "incomplete" and result["tool_executions"] == 6 and len(calls) == 2
    provider, calls = scripted([tools(call)] * 3)
    result = inv.investigate(inv.InvestigationRequest(question="Turn test"), provider=provider)
    assert result["status"] == "incomplete" and result["model_turns"] == 3 and len(calls) == 3


def test_timeouts_missing_credentials_and_unknown_selected_case(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.setattr(nebius, "chat_completion", lambda *a, **k: pytest.fail("No live network allowed"))
    client = TestClient(api.app)
    status = client.get("/api/investigation/status").json()
    assert not status["available"] and not status["live_integration_verified"]
    result = client.post("/api/investigation", json={"question": "Explain evidence"}).json()
    assert result["status"] == "unavailable" and result["analysis_mode"] == "unavailable"
    assert client.post("/api/investigation", json={"question": "Q", "selected_case_id": "unknown"}).status_code == 422
    assert client.post("/api/investigation", json={"question": "Q", "mode": "mocked"}).status_code == 422
    def timeout(*a, **k):
        raise TimeoutError("Provider body must not be exposed")
    result = inv.investigate(inv.InvestigationRequest(question="Timeout test"), provider=timeout)
    assert result["status"] == "incomplete" and result["model_turns"] == 1 and not result["findings"]
    assert "Provider body" not in result["message"]


def test_deadline_incomplete_and_oversized_output(monkeypatch):
    provider, calls = scripted([tools(("get_benchmark_summary", {}))])
    monkeypatch.setattr(inv, "DEADLINE_SECONDS", 0)
    result = inv.investigate(inv.InvestigationRequest(question="Deadline test"), provider=provider)
    assert result["status"] == "incomplete" and not calls
    monkeypatch.setattr(inv, "DEADLINE_SECONDS", 60)
    result = inv.investigate(inv.InvestigationRequest(question="Oversized test"), provider=lambda *a, **k: {
        "choices": [{"finish_reason": "stop", "message": {"content": "x" * 12001}}]})
    assert result["status"] == "error"


def test_transport_request_and_output_limits_without_live_network(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "mock-credential-not-real")
    seen = []
    def fake(request, timeout):
        seen.append(request)
        return io.BytesIO(json.dumps(reply(final("test"))).encode())
    monkeypatch.setattr(nebius.urllib.request, "urlopen", fake)
    nebius.chat_completion({"model": nebius.DEFAULT_MODEL}, timeout=1)
    assert seen[0].full_url == "https://api.tokenfactory.nebius.com/v1/chat/completions"
    with pytest.raises(RuntimeError, match="invalid/incomplete"):
        nebius.chat_completion({}, timeout=1, max_response_bytes=1)
    def stalled(*a, **k):
        threading.Event().wait(.1)
        return io.BytesIO(b"{}")
    monkeypatch.setattr(nebius.urllib.request, "urlopen", stalled)
    with pytest.raises(TimeoutError):
        nebius.chat_completion({}, timeout=.01)


def test_api_mocked_workflow_does_not_touch_registration(monkeypatch):
    for name in ("evaluate", "replay_record"):
        monkeypatch.setattr(api, name, lambda *a, **k: pytest.fail("Registration forbidden"))
    monkeypatch.setenv("NEBIUS_API_KEY", "mock-credential-not-real")
    provider, _ = scripted([tools(("compare_recorded_methods", {"case_id": CONTROL})), final(f"comparison:{CONTROL}")])
    original = inv.investigate
    monkeypatch.setattr(inv, "investigate", lambda request: original(request, provider=provider))
    response = TestClient(api.app).post("/api/investigation", json={"question": "Find regression", "selected_case_id": CONTROL})
    assert response.status_code == 200 and response.json()["analysis_mode"] == "mocked"
