# Hiểu và hoàn thành thí nghiệm D

> Cập nhật lựa chọn triển khai: người thực hiện đã chốt dùng workspace riêng trong `data/exp_d/workspace/`, chuẩn hóa hai bản sao về LF, giữ nguyên nguồn chung và manifest. Xem [hướng dẫn workspace](workspace.md), [tiến độ mới nhất](progress.md) và [audit workspace](../audit/step1_workspace_audit.json). Những mô tả lỗi nguồn bên dưới là chẩn đoán checkout gốc, không phải yêu cầu phải sửa file chung trước khi làm D. Dùng hướng dẫn workspace thay các lệnh cũ có output `data/exp_d/results/` khi gọi runner chung.

Ghi chú ngày 2026-10-15, dựa trên README, protocol hiện hành, code và dữ liệu đã kiểm tra trong workspace. Các con số bên dưới là trạng thái tại thời điểm kiểm tra, cần kiểm tra lại khi nhận dữ liệu mới.

**Giới hạn làm việc: chỉ tạo hoặc sửa file bên trong `data/exp_d/`.** Có thể đọc tài liệu, code và dữ liệu ở nơi khác để hiểu phụ thuộc, nhưng không sửa các file dùng chung, A, C, `configs/exp_d.json` hoặc `scripts/exp_d/`.

## 1. Hiểu đúng bài toán bạn phụ trách

D cần trả lời:

> Từ bài người dùng đang đọc, lịch sử và hành vi tìm kiếm/phản ứng đầu phiên, có suy được người dùng muốn tương tự hay khác biệt ở một facet, rồi dùng điều đó để khuyến nghị tốt hơn không?

Ví dụ: người dùng muốn giữ cùng **problem** nhưng tìm **method khác**.

Luồng hiện có:

```text
Facet A + lịch sử C
        ↓
Profile sở thích dài hạn
        +
Bài đang đọc + query/phản ứng đầu phiên D
        ↓
Dự đoán hướng similar / different / unknown
        ↓
Xếp hạng các bài ứng viên
        ↓
Chấm độ đúng hướng, ranking và mức tuân thủ intent
```

Theo protocol hiện hành:

- C suy sở thích dài hạn từ lịch sử đọc và tìm kiếm.
- D suy hướng similar/different trong phiên hiện tại.
- E nghiên cứu thích ứng theo thời gian.

Tên C/D đã được đổi so với kế hoạch hai tháng cũ. Dùng protocol hiện hành để xác định nhiệm vụ.

Notebook `paper-extractio-experimentA.ipynb` là công việc hỗ trợ A: dùng Qwen3 trích năm facet cho part 5, khoảng bài 3369–4210. Notebook đó không thực hiện D. Không cần chạy lại notebook A để bắt đầu nghiên cứu D.

D đã có generator, baseline và evaluator trong repo. Bạn không bắt đầu từ số 0; phần phương pháp nghiên cứu riêng vẫn cần triển khai. D cần dataset C hợp lệ, không cần chờ model C hoặc predictions của C.

## 2. Dữ liệu đã đủ chưa, cần tạo thêm gì?

**Đã có nguyên liệu để làm D, nhưng bộ D hiện tại chưa đủ tín hiệu để đánh giá đầy đủ hướng suy từ hành vi.**

| Thành phần | Hiện có | Việc còn lại |
|---|---|---|
| Corpus canonical | 4.210 bài, ID riêng biệt | Dùng nguyên corpus chung |
| A silver và metadata gộp | Mỗi file 4.210 bản | Dùng bản gộp, không dùng riêng part 5 |
| Cờ chất lượng A | 970 bản bị bộ lọc hiện hành loại | Không tự đổi chính sách lọc chung |
| Dữ liệu C | 300 users và logs | Cần handoff hợp lệ về hash/provenance |
| Phiên D | 1.500 phiên, mỗi phiên 20 candidates | Đủ quota phiên |
| Ground truth relevance D | 30.000 nhãn | Đủ quota nhãn |
| Search D | 1.500 sự kiện | Có 500 phiên mỗi nhóm clear/ambiguous/none |
| Cặp quan sát D | 0 exposures | Cần chẩn đoán và xử lý |
| Phản ứng trong phiên D | 0 interactions | Cần chẩn đoán và xử lý |

### 2.1. Lỗi đầu vào đang chặn runner

Hai lệnh đã được kiểm tra từ gốc project thực nghiệm:

```powershell
python data/exp_d/build_exp_d.py --validate-only
python scripts/exp_d/run_exp_d.py --dry-run
```

Cả hai dừng ở:

```text
Input checksum mismatch: data/processed/papers.jsonl
```

Hash của `papers.jsonl` khớp manifest khi chuyển CRLF về LF. `scripts/build_corpus.py` cũng có khác biệt xuống dòng tương tự trong hash generator C/D. Các file đầu ra được liệt kê trong manifest C/D khớp hash khi kiểm tra.

Đây chưa phải kết quả vượt qua toàn bộ validator: chương trình đang dừng ở lỗi đầu tiên.

**Cách xử lý theo phạm vi được giao:** ghi lại lỗi và chuyển cho người phụ trách dữ liệu/hạ tầng để nhận đầu vào đúng bytes. Không sửa corpus, code chung hoặc manifest C/A; không cập nhật hash tùy tiện để vượt kiểm tra. Chỉ sửa bên trong D không giải quyết được handoff C đang tham chiếu corpus không khớp hash.

### 2.2. D đủ số lượng nhưng thiếu tín hiệu hành vi

`generated/exposures.jsonl` và `generated/interactions_train.jsonl` đang rỗng. Vì vậy `direction_behavior` không có phản ứng trong phiên để suy hướng focus; phần không biết sẽ giữ `unknown`. Lịch sử C chỉ cung cấp importance dài hạn, không thay thế phản ứng trong phiên D.

Manifest `complete` phản ánh quota phiên/nhãn đã đạt, không chứng minh dữ liệu đủ cho mọi phép so nghiên cứu.

Generator D hiện chọn candidate pool trước, rồi tìm các cặp quan sát ở ngoài pool đó. Cần kiểm tra xem còn đủ bài same/different và đủ điều kiện ghép cặp hay không. Đây là điểm cần chẩn đoán, chưa phải nguyên nhân duy nhất đã được chứng minh.

Chạy lại nguyên config chưa chắc giải quyết được. Nếu sửa cách lấy mẫu trong `build_exp_d.py`, cần tạo config và output phiên bản mới trong D, ghi rõ thay đổi và giữ bộ cũ. Không tạo paper/facet giả hoặc nới điều kiện âm thầm để bù quota.

**Chưa có căn cứ phải cào thêm bài hoặc trích lại A.** Ưu tiên kiểm tra generator và pool hiện có trước.

### 2.3. Có thể chạy một phần dữ liệu không?

Có thể giảm số users/phiên/candidates để chạy pilot. Tuy nhiên, pipeline hiện hành vẫn yêu cầu A gộp complete và C handoff complete hợp lệ. Không thể chỉ trỏ `facets_path` vào part 5 để thay cho A đầy đủ.

Với giới hạn chỉ sửa D, có thể dùng C đầy đủ đã bàn giao và giảm `sessions_per_user` trong config D riêng. Nếu cần C pilot riêng, nhờ người phụ trách C chuẩn bị; không tự tạo/sửa file trong C.

Giảm quy mô không tự giải quyết việc thiếu cặp quan sát. Baseline suy hướng từ hành vi cần ít nhất hai cặp hợp lệ và chênh lệch phản ứng đủ mạnh theo config. Cần báo cáo số cặp thực tế và tỷ lệ phiên thiếu tín hiệu, không chỉ tổng số sessions.

## 3. Thứ tự làm để hoàn thành D

| Bước | Việc cần làm | Khi nào coi là xong? |
|---|---|---|
| 1. Làm đầu vào chạy được | Báo lỗi checksum, nhận handoff A/C hợp lệ; kiểm tra lại D | Validator và runner dry-run pass |
| 2. Làm dữ liệu D có tín hiệu | Chẩn đoán cặp rỗng; sửa generator D nếu cần; tạo pilot riêng | Có phiên đủ cặp để thử estimator, có thống kê coverage/thiếu tín hiệu |
| 3. Chạy baseline | Chạy các phương pháp có sẵn, đọc điểm và case sai | Có kết quả baseline tái lập được |
| 4. Thêm phương pháp của bạn | Cải thiện suy hướng/query/reactions/confidence trong code riêng thuộc D | Phương pháp mới chạy cùng giao diện và evaluator |
| 5. So sánh công bằng | Giữ cùng data, candidates, cutoff và profile C khi so direction | Có bảng đối chiếu và phân tích nguyên nhân |
| 6. Viết và bàn giao | Mô tả dữ liệu, phương pháp, kết quả, lỗi và giới hạn | Có code/config, manifest, báo cáo và hướng dẫn chạy lại |

### 3.1. Các đối chứng cần giữ

- `fixed_similar`: trọng số đều, tất cả similar.
- `profile_similar`: importance từ C, tất cả similar.
- `direction_behavior`: thêm hướng từ phản ứng trong phiên.
- `direction_search`: thêm tín hiệu tìm kiếm.
- `oracle_intent`: evaluator biết intent thật; đối chứng đặc quyền, không phải phương pháp triển khai cho người dùng.

Giữ profile C cố định khi so các bộ suy direction để xác định nguồn cải thiện.

### 3.2. Triển khai trong giới hạn chỉ sửa D

Không sửa `scripts/exp_d/run_exp_d.py` hoặc `scripts/baseline_common.py`. Đọc chúng làm tham chiếu, rồi tạo runner/phương pháp riêng bên trong `data/exp_d/`, sử dụng lại helper và evaluator chung qua import khi phù hợp.

Một cách tổ chức đề xuất, chưa phải các file đã triển khai:

```text
data/exp_d/
  build_exp_d.py          # Generator hiện có; nơi chẩn đoán cặp quan sát
  configs/               # Config D riêng, dùng --config
  methods/               # Phương pháp nghiên cứu riêng
  run_research_d.py      # Runner riêng nếu cần thêm phương pháp
  tests/                 # Kiểm tra liên quan đến thay đổi D
  samples/               # Pilot D
  results/               # Output kết quả, vẫn nằm trong phạm vi D
  docs/Understand_D.md    # Ghi chú cá nhân, được .gitignore bỏ qua
```

Giữ giao diện `predict(papers, facets, cases, history, options)` và dùng evaluator chung nếu không đổi protocol. Kiểm tra cách runner import và ghi output trước khi triển khai runner riêng.

Config mặc định nằm ngoài phạm vi sửa. Tạo config riêng bên trong D, truyền bằng `--config`; các đường dẫn trong config vẫn tính từ gốc project thực nghiệm. Chọn `output_dir`, `truth_dir` và `--output` nằm trong D. Không ghi đè bộ dữ liệu/kết quả cũ.

Sau khi đầu vào và dữ liệu đã hợp lệ, lệnh mẫu cho baseline có sẵn là:

```powershell
# Chạy từ paper-and-conference-recommendation-experiments.
# Thay đường dẫn config/output bằng phiên bản thực tế đã chuẩn bị.
python data/exp_d/build_exp_d.py --config data/exp_d/configs/pilot.json --dry-run
python data/exp_d/build_exp_d.py --config data/exp_d/configs/pilot.json
python data/exp_d/build_exp_d.py --config data/exp_d/configs/pilot.json --validate-only
python scripts/exp_d/run_exp_d.py --config data/exp_d/configs/pilot.json --output data/exp_d/results/pilot_baseline --dry-run
python scripts/exp_d/run_exp_d.py --config data/exp_d/configs/pilot.json --output data/exp_d/results/pilot_baseline --ks 5 10
```

Các lệnh này là hướng dẫn sau khi chuẩn bị; file `configs/pilot.json` chưa được tạo bởi ghi chú này. Chạy script bên ngoài D không đồng nghĩa sửa script đó, nhưng cần chỉ định output nằm trong D.

### 3.3. Phần nghiên cứu và đánh giá

Chạy baseline là mốc đầu tiên. Phần nghiên cứu tiếp theo cần một phương pháp/biến thể được chọn và phân tích kết quả. Có thể cải thiện parser query, kết hợp evidence phản ứng/search hoặc confidence/abstention. Biểu diễn semantic là phép thử khác; thêm embedding không tự cải thiện direction F1 nếu estimator giữ nguyên.

Đánh giá tối thiểu:

- Direction macro-F1, accuracy và coverage.
- nDCG, Recall, Precision, MRR ở các cutoff đã chốt.
- Intent compliance@5/10: tỷ lệ kết quả grade 2, thỏa cả context và hướng focus.
- Phân nhóm clear/ambiguous/none, similar/different và facet nếu số mẫu cho phép.
- Số cặp quan sát thực tế, tỷ lệ abstain và phân tích case sai.

Grade 1 vẫn được tính dương cho Recall/MRR nhưng có thể sai hướng. Không dùng ranking metrics riêng để kết luận đã suy intent tốt. Không truyền hidden focus/directions/weights hoặc relevance truth vào scorer thông thường; chỉ evaluator/oracle được dùng chúng. Giữ cutoff và không dùng phản ứng tương lai.

Chốt cách tune trước khi đánh giá cuối, không chỉnh theo điểm test. Khi đổi generator/config/input, tạo dataset tương ứng và chạy lại tất cả đối chứng trên cùng phiên bản. Không so trực tiếp điểm từ các bộ candidates/nhãn khác nhau.

Kết quả bàn giao gồm `predictions.jsonl`, `details.jsonl`, `report.json`, `summary.csv`, `report.md`, `manifest.json`, kèm code/config và cách chạy lại. Dữ liệu hành vi/intent là mô phỏng trên bài thật và facet silver; kết quả chưa chứng minh hiệu quả trên người dùng thật.

## 4. Đọc file nào để bắt tay làm?

Các đường dẫn dưới đây tương đối từ thư mục `data/exp_d/docs/`:

1. [README runner D](../../../scripts/exp_d/README.md): tài liệu sát nhiệm vụ nhất; baseline, công thức, metrics và hướng nghiên cứu.
2. [README dữ liệu D](../README.md): cách sinh phiên, cặp quan sát và ground truth.
3. [Protocol hiện hành](../../../docs/EXPERIMENT_PROTOCOL.md): đọc phần D và ranh giới quan sát.
4. [Giao diện baseline](../../../scripts/BASELINE_GUIDE.md): giao diện predict, evaluator và output.
5. [Kế hoạch phát triển A–E](../../../docs/EXPERIMENT_PLAN_FINAL.md): đọc phần D; các dòng trạng thái dữ liệu là snapshot cũ, cần đối chiếu dữ liệu hiện có.
6. [Hướng dẫn pilot D](../samples/README.md): tham khảo cách giảm quy mô; nếu cần C pilot thì nhờ người phụ trách C chuẩn bị.
7. [Quy trình chạy](../../../docs/RUN_EXPERIMENTS.md), [chỉ mục dữ liệu](../../README.md) và [chỉ mục script](../../../scripts/README.md): các tài liệu được dẫn từ mục “Bắt đầu từ đâu?” của README gốc.

Code cần đọc:

- [Runner baseline D](../../../scripts/exp_d/run_exp_d.py): cách gọi các phương pháp đối chứng; chỉ đọc.
- [Helper dùng chung](../../../scripts/baseline_common.py): `facet_profiles()`, `direction_estimate()`, `intent_scores()`; chỉ đọc.
- [Runner/evaluator chung](../../../scripts/experiment_runner.py): điều phối dữ liệu, oracle và output; chỉ đọc.
- [Generator D](../build_exp_d.py): nơi có thể sửa trong phạm vi được giao.

**Ưu tiên ngay:** nhận đầu vào vượt kiểm tra checksum, làm pilot D có tín hiệu hành vi, lấy kết quả baseline, rồi mới phát triển và đánh giá phương pháp riêng. Không cần tải thêm model hoặc thu thập thêm corpus trước khi xử lý hai vấn đề dữ liệu hiện tại.
