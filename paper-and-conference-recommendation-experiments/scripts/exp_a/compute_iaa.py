"""Compute Inter-Annotator Agreement (Fleiss' Kappa and Pairwise F1) on the 100 Common Core papers."""
import argparse
import itertools
import json
import math
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))

from build_corpus import normalize, read_jsonl

FACET_KEYS = ('problem', 'task', 'method', 'dataset', 'contribution')


def compute_fleiss_kappa(matrix):
    """
    Computes Fleiss' Kappa for a category assignment matrix.
    matrix: list of rows, each row is a list of counts of ratings per category.
    N: number of subjects (rows)
    n: number of raters per subject (sum of counts in each row)
    k: number of categories
    """
    N = len(matrix)
    if N == 0:
        return 0.0
    n = sum(matrix[0])
    k = len(matrix[0])

    # p_j: proportion of all assignments to category j
    p_j = [sum(matrix[i][j] for i in range(N)) / (N * n) for j in range(k)]

    # P_i: extent to which raters agree for subject i
    P_i = []
    for i in range(N):
        row_sum_sq = sum(matrix[i][j] ** 2 for j in range(k))
        P_i.append((row_sum_sq - n) / (n * (n - 1)))

    P_bar = sum(P_i) / N
    P_e_bar = sum(pj ** 2 for pj in p_j)

    if 1 - P_e_bar == 0:
        return 1.0  # Perfect agreement

    kappa = (P_bar - P_e_bar) / (1 - P_e_bar)
    return kappa


def extract_concept_set(facets, facet_key):
    """Extract normalized concept set from facet data."""
    val = facets.get(facet_key, [])
    concepts = []
    if facet_key == 'method' and isinstance(val, dict):
        concepts = val.get('proposed', []) + val.get('baseline', [])
    elif isinstance(val, list):
        concepts = val
    return set(normalize(c) for c in concepts if c and isinstance(c, str))


def evaluate_iaa(gold_dir):
    gold_dir = Path(gold_dir)
    manifest_path = gold_dir / 'manifest.json'
    if not manifest_path.exists():
        print(f"Manifest not found in {gold_dir}")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    common_pids = set(manifest.get('common_paper_ids', []))
    annotators = manifest.get('annotators', [])

    print(f"Loading annotations for {len(annotators)} annotators across {len(common_pids)} common core papers...")

    # Load annotations per annotator
    annotator_data = {}
    for filename in manifest.get('files', {}):
        if not filename.startswith('review_annotator_'):
            continue
        file_path = gold_dir / filename
        records = {r['paper_id']: r for r in read_jsonl(file_path) if r['paper_id'] in common_pids}
        # Check completeness
        reviewed = sum(r.get('review_status') == 'reviewed' for r in records.values())
        annotator_data[filename] = records
        print(f"  {filename}: {reviewed}/{len(common_pids)} reviewed")

    # Check if all annotators have reviewed common core
    total_reviewed = sum(
        sum(r.get('review_status') == 'reviewed' for r in recs.values())
        for recs in annotator_data.values()
    )
    expected_total = len(annotators) * len(common_pids)

    if total_reviewed < expected_total:
        print(f"\n[NOTICE]: Only {total_reviewed}/{expected_total} common core reviews completed.")
        print("    Fleiss' Kappa requires full completion of common core papers by all raters.")
        print("    Please complete all reviews in review_annotator_*.jsonl before generating official paper statistics.")
        return

    # 1. Fleiss' Kappa on Facet Presence/Absence
    # Subject: (paper_id, facet_key) -> Categories: [Absent (count), Present (count)]
    ratings_matrix = []
    for pid in sorted(common_pids):
        for f_key in FACET_KEYS:
            present_count = 0
            absent_count = 0
            for recs in annotator_data.values():
                c_set = extract_concept_set(recs[pid].get('facets', {}), f_key)
                if c_set:
                    present_count += 1
                else:
                    absent_count += 1
            ratings_matrix.append([absent_count, present_count])

    fleiss_k = compute_fleiss_kappa(ratings_matrix)

    # 2. Pairwise Concept-level F1 / Agreement
    annotator_keys = list(annotator_data.keys())
    pairwise_f1s = []
    pair_reports = {}

    for a1, a2 in itertools.combinations(annotator_keys, 2):
        f1_list = []
        for pid in common_pids:
            for f_key in FACET_KEYS:
                s1 = extract_concept_set(annotator_data[a1][pid].get('facets', {}), f_key)
                s2 = extract_concept_set(annotator_data[a2][pid].get('facets', {}), f_key)
                if not s1 and not s2:
                    continue
                intersection = len(s1 & s2)
                f1 = (2 * intersection) / (len(s1) + len(s2)) if (len(s1) + len(s2)) > 0 else 1.0
                f1_list.append(f1)
        avg_pair_f1 = sum(f1_list) / len(f1_list) if f1_list else 1.0
        pairwise_f1s.append(avg_pair_f1)
        pair_reports[f"{a1} <-> {a2}"] = avg_pair_f1

    mean_pairwise_f1 = sum(pairwise_f1s) / len(pairwise_f1s) if pairwise_f1s else 1.0

    print("\n" + "=" * 60)
    print("INTER-ANNOTATOR AGREEMENT (IAA) REPORT (100 COMMON PAPERS)")
    print("=" * 60)
    print(f"Fleiss' Generalized Kappa (Facet Presence): kappa = {fleiss_k:.4f}")
    if fleiss_k >= 0.81:
        print("  -> Interpretation: Almost Perfect Agreement")
    elif fleiss_k >= 0.61:
        print("  -> Interpretation: Substantial Agreement (Meets Q1 Standards)")
    elif fleiss_k >= 0.41:
        print("  -> Interpretation: Moderate Agreement")
    else:
        print("  -> Interpretation: Low Agreement - Guideline clarification required")

    print(f"\nMean Pairwise Concept-level F1: {mean_pairwise_f1:.4f}")
    print("\nPairwise Breakdown:")
    for pair, score in pair_reports.items():
        print(f"  {pair}: {score:.4f}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gold-dir', default='data/exp_a/ground_truth/gold_600')
    args = parser.parse_args()
    evaluate_iaa(args.gold_dir)


if __name__ == '__main__':
    main()
