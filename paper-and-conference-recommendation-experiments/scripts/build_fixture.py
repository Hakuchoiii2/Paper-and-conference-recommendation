"""Create a reproducible real-paper smoke sample; never fabricate annotations."""
import argparse
import json
import random
from pathlib import Path
from build_corpus import read_jsonl, write_jsonl
from download_sources import ROOT, sha256, write_json


def build(root=ROOT, seed=None):
    config = json.loads((root / 'configs/data.json').read_text(encoding='utf-8'))
    seed = config['seed'] if seed is None else seed
    source = root / config['corpus']
    rows = sorted(read_jsonl(source), key=lambda row: row['paper_id'])
    count = config['fixture_size']
    if len(rows) < count:
        raise ValueError(f'Requires {count} real IT papers, found {len(rows)}')
    sample = sorted(random.Random(seed).sample(rows, count), key=lambda row: row['paper_id'])
    destination = root / 'data/fixtures'
    destination.mkdir(parents=True, exist_ok=True)
    write_jsonl(destination / 'papers.jsonl', sample)
    # No facets.jsonl until actual annotation. An absent file is not a fake all-empty annotation.
    write_json(destination / 'manifest.json', dict(contract_version=config['contract_version'], dataset_kind='real', purpose='smoke sample, not an evaluation split', seed=seed, generator_version='1.0', generator_sha256=sha256(Path(__file__)), input_corpus_sha256=sha256(source), record_counts=dict(papers=len(sample)), files={'papers.jsonl':sha256(destination / 'papers.jsonl')}, facets_status='not annotated; gold/silver absent'))
    print(f'Created {len(sample)} real papers with seed {seed}; no gold/silver labels generated.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int)
    args = parser.parse_args()
    build(seed=args.seed)


if __name__ == '__main__':
    main()
