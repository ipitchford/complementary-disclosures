#!/usr/bin/env python3
"""Reproduce exact arithmetic tests and full-network SMT checks."""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json
import platform
import random
import sys
from disclosure import *
ROOT = Path(__file__).resolve().parents[2] / 'results' / 'fresh_optional_legacy'
OUT = ROOT / 'solver_queries'

def verify_one(v, scale=F(1), capital=F(0)):
    L, b, x, before = chain(v, scale, capital)
    p = clearing(L, b, x)
    bar = [sum(row, F(0)) + bb for row, bb in zip(L, b)]
    dag = []
    for i in range(len(b)):
        cash = x[i] + sum((L[j][i] * dag[j] / bar[j] for j in range(i)), F(0))
        dag.append(min(bar[i], cash))
    if not p == dag:
        raise AssertionError('Explicit verification failed')
    pb = clearing(L, b, before)
    if not pb == bar:
        raise AssertionError('Explicit verification failed')
    ell = outside_loss(L, b, p)
    ee = equity(L, b, x, p)
    if not all((e >= 0 for e in ee)):
        raise AssertionError('Explicit verification failed')
    if not ell == sum(b) - sum(x) + sum(ee):
        raise AssertionError('Explicit verification failed')
    if not 0 <= ell <= before[0] - x[0]:
        raise AssertionError('Explicit verification failed')
    if capital == 0:
        if not ell == chain_formula(v, scale):
            raise AssertionError('Explicit verification failed')
    elif len(v) == 2:
        expected = scale * F(7, 4) - F(5, 2) * capital + scale * F(1, 4) * (2 * v[0] - 1) * (2 * v[1] - 1)
        if not ell == expected:
            raise AssertionError('Explicit verification failed')
    else:
        raise ValueError('Positive-capital formula tested only for m=2')
    return ell

def main():
    count = 0
    grid = [F(i, 8) for i in range(9)]
    for v in product(grid, repeat=2):
        verify_one(v)
        count += 1
    rng = random.Random(20261013)
    for m in range(1, 7):
        for v in product([F(0), F(1)], repeat=m):
            verify_one(v)
            count += 1
        for _ in range(20):
            v = [F(rng.randrange(101), 100) for _ in range(m)]
            verify_one(v)
            count += 1
    a = F(1, 10)
    capital = F(1, 100)
    restricted_grid = [a + (1 - 2 * a) * F(i, 8) for i in range(9)]
    for v in product(restricted_grid, repeat=2):
        verify_one(v, capital=capital)
        count += 1
        L, b, x, _ = chain(v, capital=capital)
        p = clearing(L, b, x)
        bar = [sum(row, F(0)) + bb for row, bb in zip(L, b)]
        if not {i for i in range(6) if p[i] < bar[i]} == {0, 2, 3, 4}:
            raise AssertionError('Explicit verification failed')
    width_checks = 0
    for m in range(1, 7):
        for S in subsets(m):
            for aa in (F(0), F(1, 10)):
                values = [aa] * m
                if len(S) < m:
                    k = next((i for i in range(m) if i not in S))
                    alternative = values[:]
                    alternative[k] = 1 - aa
                    gap = abs(chain_formula(values) - chain_formula(alternative))
                else:
                    gap = F(0)
                if not gap == chain_width(m, S, a=aa):
                    raise AssertionError('Explicit verification failed')
                width_checks += 1
    summary = {'python': sys.version, 'platform': platform.platform(), 'exact_clearing_cases': count, 'endpoint_width_checks': width_checks, 'fraction_tests': 'passed', 'solver_checks': []}
    z = Z3Library()
    summary['z3_version'] = z.version
    for inst, a0 in [(chain_instance(2), F(0)), (chain_instance(2, a=F(1, 10), capital=F(1, 100), name='positive_capital'), F(1, 10))]:
        for S in subsets(2):
            width = chain_width(2, S, a=a0)
            upper = oracle(z, inst, S, width, outdir=OUT, tag=f"{inst.name}_S{''.join(map(str, S)) or 'none'}_upper")
            if not upper['status'] == 'unsat':
                raise AssertionError('Explicit verification failed')
            summary['solver_checks'].append(upper | {'instance': inst.name, 'type': 'upper_bound'})
            if width > 0:
                lower = oracle(z, inst, S, width, relation='>=', outdir=OUT, tag=f"{inst.name}_S{''.join(map(str, S)) or 'none'}_attainment")
                if not lower['status'] == 'sat':
                    raise AssertionError('Explicit verification failed')
                summary['solver_checks'].append(lower | {'instance': inst.name, 'type': 'attainment'})
    aggregate = chain_instance(2, name='one_aggregate')
    aggregate.queries = [Query('x_plus_y', [(0, 2, F(1)), (2, 4, F(1))])]
    for relation, expected in [('>', 'unsat'), ('>=', 'sat')]:
        result = oracle(z, aggregate, [0], F(1, 4), relation=relation, outdir=OUT, tag='one_aggregate_' + ('upper' if relation == '>' else 'attainment'))
        if not result['status'] == expected:
            raise AssertionError('Explicit verification failed')
        summary['solver_checks'].append(result | {'instance': aggregate.name, 'type': relation})
    main_inst = chain_instance(2)
    decoy = chain_instance(1, scale=F(1, 100), name='small_decoy')
    comb = combine(main_inst, decoy, 'chain_plus_decoy')
    table = []
    for S in subsets(3):
        width = (F(0) if {0, 1} <= set(S) else F(1, 2)) + (F(0) if 2 in S else F(1, 100))
        upper = oracle(z, comb, S, width, outdir=OUT, tag=f"combined_S{''.join(map(str, S)) or 'none'}_upper")
        if not upper['status'] == 'unsat':
            raise AssertionError('Explicit verification failed')
        summary['solver_checks'].append(upper | {'instance': comb.name, 'type': 'upper_bound'})
        if width > 0:
            lower = oracle(z, comb, S, width, relation='>=', outdir=OUT, tag=f"combined_S{''.join(map(str, S)) or 'none'}_attainment")
            if not lower['status'] == 'sat':
                raise AssertionError('Explicit verification failed')
            summary['solver_checks'].append(lower | {'instance': comb.name, 'type': 'attainment'})
        table.append({'selected': [comb.queries[i].name for i in S], 'worst_width': str(width)})
    summary['greedy_example_widths'] = table
    summary['six_bank_optimum'] = optimal_threshold(z, main_inst, F(0), outdir=OUT)
    summary['combined_optimum'] = optimal_threshold(z, comb, F(1, 100), budget=F(2), outdir=OUT)
    if not summary['six_bank_optimum']['selected'] == [0, 1]:
        raise AssertionError('Explicit verification failed')
    if not summary['combined_optimum']['selected'] == [0, 1]:
        raise AssertionError('Explicit verification failed')
    summary['combined_impossibility'] = optimal_threshold(z, comb, F(9, 1000), budget=F(2), outdir=OUT)
    if not summary['combined_impossibility']['status'] == 'infeasible':
        raise AssertionError('Explicit verification failed')
    (ROOT / 'verification_results.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k not in ('solver_checks', 'six_bank_optimum', 'combined_optimum', 'combined_impossibility')}, indent=2))
    print('Full-network solver checks:', len(summary['solver_checks']))
    print('Optimal threshold and budget-impossibility checks: passed')
if __name__ == '__main__':
    main()
