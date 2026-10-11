"""Read-only curated benchmark evidence. Geometry loading never registers a pose."""
import hashlib
import json
from pathlib import Path

from autoframe3d.tless_cases import geometry_payload

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
            check_inputs(case)
            case["geometry_status"] = "Local inputs present; hashes checked when geometry is opened."
            case["geometry_available"] = True
        except FileNotFoundError as error:
            case["geometry_status"] = str(error)
            case["geometry_available"] = False
    return result


def geometry(case_id, variant):
    case, selected = case_variant(case_id, variant)
    check_inputs(case, verify_hashes=True)
    return geometry_payload(selected["record"])
