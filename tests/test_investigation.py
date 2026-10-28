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


@pytest.mark.parametrize("raw,stage", [
    (b"not json", "response_json"), (b"[]", "response_shape"),
    (b'{"choices": []}', "response_shape"),
    (json.dumps({"choices": [{"finish_reason": "length", "message": {"content": "secret"}}]}).encode(), "finish_reason"),
    (json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": "  "}}]}).encode(), "empty_content"),
])
def test_transport_failure_stages(monkeypatch, raw, stage):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setattr(nebius.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(raw))
    trace = []
    result = inv.investigate(inv.InvestigationRequest(question="Q"), provider=nebius.chat_completion, trace=trace)
    assert result["status"] == "error"
    assert trace[-1]["stage"] == stage
    assert "secret" not in json.dumps(trace)


@pytest.mark.parametrize("code,expected", [("invalid_request_error", "invalid_request_error"), ("secret", None)])
def test_http_error_allowlist_and_trace(monkeypatch, code, expected):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    calls = []
    def reject(*a, **k):
        calls.append(1)
        raise nebius.urllib.error.HTTPError("secret", 400, "secret", {},
            io.BytesIO(json.dumps({"error": {"code": code, "message": "secret"}}).encode()))
    monkeypatch.setattr(nebius.urllib.request, "urlopen", reject)
    trace = []
    result = inv.investigate(inv.InvestigationRequest(question="Q"), provider=nebius.chat_completion, trace=trace)
    assert result["status"] == "error" and len(calls) == 1
    expected_trace = {"event": "failure", "turn": 1, "stage": "http_rejection", "http_status": 400, "provider_code": expected}
    if expected:
        expected_trace["validation_details"] = [{"code": expected}]
    assert trace[-1] == expected_trace
    assert "secret" not in json.dumps(trace) + json.dumps(result)


@pytest.mark.parametrize("error,stage,status", [
    (nebius.urllib.error.URLError("secret"), "network", "error"),
    (nebius.urllib.error.URLError(TimeoutError("secret")), "timeout", "incomplete"),
])
def test_network_diagnostics(monkeypatch, error, stage, status):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    def fail(*a, **k):
        raise error
    monkeypatch.setattr(nebius.urllib.request, "urlopen", fail)
    trace = []
    result = inv.investigate(inv.InvestigationRequest(question="Q"), provider=nebius.chat_completion, trace=trace)
    assert result["status"] == status and trace[-1]["stage"] == stage
    assert "secret" not in json.dumps(trace)


@pytest.mark.parametrize("action,stage", [
    ({"kind": "invalid"}, "action_schema"),
    (tools(), "action_validation"),
    (tools(("get_case_evidence", {"case_id": "unknown"})), "tool_validation"),
    (final("unretrieved"), "evidence_validation"),
])
def test_dispatch_failure_stages(action, stage):
    trace = []
    result = inv.investigate(inv.InvestigationRequest(question="Q"), provider=lambda *a, **k: reply(action), trace=trace)
    assert result["status"] == "error" and trace[-1]["stage"] == stage


def test_documented_direct_schema_reaches_transport(monkeypatch):
    # Nebius's Python example passes model_json_schema() directly, unlike the
    # named envelope also illustrated on the same documentation page.
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    seen = []
    def fake(request, **kwargs):
        seen.append(json.loads(request.data))
        return io.BytesIO(json.dumps(reply(tools())).encode())
    monkeypatch.setattr(nebius.urllib.request, "urlopen", fake)
    inv.investigate(inv.InvestigationRequest(question="Q"), provider=nebius.chat_completion)
    schema = seen[0]["response_format"]["json_schema"]
    assert seen[0]["response_format"] == {"type": "json_schema", "json_schema": inv.Action.model_json_schema()}
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["Finding"]["properties"]["evidence_ids"]["minItems"] == 1
    assert schema["$defs"]["ToolCall"]["properties"]["arguments"]["additionalProperties"] == {"type": "string"}


@pytest.mark.parametrize("body,expected", [
    ({"error": {"param": "response_format.json_schema.schema", "type": "invalid_request_error",
                "code": "invalid_parameter", "message": "Invalid schema: echoed secret", "input": "secret"}},
     [{"location": ["response_format", "json_schema", "schema"], "type": "invalid_request_error",
       "code": "invalid_parameter", "reason": "invalid schema"}]),
    ({"detail": [{"loc": ["body", "response_format", "json_schema", "schema"], "type": "missing",
                  "msg": "Field required", "input": {"Authorization": "Bearer secret"}, "ctx": "secret"}]},
     [{"location": ["body", "response_format", "json_schema", "schema"], "type": "missing",
       "reason": "required field missing"}]),
    ({"error": {"param": "messages.secret", "type": "secret", "code": "Bearer secret",
                "message": "secret prompt text"}}, []),
    ({"detail": [None, "secret", {"loc": ["body", {"input": "secret"}], "msg": "secret"}]}, []),
    ({"error": {"param": "schema", "type": "missing", "message": "Bearer secret"}},
     [{"location": ["schema"], "type": "missing"}]),
])
def test_sanitized_http_400_details(monkeypatch, body, expected):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    attempts = []
    def reject(*a, **k):
        attempts.append(1)
        raise nebius.urllib.error.HTTPError("secret", 400, "secret", {}, io.BytesIO(json.dumps(body).encode()))
    monkeypatch.setattr(nebius.urllib.request, "urlopen", reject)
    trace = []
    result = inv.investigate(inv.InvestigationRequest(question="Q"), provider=nebius.chat_completion, trace=trace)
    assert result["status"] == "error" and result["tool_executions"] == 0 and len(attempts) == 1
    assert trace[-1]["http_status"] == 400
    assert trace[-1].get("validation_details", []) == expected
    assert "secret" not in json.dumps(trace)


def test_error_detail_bounds_and_credential_collision(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "schema")
    assert nebius.http_error_details({"error": {"param": "schema"}}) == []
    assert len(nebius.http_error_details({"detail": [{"type": "missing"}] * 50})) == 4
    assert nebius.http_error_details({"error": {"param": "x" * 10000, "message": "x" * 10000}}) == []


def test_single_manual_probe_is_bounded_and_private(monkeypatch, tmp_path, capsys):
    from scripts import diagnose_nebius as probe
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    attempts = []
    def reject(request, **limits):
        attempts.append(json.loads(request.data))
        assert limits["timeout"] == 20
        raise nebius.urllib.error.HTTPError("secret", 400, "secret", {}, io.BytesIO(
            b'{"detail":[{"loc":["body","response_format"],"type":"missing","msg":"Field required","input":"secret"}]}'))
    monkeypatch.setattr(nebius.urllib.request, "urlopen", reject)
    assert probe.main(["--live"]) == 0
    assert len(attempts) == 1
    payload = attempts[0]
    assert payload["model"] == nebius.DEFAULT_MODEL and payload["max_tokens"] == 128
    assert payload["response_format"]["json_schema"] == inv.Action.model_json_schema()
    assert "reasoning_effort" not in payload
    saved = list(tmp_path.glob("artifacts/nebius-http-probe-*/diagnostic.json"))
    assert len(saved) == 1 and json.loads(saved[0].read_text())["http_status"] == 400
    assert "secret" not in saved[0].read_text() + capsys.readouterr().out
    with pytest.raises(SystemExit):
        probe.main([])
    assert len(attempts) == 1


@pytest.mark.parametrize("raw", [b"not JSON secret", b'{"error":{"message":"' + b"secret" * 1000 + b'"}}'])
def test_http_body_limits_and_malformed_errors(monkeypatch, raw):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    reads = []
    class Body(io.BytesIO):
        def read(self, size=-1):
            reads.append(size)
            return super().read(size)
    def reject(*a, **k):
        raise nebius.urllib.error.HTTPError("secret", 400, "secret", {}, Body(raw))
    monkeypatch.setattr(nebius.urllib.request, "urlopen", reject)
    with pytest.raises(nebius.ProviderError) as caught:
        nebius.chat_completion({}, timeout=1)
    assert reads == [4097]
    assert caught.value.diagnostic == {"stage": "http_rejection", "http_status": 400, "provider_code": None}
