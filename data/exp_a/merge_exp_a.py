"""Merge validated A parts; never publish incomplete or overlapping silver."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))

from experiment_io import FACETS, ROOT, annotation, load_silver, project_path
from build_corpus import write_jsonl
from download_sources import sha256, write_json
from validate_all import require


def merge(root, parts, output='data/exp_a/generated', dry_run=False):
    root = Path(root)
    require(parts, 'At least one A part is required')
    output_path = project_path(root, output)
    require(project_path(root, 'data/exp_a') in output_path.parents,
            'Merged output must stay inside experiment A')
    combined, metadata, sources = {}, {}, []
    common = None
    for part in sorted(parts):
        directory = project_path(root, part)
        require(directory != output_path and directory not in output_path.parents,
                'Merged output must not overwrite an A part')
        papers, rows, notes, manifest = load_silver(root, part, complete=False)
        provenance = dict(manifest['provenance'])
        provenance['config'] = {k: v for k, v in provenance['config'].items()
                                if k not in ('output_dir', 'paper_range', 'cache_dir')}
        if common is None:
            common = provenance
            merged_config = dict(max_new_tokens=2048, max_attempts=3,
                                 **manifest['provenance']['config'])
        require(provenance == common, f'{part}: annotation provenance/config differs from other parts')
        start, end = annotation.paper_bounds(manifest['provenance']['config'], len(papers))
        expected = set(list(papers)[start-1:end])
        require(set(rows) == expected, f'{part}: missing coverage inside assigned paper_range')
        require(not (combined.keys() & rows.keys()), f'{part}: overlapping/duplicate paper IDs')
        combined.update(rows)
        metadata.update(notes)
        sources.append(dict(path=directory.relative_to(root.resolve()).as_posix(),
                            manifest_sha256=sha256(directory / 'manifest.json'), count=len(rows)))
    missing = sorted(set(papers) - set(combined))
    require(not missing, f'A coverage incomplete: {len(missing)} missing IDs; cannot publish complete handoff')
    for field in ('model', 'model_revision'):
        identities = {row[field] for row in metadata.values() if row.get(field)}
        require(len(identities) <= 1, f'A parts use different runtime {field} identities/checkpoints')
    merged_config.update(output_dir=output_path.relative_to(root.resolve()).as_posix(), paper_range=[1, None])
    provenance = annotation.inputs(root, merged_config)[1]
    silver = [combined[pid] for pid in sorted(combined)]
    notes = [metadata[pid] for pid in sorted(metadata)]
    manifest = dict(contract_version='1.0', dataset_kind='real', tier='silver', status='complete',
                    count=len(silver), corpus_count=len(papers), missing_ids=[], failed_annotations={},
                    provenance=provenance, source_parts=sources, merge_version='1.0',
                    merge_sha256=sha256(Path(__file__)),
                    fallback_annotations={row['paper_id']: row['validation_errors'] for row in notes
                                          if row.get('fallback_used')},
                    coverage={facet: sum(bool(row[facet]) for row in silver) for facet in FACETS},
                    total_input_tokens=sum(row['usage'].get('input_tokens', 0) for row in notes),
                    total_output_tokens=sum(row['usage'].get('output_tokens', 0) for row in notes))
    if not dry_run:
        write_jsonl(output_path / 'facets_silver.jsonl', silver)
        write_jsonl(output_path / 'annotation_metadata.jsonl', notes)
        manifest['files'] = {name: sha256(output_path / name)
                             for name in ('facets_silver.jsonl', 'annotation_metadata.jsonl')}
        write_json(output_path / 'manifest.json', manifest)
        annotation.check_outputs(root, merged_config)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parts', nargs='+', default=[f'data/exp_a/generated/part_{i}' for i in range(1, 6)])
    parser.add_argument('--output', default='data/exp_a/generated')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        result = merge(ROOT, args.parts, args.output, args.dry_run)
        print(f"{'DRY RUN' if args.dry_run else 'COMPLETE'}: {result['count']}/{result['corpus_count']} silver papers")
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'A MERGE FAILED: {error}\n')


if __name__ == '__main__':
    main()
