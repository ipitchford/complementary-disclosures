#!/usr/bin/env python3
"""Fresh witness-retaining random study; --historical-suite reuses 44 inputs,
not historical answers. New output directory required; at most two workers.
"""
from fractions import Fraction as F
from pathlib import Path
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import time
from netinfo import (rat, random_dag_instance, random_instance, exact_width_bisection,
                     subsets, optimal_threshold, oracle, instance_record, json_ready, z3)
ROOT = Path(__file__).resolve().parents[1]


def study_instance(n, edges, seed, menu, tol_denom, timeout_ms, topology='dag'):
    started = time.perf_counter()
    inst, meta = (random_dag_instance if topology == 'dag' else random_instance)(n, edges, seed, menu)
    shock = rat(meta['shock'])
    rec = {'schema': 2, 'provenance': 'fresh_repaired_witness_retaining_run', 'name': inst.name,
           'n': n, 'edges': len(inst.bounds), 'requested_edges': edges, 'seed': seed,
           'menu': len(inst.queries), 'generator': meta, 'instance': instance_record(inst),
           'shock': str(shock), 'shocked': meta['shocked'], 'status': 'ok', 'queries': [],
           'timeout_ms': timeout_ms, 'bracket_tolerance': str(shock / tol_denom)}
    def retain(log, stage):
        for query in log:
            query['stage'] = stage
            rec['queries'].append(query)
    def finish():
        queries = rec['queries']
        rec.update(oracle_calls=len(queries), oracle_seconds=sum(q['seconds'] for q in queries),
                   max_call_seconds=max((q['seconds'] for q in queries), default=0),
                   unknown_calls=sum(q['status'] == 'unknown' for q in queries),
                   solver_only_sat_calls=sum(q['status'] == 'sat' and not q['rational_verified'] for q in queries),
                   wall_seconds=time.perf_counter() - started)
        return rec
    if shock == 0:
        rec['status'] = 'zero_shock'
        return finish()
    tol = shock / tol_denom
    widths = {}
    bisection_start = time.perf_counter()
    for selected in subsets(len(inst.queries)):
        lo, hi, log = exact_width_bisection(inst, selected, upper=shock, tol=tol,
                                           timeout_ms=timeout_ms, test_upper=False)
        retain(log, 'width:' + str(selected))
        rec['widths'] = {str(k): [str(a), str(b)] for k, (a, b) in widths.items()}
        if lo is None or hi is None or hi - lo > tol or any(q['status'] == 'unknown' or q['status'] == 'sat' and not q['rational_verified'] for q in log):
            rec.update(status='unresolved', failed_subset=list(selected),
                       failed_bracket=[None if lo is None else str(lo), None if hi is None else str(hi)],
                       bisection_seconds=time.perf_counter() - bisection_start)
            return finish()
        widths[selected] = (lo, hi)
    rec['bisection_seconds'] = time.perf_counter() - bisection_start
    rec['widths'] = {str(k): [str(a), str(b)] for k, (a, b) in widths.items()}
    initial_lo, initial_hi = widths[()]
    rec['initial_width'] = [str(initial_lo), str(initial_hi)]
    rec['initial_width_over_shock_bracket'] = [str(initial_lo / shock), str(initial_hi / shock)]
    rec['zero_width_status'] = 'positive_certified' if initial_lo > 0 else 'not_determined_by_bracket'
    if initial_lo == 0:
        query = oracle(inst, [], F(0), '>', timeout_ms)
        retain([query], 'zero_width')
        rec['zero_width_status'] = ('zero_certified_by_solver_unsat' if query['status'] == 'unsat' else
                                    'positive_certified' if query.get('rational_verified') else 'unresolved')
    d = len(inst.queries)
    full = tuple(range(d))
    rec['full_menu_width'] = list(map(str, widths[full]))
    rec['certified_negligible_singletons'] = [j for j in range(d) if initial_hi - widths[(j,)][0] <= tol]
    rec['singleton_gain_upper_bounds'] = {str(j): str(initial_hi - widths[(j,)][0]) for j in range(d)}
    rec['certified_informative_full_menu'] = widths[full][1] < initial_lo
    violations = []
    for selected in subsets(d):
        for larger in subsets(d):
            if set(selected) < set(larger):
                for j in range(d):
                    if j in larger:
                        continue
                    sj, tj = tuple(sorted(selected + (j,))), tuple(sorted(larger + (j,)))
                    earlier = widths[selected][1] - widths[sj][0]
                    later = widths[larger][0] - widths[tj][1]
                    if later > earlier:
                        violations.append({'S': list(selected), 'T': list(larger), 'j': j,
                                           'marginal_at_S_max': str(earlier), 'marginal_at_T_min': str(later)})
    rec['certified_submodularity_violations'] = violations
    rec['complementarity'] = bool(violations)
    if initial_lo > 0:
        epsilon = initial_hi / 2
        selection_start = time.perf_counter()
        selection = optimal_threshold(inst, epsilon, timeout_ms=timeout_ms)
        selection_queries = [selection['feasibility']] + selection['history']
        retain(selection_queries, 'selection')
        rec['selection'] = {**selection, 'seconds': time.perf_counter() - selection_start,
                            'target_definition': 'half_the_initial_upper_bracket_not_exact_half_width',
                            'target_excess_over_true_half_width_upper_bound': str((initial_hi-initial_lo)/2),
                            'oracle_calls': len(selection_queries),
                            'oracle_seconds': sum(q['seconds'] for q in selection_queries),
                            'max_call_seconds': max(q['seconds'] for q in selection_queries)}
    screens = []
    for j in range(d):
        query = oracle(inst, [], F(0), '>=', timeout_ms, different_report=j)
        retain([query], 'accounting_redundancy')
        screens.append({'report': j, 'classification': 'fixed_by_accounting_constraints' if query['status'] == 'unsat' else
                        'variable_with_verified_witness' if query.get('rational_verified') else 'unresolved',
                        'query_id': query['query_id']})
    rec['accounting_redundancy_screen'] = screens
    return finish()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', default='5')
    parser.add_argument('--edges-factor', type=float, default=2.0)
    parser.add_argument('--edges-add', type=int, default=2)
    parser.add_argument('--menu', type=int, default=3)
    parser.add_argument('--per', type=int, default=1)
    parser.add_argument('--tol', type=int, default=64)
    parser.add_argument('--timeout', type=int, default=40)
    parser.add_argument('--topology', choices=('dag', 'cyclic'), default='dag')
    parser.add_argument('--workers', type=int, choices=(1, 2), default=1)
    parser.add_argument('--historical-suite', action='store_true')
    parser.add_argument('--outdir', type=Path, required=True)
    args = parser.parse_args()
    if args.tol <= 0 or args.timeout <= 0 or args.per <= 0:
        parser.error('tol, timeout and per must be positive')
    args.outdir.mkdir(parents=True, exist_ok=False)
    jobs = []
    if args.historical_suite:
        for tag in ('dag_menu3_a', 'dag_menu3_b', 'dag_menu4', 'cyclic_menu3'):
            historical = json.loads((ROOT / 'results' / (tag + '.json')).read_text())
            settings = historical['args']
            for record in historical['records']:
                jobs.append((record['n'], record['edges'], record['seed'], record['menu'],
                             settings['tol'], args.timeout * 1000, settings['topology']))
    else:
        jobs = [(n, round(args.edges_factor*n)+args.edges_add, 1000*n+seed, args.menu,
                 args.tol, args.timeout*1000, args.topology) for n in map(int, args.sizes.split(',')) for seed in range(args.per)]
    summary = {'schema': 2, 'provenance': 'fresh_repaired_witness_retaining_run',
               'started_utc': datetime.now(timezone.utc).isoformat(), 'planned_instances': len(jobs),
               'workers': args.workers, 'z3_version': z3.get_version_string(), 'records': [],
               'code_sha256': {name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                               for name in ('netinfo.py', 'study_random.py')}}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(study_instance, *job): (index, job) for index, job in enumerate(jobs)}
        for future in as_completed(futures):
            index, job = futures[future]
            try:
                record = future.result()
            except Exception as error:
                record = {'status': 'error', 'exception': type(error).__name__, 'message': str(error), 'job': job}
            filename = f'instance-{index:03d}.json'
            with (args.outdir/filename).open('x') as output:
                json.dump(json_ready(record), output, indent=1)
            brief = {k: record.get(k) for k in ('name', 'status', 'initial_width', 'edges', 'requested_edges',
                                               'oracle_calls', 'unknown_calls', 'solver_only_sat_calls', 'wall_seconds')}
            brief.update(index=index, file=filename)
            summary['records'].append(brief)
            (args.outdir/'summary.json').write_text(json.dumps(summary, indent=1))
            print(json.dumps(brief), flush=True)
    summary['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (args.outdir/'summary.json').write_text(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
