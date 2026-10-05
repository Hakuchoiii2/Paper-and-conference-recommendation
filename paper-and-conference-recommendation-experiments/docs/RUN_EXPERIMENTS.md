# Chạy bộ sinh dataset A–E

## Quy mô và trạng thái

| Phần | Mặc định hiện triển khai |
|---|---|
| A | Gộp 5 phần × 842 = 4.210 silver annotations |
| Human review A | Chọn 400 IDs đầy đủ nhất; người review mới tạo gold |
| B | 300 queries × 100 candidates = 30.000 cặp |
| C | 1.500 cases × 20 candidates = 30.000 cặp; quota 6×200 + 2×150 |
| D | 300 users × 50 = 15.000 events; history 9.000 / future 6.000 |
| E | Cùng 300 users × 4 periods × 15 = 18.000 events, 1.200 profiles |

Snapshot đo thời gian 2026-10-05 có A part_1: 842/4.210 records,
192 bài fallback/lỗi; thiếu 3.368 IDs
thuộc parts 2–5. Code đã kiểm tra bằng fixtures ở quy mô trên, nhưng chưa tạo B–E
trên corpus thật hoặc tạo hàng đợi review cuối cùng. Không bù annotation còn thiếu.

Xem [thời gian generator và chẩn đoán quota trên silver thật](GENERATOR_TIMING.md).

Các lệnh dưới chạy từ **gốc dự án** với Python 3.11+. Có thể thay `python` bằng
`.\.venv-qwen\Scripts\python.exe`. Tools gộp/chọn/generate B–E chỉ dùng stdlib;
Qwen annotation có môi trường GPU riêng theo [README A](../data/exp_a/README.md).

Generator và chuẩn bị dữ liệu nằm trong `data/exp_*`; bộ điều phối chung ở
`data/build_experiments.py`. Code chạy và đánh giá mô hình ở `scripts/exp_*`;
hiện A có evaluator Qwen, B–E chưa có bộ chạy mô hình.

## 1. Nhận đủ năm phần A

Mỗi part phải có `facets_silver.jsonl`, `annotation_metadata.jsonl` và `manifest.json`.
Đặt nguyên bộ vào `data/exp_a/generated/part_1` đến `part_5`. Các phần dùng cùng
corpus, prompt/guideline, policy/code, model checkpoint và sampling config;
chỉ khác output_dir, paper_range và cache_dir. Giữ parts/checkpoints để tiếp tục/audit.
Chờ các tiến trình xuất tệp xong trước khi gộp.

~~~powershell
python data/exp_a/merge_exp_a.py --dry-run
python data/exp_a/merge_exp_a.py
python scripts/validate_all.py --dataset-kind real --phase experiments
~~~

Tool kiểm tra hashes/coverage từng khoảng, provenance, runtime model/revision,
overlap và coverage toàn corpus trước khi ghi. Fallback thiếu runtime fields vẫn
được giữ cùng audit, không được dùng để bỏ qua model mismatch đã ghi.
Output mặc định ở `data/exp_a/generated/`, gồm silver + metadata + manifest complete.
Không ghi đè parts. Thiếu một phần thì dừng; không tự biến partial thành complete.
Có thể chỉ định `--parts ...` và `--output data/exp_a/<thư_mục_mới>`.

## 2. Chọn 400 bài cho human gold review

~~~powershell
python data/exp_a/select_gold_review.py --dry-run
python data/exp_a/select_gold_review.py
~~~

Không random: bỏ P000001 (ví dụ phát triển prompt), fallback/validation errors
và bài không có facet trích được. Xếp theo số facet có dữ liệu giảm dần,
rồi số concept có dẫn chứng giảm dần, cuối cùng paper_id tăng dần. Chọn 400 đầu.
Nếu chưa đủ 400 hợp lệ thì báo thiếu, không lấy bài lỗi bù số lượng.

Gold dùng để đối chiếu độc lập độ đúng và độ đầy đủ của năm facet Qwen trích:
người review đọc title/abstract, xác định facet đúng và sửa/bổ sung nhãn.
Silver tự động không trở thành gold vì được chọn. Chọn bài đầy đủ là chủ đích
của đợt review này; kết quả không đại diện ngẫu nhiên cho toàn corpus.

Output `data/exp_a/ground_truth/gold_review/`:

- `review_papers.jsonl`: ID/title/abstract, không đính kèm nhãn Qwen.
- `review_annotations.jsonl`: form pending, reviewer và năm facets để người điền.
- `silver_reference.jsonl`: silver riêng để đối chiếu **sau** review độc lập.
- `selection_ranking.jsonl`: thứ hạng và điểm đầy đủ.
- `manifest.json`: selected IDs, tiêu chí, exclusions, selection bias và hashes.

Không sinh `facets_gold.jsonl` tự động. Queue đang tồn tại không bị ghi đè;
dùng `--output` mới nếu cần đợt khác. Người review hoàn tất nhãn, ghi reviewer,
giải quyết bất đồng rồi mới xuất gold theo contract. Không dùng gold held-out
để chỉnh prompt rồi báo lại như một đánh giá độc lập.

Để xem thử trên part_1 mà không ghi hàng đợi cuối:

~~~powershell
python data/exp_a/select_gold_review.py --source data/exp_a/generated/part_1 --count 400 --dry-run --allow-partial
~~~

## 3. Sinh B/C/D rồi E

Sau khi A complete đã qua gate, B/C/D chạy độc lập; E chạy sau khi D có users/manifest.

~~~powershell
python data/exp_b/build_exp_b.py --dry-run
python data/exp_b/build_exp_b.py
python data/exp_c/build_exp_c.py
python data/exp_d/build_exp_d.py
python data/exp_e/build_exp_e.py
python scripts/validate_all.py --dataset-kind mock --phase experiments
~~~

Mỗi generator có `--dry-run`, `--validate-only`, `--config`. Mặc định đọc
`configs/exp_b.json` đến `exp_e.json`, output `data/exp_x/generated/`, truth
`data/exp_x/ground_truth/`. Paths trong config tính từ gốc dự án.
B–E là mock trên **corpus và facets thật**; seed 42, rules có version, đủ hashes.
Các records A fallback/lỗi không được dùng để gán mock labels hoặc sinh hành vi.

B/C thiếu ứng viên/quota sẽ xuất bộ partial với report lý do và exit code 2.
`--allow-shortfall` cho phép kiểm tra bộ partial, không bỏ qua dữ liệu sai.
D/E thiếu pool đủ để tạo events riêng biệt thì báo lỗi. Không tự giảm mục tiêu,
random lại nhãn, nhân đôi records hoặc tạo facets để ép đủ số.

Nhãn B/C, D/E latent profiles và future events ở truth; mô hình chỉ đọc input
quan sát được. Báo cáo D/E chỉ thống kê loại tương tác history.
Không cho mô hình tự duyệt toàn bộ folder để tìm features.

## 4. Kiểm tra và giới hạn

Khi 400 forms đã được người review hoàn tất, chạy `python scripts/exp_a/evaluate_exp_a.py`
để chấm đối chiếu silver/gold và xem từng bài Qwen trích dư/thiếu/có thể nhầm facet.
Xem [hướng dẫn đánh giá Qwen](EVALUATE_QWEN.md) về trạng thái reviewed, metrics,
so khớp chữ và giới hạn cohort ưu tiên đầy đủ.

~~~powershell
python scripts/validate_all.py --dataset-kind real --phase corpus
python data/exp_a/build_exp_a.py --validate-only --allow-partial
python scripts/validate_all.py --dataset-kind mock --phase experiments --experiment b
python -B -m unittest discover -s tests
~~~

Fixtures của tests tách trong thư mục tạm, không ghi facets giả vào corpus thật.
Các tests kiểm tra target counts, rules bằng ví dụ độc lập, corrupted data,
same-anchor split, hidden truth, chronological boundaries và byte-identical rebuilds,
kể cả D/E trong tiến trình mới với hash seed khác.

Code/structural checks không bảo đảm Qwen trích đúng ngữ nghĩa, B/C concept overlap
phản ánh semantic similarity, hoặc D/E mô phỏng sát hành vi người thật.
Đọc [B](../data/exp_b/README.md), [C](../data/exp_c/README.md),
[D](../data/exp_d/README.md), [E](../data/exp_e/README.md) để xem chính xác rules.
