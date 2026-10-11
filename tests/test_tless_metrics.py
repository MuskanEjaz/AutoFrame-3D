import numpy as np

from autoframe3d.geometry import make_transform, rotation_z
from autoframe3d.tless_metrics import bop_symmetry_transforms, classify_result, mssd_normalized


def test_discrete_exact_symmetry_is_not_counted_as_pose_error():
    symmetry = make_transform(rotation_z(180), np.zeros(3))
    symmetries = bop_symmetry_transforms({"symmetries_discrete": [symmetry.reshape(-1).tolist()]})
    points = np.array([[0.1, 0, 0], [0, 0.2, 0], [0, 0, 0.1]])
    estimate = symmetry
    metric = mssd_normalized(estimate, np.eye(4), points, symmetries, diameter_m=0.5)
    assert metric["mssd_m"] < 1e-12
    assert metric["mssd_over_diameter"] < 1e-12


def test_continuous_z_symmetry_uses_bop_diameter_step_rule():
    symmetries = bop_symmetry_transforms(
        {"symmetries_continuous": [{"axis": [0, 0, 1], "offset": [0, 0, 0]}]},
        max_symmetry_step=0.01,
    )
    assert len(symmetries) == int(np.ceil(np.pi / 0.01))


def test_four_geometric_acceptance_and_pose_categories_are_distinct():
    assert classify_result(0.9, 0.005, 0.05)[2] == "accepted_and_correct"
    assert classify_result(0.9, 0.005, 0.5)[2] == "accepted_but_wrong"
    assert classify_result(0.4, 0.005, 0.05)[2] == "rejected_and_correct"
    assert classify_result(0.4, 0.02, 0.5)[2] == "rejected_and_wrong"