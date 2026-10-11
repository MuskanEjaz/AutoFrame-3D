"""CLI for the resumable custom internal T-LESS BOP19 evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autoframe3d.tless_benchmark import generate_manifests, run_manifest, write_diagnostic


def main() -> None:
    parser = argparse.ArgumentParser(prog="autoframe3d-tless")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("manifests", help="generate fixed scene-separated manifests")
    diagnostic = commands.add_parser("diagnostic", help="write GT-only coordinate/depth overlay")
    diagnostic.add_argument("--manifest", default="smoke20")
    evaluate = commands.add_parser("evaluate", help="resume one fixed manifest")
    evaluate.add_argument("manifest", choices=("smoke20", "smoke20_frozen", "development", "development_tuning20", "heldout200", "all_eligible"))
    evaluate.add_argument("--group", choices=("original", "perturbed"), default="original")
    evaluate.add_argument("--limit", type=int)
    evaluate.add_argument("--workers", type=int, default=1)
    evaluate.add_argument("--no-resume", action="store_true")
    all_parser = commands.add_parser("all", help="resume all eligible instances in the downloaded subset")
    all_parser.add_argument("--group", choices=("original", "perturbed"), default="original")
    all_parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.command == "manifests":
        result = generate_manifests()
    elif args.command == "diagnostic":
        result = {"overlay": str(write_diagnostic(args.manifest).relative_to(ROOT))}
    elif args.command == "all":
        result = run_manifest("all_eligible", group=args.group, workers=args.workers)
    else:
        result = run_manifest(
            args.manifest, group=args.group, limit=args.limit, workers=args.workers,
            resume=not args.no_resume,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()