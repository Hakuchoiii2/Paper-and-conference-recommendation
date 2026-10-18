"""Download one pinned SBERT checkpoint, entirely under data/exp_d/model/."""
from model_storage import configure
MODEL_ROOT = configure()

import argparse
import hashlib
import json
from pathlib import Path

REPO = 'sentence-transformers/all-MiniLM-L6-v2'
FILES = ['config.json', 'model.safetensors', 'tokenizer.json', 'tokenizer_config.json',
         'special_tokens_map.json', 'vocab.txt', 'modules.json',
         'config_sentence_transformers.json', 'sentence_bert_config.json',
         '1_Pooling/config.json', 'README.md']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', default='main')
    args = parser.parse_args()
    from huggingface_hub import HfApi, snapshot_download
    revision = HfApi(token=False).model_info(REPO, revision=args.revision).sha
    target = MODEL_ROOT / 'all-MiniLM-L6-v2'
    print(f'Downloading {REPO}@{revision} to {target}', flush=True)
    snapshot_download(REPO, revision=revision, local_dir=str(target), allow_patterns=FILES,
                      token=False, max_workers=2)
    for name in ('model.safetensors', 'tokenizer.json', 'modules.json', '1_Pooling/config.json'):
        if not (target / name).is_file():
            raise ValueError('Missing checkpoint file: ' + name)
    hashes = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(target.rglob('*')) if p.is_file() and '.cache' not in p.parts}
    manifest = dict(repo_id=REPO, revision=revision, local_dir=str(target), files=hashes,
                    format='safetensors', trust_remote_code=False,
                    bytes=sum((target / p).stat().st_size for p in hashes))
    (MODEL_ROOT / 'sbert_download_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('DOWNLOAD COMPLETE: ' + str(manifest['bytes']) + ' bytes', flush=True)


if __name__ == '__main__':
    main()
