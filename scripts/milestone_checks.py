"""Read-only artifact audit and bounded imports/API smoke; no registration or secret reads."""
import hashlib
import importlib
import json
import sys
from collections import Counter
from importlib import metadata
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))

rows = [json.loads(line) for line in (ROOT / "data/tless/results/original/heldout200.jsonl").read_text().splitlines()]
heldout = read("data/tless/manifests/heldout200.json")["cases"]
development = read("data/tless/manifests/development.json")["cases"]
assert len(rows) == len({row["case_id"] for row in rows}) == 200
assert {row["case_id"] for row in rows} == {case["case_id"] for case in heldout}
assert not {case["case_id"] for case in heldout} & {case["case_id"] for case in development}
for row in rows:
    metrics, pose = row["alignment_quality_metrics"], row["pose_metrics"]
    assert row["accepted"] == (metrics["fitness"] >= .7 and metrics["inlier_rmse_m"] <= .01)
    assert row["correct"] == (pose["mssd_over_diameter"] <= .1)
    assert abs(metrics["fitness"] - metrics["inlier_count"] / metrics["scan_point_count"]) < 1e-12
print("Historical statuses:", dict(Counter(row["status"] for row in rows)))
print("Historical categories:", dict(Counter(row["category"] for row in rows)))
config_hash = hashlib.sha256((ROOT / "configs/tless_frozen.json").read_bytes()).hexdigest()
assert config_hash == read("data/tless/results/original/heldout200.summary.json")["frozen_config_sha256"]
print("Frozen config SHA256:", config_hash)
print("Manifest IDs, scene separation, recorded thresholds and fitness denominators: consistent")
info = read("data/tless/bop/models_cad/models_info.json")
affected = [int(key) for key, value in info.items() if any(any(abs(t) > 1e-10 for t in symmetry[3:12:4]) for symmetry in value.get("symmetries_discrete", []))]
print("Translated symmetry objects:", affected, "potentially affected historical records:", sum(row["object_id"] in affected for row in rows))
exists = Path.exists
with patch.object(Path, "exists", lambda path: False if path.name == ".env" else exists(path)):
    modules = [path.stem for path in (ROOT / "autoframe3d").glob("*.py") if path.stem != "__init__"]
    for module in modules:
        importlib.import_module("autoframe3d." + module)
    from autoframe3d.api import app
    from fastapi.testclient import TestClient
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
print("Imports:", len(modules), "modules; API health:", response.status_code, "(.env access disabled)")
for name in ("autoframe3d", "setuptools", "numpy", "scipy", "Pillow", "pytest"):
    try:
        print(name, metadata.version(name))
    except metadata.PackageNotFoundError:
        print(name, "distribution unavailable")
