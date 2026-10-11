"""Reproducible source/config/case-manifest provenance for fresh benchmarks."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "autoframe3d/__init__.py",
    "autoframe3d/cli.py",
    "autoframe3d/provenance.py",
    "autoframe3d/geometry.py",
    "autoframe3d/experiment.py",
    "autoframe3d/agent.py",
    "autoframe3d/campaign.py",
    "autoframe3d/simplify.py",
    "autoframe3d/cases.py",
    "autoframe3d/tless_adapter.py",
    "autoframe3d/tless_metrics.py",
    "autoframe3d/tless_benchmark.py",
    "autoframe3d/tless_cases.py",
    "autoframe3d/tless_search.py",
    "autoframe3d/api.py",
    "scripts/tless_benchmark.py",
    "scripts/tless_data.py",
    "scripts/tless_search.py",
    "scripts/replay_tless.py",
    "pyproject.toml",
    "frontend/package-lock.json",
    "configs/tless_frozen.json",
)
PACKAGE_NAMES = (
    "numpy", "scipy", "Pillow", "fastapi", "pydantic", "uvicorn",
    "huggingface_hub",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_provenance_manifest(case_manifest_path: Path) -> dict[str, Any]:
    """Hash an explicit allowlist plus one case manifest; exclude data/secrets/reports/caches."""
    relative_case_path = case_manifest_path.resolve().relative_to(ROOT.resolve()).as_posix()
    if not relative_case_path.startswith("data/tless/manifests/"):
        raise ValueError("Replay case manifests must live under data/tless/manifests")
    relative_paths = sorted(set((*SOURCE_FILES, relative_case_path)))
    files: list[dict[str, Any]] = []
    for relative_path in relative_paths:
        path = ROOT / relative_path
        if not path.is_file():
            raise FileNotFoundError(f"Provenance input is missing: {relative_path}")
        files.append({
            "path": relative_path,
            "size_bytes": path.stat().st_size,
            "sha256": file_sha256(path),
        })
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    package_versions: dict[str, str | None] = {}
    for package in PACKAGE_NAMES:
        try:
            package_versions[package] = version(package)
        except PackageNotFoundError:
            package_versions[package] = None
    dataset_provenance_path = ROOT / "data" / "tless" / "provenance.json"
    dataset_provenance = json.loads(dataset_provenance_path.read_text(encoding="utf-8"))
    frozen_config = json.loads((ROOT / "configs" / "tless_frozen.json").read_text(encoding="utf-8"))
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "platform": platform.platform(),
        "package_versions": package_versions,
        "git_commit": None,
        "git_status": "unavailable_no_git_metadata",
        "dataset": {
            "repository": dataset_provenance["repository"],
            "revision": dataset_provenance["revision"],
            "license": dataset_provenance["license"],
        },
        "case_manifest": relative_case_path,
        "seeds": {
            "registration_random_seed_config": frozen_config["registration"]["random_seed"],
            "case_selection": "fixed manifest case IDs; replay has no stochastic search",
        },
        "excluded": [".env/secrets", "datasets", "generated reports/results", "caches", "this provenance manifest"],
        "files": files,
        "combined_sha256": hashlib.sha256(canonical).hexdigest(),
    }