"""Small deterministic triangle-mesh and rigid-pose utilities.

Coordinates are right-handed, lengths are metres, and transforms are 4x4
homogeneous matrices. A transform named T_a_from_b maps points in frame b to a.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class TriangleMesh:
    vertices: FloatArray
    faces: IntArray


def _append_mesh(parts: list[TriangleMesh]) -> TriangleMesh:
    vertices: list[FloatArray] = []
    faces: list[IntArray] = []
    offset = 0
    for part in parts:
        vertices.append(part.vertices)
        faces.append(part.faces + offset)
        offset += len(part.vertices)
    return TriangleMesh(np.vstack(vertices), np.vstack(faces))


def _cylinder_mesh(segments: int = 48) -> TriangleMesh:
    angles = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
    ring = np.column_stack((np.cos(angles), np.sin(angles)))
    vertices = np.vstack(
        (
            np.column_stack((ring, np.full(segments, -1.0))),
            np.column_stack((ring, np.full(segments, 1.0))),
            [[0.0, 0.0, -1.0],
             [0.0, 0.0, 1.0]],
        )
    )
    bottom_center = 2 * segments
    top_center = bottom_center + 1
    faces: list[list[int]] = []
    for index in range(segments):
        next_index = (index + 1) % segments
        faces.extend(
            (
                [index, next_index, segments + next_index],
                [index, segments + next_index, segments + index],
                [bottom_center, next_index, index],
                [top_center, segments + index, segments + next_index],
            )
        )
    return TriangleMesh(vertices, np.asarray(faces, dtype=np.int64))


def _ellipsoid_mesh(
    center: tuple[float, float, float],
    radii: tuple[float, float, float],
    rings: int = 8,
    segments: int = 12,
) -> TriangleMesh:
    vertices = [[0.0, 0.0, 1.0]]
    for ring_index in range(1, rings):
        phi = np.pi * ring_index / rings
        for segment_index in range(segments):
            theta = 2.0 * np.pi * segment_index / segments
            vertices.append(
                [
                    np.sin(phi) * np.cos(theta),
                    np.sin(phi) * np.sin(theta),
                    np.cos(phi),
                ]
            )
    bottom_index = len(vertices)
    vertices.append([0.0, 0.0, -1.0])
    faces: list[list[int]] = []
    for segment_index in range(segments):
        faces.append([0, 1 + segment_index, 1 + (segment_index + 1) % segments])
    for ring_index in range(rings - 2):
        first = 1 + ring_index * segments
        second = first + segments
        for segment_index in range(segments):
            next_index = (segment_index + 1) % segments
            faces.extend(
                (
                    [first + segment_index, second + segment_index, second + next_index],
                    [first + segment_index, second + next_index, first + next_index],
                )
            )
    last_ring = 1 + (rings - 2) * segments
    for segment_index in range(segments):
        faces.append(
            [last_ring + segment_index, bottom_index, last_ring + (segment_index + 1) % segments]
        )
    scaled = np.asarray(vertices, dtype=np.float64) * np.asarray(radii) + np.asarray(center)
    return TriangleMesh(scaled, np.asarray(faces, dtype=np.int64))


def make_object_mesh(kind: str = "near_symmetric") -> TriangleMesh:
    """Create a 2 m round body with a small side nub or asymmetric control nubs."""
    parts = [_cylinder_mesh()]
    if kind == "near_symmetric":
        parts.append(_ellipsoid_mesh((0.0, 0.91, 0.34), (0.19, 0.14, 0.13)))
    elif kind == "asymmetric_control":
        parts.extend(
            (
                _ellipsoid_mesh((0.28, 0.88, 0.36), (0.20, 0.13, 0.12)),
                _ellipsoid_mesh((-0.38, 0.88, -0.24), (0.12, 0.13, 0.18)),
                _ellipsoid_mesh((0.48, 0.68, -0.62), (0.10, 0.16, 0.09)),
            )
        )
    else:
        raise ValueError(f"Unknown object kind: {kind}")
    return _append_mesh(parts)


def sample_surface(
    mesh: TriangleMesh, count: int, seed: int
) -> tuple[FloatArray, FloatArray]:
    """Sample mesh faces proportional to area and return points and unit normals."""
    rng = np.random.default_rng(seed)
    triangles = mesh.vertices[mesh.faces]
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    double_areas = np.linalg.norm(cross, axis=1)
    valid = double_areas > 1e-12
    triangles = triangles[valid]
    cross = cross[valid]
    double_areas = double_areas[valid]
    indices = rng.choice(len(triangles), size=count, p=double_areas / double_areas.sum())
    chosen = triangles[indices]
    random_values = rng.random((count, 2))
    root = np.sqrt(random_values[:, 0])
    weights = np.column_stack((1.0 - root, root * (1.0 - random_values[:, 1]), root * random_values[:, 1]))
    points = np.einsum("ij,ijk->ik", weights, chosen)
    normals = cross[indices] / double_areas[indices, None]
    return points, normals


def rotation_z(degrees: float) -> FloatArray:
    angle = np.deg2rad(degrees)
    cosine, sine = np.cos(angle), np.sin(angle)
    return np.array(
        [[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )


def make_transform(rotation: FloatArray, translation: FloatArray) -> FloatArray:
    transform = np.eye(4, dtype=np.float64)
    transform[:3, :3] = rotation
    transform[:3, 3] = translation
    return transform


def invert_transform(transform: FloatArray) -> FloatArray:
    inverse = np.eye(4, dtype=np.float64)
    inverse[:3, :3] = transform[:3, :3].T
    inverse[:3, 3] = -inverse[:3, :3] @ transform[:3, 3]
    return inverse


def transform_points(points: FloatArray, transform: FloatArray) -> FloatArray:
    return points @ transform[:3, :3].T + transform[:3, 3]


def pose_error(
    estimated: FloatArray, truth: FloatArray, symmetry_order: int = 1
) -> dict[str, float]:
    """Compare scan-to-object poses, minimizing over declared exact z symmetries."""
    if symmetry_order < 1:
        raise ValueError("symmetry_order must be at least 1")
    best_translation = float("inf")
    best_rotation = float("inf")
    for symmetry_index in range(symmetry_order):
        symmetry = make_transform(rotation_z(360.0 * symmetry_index / symmetry_order), np.zeros(3))
        equivalent = symmetry @ truth
        relative_rotation = estimated[:3, :3] @ equivalent[:3, :3].T
        cosine = np.clip((np.trace(relative_rotation) - 1.0) / 2.0, -1.0, 1.0)
        angle = float(np.rad2deg(np.arccos(cosine)))
        translation = float(np.linalg.norm(estimated[:3, 3] - equivalent[:3, 3]))
        if translation + angle / 180.0 < best_translation + best_rotation / 180.0:
            best_translation, best_rotation = translation, angle
    return {"translation_error_m": best_translation, "rotation_error_deg": best_rotation}