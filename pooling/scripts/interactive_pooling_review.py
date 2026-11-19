"""interactive_pooling_review.py
Giao diện dòng lệnh tương tác (CLI) chấm điểm độ liên quan Human Relevance Judgment (Thang 0–3).
- Hiển thị song song thông tin Query Paper và Candidate Paper (Title, Abstract, 5 Facets).
- Hiển thị danh sách phương pháp đã tìm ra candidate (retrieved_by).
- Phím tắt nhanh:
    [0]: Không liên quan
    [1]: Liên quan nhẹ, giá trị hạn chế
    [2]: Có liên quan đáng kể
    [3]: Rất liên quan, tham khảo trực tiếp
    [S]: Bỏ qua (Skip)
    [P]: Quay lại (Previous)
    [X]: Lưu và thoát (Exit)
- Tự động lưu tiến độ tức thì vào pooling/human_review/human_judgments.jsonl sau mỗi lần bấm.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POOLING_DIR = PROJECT_ROOT / "pooling"
CONFIG_PATH = POOLING_DIR / "config" / "pooling_config.json"

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_path(p_str):
    p = Path(p_str)
    return p if p.is_absolute() else PROJECT_ROOT / p

def main():
    config = load_config()
    paths = config.get("paths", {})

    queue_file = resolve_path(paths.get("human_review_queue", "pooling/human_review/review_queue.jsonl"))
    judgments_file = resolve_path(paths.get("human_judgments", "pooling/human_review/human_judgments.jsonl"))

    if not queue_file.exists():
        print(f"[!] Lỗi: Chưa tìm thấy review_queue.jsonl tại {queue_file}")
        print("    Vui lòng chạy Bước 4: python pooling/scripts/04_export_human_review.py trước.")
        return

    queue = [json.loads(line) for line in open(queue_file, encoding="utf-8")]
    judgments_map = {}
    if judgments_file.exists():
        for line in open(judgments_file, encoding="utf-8"):
            try:
                r = json.loads(line)
                judgments_map[(r["query_id"], r["candidate_id"])] = r
            except Exception:
                pass

    total = len(queue)
    if total == 0:
        print("Hàng đợi rỗng.")
        return

    # Tìm vị trí bản ghi chưa chấm đầu tiên
    current_idx = 0
    for i, item in enumerate(queue):
        k = (item["query_id"], item["candidate_id"])
        if judgments_map.get(k, {}).get("human_grade") in ("UNJUDGED", None):
            current_idx = i
            break

    print("="*75)
    print("CHƯƠNG TRÌNH ĐÁNH GIÁ TƯƠNG TÁC HUMAN RELEVANCE JUDGMENT (CLI)")
    print("="*75)
    print("Thang điểm:")
    print("  [0] : Không liên quan")
    print("  [1] : Có liên quan nhẹ, giá trị sử dụng hạn chế")
    print("  [2] : Có liên quan đáng kể")
    print("  [3] : Rất liên quan, có giá trị tham khảo trực tiếp")
    print("  [S] : Skip (Bỏ qua) | [P] : Prev (Quay lại) | [X] : Exit (Lưu & Thoát)")
    print("="*75 + "\n")

    while 0 <= current_idx < total:
        item = queue[current_idx]
        k = (item["query_id"], item["candidate_id"])
        current_j = judgments_map.get(k, {}).get("human_grade", "UNJUDGED")

        # Thống kê tiến độ
        done_count = sum(1 for j in judgments_map.values() if j.get("human_grade") not in ("UNJUDGED", None))

        if HAS_RICH:
            console.rule(f"[bold cyan]CẶP [{current_idx+1}/{total}] | Query: {item['query_id']} ➔ Candidate: {item['candidate_id']} | Đã chấm: {current_j}[/bold cyan]")
            console.print(f"[bold magenta]Tìm thấy bởi các phương pháp:[/bold magenta] [yellow]{', '.join(item.get('retrieved_by', []))}[/yellow]\n")

            table = Table(title="Đối chiếu Thông tin Query và Candidate", show_header=True, header_style="bold green")
            table.add_column("Khía cạnh / Mục", style="cyan", width=18)
            table.add_column(f"Query Paper ({item['query_id']})", style="white", width=45)
            table.add_column(f"Candidate Paper ({item['candidate_id']})", style="white", width=45)

            table.add_row("Tiêu đề (Title)", item.get("query_title", ""), item.get("candidate_title", ""))
            table.add_row("Tóm tắt (Abstract)", item.get("query_abstract", "")[:350] + "...", item.get("candidate_abstract", "")[:350] + "...")
            
            q_f = item.get("query_facets", {})
            c_f = item.get("candidate_facets", {})
            table.add_row("Problem", str(q_f.get("problem", "")), str(c_f.get("problem", "")))
            table.add_row("Task", str(q_f.get("task", "")), str(c_f.get("task", "")))
            table.add_row("Method", str(q_f.get("method", "")), str(c_f.get("method", "")))
            table.add_row("Dataset", str(q_f.get("dataset", "")), str(c_f.get("dataset", "")))
            table.add_row("Contribution", str(q_f.get("contribution", "")), str(c_f.get("contribution", "")))

            console.print(table)
        else:
            print(f"\n--- CẶP [{current_idx+1}/{total}] | Q: {item['query_id']} -> C: {item['candidate_id']} | Hiện tại: {current_j} ---")
            print(f"Nguồn: {item.get('retrieved_by', [])}")
            print(f"QUERY TITLE: {item.get('query_title')}")
            print(f"CANDIDATE TITLE: {item.get('candidate_title')}")

        print(f"\n[Tiến độ: Đã chấm {done_count}/{total} cặp ({done_count/total*100:.1f}%)]")
        choice = input("Nhập điểm [0/1/2/3], [S]kip, [P]rev, hoặc [X]it: ").strip().lower()

        if choice in ('0', '1', '2', '3'):
            grade_val = int(choice)
            judgments_map[k] = {
                "query_id": item["query_id"],
                "candidate_id": item["candidate_id"],
                "human_grade": grade_val,
                "notes": "",
                "retrieved_by": item.get("retrieved_by", [])
            }
            # Ghi lại file
            with open(judgments_file, "w", encoding="utf-8") as f:
                for r in judgments_map.values():
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"-> Đã lưu Grade {grade_val} thành công.")
            current_idx += 1

        elif choice in ('s', ''):
            current_idx += 1

        elif choice == 'p':
            current_idx = max(0, current_idx - 1)

        elif choice in ('x', 'exit', 'quit'):
            print("\nĐã lưu tiến độ và thoát.")
            break

    print(f"\nPhiên làm việc kết thúc. Tổng số cặp đã chấm: {sum(1 for j in judgments_map.values() if j.get('human_grade') not in ('UNJUDGED', None))}/{total}.")

if __name__ == "__main__":
    main()
