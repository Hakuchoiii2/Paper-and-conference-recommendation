"""
Module: data_loader.py
Nhiệm vụ:
  1. Đọc dữ liệu phân chia Train (602 bài) và Test (186 bài) từ thư mục temporal split chuẩn.
  2. Nạp dữ liệu 5 Facets đã trích xuất từ Exp A (hỗ trợ chuyển đổi linh hoạt giữa các LLM Extractor).
  3. Ghép nối (Merge) văn bản gốc, nhãn hội nghị và 5 facets qua khóa duy nhất 'paper_id'.
  4. Đóng gói thành cấu trúc dữ liệu chuẩn cho mô hình khuyến nghị.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Danh sách 5 facets chuẩn mực của hệ thống
FACET_KEYS = ("problem", "task", "method", "dataset", "contribution")


def get_repo_root() -> Path:
    """Xác định đường dẫn thư mục gốc của repository."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "configs").exists() and (parent / "data").exists():
            return parent
    return current.parents[2]


def read_jsonl(file_path: Path) -> List[Dict]:
    """Đọc tệp tin JSONL thành danh sách các dictionary."""
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Lỗi cú pháp JSON tại {file_path}:{line_num} - {e}")
    return records


def load_facets(facets_path: Path) -> Dict[str, Dict[str, List[str]]]:
    """
    Nạp dữ liệu 5 facets từ file jsonl của Exp A.
    Trả về: Dict[paper_id -> {problem: [...], task: [...], method: [...], dataset: [...], contribution: [...]}]
    """
    facets_path = Path(facets_path)
    if not facets_path.exists():
        raise FileNotFoundError(f"Không tìm thấy tệp 5 facets tại: {facets_path}")

    paper_facets = {}
    records = read_jsonl(facets_path)
    for r in records:
        pid = r.get("paper_id")
        if not pid:
            continue
        paper_facets[pid] = {
            f: r.get(f, []) if isinstance(r.get(f), list) else [str(r.get(f))]
            for f in FACET_KEYS
        }
    return paper_facets


def load_dataset(
    split_dir: Path,
    facets_path: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> Tuple[List[Dict], List[Dict], Dict[str, Dict], Dict[str, int]]:
    """
    Nạp toàn bộ tập Train, Test, Catalog hội nghị và nhãn số học.

    Args:
        split_dir: Đường dẫn thư mục chứa train.jsonl, test.jsonl, conference_catalog.jsonl
        facets_path: Đường dẫn tệp 5 facets (Exp A). Nếu None, tự động trỏ về facets_silver.jsonl mặc định.
        repo_root: Thư mục gốc repo.

    Returns:
        (train_papers, test_papers, conference_catalog, label_map)
    """
    if repo_root is None:
        repo_root = get_repo_root()

    split_dir = Path(split_dir)
    if not split_dir.is_absolute():
        split_dir = repo_root / split_dir

    if facets_path is None:
        facets_path = repo_root / "data/exp_a/generated/facets_silver.jsonl"
    else:
        facets_path = Path(facets_path)
        if not facets_path.is_absolute():
            facets_path = repo_root / facets_path

    # 1. Đọc nhãn và catalog
    train_file = split_dir / "train.jsonl"
    test_file = split_dir / "test.jsonl"
    catalog_file = split_dir / "conference_catalog.jsonl"
    label_map_file = split_dir / "label_map.json"

    for p in (train_file, test_file, catalog_file, label_map_file):
        if not p.exists():
            raise FileNotFoundError(f"Thiếu tệp dữ liệu cần thiết: {p}")

    train_raw = read_jsonl(train_file)
    test_raw = read_jsonl(test_file)
    catalog_raw = read_jsonl(catalog_file)
    with open(label_map_file, "r", encoding="utf-8") as f:
        label_map = json.load(f)

    catalog = {r["conference_id"]: r for r in catalog_raw}

    # 2. Nạp 5 facets từ Exp A
    facets_dict = load_facets(facets_path)

    # 3. Ghép nối (Merge) văn bản gốc và 5 facets
    def enrich_papers(raw_list: List[Dict], split_name: str) -> List[Dict]:
        enriched = []
        for r in raw_list:
            pid = r["paper_id"]
            facets = facets_dict.get(
                pid,
                {f: [] for f in FACET_KEYS}
            )
            item = {
                "paper_id": pid,
                "title": r.get("title", "").strip(),
                "abstract": r.get("abstract", "").strip(),
                "year": r.get("year"),
                "conference_id": r.get("conference_id"),
                "conference_name": r.get("conference_name"),
                "label_index": r.get("label_index"),
                "split": split_name,
                "facets": facets,
            }
            enriched.append(item)
        return enriched

    train_papers = enrich_papers(train_raw, "train")
    test_papers = enrich_papers(test_raw, "test")

    return train_papers, test_papers, catalog, label_map
