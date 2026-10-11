"""Tests for provenance checkpoint validation and rejection."""

from __future__ import annotations

import json
from pathlib import Path

from autoframe3d.provenance import build_provenance_manifest, ROOT
from autoframe3d.tless_benchmark import verify_or_read_checkpoint


def test_verify_or_read_checkpoint_rejects_missing_provenance(tmp_path):
    manifest_path = ROOT / "data" / "tless" / "manifests" / "smoke20.json"
    ckpt = tmp_path / "smoke20.jsonl"
    # Write a record without provenance
    ckpt.write_text(json.dumps({"case_id": "test-case-1", "status": "valid"}) + "\n", encoding="utf-8")

    try:
        verify_or_read_checkpoint(ckpt, manifest_path)
        assert False, "Expected ValueError for missing provenance"
    except ValueError as error:
        assert "provenance" in str(error).lower()


def test_verify_or_read_checkpoint_accepts_matching_provenance(tmp_path):
    manifest_path = ROOT / "data" / "tless" / "manifests" / "smoke20.json"
    prov = build_provenance_manifest(manifest_path)
    ckpt = tmp_path / "smoke20.jsonl"
    record = {"case_id": "test-case-1", "status": "valid", "provenance": prov}
    ckpt.write_text(json.dumps(record) + "\n", encoding="utf-8")

    done = verify_or_read_checkpoint(ckpt, manifest_path)
    assert "test-case-1" in done


def test_checkpoint_rejects_changed_dependency_versions(tmp_path):
    import pytest
    manifest_path = ROOT / "data" / "tless" / "manifests" / "smoke20.json"
    prov = build_provenance_manifest(manifest_path)
    prov["package_versions"]["numpy"] = "different-version"
    checkpoint = tmp_path / "changed.jsonl"
    checkpoint.write_text(json.dumps({"case_id": "fixture", "provenance": prov}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="environment mismatch"):
        verify_or_read_checkpoint(checkpoint, manifest_path)
