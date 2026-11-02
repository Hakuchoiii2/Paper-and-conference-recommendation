"""
Module: run_benchmark.py
Script tự động hóa so sánh Đa Trích Xuất (Multi-LLM Extractor Benchmark):
Chạy thuật toán Gated 5-Facet k-NN Reranker trên đầu ra của nhiều mô hình LLM khác nhau:
  - Qwen-Local (4B/7B)
  - Gemini Flash API
  - Regex Heuristic Baseline
  ...
và tổng hợp vào một bảng ma trận kết quả duy nhất phục vụ viết bài báo.

Cách chạy (nhóm tự chạy khi sẵn sàng, Antigravity không tự chạy):
  python scripts/conference_recommendation/run_benchmark.py
  python scripts/conference_recommendation/run_benchmark.py --embedding-backend specter2
"""

import argparse
import csv
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.conference_recommendation.data_loader import get_repo_root, load_dataset
from scripts.conference_recommendation.feature_loader import FacetFeatureStore
from scripts.conference_recommendation.reranker import GatedFacetKNNReranker
from scripts.conference_recommendation.metrics import evaluate_predictions


def parse_args():
    parser = argparse.ArgumentParser(
        description="Chạy Benchmark so sánh nhiều LLM Extractor trên nhánh Khuyến nghị Hội nghị."
    )
    parser.add_argument(
        "--embedding-backend",
        choices=["tfidf", "specter2", "sentence_transformers", "precomputed"],
        default="tfidf",
        help="Backend embedding dùng để vector hóa 5 facets (mặc định: 'tfidf').",
    )
    parser.add_argument(
        "--output-dir",
        default="results/conference_recommendation",
        help="Thư mục xuất file tổng kết.",
    )
    return parser.parse_args()


def run_multi_extractor_benchmark():
    args = parse_args()
    repo_root = get_repo_root()
    split_dir = "data/conference_recommendation_dataset/5_mapping_reviewed/splits/temporal_2015_2016_2019"
    output_dir = repo_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Danh sách các bộ trích xuất LLM cần so sánh
    # (Nhóm bổ sung thêm tệp hoặc đường dẫn khi Quỳnh xuất các kết quả mới)
    extractors = [
        {
            "name": "Qwen-Local (Silver)",
            "path": repo_root / "data/exp_a/generated/facets_silver.jsonl",
        },
        {
            "name": "Gemini-1.5-Flash",
            "path": repo_root / "data/exp_a/generated/facets_gemini.jsonl",
        },
        {
            "name": "Regex-Rule-Baseline",
            "path": repo_root / "data/exp_a/generated/facets_regex.jsonl",
        },
    ]

    all_benchmark_rows = []

    print("=" * 85)
    print("      MULTI-LLM EXTRACTOR BENCHMARK: CONFERENCE RECOMMENDATION")
    print("=" * 85)
    print(f"[*] Embedding Backend: {args.embedding_backend}")
    print(f"[*] Thư mục xuất file: {output_dir}")

    for ext in extractors:
        ext_name = ext["name"]
        ext_path = ext["path"]

        if not ext_path.exists():
            print(f"\n[!] Bỏ qua '{ext_name}' (Chưa tìm thấy tệp tại: {ext_path})")
            continue

        print(f"\n[*] Đang chạy benchmark cho bộ trích xuất: {ext_name}...")
        train_papers, test_papers, catalog, _ = load_dataset(
            split_dir=split_dir,
            facets_path=ext_path,
            repo_root=repo_root,
        )
        candidate_venues = sorted(catalog.keys())
        ground_truth = {p["paper_id"]: p["conference_id"] for p in test_papers}

        feature_store = FacetFeatureStore(
            train_papers,
            test_papers,
            backend=args.embedding_backend,
        )

        reranker = GatedFacetKNNReranker(
            feature_store=feature_store,
            train_papers=train_papers,
            k=10,
            tau=0.45,
            kappa=10.0,
        )

        predictions = {}
        for p in test_papers:
            pid = p["paper_id"]
            predictions[pid] = reranker.predict(pid, candidate_venues)

        summary, _ = evaluate_predictions(
            predictions=predictions,
            ground_truth=ground_truth,
            candidate_venues=candidate_venues,
            top_k_list=[1, 3, 5],
        )

        row = {
            "Extractor": ext_name,
            "Algorithm": "Gated 5-Facet k-NN",
            "Embedding": args.embedding_backend,
            "Hit@1": f"{summary['hit@1'] * 100:.2f}%",
            "Hit@3": f"{summary['hit@3'] * 100:.2f}%",
            "Hit@5": f"{summary['hit@5'] * 100:.2f}%",
            "MRR": f"{summary['mrr']:.4f}",
            "Macro-Hit@3": f"{summary['macro_hit@3'] * 100:.2f}%",
            "Macro-MRR": f"{summary['macro_mrr']:.4f}",
        }
        all_benchmark_rows.append(row)

    if not all_benchmark_rows:
        print("\n[!] Chưa có file trích xuất nào khả dụng. Vui lòng kiểm tra lại data/exp_a/generated/")
        return

    # In kết quả
    print("\n" + "=" * 95)
    print("          BẢNG SO SÁNH CÁC LLM EXTRACTOR TRÊN KHUYẾN NGHỊ HỘI NGHỊ")
    print("=" * 95)
    fmt = "%-22s | %-12s | %7s | %7s | %7s | %7s | %11s"
    print(fmt % ("Extractor", "Embedding", "Hit@1", "Hit@3", "Hit@5", "MRR", "Macro-Hit@3"))
    print("-" * 95)
    for r in all_benchmark_rows:
        print(fmt % (r["Extractor"], r["Embedding"], r["Hit@1"], r["Hit@3"], r["Hit@5"], r["MRR"], r["Macro-Hit@3"]))
    print("=" * 95)

    # Xuất file CSV
    out_csv = output_dir / "multi_extractor_benchmark.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Extractor", "Algorithm", "Embedding", "Hit@1", "Hit@3", "Hit@5", "MRR", "Macro-Hit@3", "Macro-MRR"],
        )
        writer.writeheader()
        writer.writerows(all_benchmark_rows)

    print(f"\n[+] Đã xuất kết quả so sánh đa Extractor tại: {out_csv}")


if __name__ == "__main__":
    run_multi_extractor_benchmark()
