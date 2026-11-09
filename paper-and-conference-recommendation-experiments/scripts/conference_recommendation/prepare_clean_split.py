"""
Script: prepare_clean_split.py
Tự động đối soát và loại trừ Data Leakage ở tầng Dữ liệu (Data Level).

Quy trình:
1. Đọc dữ liệu tập train & dev chính thức của khối Adapter (Exp A Gold 400).
2. Tự động tìm giao tập hợp (intersection) giữa tập Test Hội nghị và tập Train/Dev của Adapter.
3. Xuất ra thư mục split sạch (temporal_2015_2016_2019_clean) gồm 168 bài Test hoàn toàn độc lập (100% Unseen).
4. Ghi lại báo cáo kiểm định minh bạch (manifest.json) để phục vụ giải trình bài báo / đồ án.
"""

import json
import shutil
import sys
from pathlib import Path

# Thiết lập encoding chuẩn UTF-8
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parents[1]


def build_clean_split():
    # 1. Đường dẫn các tệp nguồn
    adapter_split_path = REPO_ROOT / "data/exp_a/final/reference/splits.json"
    raw_split_dir = REPO_ROOT / "data/conference_recommendation_dataset/5_mapping_reviewed/splits/temporal_2015_2016_2019"
    clean_split_dir = REPO_ROOT / "data/conference_recommendation_dataset/5_mapping_reviewed/splits/temporal_2015_2016_2019_clean"

    if not adapter_split_path.exists():
        raise FileNotFoundError(f"Không tìm thấy cấu hình split của Adapter tại: {adapter_split_path}")
    if not raw_split_dir.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục split gốc tại: {raw_split_dir}")

    # 2. Đọc tập train & valid của Adapter
    with open(adapter_split_path, "r", encoding="utf-8") as f:
        adapter_splits = json.load(f)

    adapter_train_ids = set(adapter_splits.get("train", []))
    adapter_valid_ids = set(adapter_splits.get("valid", []))
    adapter_supervised_ids = adapter_train_ids | adapter_valid_ids

    # 3. Đọc tập test gốc của Conference Recommendation
    test_file = raw_split_dir / "test.jsonl"
    with open(test_file, "r", encoding="utf-8") as f:
        raw_test_records = [json.loads(line) for line in f if line.strip()]

    # 4. Tự động tìm các bài bị rò rỉ (thuộc tập train hoặc valid của Adapter)
    leak_train_records = [r for r in raw_test_records if r["paper_id"] in adapter_train_ids]
    leak_valid_records = [r for r in raw_test_records if r["paper_id"] in adapter_valid_ids]
    leak_ids = set(r["paper_id"] for r in leak_train_records + leak_valid_records)

    # 5. Lọc tập test sạch (Unseen 100%)
    clean_test_records = [r for r in raw_test_records if r["paper_id"] not in leak_ids]

    print("=" * 80)
    print("        TỰ ĐỘNG XỬ LÝ DATA LEAKAGE TẠI TẦNG DỮ LIỆU (DATA LEVEL)")
    print("=" * 80)
    print(f"[*] Nguồn kiểm soát Adapter Split: {adapter_split_path.relative_to(REPO_ROOT)}")
    print(f"[*] Tập Train của Adapter: {len(adapter_train_ids)} bài báo")
    print(f"[*] Tập Valid của Adapter: {len(adapter_valid_ids)} bài báo")
    print(f"[*] Tổng số bài test ban đầu: {len(raw_test_records)} bài báo")
    print("-" * 80)
    print(f"[!] Tự động phát hiện {len(leak_train_records)} bài trùng với tập Train của Adapter:")
    print(f"    -> {[r['paper_id'] for r in leak_train_records]}")
    print(f"[!] Tự động phát hiện {len(leak_valid_records)} bài trùng với tập Valid của Adapter:")
    print(f"    -> {[r['paper_id'] for r in leak_valid_records]}")
    print(f"[*] Tổng số bài loại trừ: {len(leak_ids)} bài báo")
    print(f"[+] Số bài test sạch sau xử lý: {len(clean_test_records)} bài báo (100% Unseen)")
    print("=" * 80)

    # 6. Tạo thư mục split sạch và ghi tệp
    clean_split_dir.mkdir(parents=True, exist_ok=True)

    # Ghi test.jsonl sạch
    clean_test_path = clean_split_dir / "test.jsonl"
    with open(clean_test_path, "w", encoding="utf-8") as f:
        for r in clean_test_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Sao chép các tệp còn lại (train.jsonl, catalog, label_map)
    for fname in ("train.jsonl", "conference_catalog.jsonl", "label_map.json"):
        src = raw_split_dir / fname
        dst = clean_split_dir / fname
        if src.exists():
            shutil.copy2(src, dst)

    # 7. Xuất manifest.json giải trình minh bạch
    manifest_info = {
        "split_name": "temporal_2015_2016_2019_clean",
        "description": "Tập chia dữ liệu sạch theo thời gian, loại bỏ hoàn toàn các bài báo từng xuất hiện trong tập huấn luyện/thẩm định của khối Adapter Exp A",
        "provenance": {
            "source_raw_split": str(raw_split_dir.relative_to(REPO_ROOT)),
            "adapter_splits_reference": str(adapter_split_path.relative_to(REPO_ROOT)),
        },
        "statistics": {
            "initial_test_count": len(raw_test_records),
            "excluded_train_leakage_count": len(leak_train_records),
            "excluded_train_leakage_ids": sorted([r["paper_id"] for r in leak_train_records]),
            "excluded_valid_leakage_count": len(leak_valid_records),
            "excluded_valid_leakage_ids": sorted([r["paper_id"] for r in leak_valid_records]),
            "clean_test_count": len(clean_test_records),
            "train_count": len(list(open(clean_split_dir / "train.jsonl", "r", encoding="utf-8"))),
        },
    }
    with open(clean_split_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_info, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Đã tạo thành công thư mục split sạch tại: {clean_split_dir.relative_to(REPO_ROOT)}")
    print(f"[+] Đã ghi kèm hồ sơ minh chứng Data Leakage: manifest.json")


if __name__ == "__main__":
    build_clean_split()
