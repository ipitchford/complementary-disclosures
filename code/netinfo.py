#!/usr/bin/env python3
"""Exact tools for disclosure design in Eisenberg-Noe networks.

Extends the earlier `disclosure.py` (kept alongside, with two helper fixes) by

* a general exact clearing routine and the loss-shock identity checks;
* the outside-debt-share layered family  layered(t, beta, b0, a);
* realised-width, expected-width and quantile-width formulas for that family;
* the bounded-error (noisy) disclosure closed form;
* exact width computation for arbitrary small instances by Z3 bisection;
* a random fixed-total instance generator for the computational study.

All inputs are rationals (Fraction/int/str). Floats are rejected on input.
Z3 outputs are solver evidence, not proof certificates; unknown/timeout are
never treated as unsat.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
import json
import hashlib
import random
import time
import uuid
from typing import Sequence

import z3


class NonRationalWitness(ValueError):
    """Solver SAT has no retained exact rational certificate."""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def instance_record(inst):
    return {'name': inst.name, 'r': list(map(str, inst.r)), 'a': list(map(str, inst.a)),
            'b': list(map(str, inst.b)), 'x': list(map(str, inst.x)),
            'bounds': [[i, j, str(lo), str(hi)] for (i, j), (lo, hi) in sorted(inst.bounds.items())],
            'queries': [{'name': q.name, 'terms': [[i, j, str(w)] for i, j, w in q.terms],
                         'cost': str(q.cost)} for q in inst.queries]}


def instance_from_record(record):
    result = Instance(record['name'], *[[rat(v) for v in record[k]] for k in ('r', 'a', 'b', 'x')],
                      {(i, j): (rat(lo), rat(hi)) for i, j, lo, hi in record['bounds']},
                      [Query(q['name'], [(i, j, rat(w)) for i, j, w in q['terms']], rat(q['cost'])) for q in record['queries']])
    result.validate()
    return result


# ----------------------------------------------------------------------------
# rational helpers
# ----------------------------------------------------------------------------

def rat(x) -> F:
    if isinstance(x, float):
        raise TypeError('Pass rationals as Fraction, int or string, not float.')
    return F(x)


def solve_linear(A, b):
    n = len(b)
    M = [[rat(x) for x in row] + [rat(y)] for row, y in zip(A, b)]
    for k in range(n):
        pivot = next((i for i in range(k, n) if M[i][k]), None)
        if pivot is None:
            raise ValueError('Singular linear system')
        M[k], M[pivot] = M[pivot], M[k]
        d = M[k][k]
        M[k] = [x / d for x in M[k]]
        for i in range(n):
            if i != k and M[i][k]:
                d = M[i][k]
                M[i] = [x - d * y for x, y in zip(M[i], M[k])]
    return [row[-1] for row in M]


# ----------------------------------------------------------------------------
# exact Eisenberg-Noe clearing (fictitious default algorithm)
# ----------------------------------------------------------------------------

def clearing(L, b, x):
    """Exact clearing payments. Every bank must have b_i > 0, x_i >= 0."""
    L = [[rat(v) for v in row] for row in L]
    b = [rat(v) for v in b]
    x = [rat(v) for v in x]
    n = len(b)
    if len(L) != n or len(x) != n or any(len(row) != n for row in L):
        raise ValueError('Dimensions disagree')
    if any(v <= 0 for v in b) or any(v < 0 for v in x):
        raise ValueError('Require positive outside debts and nonnegative external assets')
    if any(v < 0 for row in L for v in row) or any(L[i][i] for i in range(n)):
        raise ValueError('Invalid liability matrix')
    bar = [sum(L[i], F(0)) + b[i] for i in range(n)]
    P = [[L[j][i] / bar[j] for j in range(n)] for i in range(n)]
    p = bar[:]
    D: set[int] = set()
    for _ in range(n + 1):
        cash = [x[i] + sum((P[i][j] * p[j] for j in range(n)), F(0)) for i in range(n)]
        new = D | {i for i in range(n) if cash[i] < bar[i]}
        if new == D:
            if p != [min(bar[i], cash[i]) for i in range(n)]:
                raise AssertionError('Fixed-point check failed')
            return p
        D = new
        d = sorted(D)
        solvent = [j for j in range(n) if j not in D]
        A = [[F(i == j) - P[i][j] for j in d] for i in d]
        rhs = [x[i] + sum((P[i][j] * bar[j] for j in solvent), F(0)) for i in d]
        pp = solve_linear(A, rhs)
        p = bar[:]
        for i, v in zip(d, pp):
            p[i] = v
    raise AssertionError('Default-set algorithm failed to terminate')


def picard_clearing(L, b, x, iters=400):
    """Independent floating-point Picard iteration (sanity check only)."""
    n = len(b)
    Lf = [[float(v) for v in row] for row in L]
    bf = [float(v) for v in b]
    xf = [float(v) for v in x]
    bar = [sum(Lf[i]) + bf[i] for i in range(n)]
    p = bar[:]
    for _ in range(iters):
        p = [min(bar[i], xf[i] + sum(Lf[j][i] * p[j] / bar[j] for j in range(n))) for i in range(n)]
    return p


def outside_loss(L, b, p) -> F:
    return sum((rat(b[i]) * (1 - rat(p[i]) / (sum(map(rat, L[i]), F(0)) + rat(b[i]))) for i in range(len(b))), F(0))


def equity(L, b, x, p):
    bar = [sum(map(rat, row), F(0)) + rat(bi) for row, bi in zip(L, b)]
    return [rat(x[i]) + sum((rat(L[j][i]) * rat(p[j]) / bar[j] for j in range(len(b))), F(0)) - rat(p[i])
            for i in range(len(b))]


# ----------------------------------------------------------------------------
# outside-debt-share layered family
# ----------------------------------------------------------------------------

def layered(t: Sequence, beta=F(1), b0=F(1)):
    """2(m+1)-bank layered network with outside-debt share beta.

    Layer 0 (sources, banks 0,1): outside debt b0; interbank row total 1.
    Layers 1..m-1 (banks 2j, 2j+1): outside debt beta; row total 1; external
    assets beta (exactly solvent before the shock).
    Layer m (banks 2m, 2m+1): outside debt 1; no interbank liabilities;
    external assets (0, 1).
    Between layers j-1 and j the block is T(t_j) = [[t, 1-t], [1-t, t]].
    Post-shock external assets of bank 0 are 0; before the shock 1+b0.
    Returns (L, b, x_after, x_before).
    """
    t = [rat(v) for v in t]
    beta = rat(beta)
    b0 = rat(b0)
    m = len(t)
    if m < 1 or any(v < 0 or v > 1 for v in t) or beta <= 0 or b0 <= 0:
        raise ValueError('Invalid layered parameters')
    n = 2 * (m + 1)
    L = [[F(0)] * n for _ in range(n)]
    for k, v in enumerate(t):
        i, j = 2 * k, 2 * k + 2
        L[i][j] = L[i + 1][j + 1] = v
        L[i][j + 1] = L[i + 1][j] = 1 - v
    b = [b0, b0] + [beta] * (2 * (m - 1)) + [F(1), F(1)]
    x = [F(0), 1 + b0] + [beta] * (2 * (m - 1)) + [F(0), F(1)]
    before = x[:]
    before[0] = 1 + b0
    return L, b, x, before


def layered_loss_formula(t, beta=F(1), b0=F(1)) -> F:
    """Closed form: loss = shock - (1/2)(1+beta)^(1-m)(1 - prod(2t_j-1))."""
    t = [rat(v) for v in t]
    beta, b0 = rat(beta), rat(b0)
    m = len(t)
    prod = F(1)
    for v in t:
        prod *= 2 * v - 1
    return (1 + b0) - F(1, 2) * (1 + beta) ** (1 - m) * (1 - prod)


def layered_shock(b0=F(1)) -> F:
    return 1 + rat(b0)


def layered_width(m: int, selected: Sequence[int], observed=None, a=F(0), beta=F(1)) -> F:
    """Worst-case (observed=None) or realised residual width of the layered family.

    Switches are restricted to [a, 1-a]. Proper S: (1+beta)^(1-m) h^(m-|S|) *
    prod_{j in S}|2t_j-1| realised, with h=1-2a; worst case replaces each observed
    factor by h. Full S: 0. Input indices are validated and deduplicated.
    """
    S = sorted(set(int(i) for i in selected))
    if any(i < 0 or i >= m for i in S):
        raise ValueError('Report index out of range')
    if len(S) == m:
        return F(0)
    h = 1 - 2 * rat(a)
    if not (0 < h <= 1):
        raise ValueError('Require 0 <= a < 1/2')
    beta = rat(beta)
    if observed is None:
        product = h ** len(S)
    else:
        product = F(1)
        for i in S:
            product *= abs(2 * rat(observed[i]) - 1)
    return (1 + beta) ** (1 - m) * product * h ** (m - len(S))


def noisy_full_width(m: int, eta, beta=F(1)) -> F:
    """Minimax width after all m reports with absolute report error <= eta.

    Two networks are indistinguishable when |t_j - t'_j| <= 2 eta for all j, so
    |s_j - s'_j| <= 4 eta for s = 2t - 1. The maximal product gap is 1-(1-4eta)^m.
    """
    delta = 4 * rat(eta)
    if not (0 <= delta <= 1):
        raise ValueError('Require 0 <= eta <= 1/4')
    return F(1, 2) * (1 + rat(beta)) ** (1 - m) * (1 - (1 - delta) ** m)


# ----------------------------------------------------------------------------
# generic instances and Z3 pair encoding
# ----------------------------------------------------------------------------

@dataclass
class Query:
    name: str
    terms: list  # (i, j, weight)
    cost: F = F(1)

    def value(self, L) -> F:
        return sum((rat(w) * rat(L[i][j]) for i, j, w in self.terms), F(0))


@dataclass
class Instance:
    name: str
    r: list
    a: list
    b: list
    x: list
    bounds: dict  # (i,j) -> (lo, hi)
    queries: list = field(default_factory=list)

    def validate(self):
        n = len(self.r)
        if any(len(v) != n for v in (self.a, self.b, self.x)):
            raise ValueError('Dimensions disagree')
        if sum(self.r) != sum(self.a):
            raise ValueError('Network assets and liabilities do not balance')
        if any(v < 0 for v in self.r + self.a + self.x) or any(v <= 0 for v in self.b):
            raise ValueError('Invalid totals')
        for (i, j), (lo, hi) in self.bounds.items():
            if i == j or not (0 <= i < n and 0 <= j < n) or not (0 <= lo <= hi):
                raise ValueError('Invalid edge bounds')
        for q in self.queries:
            if q.cost < 0 or any((i, j) not in self.bounds for i, j, w in q.terms):
                raise ValueError('Invalid query')


def layered_instance(m=2, beta=F(1), b0=F(1), a=F(0), name=None) -> Instance:
    L, b, x, _ = layered([F(1, 2)] * m, beta, b0)
    n = len(b)
    r = [sum(row, F(0)) for row in L]
    aa = [sum((row[j] for row in L), F(0)) for j in range(n)]
    bounds = {}
    queries = []
    for k in range(m):
        for i in (2 * k, 2 * k + 1):
            for j in (2 * k + 2, 2 * k + 3):
                bounds[i, j] = (rat(a), 1 - rat(a))
        queries.append(Query(f'x{k + 1}', [(2 * k, 2 * k + 2, F(1))]))
    return Instance(name or f'layered_m{m}', r, aa, b, x, bounds, queries)


def z3rat(q: F):
    return z3.RealVal(f'{q.numerator}/{q.denominator}')


def build_pair(inst: Instance, selected, epsilon: F, relation='>', noise=None, different_report=None):
    """Z3 solver with two full networks A, B agreeing on selected reports
    (within 2*noise[q] if noise given) and loss_A - loss_B (relation) epsilon.
    Returns (solver, variables dict)."""
    inst.validate()
    require(all(type(k) is int and 0 <= k < len(inst.queries) for k in selected), 'Invalid selected report')
    require(noise is None or len(noise) == len(inst.queries) and all(rat(v) >= 0 for v in noise), 'Invalid reporting error')
    require(different_report is None or type(different_report) is int and 0 <= different_report < len(inst.queries), 'Invalid variation report')
    n = len(inst.r)
    s = z3.Solver()
    V = {}

    def Lvar(c, i, j):
        return V.get((c, 'L', i, j), z3.RealVal(0))

    for c in ('A', 'B'):
        for (i, j), (lo, hi) in sorted(inst.bounds.items()):
            v = z3.Real(f'{c}_L_{i}_{j}')
            V[(c, 'L', i, j)] = v
            s.add(v >= z3rat(rat(lo)), v <= z3rat(rat(hi)))
        for i in range(n):
            u = z3.Real(f'{c}_u_{i}')
            V[(c, 'u', i)] = u
        for i in range(n):
            row = z3.Sum([Lvar(c, i, j) for j in range(n) if (i, j) in inst.bounds] or [z3.RealVal(0)])
            col = z3.Sum([Lvar(c, j, i) for j in range(n) if (j, i) in inst.bounds] or [z3.RealVal(0)])
            s.add(row == z3rat(rat(inst.r[i])), col == z3rat(rat(inst.a[i])))
        for i in range(n):
            u = V[(c, 'u', i)]
            bar = rat(inst.r[i]) + rat(inst.b[i])
            avail = z3rat(rat(inst.x[i])) + z3.Sum([Lvar(c, j, i) * V[(c, 'u', j)] for j in range(n) if (j, i) in inst.bounds] or [z3.RealVal(0)])
            pay = z3rat(bar) * u
            s.add(u >= 0, u <= 1, pay <= avail, z3.Or(u == 1, pay == avail))
        loss = z3.Sum([z3rat(rat(inst.b[i])) * (1 - V[(c, 'u', i)]) for i in range(n)])
        V[(c, 'loss')] = loss
    for k, q in enumerate(inst.queries):
        qa = z3.Sum([z3rat(rat(w)) * Lvar('A', i, j) for i, j, w in q.terms])
        qb = z3.Sum([z3rat(rat(w)) * Lvar('B', i, j) for i, j, w in q.terms])
        V[('q', k)] = (qa, qb)
        if k == different_report:
            s.add(qa != qb)
        if k in selected:
            if noise is None or rat(noise[k]) == 0:
                s.add(qa == qb)
            else:
                tol = 2 * rat(noise[k])
                s.add(qa - qb <= z3rat(tol), qb - qa <= z3rat(tol))
    diff = V[('A', 'loss')] - V[('B', 'loss')]
    e = z3rat(rat(epsilon))
    if relation == '>':
        s.add(diff > e)
    elif relation == '>=':
        s.add(diff >= e)
    elif relation == '=':
        s.add(diff == e)
    else:
        raise ValueError('Invalid relation')
    return s, V


def model_fraction(m, v) -> F:
    val = m.eval(v, model_completion=True)
    if z3.is_rational_value(val):
        return F(val.numerator_as_long(), val.denominator_as_long())
    if z3.is_algebraic_value(val):
        raise NonRationalWitness('Non-rational (algebraic) model value: ' + str(val))
    return F(str(val))


def check_witness(inst: Instance, selected, epsilon, relation, m, V, noise=None, different_report=None):
    """Independent Fraction verification of a SAT witness."""
    n = len(inst.r)
    mats, recoveries = [], []
    for c in ('A', 'B'):
        L = [[F(0)] * n for _ in range(n)]
        for (i, j), (lo, hi) in inst.bounds.items():
            L[i][j] = model_fraction(m, V[(c, 'L', i, j)])
            if not (rat(lo) <= L[i][j] <= rat(hi)):
                raise AssertionError('Witness violates edge bounds')
        if [sum(row, F(0)) for row in L] != [rat(v) for v in inst.r]:
            raise AssertionError('Witness violates row totals')
        if [sum((L[i][j] for i in range(n)), F(0)) for j in range(n)] != [rat(v) for v in inst.a]:
            raise AssertionError('Witness violates column totals')
        mats.append(L)
        recoveries.append([model_fraction(m, V[(c, 'u', i)]) for i in range(n)])
    return check_rational_matrices(inst, selected, epsilon, relation, mats, noise, recoveries, different_report)


def check_rational_matrices(inst, selected, epsilon, relation, matrices, noise=None, recoveries=None, different_report=None):
    """Replay full retained matrices without Z3 models or floating point."""
    inst.validate()
    require(relation in ('>', '>=', '='), 'Invalid gap relation')
    require(len(matrices) == 2, 'Two witness matrices required')
    n = len(inst.r)
    mats = [[[rat(v) for v in row] for row in matrix] for matrix in matrices]
    losses, payments = [], []
    for index, L in enumerate(mats):
        require(len(L) == n and all(len(row) == n for row in L), 'Witness matrix dimensions disagree')
        for i in range(n):
            for j in range(n):
                lo, hi = inst.bounds.get((i, j), (F(0), F(0)))
                require(rat(lo) <= L[i][j] <= rat(hi), 'Witness violates edge bounds or forbidden edge')
        require([sum(row, F(0)) for row in L] == list(map(rat, inst.r)), 'Witness violates row totals')
        require([sum((row[j] for row in L), F(0)) for j in range(n)] == list(map(rat, inst.a)), 'Witness violates column totals')
        p = clearing(L, inst.b, inst.x)
        if recoveries is not None:
            require(len(recoveries) == 2 and len(recoveries[index]) == n, 'Recovery dimensions disagree')
            require([p[i] / (rat(inst.r[i]) + rat(inst.b[i])) for i in range(n)] == list(map(rat, recoveries[index])), 'Witness recovery disagrees with exact clearing')
        losses.append(outside_loss(L, inst.b, p))
        payments.append(p)
    for k in selected:
        qa, qb = inst.queries[k].value(mats[0]), inst.queries[k].value(mats[1])
        tol = 0 if noise is None else 2 * rat(noise[k])
        if abs(qa - qb) > tol:
            raise AssertionError('Witness violates report agreement')
    diff = losses[0] - losses[1]
    ok = {'>': diff > rat(epsilon), '>=': diff >= rat(epsilon), '=': diff == rat(epsilon)}[relation]
    if not ok:
        raise AssertionError('Witness does not satisfy the loss-gap relation')
    distinguishing = [k for k, q in enumerate(inst.queries) if q.value(mats[0]) != q.value(mats[1])]
    require(different_report is None or different_report in distinguishing, 'Witness does not vary requested report')
    return {'loss_A': str(losses[0]), 'loss_B': str(losses[1]), 'gap': str(diff),
            'distinguishing_queries': distinguishing, 'independent_fraction_check': 'passed',
            'rational_verified': True, 'evidence': 'rational_witness_verified',
            'witness_matrices': json_ready(mats), 'clearing_payments': json_ready(payments)}


def oracle(inst: Instance, selected, epsilon, relation='>', timeout_ms=60000, noise=None, outdir=None, tag=None, different_report=None):
    """Decide whether two feasible networks agree on `selected` with loss gap
    (relation) epsilon. Returns dict with status sat/unsat/unknown and timing."""
    selected = sorted(set(selected))
    require(timeout_ms > 0, 'Positive solver timeout required')
    started = time.perf_counter()
    s, V = build_pair(inst, selected, rat(epsilon), relation, noise, different_report)
    s.set('timeout', int(timeout_ms))
    t0 = time.perf_counter()
    res = s.check()
    dt = time.perf_counter() - t0
    query = s.to_smt2()
    instance = instance_record(inst)
    out = {'selected': list(selected), 'epsilon': str(rat(epsilon)), 'relation': relation,
           'status': str(res), 'solver_status': str(res), 'seconds': dt, 'timeout_ms': timeout_ms,
           'rational_verified': False, 'evidence': 'solver_unsat' if res == z3.unsat else 'unresolved',
           'noise': None if noise is None else list(map(str, noise)), 'different_report': different_report,
           'instance': instance, 'instance_sha256': hashlib.sha256(json.dumps(instance, sort_keys=True).encode()).hexdigest(),
           'query_sha256': hashlib.sha256(query.encode()).hexdigest(), 'query_id': uuid.uuid4().hex,
           'z3_version': z3.get_version_string()}
    if outdir and tag:
        Path(outdir).mkdir(parents=True, exist_ok=True)
        with Path(outdir, tag + '.smt2').open('x') as file:
            file.write(query)
    if res == z3.sat:
        try:
            out.update(check_witness(inst, selected, epsilon, relation, s.model(), V, noise, different_report))
        except NonRationalWitness as e:
            out['witness_check'] = 'not_verified: ' + str(e)
            out['evidence'] = 'solver_only_algebraic_sat'
            out['solver_model'] = s.model().sexpr()
    elif res == z3.unknown:
        out['reason'] = s.reason_unknown()
    out['wall_seconds'] = time.perf_counter() - started
    if outdir and tag:
        with Path(outdir, tag + '.txt').open('x') as file:
            file.write(json.dumps(out, indent=1))
    return out


def exact_width_bisection(inst: Instance, selected, upper: F, tol: F, timeout_ms=60000, noise=None, test_upper=True):
    """Bracket the minimax residual width R(S) to within tol by bisection.

    Returns (lo, hi, log): the width lies in [lo, hi]; lo is attained (sat with
    independently checked rational witness), hi is a solver upper bound
    (unsat for gap > hi). UNKNOWN or algebraic-only SAT stops without advancing
    the rational lower bound. Read bracket_status on the final log entry."""
    upper, tol = rat(upper), rat(tol)
    require(upper >= 0 and tol > 0, 'Require nonnegative upper and positive tolerance')
    log = []
    if test_upper:
        first = oracle(inst, selected, upper, '>', timeout_ms, noise)
        log.append(first)
        if first['status'] == 'unknown':
            return None, None, log
        if first['status'] == 'sat':
            first['bracket_status'] = 'invalid_upper_bound' if first.get('rational_verified') else 'unresolved_solver_only_sat'
            return (rat(first['gap']) if first.get('rational_verified') else F(0)), None, log
    # otherwise `upper` is a proven bound (e.g. the shock, by the loss-shock lemma)
    lo, hi = F(0), rat(upper)
    # attainment of 0 is trivial (identical networks). Is the width positive at all?
    while hi - lo > tol:
        mid = (lo + hi) / 2
        r = oracle(inst, selected, mid, '>', timeout_ms, noise)
        log.append(r)
        if r['status'] == 'unknown':
            return lo, hi, log
        if r['status'] == 'sat':
            if not r.get('rational_verified') or r.get('independent_fraction_check') != 'passed':
                r['bracket_status'] = 'unresolved_solver_only_sat'
                return lo, hi, log
            lo = rat(r['gap'])
            require(mid < lo <= hi, 'Verified gap contradicts bisection bounds')
        elif r['status'] == 'unsat':
            hi = mid
        else:
            raise ValueError('Unrecognized solver verdict')
    if log:
        log[-1]['bracket_status'] = 'tolerance_reached'
    return lo, hi, log


def subsets(d):
    return [tuple(s) for k in range(d + 1) for s in combinations(range(d), k)]


def optimal_threshold(inst: Instance, epsilon, budget=None, timeout_ms=60000, outdir=None):
    """Exact witness-cut / hitting-set minimum-cost disclosure (small menus)."""
    epsilon = rat(epsilon)
    if epsilon < 0:
        raise ValueError('Require a nonnegative tolerance')
    feas = oracle(inst, [], F(0), '>=', timeout_ms)
    if feas['status'] != 'sat' or not feas.get('rational_verified'):
        return {'status': 'inconsistent' if feas['status'] == 'unsat' else 'unknown',
                'reason': 'feasibility_unsat' if feas['status'] == 'unsat' else 'feasibility_unresolved_or_unverified',
                'epsilon': str(epsilon), 'feasibility': feas, 'cuts': [], 'history': []}
    cands = subsets(len(inst.queries))

    def cost(S):
        return sum((rat(inst.queries[q].cost) for q in S), F(0))
    cands.sort(key=lambda S: (cost(S), len(S), S))
    if budget is not None:
        cands = [S for S in cands if cost(S) <= rat(budget)]
    cuts, history = [], []
    for step in range(2 ** len(inst.queries) + 1):
        S = next((S for S in cands if all(set(S) & set(C) for C in cuts)), None)
        if S is None:
            return {'status': 'infeasible', 'epsilon': str(epsilon), 'cuts': cuts, 'history': history, 'feasibility': feas}
        res = oracle(inst, S, epsilon, '>', timeout_ms, outdir=outdir, tag=f'{inst.name}_sel_{step}')
        history.append(res)
        if res['status'] == 'unsat':
            return {'status': 'optimal', 'selected': list(S), 'cost': str(cost(S)), 'epsilon': str(epsilon),
                    'cuts': cuts, 'history': history, 'feasibility': feas}
        if res['status'] != 'sat':
            return {'status': 'unknown', 'epsilon': str(epsilon), 'cuts': cuts, 'history': history, 'feasibility': feas}
        C = res.get('distinguishing_queries')
        if C is None or not res.get('rational_verified'):
            return {'status': 'unknown', 'reason': 'unverified witness', 'cuts': cuts, 'history': history, 'feasibility': feas}
        if set(C) & set(S) or C in cuts:
            raise AssertionError('Inconsistent cut')
        cuts.append(C)
    raise AssertionError('Finite pattern bound exceeded')


# ----------------------------------------------------------------------------
# random fixed-total instances
# ----------------------------------------------------------------------------

def random_instance(n: int, edges: int, seed: int, menu: int, denom=4, name=None) -> Instance:
    """Random network with known row/column interbank totals.

    A base liability matrix with `edges` allowed edges and liabilities in
    {1/denom,...,1} is drawn; the allowed edges keep bounds [0, min(r_i,a_j)].
    Outside debts are 1; pre-shock external assets make every bank exactly
    solvent plus a random slack in {0,1/denom,...}; one bank is shocked to zero
    assets. The menu is `menu` random allowed edges reported individually.
    """
    rng = random.Random(seed)
    pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
    rng.shuffle(pairs)
    chosen = pairs[:edges]
    L = [[F(0)] * n for _ in range(n)]
    for i, j in chosen:
        L[i][j] = F(rng.randint(1, denom), denom)
    r = [sum(row, F(0)) for row in L]
    a = [sum((L[i][j] for i in range(n)), F(0)) for j in range(n)]
    b = [F(1)] * n
    slack = [F(rng.choice([0, 0, 1, 2]), denom) for _ in range(n)]
    before = [max(F(0), r[i] + b[i] - a[i]) + slack[i] for i in range(n)]  # exact solvency + slack
    shocked = rng.randrange(n)
    x = before[:]
    x[shocked] = F(0)
    bounds = {(i, j): (F(0), min(r[i], a[j])) for i, j in chosen}
    menu_edges = chosen[:]
    rng.shuffle(menu_edges)
    queries = [Query(f'L{i}{j}', [(i, j, F(1))]) for i, j in menu_edges[:menu]]
    inst = Instance(name or f'rand_n{n}_e{edges}_s{seed}', r, a, b, x, bounds, queries)
    inst.validate()
    return inst, {'shocked': shocked, 'shock': str(before[shocked]), 'before': [str(v) for v in before],
                  'requested_edges': edges, 'actual_edges': len(chosen), 'possible_edges': len(pairs),
                  'topology': 'cyclic_allowed', 'seed': seed, 'base_matrix': json_ready(L)}


def random_dag_instance(n: int, edges: int, seed: int, menu: int, denom=4, name=None):
    """Random feed-forward (acyclic) network with known row/column totals.

    Edges only run from lower to higher index. Liabilities in {1/denom,...,1};
    outside debts 1; pre-shock external assets give exact solvency plus a random
    slack; one bank in the upstream half is shocked to zero external assets.
    Allowed edges keep bounds [0, min(r_i, a_j)]. The menu reports `menu`
    random allowed edges individually.
    """
    rng = random.Random(seed)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    rng.shuffle(pairs)
    chosen = pairs[:edges]
    L = [[F(0)] * n for _ in range(n)]
    for i, j in chosen:
        L[i][j] = F(rng.randint(1, denom), denom)
    r = [sum(row, F(0)) for row in L]
    a = [sum((L[i][j] for i in range(n)), F(0)) for j in range(n)]
    b = [F(1)] * n
    slack = [F(rng.choice([0, 0, 1, 2]), denom) for _ in range(n)]
    before = [max(F(0), r[i] + b[i] - a[i]) + slack[i] for i in range(n)]
    shocked = rng.randrange(max(1, n // 2))
    x = before[:]
    x[shocked] = F(0)
    bounds = {(i, j): (F(0), min(r[i], a[j])) for i, j in chosen}
    menu_edges = chosen[:]
    rng.shuffle(menu_edges)
    queries = [Query(f'L{i}{j}', [(i, j, F(1))]) for i, j in menu_edges[:menu]]
    inst = Instance(name or f'dag_n{n}_e{edges}_s{seed}', r, a, b, x, bounds, queries)
    inst.validate()
    return inst, {'shocked': shocked, 'shock': str(before[shocked]), 'before': [str(v) for v in before],
                  'requested_edges': edges, 'actual_edges': len(chosen), 'possible_edges': len(pairs),
                  'topology': 'dag', 'seed': seed, 'base_matrix': json_ready(L)}


def json_ready(o):
    if isinstance(o, F):
        return str(o)
    if isinstance(o, dict):
        return {str(k): json_ready(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [json_ready(v) for v in o]
    return o
