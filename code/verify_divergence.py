#!/usr/bin/env python3
"""Exact-optimum divergence between the minimax and expected-width criteria
(Proposition on criteria divergence), with Z3 checks of the minimax widths on
the combined 14-bank instance. Writes under results/fresh_optional_verify_divergence."""
from fractions import Fraction as F
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from netinfo import *
OUT = Path(__file__).resolve().parent.parent / 'results' / 'fresh_optional_verify_divergence'
OUT.mkdir(parents=True, exist_ok=True)

def scaled_layered_instance(m, scale, name):
    inst = layered_instance(m, F(1), F(1), name=name)
    s = rat(scale)
    inst.r = [v * s for v in inst.r]
    inst.a = [v * s for v in inst.a]
    inst.b = [v * s for v in inst.b]
    inst.x = [v * s for v in inst.x]
    inst.bounds = {k: (lo * s, hi * s) for k, (lo, hi) in inst.bounds.items()}
    return inst

def combine(parts, name):
    r, a, b, x, bounds, queries = ([], [], [], [], {}, [])
    off = 0
    for P in parts:
        n = len(P.r)
        r += P.r
        a += P.a
        b += P.b
        x += P.x
        bounds |= {(i + off, j + off): v for (i, j), v in P.bounds.items()}
        queries += [Query(f'{P.name}:{q.name}', [(i + off, j + off, w) for i, j, w in q.terms], q.cost) for q in P.queries]
        off += n
    inst = Instance(name, r, a, b, x, bounds, queries)
    inst.validate()
    return inst

def main():
    d1, d2 = (F(7, 20), F(1, 10))
    core = layered_instance(2, F(1), F(1), name='core')
    z1 = scaled_layered_instance(1, d1, 'z1')
    z2 = scaled_layered_instance(1, d2, 'z2')
    inst = combine([core, z1, z2], 'three_modules')
    names = [q.name for q in inst.queries]

    def minimax(S):
        S = set(S)
        return (F(0) if {0, 1} <= S else F(1, 2)) + (F(0) if 2 in S else d1) + (F(0) if 3 in S else d2)

    def expected(S, k=F(1, 2)):
        S = set(S)
        core_w = F(0) if {0, 1} <= S else F(1, 2) * k ** len({0, 1} & S)
        return core_w + (F(0) if 2 in S else d1) + (F(0) if 3 in S else d2)
    pairs = [S for S in subsets(4) if len(S) == 2]
    table = [{'S': [names[i] for i in S], 'minimax': str(minimax(S)), 'expected_uniform': str(expected(S))} for S in pairs]
    opt_m = min(pairs, key=lambda S: (minimax(S), S))
    opt_e = min(pairs, key=lambda S: (expected(S), S))
    res = {'delta1': str(d1), 'delta2': str(d2), 'budget': 2, 'table': table, 'minimax_optimal': [names[i] for i in opt_m], 'minimax_optimal_width': str(minimax(opt_m)), 'expected_optimal': [names[i] for i in opt_e], 'expected_optimal_width': str(expected(opt_e)), 'expected_width_of_minimax_choice': str(expected(opt_m)), 'minimax_width_of_expected_choice': str(minimax(opt_e))}
    if not set(opt_m) != set(opt_e):
        raise AssertionError('Explicit verification failed')
    checks = []
    for S in [opt_m, opt_e, (2, 3)]:
        w = minimax(S)
        up = oracle(inst, S, w, '>', timeout_ms=600000)
        checks.append(up | {'type': 'upper', 'names': [names[i] for i in S], 'predicted': str(w)})
        if not up['status'] == 'unsat':
            raise AssertionError(up)
        lo = oracle(inst, S, w, '>=', timeout_ms=600000)
        checks.append(lo | {'type': 'attain', 'names': [names[i] for i in S], 'predicted': str(w)})
        if not (lo['status'] == 'sat' and lo.get('independent_fraction_check') == 'passed'):
            raise AssertionError(lo)
    res['z3_checks'] = checks
    res['z3_version'] = z3.get_version_string()
    (OUT / 'divergence.json').write_text(json.dumps(json_ready(res), indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != 'z3_checks'}, indent=1))
    for c in checks:
        print(c['names'], c['type'], c['status'], round(c['seconds'], 2), c.get('gap'))
if __name__ == '__main__':
    main()
