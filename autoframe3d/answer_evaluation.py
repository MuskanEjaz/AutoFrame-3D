"""Offline protocol/numerical evaluation. Semantic answer quality requires review."""
import hashlib
import json
import math
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator

from autoframe3d import investigation, recorded_demo

RUBRIC = recorded_demo.ROOT / "audit_evidence/investigation_evaluation.json"


class SavedResponse(investigation.Strict):
    status: Literal["complete", "insufficient", "incomplete", "error", "unavailable"]
    analysis_mode: Literal["live", "mocked", "unavailable"]
    evidence_computation: Literal["recorded"]
    question: str
    selected_case_id: str | None
    message: str
    model: str
    findings: list[investigation.Finding]
    evidence: list[dict]
    identity: dict
    model_turns: int = Field(ge=0, le=investigation.MAX_TURNS)
    tool_executions: int = Field(ge=0, le=investigation.MAX_TOOLS)
    runtime_seconds: float = Field(ge=0, allow_inf_nan=False)
    prose_verification: str
    operational_error: dict | None = None

    @field_validator("operational_error")
    @classmethod
    def safe_operational_error(cls, value):
        if value is not None and value != investigation._public_operational_error(value):
            raise ValueError("Operational diagnostics must use bounded public vocabulary")
        return value

    @field_validator("evidence")
    @classmethod
    def stable_ids(cls, value):
        if any(not isinstance(e.get("id"), str) or not e["id"] for e in value):
            raise ValueError("Evidence requires stable string IDs")
        return value


def corpus():
    tools = investigation.EvidenceTools()
    records = {}
    calls = [investigation.ToolCall(name="list_available_cases", arguments={}),
             investigation.ToolCall(name="get_benchmark_summary", arguments={})]
    for case in tools.data["cases"]:
        for method in case["variants"]:
            calls.append(investigation.ToolCall(name="get_case_evidence", arguments={
                "case_id": case["case_id"], "method_id": method["id"]}))
        calls.append(investigation.ToolCall(name="compare_recorded_methods", arguments={"case_id": case["case_id"]}))
    for call in calls:
        result = tools.execute(call)
        records[result["id"]] = result
    return tools, records


def differences(actual, expected, path=""):
    """No keyword/semantic inference; compare the complete structured record."""
    if type(actual) is not type(expected):
        if type(actual) in (int, float) and type(expected) in (int, float):
            pass
        else:
            return [path + ": type"]
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            return [path + ": fields"]
        return [d for key in expected for d in differences(actual[key], expected[key], path + "." + key)]
    if isinstance(expected, list):
        if len(actual) != len(expected):
            return [path + ": length"]
        return [d for i, value in enumerate(expected) for d in differences(actual[i], value, path + f".{i}")]
    if type(expected) in (int, float):
        return [] if math.isfinite(actual) and abs(actual - expected) <= 1e-9 else [path + ": numeric"]
    return [] if actual == expected else [path + ": value"]


def at(record, path):
    for key in path.split("."):
        record = record[key]
    return record


def evaluate_item(item, saved, tools, records):
    review = {"prose_entailment": "human_review_required", "completeness": "human_review_required",
              "unsupported_claims": "human_review_required", "appropriate_abstention": "human_review_required",
              "required_prose": item["required_prose"], "forbidden_conclusions": item["forbidden_conclusions"]}
    result = {"id": item["id"], "category": item["category"], "expected_behavior": item["expected_behavior"],
              "task_completion": "missing", "schema": "missing", "evidence_citation_validity": "missing",
              "retrieval_coverage": "missing", "citation_validity": "missing",
              "numerical_accuracy": "missing", "tool_trace": "missing", "expected_abstention": "missing",
              "human_review": review, "errors": [], "telemetry": {"requests": None, "latency_seconds": None,
                                                                         "token_usage": None}}
    if saved is None:
        result["errors"].append("Missing saved response; retained in denominator")
        return result
    result["fixture_label"] = saved.get("fixture_label")
    try:
        response = SavedResponse.model_validate(saved["response"])
    except (KeyError, ValidationError):
        result.update(schema="fail", task_completion="fail")
        result["errors"].append("Invalid response schema")
        return result
    result["schema"] = "pass"
    expected_status = "insufficient" if item["expected_behavior"] == "abstain" else "complete"
    complete = response.status == expected_status and bool(response.findings)
    result["task_completion"] = "status_pass_review_required" if complete else "fail"
    result["expected_abstention"] = ("status_pass_review_required" if response.status == "insufficient" else "fail") if item["expected_behavior"] == "abstain" else "not_expected"
    if response.question != item["question"]:
        result["errors"].append("Response question does not match item")
        result["task_completion"] = "fail"
    if response.selected_case_id is not None:
        try:
            tools.case(response.selected_case_id)
        except ValueError:
            result["errors"].append("Fabricated selected case")
            result["task_completion"] = "fail"
    if response.status in {"complete", "insufficient"} and response.identity != tools.identity:
        result["errors"].append("Current evidence identity mismatch or absent")
    ids = [e.get("id") for e in response.evidence]
    citation_errors = ["Duplicate/unknown evidence ID"] if len(set(str(i) for i in ids)) != len(ids) or any(i not in records for i in ids) else []
    numeric_errors = []
    reference_errors = []
    for record in response.evidence:
        if record.get("id") in records:
            diff = differences(record, records[record["id"]])
            citation_errors.extend("Evidence content " + d for d in diff)
            numeric_errors.extend(d for d in diff if d.endswith(": numeric") or "rmse" in d or "unit" in d)
    for finding in response.findings:
        for ref in finding.evidence_ids:
            if ref not in ids or ref not in records:
                reference_errors.append("Unknown/unreturned citation: " + ref)
    citation_errors.extend(reference_errors)
    missing_ids = set(item["required_evidence_ids"]) - set(str(i) for i in ids)
    if missing_ids:
        citation_errors.append("Required evidence absent: " + ", ".join(sorted(missing_ids)))

    trace = saved.get("trace")
    retrieved = set()
    trace_errors = []
    requests = []
    returns = []
    attempts = {}
    resolved = set()
    if trace is not None:
        try:
            for event in trace:
                kind = event["event"]
                if kind == "provider_start":
                    if type(event["turn"]) is not int or event["turn"] != len(requests) + 1 or not 0 < event["timeout_seconds"] <= 20:
                        trace_errors.append("Invalid provider turn/timeout")
                    if len(returns) != len(requests):
                        trace_errors.append("Provider call before previous return")
                    requests.append(event)
                elif kind == "provider_result":
                    if event["turn"] != len(requests) or event["turn"] in [e["turn"] for e in returns]:
                        trace_errors.append("Invalid provider result order")
                    returns.append(event)
                elif kind == "tool_attempt":
                    index = event["attempt"]
                    if type(index) is not int or index != len(attempts) + 1 or not requests or len(returns) != len(requests):
                        trace_errors.append("Invalid tool attempt order")
                    call = investigation.ToolCall.model_validate(event["call"])
                    attempts[index] = call
                    tools.execute(call)  # Deterministic allowlist/argument validation only.
                elif kind == "tool_result":
                    index = event["attempt"]
                    if index in resolved or index not in attempts:
                        trace_errors.append("Result without distinct preceding attempt")
                        continue
                    resolved.add(index)
                    authoritative = tools.execute(attempts[index])
                    if differences(event["output"], authoritative):
                        trace_errors.append("Tool result differs from authoritative output")
                    else:
                        retrieved.add(authoritative["id"])
                else:
                    trace_errors.append("Unknown trace event")
            if len(requests) > investigation.MAX_TURNS or len(attempts) > investigation.MAX_TOOLS:
                trace_errors.append("Request/tool budget exceeded")
            if (len(requests), len(attempts)) != (response.model_turns, response.tool_executions):
                trace_errors.append("Response counters disagree with trace")
            if complete and (len(returns) != len(requests) or len(resolved) != len(attempts)):
                trace_errors.append("Completed response has unfinished trace")
            if set(str(i) for i in ids) != retrieved:
                citation_errors.append("Evidence was not actually retrieved according to trace")
            if response.runtime_seconds > investigation.DEADLINE_SECONDS + 1:
                trace_errors.append("Deadline exceeded (1 second bookkeeping allowance)")
            usage = [e.get("usage") for e in returns]
            for u in usage:
                if u is not None and (not isinstance(u, dict) or not u or not set(u) <= {"prompt_tokens", "completion_tokens", "total_tokens"} or any(type(v) is not int or v < 0 for v in u.values()) or u.get("completion_tokens", 0) > 1200):
                    trace_errors.append("Invalid token usage or output token budget")
            result["telemetry"] = {"requests": len(requests), "latency_seconds": response.runtime_seconds,
                                    "token_usage": {"per_return": usage, "complete": len(returns) == len(requests) and all(isinstance(u, dict) and set(u) == {"prompt_tokens", "completion_tokens", "total_tokens"} for u in usage)} if returns else None}
        except (KeyError, TypeError, ValueError, ValidationError):
            trace_errors.append("Malformed trace or invalid tool arguments")
        result["tool_trace"] = "fail" if trace_errors else "pass"
    else:
        result["tool_trace"] = "unverified_no_trace"
    result["evidence_citation_validity"] = "fail" if citation_errors else ("pass" if trace is not None and not trace_errors else "unverified")
    result["retrieval_coverage"] = "fail" if missing_ids else ("pass" if trace is not None and not trace_errors and set(item["required_evidence_ids"]) <= retrieved else "unverified")
    cited = {ref for finding in response.findings for ref in finding.evidence_ids}
    result["citation_validity"] = "fail" if reference_errors or (trace is not None and not cited <= retrieved) else ("pass" if trace is not None and not trace_errors else "unverified")
    if response.status in {"complete", "insufficient"} and response.identity != tools.identity:
        result["evidence_citation_validity"] = "fail"
    for fact in item["required_facts"]:
        if fact["evidence_id"] not in ids:
            numeric_errors.append("Required structured fact unavailable: " + fact["path"])
    # Optional manually extracted claims are supplemental; prose is never auto-certified.
    allowed = {(f["evidence_id"], f["path"]): f for f in item["required_facts"]}
    for claim in saved.get("numerical_claims", []):
        try:
            spec = allowed[(claim["evidence_id"], claim["path"])]
            value = claim["value"]
            if claim["unit"] != spec["unit"] or type(value) not in (int, float) or not math.isfinite(value) or abs(value - spec["value"]) > spec["absolute_tolerance"]:
                numeric_errors.append("Wrong numerical claim/unit: " + claim["path"])
        except (KeyError, TypeError):
            numeric_errors.append("Unknown/malformed numerical claim")
    result["numerical_accuracy"] = "fail" if numeric_errors else ("structured_pass_prose_review_required" if response.evidence else "unverified")
    result["errors"].extend(citation_errors + numeric_errors + trace_errors)
    # Status alone cannot satisfy the requested task. Missing comparison cards,
    # incorrect facts, invalid citations/provenance or broken traces stay failures.
    if citation_errors or numeric_errors or trace_errors or (
        response.status in {"complete", "insufficient"} and response.identity != tools.identity
    ):
        result["task_completion"] = "fail"
        if item["expected_behavior"] == "abstain":
            result["expected_abstention"] = "fail"
    return result


def evaluate(saved_rows, *, split="development", rubric_path=RUBRIC):
    rubric = json.loads(Path(rubric_path).read_text(encoding="utf-8"))
    tools, records = corpus()
    if rubric["evidence_identity"] != tools.identity:
        raise ValueError("Rubric evidence identity differs from current corpus")
    if split not in {"all", "development", "reserved"}:
        raise ValueError("Unknown evaluation split")
    for item in rubric["questions"]:
        if not set(item["required_evidence_ids"]) <= records.keys():
            raise ValueError("Rubric references unavailable evidence")
        for fact in item["required_facts"]:
            if at(records[fact["evidence_id"]], fact["path"]) != fact["value"] or fact["absolute_tolerance"] < 0:
                raise ValueError("Rubric fact differs from authoritative evidence")
    ids = {q["id"] for q in rubric["questions"]}
    saved = {}
    for row in saved_rows:
        if row["item_id"] not in ids or row["item_id"] in saved:
            raise ValueError("Unknown or duplicate evaluation item ID")
        saved[row["item_id"]] = row
    items = [q for q in rubric["questions"] if split == "all" or q["split"] == split]
    results = [evaluate_item(item, saved.get(item["id"]), tools, records) for item in items]
    dimensions = ["schema", "task_completion", "retrieval_coverage", "citation_validity", "evidence_citation_validity", "numerical_accuracy", "tool_trace", "expected_abstention"]
    summary = {d: {status: sum(r[d] == status for r in results) for status in sorted({r[d] for r in results})} for d in dimensions}
    summary["unsupported_claim_review"] = {"human_review_required": len(results)}
    return {"schema_version": 1, "split": split, "denominator": len(items), "dimensions": summary,
            "quality_scope": "Protocol/cards/optional extracted numbers only; no automated semantic PASS or overall score",
            "fixture_rows": sum(bool(r.get("fixture_label")) for r in results),
            "rubric_sha256": hashlib.sha256(Path(rubric_path).read_bytes()).hexdigest(),
            "evidence_identity": tools.identity, "results": results}
