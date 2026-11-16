# Chạy thực nghiệm hội nghị và tạo báo cáo v2

Chạy lệnh bên dưới từ thư mục `paper-and-conference-recommendation-experiments`.
Python cần NumPy. SPECTER/BGE cần thêm PyTorch và sentence-transformers, cùng checkpoint tương ứng.
Có thể dùng môi trường `.venv-qwen` đang có; nếu dùng Python khác, thay đường dẫn Python trong lệnh.

## Quy trình

```powershell
# 1. Tune tất cả phương pháp trên cùng 5 fold Train; không đánh giá Test.
.\.venv-qwen\Scripts\python.exe scripts\conference_recommendation\run_experiments.py --stage tune --embedding-backend all

# 2. Đọc cấu hình đã đóng băng và đánh giá mặc định/best trên Test.
.\.venv-qwen\Scripts\python.exe scripts\conference_recommendation\run_experiments.py --stage test --embedding-backend all

# 3. Ablation đã định trước trên Test; sensitivity chỉ trên Train CV.
.\.venv-qwen\Scripts\python.exe scripts\conference_recommendation\run_experiments.py --stage analyze --embedding-backend all

# 4. So sánh 5 LLM, cố định Train Qwen-8B và cấu hình đã tune.
.\.venv-qwen\Scripts\python.exe scripts\conference_recommendation\run_experiments.py --stage benchmark --embedding-backend all

# 5. Điền report Markdown và xuất CSV của các bảng.
.\.venv-qwen\Scripts\python.exe scripts\conference_recommendation\run_experiments.py --stage report --overwrite
```

Bước report giữ nguyên Bảng 3 và tự thêm **Hình 3**, một biểu đồ đường nhiều ô
(mỗi hàng một backend, mỗi cột k/tau/kappa), có mean ± fold std và dấu cấu hình đóng băng.
Hình được vẽ từ JSON sensitivity đã có, không chạy lại mô hình hoặc grid search.
File PNG, SVG và CSV dữ liệu vẽ nằm cạnh report trong thư mục `figures`.
Matplotlib cần có trong Python tạo report; trên Windows, nếu môi trường venv thiếu nhưng Python gốc
có Matplotlib, bộ tạo hình tự dùng Python gốc. Nếu cả hai đều thiếu, dùng một Python có Matplotlib
để chạy `--stage report`, hoặc cài Matplotlib vào môi trường hiện tại.
Nhận xét dưới các bảng được lấy theo số liệu hiện có, nêu rõ các trường hợp tuning/gate không giúp,
chạm biên grid và đánh đổi giữa Hit@3 với Hit@1/MRR; phụ lục A bổ sung macro metric của baseline.

Hoặc thực hiện cả 5 bước bằng `--stage all --embedding-backend all --overwrite`.
`--overwrite` cho phép thay artifact đã có; bỏ cờ này để tránh vô tình ghi đè kết quả.
Khi chỉ báo cáo, cờ này chỉ thay report/CSV. Khi `all`, nó cho phép chạy và ghi lại toàn bộ.
Mặc định chỉ chạy `tune` với TF-IDF nếu không truyền tham số. Không tải dense model khi chỉ tạo report.

Kết quả mới ở `results/conference_recommendation_v2`, tách biệt hoàn toàn kết quả cũ.
Mỗi backend tự động xuất **toàn bộ grid** ra hai CSV riêng ngay sau tuning:

- `grid_search_all_<backend>.csv`: một dòng/cấu hình, gồm tham số, 5 cột trọng số riêng,
  CV mean/std và điểm mọi fold; `selected=1` đánh dấu cấu hình thắng trong từng phương pháp.
- `grid_search_folds_<backend>.csv`: một dòng/cấu hình/fold, kèm kích thước validation để phân tích lại.

Mặc định CSV tổng có **1.506 dòng/backend**: 1.440 Gated + 60 Flat + 6 Whole-Text;
CSV fold có 7.530 dòng/backend với 5 fold (không tính header). Số thực tế phụ thuộc grid truyền vào.
CSV dùng số thập phân thô 0..1, không ghép chuỗi phần trăm hoặc `mean ± std`; mỗi dòng có tuning ID.
Không chép toàn bộ grid vào report; report dẫn tới CSV để kiểm tra/phân tích, có thể nộp như dữ liệu bổ sung.
Các cấu hình mặc định được đo riêng và lưu trong JSON/report; không thêm vào CSV grid nếu không thuộc grid quét.

Report mặc định ở `../output/report_gated_facet_gridsearch_experiments.md`.
Có thể đổi bằng `--output-dir` và `--report-path` (đường dẫn tương đối tính từ thư mục dự án thí nghiệm).
Report từ chối ghép kết quả khác tuning ID; sau khi tune lại, phải chạy lại các bước đánh giá liên quan.

## Không gian tìm kiếm và công thức

- Whole-Text: k = 5, 10, 15, 20, 25, 30 (6 cấu hình).
- Flat 5-Facet: cùng dải k × 10 preset 5 chiều (60 cấu hình).
- Gated: cùng dải k × 8 tau × 3 kappa × 10 preset 4 chiều (1.440 cấu hình/backend).
- Tau TF-IDF: 0.15..0.50, bước 0.05; dense: 0.35..0.70, bước 0.05.
- Kappa tìm kiếm: 5, 10, 20. Sensitivity mở rộng thêm 2, 15, 30.
- Tiêu chuẩn mặc định: max CV Hit@3; hòa thì max MRR, max Macro-Hit@3, min k, hash config tăng dần.
- CV ghi sample std (ddof=1), lưu cả điểm từng fold. Fold được phân tầng, cân bằng tổng kích thước, seed=42.
- Train thực tế có 6 hội nghị chỉ có 3–4 bài, không đủ xuất hiện trong cả 5 validation fold.
  Phân phối số mẫu mỗi lớp giữa fold lệch tối đa 1; không nhân bản/oversample validation.
  JSON và report ghi rõ các lớp hiếm. Macro CV chỉ tính các lớp có mẫu trong validation fold tương ứng.
- Whole-Text dùng Title + Abstract; mỗi trường TF-IDF có vocabulary/IDF riêng, chỉ học từ reference Train của fold.
- Flat dùng trung bình cosine có trọng số của 5 facets quan sát được.
- Gated dùng sigmoid(kappa × (cos_problem − tau)) nhân trung bình có trọng số 4 facets giải pháp; thiếu Problem thì gate=0.5.
- Với k lớn hơn reference size, dùng toàn bộ reference; nên chọn grid k không vượt reference size của fold.
- Neighbor hòa điểm: paper_id tăng dần; venue hòa điểm: conference_id tăng dần, thống nhất runtime và CV.
- Random chỉ có kỳ vọng lý thuyết Hit@K=min(K,C)/C, MRR=H_C/C, không tune seed, không gán std=0 như số đo CV.

Các preset cụ thể nằm trong `search_space` của JSON tuning. Flat có 10 preset: equal, 4 heavy
(problem/task/method/dataset), method_task_focus, no_problem, no_task, no_method, no_dataset.
Không cần đủ mọi leave-one-out trong search Flat;
đây là ngân sách tìm kiếm đã công bố, không phải bảng ablation toàn bộ Flat.

Bảng 2 gồm 6 preset mô tả và 4 leave-one-out từ **weights thắng cuộc**, khác với preset ablation
dùng trong search (được tạo từ default). Tắt Problem gate là phép so sánh bổ sung với gate=1.
Nếu best đã cho một facet trọng số 0, bỏ facet đó sẽ không thay đổi kết quả: cần báo cáo trung thực.
Không kỳ vọng trước đường sensitivity phải có dạng chuông hoặc Gated phải thắng baseline.

## Tùy chỉnh và tính tái lập

Dùng `--k-list`, `--tau-list`, `--kappa-list`, `--metric`, `--seed`, `--n-splits`,
`--embedding-model`, `--device`, `--batch-size` để đổi thí nghiệm. Các tùy chọn ảnh hưởng nguồn gốc
phải được giữ giống khi chạy những stage tiếp theo; dữ liệu hoặc cấu hình không khớp sẽ gây lỗi.
Không dùng `--embedding-model` khi backend=all. Tuning artifact là cấu hình đóng băng; không sửa tay JSON.

Với file LLM khác, truyền `--extractor-manifest` trỏ tới JSON:

```json
{
  "Qwen-8B": "data/exp_a/generated/facets_silver.jsonl",
  "Qwen-14B": "data/conference_recommendation_dataset/generated_facets/Qwen14B/facets_silver.jsonl",
  "Qwen-4B": "data/conference_recommendation_dataset/generated_facets/Qwen4B/facets_silver.jsonl",
  "Llama-8B": "data/conference_recommendation_dataset/generated_facets/Llama8B/facets_silver.jsonl",
  "Gemma-9B": "data/conference_recommendation_dataset/generated_facets/Gemma9B/facets_silver.jsonl"
}
```

Đường dẫn trong manifest tính từ dự án thí nghiệm. Train luôn đọc từ `--facets-path`, chỉ Test lấy từ manifest.
Thiếu file, thiếu ID hoặc trùng ID gây lỗi; không âm thầm fallback cho pipeline v2.
Chấp nhận facet rỗng có chủ ý, nhưng không chấp nhận thiếu record của bài.

Các entry point cũ `run_cross_validation.py`, `run_baseline_cross_validation.py`, `run_grid_search.py`
đều chuyển sang tune chung **cả ba phương pháp**. `run_sensitivity_and_ablation.py` mặc định analyze;
`run_benchmark.py` mặc định benchmark. Chúng nhận cùng tham số như runner chính.
`evaluate.py` vẫn dành cho đánh giá thủ công từ config, không phải nguồn cho report v2;
Flat có thể nhận `flat_facet_weights` 5 chiều trong config.

## Kiểm tra trước khi chạy dài

```powershell
.\.venv-qwen\Scripts\python.exe -m unittest discover -s tests -p test_conference_protocol.py -v
```

Test dùng dữ liệu tổng hợp và dense encoder giả, không tải checkpoint hoặc chạy lại kết quả nghiên cứu.
Checkpoint dense thực phải có sẵn hoặc cho phép tải khi chạy thực nghiệm. JSON ghi phiên bản thư viện;
để tái lập lâu dài nên cố định môi trường và snapshot checkpoint đã dùng.
