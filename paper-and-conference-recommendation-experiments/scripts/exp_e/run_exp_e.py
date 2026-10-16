"""E: Modular temporal profile runner supporting baselines and extensible research ideas."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from baseline_common import popularity, ranked
from experiment_io import ROOT
from experiment_runner import run_experiment

import exp_e.methods  # noqa: F401 - triggers @register_temporal_model decorators
from exp_e.registry import (
    MODEL_PRESETS,
    get_temporal_model,
    list_registered_models,
    resolve_model_keys,
)


def predict(papers, facets, cases, history, options):
    """Score candidate papers for each rolling temporal case using registered models."""
    popular = popularity(history)
    active_keys = resolve_model_keys(
        preset=options.get('preset', 'canonical'),
        models=options.get('active_models'),
    )
    active_models = [get_temporal_model(key) for key in active_keys]
    built_profiles = {
        model.name: (
            model,
            model.build_profiles(history, options['searches'], facets, options['cutoff'], options),
        )
        for model in active_models
    }

    predictions = []
    for case in cases:
        predictions.append(
            ranked(case, 'popularity', {p: popular[p] for p in case['candidate_ids']})
        )
        for model_name, (model_obj, profiles) in built_profiles.items():
            profile = profiles.get(case['user_id'])
            scores = model_obj.score_candidates(profile, case['candidate_ids'], facets)
            row = ranked(case, model_name, scores)
            if profile and 'facet_importance' in profile:
                row['facet_importance'] = profile['facet_importance']
            predictions.append(row)
    return predictions


def main_cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', help='Dataset config for one experiment')
    parser.add_argument(
        '--split',
        choices=['train', 'dev', 'test'],
        default='test',
        help='B only; C/D/E use temporal prefixes',
    )
    parser.add_argument('--ks', type=int, nargs='+', default=[5, 10])
    parser.add_argument(
        '--half-life-days',
        type=float,
        default=30,
        help='E decay baseline half-life in days, fixed before test',
    )
    parser.add_argument('--output', help='Result directory under project/results')
    parser.add_argument('--allow-shortfall', action='store_true')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--dry-run', action='store_true', help='Validate inputs without scoring/writing')
    parser.add_argument(
        '--preset',
        choices=sorted(MODEL_PRESETS.keys()),
        default='canonical',
        help='Model preset to evaluate (default: canonical)',
    )
    parser.add_argument(
        '--models',
        nargs='+',
        help='Explicit list of registered model keys to evaluate (overrides --preset)',
    )
    parser.add_argument(
        '--list-models',
        action='store_true',
        help='List all registered models and presets for Exp E and exit',
    )
    args = parser.parse_args()

    if args.list_models:
        print('=== Registered Exp E Temporal Models ===')
        for key in list_registered_models():
            print(f'  - {key}')
        print('\n=== Available Presets ===')
        for preset_name, keys in MODEL_PRESETS.items():
            print(f"  - {preset_name}: {', '.join(keys)}")
        return

    def configured_predict(papers, facets, cases, history, options):
        merged_options = dict(options, preset=args.preset, active_models=args.models)
        return predict(papers, facets, cases, history, merged_options)

    try:
        report = run_experiment(
            ROOT,
            'e',
            configured_predict,
            config_path=args.config,
            split=args.split,
            ks=args.ks,
            half_life_days=args.half_life_days,
            output=args.output,
            allow_shortfall=args.allow_shortfall,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
        print(
            f"{'DRY RUN' if args.dry_run else 'PASS'} E: {report['cases']} cases; "
            f"{report['protocol']}"
        )
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'FAILED E: {error}\n')


if __name__ == '__main__':
    main_cli()
