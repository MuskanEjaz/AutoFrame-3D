"""Protect offline diagnosis from GT leakage, changed evidence and stale output."""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('selection_diagnostic', ROOT / 'scripts/diagnose_saved_pose_selection.py')
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


def test_selection_does_not_receive_gt_and_ignores_injected_labels():
    ranking, _ = diagnostic.rule_expressions()
    baseline = {'fitness': .9, 'inlier_rmse_m': .005, 'correct': True, 'mssd_over_diameter': 0.}
    refined = {'fitness': .91, 'inlier_rmse_m': .006, 'correct': False, 'mssd_over_diameter': 9.}
    assert diagnostic.choose_pair(baseline, refined, ranking) == 'refined'
    baseline['correct'], refined['correct'] = False, True
    baseline['mssd_over_diameter'], refined['mssd_over_diameter'] = 9., 0.
    assert diagnostic.choose_pair(baseline, refined, ranking) == 'refined'
    assert diagnostic.choose_pair({k: baseline[k] for k in ('fitness', 'inlier_rmse_m')},
                                  {k: refined[k] for k in ('fitness', 'inlier_rmse_m')}, ranking) == 'refined'


def test_current_lexicographic_priority_and_exact_tie_retention():
    ranking, _ = diagnostic.rule_expressions()
    before = {'fitness': .9, 'inlier_rmse_m': .005}
    assert diagnostic.choose_pair(before, dict(before), ranking) == 'baseline'
    assert diagnostic.choose_pair(before, {'fitness': .899, 'inlier_rmse_m': .001}, ranking) == 'baseline'
    assert diagnostic.choose_pair(before, {'fitness': .9, 'inlier_rmse_m': .004}, ranking) == 'refined'


def test_published_analysis_is_reproducible_and_four_pairs_are_unchanged():
    expected = json.loads((ROOT / 'audit_evidence/selection_diagnostic_20261023/analysis.json').read_text())
    actual = diagnostic.diagnose()
    # Reproduction preserves saved pairs/rules/results; current source identity
    # must be truthful rather than rewritten to the historical adapter hash.
    assert set(actual['source_sha256']) == set(expected['source_sha256'])
    for name, digest in actual['source_sha256'].items():
        assert digest == diagnostic.sha(ROOT / name)
        if name not in {'autoframe3d/tless_adapter.py', 'scripts/evaluate_saved_pose_reciprocal.py'}:
            assert digest == expected['source_sha256'][name]
    assert {k: v for k, v in actual.items() if k != 'source_sha256'} == {
        k: v for k, v in expected.items() if k != 'source_sha256'}
    assert expected['counts'] == {'pairs': 4, 'refined_selected': 4, 'selected_error_worsens': 3,
                                  'recoveries': 0, 'regressions': 0}


def test_changed_evidence_is_rejected(tmp_path):
    for relative in (diagnostic.EVIDENCE, Path('configs'), Path('autoframe3d')):
        shutil.copytree(ROOT / relative, tmp_path / relative)
    case = tmp_path / diagnostic.EVIDENCE / 'case-1.json'
    case.write_text(case.read_text() + ' ')
    with pytest.raises(ValueError, match='Result hash mismatch'):
        diagnostic.diagnose(tmp_path)


def test_rule_with_additional_gt_input_is_rejected(tmp_path):
    (tmp_path / 'autoframe3d').mkdir()
    for name in ('tless_adapter.py', 'tless_metrics.py'):
        text = (ROOT / 'autoframe3d' / name).read_text(encoding='utf-8')
        if name == 'tless_adapter.py':
            text = text.replace('if best is None or (fitness, -rmse)',
                                'if best is None or gt_correct and (fitness, -rmse)')
        (tmp_path / 'autoframe3d' / name).write_text(text, encoding='utf-8')
    with pytest.raises(ValueError, match='Rule inputs changed'):
        diagnostic.rule_expressions(tmp_path)
