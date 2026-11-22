"""run_pooling_pipeline.py
Trình điều phối (Pipeline Orchestrator) cho toàn bộ quy trình Pooling & Final Ground Truth (Exp B).
Cho phép chạy tuần tự từ Bước 1 đến Bước 6 hoặc kiểm tra tính sẵn sàng.

Sử dụng:
    python pooling/run_pooling_pipeline.py
    python pooling/run_pooling_pipeline.py --check-only   # Kiểm tra tính sẵn sàng
"""

import sys
import subprocess
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
POOLING_DIR = PROJECT_ROOT / "pooling"
SCRIPTS_DIR = POOLING_DIR / "scripts"

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
        raise SystemExit(res.returncode)
    return True

def main():
    parser = argparse.ArgumentParser(description="Điều phối Pooling Pipeline (Exp B)")
    parser.add_argument("--check-only", action="store_true", help="Chỉ kiểm tra cấu hình và tính sẵn sàng, không chạy quy trình đầy đủ")
    parser.add_argument("--finalize", action="store_true", help="Publish qrels after all TEST pairs are graded")
    args = parser.parse_args()

    print("*"*80)
    print("🚀 KHỞI ĐỘNG POOLING & FINAL GROUND TRUTH PIPELINE (EXP B)")
    print("*"*80)

    # Bước 1: Merge Candidates
    if not run_step("Bước 1: Thu thập Candidate từ các nguồn", SCRIPTS_DIR / "01_merge_candidates.py"):
        return

    # Bước 2: Deduplication
    if not run_step("Bước 2: Deduplication (Khóa cặp Query, Candidate)", SCRIPTS_DIR / "02_deduplicate_pool.py"):
        return

    # Bước 3: Pool Validation
    if not run_step("Bước 3: Kiểm định Pool (Loại self-query & kiểm tra corpus)", SCRIPTS_DIR / "03_validate_pool.py"):
        return

    if args.check_only:
        print("\n" + "="*80)
        print("✅ KIỂM TRA TÍNH SẴN SÀNG HOÀN TẤT: Pipeline Pooling đã được thiết lập chuẩn 100%!")
        print("   Khi hoàn thành các bước Ranking, bạn có thể chạy:")
        print("   python pooling/run_pooling_pipeline.py")
        print("="*80)
        return

    # Bước 4: Export Human Review
    if not run_step("Bước 4: Chuẩn bị Hàng đợi Đánh giá Human Review", SCRIPTS_DIR / "04_export_human_review.py"):
        return

    if not args.finalize:
        print("TEST review queue is ready. Run again with --finalize after grading.")
        return

    # Bước 5: Merge Judgments
    if not run_step("Bước 5: Kiểm tra và Hợp nhất Đánh giá Con người", SCRIPTS_DIR / "05_merge_human_judgments.py"):
        return

    # Bước 6: Finalize Qrels & Report
    if not run_step("Bước 6: Khóa Qrels & Xuất Báo cáo Pooling", SCRIPTS_DIR / "06_finalize_qrels.py"):
        return

    print("\n" + "*"*80)
    print("🎉 HOÀN THÀNH QUY TRÌNH POOLING & FINAL GROUND TRUTH THÀNH CÔNG!")
    print(f"   Kết quả lưu tại: {POOLING_DIR / 'output'}")
    print("*"*80)

if __name__ == "__main__":
    main()
