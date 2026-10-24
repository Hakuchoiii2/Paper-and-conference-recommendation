"""Partition a 600-paper Gold Set for 5 annotators: 100 common core + 500 disjoint."""
import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

from build_corpus import read_jsonl, write_jsonl
from download_sources import sha256, write_json
from validate_all import require

FACET_TEMPLATE = {
    "problem": [],
    "task": [],
    "method": {
        "proposed": [],
        "baseline": []
    },
    "dataset": [],
    "contribution": []
}

ANNOTATORS = [
    ("annotator_1_kien", "Kien"),
    ("annotator_2_khai", "Khai"),
    ("annotator_3_phi", "Phi"),
    ("annotator_4", "Annotator_4"),
    ("annotator_5", "Annotator_5"),
]


def split_sentences(abstract):
    """Splits an abstract into sentences matching build_exp_a convention."""
    examples = [match.span() for match in re.finditer(r'\be\s*\.\s*g\s*\.', abstract, re.IGNORECASE)]
    sentences, cursor = [], 0
    for boundary in re.finditer(r'(?<=[.!?])\s+', abstract):
        if any(start <= boundary.start() <= end for start, end in examples):
            continue
        sentences.append(abstract[cursor:boundary.start()].strip())
        cursor = boundary.end()
    sentences.append(abstract[cursor:].strip())
    return [s for s in sentences if s]


def prepare_context_paper(paper):
    """Prepare paper text with sentence IDs for human review."""
    sentences = split_sentences(paper['abstract'])
    options = {'T0': paper['title']}
    options.update({f'A{i}': s for i, s in enumerate(sentences)})
    return {
        'paper_id': paper['paper_id'],
        'title': paper['title'],
        'year': paper.get('year'),
        'sentences': options
    }


def select_and_partition(root, count=600, common_count=100, output_dir='data/exp_a/ground_truth/gold_600'):
    root = Path(root)
    corpus_path = root / 'data/processed/papers.jsonl'
    require(corpus_path.exists(), f'Corpus not found at {corpus_path}')
    all_papers = read_jsonl(corpus_path)
    paper_map = {p['paper_id']: p for p in all_papers}

    # If silver exists, prioritize clean papers
    silver_meta_path = root / 'data/exp_a/generated/annotation_metadata.jsonl'
    eligible_pids = []
    if silver_meta_path.exists():
        metadata = {r['paper_id']: r for r in read_jsonl(silver_meta_path)}
        for p in all_papers:
            pid = p['paper_id']
            if pid == 'P000001':
                continue
            meta = metadata.get(pid, {})
            if not meta.get('fallback_used') and not meta.get('validation_errors'):
                eligible_pids.append(pid)
    else:
        eligible_pids = [p['paper_id'] for p in all_papers if p['paper_id'] != 'P000001']

    require(len(eligible_pids) >= count, f'Need {count} eligible papers, found {len(eligible_pids)}')
    selected_pids = eligible_pids[:count]

    # Partitioning: First common_count are common to all 5
    common_pids = selected_pids[:common_count]
    remaining_pids = selected_pids[common_count:]

    disjoint_count = (count - common_count) // len(ANNOTATORS)
    require(disjoint_count * len(ANNOTATORS) == (count - common_count), 'Disjoint count must divide evenly')

    partitions = {}
    for idx, (file_id, reviewer_name) in enumerate(ANNOTATORS):
        start = idx * disjoint_count
        end = start + disjoint_count
        assigned_disjoint = remaining_pids[start:end]
        # Full workload for this reviewer = common + assigned disjoint
        reviewer_pids = common_pids + assigned_disjoint
        partitions[file_id] = {
            'reviewer': reviewer_name,
            'pids': reviewer_pids,
            'disjoint_pids': assigned_disjoint,
        }

    out_path = root / output_dir
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Write papers context
    context_papers = [prepare_context_paper(paper_map[pid]) for pid in selected_pids]
    write_jsonl(out_path / 'review_papers_context.jsonl', context_papers)

    # 2. Write individual reviewer files
    for file_id, data in partitions.items():
        file_path = out_path / f'review_{file_id}.jsonl'
        records = [
            {
                'paper_id': pid,
                'reviewer': data['reviewer'],
                'review_status': 'pending',
                'is_common_core': (pid in common_pids),
                'facets': json.loads(json.dumps(FACET_TEMPLATE))
            }
            for pid in data['pids']
        ]
        write_jsonl(file_path, records)

    # 3. Write manifest
    manifest = {
        'version': '2.0',
        'tier': 'human_gold_set',
        'total_papers': count,
        'common_core_count': common_count,
        'disjoint_per_annotator': disjoint_count,
        'annotators': [a[1] for a in ANNOTATORS],
        'common_paper_ids': common_pids,
        'files': {
            f'review_{file_id}.jsonl': sha256(out_path / f'review_{file_id}.jsonl')
            for file_id in partitions
        }
    }
    manifest['files']['review_papers_context.jsonl'] = sha256(out_path / 'review_papers_context.jsonl')
    write_json(out_path / 'manifest.json', manifest)

    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=600)
    parser.add_argument('--common', type=int, default=100)
    parser.add_argument('--output', default='data/exp_a/ground_truth/gold_600')
    args = parser.parse_args()

    manifest = select_and_partition(PROJECT_ROOT, count=args.count, common_count=args.common, output_dir=args.output)
    print(f"SUCCESS: Partitioned {manifest['total_papers']} papers into {args.output}")
    print(f"Common Core: {manifest['common_core_count']} papers (evaluated by all {len(manifest['annotators'])} annotators)")
    print(f"Workload per annotator: {manifest['common_core_count'] + manifest['disjoint_per_annotator']} papers")


if __name__ == '__main__':
    main()
