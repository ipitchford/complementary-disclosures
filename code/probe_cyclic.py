#!/usr/bin/env python3
"""Tractability probe: the 'gap > shock' query (unsatisfiable by Lemma 2) on dense cyclic
and feed-forward random instances, default Z3 tactic and qfnra-nlsat, 60 s limit each."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from netinfo import *
import z3
for topo, gen, sizes in [('cyclic', random_instance, [(4, 9), (4, 10), (5, 11), (5, 12), (6, 13)]),
                         ('feed-forward', random_dag_instance, [(5, 10), (6, 13), (8, 17), (10, 22)])]:
    for n, E in sizes:
        inst, meta = gen(n, E, 1000 * n if topo == 'cyclic' else 7 * n, 3)
        shock = rat(meta['shock'])
        for tactic in (['default', 'qfnra-nlsat'] if topo == 'cyclic' else ['default']):
            s, V = build_pair(inst, [], shock, '>')
            if tactic != 'default':
                s2 = z3.Tactic('qfnra-nlsat').solver(); s2.add(*s.assertions()); s = s2
            s.set('timeout', 60000)
            t0 = time.perf_counter(); r = s.check(); dt = time.perf_counter() - t0
            print(topo, n, E, 'shock', shock, tactic, r, round(dt, 2), flush=True)
