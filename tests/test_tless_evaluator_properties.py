import numpy as np

from autoframe3d.geometry import make_transform, rotation_z
from autoframe3d.tless_metrics import bop_symmetry_transforms, classify_result, mssd_normalized


def test_mssd_identity_pose():
    points = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    symmetries = [np.eye(4)]
    diameter = 2.0
    res = mssd_normalized(np.eye(4), np.eye(4), points, symmetries, diameter)
    assert np.isclose(res["mssd_m"], 0.0, atol=1e-12)
    assert np.isclose(res["mssd_over_diameter"], 0.0, atol=1e-12)


def test_mssd_known_translation():
    points = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    symmetries = [np.eye(4)]
    diameter = 2.0
    translation_vector = np.array([0.2, 0.0, 0.0])
    estimate = make_transform(np.eye(3), translation_vector)
    res = mssd_normalized(estimate, np.eye(4), points, symmetries, diameter)
    assert np.isclose(res["mssd_m"], 0.2, atol=1e-12)
    assert np.isclose(res["mssd_over_diameter"], 0.1, atol=1e-12)


def test_mssd_valid_symmetry_with_translation_offset():
    # Symmetry: rotation about Z by 180 deg with an offset translation [0.1, 0.2, 0.3]
    rot = rotation_z(180)
    offset = np.array([0.1, 0.2, 0.3])
    sym_matrix = make_transform(rot, offset - rot @ offset)
    bop_sym_matrix = sym_matrix.copy()
    bop_sym_matrix[:3, 3] *= 1000.0  # BOP model metadata uses millimetres.
    symmetries = bop_symmetry_transforms({
        "symmetries_discrete": [bop_sym_matrix.reshape(-1).tolist()],
        "symmetries_continuous": [],
    })
    points = np.array([[0.5, 0.0, 0.0], [0.0, 0.5, 0.0]])
    diameter = 2.0
    # If estimate equals the valid symmetry transform relative to GT (GT = I), MSSD should be zero.
    res = mssd_normalized(sym_matrix, np.eye(4), points, symmetries, diameter)
    assert np.isclose(res["mssd_m"], 0.0, atol=1e-10)
    assert np.isclose(res["mssd_over_diameter"], 0.0, atol=1e-10)


def test_mssd_nonequivalent_pose_exceeds_threshold():
    points = np.array([[1.0, 0.0, 0.0]])
    symmetries = [np.eye(4)]
    diameter = 1.0
    estimate = make_transform(np.eye(3), np.array([0.15, 0.0, 0.0]))
    res = mssd_normalized(estimate, np.eye(4), points, symmetries, diameter)
    assert res["mssd_over_diameter"] > 0.10


def test_threshold_boundaries_classification():
    # fitness >= 0.70, rmse <= 0.010, mssd_over_diameter <= 0.10
    assert classify_result(0.70, 0.010, 0.10)[2] == "accepted_and_correct"
    assert classify_result(0.6999, 0.010, 0.10)[2] == "rejected_and_correct"
    assert classify_result(0.70, 0.0101, 0.10)[2] == "rejected_and_correct"
    assert classify_result(0.70, 0.010, 0.1001)[2] == "accepted_but_wrong"


def test_continuous_symmetry_offset_converts_bop_millimetres():
    symmetries = bop_symmetry_transforms({"symmetries_continuous": [
        {"axis": [0, 0, 1], "offset": [100, 200, 0]}]})
    offset_m = np.array([.1, .2, 0.])
    for symmetry in symmetries:
        np.testing.assert_allclose(symmetry[:3, 3], offset_m - symmetry[:3, :3] @ offset_m, atol=1e-12)
    estimate = make_transform(rotation_z(37), offset_m - rotation_z(37) @ offset_m)
    result = mssd_normalized(estimate, np.eye(4), np.array([[.5, 0, 0], [0, .5, 0]]), symmetries, 2.)
    assert classify_result(1., 0., result["mssd_over_diameter"])[1]
