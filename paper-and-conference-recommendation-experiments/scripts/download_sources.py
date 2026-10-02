"""Download official public data, preserve original bytes, and safely unpack it."""
import hashlib
import json
import tarfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'csfcube': {
        'version': 'v1.1',
        'homepage': 'https://github.com/iesl/CSFCube',
        'archive': 'csfcube-v1.1.zip',
        'url': 'https://codeload.github.com/iesl/CSFCube/zip/refs/tags/v1.1',
        'documents': {},
    },
    'scifact': {
        'version': 'official latest, identified by archive SHA-256',
        'homepage': 'https://github.com/allenai/scifact',
        'archive': 'data.tar.gz',
        'url': 'https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz',
        'documents': {
            'README.md': 'https://raw.githubusercontent.com/allenai/scifact/master/README.md',
            'LICENSE.md': 'https://raw.githubusercontent.com/allenai/scifact/master/LICENSE.md',
            'DATA_FORMAT.md': 'https://raw.githubusercontent.com/allenai/scifact/master/doc/data.md',
        },
    },
}


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    temporary.replace(path)


def fetch(url, target):
    if target.exists():
        return
    temporary = target.with_name(target.name + '.part')
    request = urllib.request.Request(url, headers={'User-Agent': 'DS300-data-bootstrap/1.0'})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open('wb') as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    temporary.replace(target)


def safe_relative(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
        raise ValueError(f'Unsafe archive path: {name}')
    parts = path.parts[1:]
    if not parts or any(part.startswith('._') or part == '__MACOSX' for part in parts):
        return None
    return Path(*parts)


def unpack(archive, destination):
    def save(name, content):
        relative = safe_relative(name)
        if relative is None:
            return
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != content:
            raise ValueError(f'Refusing to overwrite changed raw file: {target}')
        if not target.exists():
            target.write_bytes(content)

    if archive.suffix == '.zip':
        with zipfile.ZipFile(archive) as bundle:
            for info in bundle.infolist():
                if not info.is_dir():
                    if (info.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError(f'Archive symlink rejected: {info.filename}')
                    save(info.filename, bundle.read(info))
    else:
        with tarfile.open(archive, 'r:gz') as bundle:
            for member in bundle.getmembers():
                if member.isfile():
                    save(member.name, bundle.extractfile(member).read())
                elif member.issym() or member.islnk():
                    raise ValueError(f'Archive link rejected: {member.name}')


def main():
    for source, spec in SOURCES.items():
        directory = ROOT / 'data/raw' / source
        directory.mkdir(parents=True, exist_ok=True)
        old_path = directory / 'source_manifest.json'
        old = json.loads(old_path.read_text(encoding='utf-8')) if old_path.exists() else None
        archive = directory / spec['archive']
        fetch(spec['url'], archive)
        if old and old['archive_sha256'] != sha256(archive):
            raise ValueError(f'{source}: archive changed; preserve the old release and version a new source')
        unpack(archive, directory)
        for filename, url in spec['documents'].items():
            fetch(url, directory / filename)
        hashes = {p.relative_to(directory).as_posix(): sha256(p) for p in sorted(directory.rglob('*')) if p.is_file() and p.name != 'source_manifest.json'}
        if old and old['files'] != hashes:
            raise ValueError(f'{source}: raw files changed since the last download')
        write_json(old_path, dict(source=source, **spec, archive_sha256=sha256(archive), files=hashes))
        print(f'{source}: archive verified; {len(hashes)} preserved files')


if __name__ == '__main__':
    main()
