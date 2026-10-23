# Giao diện baseline và evaluator B–E

[Chỉ mục script](README.md) · [Protocol](../docs/EXPERIMENT_PROTOCOL.md)

Tài liệu này giữ các quy tắc dùng chung. Logic riêng và ví dụ số nằm trong README [B](exp_b/README.md), [C](exp_c/README.md), [D](exp_d/README.md), [E](exp_e/README.md).

## 1. Một lượt chạy làm gì?

```text
config + manifest dataset
→ kiểm tra schema, hash, provenance và trạng thái complete
→ nạp corpus và facet hợp lệ
→ chọn cases / cắt lịch sử trước cutoff
→ predict(...) xếp hạng bằng dữ liệu quan sát được
→ evaluator đọc ground truth, tính điểm
→ xuất predictions, metrics, báo cáo và manifest kết quả
```

Scorer không đọc nhãn relevance, latent profile hoặc intent ẩn. D có một comparator `oracle` do evaluator tạo bằng intent thật; đó là điều kiện có thông tin đặc quyền, không phải phương pháp deploy.

B chọn split bài mốc. C/D/E dùng thời gian để tách phần quan sát và phần chấm điểm. Tên `interactions_train` là lịch sử quan sát; không có nghĩa baseline đã huấn luyện mạng neural.

## 2. Hợp đồng predict

Mỗi `scripts/exp_*/run_exp_*.py` cung cấp `predict(papers, facets, cases, history, options)`.

| Đối số | Nội dung |
|---|---|
| `papers` | Dictionary theo paper_id; title, abstract và metadata corpus |
| `facets` | Dictionary theo paper_id; năm tập concept đã chuẩn hóa, đã lọc flags |
| `cases` | Case có ID và candidate_ids; trường riêng tùy exp |
| `history` | Hành vi được phép quan sát; B không cần lịch sử |
| `options` | Seed và tín hiệu/giới hạn thời gian riêng của exp |

Các trường đặc thù:

| Exp | Case và options cần chú ý |
|---|---|
| B | Case có query_id, query_paper_id; options có fixed_weights cố định |
| C | user_id, cutoff; options có search/exposure và cutoff |
| D | user_id, query_paper_id, context_facet, cutoff; lịch sử profile và tín hiệu phiên; ngưỡng suy hướng |
| E | user_id, period, cutoff; options có recent_start và half_life_days |

Runner điều phối cấu trúc thực tế; khi viết phương pháp mới, giữ nguyên chữ ký và cách truyền đối số đang có trong exp.

Một prediction ranking có dạng:

```json
{
  "case_id": "Q0001",
  "model": "my_method",
  "ranking": [
    {"paper_id": "P000010", "score": 0.8},
    {"paper_id": "P000020", "score": 0.3}
  ]
}
```

Ví dụ chỉ có hai ứng viên. Với case thật, phải có **đúng toàn bộ candidate_ids**, mỗi ID một lần, đủ điểm hữu hạn, đúng thứ tự giảm dần. Hòa điểm dùng paper_id tăng dần. Mỗi model có đúng một prediction/case.

C/D/E có thể thêm `facet_importance`: đúng năm khóa, giá trị không âm, tổng bằng 1. D thêm `directions` với năm khóa và nhãn `similar`, `different`, `unknown`, `ignore`. `direction_confidence` là độ tin cậy heuristic, chưa phải xác suất đã hiệu chuẩn.

Ở D, `unknown` dùng phép tính similar khi ranking nhưng **giữ nguyên unknown trong prediction** để evaluator ghi nhận chưa suy được hướng.

## 3. Đọc các chỉ số

| Chỉ số | Tính thế nào? | Ý nghĩa |
|---|---|---|
| nDCG@k | gain = 2^relevance − 1; chia discount log2(rank+1), chuẩn hóa bằng thứ tự lý tưởng | Nhãn cao lên đầu có tốt không |
| Recall@k | Số ứng viên dương trong top k / tổng ứng viên dương của case | Tìm được bao nhiêu đáp án dương |
| Precision@k | Số ứng viên dương trong top k / số vị trí được đánh giá | Top k có bao nhiêu đáp án dương |
| MRR | Nghịch đảo thứ hạng ứng viên dương đầu tiên | Bao lâu mới gặp đáp án dương |
| Importance MAE | Trung bình sai số tuyệt đối giữa năm trọng số dự đoán và latent weights | Ước lượng mức quan tâm từng facet |
| Direction F1 | Gộp quyết định similar/different trên facet intent có hiệu lực | Suy hướng đúng đến đâu |
| Direction coverage | Tỷ lệ facet intent có dự đoán similar/different | Có suy được hướng hay vẫn unknown |
| Compliance@k ở D | Tỷ lệ top k có intent grade 2 | Tuân thủ đồng thời context và focus |

Relevance **lớn hơn 0** được xem là dương cho Recall/Precision/MRR. Ở B, ngưỡng 0.6 chỉ dùng lấy mẫu high/low; nhãn 0.2 vẫn dương khi đánh giá. Ở D, grade 1 vẫn dương cho retrieval nhưng có thể sai hướng; compliance chỉ nhận grade 2. C/E dùng dislike/view/click/save/like tương ứng grade 0/0/1/2/3.

Direction F1 tính từ confusion counts gộp; không lấy trung bình F1 từng phiên. `unknown` trên facet active làm mất true positive, `ignore` ngoài intent không tham gia chấm. Báo cáo có thêm accuracy và coverage để hiểu nguyên nhân điểm thấp.

Case không có positive không có Recall/MRR hợp lệ; chỉ số với mẫu số bằng 0 được ghi N/A, không tự xem là thành công. Chi tiết xử lý và các cohort được ghi trong output của evaluator.

## 4. Lệnh và output chung

Chạy từ gốc repository, Python 3.11+. Ví dụ B:

```powershell
python scripts/exp_b/run_exp_b.py --dry-run
python scripts/exp_b/run_exp_b.py
```

`--config` chọn config; `--output` chọn thư mục kết quả; `--overwrite` cho phép thay kết quả đã có; `--ks` chọn cutoff chỉ số. `--split` chỉ dành cho B, mặc định test. C/D/E đánh giá holdout của dataset. Tham khảo `--help` và lệnh cụ thể trong từng README.

| Tệp trong thư mục kết quả | Vai trò |
|---|---|
| `predictions.jsonl` | Ranking, scores và trường phụ từng case/model |
| `details.jsonl` | Điểm từng case/model |
| `report.json` | Điểm tổng hợp, cấu hình đánh giá và phân nhóm |
| `summary.csv` | Bảng số liệu để tổng hợp |
| `report.md` | Bảng so sánh dễ đọc và giới hạn |
| `manifest.json` | Hash input/code/output và provenance |

Bàn giao cả thư mục, không gửi riêng một bảng điểm. Tên model trong prediction là khóa evaluator dùng để nhóm so sánh.

## 5. Phát triển từ baseline

Giữ các baseline để so sánh, thêm phương pháp trong `scripts/exp_<x>/`, rồi trả thêm prediction qua cùng giao diện. [Ví dụ mở rộng B](exp_b/README.md) minh họa cụ thể. Dùng chung dataset, candidate pools, split/cutoff và evaluator để phép so sánh có ý nghĩa.

Helper trong `baseline_common.py` được nhiều exp gọi. Sửa helper sẽ thay đối chứng của các thành viên khác; phương pháp nghiên cứu riêng nên nằm trong exp trước. Nếu thay hợp đồng chung, cập nhật callers và tests liên quan.

B/C/D/E có thể nghiên cứu song song khi đã có dữ liệu đầu vào. Phương pháp profile mới của C chỉ được đưa sang D/E qua một phiên bản tích hợp được thống nhất sau, không tự làm D/E phụ thuộc kết quả C.

Encoder pretrained có thể được freeze để biểu diễn title/abstract hoặc facet; thêm nó không tự tạo reranker, nhãn ground truth hoặc bước training. Nếu có model học tham số, B dùng train/validation/test theo anchor; C/D/E phải giữ cutoff, fit/tune trên phần được phép quan sát.

Đổi scorer không đòi sinh lại dữ liệu. Đổi quy tắc generator/config/input phải tạo dataset và manifest tương ứng trước khi so điểm.

## 6. Kiểm tra khi đổi code

```powershell
python -m unittest discover -s tests -v
```

Chọn test liên quan trước; chạy bộ đầy đủ khi sửa helper/runner/evaluator chung. Dry-run xác nhận đầu vào và điều phối, chưa chứng minh chất lượng ranking. Các ví dụ số trong README dùng để hiểu công thức, không phải kết quả benchmark.
