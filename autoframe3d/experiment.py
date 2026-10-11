"""Seeded synthetic scans, a deterministic ICP baseline, and bounded search."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import cKDTree

from autoframe3d.geometry import (
    FloatArray,
    TriangleMesh,
    invert_transform,
    make_object_mesh,
    make_transform,
    pose_error,
    rotation_z,
    sample_surface,
    transform_points,
)


@dataclass(frozen=True)
class ExperimentConfig:
    object_kind: str = "near_symmetric"
    seed: int = 41
    visibility: str = "top"
    yaw_deg: float = 23.0
    translation_m: tuple[float, float, float] = (0.16, -0.08, 0.22)
    noise_std_m: float = 0.001
    background_points: int = 0
    scan_points: int = 768
    target_points: int = 3072
    yaw_step_deg: float = 30.0
    max_correspondence_m: float = 0.18
    max_iterations: int = 20


@dataclass(frozen=True)
class AcceptanceThresholds:
    minimum_fitness: float = 0.70
    maximum_inlier_rmse_m: float = 0.075
    maximum_translation_error_m: float = 0.08
    maximum_rotation_error_deg: float = 12.0


DEFAULT_THRESHOLDS = AcceptanceThresholds()


def _visible(normals: FloatArray, visibility: str) -> NDArray[np.bool_]:
    if visibility == "all":
        return np.ones(len(normals), dtype=bool)
    if visibility == "top":
        return normals[:, 2] > 0.85
    if visibility == "front":
        return normals[:, 1] > 0.20
    raise ValueError("visibility must be one of: all, front, top")


def generate_scan(
    config: ExperimentConfig, mesh: TriangleMesh | None = None
) -> tuple[FloatArray, FloatArray]:
    """Return world-frame scan points and T_object_from_scan ground truth."""
    mesh = mesh or make_object_mesh(config.object_kind)
    rng = np.random.default_rng(config.seed)
    candidates, normals = sample_surface(mesh, config.scan_points * 14, config.seed + 1)
    visible = _visible(normals, config.visibility)
    points = candidates[visible]
    if len(points) < config.scan_points:
        raise ValueError("Visibility leaves too few sampled points; increase scan_points")
    selected = rng.choice(len(points), size=config.scan_points, replace=False)
    points = points[selected]
    if config.noise_std_m:
        points = points + rng.normal(0.0, config.noise_std_m, points.shape)
    truth_world_from_object = make_transform(
        rotation_z(config.yaw_deg), np.asarray(config.translation_m, dtype=np.float64)
    )
    scan = transform_points(points, truth_world_from_object)
    if config.background_points:
        if config.background_points < 0:
            raise ValueError("background_points cannot be negative")
        background = rng.uniform([-1.5, -1.5, -1.2], [1.5, 1.5, 1.2], (config.background_points, 3))
        scan = np.vstack((scan, background))
    return scan, invert_transform(truth_world_from_object)


def _best_fit_transform(source: FloatArray, target: FloatArray) -> FloatArray:
    source_center = source.mean(axis=0)
    target_center = target.mean(axis=0)
    covariance = (source - source_center).T @ (target - target_center)
    left, _, right = np.linalg.svd(covariance)
    rotation = right.T @ left.T
    if np.linalg.det(rotation) < 0:
        right[-1] *= -1.0
        rotation = right.T @ left.T
    return make_transform(rotation, target_center - rotation @ source_center)


def _icp(
    source: FloatArray,
    target: FloatArray,
    initial: FloatArray,
    max_correspondence_m: float,
    max_iterations: int,
) -> tuple[FloatArray, float, float, int]:
    target_tree = cKDTree(target)
    transform = initial.copy()
    for _ in range(max_iterations):
        moved = transform_points(source, transform)
        distances, indices = target_tree.query(moved, k=1, workers=1)
        inliers = distances <= max_correspondence_m
        if inliers.sum() < 6:
            break
        update = _best_fit_transform(moved[inliers], target[indices[inliers]])
        transform = update @ transform
        if np.linalg.norm(update[:3, 3]) < 1e-5 and np.rad2deg(
            np.arccos(np.clip((np.trace(update[:3, :3]) - 1) / 2, -1, 1))
        ) < 0.01:
            break
    moved = transform_points(source, transform)
    distances, _ = target_tree.query(moved, k=1, workers=1)
    inliers = distances <= max_correspondence_m
    fitness = float(inliers.sum() / len(source))
    rmse = float(np.sqrt(np.mean(np.square(distances[inliers])))) if inliers.any() else float("inf")
    return transform, fitness, rmse, int(inliers.sum())


def register(scan: FloatArray, config: ExperimentConfig) -> dict[str, object]:
    """Register scan to CAD using centroid initialization, yaw sweep, then point ICP.

    Candidate yaw angles are a fixed grid in the CAD frame and do not use ground
    truth. This is a global ambiguity search, not an intentionally wrong seed.
    The reported fitness is the fraction of input scan points with a CAD neighbor
    within max_correspondence_m; inlier RMSE is computed over those points.
    """
    mesh = make_object_mesh(config.object_kind)
    target, _ = sample_surface(mesh, config.target_points, seed=202605)
    target_tree = cKDTree(target)
    target_center = mesh.vertices.mean(axis=0)
    target_min, target_max = mesh.vertices.min(axis=0), mesh.vertices.max(axis=0)
    best: dict[str, object] | None = None
    yaw_angles = np.arange(0.0, 360.0, config.yaw_step_deg)
    if len(yaw_angles) < 1 or config.yaw_step_deg <= 0:
        raise ValueError("yaw_step_deg must be positive")
    for yaw in yaw_angles:
        rotation = rotation_z(float(yaw))
        if config.visibility == "top":
            translation = target_center.copy()
            translation[:2] -= (rotation @ scan.mean(axis=0))[:2]
            translation[2] = target_max[2] - float((scan @ rotation.T)[:, 2].max())
        else:
            translation = target_center - rotation @ scan.mean(axis=0)
        initial = make_transform(rotation, translation)
        estimate, fitness, rmse, inlier_count = _icp(
            scan,
            target,
            initial,
            config.max_correspondence_m,
            config.max_iterations,
        )
        candidate = {
            "transform": estimate,
            "fitness": fitness,
            "inlier_rmse_m": rmse,
            "inlier_count": inlier_count,
            "initial_yaw_deg": float(yaw),
        }
        if best is None or (fitness, -rmse) > (best["fitness"], -best["inlier_rmse_m"]):
            best = candidate
    assert best is not None
    best["target_points"] = target
    return best


def evaluate(
    config: ExperimentConfig,
    thresholds: AcceptanceThresholds = DEFAULT_THRESHOLDS,
) -> dict[str, object]:
    mesh = make_object_mesh(config.object_kind)
    scan, truth = generate_scan(config, mesh)
    registration = register(scan, config)
    errors = pose_error(registration["transform"], truth, symmetry_order=1)
    accepted = (
        registration["fitness"] >= thresholds.minimum_fitness
        and registration["inlier_rmse_m"] <= thresholds.maximum_inlier_rmse_m
    )
    wrong = (
        errors["translation_error_m"] > thresholds.maximum_translation_error_m
        or errors["rotation_error_deg"] > thresholds.maximum_rotation_error_deg
    )
    classification = "accepted_but_wrong" if accepted and wrong else (
        "accepted_correct" if accepted else "rejected"
    )
    return {
        "config": asdict(config),
        "thresholds": asdict(thresholds),
        "scan": scan,
        "mesh": mesh,
        "ground_truth_T_object_from_scan": truth,
        "estimated_T_object_from_scan": registration["transform"],
        "alignment_quality_metrics": {
            "fitness": registration["fitness"],
            "inlier_rmse_m": registration["inlier_rmse_m"],
            "inlier_count": registration["inlier_count"],
        },
        "pose_errors": errors,
        "classification": classification,
        "initial_yaw_deg": registration["initial_yaw_deg"],
    }


def deterministic_configs(budget: int = 12) -> list[ExperimentConfig]:
    """Return fixed reproducible perturbations without evaluating them."""
    if not 1 <= budget <= 12:
        raise ValueError("budget must be between 1 and 12")
    candidates = [
        ExperimentConfig(seed=41 + index, visibility="top", noise_std_m=0.001 + 0.0005 * (index % 4))
        for index in range(6)
    ] + [
        ExperimentConfig(seed=71 + index, visibility="front", noise_std_m=0.002 + 0.0005 * (index % 3))
        for index in range(6)
    ]
    return candidates[:budget]


def bounded_search(budget: int = 12) -> list[dict[str, object]]:
    """Evaluate a fixed, reproducible perturbation list within the supplied budget."""
    return [evaluate(config) for config in deterministic_configs(budget)]