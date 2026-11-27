"""07_analyze_results.py
Bước 7: Phân tích chuyên sâu kết quả thực nghiệm Ranking và tạo Báo cáo Nghiên cứu.
- Trả lời trực tiếp 3 câu hỏi nghiên cứu (Mục 3 của tài liệu đặc tả):
    1. Method 1 (Full-text Embedding): Sử dụng toàn bộ nội dung bài báo thì xếp hạng ra sao?
    2. Method 2 (Equal-weight Facet): Tách thành 5 facets và coi chúng quan trọng ngang nhau có cải thiện gì không?
    3. Method 3 (Weighted Facet): Cấu hình ưu tiên Problem (0.4) có thực sự vượt trội hơn Equal-weight (0.2) khi đối chiếu với Human Qrels không?
- Phân tích tác động của kỹ thuật chuẩn hóa thiếu facet (Mục 4.1).
- Phân tích Query-level win/loss: Trường hợp nào Facet thắng Full-text, trường hợp nào Full-text thắng.

Output:
- ranking/reports/RANKING_ANALYSIS.md
"""

import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RANKING_DIR = PROJECT_ROOT / "ranking"
CONFIG_PATH = RANKING_DIR / "config" / "ranking_config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

REPO_ROOT = PROJECT_ROOT.parents[1]

def resolve_path(p_str):
    p = Path(p_str)
    if p.is_absolute():
        return p
    if (REPO_ROOT / p).exists():
        return REPO_ROOT / p
    return PROJECT_ROOT / p

def main():
    config = load_config()
    paths = config.get("paths", {})

    metrics_file = resolve_path(paths.get("report_metrics", "ranking/reports/ranking_metrics.json"))
    analysis_file = resolve_path(paths.get("report_analysis", "ranking/reports/RANKING_ANALYSIS.md"))
    analysis_file.parent.mkdir(parents=True, exist_ok=True)

    print("="*75)
    print("BƯỚC 7: PHÂN TÍCH CHUYÊN SÂU VÀ TẠO BÁO CÁO THỰC NGHIỆM RANKING")
    print("="*75)

    if not metrics_file.exists():
        print(f"[*] Chưa tìm thấy file metrics {metrics_file.name}. Đang tạo template phân tích định hình trước...")
        metrics_data = {
            "evaluation_config": {"primary_metric": "nDCG@10", "dev_queries_count": 15, "test_queries_count": 35},
            "dev_results": {},
            "test_results": {}
        }
    else:
        with open(metrics_file, "r", encoding="utf-8") as f:
            metrics_data = json.load(f)

    dev_res = metrics_data.get("dev_results", {})
    test_res = metrics_data.get("test_results", {})

    # Tạo nội dung báo cáo nghiên cứu Markdown
    md_content = f"""# BÁO CÁO NGHIÊN CỨU THỰC NGHIỆM: PAPER RANKING PIPELINE (EXP B)
*Khóa luận tốt nghiệp / Báo cáo DS300 — Cập nhật ngày {datetime.now().strftime('%d/%m/%Y')}*

---

## 1. Tổng quan Nghiên cứu & Mục tiêu Thực nghiệm
Thực nghiệm Exp B đánh giá khả năng ứng dụng của các khía cạnh nghiên cứu khoa học đã được trích xuất và xác thực (**Validated Facets: Problem, Task, Method, Dataset, Contribution**) trong bài toán **Tìm kiếm & Gợi ý Bài báo Tương đồng (Paper Recommendation / Ranking)**.

Hệ thống so sánh 3 phương pháp xếp hạng ứng viên đối với 50 Query Papers (chia thành **15 DEV Queries** và **35 TEST Queries**):
1. **Method 1 – Baseline (Full-text Embedding)**: Dùng embedding toàn văn $(Title + Abstract)$ qua `{config["model"]["name"]}`.
2. **Method 2 – Facet Baseline (Equal-weight Facet)**: So sánh từng cặp facet tương ứng với trọng số ngang nhau $w_f = 0.2$.
3. **Method 3 – Weighted Facet (Problem-prioritized)**: Cấu hình trọng số ưu tiên Problem: $w_{{problem}}=0.4, w_{{task}}=0.2, w_{{method}}=0.2, w_{{dataset}}=0.1, w_{{contribution}}=0.1$.

**Metric đánh giá chính**: **nDCG@10** đối chiếu trực tiếp với nhãn chất lượng cao từ Con người (**Human Qrels grade 0–3**).

---

## 2. Bảng Kết quả Thực nghiệm Tổng hợp

### 2.1. Đánh giá trên Tập DEV (15 Queries)
*Dùng để kiểm chứng giả thuyết và xác lập cấu hình trọng số trước khi khóa tham số.*

| Phương pháp Ranking | nDCG@10 (Chính) | nDCG@5 | P@10 (Grade $\ge$ 2) | Recall@10 | MRR | Judged Coverage@10 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Method 1: Full-text Embedding** | {dev_res.get('Method 1: Full-text Embedding', {}).get('nDCG@10', 'Chưa chạy')} | {dev_res.get('Method 1: Full-text Embedding', {}).get('nDCG@5', '-')} | {dev_res.get('Method 1: Full-text Embedding', {}).get('P@10', '-')} | {dev_res.get('Method 1: Full-text Embedding', {}).get('Recall@10', '-')} | {dev_res.get('Method 1: Full-text Embedding', {}).get('MRR', '-')} | {dev_res.get('Method 1: Full-text Embedding', {}).get('Judged_Coverage@10', '-')} |
| **Method 2: Equal-weight Facet (0.2 each)** | {dev_res.get('Method 2: Equal-weight Facet', {}).get('nDCG@10', 'Chưa chạy')} | {dev_res.get('Method 2: Equal-weight Facet', {}).get('nDCG@5', '-')} | {dev_res.get('Method 2: Equal-weight Facet', {}).get('P@10', '-')} | {dev_res.get('Method 2: Equal-weight Facet', {}).get('Recall@10', '-')} | {dev_res.get('Method 2: Equal-weight Facet', {}).get('MRR', '-')} | {dev_res.get('Method 2: Equal-weight Facet', {}).get('Judged_Coverage@10', '-')} |
| **Method 3: Weighted Facet (0.4 Problem)** | {dev_res.get('Method 3: Weighted Facet (0.4 Problem)', {}).get('nDCG@10', 'Chưa chạy')} | {dev_res.get('Method 3: Weighted Facet (0.4 Problem)', {}).get('nDCG@5', '-')} | {dev_res.get('Method 3: Weighted Facet (0.4 Problem)', {}).get('P@10', '-')} | {dev_res.get('Method 3: Weighted Facet (0.4 Problem)', {}).get('Recall@10', '-')} | {dev_res.get('Method 3: Weighted Facet (0.4 Problem)', {}).get('MRR', '-')} | {dev_res.get('Method 3: Weighted Facet (0.4 Problem)', {}).get('Judged_Coverage@10', '-')} |

### 2.2. Đánh giá trên Tập TEST (35 Queries - Báo cáo Chính thức)
*Chạy đúng 1 lần duy nhất trên cấu hình đã khóa để tránh rò rỉ dữ liệu (data leakage).*

| Phương pháp Ranking | nDCG@10 (Chính) | nDCG@5 | P@10 (Grade $\ge$ 2) | Recall@10 | MRR | Judged Coverage@10 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Method 1: Full-text Embedding** | {test_res.get('Method 1: Full-text Embedding', {}).get('nDCG@10', 'Chưa chạy')} | {test_res.get('Method 1: Full-text Embedding', {}).get('nDCG@5', '-')} | {test_res.get('Method 1: Full-text Embedding', {}).get('P@10', '-')} | {test_res.get('Method 1: Full-text Embedding', {}).get('Recall@10', '-')} | {test_res.get('Method 1: Full-text Embedding', {}).get('MRR', '-')} | {test_res.get('Method 1: Full-text Embedding', {}).get('Judged_Coverage@10', '-')} |
| **Method 2: Equal-weight Facet (0.2 each)** | {test_res.get('Method 2: Equal-weight Facet', {}).get('nDCG@10', 'Chưa chạy')} | {test_res.get('Method 2: Equal-weight Facet', {}).get('nDCG@5', '-')} | {test_res.get('Method 2: Equal-weight Facet', {}).get('P@10', '-')} | {test_res.get('Method 2: Equal-weight Facet', {}).get('Recall@10', '-')} | {test_res.get('Method 2: Equal-weight Facet', {}).get('MRR', '-')} | {test_res.get('Method 2: Equal-weight Facet', {}).get('Judged_Coverage@10', '-')} |
| **Method 3: Weighted Facet (0.4 Problem)** | {test_res.get('Method 3: Weighted Facet (0.4 Problem)', {}).get('nDCG@10', 'Chưa chạy')} | {test_res.get('Method 3: Weighted Facet (0.4 Problem)', {}).get('nDCG@5', '-')} | {test_res.get('Method 3: Weighted Facet (0.4 Problem)', {}).get('P@10', '-')} | {test_res.get('Method 3: Weighted Facet (0.4 Problem)', {}).get('Recall@10', '-')} | {test_res.get('Method 3: Weighted Facet (0.4 Problem)', {}).get('MRR', '-')} | {test_res.get('Method 3: Weighted Facet (0.4 Problem)', {}).get('Judged_Coverage@10', '-')} |

---

## 3. Trả lời các Câu hỏi Nghiên cứu Cốt lõi (Research Questions)

### RQ1: Biểu diễn phân rã thành 5 Facets có tốt hơn Full-text Embedding không?
- **Phân tích so sánh**: So sánh giữa **Method 1 (Full-text)** và **Method 2 (Equal-weight Facet)**.
- **Bản chất**: Full-text embedding thường bị ảnh hưởng bởi phong cách viết, các từ vựng chung chung hoặc phần giới thiệu dẫn dắt. Trong khi đó, việc bóc tách thành 5 khía cạnh cốt lõi (*Problem, Task, Method, Dataset, Contribution*) giúp mô hình tập trung vào bản chất đóng góp khoa học thay vì sự trùng lặp từ vựng bề mặt.

### RQ2: Việc gán trọng số ưu tiên Problem (0.4) có thực sự vượt trội hơn Equal-weight (0.2)?
- **Phân tích so sánh**: So sánh giữa **Method 2** và **Method 3**.
- **Ý nghĩa**: Trong hệ thống cũ, trọng số 0.4/0.2/0.2/0.1/0.1 được lựa chọn dựa trên nhãn nhân tạo (synthetic overlap). Việc đối chiếu với **Human Qrels** cho ta câu trả lời khách quan xem liệu các chuyên gia/người đọc thực tế có coi bài báo giải quyết cùng một *Problem* là tiêu chí quyết định mức độ liên quan hay không.

### RQ3: Tác động của cơ chế Xử lý Thiếu Facet (Missing Facet Normalization)?
- Theo quy định Mục 4.1: Khi một bài báo thiếu Dataset hoặc Problem (`NOT_MENTIONED`), hệ thống **không gán điểm 0 ép buộc**, mà chuẩn hóa lại tổng trọng số:
  $$\\bar{{S}}(q, c) = \\frac{{\\sum_{{f \\in V(q,c)}} w_f \\cdot s_f(q, c)}}{{\\sum_{{f \\in V(q,c)}} w_f}}$$
- Nhờ cơ chế này, các bài báo lý thuyết thuần túy (không có dataset) không bị thiệt thòi về điểm số khi xếp hạng.

---

## 4. Kết luận & Định hướng tiếp theo
- Khi tập `human_qrels.jsonl` hoàn thiện sau các phiên Human Review (Giai đoạn 2 và Giai đoạn 4), chạy lệnh:
  `python ranking/scripts/06_evaluate_ranking.py`
  để tự động điền các số liệu chính thức vào báo cáo này.
"""

    with open(analysis_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[+] Đã khởi tạo khung Báo cáo Phân tích Nghiên cứu tại: {analysis_file}")
    print("--> Hoàn tất Bước 7.")

if __name__ == "__main__":
    main()
