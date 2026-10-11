"""Portable display publication and offline preparation checks."""
import json

import pytest

from autoframe3d import recorded_demo
from scripts.prepare_demo_assets import prepare


def test_bundle_independent_of_original_dataset(monkeypatch):
    from autoframe3d import tless_adapter
    monkeypatch.setattr(tless_adapter, "BOP_ROOT", recorded_demo.ROOT / "absent-fixture")
    manifest = json.loads((recorded_demo.ROOT / "demo_assets/manifest.json").read_text())
    for case in recorded_demo.catalogue()["cases"]:
        assert case["geometry_available"]
        for variant in case["variants"]:
            payload = recorded_demo.geometry(case["id"], variant["id"])
            assert payload["config"]["visualization_only"]
            assert len(payload["scan"]) == manifest["cases"][case["id"]]["scan_points"]


def test_preparation_missing_input_is_actionable(tmp_path):
    with pytest.raises(FileNotFoundError, match="Supply --dataset"):
        prepare(tmp_path / "missing", tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_preparation_reproducible_and_matches_publication(tmp_path):
    dataset = recorded_demo.ROOT / "data/tless/bop"
    if not dataset.exists():
        pytest.skip("Optional rebuild requires local source dataset")
    manifest = prepare(dataset, tmp_path)
    assert manifest == json.loads((recorded_demo.ROOT / "demo_assets/manifest.json").read_text())
    for entry in manifest["cases"].values():
        assert (tmp_path / entry["file"]).read_bytes() == (recorded_demo.ROOT / "demo_assets" / entry["file"]).read_bytes()


def test_modified_bundle_rejected(tmp_path, monkeypatch):
    directory = tmp_path / "demo_assets"
    directory.mkdir()
    manifest = json.loads((recorded_demo.ROOT / "demo_assets/manifest.json").read_text())
    (directory / "manifest.json").write_text(json.dumps(manifest))
    (directory / "accepted-wrong.json.gz").write_bytes(b"damaged fixture")
    monkeypatch.setattr(recorded_demo, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="differs from publication"):
        recorded_demo.geometry("accepted-wrong", "baseline")
