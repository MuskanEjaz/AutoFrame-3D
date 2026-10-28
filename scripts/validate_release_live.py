"""Opt-in: one diagnostic then dev-01/dev-02/dev-13 once; ten requests maximum."""
import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autoframe3d import answer_evaluation, investigation, nebius
from scripts.diagnose_nebius import run_probe
ITEMS = ("dev-01", "dev-02", "dev-13")
MAX_REQUESTS = 10


def run_release(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    requests = 0
    original = nebius.chat_completion
    rows = []
    summary = {"provider_requests": 0, "attempted_items": [], "stop_reason": None,
               "manual_review": "Required: completion, pairing, numbers/units, citations, recorded/GT scope and abstention"}

    def bounded(payload, *, timeout, max_response_bytes):
        nonlocal requests
        cap = 128 if requests == 0 else 1200
        if requests >= MAX_REQUESTS or payload.get("max_tokens", cap + 1) > cap or not 0 < timeout <= 20 or max_response_bytes != 32768:
            raise RuntimeError("Release validation request limit violated")
        requests += 1
        return original(payload, timeout=timeout, max_response_bytes=max_response_bytes)

    nebius.chat_completion = bounded
    try:
        diagnostic = directory / "diagnostic"
        diagnostic.mkdir()
        result = run_probe(diagnostic)
        summary["diagnostic"] = result
        if result.get("stage") != "response_received":
            summary["stop_reason"] = "diagnostic_did_not_succeed"
        else:
            rubric = json.loads(answer_evaluation.RUBRIC.read_text(encoding="utf-8"))
            selected = {q["id"]: q for q in rubric["questions"] if q["split"] == "development" and q["id"] in ITEMS}
            if set(selected) != set(ITEMS):
                raise ValueError("Authorized development items missing")
            with (directory / "capture.jsonl").open("x", encoding="utf-8") as handle:
                for item_id in ITEMS:
                    trace = []
                    response = investigation.investigate(investigation.InvestigationRequest(question=selected[item_id]["question"]), trace=trace)
                    row = {"item_id": item_id, "response": response, "trace": trace}
                    handle.write(json.dumps(row, allow_nan=False) + "\n")
                    handle.flush()
                    rows.append(row)
                    summary["attempted_items"].append(item_id)
                    if response.get("operational_error", {}).get("stage") in {"http_rejection", "invalid_credentials", "setup", "provider"}:
                        summary["stop_reason"] = "operational_rejection_no_further_items"
                        break
            with (directory / "report.json").open("x", encoding="utf-8") as handle:
                json.dump(answer_evaluation.evaluate(rows, split="development"), handle, indent=2, allow_nan=False)
    finally:
        nebius.chat_completion = original
        summary["provider_requests"] = requests
        with (directory / "summary.json").open("x", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, allow_nan=False)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if not args.live:
        parser.error("Explicit --live required; at most ten requests, no retries")
    if not nebius.configured():
        parser.error("Configure process credential securely; no secret files are loaded")
    directory = args.output or Path("artifacts") / ("release-live-" + uuid4().hex)
    result = run_release(directory)
    print(json.dumps({"output": str(directory), **result}))
    return 0 if result["stop_reason"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
