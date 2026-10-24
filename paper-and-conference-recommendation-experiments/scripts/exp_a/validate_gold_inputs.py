"""Pre-flight Validator for Annotator JSONL files in VSCode."""
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

from build_corpus import read_jsonl

FACET_KEYS = ('problem', 'task', 'method', 'dataset', 'contribution')


def validate_file(file_path, context_file=None):
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"ERROR: File {file_path} not found.")
        sys.exit(1)

    context_map = {}
    if context_file and Path(context_file).exists():
        for row in read_jsonl(context_file):
            context_map[row['paper_id']] = row

    errors = []
    warnings = []
    total_lines = 0
    reviewed_count = 0
    pending_count = 0

    with file_path.open('r', encoding='utf-8') as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            total_lines += 1

            # 1. JSON parsing
            try:
                data = json.loads(line)
            except Exception as e:
                errors.append(f"Line {line_no}: Malformed JSON - {e}")
                continue

            # 2. Schema check
            for req in ('paper_id', 'reviewer', 'review_status', 'facets'):
                if req not in data:
                    errors.append(f"Line {line_no}: Missing required key '{req}'")

            pid = data.get('paper_id')
            status = data.get('review_status')
            facets = data.get('facets', {})

            if status == 'pending':
                pending_count += 1
                continue
            elif status == 'reviewed':
                reviewed_count += 1
            else:
                errors.append(f"Line {line_no} ({pid}): Invalid review_status '{status}'. Must be 'pending' or 'reviewed'.")

            # 3. Facets validation
            for f_key in FACET_KEYS:
                if f_key not in facets:
                    errors.append(f"Line {line_no} ({pid}): Missing facet '{f_key}' in 'facets'")

            # Check method structure
            method = facets.get('method', {})
            if isinstance(method, dict):
                for m_sub in ('proposed', 'baseline'):
                    if m_sub not in method or not isinstance(method[m_sub], list):
                        errors.append(f"Line {line_no} ({pid}): method.{m_sub} must be a list of strings")
            elif isinstance(method, list):
                warnings.append(f"Line {line_no} ({pid}): 'method' is a flat list. Recommended: {{'proposed': [...], 'baseline': [...]}}")
            else:
                errors.append(f"Line {line_no} ({pid}): 'method' must be a dict or list")

            # Check concepts
            all_concepts = []
            for f_key, val in facets.items():
                concept_list = []
                if f_key == 'method' and isinstance(val, dict):
                    concept_list = val.get('proposed', []) + val.get('baseline', [])
                elif isinstance(val, list):
                    concept_list = val

                for c in concept_list:
                    if not isinstance(c, str) or not c.strip():
                        errors.append(f"Line {line_no} ({pid}): Empty or non-string concept in facet '{f_key}'")
                        continue
                    clean_c = c.strip()
                    if clean_c in all_concepts:
                        warnings.append(f"Line {line_no} ({pid}): Duplicate concept '{clean_c}' across facets")
                    all_concepts.append(clean_c)

                    # Substring check with context
                    if pid in context_map:
                        full_text = context_map[pid]['title'] + " " + " ".join(context_map[pid]['sentences'].values())
                        if clean_c.lower() not in full_text.lower():
                            warnings.append(f"Line {line_no} ({pid}): Concept '{clean_c}' not found verbatim in Title/Abstract")

    print("=" * 60)
    print(f"VALIDATION REPORT: {file_path.name}")
    print(f"Total Papers Assigned: {total_lines}")
    print(f"Completed (Reviewed):  {reviewed_count} ({reviewed_count / total_lines * 100:.1f}%)" if total_lines else "0")
    print(f"Remaining (Pending):   {pending_count}")
    print(f"Syntax/Schema Errors:  {len(errors)}")
    print(f"Warnings (Soft checks):{len(warnings)}")
    print("=" * 60)

    if errors:
        print("\n[CRITICAL ERRORS - MUST FIX]:")
        for err in errors[:15]:
            print(f"  [ERROR] {err}")
        if len(errors) > 15:
            print(f"  ... and {len(errors) - 15} more errors.")
        sys.exit(1)

    if warnings:
        print("\n[WARNINGS - REVIEW RECOMMENDED]:")
        for warn in warnings[:10]:
            print(f"  [WARN]  {warn}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more warnings.")

    print("\n[PASSED] PRE-FLIGHT VALIDATION COMPLETED SUCCESSFULLY!")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', required=True, help='Path to reviewer JSONL file')
    parser.add_argument('--context', default='data/exp_a/ground_truth/gold_600/review_papers_context.jsonl',
                        help='Path to review_papers_context.jsonl')
    args = parser.parse_args()
    validate_file(args.file, args.context)


if __name__ == '__main__':
    main()
