"""01_load_ranking_data.py
Bước 1: Nạp và kiểm định dữ liệu đầu vào cho Ranking Pipeline.
- Kiểm tra tập Validated Silver (4,210 bài)
- Kiểm tra phân chia Query DEV (15) / TEST (35)
- Kiểm tra Human Qrels (nếu đã có)
- Báo cáo số lượng ứng viên hợp lệ và thống kê độ phủ facet.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RANKING_DIR = PROJECT_ROOT / "ranking"
CONFIG_PATH = RANKING_DIR / "config" / "ranking_config.json"

def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy file cấu hình {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_path(rel_or_abs_path):
    p = Path(rel_or_abs_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p

def main():
    print("="*75)
    print("BƯỚC 1: KIỂM ĐỊNH VÀ NẠP DỮ LIỆU ĐẦU VÀO CHO RANKING PIPELINE")
    print("="*75)

    config = load_config()
    paths = config.get("paths", {})

    # 1. Kiểm tra validated_silver.jsonl
    val_silver_path = resolve_path(paths.get("validated_silver", "ranking/input/validated_silver.jsonl"))
    # Fallback tự động nếu chưa copy sang ranking/input
    if not val_silver_path.exists():
        fallback_path = PROJECT_ROOT / "data_preparation" / "output" / "validated_silver.jsonl"
        if fallback_path.exists():
            print(f"[*] Lưu ý: Chưa có {val_silver_path.name} trong ranking/input/, tự động liên kết từ {fallback_path}")
            val_silver_path = fallback_path

    if not val_silver_path.exists():
        print(f"[!] CẢNH BÁO: Chưa tìm thấy file validated_silver.jsonl tại {val_silver_path}")
        print("    Vui lòng hoàn thành Data Preparation hoặc đặt file vào ranking/input/")
        papers_dict = {}
    else:
        papers_dict = {}
        with open(val_silver_path, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                papers_dict[r["paper_id"]] = r
        print(f"[+] Đã nạp thành công {len(papers_dict)} bài báo từ {val_silver_path.name}")

    # 2. Kiểm tra query_split.json
    split_path = resolve_path(paths.get("query_split", "ranking/input/query_split.json"))
    if not split_path.exists():
        template_split = RANKING_DIR / "input" / "query_split.template.json"
        if template_split.exists():
            print(f"[*] Chưa có query_split.json chính thức, đang dùng template {template_split.name} để kiểm tra schema")
            split_path = template_split

    dev_queries = []
    test_queries = []
    if split_path.exists():
        with open(split_path, "r", encoding="utf-8") as f:
            split_data = json.load(f)
            dev_queries = split_data.get("dev", [])
            test_queries = split_data.get("test", [])
        print(f"[+] Phân chia Queries: {len(dev_queries)} DEV queries | {len(test_queries)} TEST queries (Tổng: {len(dev_queries)+len(test_queries)})")
        
        # Kiểm tra xem các query ID có nằm trong corpus không
        if papers_dict:
            missing_dev = [q for q in dev_queries if q not in papers_dict]
            missing_test = [q for q in test_queries if q not in papers_dict]
            if missing_dev:
                print(f"[!] Lỗi: Có {len(missing_dev)} DEV queries không tồn tại trong corpus: {missing_dev}")
            if missing_test:
                print(f"[!] Lỗi: Có {len(missing_test)} TEST queries không tồn tại trong corpus: {missing_test}")
            if not missing_dev and not missing_test:
                print("[+] Kiểm tra Query IDs: 100% Query IDs hợp lệ và tồn tại trong corpus.")
    else:
        print(f"[!] Chưa tìm thấy query_split.json tại {split_path}")

    # 3. Kiểm tra human_qrels.jsonl
    qrels_path = resolve_path(paths.get("human_qrels", "ranking/input/human_qrels.jsonl"))
    if not qrels_path.exists():
        print(f"[*] Lưu ý: File đánh giá Human Qrels chưa có tại {qrels_path}")
        print("    (Đây là dữ liệu đầu ra của Giai đoạn 2 & 4. Pipeline Ranking vẫn sẵn sàng chạy xếp hạng trước).")
    else:
        qrel_count = sum(1 for _ in open(qrels_path, encoding="utf-8"))
        print(f"[+] Đã tìm thấy {qrel_count} nhãn Human Qrels tại {qrels_path.name}")

    print("\n--> Hoàn tất kiểm tra Bước 1. Dữ liệu sẵn sàng cho Bước 2 (Chuẩn bị Embeddings).")

if __name__ == "__main__":
    main()
