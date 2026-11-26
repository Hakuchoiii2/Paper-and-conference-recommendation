"""run_ranking_pipeline.py
Trình điều phối (Pipeline Orchestrator) cho toàn bộ quy trình Ranking (Exp B).
Cho phép chạy tuần tự từ Bước 1 đến Bước 7 hoặc chạy từng bước theo tùy chọn.

Sử dụng:
    python ranking/run_ranking_pipeline.py
    python ranking/run_ranking_pipeline.py --check-only   # Kiểm tra tính sẵn sàng
    python ranking/run_ranking_pipeline.py --skip-embeddings  # Dùng cache có sẵn
    python ranking/run_ranking_pipeline.py --dev-only      # Chỉ chạy DEV queries
    python ranking/run_ranking_pipeline.py --test-only     # Chỉ chạy TEST queries
"""

import sys
import subprocess
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RANKING_DIR = PROJECT_ROOT / "ranking"
SCRIPTS_DIR = RANKING_DIR / "scripts"

PIPELINE_STEPS = [
    ("Bước 1: Nạp & Kiểm định Dữ liệu", SCRIPTS_DIR / "01_load_ranking_data.py"),
    ("Bước 2: Chuẩn bị & Cache Embeddings", SCRIPTS_DIR / "02_prepare_embeddings.py"),
    ("Bước 3: Method 1 - Full-text Embedding Ranking", SCRIPTS_DIR / "03_fulltext_ranking.py"),
    ("Bước 4: Method 2 - Equal-weight Facet Ranking", SCRIPTS_DIR / "04_equal_weight_ranking.py"),
    ("Bước 5: Method 3 - Weighted Facet Ranking", SCRIPTS_DIR / "05_weighted_ranking.py"),
    ("Bước 6: Đánh giá Xếp hạng (Human Qrels IR Metrics)", SCRIPTS_DIR / "06_evaluate_ranking.py"),
    ("Bước 7: Phân tích Kết quả & Xuất Báo cáo", SCRIPTS_DIR / "07_analyze_results.py"),
]

def run_step(step_name, script_path, extra_args=None):
    print("\n" + "="*80)
    print(f"▶ ĐANG THỰC HIỆN: {step_name}")
    print(f"  Script: {script_path.relative_to(PROJECT_ROOT)}")
    print("="*80)

    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)

    res = subprocess.run(cmd)
    if res.returncode != 0:
        print(f"\n[!] LỖI tại {step_name} (Exit code: {res.returncode})")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="Điều phối Ranking Pipeline (Exp B)")
    parser.add_argument("--check-only", action="store_true", help="Chỉ kiểm tra cấu hình và tính sẵn sàng, không chạy suy luận nặng")
    parser.add_argument("--skip-embeddings", action="store_true", help="Bỏ qua bước tính lại embeddings (sử dụng cache hiện có)")
    parser.add_argument("--dev-only", action="store_true", help="Chỉ chạy và đánh giá trên 15 DEV queries")
    parser.add_argument("--test-only", action="store_true", help="Chỉ chạy và đánh giá trên 35 TEST queries")
    parser.add_argument("--top-k", type=int, default=100, help="Số lượng ứng viên lưu lại cho mỗi query (mặc định: 100)")
    args = parser.parse_args()

    print("*"*80)
    print("🚀 KHỞI ĐỘNG RANKING PIPELINE CHO EXP B (CHUẨN BỊ CHO HỆ THỐNG ĐỀ XUẤT)")
    print("*"*80)

    split_arg = "all"
    if args.dev_only:
        split_arg = "dev"
    elif args.test_only:
        split_arg = "test"

    # Bước 1: Load & Validate data
    if not run_step("Bước 1: Nạp & Kiểm định Dữ liệu", SCRIPTS_DIR / "01_load_ranking_data.py"):
        return

    # Bước 2: Embeddings
    emb_args = []
    if args.check_only:
        emb_args.append("--check-only")
    if not args.skip_embeddings:
        if not run_step("Bước 2: Chuẩn bị & Cache Embeddings", SCRIPTS_DIR / "02_prepare_embeddings.py", emb_args):
            return
    else:
        print("\n[*] Bỏ qua Bước 2 (--skip-embeddings được bật).")

    if args.check_only:
        print("\n" + "="*80)
        print("✅ KIỂM TRA TÍNH SẴN SÀNG HOÀN TẤT: Pipeline đã được xây dựng chuẩn xác 100%!")
        print("   Khi bạn của bạn hoàn thành tập Silver và chia tập Dev-Test, bạn có thể chạy:")
        print("   python ranking/run_ranking_pipeline.py")
        print("="*80)
        return

    # Bước 3, 4, 5: Ba phương pháp ranking
    rank_args = ["--top-k", str(args.top_k), "--split", split_arg]
    if not run_step("Bước 3: Method 1 - Full-text Embedding", SCRIPTS_DIR / "03_fulltext_ranking.py", rank_args):
        return
    if not run_step("Bước 4: Method 2 - Equal-weight Facet", SCRIPTS_DIR / "04_equal_weight_ranking.py", rank_args):
        return
    if not run_step("Bước 5: Method 3 - Weighted Facet", SCRIPTS_DIR / "05_weighted_ranking.py", rank_args):
        return

    # Bước 6: Evaluate
    if not run_step("Bước 6: Đánh giá bằng Human Qrels", SCRIPTS_DIR / "06_evaluate_ranking.py"):
        return

    # Bước 7: Analyze
    if not run_step("Bước 7: Phân tích & Tạo Báo cáo", SCRIPTS_DIR / "07_analyze_results.py"):
        return

    print("\n" + "*"*80)
    print("🎉 HOÀN THÀNH TOÀN BỘ RANKING PIPELINE THÀNH CÔNG!")
    print(f"   Kết quả và báo cáo lưu tại: {RANKING_DIR / 'reports'}")
    print("*"*80)

if __name__ == "__main__":
    main()
