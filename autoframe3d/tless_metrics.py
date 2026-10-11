"""BOP symmetry-aware pose metrics and predeclared evaluation categories."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.spatial.transform import Rotation

from autoframe3d.geometry import FloatArray


def bop_symmetry_transforms(model_info: dict[str, Any], max_symmetry_step: float = 0.01) -> list[FloatArray]:
    """Build BOP symmetries with millimetre translations converted to metres.

    Continuous angular step follows the BOP diameter-fraction rule.
    """
    discrete = [np.eye(4, dtype=np.float64)]
    for flattened in model_info.get("symmetries_discrete", []):
        transform = np.asarray(flattened, dtype=np.float64).reshape((4, 4)).copy()
        transform[:3, 3] *= 0.001
        discrete.append(transform)
    continuous: list[FloatArray] = []
    for symmetry in model_info.get("symmetries_continuous", []):
        axis = np.asarray(symmetry["axis"], dtype=np.float64)
        axis /= np.linalg.norm(axis)
        offset = np.asarray(symmetry["offset"], dtype=np.float64) * 0.001
        count = int(np.ceil(np.pi / max_symmetry_step))
        for index in range(count):
            rotation = Rotation.from_rotvec(axis * (index * 2.0 * np.pi / count)).as_matrix()
            transform = np.eye(4, dtype=np.float64)
            transform[:3, :3] = rotation
            transform[:3, 3] = offset - rotation @ offset
            continuous.append(transform)
    if not continuous:
        return discrete
    return [cont @ disc for disc in discrete for cont in continuous]


def mssd_normalized(
    estimated_camera_from_object: FloatArray,
    ground_truth_camera_from_object: FloatArray,
    evaluation_points_object_m: FloatArray,
    symmetries_object: list[FloatArray],
    diameter_m: float,
) -> dict[str, float]:
    """Compute BOP MSSD (maximum model-surface displacement), normalized by diameter."""
    if diameter_m <= 0:
        raise ValueError("Object diameter must be positive")
    estimate = evaluation_points_object_m @ estimated_camera_from_object[:3, :3].T + estimated_camera_from_object[:3, 3]
    best = math.inf
    for symmetry in symmetries_object:
        equivalent_rotation = ground_truth_camera_from_object[:3, :3] @ symmetry[:3, :3]
        equivalent_translation = (
            ground_truth_camera_from_object[:3, :3] @ symmetry[:3, 3]
            + ground_truth_camera_from_object[:3, 3]
        )
        truth = evaluation_points_object_m @ equivalent_rotation.T + equivalent_translation
        best = min(best, float(np.linalg.norm(estimate - truth, axis=1).max()))
    return {"mssd_m": best, "mssd_over_diameter": best / diameter_m}


def classify_result(
    fitness: float,
    rmse_m: float,
    mssd_over_diameter: float,
    *,
    minimum_fitness: float = 0.70,
    maximum_rmse_m: float = 0.010,
    maximum_mssd_over_diameter: float = 0.10,
) -> tuple[bool, bool, str]:
    """Classification using fixed geometric and normalized-pose thresholds."""
    accepted = fitness >= minimum_fitness and rmse_m <= maximum_rmse_m
    correct = mssd_over_diameter <= maximum_mssd_over_diameter
    category = {
        (True, True): "accepted_and_correct",
        (True, False): "accepted_but_wrong",
        (False, True): "rejected_and_correct",
        (False, False): "rejected_and_wrong",
    }[(accepted, correct)]
    return accepted, correct, category