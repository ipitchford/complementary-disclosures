#!/usr/bin/env python3
"""Optional exact and solver checks for the outside-debt-share layered family.
Writes only under results/fresh_optional_verify_magnitude."""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json
import random
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent))
from netinfo import *
OUT = Path(__file__).resolve().parent.parent / 'results' / 'fresh_optional_verify_magnitude'
OUT.mkdir(parents=True, exist_ok=True)

def check_case(t, beta, b0):
    L, b, x, before = layered(t, beta, b0)
    p = clearing(L, b, x)
    pb = clearing(L, b, before)
    bar = [sum(row, F(0)) + bb for row, bb in zip(L, b)]
    if not pb == bar:
        raise AssertionError('pre-shock full payment fails')
    ell = outside_loss(L, b, p)
    e = equity(L, b, x, p)
    if not all((v >= 0 for v in e)):
        raise AssertionError('Explicit verification failed')
    if not ell == sum(b) - sum(x) + sum(e):
        raise AssertionError('conservation identity')
    shock = before[0] - x[0]
    if not shock == layered_shock(b0):
        raise AssertionError('Explicit verification failed')
    if not 0 <= ell <= shock:
        raise AssertionError('loss-shock bound')
    if not ell == layered_loss_formula(t, beta, b0):
        raise AssertionError(f'closed form fails at {t},{beta},{b0}')
    pf = picard_clearing(L, b, x)
    if not max((abs(float(pi) - pfi) for pi, pfi in zip(p, pf))) < 1e-09:
        raise AssertionError('Explicit verification failed')
    return ell

def main():
    rng = random.Random(20261013)
    betas = [F(1), F(1, 2), F(1, 4), F(1, 10), F(1, 100)]
    count = 0
    t0 = time.time()
    for m in range(1, 7):
        for beta in betas:
            for b0 in (F(1), beta):
                for t in product([F(0), F(1)], repeat=m):
                    check_case(t, beta, b0)
                    count += 1
                for _ in range(8):
                    t = [F(rng.randrange(101), 100) for _ in range(m)]
                    check_case(t, beta, b0)
                    count += 1
    width_checks = 0
    for m in range(1, 7):
        for beta in betas:
            for S in subsets(m):
                for aa in (F(0), F(1, 10)):
                    vals = [aa] * m
                    if len(S) < m:
                        k = next((i for i in range(m) if i not in S))
                        alt = vals[:]
                        alt[k] = 1 - aa
                        gap = abs(layered_loss_formula(vals, beta) - layered_loss_formula(alt, beta))
                    else:
                        gap = F(0)
                    if not gap == layered_width(m, S, a=aa, beta=beta):
                        raise AssertionError('Explicit verification failed')
                    width_checks += 1
    ratio_table = []
    for m in range(1, 11):
        for beta in betas:
            w = layered_width(m, [], beta=beta)
            ratio_table.append({'m': m, 'beta': str(beta), 'b0': str(beta), 'width': str(w), 'shock': str(1 + beta), 'ratio': str(w / (1 + beta)), 'ratio_float': float(w / (1 + beta))})
    summary = {'exact_cases': count, 'endpoint_width_checks': width_checks, 'exact_seconds': time.time() - t0, 'ratio_table': ratio_table}
    solver = []
    configs = [(2, F(1), F(1)), (2, F(1, 4), F(1, 4)), (2, F(1, 100), F(1, 100)), (3, F(1), F(1)), (3, F(1, 4), F(1, 4)), (3, F(1, 10), F(1, 10))]
    for m, beta, b0 in configs:
        inst = layered_instance(m, beta, b0)
        for S in subsets(m):
            w = layered_width(m, S, beta=beta)
            up = oracle(inst, S, w, '>', timeout_ms=120000)
            solver.append(up | {'m': m, 'beta': str(beta), 'b0': str(b0), 'type': 'upper'})
            if not up['status'] == 'unsat':
                raise AssertionError((m, beta, S, up))
            if w > 0:
                lo = oracle(inst, S, w, '>=', timeout_ms=120000)
                solver.append(lo | {'m': m, 'beta': str(beta), 'b0': str(b0), 'type': 'attain'})
                if not (lo['status'] == 'sat' and lo.get('independent_fraction_check') == 'passed'):
                    raise AssertionError((m, beta, S, lo))
    summary['solver_checks'] = solver
    summary['z3_version'] = z3.get_version_string()
    summary['solver_unsat'] = sum((1 for s in solver if s['status'] == 'unsat'))
    summary['solver_sat'] = sum((1 for s in solver if s['status'] == 'sat'))
    (OUT / 'magnitude.json').write_text(json.dumps(json_ready(summary), indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k not in ('solver_checks', 'ratio_table')}, indent=1))
    print('max solver seconds', max((s['seconds'] for s in solver)))
if __name__ == '__main__':
    main()
