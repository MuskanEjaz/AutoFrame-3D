"""Local FastAPI application; geometry runs on worker threads, not requests."""

from __future__ import annotations

import json
import os
import threading
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Literal

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from autoframe3d.agent import DEFAULT_MODEL
from autoframe3d.campaign import run_campaign, summarize
from autoframe3d.cases import export_case, replay_bundle
from autoframe3d.experiment import ExperimentConfig, evaluate
from autoframe3d.simplify import simplify_failure
from autoframe3d.tless_cases import export_case_bundle, geometry_payload, list_result_records, load_result_record, replay_record

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


_load_dotenv()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ScenarioRequest(StrictModel):
    object_kind: Literal["near_symmetric", "asymmetric_control"] = "near_symmetric"
    visibility: Literal["all", "front", "top"] = "top"
    seed: int = Field(default=41, ge=0, le=1_000_000)
    yaw_deg: float = Field(default=23.0, ge=-180, le=180)
    noise_std_m: float = Field(default=0.001, ge=0, le=0.005)
    background_points: int = Field(default=0, ge=0, le=128)

    def to_config(self) -> ExperimentConfig:
        return ExperimentConfig(**self.model_dump())


class CampaignRequest(StrictModel):
    budget: int = Field(default=12, ge=2, le=12)
    mode: Literal["auto", "deterministic", "live_ai"] = "auto"


class JobStore:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.jobs: dict[str, dict[str, object]] = {}
        self.stop_events: dict[str, threading.Event] = {}
        self.cases: dict[str, dict[str, object]] = {}

    def new_job(self, job_type: str, total: int) -> str:
        job_id = uuid.uuid4().hex[:12]
        with self.lock:
            self.jobs[job_id] = {
                "job_id": job_id,
                "type": job_type,
                "status": "queued",
                "progress": {"completed": 0, "total": total},
                "events": [],
                "result": None,
                "error": None,
            }
            self.stop_events[job_id] = threading.Event()
        return job_id

    def append_event(self, job_id: str, event: dict[str, object]) -> None:
        with self.lock:
            job = self.jobs[job_id]
            job["events"].append(event)
            if event.get("kind") in {"experiment_measured", "simplification_trial"}:
                progress = job["progress"]
                progress["completed"] += 1
                case_id = f"{job_id}-{event.get('arm', 'baseline')}-{event.get('index', progress['completed'])}"
                self.cases[case_id] = {
                    "case_id": case_id,
                    "config": event["config"],
                    "result": {key: event[key] for key in (
                        "config", "thresholds", "ground_truth_T_object_from_scan",
                        "estimated_T_object_from_scan", "alignment_quality_metrics",
                        "pose_errors", "classification", "initial_yaw_deg",
                    )},
                    "job_id": job_id,
                    "arm": event.get("arm", "baseline"),
                }
                event["case_id"] = case_id

    def case(self, case_id: str) -> dict[str, object]:
        with self.lock:
            value = self.cases.get(case_id)
            if value is None:
                raise HTTPException(status_code=404, detail="Case not found")
            return value


store = JobStore()
app = FastAPI(title="AutoFrame 3D", version="0.1.0")


def _json_safe(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _start_worker(job_id: str, target) -> None:
    def run() -> None:
        with store.lock:
            store.jobs[job_id]["status"] = "running"
        try:
            target()
            with store.lock:
                job = store.jobs[job_id]
                if job["status"] == "running":
                    job["status"] = "stopped" if store.stop_events[job_id].is_set() else "completed"
        except Exception as error:
            with store.lock:
                store.jobs[job_id]["status"] = "failed"
                store.jobs[job_id]["error"] = f"{type(error).__name__}: {error}"

    threading.Thread(target=run, name=f"autoframe3d-{job_id}", daemon=True).start()


def _start_baseline(config: ExperimentConfig) -> str:
    job_id = store.new_job("baseline", 1)

    def run() -> None:
        result = evaluate(config)
        event = {"kind": "experiment_measured", **summarize(result)}
        store.append_event(job_id, event)
        with store.lock:
            store.jobs[job_id]["result"] = {key: value for key, value in event.items() if key != "kind"}

    _start_worker(job_id, run)
    return job_id


@lru_cache(maxsize=8)
def _sample_payload(
    object_kind: str, visibility: str, seed: int, yaw_deg: float, noise_std_m: float
) -> dict[str, object]:
    result = evaluate(ExperimentConfig(
        object_kind=object_kind,
        visibility=visibility,
        seed=seed,
        yaw_deg=yaw_deg,
        noise_std_m=noise_std_m,
    ))
    mesh = result["mesh"]
    return {
        "config": result["config"],
        "classification": result["classification"],
        "mesh": {"vertices": mesh.vertices.tolist(), "faces": mesh.faces.tolist()},
        "scan": result["scan"].tolist(),
        "ground_truth_T_object_from_scan": result["ground_truth_T_object_from_scan"].tolist(),
        "estimated_T_object_from_scan": result["estimated_T_object_from_scan"].tolist(),
        "alignment_quality_metrics": result["alignment_quality_metrics"],
        "pose_errors": result["pose_errors"],
    }


@app.get("/api/health")
def health() -> dict[str, object]:
    configured = bool(os.environ.get("NEBIUS_API_KEY"))
    return {
        "status": "ok",
        "model_mode": "live_ai_available" if configured else "deterministic_only",
        "model": os.environ.get("NEBIUS_MODEL", DEFAULT_MODEL),
        "api_key_configured": configured,
        "campaign_budget_max": 12,
        "model_calls_max": 4,
        "tless_subset_available": (ROOT / "data" / "tless" / "bop" / "test_primesense").exists(),
    }


@app.get("/api/sample")
def sample(
    object_kind: Literal["near_symmetric", "asymmetric_control"] = "near_symmetric",
    visibility: Literal["all", "front", "top"] = "all",
    seed: int = 41,
    yaw_deg: float = 0.0,
    noise_std_m: float = 0.001,
) -> dict[str, object]:
    if not 0 <= seed <= 1_000_000 or not -180 <= yaw_deg <= 180 or not 0 <= noise_std_m <= 0.005:
        raise HTTPException(status_code=422, detail="Scenario parameter outside supported range")
    return _sample_payload(object_kind, visibility, seed, yaw_deg, noise_std_m)


@app.post("/api/baseline")
def baseline(request: ScenarioRequest) -> dict[str, str]:
    return {"job_id": _start_baseline(request.to_config())}


@app.post("/api/campaigns")
def start_campaign(request: CampaignRequest) -> dict[str, str]:
    if request.budget % 2:
        raise HTTPException(status_code=422, detail="Budget must split evenly between agent and random search")
    job_id = store.new_job("campaign", request.budget)

    def run() -> None:
        result = run_campaign(
            budget=request.budget,
            mode=request.mode,
            stop_event=store.stop_events[job_id],
            on_event=lambda event: store.append_event(job_id, event),
        )
        with store.lock:
            store.jobs[job_id]["result"] = result

    _start_worker(job_id, run)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, object]:
    with store.lock:
        job = store.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return _json_safe(job)


@app.post("/api/jobs/{job_id}/stop")
def stop_job(job_id: str) -> dict[str, str]:
    with store.lock:
        if job_id not in store.jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        store.stop_events[job_id].set()
    return {"status": "stop_requested"}


@app.get("/api/cases/{case_id}")
def get_case(case_id: str) -> dict[str, object]:
    case = store.case(case_id)
    return _json_safe({"case_id": case_id, **case["result"]})


@app.get("/api/tless/cases")
def list_tless_cases(
    group: Literal["original", "perturbed"] = "original",
    manifest: Literal["smoke20", "smoke20_frozen", "development_tuning20", "heldout200", "all_eligible"] = "smoke20_frozen",
) -> dict[str, object]:
    records = list_result_records(group, manifest)
    return {
        "group": group,
        "manifest": manifest,
        "protocol": "Custom internal evaluation on the public BOP test subset; not an official BOP score",
        "mask_protocol": "Registration evaluation with ground-truth instance masks; not end-to-end detection",
        "cases": [
            {
                key: row.get(key)
                for key in (
                    "case_id", "scene_id", "image_id", "gt_index", "object_id", "group",
                    "status", "category", "alignment_quality_metrics", "pose_metrics", "runtime_seconds",
                )
            }
            for row in records
        ],
    }


@app.get("/api/tless/cases/{case_id}")
def get_tless_case(
    case_id: str,
    group: Literal["original", "perturbed"] = "original",
    manifest: Literal["smoke20", "smoke20_frozen", "development_tuning20", "heldout200", "all_eligible"] = "smoke20_frozen",
) -> dict[str, object]:
    try:
        return load_result_record(case_id, group, manifest)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except KeyError as error:
        raise HTTPException(status_code=404, detail="T-LESS case not found in requested manifest") from error


@app.get("/api/tless/cases/{case_id}/geometry")
def tless_case_geometry(
    case_id: str,
    group: Literal["original", "perturbed"] = "original",
    manifest: Literal["smoke20", "smoke20_frozen", "development_tuning20", "heldout200", "all_eligible"] = "smoke20_frozen",
) -> dict[str, object]:
    try:
        record = load_result_record(case_id, group, manifest)
    except (FileNotFoundError, KeyError) as error:
        raise HTTPException(status_code=404, detail="T-LESS case not found") from error
    return geometry_payload(record)


@app.post("/api/tless/cases/{case_id}/replay")
def replay_tless_case(
    case_id: str,
    group: Literal["original", "perturbed"] = "original",
    manifest: Literal["smoke20", "smoke20_frozen", "development_tuning20", "heldout200", "all_eligible"] = "smoke20_frozen",
) -> dict[str, str]:
    try:
        record = load_result_record(case_id, group, manifest)
    except (FileNotFoundError, KeyError) as error:
        raise HTTPException(status_code=404, detail="T-LESS case not found") from error
    job_id = store.new_job("tless_replay", 1)

    def run() -> None:
        result = replay_record(record)
        with store.lock:
            store.jobs[job_id]["result"] = result
            store.jobs[job_id]["progress"]["completed"] = 1

    _start_worker(job_id, run)
    return {"job_id": job_id}


@app.get("/api/tless/cases/{case_id}/export")
def export_tless_case(
    case_id: str,
    group: Literal["original", "perturbed"] = "original",
    manifest: Literal["smoke20", "smoke20_frozen", "development_tuning20", "heldout200", "all_eligible"] = "smoke20_frozen",
) -> FileResponse:
    try:
        record = load_result_record(case_id, group, manifest)
    except (FileNotFoundError, KeyError) as error:
        raise HTTPException(status_code=404, detail="T-LESS case not found") from error
    path = export_case_bundle(record, ARTIFACTS / "exports" / "tless" / f"{group}-{case_id}.zip")
    return FileResponse(path, filename=f"autoframe3d-{group}-{case_id}.zip", media_type="application/zip")


@app.get("/api/cases/{case_id}/geometry")
def case_geometry(case_id: str) -> dict[str, object]:
    case = store.case(case_id)
    config = ExperimentConfig(**case["config"])
    from autoframe3d.experiment import generate_scan
    from autoframe3d.geometry import make_object_mesh

    mesh = make_object_mesh(config.object_kind)
    scan, truth = generate_scan(config, mesh)
    result = case["result"]
    return _json_safe({
        "config": case["config"],
        "mesh": {"vertices": mesh.vertices.tolist(), "faces": mesh.faces.tolist()},
        "scan": scan.tolist(),
        "ground_truth_T_object_from_scan": result.get("ground_truth_T_object_from_scan", truth.tolist()),
        "estimated_T_object_from_scan": result["estimated_T_object_from_scan"],
    })


@app.post("/api/cases/{case_id}/simplify")
def simplify_case(case_id: str) -> dict[str, str]:
    original = store.case(case_id)
    if original["result"]["classification"] != "accepted_but_wrong":
        raise HTTPException(status_code=422, detail="Only an accepted-but-wrong case can be simplified")
    job_id = store.new_job("simplification", 8)

    def record_trial(event: dict[str, object]) -> None:
        store.append_event(job_id, event)
        with store.lock:
            new_id = f"{job_id}-simplify-{event['attempt']}"
            store.cases[new_id] = {
                "case_id": new_id,
                "config": event["config"],
                "result": {key: event[key] for key in (
                    "config", "thresholds", "ground_truth_T_object_from_scan",
                    "estimated_T_object_from_scan", "alignment_quality_metrics",
                    "pose_errors", "classification", "initial_yaw_deg",
                )},
                "job_id": job_id,
                "arm": "simplification",
            }
            event["case_id"] = new_id

    def run() -> None:
        result = simplify_failure(original["result"], on_trial=record_trial)
        with store.lock:
            store.jobs[job_id]["result"] = result

    _start_worker(job_id, run)
    return {"job_id": job_id}


@app.post("/api/cases/{case_id}/replay")
def replay_case(case_id: str) -> dict[str, str]:
    case = store.case(case_id)
    job_id = store.new_job("replay", 1)

    def run() -> None:
        bundle = export_case(case_id, case["config"], case["result"], ARTIFACTS / "exports" / f"{case_id}.zip")
        result = replay_bundle(bundle)
        with store.lock:
            store.jobs[job_id]["result"] = result

    _start_worker(job_id, run)
    return {"job_id": job_id}


@app.get("/api/cases/{case_id}/export")
def export(case_id: str) -> FileResponse:
    case = store.case(case_id)
    path = export_case(case_id, case["config"], case["result"], ARTIFACTS / "exports" / f"{case_id}.zip")
    return FileResponse(path, filename=f"autoframe3d-{case_id}.zip", media_type="application/zip")