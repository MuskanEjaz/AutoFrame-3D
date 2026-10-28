"""Hand-authored evaluator verification, never Nemotron model-quality results."""
import copy
import json
from pathlib import Path

import pytest

from autoframe3d import answer_evaluation as ev, investigation
from scripts.evaluate_investigation import main

FIXTURES = Path(__file__).parent / "fixtures/answer_evaluation"


def fixture(name):
    return json.loads((FIXTURES / (name + ".json")).read_text(encoding="utf-8"))


def score(row):
    return next(r for r in ev.evaluate([row])["results"] if r["id"] == row["item_id"])


def test_supported_fixture_protocol_pass_is_not_semantic_pass():
    row = score(fixture("supported"))
    assert row["schema"] == row["evidence_citation_validity"] == row["tool_trace"] == "pass"
    assert row["numerical_accuracy"] == "structured_pass_prose_review_required"
    assert row["task_completion"] == "status_pass_review_required"
    assert row["human_review"]["unsupported_claims"] == "human_review_required"
    assert row["telemetry"]["token_usage"]["complete"] is False


@pytest.mark.parametrize("name", ["wrong_number", "wrong_unit"])
def test_wrong_structured_number_or_extracted_unit_detected(name):
    row = score(fixture(name))
    assert row["numerical_accuracy"] == "fail"
    assert row["tool_trace"] == "pass"


@pytest.mark.parametrize("name", ["unsupported_citation", "fabricated_case"])
def test_unretrieved_citation_and_fabricated_case_detected(name):
    assert score(fixture(name))["evidence_citation_validity"] == "fail"


def test_semantic_overclaim_never_auto_passes():
    row = score(fixture("gt_free_overclaim"))
    assert row["evidence_citation_validity"] == "pass"
    assert row["expected_abstention"] == "status_pass_review_required"
    assert row["human_review"]["unsupported_claims"] == "human_review_required"
    assert "GT-free wrong-pose detector proven" in row["human_review"]["forbidden_conclusions"]


def test_appropriate_insufficient_requires_review():
    row = score(fixture("appropriate_insufficient"))
    assert row["expected_abstention"] == "status_pass_review_required"
    assert row["human_review"]["appropriate_abstention"] == "human_review_required"


@pytest.mark.parametrize("name", ["provider_failure", "incomplete"])
def test_failure_and_missing_results_stay_in_denominator(name):
    report = ev.evaluate([fixture(name)])
    assert report["denominator"] == 15
    assert report["dimensions"]["task_completion"] == {"fail": 1, "missing": 14}
    assert report["results"][0]["telemetry"]["requests"] == 1


def test_trace_missing_does_not_prove_retrieval():
    row = fixture("supported")
    del row["trace"]
    result = score(row)
    assert result["evidence_citation_validity"] == "unverified"
    assert result["tool_trace"] == "unverified_no_trace"


def test_known_returned_card_not_retrieved_is_rejected():
    row = fixture("supported")
    row["trace"] = row["trace"][:2] + row["trace"][-2:]
    row["response"]["tool_executions"] = 0
    assert score(row)["evidence_citation_validity"] == "fail"


def test_invalid_tool_arguments_and_trace_budget():
    row = fixture("supported")
    row["trace"][2]["call"]["arguments"]["path"] = "unapproved"
    assert score(row)["tool_trace"] == "fail"


def test_invalid_usage_and_tool_before_provider_return():
    row = fixture("supported")
    row["trace"][1]["usage"] = ["malformed fixture"]
    assert score(row)["tool_trace"] == "fail"
    row = fixture("supported")
    row["trace"][1], row["trace"][2] = row["trace"][2], row["trace"][1]
    assert score(row)["tool_trace"] == "fail"
    row = fixture("supported")
    row["trace"][1]["usage"] = {"completion_tokens": 1201}
    assert score(row)["tool_trace"] == "fail"
    row = fixture("supported")
    row["trace"].append({"event": "provider_start", "turn": 3, "timeout_seconds": 20.0})
    row["trace"].append({"event": "provider_start", "turn": 4, "timeout_seconds": 20.0})
    assert score(row)["tool_trace"] == "fail"


def test_duplicate_result_and_invalid_schema():
    row = fixture("supported")
    row["trace"].append(copy.deepcopy(row["trace"][3]))
    assert score(row)["tool_trace"] == "fail"
    row = fixture("supported")
    row["response"]["model_turns"] = 4
    assert score(row)["schema"] == "fail"


def test_telemetry_only_reports_available_usage():
    row = fixture("supported")
    for event in row["trace"]:
        if event["event"] == "provider_result":
            event["usage"] = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    result = score(row)
    assert result["telemetry"]["requests"] == 2
    assert result["telemetry"]["latency_seconds"] == 0.01
    assert result["telemetry"]["token_usage"]["complete"] is True
    assert len(result["telemetry"]["token_usage"]["per_return"]) == 2


def test_declared_split_and_facts_match_current_evidence():
    assert ev.evaluate([], split="reserved")["denominator"] == 5
    assert ev.evaluate([], split="all")["denominator"] == 20
    rubric = json.loads(ev.RUBRIC.read_text(encoding="utf-8"))
    assert len({q["id"] for q in rubric["questions"]}) == 20
    assert len({q["question"] for q in rubric["questions"]}) == 20
    assert "not an independent scientific holdout" in rubric["split_policy"]
    with pytest.raises(ValueError, match="duplicate"):
        ev.evaluate([fixture("supported"), fixture("supported")])


def test_live_default_off_and_explicit_missing_key_blocked(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No provider call authorized in harness verification")
    monkeypatch.setattr(investigation, "investigate", forbidden)
    assert main(["--report", str(tmp_path / "offline.json")]) == 0
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        main(["--live", "--capture", str(tmp_path / "capture.jsonl"), "--report", str(tmp_path / "live.json")])
    assert not (tmp_path / "capture.jsonl").exists()


def test_trace_observes_actual_dispatch_without_provider_calls():
    source = fixture("supported")
    call = source["trace"][2]["call"]
    actions = iter([{"kind": "tools", "calls": [call], "findings": []},
                    {"kind": "final", "calls": [], "findings": source["response"]["findings"]}])
    def mocked_provider(*args, **kwargs):
        return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(next(actions))}}]}
    trace = []
    response = investigation.investigate(investigation.InvestigationRequest(question=source["response"]["question"]), provider=mocked_provider, trace=trace)
    assert score({"item_id": "dev-01", "response": response, "trace": trace})["evidence_citation_validity"] == "pass"
    assert len([e for e in trace if e["event"] == "provider_start"]) == 2


@pytest.mark.parametrize("failure", ["timeout", "invalid_response"])
def test_failed_injected_provider_still_captures_request(failure):
    def mocked_provider(*args, **kwargs):
        if failure == "timeout":
            raise TimeoutError("Hand-authored fixture timeout")
        return None
    source = fixture("supported")
    trace = []
    response = investigation.investigate(investigation.InvestigationRequest(question=source["response"]["question"]), provider=mocked_provider, trace=trace)
    result = score({"item_id": "dev-01", "response": response, "trace": trace})
    assert result["task_completion"] == "fail"
    assert result["telemetry"]["requests"] == 1


def test_operational_diagnostics_preserve_strict_saved_response_validation():
    from autoframe3d.answer_evaluation import SavedResponse
    from pydantic import ValidationError
    source = fixture("supported")["response"]
    safe = {**source, "operational_error": {"stage": "http_rejection", "http_status": 401}}
    assert SavedResponse.model_validate(safe).operational_error["http_status"] == 401
    with pytest.raises(ValidationError):
        SavedResponse.model_validate({**source, "operational_error": {"stage": "http_rejection", "body": "PRIVATE"}})


def test_unavailable_comparison_is_authoritative_but_does_not_satisfy_required_comparison():
    from autoframe3d.answer_evaluation import corpus
    _, records = corpus()
    unavailable = records["comparison-unavailable:tless-s000001-i000001-g00-o02"]
    assert unavailable["status"] == "unavailable" and "baseline" not in unavailable
    assert "comparison:tless-s000001-i000001-g00-o02" not in records


@pytest.mark.parametrize("status", ["complete", "insufficient"])
def test_unavailable_evidence_cannot_complete_requested_comparison(status):
    tools, records = ev.corpus()
    item = next(q for q in json.loads(ev.RUBRIC.read_text(encoding="utf-8"))["questions"]
                if q["split"] == "development" and q["id"] == "dev-02")
    card = records["comparison-unavailable:tless-s000001-i000001-g00-o02"]
    row = fixture("supported")
    row["item_id"] = item["id"]
    row["response"].update(status=status, question=item["question"], evidence=[card], identity=tools.identity,
        findings=[{"kind": "limitation", "text": card["message"], "evidence_ids": [card["id"]]}])
    row.pop("trace", None)
    result = score(row)
    assert result["task_completion"] == "fail"
    assert result["retrieval_coverage"] == result["numerical_accuracy"] == "fail"


def test_provider_error_is_not_abstention_for_requested_missing_measurements():
    row = fixture("appropriate_insufficient")
    row["response"].update(status="error", findings=[], evidence=[],
        operational_error={"stage": "http_rejection", "http_status": 401})
    row.pop("trace", None)
    result = score(row)
    assert result["task_completion"] == result["expected_abstention"] == "fail"
