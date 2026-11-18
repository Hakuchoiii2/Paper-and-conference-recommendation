"""run_pipeline.py
Script điều phối chạy tuần tự toàn bộ 9 bước của Data Preparation từ 01 đến 09:
01_validate_structure.py -> 02_split_source_sentences.py -> 03_generate_embeddings.py ->
04_align_evidence.py -> 05_qwen_semantic_audit.py -> 06_make_decisions.py ->
07_export_human_review.py -> 08_merge_validated_silver.py -> 09_evaluate_audit.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"

STEPS = [
    ("01_validate_structure.py", "Bước 1: Structural Validation"),
    ("02_split_source_sentences.py", "Bước 2A: Split Source Sentences"),
    ("03_generate_embeddings.py", "Bước 2B: Prepare Embeddings Readiness"),
    ("04_align_evidence.py", "Bước 2C: Evidence Alignment (all-MiniLM-L6-v2)"),
    ("05_qwen_semantic_audit.py", "Bước 3: Semantic Audit (Qwen3-4B-Instruct)"),
    ("06_make_decisions.py", "Bước 4: Automated Decisions (Mục 2.5)"),
    ("07_export_human_review.py", "Bước 5: Export Human Review Queue & QC Sample"),
    ("08_merge_validated_silver.py", "Bước 6: Merge Validated Silver & Rejected Facets"),
    ("09_evaluate_audit.py", "Mục 2.6: Gold Calibration & Held-out Evaluation")
]

def main():
    print("=" * 80)
    print("BẮT ĐẦU CHẠY TOÀN BỘ PIPELINE DATA PREPARATION THEO TRÌNH TỰ FILE DOCX")
    print("=" * 80)

    for script_name, desc in STEPS:
        script_path = SCRIPTS_DIR / script_name
        print(f"\n>>> ĐANG CHẠY: {desc} ({script_name})...")
        res = subprocess.run([sys.executable, str(script_path)], capture_output=False)
        if res.returncode != 0:
            print(f"[ERROR] Lỗi khi thực thi {script_name}! Pipeline tạm dừng.")
            sys.exit(res.returncode)

    print("\n" + "=" * 80)
    print("HOÀN THÀNH 100% TOÀN BỘ 9 BƯỚC DATA PREPARATION!")
    print("Tất cả file output đã sẵn sàng tại data_preparation/output/ và evaluation/")
    print("=" * 80)

if __name__ == "__main__":
    main()
