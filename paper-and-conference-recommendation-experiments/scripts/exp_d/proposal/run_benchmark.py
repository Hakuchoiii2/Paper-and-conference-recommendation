"""Complete D run: locked dataset -> 8 public methods -> oracle -> all metrics."""
import argparse
import importlib.util
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from data_io import (DATA_ROOT, FACETS, PROJECT, evidence_for, inside, load_public, new_output,
                     read_json, read_rows, require, sha, shared_representation, write_json, write_rows)
from baseline_common import intent_scores, ranked, search_vocabulary
from methods import DEFAULTS, MODELS, predict_all
from ordinal_intent import DEFAULTS as ORDINAL_DEFAULTS
from common_ranking import ranking_directions
from evaluate import (ORACLE, conclusions, legacy_summary, load_truth, oracle_predictions,
                      paired_comparisons, score_predictions, summarize, write_csv)
from reporting import report, metric_definitions
from validate_observation_data import validate_dataset


def progress(phase, **values):
    import json
    print(json.dumps(dict(phase=phase, **values), ensure_ascii=False), flush=True)


def validate_parameters(config):
    require(set(config) == set(DEFAULTS), 'Config keys differ from frozen method schema')
    require(type(config['minimum_pairs']) is int and config['minimum_pairs'] > 0, 'Invalid minimum pairs')
    require(config['delta_margin'] >= 0, 'Invalid DELTA margin')
    require(.5 < config['vote_fraction'] <= 1, 'Invalid vote fraction')
    for field in ('reaction_reliability', 'query_reliability'):
        require(.5 < config[field] < 1, 'Reliability must be between .5 and 1')
    for field in ('posterior_minimum', 'posterior_gap'):
        require(0 <= config[field] <= 1, 'Invalid posterior threshold')


def validate_ordinal(config):
    require(set(config)==set(ORDINAL_DEFAULTS), 'Invalid ordinal config schema')
    require(isinstance(config['strengths'],list) and bool(config['strengths'])
            and all(type(v) in (int,float) and math.isfinite(v) and v>0 for v in config['strengths']),
            'Ordinal strengths must be positive finite values')
    require(.5<config['query_reliability']<1, 'Invalid ordinal query reliability')
    require(type(config['minimum_pairs']) is int and config['minimum_pairs']>0, 'Invalid ordinal pair count')
    require(all(0<=config[f]<=1 for f in ('posterior_minimum','posterior_gap')), 'Invalid ordinal thresholds')


def predict_condition(public, condition_name, profiles, vectors, config, ordinal_config=None):
    vocabulary = search_vocabulary(public['facets'])
    predictions = []
    for case in public['cases']:
        evidence = evidence_for(case, public['conditions'][condition_name], public['queries'])
        estimates = predict_all(evidence, public['facets'], config, vocabulary, ordinal_config)
        for model in MODELS:
            weights = (dict.fromkeys(FACETS, 1/len(FACETS)) if model == 'fixed_similar'
                       else dict(profiles[case['user_id']]['facet_importance']))
            estimate = estimates[model]
            directions, policy = ranking_directions(case['context_facet'],estimate['directions'])
            row = ranked(case, model, intent_scores(case, weights, directions, vectors))
            original = ranked(case,model,intent_scores(case,weights,estimate['directions'],vectors))
            row.update(condition=condition_name, facet_importance=weights, privileged_information=False,
                       ranking_directions=directions, ranking_policy=policy,
                       legacy_ranking=original['ranking'], **estimate)
            predictions.append(row)
    return predictions


def legacy_parity(public, condition_name, predictions, cutoff, config):
    """Actual original runner, not a rewritten expected implementation."""
    path = PROJECT / 'scripts/exp_d/run_exp_d.py'
    spec = importlib.util.spec_from_file_location('original_d_runner_for_parity', path)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    cases = public['cases']
    options = dict(profile_history=public['history'], profile_searches=public['history_queries'], cutoff=cutoff,
                   exposures=public['conditions'][condition_name]['exposures'], searches=public['queries'],
                   direction_margin=config['delta_margin'], min_direction_pairs=config['minimum_pairs'])
    original = legacy.predict({}, public['facets'], cases, public['conditions'][condition_name]['reactions'], options)
    actual = {(r['case_id'], r['model']):r for r in predictions if r['condition'] == condition_name}
    for expected in original:
        row = actual[expected['case_id'], expected['model']]
        for field, value in expected.items():
            actual_value = row['legacy_ranking'] if field=='ranking' else row[field]
            require(actual_value == value, f'Original baseline mismatch: {expected["model"]}/{field}')
    return dict(status='PASS', original_runner=str(path.relative_to(PROJECT)), cases=len(cases),
                original_prediction_rows=len(original), models=sorted({r['model'] for r in original}),
                exact_fields=['ranking', 'directions', 'direction_confidence', 'facet_importance'],
                scope='All sessions in this condition; raw directions/weights and original-policy rankings exact.')


def protected_inputs(dataset):
    manifest = read_json(dataset / 'manifest.json')
    paths = [dataset / 'manifest.json'] + [inside(dataset, name) for name in manifest['files']]
    source = inside(DATA_ROOT, manifest['source_directory'])
    source_manifest = read_json(source / 'manifest.json')
    paths += [source / 'manifest.json'] + [inside(source, name) for name in source_manifest['files']]
    paths += [PROJECT / name for name in (
        'scripts/baseline_common.py', 'scripts/exp_d/run_exp_d.py', 'scripts/exp_d/README.md',
        'data/exp_d/build_exp_d.py', 'data/exp_d/README.md', 'scripts/experiment_io.py',
        'scripts/experiment_runner.py', 'scripts/build_corpus.py', 'scripts/validate_all.py')]
    for name in ('generated', 'ground_truth', 'samples'):
        paths += [p for p in (PROJECT / 'data/exp_d' / name).rglob('*') if p.is_file()]
    return {str(p.relative_to(PROJECT)).replace('\\', '/'):sha(p) for p in paths}


def run(dataset, output, config_path=None, bootstrap_repetitions=2000, ordinal_config_path=None):
    dataset = Path(dataset).resolve()
    require(dataset.is_relative_to(DATA_ROOT) and dataset != DATA_ROOT, 'Dataset escapes proposal')
    output = new_output(output)
    config_path = Path(config_path) if config_path else Path(__file__).with_name('benchmark_config.json')
    config = read_json(config_path)
    validate_parameters(config)
    ordinal_config_path = Path(ordinal_config_path) if ordinal_config_path else Path(__file__).with_name('ordinal_config.json')
    ordinal_config = read_json(ordinal_config_path)
    validate_ordinal(ordinal_config)
    require(bootstrap_repetitions >= 20, 'At least 20 bootstrap repetitions required')
    progress('validate_dataset')
    validation = validate_dataset(dataset)
    before = protected_inputs(dataset)
    public = load_public(dataset)
    output.mkdir(parents=True)
    write_json(output / 'manifest.json', dict(status='running', models=list(MODELS)))
    try:
        write_json(output / 'validation_report.json', validation)
        write_json(output / 'config.json', dict(methods=config, ordinal=ordinal_config, bootstrap_repetitions=bootstrap_repetitions,
                   aggregation='mean repeats within design -> mean designs within anchor workgroup -> mean workgroups',
                   training='none', tuning_on_dataset=False, posterior_calibrated=False,
                   input_dataset=str(dataset.relative_to(PROJECT)), models=list(MODELS), oracle=ORACLE,
                   ranking_policy='R_active shared by all public methods; unchanged intent_scores',
                   metric_scope='Focus-only main; original context+focus metrics in legacy tables',
                   inference_source='dataset only; never read previous results',
                   protocol='Exploratory pilot inspected previously; no tuning in this run'))
        (output / 'protocol.md').write_bytes((PROJECT / 'data/exp_d/README_PROPOSAL.md').read_bytes())
        progress('freeze_C_profiles_and_facet_vectors')
        profiles, vectors, cutoff = shared_representation(public)
        write_json(output / 'shared_profiles.json', {u:profiles[u]['facet_importance'] for u in sorted(profiles)})
        predictions = []
        parity_conditions = {}
        for condition in public['conditions']:
            rows = predict_condition(public, condition, profiles, vectors, config, ordinal_config)
            predictions.extend(rows)
            progress('predictions', condition=condition, rows=len(rows))
            parity_conditions[condition] = legacy_parity(public,condition,rows,cutoff,config)
        write_rows(output / 'predictions.jsonl', predictions)
        progress('original_baseline_parity')
        parity = dict(status='PASS',conditions=parity_conditions,
                      original_prediction_rows=sum(r['original_prediction_rows'] for r in parity_conditions.values()))
        write_json(output / 'baseline_parity.json', parity)
        # Load labels only after all predictions have been persisted and parity checked.
        progress('evaluate_predictions')
        truth = load_truth(dataset)
        oracles = oracle_predictions(public['cases'],public['conditions'],truth,vectors)
        write_rows(output/'oracle_predictions.jsonl',oracles)
        details = score_predictions(predictions+oracles, public['cases'], truth, public['condition_metadata'], include_oracle=True)
        summary, cluster_values = summarize(details)
        original_metrics = legacy_summary(details)
        comparisons = paired_comparisons(cluster_values, bootstrap_repetitions)
        claims = conclusions(comparisons, summary)
        write_rows(output / 'details.jsonl', details)
        write_json(output / 'summary.json', summary)
        write_json(output / 'legacy_summary.json',original_metrics)
        write_json(output / 'metric_definitions.json',metric_definitions())
        write_json(output / 'conclusions.json', claims)
        write_csv(output / 'summary.csv', [r for r in summary if r['group'] == 'overall'])
        write_csv(output / 'groups.csv', summary)
        write_csv(output / 'legacy_summary.csv',[{k:v for k,v in r.items() if k!='defined_cases'}
                  for r in original_metrics if r['group']=='overall'])
        write_csv(output / 'legacy_groups.csv',[{k:v for k,v in r.items() if k!='defined_cases'} for r in original_metrics])
        write_csv(output / 'paired_comparisons.csv', comparisons)
        run_info = dict(evaluations=len(predictions),oracle_evaluations=len(oracles),
                        sessions=len(public['cases']),conditions=len(public['conditions']),
                        feedback_seeds=sorted({r['seed'] for r in public['condition_metadata'].values()}),
                        feedback_noises=sorted({r['noise'] for r in public['condition_metadata'].values()}),
                        dataset=str(dataset.relative_to(PROJECT)),validation=validation,
                        source_snapshots='scripts/exp_d/backup/20261021_complete_runner')
        (output / 'report.md').write_text(report(summary,original_metrics,claims,run_info), encoding='utf-8')
        require(all(sha(PROJECT / name) == expected for name, expected in before.items()), 'Input or baseline changed during run')
        code_paths = list(Path(__file__).parent.glob('*.py')) + [config_path,ordinal_config_path]
        write_json(output / 'manifest.json', dict(status='complete', protocol='d_complete_v2',
                   models=list(MODELS), oracle=ORACLE, prediction_rows=len(predictions), oracle_rows=len(oracles),
                   total_evaluations=len(details),dataset_unchanged=True, baseline_unchanged=True,
                   protected_inputs=before, C_profile_cutoff=cutoff,
                   code_sha256={str(p.relative_to(PROJECT)).replace('\\', '/'):sha(p) for p in code_paths},
                   output_sha256={p.name:sha(p) for p in output.iterdir() if p.is_file() and p.name != 'manifest.json'},
                   no_training=True, independent_test=False, scope='controlled_mock_pilot',
                   baseline_parity=parity['status'], semantic_review='not_required_for_controlled_mock_not_human_validated'))
        progress('complete', output=str(output), prediction_rows=len(predictions),oracle_rows=len(oracles))
        return summary, comparisons
    except Exception as error:
        write_json(output / 'FAILED.json', dict(status='failed', error=repr(error)))
        write_json(output / 'manifest.json',dict(status='FAILED',error=repr(error)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=DATA_ROOT / 'datasets/observation_v1')
    stamp = datetime.now(timezone(timedelta(hours=7))).strftime('%Y%m%d_%H%M%S')
    parser.add_argument('--output', type=Path, default=DATA_ROOT / 'results' / ('benchmark_complete_'+stamp))
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('benchmark_config.json'))
    parser.add_argument('--bootstrap-repetitions', type=int, default=2000)
    parser.add_argument('--ordinal-config',type=Path,default=Path(__file__).with_name('ordinal_config.json'))
    args = parser.parse_args()
    run(args.dataset, args.output, args.config, args.bootstrap_repetitions,args.ordinal_config)


if __name__ == '__main__':
    main()
