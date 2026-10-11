import numpy as np

from autoframe3d.geometry import make_transform, pose_error, rotation_z, transform_points


def test_transform_maps_points_with_translation_and_rotation():
    transform = make_transform(rotation_z(90), np.array([1.0, 2.0, 3.0]))
    actual = transform_points(np.array([[1.0, 0.0, 0.0]]), transform)
    np.testing.assert_allclose(actual, [[1.0, 3.0, 3.0]], atol=1e-12)


def test_pose_error_ignores_only_declared_exact_symmetry():
    truth = make_transform(rotation_z(0), np.zeros(3))
    quarter_turn = make_transform(rotation_z(90), np.zeros(3))
    assert pose_error(quarter_turn, truth, symmetry_order=4)["rotation_error_deg"] < 1e-6
    assert pose_error(quarter_turn, truth, symmetry_order=1)["rotation_error_deg"] == 90.0