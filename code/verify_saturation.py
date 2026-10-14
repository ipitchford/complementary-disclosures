#!/usr/bin/env python3
"""Proposition (saturation family): order k-1 all-or-nothing complementarity from a
single defaulting layer with all row and column totals fixed.
Writes only under results/fresh_optional_verify_saturation."""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json
import random
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from netinfo import *
OUT = Path(__file__).resolve().parent.parent / 'results' / 'fresh_optional_verify_saturation'
OUT.mkdir(parents=True, exist_ok=True)

def saturation_instance(k, bs=F(1), slack=F(1, 2), name=None):
    """k sources (0..k-1; source 0 shocked) owe a doubly stochastic k x k block to k sinks (k..2k-1).
    Sources: outside debt bs, external assets 1+bs (source 0: 0 after shock).
    Sinks: outside debt 1, external assets `slack`, no interbank liabilities."""
    n = 2 * k
    r = [F(1)] * k + [F(0)] * k
    a = [F(0)] * k + [F(1)] * k
    b = [bs] * k + [F(1)] * k
    x = [F(0)] + [1 + bs] * (k - 1) + [slack] * k
    bounds = {(i, k + j): (F(0), F(1)) for i in range(k) for j in range(k)}
    queries = [Query(f't{j + 1}', [(0, k + j, F(1))]) for j in range(k)]
    inst = Instance(name or f'saturation_k{k}', r, a, b, x, bounds, queries)
    inst.validate()
    return inst

def loss_formula(t, bs=F(1), slack=F(1, 2)):
    return bs + sum((max(F(0), v - slack) for v in t))

def main():
    rng = random.Random(5)
    res = {'exact_cases': 0}
    for k in (2, 3, 4, 5):
        for _ in range(60):
            t = [F(rng.randrange(0, 9), 8) for _ in range(k)]
            tot = sum(t)
            if tot == 0:
                continue
            t = [v / tot for v in t]
            n = 2 * k
            L = [[F(0)] * n for _ in range(n)]
            for j in range(k):
                L[0][k + j] = t[j]
            for i in range(1, k):
                for j in range(k):
                    L[i][k + j] = (1 - t[j]) / (k - 1)
            inst = saturation_instance(k)
            p = clearing(L, inst.b, inst.x)
            ell = outside_loss(L, inst.b, p)
            if not ell == loss_formula(t):
                raise AssertionError((k, t, ell))
            xb = inst.x[:]
            xb[0] = 1 + F(1)
            pb = clearing(L, inst.b, xb)
            if not pb == [sum(row, F(0)) + bi for row, bi in zip(L, inst.b)]:
                raise AssertionError('Explicit verification failed')
            res['exact_cases'] += 1
    checks = []
    for k in (3, 4):
        inst = saturation_instance(k)
        for S in subsets(k):
            w = F(1, 2) if len(S) <= k - 2 else F(0)
            up = oracle(inst, S, w, '>', timeout_ms=300000)
            checks.append(up | {'k': k, 'type': 'upper', 'predicted': str(w)})
            if not up['status'] == 'unsat':
                raise AssertionError((k, S, up))
            if w > 0:
                lo = oracle(inst, S, w, '>=', timeout_ms=300000)
                checks.append(lo | {'k': k, 'type': 'attain', 'predicted': str(w)})
                if not (lo['status'] == 'sat' and lo.get('independent_fraction_check') == 'passed'):
                    raise AssertionError((k, S, lo))
    res['z3_checks'] = checks
    res['z3_version'] = z3.get_version_string()
    res['max_seconds'] = max((c['seconds'] for c in checks))
    (OUT / 'saturation.json').write_text(json.dumps(json_ready(res), indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != 'z3_checks'}, indent=1))
    print('checks', len(checks), 'unsat', sum((c['status'] == 'unsat' for c in checks)), 'sat', sum((c['status'] == 'sat' for c in checks)))
if __name__ == '__main__':
    main()
