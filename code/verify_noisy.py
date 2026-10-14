#!/usr/bin/env python3
"""Optional original bounded-error and loss-shock checks, with explicit checks.
Fresh outputs are isolated under results/fresh_optional_verify_noisy."""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json
import random
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from netinfo import *
OUT = Path(__file__).resolve().parent.parent / 'results' / 'fresh_optional_verify_noisy'
OUT.mkdir(parents=True, exist_ok=True)

def product_gap_search(m, delta, trials=200000, seed=0):
    """Random + vertex search for max |prod a - prod a'| with |a_j-a'_j|<=delta."""
    rng = np.random.default_rng(seed)
    A = rng.uniform(-1, 1, size=(trials, m))
    E = rng.uniform(-delta, delta, size=(trials, m))
    B = np.clip(A + E, -1, 1)
    best = float(np.max(np.abs(A.prod(axis=1) - B.prod(axis=1))))
    for signs in product([-1, 1], repeat=m):
        a = np.array(signs, dtype=float)
        for shifts in product([0, 1], repeat=m):
            ap = a - delta * a * np.array(shifts)
            best = max(best, abs(a.prod() - ap.prod()))
    return best

def main():
    res = {}
    lemma = []
    for m in (1, 2, 3, 4, 5):
        for delta in (0.04, 0.1, 0.3, 0.6, 0.95):
            found = product_gap_search(m, delta)
            pred = 1 - (1 - delta) ** m
            lemma.append({'m': m, 'delta': delta, 'search_max': found, 'predicted': pred})
            if not (found <= pred + 1e-09 and found >= pred - 1e-09):
                raise AssertionError(lemma[-1])
    res['product_gap_lemma'] = lemma
    solver = []
    configs = [(2, F(1), F(1, 100)), (2, F(1, 4), F(1, 100)), (2, F(1), F(1, 20))]
    for m, beta, eta in configs:
        inst = layered_instance(m, beta, beta)
        noise = [eta] * m
        full = tuple(range(m))
        w = noisy_full_width(m, eta, beta)
        up = oracle(inst, full, w, '>', timeout_ms=300000, noise=noise)
        solver.append(up | {'m': m, 'beta': str(beta), 'eta': str(eta), 'type': 'upper', 'predicted_width': str(w)})
        if not up['status'] == 'unsat':
            raise AssertionError(up)
        lo = oracle(inst, full, w, '>=', timeout_ms=300000, noise=noise)
        solver.append(lo | {'m': m, 'beta': str(beta), 'eta': str(eta), 'type': 'attain', 'predicted_width': str(w)})
        if not (lo['status'] == 'sat' and lo.get('independent_fraction_check') == 'passed'):
            raise AssertionError(lo)
        if m == 2:
            for S in [(0,), (1,)]:
                w0 = layered_width(m, S, beta=beta)
                up = oracle(inst, S, w0, '>', timeout_ms=300000, noise=noise)
                solver.append(up | {'m': m, 'beta': str(beta), 'eta': str(eta), 'type': 'upper_proper'})
                if not up['status'] == 'unsat':
                    raise AssertionError('Explicit verification failed')
                lo = oracle(inst, S, w0, '>=', timeout_ms=300000, noise=noise)
                solver.append(lo | {'m': m, 'beta': str(beta), 'eta': str(eta), 'type': 'attain_proper'})
                if not (lo['status'] == 'sat' and lo.get('independent_fraction_check') == 'passed'):
                    raise AssertionError('Explicit verification failed')
    res['noisy_solver_checks'] = solver
    vertex = []
    for m in (2, 3, 4, 5):
        for beta in (F(1), F(1, 4)):
            for eta in (F(1, 100), F(1, 20)):
                e2 = 2 * eta
                hexv = [(F(0), F(0)), (F(1), F(1)), (F(0), e2), (e2, F(0)), (F(1), 1 - e2), (1 - e2, F(1))]
                best = F(0)
                for combo in product(hexv, repeat=m):
                    t = [c[0] for c in combo]
                    tp = [c[1] for c in combo]
                    L, b, x, _ = layered(t, beta, beta)
                    Lp, _, _, _ = layered(tp, beta, beta)
                    g = abs(outside_loss(L, b, clearing(L, b, x)) - outside_loss(Lp, b, clearing(Lp, b, x)))
                    best = max(best, g)
                pred = noisy_full_width(m, eta, beta)
                vertex.append({'m': m, 'beta': str(beta), 'eta': str(eta), 'vertex_max': str(best), 'predicted': str(pred)})
                if not best == pred:
                    raise AssertionError(vertex[-1])
    res['noisy_vertex_enumeration'] = vertex
    res['reviewer_case_width'] = str(noisy_full_width(2, F(1, 100), F(1)))
    if not noisy_full_width(2, F(1, 100), F(1)) == F(49, 2500):
        raise AssertionError('Explicit verification failed')
    table = []
    for m in (1, 2, 3, 4, 6, 8):
        for eta in (F(1, 1000), F(1, 100), F(1, 20)):
            rel = (1 - (1 - 4 * eta) ** m) / 2
            table.append({'m': m, 'eta': str(eta), 'relative_residual': str(rel), 'relative_float': float(rel), 'small_eta_approx_2m_eta': float(2 * m * eta)})
    res['relative_residual_table'] = table
    rng = random.Random(3)
    cases = 0
    for _ in range(400):
        n = rng.randint(2, 6)
        L = [[F(0)] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j and rng.random() < 0.6:
                    L[i][j] = F(rng.randint(0, 8), 4)
        b = [F(rng.randint(1, 8), 4) for _ in range(n)]
        before = [F(rng.randint(0, 16), 4) for _ in range(n)]
        pb = clearing(L, b, before)
        ell_before = outside_loss(L, b, pb)
        shock = [F(rng.randint(0, 8), 4) for _ in range(n)]
        after = [max(F(0), v - s) for v, s in zip(before, shock)]
        total_shock = sum((v - w for v, w in zip(before, after)))
        pa = clearing(L, b, after)
        ell_after = outside_loss(L, b, pa)
        if not all((q <= p for p, q in zip(pb, pa))):
            raise AssertionError('monotonicity')
        if not ell_before <= ell_after <= ell_before + total_shock:
            raise AssertionError('loss-shock bound')
        pf = picard_clearing(L, b, after)
        if not max((abs(float(p) - q) for p, q in zip(pa, pf))) < 1e-09:
            raise AssertionError('Explicit verification failed')
        cases += 1
    res['loss_shock_random_cases'] = cases
    res['z3_version'] = z3.get_version_string()
    (OUT / 'noisy.json').write_text(json.dumps(json_ready(res), indent=1))
    print(json.dumps({k: v for k, v in res.items() if k not in ('product_gap_lemma', 'noisy_solver_checks')}, indent=1))
    for s in solver:
        print(s['m'], s['beta'], s['eta'], s['type'], s['status'], round(s['seconds'], 2), s.get('gap'))
if __name__ == '__main__':
    main()
