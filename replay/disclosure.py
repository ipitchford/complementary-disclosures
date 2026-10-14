#!/usr/bin/env python3
"""Exact small-network disclosure design. Python stdlib, optional libz3.

L[i][j] is the nominal liability of i to j. Every bank has positive
outside debt b[i]; outside creditors rank pari passu with network creditors.
Inputs and independent checks use Fraction, never binary floating point.
The SMT backend is an optional exact-real solver check, not a proof-assistant
certificate. Unknown and timeout results are never interpreted as unsat.
"""
from __future__ import annotations
import ctypes
import ctypes.util
from dataclasses import dataclass
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
import json
import re
from typing import Iterable, Sequence


def rat(x) -> F:
    if isinstance(x, float):
        raise TypeError('Pass rational numbers as Fraction, int or string, not float.')
    return F(x)


def solve_linear(A: Sequence[Sequence[F]], b: Sequence[F]) -> list[F]:
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
                M[i] = [x - d*y for x, y in zip(M[i], M[k])]
    return [row[-1] for row in M]


def clearing(L: Sequence[Sequence[F]], b: Sequence[F], x: Sequence[F]) -> list[F]:
    """Exact fictitious-default clearing; at most n default-set enlargements."""
    L = [[rat(v) for v in row] for row in L]
    b = [rat(v) for v in b]; x = [rat(v) for v in x]
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
        cash = [x[i] + sum((P[i][j]*p[j] for j in range(n)), F(0)) for i in range(n)]
        new = D | {i for i in range(n) if cash[i] < bar[i]}
        if new == D:
            assert p == [min(bar[i], cash[i]) for i in range(n)]
            return p
        D = new
        d = sorted(D)
        solvent = [j for j in range(n) if j not in D]
        A = [[F(i == j) - P[i][j] for j in d] for i in d]
        rhs = [x[i] + sum((P[i][j]*bar[j] for j in solvent), F(0)) for i in d]
        pp = solve_linear(A, rhs)
        p = bar[:]
        for i, v in zip(d, pp):
            p[i] = v
    raise AssertionError('Default-set algorithm failed to terminate')


def outside_loss(L, b, p) -> F:
    return sum((b[i]*(1 - p[i]/(sum(L[i], F(0)) + b[i])) for i in range(len(b))), F(0))


def equity(L, b, x, p) -> list[F]:
    bar = [sum(row, F(0)) + bi for row, bi in zip(L, b)]
    return [x[i] + sum((L[j][i]*p[j]/bar[j] for j in range(len(b))), F(0)) - p[i]
            for i in range(len(b))]


def chain(values: Sequence[F], scale=F(1), capital=F(0)):
    """2(m+1)-bank layered family. capital > 0 is tested for m=2 only.

    Sources: post-shock assets (0, 2*scale + capital).
    Intermediate layers: assets scale+capital at each bank.
    Final layer: assets (capital, scale+capital).
    Before shock, source 0 has assets 2*scale+capital.
    Every bank owes scale to society.
    """
    t = list(map(rat, values)); scale = rat(scale); capital = rat(capital)
    if not t or any(v < 0 or v > 1 for v in t) or scale <= 0 or capital < 0:
        raise ValueError('Invalid chain parameters')
    m = len(t); n = 2*(m + 1)
    L = [[F(0) for _ in range(n)] for _ in range(n)]
    for k, v in enumerate(t):
        i, j = 2*k, 2*k+2
        L[i][j] = L[i+1][j+1] = scale*v
        L[i][j+1] = L[i+1][j] = scale*(1-v)
    b = [scale]*n
    x = [F(0), 2*scale+capital] + [scale+capital]*(2*(m-1)) + [capital, scale+capital]
    before = x[:]; before[0] = 2*scale+capital
    return L, b, x, before


def chain_formula(values, scale=F(1)) -> F:
    m = len(values); product = F(1)
    for v in values:
        product *= 2*v - 1
    return rat(scale)*(2 - F(1, 2**m) + product/F(2**m))


def chain_width(m: int, selected: Sequence[int], observed=None, a=F(0), scale=F(1)) -> F:
    """Analytically proved worst-case width, or realised-report width."""
    if len(set(selected)) == m:
        return F(0)
    h = 1-2*rat(a)
    if not (0 < h <= 1):
        raise ValueError('Require 0 <= a < 1/2')
    if observed is None:
        product = h**len(selected)
    else:
        product = F(1)
        for i in selected:
            product *= abs(2*observed[i]-1)
    return rat(scale)*F(1, 2**(m-1))*product*h**(m-len(set(selected)))


@dataclass
class Query:
    name: str
    terms: list[tuple[int, int, F]]
    cost: F = F(1)
    def value(self, L) -> F:
        return sum((w*L[i][j] for i,j,w in self.terms), F(0))


@dataclass
class Instance:
    name: str
    r: list[F]
    a: list[F]
    b: list[F]
    x: list[F]
    bounds: dict[tuple[int,int], tuple[F,F]]
    queries: list[Query]
    def validate(self):
        n = len(self.r)
        if any(len(v) != n for v in (self.a,self.b,self.x)):
            raise ValueError('Dimensions disagree')
        if sum(self.r) != sum(self.a):
            raise ValueError('Network assets and liabilities do not balance')
        if any(v < 0 for v in self.r+self.a+self.x) or any(v <= 0 for v in self.b):
            raise ValueError('Invalid totals')
        for (i,j),(lo,hi) in self.bounds.items():
            if i == j or not (0 <= i < n and 0 <= j < n) or not (0 <= lo <= hi):
                raise ValueError('Invalid edge bounds')
        for q in self.queries:
            if q.cost < 0 or any((i,j) not in self.bounds for i,j,w in q.terms):
                raise ValueError('Invalid query')


def chain_instance(m=2, a=F(0), scale=F(1), capital=F(0), name=None) -> Instance:
    L,b,x,_ = chain([F(1,2)]*m, scale, capital)
    r = [sum(row,F(0)) for row in L]
    aa = [sum((row[j] for row in L),F(0)) for j in range(len(b))]
    bounds = {}
    queries = []
    for k in range(m):
        for i in (2*k,2*k+1):
            for j in (2*k+2,2*k+3):
                bounds[i,j] = (scale*a, scale*(1-a))
        queries.append(Query(f'x{k+1}',[(2*k,2*k+2,F(1))]))
    return Instance(name or f'chain_{m}',r,aa,b,x,bounds,queries)


def combine(A: Instance, B: Instance, name='combined') -> Instance:
    n=len(A.r)
    bounds=A.bounds | {(i+n,j+n):v for (i,j),v in B.bounds.items()}
    qq=A.queries+[Query('decoy_'+q.name,[(i+n,j+n,w) for i,j,w in q.terms],q.cost) for q in B.queries]
    return Instance(name,A.r+B.r,A.a+B.a,A.b+B.b,A.x+B.x,bounds,qq)


def subsets(m):
    return [tuple(s) for k in range(m+1) for s in combinations(range(m),k)]


def smt_rat(x) -> str:
    q=rat(x)
    if q < 0: return f'(- {smt_rat(-q)})'
    if q.denominator==1: return str(q.numerator)
    return f'(/ {q.numerator} {q.denominator})'


def smt_sum(xs: Iterable[str]) -> str:
    xs=list(xs)
    return '0' if not xs else xs[0] if len(xs)==1 else '(+ '+' '.join(xs)+')'


def smt_pair(inst: Instance, selected: Sequence[int], epsilon: F,
             relation='>', timeout_ms=15000) -> tuple[str,list[str]]:
    """Two full unknown networks, each with exact row/column constraints.

    Clearing is encoded by 0<=u<=1, bar*u<=available, and
    (u=1 or bar*u=available), i.e. exact proportional clearing.
    All variable products are degree two; no linearisation is used.
    """
    inst.validate(); n=len(inst.r)
    if relation not in ('>','>=','='):
        raise ValueError('Invalid relation')
    lines=['(set-logic QF_NRA)',f'(set-option :timeout {int(timeout_ms)})','(set-option :produce-models true)']
    names=[]
    def declare(v,typ='Real'):
        lines.append(f'(declare-const {v} {typ})'); names.append(v)
    def expr(c,i,j): return f'{c}_L_{i}_{j}' if (i,j) in inst.bounds else '0'
    for c in ('A','B'):
        for (i,j),(lo,hi) in sorted(inst.bounds.items()):
            v=expr(c,i,j); declare(v)
            lines.append(f'(assert (and (<= {smt_rat(lo)} {v}) (<= {v} {smt_rat(hi)})))')
        for i in range(n):
            declare(f'{c}_u_{i}')
            row=smt_sum(expr(c,i,j) for j in range(n) if (i,j) in inst.bounds)
            col=smt_sum(expr(c,j,i) for j in range(n) if (j,i) in inst.bounds)
            lines += [f'(assert (= {row} {smt_rat(inst.r[i])}))',f'(assert (= {col} {smt_rat(inst.a[i])}))']
        for i in range(n):
            u=f'{c}_u_{i}'; bar=inst.r[i]+inst.b[i]
            available=smt_sum([smt_rat(inst.x[i])]+[f'(* {expr(c,j,i)} {c}_u_{j})' for j in range(n) if (j,i) in inst.bounds])
            pay=f'(* {smt_rat(bar)} {u})'
            lines += [f'(assert (and (<= 0 {u}) (<= {u} 1)))',f'(assert (<= {pay} {available}))',
                      f'(assert (or (= {u} 1) (= {pay} {available})))']
        loss=smt_sum(f'(* {smt_rat(inst.b[i])} (- 1 {c}_u_{i}))' for i in range(n))
        lines.append(f'(define-fun {c}_loss () Real {loss})')
        names.append(f'{c}_loss')
    for k,q in enumerate(inst.queries):
        def qexpr(c): return smt_sum(f'(* {smt_rat(w)} {expr(c,i,j)})' for i,j,w in q.terms)
        declare(f'different_{k}','Bool')
        lines.append(f'(assert (= different_{k} (not (= {qexpr("A")} {qexpr("B")}))))')
        if k in selected: lines.append(f'(assert (not different_{k}))')
    lines.append(f'(assert ({relation} (- A_loss B_loss) {smt_rat(epsilon)}))')
    return '\n'.join(lines)+'\n', names


class Z3Library:
    """Use a system Z3 shared library through its stable C API.
    Alternatively, saved .smt2 files can be passed to the z3 command line.
    """
    def __init__(self):
        name=ctypes.util.find_library('z3')
        if not name:
            try:
                import z3
                candidates=list(Path(z3.__file__).parent.rglob('*z3*.so'))+list(Path(z3.__file__).parent.rglob('*z3*.dylib'))
                name=str(candidates[0]) if candidates else None
            except ImportError:
                pass
        if not name: raise RuntimeError('Install Z3 / z3-solver to run solver checks; rational tests need no solver.')
        self.lib=ctypes.CDLL(name)
        z=self.lib
        z.Z3_mk_config.restype=ctypes.c_void_p
        z.Z3_del_config.argtypes=[ctypes.c_void_p]
        z.Z3_mk_context.argtypes=[ctypes.c_void_p]; z.Z3_mk_context.restype=ctypes.c_void_p
        z.Z3_del_context.argtypes=[ctypes.c_void_p]
        z.Z3_eval_smtlib2_string.argtypes=[ctypes.c_void_p,ctypes.c_char_p]; z.Z3_eval_smtlib2_string.restype=ctypes.c_char_p
        z.Z3_get_full_version.restype=ctypes.c_char_p
        self.version=z.Z3_get_full_version().decode()
    def run(self,script):
        z=self.lib; cfg=z.Z3_mk_config(); ctx=z.Z3_mk_context(cfg); z.Z3_del_config(cfg)
        try:
            return z.Z3_eval_smtlib2_string(ctx,script.encode()).decode()
        finally:
            z.Z3_del_context(ctx)


def parse_sexpr(text):
    tokens=re.findall(r'\(|\)|[^\s()]+',text); pos=0
    def parse():
        nonlocal pos
        tok=tokens[pos];pos+=1
        if tok!='(': return tok
        ans=[]
        while tokens[pos]!=')': ans.append(parse())
        pos+=1; return ans
    return parse()


def sexpr_fraction(v):
    if isinstance(v,str): return F(v)
    op,*args=v
    vals=list(map(sexpr_fraction,args))
    if op=='/': return vals[0]/vals[1]
    if op=='-': return -vals[0] if len(vals)==1 else vals[0]-vals[1]
    if op=='+': return sum(vals,F(0))
    if op=='*':
        p=F(1)
        for x in vals: p*=x
        return p
    raise ValueError(f'Non-rational model expression: {v}')


def check_pair_model(inst,selected,epsilon,relation,raw):
    """Independent Fraction check of every returned rational witness."""
    values=dict(parse_sexpr(raw[raw.index('('):]))
    n=len(inst.r); mats=[]; losses=[]
    for c in ('A','B'):
        L=[[F(0) for _ in range(n)] for _ in range(n)]
        for (i,j),(lo,hi) in inst.bounds.items():
            L[i][j]=sexpr_fraction(values[f'{c}_L_{i}_{j}'])
            assert lo <= L[i][j] <= hi
        assert [sum(row,F(0)) for row in L]==inst.r
        assert [sum((L[i][j] for i in range(n)),F(0)) for j in range(n)]==inst.a
        p=clearing(L,inst.b,inst.x)
        for i in range(n):
            assert p[i]/(inst.r[i]+inst.b[i])==sexpr_fraction(values[f'{c}_u_{i}'])
        loss=outside_loss(L,inst.b,p)
        assert loss==sexpr_fraction(values[f'{c}_loss'])
        losses.append(loss);mats.append(L)
    for q in selected: assert inst.queries[q].value(mats[0])==inst.queries[q].value(mats[1])
    diff=losses[0]-losses[1]
    assert {'>':diff>epsilon,'>=':diff>=epsilon,'=':diff==epsilon}[relation]
    differences=[i for i,q in enumerate(inst.queries) if q.value(mats[0])!=q.value(mats[1])]
    return {'loss_A':str(losses[0]),'loss_B':str(losses[1]),'gap':str(diff),'distinguishing_queries':differences,
            'independent_fraction_check':'passed'}


def oracle(z: Z3Library, inst: Instance, selected, epsilon, relation='>', outdir=None, tag='query'):
    text,names=smt_pair(inst,selected,rat(epsilon),relation)
    query=text+'(check-sat)\n'
    raw=z.run(query);status=raw.strip().splitlines()[0]
    result={'selected':list(selected),'epsilon':str(epsilon),'relation':relation,'status':status}
    if status=='sat':
        query+='(get-value ('+' '.join(names)+'))\n'
        raw=z.run(query)
        if raw.strip().splitlines()[0]!='sat': raise RuntimeError('Inconsistent solver rerun')
        result.update(check_pair_model(inst,selected,rat(epsilon),relation,raw))
    elif status!='unsat':
        raise RuntimeError('No solver certificate: '+raw)
    if outdir:
        Path(outdir).mkdir(parents=True,exist_ok=True)
        Path(outdir,tag+'.smt2').write_text(query)
        Path(outdir,tag+'.txt').write_text(raw)
    return result


def optimal_threshold(z,inst,epsilon,budget=None,outdir=None):
    """Exact witness-cut/hitting-set algorithm for minimum-cost disclosure.
    The master problem is exhaustively solved (intended for small menus).
    """
    epsilon=rat(epsilon)
    if epsilon < 0:
        raise ValueError('Require a nonnegative loss-width tolerance')
    suffix=str(epsilon).replace('/', '_')
    feasibility=oracle(z,inst,[],F(0),relation='>=',outdir=outdir,tag=f'{inst.name}_eps{suffix}_feasibility')
    if feasibility['status']!='sat':
        raise ValueError('No network is consistent with the supplied observations')
    candidates=subsets(len(inst.queries))
    def cost(S): return sum((inst.queries[q].cost for q in S),F(0))
    candidates.sort(key=lambda S:(cost(S),len(S),S))
    if budget is not None: candidates=[S for S in candidates if cost(S)<=budget]
    cuts=[];history=[]
    for step in range(2**len(inst.queries)+1):
        S=next((S for S in candidates if all(set(S)&set(C) for C in cuts)),None)
        if S is None:
            return {'status':'infeasible','epsilon':str(epsilon),'cuts':cuts,'history':history}
        res=oracle(z,inst,S,epsilon,outdir=outdir,tag=f'{inst.name}_eps{suffix}_selection_{step}')
        history.append(res)
        if res['status']=='unsat':
            return {'status':'optimal','selected':list(S),'cost':str(cost(S)),'epsilon':str(epsilon),
                    'cuts':cuts,'history':history}
        C=res['distinguishing_queries']
        assert not set(C)&set(S)
        if C in cuts: raise AssertionError('Repeated cut')
        cuts.append(C)
    raise AssertionError('Finite pattern bound exceeded')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stages',type=int,default=2)
    p.add_argument('--epsilon',default='0')
    p.add_argument('--outdir',default='solver_queries')
    args=p.parse_args()
    result=optimal_threshold(Z3Library(),chain_instance(args.stages),F(args.epsilon),outdir=args.outdir)
    print(json.dumps(result,indent=2))
