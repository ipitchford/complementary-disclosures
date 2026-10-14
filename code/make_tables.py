#!/usr/bin/env python3
"""Read-only historical reporting audit; never edits manuscript or old results.

Historical brackets are reported as archived solver evidence, not retroactively
certified rational-witness bounds. --output creates a new JSON file exclusively.
"""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import statistics
from netinfo import random_dag_instance, random_instance

ROOT = Path(__file__).resolve().parents[1]


def audit():
    output = {'scope': 'reaggregation_and_generator_metadata_check_only_not_fresh_solver_replay',
              'historical_lower_bound_witness_matrices': 'not_retained_cannot_retrofit',
              'datasets': {}, 'edge_count_corrections': []}
    combined = []
    def summarize(records):
        completed = [r for r in records if r['status'] == 'ok']
        positive = [r for r in completed if F(r['initial_width'][0]) > 0]
        unproved_zero = [r['name'] for r in completed if F(r['initial_width'][0]) == 0]
        width_calls = [r['max_call_seconds'] for r in completed]
        return {'instances': len(records), 'completed_brackets': len(completed),
                'unresolved_instances': len(records)-len(completed), 'positive_lower_bracket': len(positive),
                'zero_width_not_established_by_archived_bracket': unproved_zero,
                'reported_complementarity_among_completed_positive': sum(bool(r['complementarity']) for r in positive),
                'reported_negligible_singleton_among_completed_positive': sum(bool(r['certified_zero_value_singletons']) for r in positive),
                'selection_statuses': {status:sum(r.get('selection',{}).get('status')==status for r in positive)
                                       for status in ('optimal','infeasible','unknown')},
                'selection_target': 'initial_upper_bracket/2_not_exact_half_true_width',
                'max_recorded_width_query_seconds_completed_only': max(width_calls,default=None),
                'historical_selection_query_maximum': 'unavailable_not_reconstructed_from_total_duration',
                'median_wall_seconds_all_instances': statistics.median(r['wall_seconds'] for r in records),
                'max_wall_seconds_all_instances': max(r['wall_seconds'] for r in records),
                'interpretation': 'conditional_descriptive_counts_not_population_prevalence_or_causal_topology_comparison'}
    for tag in ('dag_menu3_a','dag_menu3_b','dag_menu4','cyclic_menu3'):
        file = ROOT/'results'/(tag+'.json')
        data = json.loads(file.read_text())
        records, settings = data['records'], data['args']
        output['datasets'][tag] = {**summarize(records), 'source_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                                   'source_file': 'results/'+file.name}
        if tag.startswith('dag_menu3'):
            combined += records
        generator = random_dag_instance if settings['topology']=='dag' else random_instance
        for record in records:
            inst, meta = generator(record['n'],record['edges'],record['seed'],record['menu'])
            if record['edges'] != len(inst.bounds):
                output['edge_count_corrections'].append({'dataset':tag,'name':record['name'],
                    'historical_requested_and_reported_edges':record['edges'],'actual_allowed_edges':len(inst.bounds)})
    output['dag_menu3_combined'] = summarize(combined)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    result = json.dumps(audit(),indent=2)+'\n'
    if args.output:
        with args.output.open('x') as file:
            file.write(result)
    print(result,end='')


if __name__=='__main__':
    main()
