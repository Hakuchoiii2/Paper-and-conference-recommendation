"""Fresh current-code workspace -> regenerate/validate D -> baseline -> verified export.

Optional --with-synthetic also runs/exports the separate synthetic observation pilot.
No existing workspace, dataset or result directory is deleted or overwritten.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

from export_results import export_bundle, sha

OWNER = Path(__file__).resolve().parent
PROJECT = OWNER.parents[1]


def run(arguments, cwd):
    command = [sys.executable, '-B', *arguments]
    print(f'RUN [{cwd}] ' + subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='run_' + datetime.now(ZoneInfo('Asia/Saigon')).strftime('%Y%m%d_%H%M%S'))
    parser.add_argument('--with-synthetic', action='store_true')
    args = parser.parse_args()
    if not args.name or Path(args.name).name != args.name or args.name in ('.', '..') or any(c in args.name for c in '/\\:'):
        raise ValueError('Run name must be a single directory name')
    workspace = OWNER / ('workspace_' + args.name)
    result = workspace / 'results/exp_d' / args.name
    destination = OWNER / 'results' / args.name
    synthetic = OWNER / 'evaluation' / (args.name + '_synthetic')
    synthetic_destination = OWNER / 'results' / (args.name + '_synthetic')
    for path in [workspace, destination] + ([synthetic, synthetic_destination] if args.with_synthetic else []):
        if path.exists():
            raise ValueError(f'Path already exists; choose a new --name: {path}')
    run([str(OWNER / 'prepare_workspace.py'), '--name', workspace.name, '--mode', 'current'], PROJECT)
    # Run current generator to issue a new manifest; never rewrite old hashes by hand.
    run(['data/exp_d/build_exp_d.py'], workspace)
    run(['data/exp_d/build_exp_d.py', '--validate-only'], workspace)
    run(['scripts/exp_d/run_exp_d.py', '--config', 'configs/exp_d.json',
         '--output', 'results/exp_d/' + args.name, '--ks', '5', '10', '--dry-run'], workspace)
    run(['scripts/exp_d/run_exp_d.py', '--config', 'configs/exp_d.json',
         '--output', 'results/exp_d/' + args.name, '--ks', '5', '10'], workspace)
    export_bundle(result, destination)
    if args.with_synthetic:
        run([str(OWNER / 'run_synthetic_observation_pilot.py'), '--source-root', str(workspace),
             '--output', str(synthetic)], PROJECT)
        export_bundle(synthetic, synthetic_destination)
    snapshot = json.loads((OWNER / 'audit' / (workspace.name + '_snapshot.json')).read_text(encoding='utf-8'))
    for record in snapshot['files']:
        if sha(PROJECT / record['path']) != record['source_sha256']:
            raise ValueError(f'Source checkout changed during pipeline: {record["path"]}')
    receipt = dict(workspace=str(workspace), baseline_results=str(destination),
                   synthetic_results=str(synthetic_destination) if args.with_synthetic else None,
                   current_D_regenerated=True, source_checkout_unchanged=True)
    (destination / 'pipeline_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print('PIPELINE COMPLETE: ' + str(destination), flush=True)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'PIPELINE FAILED (existing artifacts preserved): {error}', file=sys.stderr)
        raise SystemExit(1)
