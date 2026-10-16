"""Create an isolated D snapshot; restore LF only if manifest fingerprints match."""
import hashlib
import argparse
import json
from pathlib import Path
import sys
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='workspace', help='New directory name inside exp_d')
    parser.add_argument('--mode', choices=['current', 'baseline'], default='current',
                        help='current: copy current D generator, then regenerate D; baseline: replay manifest generator')
    args = parser.parse_args()
    owner = Path(__file__).resolve().parent
    source = owner.parents[1]
    require_name = args.name and Path(args.name).name == args.name and args.name not in ('.', '..')
    if not require_name or '/' in args.name or '\\' in args.name or ':' in args.name:
        raise ValueError('Workspace name must be one directory name inside exp_d')
    target = owner / args.name
    # Existing snapshots are never refreshed silently; preserve experiments run there.
    if target.exists():
        raise ValueError(f'Workspace already exists; preserved without changes: {target}')
    paths = set()
    for directory in ('scripts', 'schemas', 'configs'):
        paths.update(p.relative_to(source).as_posix() for p in (source / directory).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts)
    paths.update(p.relative_to(source).as_posix() for p in (source / 'data').glob('*.py'))
    for name in 'abcde':
        paths.update(p.relative_to(source).as_posix()
                     for p in (source / f'data/exp_{name}').glob('*.py'))
    expected = {}
    def remember(name, value):
        if name in expected and expected[name] != value:
            raise ValueError(f'Conflicting manifest fingerprints: {name}')
        expected[name] = value
        paths.add(name)
    for name in 'acd':
        manifest_name = f'data/exp_{name}/generated/manifest.json'
        paths.add(manifest_name)
        manifest = json.loads((source / manifest_name).read_text(encoding='utf-8'))
        if name == 'a':
            for key, value in manifest['files'].items():
                remember(f'data/exp_a/generated/{key}', value)
            for key, value in manifest['provenance']['input_hashes'].items():
                remember(manifest['provenance']['config'][key], value)
        else:
            for section in ('input_hashes', 'files', 'generator_hashes'):
                for key, value in manifest[section].items():
                    remember(key, value)
    payloads = {}
    records = []
    normalized = {'data/processed/papers.jsonl', 'scripts/build_corpus.py'}
    d_generator = 'data/exp_d/build_exp_d.py'
    for name in sorted(paths):
        original = (source / name).resolve()
        destination = (target / name).resolve()
        if not original.is_relative_to(source) or not destination.is_relative_to(target):
            raise ValueError(f'Unsafe snapshot path: {name}')
        if original.is_relative_to(target):
            raise ValueError('Recursive workspace copy refused')
        data = original.read_bytes()
        copied = data.replace(b'\r\n', b'\n') if name in normalized else data
        operation = 'CRLF_to_LF' if copied != data else 'byte_copy'
        if name == d_generator and args.mode == 'current':
            operation = 'current_D_generator_regenerate_D_before_validation'
        elif name in expected and sha(copied) != expected[name]:
            if name != d_generator or args.mode != 'baseline':
                raise ValueError(f'Cannot reproduce expected manifest bytes: {name}')
            # Replay only if the tracked HEAD version reproduces the recorded hash exactly.
            git_path = original.relative_to(Path(subprocess.check_output(
                ['git', '-C', str(source), 'rev-parse', '--show-toplevel'], text=True).strip())).as_posix()
            copied = subprocess.check_output(['git', '-C', str(source), 'show', 'HEAD:' + git_path])
            if sha(copied) != expected[name]:
                raise ValueError(f'HEAD cannot reproduce manifest generator: {name}')
            operation = 'verified_manifest_generator_from_git_HEAD'
        payloads[name] = copied
        records.append(dict(path=name, source_sha256=sha(data), workspace_sha256=sha(copied),
                            operation=operation,
                            bytes=len(copied)))
    for name, data in payloads.items():
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    for record in records:
        if sha((source / record['path']).read_bytes()) != record['source_sha256']:
            raise ValueError(f'Source changed during snapshot: {record["path"]}')
        if sha((target / record['path']).read_bytes()) != record['workspace_sha256']:
            raise ValueError(f'Copy verification failed: {record["path"]}')
    report = dict(created_at=datetime.now(ZoneInfo('Asia/Saigon')).isoformat(),
                  source_root=str(source), workspace_root=str(target),
                  mode=args.mode, requires_D_regeneration=args.mode == 'current',
                  source_files_unchanged=True, manifests_modified=False,
                  file_count=len(records), total_bytes=sum(r['bytes'] for r in records), files=records)
    (owner / 'audit').mkdir(exist_ok=True)
    (owner / f'audit/{args.name}_snapshot.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Created {target}: {len(records)} files; source unchanged; manifests unchanged.')
    if args.mode == 'current':
        print('Next: cd into this workspace; python -B data/exp_d/build_exp_d.py; '
              'then validate D and run baselines. Old D manifest is only a snapshot until regeneration.')
    else:
        print('Baseline replay snapshot ready for source validation; current generator changes are not applied.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print(f'WORKSPACE FAILED: {error}', file=sys.stderr)
        raise SystemExit(1)
