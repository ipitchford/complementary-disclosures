#!/usr/bin/env python3
"""Read-only aggregation of the completed retained study; no solver rerun."""
import argparse
from collections import Counter
from datetime import datetime
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
from verify_assurance import recheck_coverage, recheck_record


def aggregate(records):
    queries=[q for record in records for q in record['queries']]
    screens=[screen for record in records for screen in record.get('accounting_redundancy_screen',[])]
    selections=[record['selection'] for record in records if 'selection' in record]
    cross={key:Counter() for key in ('certified_negligible','not_certified_negligible')}
    for record in records:
        negligible=set(record.get('certified_negligible_singletons',[]))
        for screen in record.get('accounting_redundancy_screen',[]):
            key='certified_negligible' if screen['report'] in negligible else 'not_certified_negligible'
            cross[key][screen['classification']]+=1
    return {
        'instances':len(records),
        'width_stage_statuses':dict(Counter(record['status'] for record in records)),
        'positive_width_certified':sum(record.get('zero_width_status')=='positive_certified' for record in records),
        'zero_width_by_positive_gap_unsat':sum(record.get('zero_width_status')=='zero_certified_by_solver_unsat' for record in records),
        'zero_shock_instances':sum(record['status']=='zero_shock' for record in records),
        'complementarity_certified':sum(record.get('complementarity',False) for record in records),
        'full_menu_informative_certified':sum(record.get('certified_informative_full_menu',False) for record in records),
        'instances_with_negligible_singletons':sum(bool(record.get('certified_negligible_singletons')) for record in records),
        'negligible_singleton_reports':sum(len(record.get('certified_negligible_singletons',[])) for record in records),
        'selection_attempts':len(selections),
        'selection_statuses':dict(Counter(s['status'] for s in selections)),
        'screened_instances':sum('accounting_redundancy_screen' in record for record in records),
        'screened_reports':len(screens),
        'accounting_screen':dict(Counter(s['classification'] for s in screens)),
        'negligibility_by_accounting_status':{key:dict(value) for key,value in cross.items()},
        'requested_edge_counts':sorted(set(record['requested_edges'] for record in records)),
        'actual_edge_counts':sorted(set(record['edges'] for record in records)),
        'edge_count_corrections':sum(record['edges']!=record['requested_edges'] for record in records),
        'queries':len(queries),
        'solver_statuses':dict(Counter(q['status'] for q in queries)),
        'evidence_classes':dict(Counter(q['evidence'] for q in queries)),
        'query_stages':dict(Counter('width' if q['stage'].startswith('width:') else q['stage'] for q in queries)),
        'solver_seconds_sum':sum(q['seconds'] for q in queries),
        'max_solver_call_seconds':max((q['seconds'] for q in queries),default=0),
        'max_query_wall_seconds':max((q['wall_seconds'] for q in queries),default=0),
        'sum_instance_wall_seconds':sum(record['wall_seconds'] for record in records),
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=Path(__file__).resolve().parents[1]/'results'/'fresh-full')
    args=parser.parse_args()
    summary=json.loads((args.results/'summary.json').read_text())
    records={p.name:json.loads(p.read_text()) for p in sorted(args.results.glob('instance-*.json'))}
    coverage=recheck_coverage(summary,records)
    for record in records.values():
        recheck_record(record)
    groups={}; start=0
    for tag in ('dag_menu3_a','dag_menu3_b','dag_menu4','cyclic_menu3'):
        original=json.loads((Path(__file__).resolve().parents[1]/'results'/(tag+'.json')).read_text())
        count=len(original['records'])
        groups[tag]=aggregate([records[f'instance-{i:03d}.json'] for i in range(start,start+count)])
        start+=count
    result={
        'status':'PASS','scope':'Completed finite replay; not a prevalence estimate or universal proof',
        'coverage':coverage,'groups':groups,'all_instances':aggregate(list(records.values())),
        'started_utc':summary['started_utc'],'finished_utc':summary['finished_utc'],
        'elapsed_wall_seconds':(datetime.fromisoformat(summary['finished_utc'])-datetime.fromisoformat(summary['started_utc'])).total_seconds(),
        'timing_scope':'solver seconds sum/max includes every retained width, zero test, feasibility, selection and redundancy call; query wall includes extraction/check overhead; elapsed wall is the two-worker makespan, not summed worker time',
        'denominators':'ok means every width bracket completed, not every later query resolved; selection attempted only after a positive initial lower bracket; redundancy screens only after width completion; variable reports need not affect loss',
        'summary_sha256':hashlib.sha256((args.results/'summary.json').read_bytes()).hexdigest(),
        'record_sha256':{name:hashlib.sha256((args.results/name).read_bytes()).hexdigest() for name in records},
        'code_sha256':{name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in ('summarize_fresh.py','verify_assurance.py','netinfo.py','study_random.py')},
        'python_version':sys.version.split()[0],'optimized':sys.flags.optimize,
    }
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
