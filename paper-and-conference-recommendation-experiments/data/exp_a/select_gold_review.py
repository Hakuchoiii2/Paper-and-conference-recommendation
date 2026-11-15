"""Choose the most complete A annotations for independent HUMAN gold review."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))

from experiment_io import FACETS, ROOT, load_silver, project_path
from build_corpus import write_jsonl
from download_sources import sha256, write_json
from validate_all import require


def select(root, source='data/exp_a/generated', output='data/exp_a/ground_truth/gold_review',
           count=400, dry_run=False, allow_partial=False):
    root = Path(root)
    require(type(count) is int and count > 0, 'Review count must be a positive integer')
    require(not allow_partial or dry_run, 'Partial A is allowed only for a read-only preview')
    papers, facets, metadata, source_manifest = load_silver(root, source, complete=not allow_partial)
    ranked, excluded = [], {}
    for pid, row in facets.items():
        note = metadata[pid]
        if pid == 'P000001':
            excluded[pid] = 'prompt_development_example'
        elif note.get('fallback_used') or note.get('validation_errors'):
            excluded[pid] = 'fallback_or_quality_errors'
        elif not any(row[facet] for facet in FACETS):
            excluded[pid] = 'no_extracted_facets'
        else:
            nonempty = sum(bool(row[facet]) for facet in FACETS)
            concepts = sum(len(row[facet]) for facet in FACETS)
            ranked.append((pid, nonempty, concepts))
    ranked.sort(key=lambda row: (-row[1], -row[2], row[0]))
    require(len(ranked) >= count, f'Review shortfall: requested {count}, only {len(ranked)} eligible papers')
    selected = ranked[:count]
    directory = project_path(root, output)
    report = dict(contract_version='1.0', dataset_kind='real', tier='review_queue',
                  review_status='pending', requested_count=count, count=len(selected),
                  selected_ids=[pid for pid, _, _ in selected], eligible_count=len(ranked),
                  excluded_ids=excluded, input_status=source_manifest['status'],
                  selection_policy='nonempty_facets_desc_supported_concepts_desc_paper_id_asc_v1',
                  selection_bias='Purposefully favors complete clean silver; not representative of the whole corpus.',
                  facet_completeness={str(n): sum(item[1] == n for item in selected) for n in range(1, 6)},
                  source_manifest_sha256=sha256(project_path(root, source) / 'manifest.json'),
                  selector_sha256=sha256(Path(__file__)))
    if not dry_run:
        require(not directory.exists() or not any(directory.iterdir()),
                'Review queue already exists; use a new output directory to avoid overwriting human work')
        write_jsonl(directory / 'review_papers.jsonl', [dict(paper_id=pid, title=papers[pid]['title'],
                    abstract=papers[pid]['abstract']) for pid, _, _ in selected])
        write_jsonl(directory / 'review_annotations.jsonl', [dict(paper_id=pid, reviewer=None,
                    review_status='pending', facets={facet: [] for facet in FACETS}) for pid, _, _ in selected])
        write_jsonl(directory / 'silver_reference.jsonl', [facets[pid] for pid, _, _ in selected])
        write_jsonl(directory / 'selection_ranking.jsonl', [dict(paper_id=pid, rank=rank,
                    nonempty_facets=filled, supported_concepts=concepts)
                    for rank, (pid, filled, concepts) in enumerate(selected, 1)])
        report['files'] = {name: sha256(directory / name) for name in
                           ('review_papers.jsonl', 'review_annotations.jsonl', 'silver_reference.jsonl',
                            'selection_ranking.jsonl')}
        write_json(directory / 'manifest.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='data/exp_a/generated')
    parser.add_argument('--output', default='data/exp_a/ground_truth/gold_review')
    parser.add_argument('--count', type=int, default=400)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--allow-partial', action='store_true', help='Only permitted with --dry-run')
    args = parser.parse_args()
    try:
        report = select(ROOT, args.source, args.output, args.count, args.dry_run, args.allow_partial)
        print(f"{'PREVIEW' if args.dry_run else 'PENDING HUMAN REVIEW'}: {report['count']} papers; "
              f"facet completeness={report['facet_completeness']}")
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'GOLD REVIEW SELECTION FAILED: {error}\n')


if __name__ == '__main__':
    main()
