"""Read-only curated benchmark evidence. Geometry loading never registers a pose."""
import hashlib
import gzip
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = ROOT / "audit_evidence/recorded_benchmark_demo/demo.json"


def evidence():
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def case_variant(case_id, variant="baseline"):
    case = next((c for c in evidence()["cases"] if c["id"] == case_id), None)
    if case is None:
        raise KeyError("Recorded demo case not found")
    selected = next((v for v in case["variants"] if v["id"] == variant), None)
    if selected is None:
        raise KeyError("Recorded method not found")
    return case, selected


def check_inputs(case, verify_hashes=False):
    for relative, expected in case["inputs"].items():
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"Local geometry input missing: {relative}. Recorded metrics remain available; no data download is performed.")
        if verify_hashes and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Local input differs from recorded evidence: {relative}. Geometry cannot be verified.")


def catalogue():
    result = evidence()
    for case in result["cases"]:
        try:
            display_asset(case)
            case["geometry_status"] = "Bundled T-LESS display geometry; visualization only, not scoring/replay inputs."
            case["geometry_available"] = True
        except (FileNotFoundError, ValueError) as error:
            case["geometry_status"] = str(error)
            case["geometry_available"] = False
    return result


def geometry(case_id, variant):
    case, selected = case_variant(case_id, variant)
    payload = display_asset(case)
    record = selected["record"]
    return {**payload, "config": {"object_kind": "T-LESS object", "object_id": case["object_id"],
                                  "units": "metres", "visualization_only": True},
            "estimated_T_object_from_scan": np.linalg.inv(record["camera_from_object_estimate"]).tolist(),
            "ground_truth_T_object_from_scan": np.linalg.inv(record["camera_from_object_ground_truth"]).tolist()}


def display_asset(case):
    directory = ROOT / "demo_assets"
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        entry = manifest["cases"][case["id"]]
        raw = (directory / (case["id"] + ".json.gz")).read_bytes()
    except FileNotFoundError as error:
        raise FileNotFoundError("Display geometry missing; restore demo_assets or run python scripts/prepare_demo_assets.py --dataset <T-LESS BOP root>. Recorded metrics remain available.") from error
    if len(raw) != entry["size_bytes"] or hashlib.sha256(raw).hexdigest() != entry["publication_sha256"]:
        raise ValueError("Display geometry differs from publication manifest; regenerate demo_assets.")
    return json.loads(gzip.decompress(raw))
