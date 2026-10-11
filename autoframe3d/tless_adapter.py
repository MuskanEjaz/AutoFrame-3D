"""BOP/T-LESS input adapter. Registration inputs intentionally exclude GT poses."""

from __future__ import annotations

import itertools
import json
import math
import struct
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageDraw, ImageFilter
from scipy.spatial import cKDTree

from autoframe3d.geometry import invert_transform, make_transform, transform_points

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
ROOT = Path(__file__).resolve().parent.parent
BOP_ROOT = ROOT / "data" / "tless" / "bop"
MM_TO_M = 0.001


@dataclass(frozen=True)
class PLYModel:
    vertices_m: FloatArray
    faces: IntArray


@dataclass(frozen=True)
class RegistrationInputs:
    """Only measured inputs. This type has no ground-truth pose field."""

    case_id: str
    scene_id: int
    image_id: int
    gt_index: int
    object_id: int
    scan_points_camera_m: FloatArray
    model_vertices_object_m: FloatArray
    model_faces: IntArray
    evaluation_points_object_m: FloatArray
    camera_matrix: FloatArray
    visible_mask: NDArray[np.bool_]
    depth_image_m: FloatArray
    rgb_path: Path
    visible_mask_path: Path
    depth_scale_mm_per_unit: float
    model_info: dict[str, Any]


@dataclass(frozen=True)
class GroundTruth:
    object_id: int
    camera_from_object: FloatArray


def _ply_header(data: bytes) -> tuple[str, int, list[tuple[str, str]], int, list[tuple[str, str]], int]:
    marker = data.index(b"end_header")
    end = data.index(b"\n", marker) + 1
    lines = data[:end].decode("ascii").splitlines()
    fmt = next(line.split()[1] for line in lines if line.startswith("format "))
    vertex_count = 0
    face_count = 0
    section = ""
    vertex_properties: list[tuple[str, str]] = []
    face_properties: list[tuple[str, str]] = []
    for line in lines:
        parts = line.split()
        if len(parts) == 3 and parts[0] == "element":
            section = parts[1]
            if section == "vertex":
                vertex_count = int(parts[2])
            elif section == "face":
                face_count = int(parts[2])
        elif len(parts) == 3 and parts[0] == "property" and parts[1] != "list":
            if section == "vertex":
                vertex_properties.append((parts[2], parts[1]))
            elif section == "face":
                face_properties.append((parts[2], parts[1]))
        elif len(parts) == 5 and parts[:2] == ["property", "list"] and section == "face":
            face_properties.append((parts[4], f"list:{parts[2]}:{parts[3]}"))
    return fmt, vertex_count, vertex_properties, face_count, face_properties, end


_PLY_TYPES = {
    "char": "b", "int8": "b", "uchar": "B", "uint8": "B",
    "short": "h", "int16": "h", "ushort": "H", "uint16": "H",
    "int": "i", "int32": "i", "uint": "I", "uint32": "I",
    "float": "f", "float32": "f", "double": "d", "float64": "d",
}


def read_ply_model(path: Path) -> PLYModel:
    """Read BOP ASCII or binary-little-endian PLY vertices/faces, convert mm to m."""
    data = path.read_bytes()
    fmt, vertex_count, vertex_properties, face_count, face_properties, offset = _ply_header(data)
    names = [name for name, _ in vertex_properties]
    try:
        xyz_indices = [names.index(name) for name in ("x", "y", "z")]
    except ValueError as error:
        raise ValueError(f"PLY has no x/y/z vertex fields: {path}") from error
    vertices = np.empty((vertex_count, 3), dtype=np.float64)
    faces: list[list[int]] = []
    if fmt == "ascii":
        text = data[offset:].decode("ascii").splitlines()
        for row_index in range(vertex_count):
            values = text[row_index].split()
            vertices[row_index] = [float(values[index]) * MM_TO_M for index in xyz_indices]
        cursor = vertex_count
        if face_count:
            face_list_property = next(
                (value for name, value in face_properties if name == "vertex_indices"),
                None,
            )
            if face_list_property is None:
                raise ValueError(f"PLY faces have no vertex_indices: {path}")
            for line in text[cursor:cursor + face_count]:
                values = [int(value) for value in line.split()]
                faces.append(values[1:1 + values[0]])
    elif fmt == "binary_little_endian":
        vertex_format = "<" + "".join(_PLY_TYPES[type_name] for _, type_name in vertex_properties)
        vertex_struct = struct.Struct(vertex_format)
        for row_index in range(vertex_count):
            values = vertex_struct.unpack_from(data, offset + row_index * vertex_struct.size)
            vertices[row_index] = [float(values[index]) * MM_TO_M for index in xyz_indices]
        offset += vertex_count * vertex_struct.size
        if face_count:
            face_list_type = next(
                (value for name, value in face_properties if name == "vertex_indices" and value.startswith("list:")),
                None,
            )
            if face_list_type is None:
                raise ValueError(f"PLY faces have no vertex_indices: {path}")
            _, count_type, index_type = face_list_type.split(":")
            count_struct = struct.Struct("<" + _PLY_TYPES[count_type])
            index_struct = struct.Struct("<" + _PLY_TYPES[index_type])
            for _ in range(face_count):
                count = count_struct.unpack_from(data, offset)[0]
                offset += count_struct.size
                face = list(struct.unpack_from("<" + _PLY_TYPES[index_type] * count, data, offset))
                faces.append(face)
                offset += index_struct.size * count
    else:
        raise ValueError(f"Unsupported PLY format {fmt}: {path}")
    return PLYModel(vertices, np.asarray(faces, dtype=np.int64).reshape((-1, 3)))


@lru_cache(maxsize=96)
def load_model(object_id: int, model_kind: str = "cad") -> PLYModel:
    folder = "models_cad" if model_kind == "cad" else "models_eval"
    return read_ply_model(BOP_ROOT / folder / f"obj_{object_id:06d}.ply")


@lru_cache(maxsize=32)
def load_model_info() -> dict[str, dict[str, Any]]:
    return json.loads((BOP_ROOT / "models_cad" / "models_info.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=16)
def _load_scene_arrays(scene_id: int, image_id: int) -> tuple[FloatArray, NDArray[Any], dict[str, Any], Path, Path]:
    scene_root = BOP_ROOT / "test_primesense" / f"{scene_id:06d}"
    camera_data = json.loads((scene_root / "scene_camera.json").read_text(encoding="utf-8"))[str(image_id)]
    matrix = np.asarray(camera_data["cam_K"], dtype=np.float64).reshape((3, 3))
    depth_path = scene_root / "depth" / f"{image_id:06d}.png"
    rgb_path = scene_root / "rgb" / f"{image_id:06d}.png"
    depth_raw = np.asarray(Image.open(depth_path), dtype=np.uint16)
    return matrix, depth_raw, camera_data, rgb_path, depth_path


def depth_to_camera_points(
    depth_units: NDArray[Any],
    mask: NDArray[np.bool_],
    camera_matrix: FloatArray,
    depth_scale_mm_per_unit: float,
) -> FloatArray:
    """Project BOP uint16 camera-Z depth through K, returning right-handed metres."""
    if depth_units.shape != mask.shape:
        raise ValueError("Depth and instance mask shapes must match")
    if depth_scale_mm_per_unit <= 0 or camera_matrix.shape != (3, 3):
        raise ValueError("Depth scale must be positive and camera matrix must be 3x3")
    rows, columns = np.nonzero(mask & (depth_units > 0))
    z = np.asarray(depth_units[rows, columns], dtype=np.float64) * depth_scale_mm_per_unit * MM_TO_M
    return np.column_stack(
        (
            (columns - camera_matrix[0, 2]) * z / camera_matrix[0, 0],
            (rows - camera_matrix[1, 2]) * z / camera_matrix[1, 1],
            z,
        )
    )


def load_registration_inputs(case: dict[str, int]) -> RegistrationInputs:
    """Load intrinsics, visible-mask depth points, and CAD model without opening GT poses."""
    scene_id, image_id = int(case["scene_id"]), int(case["image_id"])
    gt_index, object_id = int(case["gt_index"]), int(case["object_id"])
    matrix, raw_depth, camera_data, rgb_path, _ = _load_scene_arrays(scene_id, image_id)
    depth_m = raw_depth.astype(np.float64) * float(camera_data["depth_scale"]) * MM_TO_M
    scene_root = BOP_ROOT / "test_primesense" / f"{scene_id:06d}"
    mask_path = scene_root / "mask_visib" / f"{image_id:06d}_{gt_index:06d}.png"
    visible_mask = np.asarray(Image.open(mask_path)) > 0
    if visible_mask.shape != depth_m.shape:
        raise ValueError(f"Mask/depth shape mismatch for {case['case_id']}")
    points = depth_to_camera_points(
        raw_depth, visible_mask, matrix, float(camera_data["depth_scale"])
    )
    cad = load_model(object_id, "cad")
    evaluation = load_model(object_id, "eval")
    return RegistrationInputs(
        case_id=str(case["case_id"]),
        scene_id=scene_id,
        image_id=image_id,
        gt_index=gt_index,
        object_id=object_id,
        scan_points_camera_m=points,
        model_vertices_object_m=cad.vertices_m,
        model_faces=cad.faces,
        evaluation_points_object_m=evaluation.vertices_m,
        camera_matrix=matrix,
        visible_mask=visible_mask,
        depth_image_m=depth_m,
        rgb_path=rgb_path,
        visible_mask_path=mask_path,
        depth_scale_mm_per_unit=float(camera_data["depth_scale"]),
        model_info=load_model_info()[str(object_id)],
    )


def load_ground_truth(case: dict[str, int]) -> GroundTruth:
    """Evaluator-only annotation access; never pass this object to registration."""
    scene_root = BOP_ROOT / "test_primesense" / f"{int(case['scene_id']):06d}"
    annotations = json.loads((scene_root / "scene_gt.json").read_text(encoding="utf-8"))
    annotation = annotations[str(int(case["image_id"]))][int(case["gt_index"])]
    translation = np.asarray(annotation["cam_t_m2c"], dtype=np.float64) * MM_TO_M
    transform = make_transform(
        np.asarray(annotation["cam_R_m2c"], dtype=np.float64).reshape((3, 3)), translation
    )
    return GroundTruth(int(annotation["obj_id"]), transform)


def write_ground_truth_diagnostic(inputs: RegistrationInputs, truth: GroundTruth, output: Path) -> Path:
    """Write an annotation-only overlay for coordinate/scale inspection, never used for fitting."""
    rgb = Image.open(inputs.rgb_path).convert("RGB").convert("RGBA")
    mask_edges = Image.fromarray(inputs.visible_mask.astype(np.uint8) * 255).filter(ImageFilter.FIND_EDGES)
    edge_pixels = np.asarray(mask_edges) > 0
    overlay = Image.new("RGBA", rgb.size, (0, 0, 0, 0))
    edge_image = np.zeros((rgb.height, rgb.width, 4), dtype=np.uint8)
    edge_image[edge_pixels] = [69, 222, 197, 180]
    overlay = Image.alpha_composite(overlay, Image.fromarray(edge_image, "RGBA"))
    vertices = load_model(inputs.object_id, "cad").vertices_m
    camera_vertices = transform_points(vertices, truth.camera_from_object)
    in_front = camera_vertices[:, 2] > 0
    projected = camera_vertices[in_front] @ inputs.camera_matrix.T
    pixels = np.rint(projected[:, :2] / projected[:, 2, None]).astype(np.int64)
    inside = (
        (pixels[:, 0] >= 0) & (pixels[:, 0] < rgb.width)
        & (pixels[:, 1] >= 0) & (pixels[:, 1] < rgb.height)
    )
    draw = ImageDraw.Draw(overlay)
    for x, y in pixels[inside][::max(1, int(inside.sum() / 6000))]:
        draw.point((int(x), int(y)), fill=(255, 155, 91, 155))
    result = Image.alpha_composite(rgb, overlay).convert("RGB")
    draw = ImageDraw.Draw(result)
    draw.rectangle((5, 5, 296, 25), fill=(12, 20, 23))
    draw.text((10, 9), "GT DIAGNOSTIC OVERLAY ONLY | model orange, visible mask cyan", fill=(240, 244, 240))
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output)
    return output


def pca_initial_rotations(model_points: FloatArray, scan_points: FloatArray) -> list[FloatArray]:
    """Ground-truth-blind proper PCA alignments, ordered for rotational diversity."""
    def basis(points: FloatArray) -> tuple[FloatArray, FloatArray]:
        center = points.mean(axis=0)
        _, vectors = np.linalg.eigh(np.cov((points - center).T))
        return center, vectors[:, ::-1]

    model_center, model_basis = basis(model_points)
    scan_center, scan_basis = basis(scan_points)
    _ = model_center, scan_center
    rotations: list[FloatArray] = []
    for permutation in itertools.permutations(range(3)):
        for signs in itertools.product((-1.0, 1.0), repeat=3):
            rotation = scan_basis[:, permutation] @ np.diag(signs) @ model_basis.T
            if np.linalg.det(rotation) > 0.999:
                rotations.append(rotation)
    selected = [min(rotations, key=lambda matrix: _rotation_angle(matrix, np.eye(3)))]
    remaining = [rotation for rotation in rotations if not np.allclose(rotation, selected[0])]
    while remaining:
        next_rotation = max(
            remaining,
            key=lambda candidate: min(_rotation_angle(candidate, chosen) for chosen in selected),
        )
        selected.append(next_rotation)
        remaining = [candidate for candidate in remaining if candidate is not next_rotation]
    return selected


def _rotation_angle(first: FloatArray, second: FloatArray) -> float:
    cosine = np.clip((np.trace(first @ second.T) - 1.0) / 2.0, -1.0, 1.0)
    return float(np.arccos(cosine))


def _rigid_fit(source: FloatArray, target: FloatArray) -> FloatArray:
    source_center, target_center = source.mean(0), target.mean(0)
    left, _, right = np.linalg.svd((source - source_center).T @ (target - target_center))
    rotation = right.T @ left.T
    if np.linalg.det(rotation) < 0:
        right[-1] *= -1
        rotation = right.T @ left.T
    return make_transform(rotation, target_center - rotation @ source_center)


def register_masked_scan(
    inputs: RegistrationInputs,
    *,
    correspondence_distance_m: float = 0.015,
    max_iterations: int = 12,
    registration_evaluations: int = 6,
    registration_points_max: int = 3000,
    deadline: float | None = None,
) -> dict[str, Any]:
    """Run PCA multi-start ICP on the masked depth cloud. No GT is read or accepted."""
    scan = inputs.scan_points_camera_m
    model = inputs.evaluation_points_object_m
    if len(scan) < 20 or len(model) < 20:
        raise ValueError("Insufficient visible scan or CAD surface points")
    model_ids = np.linspace(0, len(model) - 1, min(registration_points_max, len(model)), dtype=np.int64)
    model_fit = model[model_ids]
    rotations = pca_initial_rotations(model_fit, scan)
    if not 1 <= registration_evaluations <= len(rotations):
        raise ValueError("registration_evaluations must be between 1 and 24")
    scan_tree = cKDTree(scan)
    model_tree = cKDTree(model)
    best: dict[str, Any] | None = None
    for init_index, rotation in enumerate(rotations[:registration_evaluations]):
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError("Per-instance registration deadline exceeded")
        estimate = make_transform(rotation, scan.mean(0) - rotation @ model_fit.mean(0))
        for _ in range(max_iterations):
            if deadline is not None and time.monotonic() > deadline:
                raise TimeoutError("Per-instance registration deadline exceeded")
            moved = transform_points(model_fit, estimate)
            distances, nearest = scan_tree.query(moved, k=1, workers=1)
            inliers = distances <= correspondence_distance_m
            if inliers.sum() < 20:
                break
            update = _rigid_fit(moved[inliers], scan[nearest[inliers]])
            estimate = update @ estimate
            if np.linalg.norm(update[:3, 3]) < 1e-5:
                break
        scan_in_object = transform_points(scan, invert_transform(estimate))
        scan_distances, _ = model_tree.query(scan_in_object, k=1, workers=1)
        scan_inliers = scan_distances <= correspondence_distance_m
        fitness = float(scan_inliers.mean())
        rmse = float(np.sqrt(np.mean(np.square(scan_distances[scan_inliers])))) if scan_inliers.any() else math.inf
        candidate = {
            "camera_from_object": estimate,
            "fitness": fitness,
            "inlier_rmse_m": rmse,
            "inlier_count": int(scan_inliers.sum()),
            "scan_point_count": len(scan),
            "initialization": "24 PCA signed-axis starts; geometry-only ranking",
            "selected_initialization_index": init_index,
            "registration_evaluations": registration_evaluations,
            "iterations_max": max_iterations,
            "max_correspondence_distance_m": correspondence_distance_m,
        }
        if best is None or (fitness, -rmse) > (best["fitness"], -best["inlier_rmse_m"]):
            best = candidate
    assert best is not None
    return best