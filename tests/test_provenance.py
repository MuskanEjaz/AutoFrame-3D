"""Tests for reproducible provenance capturing and verification."""

from __future__ import annotations

import json
from pathlib import Path

from autoframe3d.provenance import build_provenance_manifest, ROOT


def test_provenance_unchanged_inputs_produce_identical_hashes(tmp_path):
    manifest_path = ROOT / "data" / "tless" / "manifests" / "smoke20.json"
    first = build_provenance_manifest(manifest_path)
    second = build_provenance_manifest(manifest_path)
    assert first["combined_sha256"] == second["combined_sha256"]


def test_provenance_content_change_alters_hash(tmp_path):
    manifest_path = ROOT / "data" / "tless" / "manifests" / "smoke20.json"
    original = build_provenance_manifest(manifest_path)

    # Modify a source file temporarily
    target = ROOT / "autoframe3d" / "tless_metrics.py"
    content = target.read_text(encoding="utf-8")
    try:
        target.write_text(content + "\n# provenance test edit", encoding="utf-8")
        modified = build_provenance_manifest(manifest_path)
        assert original["combined_sha256"] != modified["combined_sha256"]
    finally:
        target.write_text(content, encoding="utf-8")


def test_provenance_inventory_ordering_is_deterministic(tmp_path):
    manifest_path = ROOT / "data" / "tless" / "manifests" / "smoke20.json"
    prov = build_provenance_manifest(manifest_path)
    paths = [item["path"] for item in prov["files"]]
    assert paths == sorted(paths)
