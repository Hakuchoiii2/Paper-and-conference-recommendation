"""Copy a verified result bundle into exp_d/results, without altering its manifest."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
from zoneinfo import ZoneInfo

OWNER = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_bundle(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_relative_to(OWNER) or not destination.is_relative_to(OWNER / 'results'):
        raise ValueError('Source must be inside exp_d; destination must be inside exp_d/results')
    if destination == source or destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError('Source and destination must be separate')
    if destination.exists():
        raise ValueError(f'Destination already exists; choose a new name: {destination}')
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    hashes = manifest.get('files')
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError('Source manifest has no file hashes')
    files = {}
    for name, expected in hashes.items():
        relative = Path(name)
        path = source / relative
        if relative.is_absolute() or '..' in relative.parts or path.is_symlink() or not path.resolve().is_relative_to(source):
            raise ValueError(f'Unsafe manifest path: {name}')
        if not path.is_file() or sha(path) != expected:
            raise ValueError(f'Source result checksum mismatch: {name}')
        files[name] = expected
    files['manifest.json'] = sha(source / 'manifest.json')
    # Nothing is written until all declared source files have passed verification.
    destination.mkdir(parents=True, exist_ok=False)
    for name, expected in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, path)
        if sha(path) != expected or sha(source / name) != expected:
            raise ValueError(f'File changed during export: {name}')
    receipt = dict(exported_at=datetime.now(ZoneInfo('Asia/Saigon')).isoformat(),
                   source=str(source), destination=str(destination), verified_files=files,
                   original_manifest_preserved=True,
                   note='Artifact copy of the original run; input paths/hashes still describe that run.')
    (destination / 'export_receipt.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'EXPORTED {len(files)} verified files: {destination}', flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--name', required=True, help='New directory name under exp_d/results')
    args = parser.parse_args()
    if not args.name or Path(args.name).name != args.name or args.name in ('.', '..') or any(c in args.name for c in '/\\:'):
        raise ValueError('Export name must be a single directory name')
    export_bundle(args.source, OWNER / 'results' / args.name)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print(f'EXPORT FAILED: {error}', file=sys.stderr)
        raise SystemExit(1)
