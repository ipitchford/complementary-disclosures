#!/usr/bin/env python3
"""Read-only tests and replay of retained rational certificates (no study rerun).

python3 -B code/verify_assurance.py [--results results/fresh-full]
Repeat with -O. Solver UNSAT remains solver evidence, not a proof certificate.
"""
import argparse
import ast
import copy
from datetime import datetime
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
import netinfo as n


def reject(label, callback, error=(ValueError, AssertionError, TypeError)):
    try:
        callback()
    except error:
        return label
    raise ValueError('Negative control accepted: ' + label)


def recheck_query(query):
    n.require(query['status'] in ('sat', 'unsat', 'unknown'), 'Invalid solver status')
    n.require(query['solver_status'] == query['status'], 'Solver/status mismatch')
    inst = n.instance_from_record(query['instance'])
    expected_hash = hashlib.sha256(json.dumps(query['instance'], sort_keys=True).encode()).hexdigest()
    n.require(query['instance_sha256'] == expected_hash, 'Instance digest mismatch')
    n.require(type(query['rational_verified']) is bool, 'Verification flag not Boolean')
    if query['status'] == 'sat' and query['rational_verified']:
        n.require(query['evidence'] == 'rational_witness_verified' and query['independent_fraction_check'] == 'passed', 'False rational assurance flag')
        result = n.check_rational_matrices(inst, query['selected'], query['epsilon'], query['relation'],
                                          query['witness_matrices'], query['noise'], different_report=query.get('different_report'))
        for key in ('gap', 'loss_A', 'loss_B', 'clearing_payments', 'distinguishing_queries'):
            n.require(result[key] == query[key], 'Retained witness metadata mismatch: ' + key)
        return 1
    if query['status'] == 'sat':
        n.require(query['evidence'] == 'solver_only_algebraic_sat' and 'witness_matrices' not in query, 'Unverified SAT mislabelled')
    else:
        n.require(not query['rational_verified'], 'Nonsatisfiable verdict cannot verify a witness')
    return 0


def self_tests():
    tests = []
    for source in Path(__file__).parent.rglob('*.py'):
        require_tree = ast.parse(source.read_text())
        n.require(not any(isinstance(node,ast.Assert) for node in ast.walk(require_tree)),
                  'Bare assert may disappear under -O: '+source.name)
    tests.append('all shipped Python checks use explicit exceptions, not removable assert')
    inst = n.layered_instance(1)
    sat = n.oracle(inst, [], F(1, 2), timeout_ms=3000)
    n.require(sat['status'] == 'sat' and recheck_query(sat) == 1, 'Rational SAT smoke test failed')
    tests.append('rational SAT persists complete replayable matrices')
    raw_builder = n.build_pair
    def algebraic_builder(*args, **kwargs):
        solver, variables = raw_builder(*args, **kwargs)
        value = variables[('A', 'L', 0, 2)]
        solver.add(value*value == n.z3.RealVal('1/2'))
        return solver, variables
    with patch.object(n, 'build_pair', algebraic_builder):
        algebraic = n.oracle(inst, [], 0, timeout_ms=3000)
    n.require(algebraic['status'] == 'sat' and algebraic['evidence'] == 'solver_only_algebraic_sat'
              and not algebraic['rational_verified'], 'Actual algebraic model not separated')
    recheck_query(algebraic)
    tests.append('actual square-root algebraic SAT remains solver-only')
    with patch.object(n, 'oracle', return_value=copy.deepcopy(algebraic)):
        lower, upper, logs = n.exact_width_bisection(inst, [], F(2), F(1, 16), test_upper=False)
    n.require((lower, upper) == (F(0), F(2)) and len(logs) == 1, 'Algebraic SAT advanced rational lower bound')
    tests.append('algebraic SAT cannot advance bisection lower bound')
    with patch.object(n, 'oracle', return_value={'status': 'unknown', 'rational_verified': False, 'seconds': 0}):
        unknown = n.optimal_threshold(inst, 0)
    n.require(unknown['status'] == 'unknown', 'UNKNOWN misreported as inconsistent')
    tests.append('unknown feasibility stays unknown')
    with patch.object(n, 'oracle', return_value={'status': 'unsat', 'rational_verified': False, 'seconds': 0}):
        inconsistent = n.optimal_threshold(inst, 0)
    n.require(inconsistent['status'] == 'inconsistent', 'UNSAT feasibility not distinguished')
    tests.append('inconsistent feasibility distinguished from unknown and menu infeasibility')
    with patch.object(n, 'oracle', return_value=copy.deepcopy(algebraic)):
        unverified = n.optimal_threshold(inst, 0)
    n.require(unverified['status'] == 'unknown', 'Selection accepted unverified feasibility')
    tests.append('selection refuses solver-only feasibility')
    bad = copy.deepcopy(sat)
    bad['witness_matrices'][0][0][0] = '1'
    tests.append(reject('forbidden-edge matrix corruption', lambda: recheck_query(bad)))
    bad = copy.deepcopy(sat)
    bad['gap'] = '999'
    tests.append(reject('false retained loss gap', lambda: recheck_query(bad)))
    bad = copy.deepcopy(sat)
    bad['clearing_payments'][0][0] = '999'
    tests.append(reject('false retained payments', lambda: recheck_query(bad)))
    bad = copy.deepcopy(sat)
    bad['instance']['r'][0] = '999'
    tests.append(reject('corrupt instance metadata', lambda: recheck_query(bad)))
    bad = copy.deepcopy(sat)
    bad['rational_verified'] = False
    tests.append(reject('inconsistent evidence classification', lambda: recheck_query(bad)))
    tests.append(reject('float witness coordinate', lambda: n.rat(0.5)))
    tests.append(reject('invalid noise input', lambda: n.build_pair(inst, [0], 0, noise=[F(-1)])))
    generated, meta = n.random_dag_instance(5, 12, 5000, 3)
    n.require(len(generated.bounds) == meta['actual_edges'] == 10 and meta['requested_edges'] == 12, 'Edge metadata regression')
    tests.append('requested twelve versus actual ten DAG edges retained')
    selection = n.optimal_threshold(inst, 0, timeout_ms=3000)
    n.require(selection['status'] == 'optimal' and selection['selected'] == [0] and 'feasibility' in selection, 'Selection history incomplete')
    for query in [selection['feasibility']] + selection['history']:
        recheck_query(query)
    tests.append('selection feasibility and every subsequent query retained')
    return tests


def recheck_record(record):
    n.require(record.get('schema') == 2 and record.get('provenance') == 'fresh_repaired_witness_retaining_run', 'Historical record cannot claim fresh verification')
    n.require(record['status'] in ('ok', 'unresolved', 'zero_shock'), 'Execution error or invalid record status')
    inst = n.instance_from_record(record['instance'])
    generator = record['generator']
    n.require(generator['topology'] in ('dag','cyclic_allowed'),'Invalid generator topology')
    regenerate = n.random_dag_instance if generator['topology']=='dag' else n.random_instance
    expected, metadata = regenerate(record['n'],record['requested_edges'],record['seed'],record['menu'])
    n.require(n.instance_record(expected)==record['instance'] and metadata==generator,'Retained instance differs from deterministic generator inputs')
    n.require(record['edges'] == len(inst.bounds) == generator['actual_edges'], 'Actual edge count mismatch')
    n.require(record['requested_edges'] == generator['requested_edges'], 'Requested edge count mismatch')
    base = [[n.rat(v) for v in row] for row in generator['base_matrix']]
    n.check_rational_matrices(inst, [], 0, '=', [base,base])
    before = list(map(n.rat, generator['before']))
    n.require(n.clearing(base, inst.b, before) == [n.rat(a)+n.rat(b) for a,b in zip(inst.r, inst.b)], 'Pre-shock baseline not fully solvent')
    n.require(sum(before)-sum(inst.x) == n.rat(record['shock']), 'Shock metadata mismatch')
    queries = record['queries']
    witnessed = sum(recheck_query(query) for query in queries)
    n.require(all(query['instance'] == record['instance'] for query in queries), 'Query bound to another instance')
    n.require(record['oracle_calls'] == len(queries), 'Query count omits calls')
    n.require(abs(record['oracle_seconds']-sum(query['seconds'] for query in queries)) < 1e-8, 'Query timing sum mismatch')
    n.require(record['max_call_seconds'] == max((query['seconds'] for query in queries), default=0), 'Longest call omits selection or feasibility')
    n.require(record['unknown_calls'] == sum(query['status']=='unknown' for query in queries), 'Unknown count mismatch')
    n.require(record['solver_only_sat_calls'] == sum(query['status']=='sat' and not query['rational_verified'] for query in queries), 'Unverified SAT count mismatch')
    shock = n.rat(record['shock'])
    reconstructed = {}
    for query in queries:
        if not query['stage'].startswith('width:'):
            continue
        key = query['stage'][6:]
        lo, hi = reconstructed.get(key, (F(0), shock))
        n.require(query['selected'] == list(ast.literal_eval(key)), 'Bracket query selected wrong reports')
        n.require(n.rat(query['epsilon']) == (lo+hi)/2 and query['relation'] == '>', 'Invalid bisection query')
        if query['status'] == 'sat' and query['rational_verified']:
            gap = n.rat(query['gap'])
            n.require((lo+hi)/2 < gap <= hi, 'Invalid rational lower-bound advancement')
            lo = gap
        elif query['status'] == 'unsat':
            hi = (lo+hi)/2
        reconstructed[key] = lo, hi
    for key, bounds in record.get('widths', {}).items():
        n.require(tuple(map(n.rat,bounds)) == reconstructed[key], 'Stored bracket unsupported by query trace')
        n.require(reconstructed[key][1]-reconstructed[key][0] <= n.rat(record['bracket_tolerance']), 'Completed bracket too wide')
    if record['status'] == 'ok':
        n.require(len(record['widths']) == 2**len(inst.queries), 'Incomplete study marked complete')
        widths = {ast.literal_eval(key):tuple(map(n.rat,bounds)) for key,bounds in record['widths'].items()}
        lo,hi = widths[()]
        d = len(inst.queries)
        n.require(list(map(n.rat,record['initial_width']))==[lo,hi], 'Initial bracket metadata mismatch')
        n.require(list(map(n.rat,record['initial_width_over_shock_bracket']))==[lo/shock,hi/shock], 'Width/shock ratio mismatch')
        n.require(tuple(map(n.rat,record['full_menu_width']))==widths[tuple(range(d))], 'Full-menu bracket mismatch')
        negligible = [j for j in range(d) if hi-widths[(j,)][0]<=n.rat(record['bracket_tolerance'])]
        n.require(record['certified_negligible_singletons']==negligible, 'Negligible-report classification mismatch')
        n.require({j:str(hi-widths[(int(j),)][0]) for j in record['singleton_gain_upper_bounds']}==record['singleton_gain_upper_bounds'] and set(record['singleton_gain_upper_bounds'])==set(map(str,range(d))), 'Singleton gain bounds mismatch')
        n.require(record['certified_informative_full_menu']==(widths[tuple(range(d))][1]<lo), 'Full-menu informativeness mismatch')
        violations=[]
        for selected in n.subsets(d):
            for larger in n.subsets(d):
                if set(selected)<set(larger):
                    for j in range(d):
                        if j in larger:
                            continue
                        sj,tj=tuple(sorted(selected+(j,))),tuple(sorted(larger+(j,)))
                        earlier=widths[selected][1]-widths[sj][0]
                        later=widths[larger][0]-widths[tj][1]
                        if later>earlier:
                            violations.append({'S':list(selected),'T':list(larger),'j':j,'marginal_at_S_max':str(earlier),'marginal_at_T_min':str(later)})
        n.require(record['certified_submodularity_violations']==violations and record['complementarity']==bool(violations), 'Complementarity bounds mismatch')
        screens=record['accounting_redundancy_screen']
        screen_queries=[q for q in queries if q['stage']=='accounting_redundancy']
        n.require(len(screens)==len(screen_queries)==d,'Accounting screen population mismatch')
        for j,(screen,query) in enumerate(zip(screens,screen_queries)):
            label='fixed_by_accounting_constraints' if query['status']=='unsat' else 'variable_with_verified_witness' if query['rational_verified'] else 'unresolved'
            n.require(query['different_report']==j and screen=={'report':j,'classification':label,'query_id':query['query_id']},'Accounting classification mismatch')
    elif record['status']=='unresolved':
        key=str(tuple(record['failed_subset']))
        n.require(tuple(map(n.rat,record['failed_bracket']))==reconstructed[key], 'Failed bracket unsupported by trace')
        terminal=queries[-1]
        n.require(terminal['status']=='unknown' or terminal['status']=='sat' and not terminal['rational_verified'], 'Unresolved record lacks unresolved terminal query')
    if record.get('zero_width_status') == 'zero_certified_by_solver_unsat':
        n.require(any(q['stage']=='zero_width' and q['status']=='unsat' and n.rat(q['epsilon'])==0 for q in queries), 'Zero width inferred from bracket alone')
    if 'selection' in record:
        selection = record['selection']
        sq = [selection['feasibility']] + selection['history']
        n.require(sq == [q for q in queries if q['stage']=='selection'], 'Selection history differs from validated retained queries')
        n.require(selection['oracle_calls']==len(sq) and selection['max_call_seconds']==max(q['seconds'] for q in sq), 'Selection timings incomplete')
        n.require(abs(selection['oracle_seconds']-sum(q['seconds'] for q in sq))<1e-8,'Selection timing sum mismatch')
        feasibility=selection['feasibility']
        n.require(feasibility['selected']==[] and feasibility['relation']=='>=' and n.rat(feasibility['epsilon'])==0,'Incorrect selection feasibility query')
        n.require(feasibility['status']!='unsat','Solver infeasibility contradicts exact generator base witness')
        if not feasibility['rational_verified']:
            n.require(selection['status']=='unknown' and not selection['history'] and not selection['cuts'],'Selection proceeded from unresolved feasibility')
        n.require(all(q['relation']=='>' and n.rat(q['epsilon'])==n.rat(selection['epsilon']) for q in selection['history']),'Selection history threshold mismatch')
        n.require(n.rat(selection['epsilon']) == n.rat(record['initial_width'][1])/2, 'Mislabelled selection target')
        n.require(selection['target_definition']=='half_the_initial_upper_bracket_not_exact_half_width', 'Exact half-width misclaim')
        if selection['status']=='optimal':
            n.require(selection['history'][-1]['status']=='unsat' and selection['history'][-1]['selected']==selection['selected'], 'Optimal selection lacks final UNSAT')
        # Reconstruct the exhaustive minimum-cost master and every witness cut.
        candidates = n.subsets(len(inst.queries))
        candidates.sort(key=lambda selected:(sum(inst.queries[j].cost for j in selected),len(selected),selected))
        cuts = []
        for index, query in enumerate(selection['history']):
            candidate = next((s for s in candidates if all(set(s)&set(cut) for cut in cuts)),None)
            n.require(candidate is not None and list(candidate)==query['selected'], 'Selection skipped a cheaper cut-feasible menu')
            if query['status']=='sat' and query['rational_verified']:
                cuts.append(query['distinguishing_queries'])
            else:
                n.require(index==len(selection['history'])-1, 'Selection continued after terminal verdict')
        n.require(cuts==selection['cuts'], 'Stored witness cuts differ from verified history')
        if selection['status']=='infeasible':
            n.require(not any(all(set(s)&set(cut) for cut in cuts) for s in candidates), 'Menu impossibility not established by cuts')
    return {'queries': len(queries), 'rational_witnesses_rechecked': witnessed,
            'unsat_solver_evidence': sum(q['status']=='unsat' for q in queries),
            'unknown_retained': sum(q['status']=='unknown' for q in queries),
            'solver_only_sat_retained': sum(q['status']=='sat' and not q['rational_verified'] for q in queries)}


def recheck_coverage(summary, records, allow_incomplete=False):
    """Bind directory completeness, original design inputs, and summary metadata."""
    n.require(summary.get('schema')==2 and summary.get('provenance')=='fresh_repaired_witness_retaining_run', 'Invalid study summary')
    planned = summary['planned_instances']
    n.require(type(planned) is int and planned>0, 'Invalid planned count')
    briefs = summary['records']
    indices = [r['index'] for r in briefs]
    n.require(all(type(i) is int and 0<=i<planned for i in indices) and len(set(indices))==len(indices), 'Invalid or duplicate design indexes')
    n.require(len(records)==len(briefs), 'Record omitted from summary or missing from directory')
    n.require(set(records)=={r['file'] for r in briefs}, 'Summary file inventory mismatch')
    complete = set(indices)==set(range(planned))
    if not allow_incomplete:
        n.require(complete and 'finished_utc' in summary, 'Incomplete study: require all planned records and completion marker')
    if 'finished_utc' in summary:
        n.require(complete, 'Completion marker attached to incomplete study')
        n.require(datetime.fromisoformat(summary['finished_utc'])>=datetime.fromisoformat(summary['started_utc']), 'Invalid completion time')
    for name, digest in summary['code_sha256'].items():
        n.require(name in ('netinfo.py','study_random.py'), 'Unexpected code binding')
        n.require(hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()==digest, 'Study implementation hash changed: '+name)
    n.require(set(summary['code_sha256'])=={'netinfo.py','study_random.py'}, 'Missing study code binding')
    designs = []
    if planned==44:
        for tag in ('dag_menu3_a','dag_menu3_b','dag_menu4','cyclic_menu3'):
            historic = json.loads((Path(__file__).resolve().parents[1]/'results'/(tag+'.json')).read_text())
            topology = 'cyclic_allowed' if historic['args']['topology']=='cyclic' else historic['args']['topology']
            designs.extend((r['n'],r['edges'],r['seed'],r['menu'],topology) for r in historic['records'])
        n.require(len(designs)==44, 'Historical design does not contain 44 inputs')
    keys = ('name','status','initial_width','edges','requested_edges','oracle_calls','unknown_calls','solver_only_sat_calls','wall_seconds')
    for brief in briefs:
        n.require(brief['file']==f"instance-{brief['index']:03d}.json", 'Noncanonical record filename')
        record = records[brief['file']]
        n.require(all(brief[key]==record.get(key) for key in keys), 'Summary metadata differs from retained record')
        if designs:
            n.require((record['n'],record['requested_edges'],record['seed'],record['menu'],record['generator']['topology'])==designs[brief['index']], 'Retained record differs from assigned historical design')
    return {'planned':planned,'retained':len(records),'complete':complete,'completion_marker':'finished_utc' in summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, action='append', default=[])
    parser.add_argument('--allow-incomplete', action='store_true', help='Interim diagnostics only; final replay must omit this flag')
    args = parser.parse_args()
    result = {'self_tests': self_tests(), 'retained_records': [], 'retained_negative_controls': [], 'coverage':[], 'optimized': sys.flags.optimize}
    sample = None
    for directory in args.results:
        files = sorted(directory.glob('instance-*.json'))
        n.require(bool(files), 'No retained instance records found')
        records = {file.name:json.loads(file.read_text()) for file in files}
        summary = json.loads((directory/'summary.json').read_text())
        result['coverage'].append(recheck_coverage(summary,records,args.allow_incomplete))
        bad_records = dict(records)
        bad_records.pop(next(iter(bad_records)))
        result['retained_negative_controls'].append(reject('omitted instance record',lambda:recheck_coverage(summary,bad_records,True)))
        bad_summary = copy.deepcopy(summary)
        bad_summary['records'][0]['oracle_calls'] += 1
        result['retained_negative_controls'].append(reject('summary query-count mismatch',lambda:recheck_coverage(bad_summary,records,True)))
        bad_summary = copy.deepcopy(summary)
        bad_summary.pop('finished_utc',None)
        result['retained_negative_controls'].append(reject('missing completion marker',lambda:recheck_coverage(bad_summary,records)))
        for file in files:
            record = records[file.name]
            counts = recheck_record(record)
            if sample is None and record['status']=='ok' and 'selection' in record:
                sample = record
            result['retained_records'].append({'file': file.name, **counts,
                                               'sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
    if sample is not None:
        mutations = {
            'incorrect actual edge count': lambda r:r.update(edges=r['edges']+1),
            'omitted query timing': lambda r:r.update(max_call_seconds=r['max_call_seconds']+1),
            'unsupported lower bracket': lambda r:r['widths']['()'].__setitem__(0,'999'),
            'zero width from bracket alone': lambda r:r.update(zero_width_status='zero_certified_by_solver_unsat'),
            'mislabelled half-width target': lambda r:r['selection'].update(epsilon='999'),
            'missing feasibility call': lambda r:r['selection'].update(oracle_calls=r['selection']['oracle_calls']-1),
            'corrupted nested selection history': lambda r:r['selection']['history'][0].update(epsilon='999'),
            'invented complementarity finding': lambda r:r.update(complementarity=not r['complementarity']),
            'invented accounting-fixed classification': lambda r:r['accounting_redundancy_screen'][0].update(classification='invented'),
        }
        for label, mutate in mutations.items():
            bad = copy.deepcopy(sample)
            mutate(bad)
            result['retained_negative_controls'].append(reject(label,lambda:recheck_record(bad)))
    result['status'] = 'PASS'
    result['python_version'] = sys.version.split()[0]
    result['z3_library_version'] = n.z3.get_version_string()
    result['code_sha256'] = {name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                             for name in ('verify_assurance.py','netinfo.py','study_random.py')}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
