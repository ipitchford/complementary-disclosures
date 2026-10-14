#!/usr/bin/env python3
"""Optional original expected-width and quantile numerical checks.
Fresh outputs are isolated; corrected zero-prior cases are in verify_extensions.py."""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json
import math
import random
import sys
import numpy as np
from scipy import stats, integrate
sys.path.insert(0, str(Path(__file__).resolve().parent))
from netinfo import *
OUT = Path(__file__).resolve().parent.parent / 'results' / 'fresh_optional_verify_bayes'
OUT.mkdir(parents=True, exist_ok=True)

def realised_width_exact(m, S, observed, beta, b0=F(1)):
    """Sharp width of the identified set after observing t_S, computed from exact
    clearing over all vertices of the free coordinates (loss is multilinear)."""
    free = [j for j in range(m) if j not in S]
    vals = []
    for corner in product([F(0), F(1)], repeat=len(free)):
        t = list(observed)
        for j, c in zip(free, corner):
            t[j] = c
        L, b, x, _ = layered(t, beta, b0)
        vals.append(outside_loss(L, b, clearing(L, b, x)))
    return max(vals) - min(vals)

def main():
    rng = random.Random(7)
    res = {}
    checks = 0
    for m in (2, 3, 4):
        for beta in (F(1), F(1, 4)):
            for S in subsets(m):
                for _ in range(6):
                    obs = [F(rng.randrange(0, 101), 100) for _ in range(m)]
                    w = realised_width_exact(m, S, obs, beta)
                    if not w == layered_width(m, S, observed=obs, beta=beta):
                        raise AssertionError((m, S, obs))
                    checks += 1
    res['realised_width_checks'] = checks
    priors = {'uniform': (lambda n: np.random.default_rng(1).uniform(size=n), 0.5), 'beta22': (lambda n: np.random.default_rng(2).beta(2, 2, size=n), None), 'beta13': (lambda n: np.random.default_rng(3).beta(1, 3, size=n), None), 'beta_half_half': (lambda n: np.random.default_rng(4).beta(0.5, 0.5, size=n), None)}
    kappa = {}
    for name, (sampler, exact) in priors.items():
        if name == 'uniform':
            k = 0.5
        else:
            a, bparam = {'beta22': (2, 2), 'beta13': (1, 3), 'beta_half_half': (0.5, 0.5)}[name]
            k, _ = integrate.quad(lambda t: abs(2 * t - 1) * stats.beta.pdf(t, a, bparam), 0, 1, limit=200)
        kappa[name] = k
    res['kappa'] = kappa
    N = 400000
    mc = []
    m, beta = (3, 0.25)
    for name, (sampler, _) in priors.items():
        T = sampler(N * m).reshape(N, m)
        for S in subsets(m):
            if len(S) == m:
                continue
            w = (1 + beta) ** (1 - m) * np.prod(np.abs(2 * T[:, list(S)] - 1), axis=1) if S else np.full(N, (1 + beta) ** (1 - m))
            pred = (1 + beta) ** (1 - m) * kappa[name] ** len(S)
            mc.append({'prior': name, 'S': list(S), 'mc_mean': float(w.mean()), 'mc_se': float(w.std() / math.sqrt(N)), 'predicted': float(pred)})
            if not abs(w.mean() - pred) < 5 * w.std() / math.sqrt(N) + 1e-12:
                raise AssertionError(mc[-1])
    res['expected_width_mc'] = mc
    m = 4
    for name in priors:
        k = kappa[name]
        W = {S: (1 + 0.25) ** (1 - m) * (k ** len(S) if len(S) < m else 0.0) for S in subsets(m)}
        G = {S: W[()] - W[S] for S in W}
        viol = 0
        strict = 0
        for S in subsets(m):
            for j in range(m):
                if j in S:
                    continue
                for T in subsets(m):
                    if set(S) <= set(T) and j not in T and (S != T):
                        mS = G[tuple(sorted(S + (j,)))] - G[S]
                        mT = G[tuple(sorted(T + (j,)))] - G[T]
                        if mT > mS + 1e-12:
                            viol += 1
                        elif mT < mS - 1e-12:
                            strict += 1
        res[f'submodularity_{name}'] = {'kappa': k, 'violations': viol, 'strict_decreases': strict, 'predicted_submodular': bool(2 * k <= 1 + 1e-12)}
        if not (viol == 0) == (2 * k <= 1 + 1e-12):
            raise AssertionError((name, k, viol))
    Rm = {S: float(layered_width(m, S, beta=F(1, 4))) for S in subsets(m)}
    res['minimax_widths_m4'] = {str(S): v for S, v in Rm.items()}
    if not (all((Rm[S] == Rm[()] for S in subsets(m) if len(S) < m)) and Rm[tuple(range(m))] == 0):
        raise AssertionError('Explicit verification failed')
    qt = []
    rng2 = np.random.default_rng(11)
    for n in range(1, 7):
        U = rng2.uniform(size=(1000000, n)).prod(axis=1)
        for alpha in (0.5, 0.25, 0.1, 0.05, 0.01):
            pred = math.exp(-stats.gamma.ppf(alpha, n))
            emp = float(np.quantile(U, 1 - alpha))
            qt.append({'n': n, 'alpha': alpha, 'predicted': pred, 'empirical': emp})
            if not abs(emp - pred) < 0.01:
                raise AssertionError(qt[-1])
    res['quantile_widths'] = qt
    delta = 0.01

    def minimax(S):
        return (0.0 if {0, 1} <= set(S) else 0.5) + (0.0 if 2 in S else delta)

    def expected(S, k=0.5):
        core = 0.0 if {0, 1} <= set(S) else 0.5 * k ** len({0, 1} & set(S))
        return core + (0.0 if 2 in S else delta)

    def greedy(f, budget=2):
        S = []
        for _ in range(budget):
            best = min((j for j in range(3) if j not in S), key=lambda j: (f(S + [j]), j))
            S.append(best)
        return (S, f(S))
    gm, wm = greedy(minimax)
    ge, we = greedy(expected)
    opt_m = min(((S, minimax(list(S))) for S in subsets(3) if len(S) <= 2), key=lambda p: p[1])
    opt_e = min(((S, expected(list(S))) for S in subsets(3) if len(S) <= 2), key=lambda p: p[1])
    res['greedy_reversal'] = {'minimax_greedy': gm, 'minimax_greedy_width': wm, 'minimax_opt': list(opt_m[0]), 'minimax_opt_width': opt_m[1], 'expected_greedy': ge, 'expected_greedy_width': we, 'expected_opt': list(opt_e[0]), 'expected_opt_width': opt_e[1], 'expected_table': {str(S): expected(list(S)) for S in subsets(3)}}
    (OUT / 'bayes.json').write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k not in ('expected_width_mc', 'quantile_widths')}, indent=1))
    print('quantile sample:', [q for q in qt if q['n'] in (1, 3, 6) and q['alpha'] in (0.05,)])
if __name__ == '__main__':
    main()
