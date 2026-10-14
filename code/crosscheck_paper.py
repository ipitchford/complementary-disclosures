#!/usr/bin/env python3
"""Read-only semantic checks of specified manuscript tables/numerical examples.
Fraction arithmetic and Decimal gamma-CDF inversion; not a whole-proof checker.
"""
import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as F
from itertools import combinations
import hashlib
import json
from pathlib import Path
import re
import sys

def require(value,message):
    if not value:
        raise ValueError(message)

def rounded(value,digits):
    require(value>=0,'Expected nonnegative value')
    scale=10**digits
    result=(2*value.numerator*scale+value.denominator)//(2*value.denominator)
    return str(result//scale)+'.'+str(result%scale).zfill(digits)

def table(text,header):
    lines=text.splitlines()
    found=[i for i,line in enumerate(lines) if line==header]
    require(len(found)==1,'Missing/duplicate table header')
    rows=[]; index=found[0]+2
    while index<len(lines) and lines[index].startswith('|'):
        rows.append([cell.strip() for cell in lines[index].strip('|').split('|')])
        index+=1
    return rows

def quantile_six():
    with localcontext() as context:
        context.prec=70
        low,high=Decimal(0),Decimal(20)
        for _ in range(240):
            x=(low+high)/2
            term=total=Decimal(1)
            for k in range(1,6):
                term*=x/k
                total+=term
            if 1-(-x).exp()*total<Decimal('0.05'):
                low=x
            else:
                high=x
        return (-high).exp(),(-low).exp()

def check(text):
    rows=table(text,r'| \(m\) | \(\beta=1\) | \(\beta=1/10\) | \(\beta=1/100\) |')
    require(len(rows)==5,'Ratio table row count')
    for row,m in zip(rows,(1,2,4,6,10)):
        require(row==[str(m)]+[rounded((1+b)**(-m),3) for b in (F(1),F(1,10),F(1,100))],'Ratio formula or half-up rounding mismatch')
    packages={}
    for selected in combinations(('x','y','z_1','z_2'),2):
        count=sum(q in selected for q in ('x','y'))
        worst=F(0) if count==2 else F(1,2)
        expected=F(0) if count==2 else F(1,2)*F(1,2)**count
        residual=sum((width for report,width in (('z_1',F(7,20)),('z_2',F(1,10))) if report not in selected),F(0))
        packages[frozenset(selected)]=(worst+residual,expected+residual)
    rows=table(text,'| Package | Worst-case width | Expected width |')
    labels=(r'\(\{x,y\}\)',r'\(\{z_1,z_2\}\)',r'\(\{x,z_1\}\) or \(\{y,z_1\}\)',r'\(\{x,z_2\}\) or \(\{y,z_2\}\)')
    require(len(rows)==4,'Package table row count')
    seen=set()
    for row,label in zip(rows,labels):
        require(len(row)==3 and row[0]==label,'Package label/group mismatch')
        values=tuple(F(v.removeprefix(r'\(').removesuffix(r'\)')) for v in row[1:])
        for members in re.findall(r'\\\{([^}]+)\\\}',row[0]):
            selected=frozenset(members.split(','))
            require(selected in packages and selected not in seen,'Invalid/duplicate package')
            require(values==packages[selected],'Package arithmetic mismatch')
            seen.add(selected)
    require(seen==set(packages),'Package choice missing')
    worst=min(v[0] for v in packages.values()); expected=min(v[1] for v in packages.values())
    require({s for s,v in packages.items() if v[0]==worst}=={frozenset(('x','y'))},'Minimax optimum mismatch')
    require({s for s,v in packages.items() if v[1]==expected}=={frozenset(('x','z_1')),frozenset(('y','z_1'))},'Expected optimum tie mismatch')
    prefix=r'At \(m=2,\beta=1,\eta=1/100\), the residual is \('
    match=re.search(re.escape(prefix)+r'([^=]+)=([0-9.]+)\\\), or \\\(([0-9.]+)\\\) of initial width\.',text)
    noise=F(1,4)*(1-(1-4*F(1,100))**2)
    require(match is not None,'Contextual two-report noise example missing')
    require(F(match[1])==noise and match[2]==rounded(noise,4) and match[3]==rounded(2*noise,4),'Noise value/normalization mismatch')
    match=re.search(r'Eight reports each with \\\(\\eta=1/1000\\\) leave about \\\(([0-9.]+)\\\) of initial width\.',text)
    require(match is not None and match[1]==rounded(F(1,2)*(1-(1-4*F(1,1000))**8),4),'Eight-report residual mismatch')
    match=re.search(r'After six of at least seven reports the 95th percentile is about \\\(([0-9.]+)c\\\): the realised width exceeds this threshold with probability 5%\.',text)
    qlo,qhi=quantile_six()
    require(qhi-qlo<Decimal('1e-60'),'Quantile bracket too wide')
    require(match is not None and match[1]==rounded(F(qlo),3)==rounded(F(qhi),3),'Six-report quantile or tail interpretation mismatch')
    return {'ratio_table_cells':15,'package_choices':6,'noise_examples':2,'quantile_fraction_bracket':[str(qlo),str(qhi)],'scope':'Specified numerical consequences; not universal/formal proof verification'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper',type=Path,default=Path(__file__).resolve().parents[1]/'paper'/'paper.md')
    args=parser.parse_args()
    text=args.paper.read_text()
    result=check(text)
    controls={
        'half-up tie rounded down':('| 4 | 0.063 |','| 4 | 0.062 |'),
        'ratio columns swapped':('| 1 | 0.500 | 0.909 | 0.990 |','| 1 | 0.909 | 0.500 | 0.990 |'),
        'package width changed':(r'| \(\{x,y\}\) | \(9/20\) |',r'| \(\{x,y\}\) | \(1/2\) |'),
        'package row omitted':(r'| \(\{z_1,z_2\}\) | \(1/2\) | \(1/2\) |',''),
        'noise numerator changed':('49/2500=0.0196','48/2500=0.0196'),
        'relative residual changed':(r'\(0.0158\) of initial width',r'\(0.0316\) of initial width'),
        'quantile tail reversed':('the 95th percentile is about','the 5th percentile is about'),
    }
    passed=[]
    for label,(old,new) in controls.items():
        require(old in text,'Missing negative-control marker: '+label)
        try:
            check(text.replace(old,new,1))
        except (ValueError,IndexError):
            passed.append(label)
        else:
            raise ValueError('Corruption control accepted: '+label)
    result.update(status='PASS',negative_controls=passed,optimized=sys.flags.optimize,manuscript_sha256=hashlib.sha256(args.paper.read_bytes()).hexdigest(),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),python_version=sys.version.split()[0])
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
