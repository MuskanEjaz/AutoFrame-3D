"""Partial-observation regression for the explicit development ICP policy."""
from types import SimpleNamespace

import numpy as np
import pytest

from autoframe3d import tless_adapter
from autoframe3d.geometry import make_transform, transform_points
from scipy.spatial.transform import Rotation


def controlled_partial_observation(partial, perturbed, policy):
    """An asymmetric curved front sheet with four hidden parallel sheets.

    The visible sheet is noncoplanar and has distinct x/y dimensions/curvature.
    Exact noiseless correspondences isolate overlap bias from sensor noise.
    The complete-cloud control observes all sheets.
    """
    x, y = np.meshgrid(np.linspace(-.043, .039, 11), np.linspace(-.027, .031, 9))
    z = .005 * ((x + .043) / .082) ** 2 + .002 * np.sin(5 * y / .031) + .003 * x * y / (.043 * .031)
    visible = np.column_stack((x.ravel(), y.ravel(), z.ravel()))
    assert np.linalg.matrix_rank(visible - visible.mean(0)) == 3
    model = np.vstack([visible + [0, 0, d] for d in (0., .004, .006, .008, .010)])
    truth = make_transform(Rotation.from_euler('xyz', [17, -11, 29], degrees=True).as_matrix(), np.array([.11, -.07, .75]))
    scan = transform_points(visible if partial else model, truth)
    initial = truth.copy()
    if perturbed:
        # Object-coordinate perturbation: 0.2 degrees and sub-mm translation.
        initial = truth @ make_transform(Rotation.from_euler('xyz', [.12, -.16, .08], degrees=True).as_matrix(), np.array([.00035, -.00025, .0003]))
    trace = []
    result = tless_adapter._refine_icp(scan, model, model, initial, correspondence_distance_m=.015, max_iterations=8, icp_correspondence_policy=policy, iteration_trace=trace)
    def independent_error(estimate):
        return {'translation_m': float(np.linalg.norm(estimate[:3, 3] - truth[:3, 3])),
                'rotation_deg': float(np.degrees(Rotation.from_matrix(estimate[:3, :3] @ truth[:3, :3].T).magnitude())),
                'maximum_point_displacement_m': float(np.linalg.norm(transform_points(model, estimate) - transform_points(model, truth), axis=1).max())}
    return {'partial': partial, 'perturbed': perturbed, 'policy': policy, 'initial_error': independent_error(initial), 'final_error': independent_error(result), 'iterations': [dict(independent_error(row['camera_from_object']), correspondence_count=row['correspondence_count']) for row in trace]}


@pytest.mark.parametrize('partial', [False, True])
@pytest.mark.parametrize('perturbed', [False, True])
def test_reciprocal_icp_converges_on_asymmetric_observable_geometry(partial, perturbed):
    result = controlled_partial_observation(partial, perturbed, 'reciprocal')
    assert result['iterations']
    assert result['final_error']['translation_m'] < 1e-10
    assert result['final_error']['rotation_deg'] < 1e-8
    assert result['final_error']['maximum_point_displacement_m'] < 1e-10
    assert len(result['iterations']) <= 3


@pytest.mark.parametrize('perturbed', [False, True])
def test_historical_icp_drift_is_specific_to_partial_overlap(perturbed):
    partial = controlled_partial_observation(True, perturbed, 'model_to_scan')
    full = controlled_partial_observation(False, perturbed, 'model_to_scan')
    assert partial['final_error']['maximum_point_displacement_m'] > .003
    assert full['final_error']['maximum_point_displacement_m'] < 1e-10


def test_unobserved_model_surfaces_do_not_pull_exact_visible_alignment(monkeypatch):
    rng = np.random.default_rng(19)
    visible = rng.uniform(-.04, .04, (100, 3))
    visible[:, 2] = 0
    visible[:, :2] -= visible[:, :2].mean(0)
    # Balanced full-model centroid, but only the upper hidden layer lies within
    # the correspondence gate. Model-to-scan ICP pulls that unseen layer inward.
    upper = np.tile(visible, (4, 1)) + [0, 0, .005]
    lower = visible + [0, 0, -.020]
    model = np.vstack([visible, upper, lower])
    inputs = SimpleNamespace(scan_points_camera_m=visible, evaluation_points_object_m=model)
    monkeypatch.setattr(tless_adapter, "pca_initial_rotations", lambda model, scan: [np.eye(3)])
    kwargs = dict(registration_evaluations=1, max_iterations=8)
    historical = tless_adapter.register_masked_scan(inputs, **kwargs)
    observed = tless_adapter.register_masked_scan(inputs, icp_correspondence_policy="scan_to_model", **kwargs)
    np.testing.assert_allclose(observed["camera_from_object"], np.eye(4), atol=1e-12)
    assert abs(historical["camera_from_object"][2, 3]) > .003
    assert observed["inlier_rmse_m"] < 1e-12


def test_unknown_correspondence_policy_is_rejected():
    with pytest.raises(ValueError, match="Unknown ICP"):
        tless_adapter.register_masked_scan(None, icp_correspondence_policy="oracle")
