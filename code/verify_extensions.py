#!/usr/bin/env python3
"""Original finite Fraction checks for revised statements; not universal proof.

Checks exact primal/dual affine-simplex certificates, the zero-prior correction,
one-layer endpoint witnesses, and heterogeneous noise including coarse errors.
Read-only. No private reviewer implementation is imported or redistributed.
"""
from fractions import Fraction as F
from itertools import product, combinations
import json
import hashlib
from pathlib import Path
import sys
from netinfo import clearing, outside_loss, require, subsets


def dot(a, b):
    return sum((x*y for x,y in zip(a,b)),F(0))


def certificate(A, c, eta, t, u, multipliers):
    k = len(c)
    require(k > 0 and len(t)==len(u)==k, 'Primal dimensions disagree')
    require(len(A)==len(eta)==len(multipliers) and all(len(row)==k for row in A), 'Dual dimensions disagree')
    values = list(c)+list(t)+list(u)+list(eta)+list(multipliers)+[v for row in A for v in row]
    require(all(isinstance(v,(int,F)) and not isinstance(v,bool) for v in values), 'Exact rational certificate required')
    require(all(v>=0 for v in eta), 'Negative reporting error')
    require(all(v>=0 for v in t+u) and sum(t)==sum(u)==1, 'Primal point outside simplex')
    difference = [x-y for x,y in zip(t,u)]
    require(all(abs(dot(row,difference))<=2*error for row,error in zip(A,eta)), 'Primal reports incompatible')
    residual = [c[i]-sum((lam*row[i] for lam,row in zip(multipliers,A)),F(0)) for i in range(k)]
    lower = dot(c,difference)
    upper = max(residual)-min(residual)+2*dot(eta,list(map(abs,multipliers)))
    require(lower==upper and lower>=0, 'Primal and dual bounds do not coincide')
    return lower


def affine_tests():
    count = 0
    c = [F(1),F(0),F(0)]
    A = [[F(0),F(1),F(0)],[F(0),F(0),F(1)]]
    e0 = [F(1),F(0),F(0)]
    for eta in product([F(0),F(1,100),F(1,10),F(1,4),F(1,2),F(3,4)],repeat=2):
        if 2*sum(eta)<=1:
            u = [1-2*sum(eta),2*eta[0],2*eta[1]]
            multipliers = [F(-1),F(-1)]
        else:
            mass = min(F(1),2*eta[0])
            u = [F(0),mass,1-mass]
            multipliers = [F(0),F(0)]
        require(certificate(A,c,list(eta),e0,u,multipliers)==min(F(1),2*sum(eta)), 'Coordinate noisy width mismatch')
        count += 1
    certificate(A[:1],c,[F(0)],e0,[F(0),F(0),F(1)],[F(0)])
    certificate([A[0],A[0],A[1]],c,[F(0)]*3,e0,e0,[F(-1),F(0),F(-1)])
    count += 2
    for coefficients in ([F(3),F(-1),F(2),F(0)],[F(1)]*4):
        for selected in subsets(4):
            unseen = [i for i in range(4) if i not in selected]
            rows = [[F(i==j) for i in range(4)] for j in selected]
            if unseen:
                high = max(unseen,key=lambda i:coefficients[i])
                low = min(unseen,key=lambda i:coefficients[i])
                center = (coefficients[high]+coefficients[low])/2
                t = [F(i==high) for i in range(4)]
                u = [F(i==low) for i in range(4)]
                expected = coefficients[high]-coefficients[low]
            else:
                center=F(0); t=u=[F(1,4)]*4; expected=F(0)
            lam = [coefficients[i]-center for i in selected]
            require(certificate(rows,coefficients,[F(0)]*len(rows),t,u,lam)==expected, 'Coordinate menu formula mismatch')
            count += 1
    return count


def corrected_prior_tests():
    count, old_failures = 0, 0
    for m in (2,3,4):
        for kappa in product([F(0),F(1,4),F(1,2),F(3,4),F(1)],repeat=m):
            widths = {selected: (F(0) if len(selected)==m else product_fraction(kappa[i] for i in selected)) for selected in subsets(m)}
            gain = {selected:F(1)-value for selected,value in widths.items()}
            submodular = True
            for selected in subsets(m):
                for i,j in combinations([i for i in range(m) if i not in selected],2):
                    si,sj,sij = [tuple(sorted(selected+extra)) for extra in ((i,),(j,),(i,j))]
                    if gain[si]+gain[sj]-gain[selected]-gain[sij]<0:
                        submodular=False
            corrected = all(product_fraction(kappa[k] for k in range(m) if k not in (i,j))*(1-kappa[i]-kappa[j])>=0
                            for i,j in combinations(range(m),2))
            old = all(kappa[i]+kappa[j]<=1 for i,j in combinations(range(m),2))
            require(corrected==submodular, 'Corrected prior criterion failed')
            old_failures += old!=submodular
            count += 1
    require(count==775 and old_failures==302, 'Prior grid census mismatch')
    return {'parameter_vectors':count,'old_criterion_counterexamples':old_failures}


def product_fraction(values):
    result=F(1)
    for value in values:
        result *= value
    return result


def product_gap_formula(errors):
    require(bool(errors) and all(v>=0 for v in errors), 'Nonnegative nonempty noise vector required')
    delta=[min(4*v,F(2)) for v in errors]
    largest=max(delta)
    return 1-product_fraction(1-v for v in delta) if largest<=1 else largest


def noise_tests():
    count=pairs=0
    errors=[F(0),F(1,100),F(1,4),F(1,2),F(3,4)]
    for m in (1,2,3):
        for eta in product(errors,repeat=m):
            vertices=[]
            for error in eta:
                delta=min(4*error,F(2))
                vertices.append(sorted(set([(-F(1),-F(1)),(F(1),F(1)),(-F(1),-1+delta),
                                            (-1+delta,-F(1)),(F(1),1-delta),(1-delta,F(1))])))
            best=F(0)
            for vertex in product(*vertices):
                best=max(best,abs(product_fraction(v[0] for v in vertex)-product_fraction(v[1] for v in vertex)))
                pairs+=1
            require(best==product_gap_formula(eta),'Heterogeneous/coarse noise formula failed')
            count+=1
    require(product_gap_formula([F(1,100)]*2)/4==F(49,2500),'Noise sanity value wrong')
    return {'heterogeneous_configurations':count,'product_polytope_vertices':pairs,
            'domains_included':['zero','one_quarter','one_half','above_one_half','mixed_precisions']}


def one_layer_matrix(t, outside):
    k=len(t)
    L=[[F(0)]*(2*k) for _ in range(2*k)]
    for j in range(k):
        L[0][k+j]=t[j]
        for i in range(1,k):
            L[i][k+j]=(1-t[j])/(k-1)
    b=[outside]*k+[F(1)]*k
    assets=[F(0)]+[1+outside]*(k-1)+[F(0)]+[F(1)]*(k-1)
    return L,b,assets


def one_layer_tests():
    count=endpoints=0
    for k in (2,3,4,5):
        for outside in (F(1,100),F(1,4),F(1)):
            for integers in product(range(5),repeat=k):
                if sum(integers)!=4:
                    continue
                t=[F(x,4) for x in integers]
                L,b,assets=one_layer_matrix(t,outside)
                require(outside_loss(L,b,clearing(L,b,assets))==outside+t[0],'Affine one-layer clearing mismatch')
                count+=1
            for selected in subsets(k-1):
                if len(selected)==k-1:
                    continue
                omitted=next(j+1 for j in range(k-1) if j not in selected)
                t=[F(i==0) for i in range(k)]
                u=[F(i==omitted) for i in range(k)]
                require(all(t[j+1]==u[j+1] for j in selected),'Endpoint reports differ')
                L,b,assets=one_layer_matrix(t,outside)
                M,_,_=one_layer_matrix(u,outside)
                require(outside_loss(L,b,clearing(L,b,assets))-outside_loss(M,b,clearing(M,b,assets))==1,'Endpoint loss gap not one')
                endpoints+=1
    return {'rational_clearing_cases':count,'proper_menu_endpoint_pairs':endpoints}


def negative_controls():
    passed=[]
    def fails(label,callback):
        try:
            callback()
        except ValueError:
            passed.append(label)
            return
        raise ValueError('Negative control accepted: '+label)
    c=[F(1),F(0),F(0)]; A=[[F(0),F(1),F(0)],[F(0),F(0),F(1)]]
    e0=[F(1),F(0),F(0)]; e1=[F(0),F(1),F(0)]
    fails('primal outside simplex',lambda:certificate(A,c,[F(0)]*2,[F(2),F(0),F(0)],e0,[F(-1)]*2))
    fails('incompatible exact reports',lambda:certificate(A,c,[F(0)]*2,e0,e1,[F(-1)]*2))
    fails('incorrect dual objective',lambda:certificate(A,c,[F(0)]*2,e0,e0,[F(0)]*2))
    fails('negative noise',lambda:certificate(A,c,[F(-1),F(0)],e0,e0,[F(-1)]*2))
    fails('floating point certificate',lambda:certificate(A,c,[F(0)]*2,[1.0,F(0),F(0)],e0,[F(-1)]*2))
    fails('negative product error',lambda:product_gap_formula([F(-1)]))
    # The small-error branch must not be extrapolated through the coarse regime.
    eta=[F(1,2),F(1,2)]
    require(product_gap_formula(eta)==2 and 1-product_fraction(1-4*v for v in eta)==0,'Coarse regime regression')
    passed.append('coarse-error branch rejects small-error extrapolation')
    return passed


def main():
    result={'affine_primal_dual_certificates':affine_tests(),'corrected_prior':corrected_prior_tests(),
            'noise':noise_tests(),'one_layer':one_layer_tests(),'negative_controls':negative_controls(),
            'optimized':sys.flags.optimize,'scope':'finite exact checks, not a universal proof or independent external reproduction',
            'status':'PASS'}
    result['python_version']=sys.version.split()[0]
    result['code_sha256']={name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                           for name in ('verify_extensions.py','netinfo.py')}
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
