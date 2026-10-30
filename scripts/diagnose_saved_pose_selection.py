"""Offline scalar-only diagnosis of four immutable saved pairs. Never fits geometry."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path('audit_evidence/saved_pose_reciprocal_20261014')
IDS = (
    'tless-s000001-i000001-g00-o02', 'tless-s000002-i000003-g00-o05',
    'tless-s000002-i000003-g01-o06', 'tless-s000002-i000024-g02-o07',
)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def rule_expressions(root=ROOT):
    """Extract the current source expressions without importing the fitting code."""
    adapter = ast.parse((root / 'autoframe3d/tless_adapter.py').read_text(encoding='utf-8'))
    register = next(n for n in adapter.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'register_masked_scan')
    ranking = [n.test for n in ast.walk(register) if isinstance(n, ast.If)
               and ast.unparse(n.test).startswith('best is None or')]
    metrics = ast.parse((root / 'autoframe3d/tless_metrics.py').read_text(encoding='utf-8'))
    classify = next(n for n in metrics.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'classify_result')
    acceptance = [n.value for n in classify.body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'accepted' for t in n.targets)]
    if len(ranking) != 1 or len(acceptance) != 1:
        raise ValueError('Selection/acceptance source shape changed; review before diagnosis')
    # Fail closed if source starts using other inputs (especially GT).
    for expr, allowed in ((ranking[0], {'best', 'fitness', 'rmse'}),
                          (acceptance[0], {'fitness', 'rmse_m', 'minimum_fitness', 'maximum_rmse_m'})):
        if {n.id for n in ast.walk(expr) if isinstance(n, ast.Name)} != allowed:
            raise ValueError('Rule inputs changed; manual source review required')
        if any(isinstance(n, (ast.Call, ast.Attribute)) for n in ast.walk(expr)):
            raise ValueError('Unexpected executable rule content')
    return ranking[0], acceptance[0]


def choose_pair(baseline, refined, ranking):
    """Pass geometry scalars only; exact ties retain the baseline (visited first)."""
    best = None
    selected = None
    for label, values in (('baseline', baseline), ('refined', refined)):
        candidate = {k: float(values[k]) for k in ('fitness', 'inlier_rmse_m')}
        if not all(math.isfinite(v) for v in candidate.values()):
            raise ValueError('Nonfinite saved geometric metric')
        take = eval(compile(ast.Expression(ranking), '<current ranking>', 'eval'),
                    {'__builtins__': {}}, {'best': best, 'fitness': candidate['fitness'],
                                          'rmse': candidate['inlier_rmse_m']})
        if take:
            best, selected = candidate, label
    return selected


def diagnose(root=ROOT):
    evidence = root / EVIDENCE
    summary = read(evidence / 'summary.json')
    manifest_path = evidence / 'manifest.json'
    if sha(manifest_path) != summary['manifest_sha256']:
        raise ValueError('Manifest hash mismatch')
    manifest = read(manifest_path)
    config = read(root / 'configs/tless_frozen.json')
    if config['geometric_acceptance'] != manifest['scoring']['geometric_acceptance']:
        raise ValueError('Acceptance configuration changed')
    if config['pose_correctness'] != manifest['scoring']['pose_correctness']:
        raise ValueError('Correctness configuration changed')
    ranking, acceptance = rule_expressions(root)
    rows = []
    hashes = {'manifest.json': sha(manifest_path)}
    for index, case_id in enumerate(IDS):
        name = f'case-{index+1}.json'
        path = evidence / name
        if sha(path) != summary['result_sha256'][name]:
            raise ValueError(f'Result hash mismatch: {name}')
        hashes[name] = sha(path)
        result, item = read(path), manifest['cases'][index]
        if result['case_id'] != case_id or item['case']['case_id'] != case_id:
            raise ValueError('Case order/identity mismatch')
        if result['manifest_sha256'] != summary['manifest_sha256']:
            raise ValueError('Case manifest reference mismatch')
        if (result['initial_camera_from_object'] != item['initial_camera_from_object']
                or canonical_sha(result['initial_camera_from_object']) != item['initial_pose_sha256']):
            raise ValueError('Saved initial pose mismatch')
        before, after = result['baseline'], result['refined']
        saved = item['saved_baseline']
        for section, keys in (('alignment_quality_metrics', ('fitness', 'inlier_rmse_m')),
                              ('pose_metrics', ('mssd_m', 'mssd_over_diameter'))):
            if any(abs(before[k] - saved[section][k]) > 1e-9 for k in keys):
                raise ValueError('Baseline scalar mismatch')
        if result['status'] != 'completed':
            raise ValueError('Incomplete pair requires explicit handling')
        # This decision occurs before accessing GT scores below.
        selected = choose_pair(before, after, ranking)
        accepted = []
        for metrics in (before, after):
            value = eval(compile(ast.Expression(acceptance), '<current acceptance>', 'eval'),
                         {'__builtins__': {}}, {
                             'fitness': metrics['fitness'], 'rmse_m': metrics['inlier_rmse_m'],
                             'minimum_fitness': config['geometric_acceptance']['minimum_fitness'],
                             'maximum_rmse_m': config['geometric_acceptance']['maximum_inlier_rmse_m']})
            if value != metrics['accepted']:
                raise ValueError('Saved acceptance disagrees with current rule')
            if (metrics['mssd_over_diameter'] <= config['pose_correctness']['maximum_normalized_mssd']) != metrics['correct']:
                raise ValueError('Saved correctness disagrees with threshold')
            accepted.append(value)
        rows.append({
            'case_id': case_id, 'baseline': before, 'refined': after,
            'fitness_delta': after['fitness'] - before['fitness'],
            'rmse_delta_mm': 1000 * (after['inlier_rmse_m'] - before['inlier_rmse_m']),
            'mssd_delta_mm': 1000 * (after['mssd_m'] - before['mssd_m']),
            'normalized_mssd_delta': after['mssd_over_diameter'] - before['mssd_over_diameter'],
            'hypothetical_ranked_choice': selected,
            'reason': 'higher fitness' if before['fitness'] != after['fitness'] else 'tied fitness; lower RMSE',
            'both_geometrically_accepted': all(accepted),
            'selected_gt_error_worsens': result[selected]['mssd_over_diameter'] > before['mssd_over_diameter'],
            'correctness_transition': f"{before['correct']} -> {result[selected]['correct']}",
            'termination': result['termination'], 'iterations': result['iterations'],
            'reciprocal_correspondence_counts': result['correspondence_counts'],
            'saved_baseline_inlier_count': saved['alignment_quality_metrics']['inlier_count'],
            'saved_scan_point_count': saved['alignment_quality_metrics']['scan_point_count'],
            'origin_shift_mm': 1000 * math.sqrt(sum(
                (result['refined_camera_from_object'][i][3] - result['initial_camera_from_object'][i][3]) ** 2
                for i in range(3))),
            'relative_rotation_degrees': math.degrees(math.acos(max(-1., min(1., (
                sum(result['refined_camera_from_object'][i][j] * result['initial_camera_from_object'][i][j]
                    for i in range(3) for j in range(3)) - 1) / 2)))),
        })
    source_files = ('autoframe3d/tless_adapter.py', 'autoframe3d/tless_metrics.py',
                    'autoframe3d/tless_benchmark.py', 'configs/tless_frozen.json',
                    'scripts/evaluate_saved_pose_reciprocal.py', 'scripts/diagnose_saved_pose_selection.py')
    return {
        'scope': 'Four saved pairs only; current ranking applied hypothetically baseline first; no fitting or GT in selection',
        'ranking_expression': ast.unparse(ranking), 'acceptance_expression': ast.unparse(acceptance),
        'evidence_sha256': hashes, 'source_sha256': {p: sha(root / p) for p in source_files},
        'cases': rows,
        'counts': {'pairs': len(rows), 'refined_selected': sum(r['hypothetical_ranked_choice'] == 'refined' for r in rows),
                   'selected_error_worsens': sum(r['selected_gt_error_worsens'] for r in rows),
                   'recoveries': sum(not r['baseline']['correct'] and r[r['hypothetical_ranked_choice']]['correct'] for r in rows),
                   'regressions': sum(r['baseline']['correct'] and not r[r['hypothetical_ranked_choice']]['correct'] for r in rows)},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional diagnostic JSON output; never use the frozen experiment directory')
    args = parser.parse_args()
    result = diagnose()
    text = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        destination = args.output.resolve()
        destination.relative_to(ROOT)
        if destination.is_relative_to(ROOT / EVIDENCE):
            parser.error('Frozen experiment directory is read-only for this diagnostic')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding='utf-8')
    print(text)
