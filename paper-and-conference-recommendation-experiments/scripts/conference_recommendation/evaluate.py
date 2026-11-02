"""
Module: evaluate.py
Script chính thực thi đánh giá và đo lường hiệu năng Hệ thống Khuyến nghị Hội nghị.
Hỗ trợ so sánh trực tiếp:
  - Proposed: Gated 5-Facet k-NN Reranker
  - Baseline 1: Whole-Text k-NN Reranker
  - Baseline 2: Flat 5-Facet k-NN Reranker
  - Baseline 3: Random Reranker

Hỗ trợ đa dạng Embedding Backends:
  - tfidf (mặc định)
  - specter2
  - sentence_transformers
  - precomputed

Cách chạy (nhóm tự chạy khi sẵn sàng, Antigravity không tự chạy):
  python scripts/conference_recommendation/evaluate.py --model all
  python scripts/conference_recommendation/evaluate.py --model gated_knn --facets-path data/exp_a/generated/facets_gemini.jsonl
  python scripts/conference_recommendation/evaluate.py --embedding-backend specter2
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List

# Nối đường dẫn nội bộ package
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.conference_recommendation.data_loader import get_repo_root, load_dataset
from scripts.conference_recommendation.feature_loader import FacetFeatureStore
from scripts.conference_recommendation.reranker import GatedFacetKNNReranker
from scripts.conference_recommendation.baselines import (
    WholeTextKNNReranker,
    FlatFacetKNNReranker,
    RandomReranker,
)
from scripts.conference_recommendation.metrics import evaluate_predictions


def parse_args():
    parser = argparse.ArgumentParser(
        description="Đánh giá mô hình Khuyến nghị Hội nghị Khoa học dựa trên 5 Facets."
    )
    parser.add_argument(
        "--config",
        default="configs/conference_recommendation/config.json",
        help="Đường dẫn tệp cấu hình JSON.",
    )
    parser.add_argument(
        "--facets-path",
        default=None,
        help="Đường dẫn ghi đè tệp 5 facets của Exp A (dùng khi so sánh giữa các LLM).",
    )
    parser.add_argument(
        "--model",
        choices=["gated_knn", "whole_text_knn", "flat_facet_knn", "random", "all"],
        default="all",
        help="Mô hình cần đánh giá (mặc định: 'all' để chạy toàn bộ bảng so sánh).",
    )
    parser.add_argument(
        "--embedding-backend",
        choices=["tfidf", "specter2", "sentence_transformers", "precomputed"],
        default=None,
        help="Loại backend vector hóa văn bản (mặc định lấy theo config, ví dụ: 'tfidf', 'specter2').",
    )
    parser.add_argument(
        "--embedding-model",
        default=None,
        help="Tên mô hình HuggingFace khi dùng sentence_transformers (mặc định: 'allenai/specter2_base').",
    )
    parser.add_argument(
        "--embedding-path",
        default=None,
        help="Đường dẫn file vector có sẵn (.npz hoặc .jsonl) khi dùng backend 'precomputed'.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        help="Số lượng láng giềng k trong thuật toán k-NN (mặc định lấy theo config).",
    )
    parser.add_argument(
        "--tau",
        type=float,
        default=None,
        help="Ngưỡng cắt của Cổng Ngữ Cảnh tau (mặc định lấy theo config).",
    )
    parser.add_argument(
        "--kappa",
        type=float,
        default=None,
        help="Độ dốc của Cổng Ngữ Cảnh kappa (mặc định lấy theo config).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Thư mục xuất báo cáo và tệp dự đoán (mặc định: results/conference_recommendation).",
    )
    return parser.parse_args()


def run_evaluation():
    args = parse_args()
    repo_root = get_repo_root()

    # 1. Đọc tệp cấu hình
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = repo_root / config_path

    if not config_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file config tại: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Ghi đè tham số nếu truyền qua CLI
    split_dir = cfg["dataset_split_dir"]
    facets_path = args.facets_path or cfg.get("facets_path")
    k = args.k or cfg.get("k_neighbors", 10)
    tau = args.tau or cfg.get("context_gate", {}).get("tau", 0.45)
    kappa = args.kappa or cfg.get("context_gate", {}).get("kappa", 10.0)
    facet_weights = cfg.get("facet_weights")

    embedding_backend = args.embedding_backend or cfg.get("feature_type", "tfidf")
    backend_config = {}
    if args.embedding_model:
        backend_config["model_name"] = args.embedding_model
    elif "embedding_model" in cfg:
        backend_config["model_name"] = cfg["embedding_model"]

    if args.embedding_path:
        backend_config["path"] = args.embedding_path
    elif "embedding_path" in cfg:
        backend_config["path"] = cfg["embedding_path"]

    output_dir = Path(args.output_dir or cfg.get("output_dir", "results/conference_recommendation"))
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 75)
    print("      HỆ THỐNG KHUYẾN NGHỊ HỘI NGHỊ KHOA HỌC DỰA TRÊN 5 FACETS")
    print("=" * 75)
    print(f"[*] Thư mục dữ liệu:      {split_dir}")
    print(f"[*] Tệp 5 Facets:          {facets_path}")
    print(f"[*] Embedding Backend:     {embedding_backend}")
    if backend_config:
        print(f"[*] Backend Config:        {backend_config}")
    print(f"[*] Cấu hình k-NN:         k={k}, tau={tau}, kappa={kappa}")
    print(f"[*] Thư mục kết quả:       {output_dir}")
    print("-" * 75)

    # 2. Nạp dữ liệu
    print("[*] Đang nạp và hợp nhất dữ liệu Train/Test...")
    train_papers, test_papers, catalog, label_map = load_dataset(
        split_dir=split_dir,
        facets_path=facets_path,
        repo_root=repo_root,
    )
    candidate_venues = sorted(catalog.keys())
    ground_truth = {p["paper_id"]: p["conference_id"] for p in test_papers}

    print(f"[+] Đã nạp thành công: {len(train_papers)} bài Train, {len(test_papers)} bài Test.")
    print(f"[+] Số hội nghị ứng viên (Candidate Venues): {len(candidate_venues)} hội nghị.")

    # 3. Xây dựng không gian vector
    print(f"[*] Đang khởi tạo không gian vector ({embedding_backend}) cho Toàn văn và 5 Facets...")
    feature_store = FacetFeatureStore(
        train_papers,
        test_papers,
        backend=embedding_backend,
        backend_config=backend_config,
    )
    print("[+] Hoàn thành vector hóa dữ liệu.")
    print("-" * 75)

    # 4. Khởi tạo danh sách mô hình cần đánh giá
    models_to_run = {}
    if args.model in ("gated_knn", "all"):
        models_to_run["Proposed: Gated 5-Facet k-NN"] = GatedFacetKNNReranker(
            feature_store=feature_store,
            train_papers=train_papers,
            k=k,
            tau=tau,
            kappa=kappa,
            weights=facet_weights,
        )
    if args.model in ("flat_facet_knn", "all"):
        models_to_run["Baseline: Flat 5-Facet k-NN"] = FlatFacetKNNReranker(
            feature_store=feature_store,
            train_papers=train_papers,
            k=k,
        )
    if args.model in ("whole_text_knn", "all"):
        models_to_run["Baseline: Whole-Text k-NN"] = WholeTextKNNReranker(
            feature_store=feature_store,
            train_papers=train_papers,
            k=k,
        )
    if args.model in ("random", "all"):
        models_to_run["Baseline: Random"] = RandomReranker()

    # 5. Chạy đánh giá từng mô hình trên 186 bài Test
    benchmark_results = []
    for model_name, model in models_to_run.items():
        print(f"[*] Đang chạy dự đoán cho: {model_name}...")
        predictions = {}
        for p in test_papers:
            pid = p["paper_id"]
            ranked_list = model.predict(pid, candidate_venues)
            predictions[pid] = ranked_list

        # Lưu kết quả dự đoán chi tiết
        safe_model_name = model_name.replace(" ", "_").replace(":", "").lower()
        pred_file = output_dir / f"predictions_{safe_model_name}.jsonl"
        with open(pred_file, "w", encoding="utf-8") as f:
            for pid, ranked_list in predictions.items():
                row = {
                    "paper_id": pid,
                    "ground_truth": ground_truth.get(pid),
                    "top_5": ranked_list[:5],
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        # Tính toán chỉ số
        summary, per_venue = evaluate_predictions(
            predictions=predictions,
            ground_truth=ground_truth,
            candidate_venues=candidate_venues,
            top_k_list=[1, 3, 5],
        )

        res_row = {
            "Model": model_name,
            "Embedding": embedding_backend,
            "Hit@1": f"{summary['hit@1'] * 100:.2f}%",
            "Hit@3": f"{summary['hit@3'] * 100:.2f}%",
            "Hit@5": f"{summary['hit@5'] * 100:.2f}%",
            "MRR": f"{summary['mrr']:.4f}",
            "Macro-Hit@3": f"{summary['macro_hit@3'] * 100:.2f}%",
            "Macro-MRR": f"{summary['macro_mrr']:.4f}",
        }
        benchmark_results.append(res_row)

    # 6. In bảng tổng kết ra màn hình terminal
    print("\n" + "=" * 95)
    print("                BẢNG TỔNG KẾT KẾT QUẢ BENCHMARK KHUYẾN NGHỊ HỘI NGHỊ")
    print("=" * 95)
    header = "%-30s | %-10s | %7s | %7s | %7s | %7s | %11s"
    print(header % ("Mô hình (Model)", "Embedding", "Hit@1", "Hit@3", "Hit@5", "MRR", "Macro-Hit@3"))
    print("-" * 95)
    for r in benchmark_results:
        print(
            header
            % (
                r["Model"],
                r["Embedding"],
                r["Hit@1"],
                r["Hit@3"],
                r["Hit@5"],
                r["MRR"],
                r["Macro-Hit@3"],
            )
        )
    print("=" * 95)

    # 7. Xuất file CSV kết quả
    summary_csv = output_dir / "benchmark_summary.csv"
    with open(summary_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Model",
                "Embedding",
                "Hit@1",
                "Hit@3",
                "Hit@5",
                "MRR",
                "Macro-Hit@3",
                "Macro-MRR",
            ],
        )
        writer.writeheader()
        writer.writerows(benchmark_results)

    print(f"\n[+] Đã xuất báo cáo tổng kết tại: {summary_csv}")
    print(f"[+] Đã lưu các tệp chi tiết từng bài test tại: {output_dir}")


if __name__ == "__main__":
    run_evaluation()
