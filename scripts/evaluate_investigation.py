"""Score saved JSONL offline; explicit bounded --live capture is disabled by default."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autoframe3d import answer_evaluation as evaluation, investigation, nebius


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--responses", type=Path, help="Saved JSONL, one {item_id,response,trace} per attempted item")
    parser.add_argument("--split", choices=["development", "reserved", "all"], default="development")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--live", action="store_true", help="Explicitly authorize bounded provider requests; never loads .env")
    parser.add_argument("--capture", type=Path, help="New JSONL capture for --live; refuses overwrite")
    parser.add_argument("--item", action="append", help="Restrict live attempts to listed IDs; unattempted split items remain in denominator")
    args = parser.parse_args(argv)
    if args.report.exists():
        parser.error("Report already exists; choose a new path")
    if not args.report.parent.is_dir():
        parser.error("Report parent directory must already exist")
    if args.live:
        if args.responses or not args.capture:
            parser.error("--live requires --capture and excludes --responses")
        if not nebius.configured():
            parser.error("Live capture requires server-process NEBIUS_API_KEY; no .env is loaded")
        rubric = json.loads(evaluation.RUBRIC.read_text(encoding="utf-8"))
        selected = [q for q in rubric["questions"] if args.split == "all" or q["split"] == args.split]
        if args.item:
            if len(set(args.item)) != len(args.item) or not set(args.item) <= {q["id"] for q in selected}:
                parser.error("--item IDs must be distinct and belong to selected split")
            selected = [q for q in selected if q["id"] in args.item]
        # One investigation per selected item; no retry. Existing dispatcher enforces 3 turns.
        rows = []
        with args.capture.open("x", encoding="utf-8") as handle:
            for item in selected:
                trace = []
                response = investigation.investigate(investigation.InvestigationRequest(question=item["question"]), trace=trace)
                row = {"item_id": item["id"], "response": response, "trace": trace}
                handle.write(json.dumps(row, allow_nan=False) + "\n")
                handle.flush()  # Preserve failures and progress; never discard failed runs.
                rows.append(row)
    else:
        if args.capture or args.item:
            parser.error("--capture/--item require --live")
        rows = [json.loads(line) for line in args.responses.read_text(encoding="utf-8").splitlines() if line.strip()] if args.responses else []
    report = evaluation.evaluate(rows, split=args.split)
    with args.report.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"split": report["split"], "denominator": report["denominator"], "dimensions": report["dimensions"]}))
    return 0  # A written evaluation is not a model-quality pass.


if __name__ == "__main__":
    raise SystemExit(main())
