import struct
from dataclasses import fields

import numpy as np

from autoframe3d.tless_adapter import depth_to_camera_points, read_ply_model


def test_bop_depth_scale_and_camera_projection_are_in_metres(tmp_path):
    depth = np.array([[100, 0], [200, 300]], dtype=np.uint16)
    mask = np.ones((2, 2), dtype=bool)
    camera = np.array([[2.0, 0.0, 0.5], [0.0, 4.0, 0.5], [0.0, 0.0, 1.0]])
    points = depth_to_camera_points(depth, mask, camera, depth_scale_mm_per_unit=0.1)
    np.testing.assert_allclose(
        points,
        [[-0.0025, -0.00125, 0.01], [-0.005, 0.0025, 0.02], [0.0075, 0.00375, 0.03]],
        atol=1e-12,
    )


def test_ascii_ply_model_converts_millimetres_to_metres(tmp_path):
    path = tmp_path / "ascii.ply"
    path.write_text(
        "ply\nformat ascii 1.0\nelement vertex 3\n"
        "property float x\nproperty float y\nproperty float z\n"
        "element face 1\nproperty list uchar int vertex_indices\nend_header\n"
        "0 0 0\n100 0 0\n0 200 0\n3 0 1 2\n",
        encoding="ascii",
    )
    model = read_ply_model(path)
    np.testing.assert_allclose(model.vertices_m, [[0, 0, 0], [0.1, 0, 0], [0, 0.2, 0]])
    np.testing.assert_array_equal(model.faces, [[0, 1, 2]])


def test_binary_little_endian_ply_model_parses_faces_and_units(tmp_path):
    path = tmp_path / "binary.ply"
    header = (
        b"ply\nformat binary_little_endian 1.0\nelement vertex 3\n"
        b"property float x\nproperty float y\nproperty float z\n"
        b"element face 1\nproperty list uchar int vertex_indices\nend_header\n"
    )
    vertices = b"".join(struct.pack("<fff", *point) for point in ((0, 0, 0), (25, 0, 0), (0, 50, 0)))
    face = struct.pack("<Biii", 3, 0, 1, 2)
    path.write_bytes(header + vertices + face)
    model = read_ply_model(path)
    np.testing.assert_allclose(model.vertices_m, [[0, 0, 0], [0.025, 0, 0], [0, 0.05, 0]])
    np.testing.assert_array_equal(model.faces, [[0, 1, 2]])


def test_registration_inputs_do_not_expose_ground_truth_pose():
    from autoframe3d.tless_adapter import RegistrationInputs

    names = {item.name for item in fields(RegistrationInputs)}
    assert "ground_truth" not in " ".join(names)
    assert "camera_from_object_ground_truth" not in names