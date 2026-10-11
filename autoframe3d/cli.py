"""Command-line entry points for AutoFrame 3D's reproducible core experiment."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

import numpy as np

from autoframe3d.experiment import bounded_search, evaluate
from autoframe3d.cases import replay_bundle


def _json_safe(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _write_result(result: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    mesh = result["mesh"]
    vertices, faces = mesh.vertices, mesh.faces
    with (output_dir / "cad_mesh.obj").open("w", encoding="ascii") as file:
        for vertex in vertices:
            file.write("v %.8f %.8f %.8f\n" % tuple(vertex))
        for face in faces + 1:
            file.write("f %d %d %d\n" % tuple(face))
    np.savetxt(output_dir / "scan.xyz", result["scan"], fmt="%.8f")
    summary = {key: value for key, value in result.items() if key not in {"mesh", "scan"}}
    (output_dir / "result.json").write_text(
        json.dumps(_json_safe(summary), indent=2), encoding="utf-8"
    )
    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "scipy", "fastapi", "pydantic")
        },
    }
    (output_dir / "environment.json").write_text(
        json.dumps(environment, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="autoframe3d")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="run one documented experiment")
    run_parser.add_argument("--visibility", choices=("top", "front", "all"), default="top")
    run_parser.add_argument("--object", choices=("near_symmetric", "asymmetric_control"), default="near_symmetric")
    run_parser.add_argument("--seed", type=int, default=41)
    run_parser.add_argument("--yaw", type=float, default=23.0, help="synthetic ground-truth yaw in degrees")
    run_parser.add_argument("--output", type=Path, default=Path("artifacts/sample"))
    search_parser = commands.add_parser("search", help="run the bounded deterministic search")
    search_parser.add_argument("--budget", type=int, default=12)
    search_parser.add_argument("--output", type=Path, default=Path("artifacts/search"))
    replay_parser = commands.add_parser("replay", help="recompute a saved case bundle")
    replay_parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    if args.command == "replay":
        result = replay_bundle(args.bundle)
        print(json.dumps(result, indent=2))
        if not result["passed"]:
            raise SystemExit(1)
        return
    if args.command == "run":
        from autoframe3d.experiment import ExperimentConfig

        results = [evaluate(ExperimentConfig(
            object_kind=args.object,
            visibility=args.visibility,
            seed=args.seed,
            yaw_deg=args.yaw,
        ))]
    else:
        results = bounded_search(args.budget)
    for index, result in enumerate(results):
        destination = args.output if len(results) == 1 else args.output / f"case-{index:02d}"
        _write_result(result, destination)
        print(json.dumps({
            "case": str(destination),
            "classification": result["classification"],
            "alignment_quality_metrics": result["alignment_quality_metrics"],
            "pose_errors": result["pose_errors"],
        }, indent=2))


if __name__ == "__main__":
    main()