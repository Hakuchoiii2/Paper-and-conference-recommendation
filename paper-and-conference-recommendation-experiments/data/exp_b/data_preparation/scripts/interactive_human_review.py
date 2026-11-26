"""interactive_human_review.py
Công cụ giao diện dòng lệnh (CLI) tương tác giúp con người duyệt và xử lý Bước 5: Human Quality Control.
- Đọc hàng đợi từ data_preparation/human_review/review_queue.jsonl
- Tự động cập nhật trực tiếp vào data_preparation/human_review/human_corrections.jsonl
- Hiển thị đầy đủ: Title, Abstract, Câu bằng chứng (Evidence), Facet hiện tại, Đánh giá của Qwen và Đề xuất sửa.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HUMAN_DIR = PROJECT_ROOT / "data_preparation" / "human_review"
QUEUE_PATH = HUMAN_DIR / "review_queue.jsonl"
CORR_PATH = HUMAN_DIR / "human_corrections.jsonl"

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

def load_data():
    if not QUEUE_PATH.exists():
        print(f"Lỗi: Không tìm thấy file {QUEUE_PATH}")
        sys.exit(1)

    queue = [json.loads(line) for line in open(QUEUE_PATH, encoding="utf-8")]
    
    corrections = {}
    if CORR_PATH.exists():
        for line_no, line in enumerate(open(CORR_PATH, encoding="utf-8"), 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{CORR_PATH}:{line_no}: invalid JSON: {exc}") from exc
            if row.get("review_source") not in {"cli", "web_ui", "spreadsheet_import"}:
                row["human_decision"] = "PENDING"
            corrections[(row["paper_id"], row["facet"])] = row
    return queue, corrections

def save_correction(corr_dict, reviewed_key=None):
    if reviewed_key is not None:
        correction = corr_dict[reviewed_key]
        correction["review_source"] = "cli"
        correction["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    # Ghi lại toàn bộ corrections
    with open(CORR_PATH, "w", encoding="utf-8") as f:
        for r in corr_dict.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def display_item(item, corr, idx, total):
    pid = item["paper_id"]
    facet = item["facet"]
    audit_dec = item["audit_decision"]
    title = item.get("title", "")
    abstract = item.get("abstract", item.get("abstract_snippet", ""))
    curr_concepts = item.get("current_concepts", [])
    ev_texts = item.get("evidence_texts", [])
    q_status = item.get("qwen_support_status", "N/A")
    q_issues = item.get("qwen_detected_issues", "none")
    q_rev = item.get("qwen_proposed_revision")
    q_exp = item.get("qwen_explanation", "")

    h_dec = corr.get("human_decision", "PENDING") if corr else "PENDING"
    h_rev = corr.get("human_revised_facet", curr_concepts) if corr else curr_concepts
    h_notes = corr.get("human_notes", "") if corr else ""

    if HAS_RICH:
        dec_color = "red" if audit_dec == "REJECTED" else ("yellow" if audit_dec == "NEEDS_REVIEW" else "blue")
        console.rule(f"[{dec_color}]MỤC [{idx+1}/{total}] | Paper ID: {pid} | Facet: {facet.upper()} | Trạng thái Audit: {audit_dec}[/{dec_color}]")
        
        console.print(f"[bold cyan]Tiêu đề:[/bold cyan] {title}")
        
        # In abstract với trích dẫn bằng chứng
        console.print(f"\n[bold]Abstract:[/bold]")
        console.print(f"[dim]{abstract[:400]}...[/dim]" if len(abstract) > 400 else f"[dim]{abstract}[/dim]")

        table = Table(title="Chi tiết Đánh giá & Bằng chứng", show_header=True, header_style="bold magenta")
        table.add_column("Thuộc tính", style="cyan", width=22)
        table.add_column("Nội dung chi tiết", style="white")

        table.add_row("Silver Facet hiện tại", str(curr_concepts))
        table.add_row("Bằng chứng nguồn (MiniLM)", "\n---\n".join(ev_texts) if ev_texts else "[red]Không tìm thấy câu hỗ trợ (Low similarity)[/red]")
        table.add_row("Qwen Hỗ trợ (Support)", f"{q_status} (Lỗi: {q_issues})")
        table.add_row("Qwen Đề xuất sửa", str(q_rev) if q_rev else "[italic dim]Không đề xuất[/italic dim]")
        table.add_row("Qwen Giải thích", q_exp or "N/A")
        table.add_row("Quyết định hiện tại", f"[bold green]{h_dec}[/bold green]" if h_dec != "PENDING" else "[yellow]PENDING (Chưa duyệt)[/yellow]")
        if h_dec == "REVISE":
            table.add_row("Nội dung sau khi sửa", str(h_rev))
        if h_notes:
            table.add_row("Ghi chú con người", h_notes)

        console.print(table)
    else:
        print("="*70)
        print(f"MỤC [{idx+1}/{total}] | Paper ID: {pid} | Facet: {facet} | Audit: {audit_dec}")
        print(f"Tiêu đề: {title}")
        print(f"Silver Concepts hiện tại: {curr_concepts}")
        print(f"Evidence: {ev_texts}")
        print(f"Qwen: {q_status} | Đề xuất sửa: {q_rev} | Giải thích: {q_exp}")
        print(f"Trạng thái duyệt: {h_dec}")
        print("="*70)

def main():
    queue, corrections = load_data()
    total = len(queue)
    if total == 0:
        print("Hàng đợi duyệt rỗng!")
        return

    # Khởi tạo map cho các item chưa có trong corrections
    for item in queue:
        key = (item["paper_id"], item["facet"])
        if key not in corrections:
            corrections[key] = {
                "paper_id": item["paper_id"],
                "facet": item["facet"],
                "human_decision": "PENDING",
                "human_revised_facet": item.get("qwen_proposed_revision") or item.get("current_concepts", []),
                "human_notes": ""
            }

    # Tìm vị trí bản ghi đầu tiên chưa duyệt (PENDING)
    current_idx = 0
    for i, item in enumerate(queue):
        key = (item["paper_id"], item["facet"])
        if corrections[key].get("human_decision") == "PENDING":
            current_idx = i
            break

    print("\n" + "="*70)
    print("CHƯƠNG TRÌNH DUYỆT TƯƠNG TÁC HUMAN QUALITY CONTROL (CLI)")
    print("="*70)
    print("Phím tắt lệnh:")
    print("  [1] hoặc [A] : ACCEPT  (Chấp nhận silver facet hiện tại)")
    print("  [2] hoặc [R] : REJECT  (Bác bỏ nội dung facet hiện tại)")
    print("  [3] hoặc [Q] : USE QWEN (Sử dụng đề xuất sửa của Qwen)")
    print("  [4] hoặc [E] : REVISE  (Tự nhập nội dung sửa mới)")
    print("  [S]          : SKIP    (Bỏ qua để xem mục tiếp theo)")
    print("  [P]          : PREV    (Quay lại mục trước)")
    print("  [G]          : GOTO    (Nhảy đến Paper ID hoặc STT)")
    print("  [X]          : EXIT    (Lưu và thoát)")
    print("="*70 + "\n")

    while 0 <= current_idx < total:
        item = queue[current_idx]
        key = (item["paper_id"], item["facet"])
        corr = corrections.get(key)

        display_item(item, corr, current_idx, total)

        # Tính thống kê tiến độ
        done_count = sum(1 for c in corrections.values() if c.get("human_decision") != "PENDING")
        print(f"\n[Tiến độ: Đã duyệt {done_count}/{total} mục ({done_count/total*100:.1f}%)]")

        choice = input("\nNhập lựa chọn của bạn ([1]Accept / [2]Reject / [3]Use Qwen / [4]Revise / [S]kip / [P]rev / [X]it): ").strip()

        if choice.lower() in ('1', 'a', 'accept'):
            corrections[key]["human_decision"] = "ACCEPT"
            corrections[key]["human_revised_facet"] = item.get("current_concepts", [])
            corrections[key].pop("human_facet_status", None)
            save_correction(corrections, key)
            print("-> Đã lưu: ACCEPT")
            current_idx += 1

        elif choice.lower() in ('2', 'r', 'reject'):
            corrections[key]["human_decision"] = "REJECT"
            corrections[key]["human_revised_facet"] = []
            note = input("Ghi chú lý do bác bỏ (Enter để bỏ qua): ").strip()
            if note:
                corrections[key]["human_notes"] = note
            status_choice = input(
                "Trạng thái cuối [N] NOT_MENTIONED / [S] SOURCE_MISSING / "
                "[T] TRUNCATED / [E] EXTRACTION_FAILED / Enter để suy ra: "
            ).strip().lower()
            status_by_choice = {
                "n": "NOT_MENTIONED",
                "s": "SOURCE_MISSING",
                "t": "TRUNCATED",
                "e": "EXTRACTION_FAILED",
            }
            if status_choice in status_by_choice:
                corrections[key]["human_facet_status"] = status_by_choice[status_choice]
            else:
                corrections[key].pop("human_facet_status", None)
            save_correction(corrections, key)
            print("-> Đã lưu: REJECT (Facet sẽ bị loại bỏ)")
            current_idx += 1

        elif choice.lower() in ('3', 'q', 'qwen'):
            q_rev = item.get("qwen_proposed_revision")
            if not q_rev:
                print("-> Qwen không có đề xuất sửa cho mục này. Vui lòng chọn [4] để tự nhập.")
                continue
            corrections[key]["human_decision"] = "REVISE"
            corrections[key]["human_revised_facet"] = [q_rev] if isinstance(q_rev, str) else q_rev
            corrections[key].pop("human_facet_status", None)
            save_correction(corrections, key)
            print(f"-> Đã lưu: REVISE (sử dụng đề xuất của Qwen: {q_rev})")
            current_idx += 1

        elif choice.lower() in ('4', 'e', 'revise'):
            new_text = input("Nhập nội dung sửa mới (hoặc các concept cách nhau bởi dấu phẩy): ").strip()
            if not new_text:
                print("-> Bạn chưa nhập nội dung, đã hủy thao tác sửa.")
                continue
            concepts = [c.strip() for c in new_text.split(",") if c.strip()]
            corrections[key]["human_decision"] = "REVISE"
            corrections[key]["human_revised_facet"] = concepts
            corrections[key].pop("human_facet_status", None)
            note = input("Ghi chú bổ sung (Enter để bỏ qua): ").strip()
            if note:
                corrections[key]["human_notes"] = note
            save_correction(corrections, key)
            print(f"-> Đã lưu: REVISE với nội dung: {concepts}")
            current_idx += 1

        elif choice.lower() in ('s', 'skip', ''):
            current_idx += 1

        elif choice.lower() in ('p', 'prev'):
            current_idx = max(0, current_idx - 1)

        elif choice.lower() in ('g', 'goto'):
            target = input("Nhập Paper ID hoặc STT (1-based): ").strip()
            if target.isdigit():
                tgt_idx = int(target) - 1
                if 0 <= tgt_idx < total:
                    current_idx = tgt_idx
                else:
                    print("STT không hợp lệ.")
            else:
                found = False
                for i, q in enumerate(queue):
                    if q["paper_id"].lower() == target.lower():
                        current_idx = i
                        found = True
                        break
                if not found:
                    print(f"Không tìm thấy Paper ID '{target}'.")

        elif choice.lower() in ('x', 'exit', 'quit', 'q!'):
            save_correction(corrections)
            print("\nĐã lưu tiến độ duyệt và thoát.")
            break

    print(f"\nHoàn tất phiên làm việc. Tổng số mục đã duyệt: {sum(1 for c in corrections.values() if c.get('human_decision') != 'PENDING')}/{total}.")
    print("Sau khi duyệt xong, bạn hãy chạy Bước 6: python data_preparation/scripts/08_merge_validated_silver.py để áp dụng kết quả.")

if __name__ == "__main__":
    main()
