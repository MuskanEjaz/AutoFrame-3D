"""Explicit opt-in live smoke; one investigation, no retries or registration."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autoframe3d.investigation import InvestigationRequest, investigate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Authorize up to three paid model turns")
    args = parser.parse_args()
    if not args.live:
        parser.error("Live inference is opt-in: use --live only when authorized; no request sent")
    result = investigate(InvestigationRequest(question="Compare the recorded refinement whose RMSE improved while pose correctness worsened. Cite supporting evidence."))
    # Do not print prompts, credentials, provider payloads, or unverified model prose.
    print(json.dumps({k: result[k] for k in ("status", "analysis_mode", "message", "model", "model_turns", "tool_executions", "runtime_seconds", "identity")}, indent=2))
    print("Validated evidence IDs:", [e["id"] for e in result["evidence"]])
    return 0 if result["status"] == "complete" and any(e["id"].startswith("comparison:") for e in result["evidence"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
