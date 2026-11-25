# Kaggle policy matrix v4 — kết quả 8B và kiểm tra local

Kernel `htnkhi/exp-a-qwen-facet-matrix/4` đã COMPLETE. Đủ 30 paper ×3 nhánh,
90 signed records. Original vẫn tốt nhất; chưa thay prompt/handoff production.
Theo yêu cầu mới của người dùng, không sửa nhánh policy thành original + policy
và không chạy lại kernel trong lần kiểm tra này.

## Kết quả cùng 30 paper

| Nhánh 8B | TP | FP | FN | Precision | Recall | Micro F1 | Macro F1 | Fallback |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| original, tái sử dụng | 141 | 78 | 105 | 64.38 | 57.32 | **60.65** | **61.64** | 21/30 |
| policy | 116 | 98 | 130 | 54.21 | 47.15 | 50.43 | 45.02 | 21/30 |
| policy_examples | 115 | 77 | 131 | 59.90 | 46.75 | 52.51 | 51.89 | 9/30 |

Các điểm là phần trăm. Policy giảm 10,21 điểm phần trăm micro; policy_examples
giảm 8,13 điểm so original. Thêm ví dụ vào policy giảm 21 FP nhưng mất thêm 1 TP:
điểm tăng nhờ giảm nhãn thừa, không phải tăng số nhãn khớp. So với original,
policy_examples mất 26 TP và chỉ giảm 1 FP.

| Facet F1 | Original | Policy | Policy + examples |
|---|---:|---:|---:|
| problem | 57.69 | 26.42 | 27.78 |
| task | 58.43 | 55.56 | 48.78 |
| method | 64.56 | 57.14 | 58.82 |
| dataset | 70.00 | 35.29 | 73.68 |
| contribution | 57.53 | 50.68 | 50.38 |

Dataset chỉ có 9 nhãn tham chiếu. Original và policy_examples đều khớp 7, thiếu 2;
nhãn thừa giảm 4→3, làm F1 tăng 70,00→73,68. Không có thêm TP dataset trong so sánh
này và cải thiện nhỏ đó không bù 26 TP mất ở các facet khác.

## Lỗi còn tập trung ở đâu

| Facet | FP+FN original | FP+FN policy | FP+FN policy_examples |
|---|---:|---:|---:|
| problem | 22 | 39 | 26 |
| task | 37 | 40 | 42 |
| method | 56 | 66 | 70 |
| dataset | 6 | 11 | 5 |
| contribution | 62 | 72 | 65 |
| Tổng | 183 | 228 | 208 |

Method + contribution chiếm 64,5% số FP+FN của original, 60,5% của policy và
64,9% của policy_examples. Đây là hai facet có nhiều lỗi nhất theo bộ chấm.
Problem giảm F1 mạnh nhất; nhánh có ví dụ để problem rỗng ở 8 bài có reference,
so với 3 bài ở original. Không chỉ có lỗi rỗng: nhãn problem quá chung hoặc khác
quy ước reference cũng gây mất TP.

Ví dụ đọc trực tiếp source, raw attempts và evaluation:

- **P001211, method:** original khớp 6/7 method; policy_examples khớp 3/7.
  Bỏ `insert typos`, `change word boundaries`, `add innocuous words`,
  `word-level features`; có thêm nhãn reproduce models mà original thiếu.
  Raw extract chỉ có reproduce models, review thêm adversarial training và
  character-level features nhưng vẫn bỏ bốn thành phần trên. Không phải parser
  xóa bốn method sau sinh.
- **P002380, contribution:** original khớp ba artifact; policy_examples chỉ sinh
  một câu dài gộp array-parameter solution và modularization facility, đồng thời
  thiếu nhãn two language design methods. Ba nhãn reference đều không được ghép.
  Có cả thiếu artifact, sai mức tách ý và độ dài biểu diễn; không thể gọi cả ba FN
  là ba ý hoàn toàn vắng khỏi văn bản model sinh.
- **P002684, task:** policy_examples dùng tiêu đề về integrating joint n-gram
  features làm task, bỏ `letter-to-phoneme conversion` và `name transliteration`.
  Task này hợp lệ về nguồn nhưng sai vai trò so với mục tiêu trong abstract.
  Review scope không mở task, nên raw sai được giữ nguyên ở lượt sau.
- **P003441, contribution:** policy_examples chỉ sinh `LightRocks`, bỏ graphical
  editor và three abstraction levels. Bộ chấm cũng không ghép `LightRocks` với
  `LightRocks (Light Weight Robot Coding for Skills)`, dù source xác nhận cùng tên.
  Trong ba FN ở đây, hai là bỏ sót nội dung và một là biểu diễn/tên tương đương.
- **P001409, contribution:** model vẫn sinh hai câu chứa đúng 75.60% và 70.65%,
  kèm nhiều đối chứng/điều kiện; các nhãn dài này không được scorer ghép với nhãn accuracy ngắn.
  Ngoài ra thiếu artifact POS tool và thêm câu training/testing làm contribution.
  Điểm này trộn lỗi coverage/role với giới hạn biểu diễn của semantic matching.

Policy v1 định nghĩa problem là limitation/unresolved question thúc đẩy nghiên cứu,
loại một new negative result đứng riêng. Reference ở P001211 lại nhận finding
`models perform well only when tested on the same type of data they were trained on`
là problem. Đây là bằng chứng có khác biệt quy ước nhãn cần rà, không chỉ lỗi
tuân thủ prompt. Không đổi reference hay threshold sau khi thấy kết quả.

## Lỗi grounding và review còn lặp

Số lỗi validation ở đầu ra được chọn: original 58, policy 51, policy_examples 12.
Phần lớn là không giữ từ nguồn đúng thứ tự; còn lỗi rút ngắn bỏ phủ định.
Số bài có ít nhất một lỗi validation giống nguyên văn giữa extract đầu và kết quả
được chọn: 20/30, 20/30, 7/30 tương ứng. Vì vậy ví dụ giúp grounding/review flags,
nhưng chưa giải quyết coverage/roles. Đây là đếm lỗi validation lặp trong cùng bài,
không phải đếm mọi lỗi ngữ nghĩa hay tỷ lệ lỗi giữa các version.

Phát lại 60 record mới qua extractor/review hiện có khớp hoàn toàn facets, audit,
usage, generation_seconds và fallback. Các hiện tượng trên đã có trong raw/review;
không phát hiện sai lệch xử lý hoặc thiếu record trong lần kiểm tra này.

## Xác minh và giới hạn

- Bundle SHA256 `6c57e37c810e6a8ffcf6ae54845641bf76ff969ea938e5035cb9189802c586c4`.
- Generation signature `22c5003b392245266c4ec34415e5e2b83cf729329798769e4eab69615c196ea7`.
- Input source/reference tải từ Kaggle khớp byte với bundle đã duyệt; settings
  và các file trong bundle khớp hash. Code dùng replay/scoring khớp bundle.
- 90 checkpoint kiểm signature + record checksum; 60 record mới raw replay.
- Chấm local 621 label, 450 ô paper/facet, Qwen3-Embedding-0.6B revision đã khóa,
  threshold 0.85, numeric/negation/task guards và ghép một-một giữ nguyên.
  TP/FP/FN, missing/extra và aggregate scores khớp Kaggle; sai khác macro cuối
  khoảng 2e-16 do floating point được chấp nhận trong tolerance 1e-12.
- Qwen3-8B NF4 double, thinking=false; model revision và extract/review 3.7 giữ
  nguyên. Original là kết quả tái sử dụng; không phải control sinh mới cùng run.
- 20 bài rà policy bị loại khỏi 30 bài chấm, nhưng cả 30 là dev từng dùng.
  Reference là AI, chưa phải human gold. Điểm là agreement theo quy ước hiện tại,
  không phải độ chính xác tuyệt đối hoặc bằng chứng tổng quát hóa.
- Nhánh policy thay thế prompt gốc, không phải bổ sung policy vào original.
  Kết quả này không trả lời phép thử original + policy và không chứng minh rằng
  mọi cách thêm policy đều kém. Người dùng đã yêu cầu dừng sửa phép thử đó.

Artifacts ở `data/exp_a/evaluation/policy_matrix_kaggle_v4/`: bảng điểm, evaluation
từng nhánh, 90 signed records, input snapshot, `verification.json`, `error_audit.json`.
Log/API download ở `.kaggle/downloads/policy_v4/`; script kiểm tra chỉ ở
`tmp/verify_policy_kaggle_v4.py`. Không sửa prompt, extractor, evaluator hoặc chạy
fine-tuning/kernel mới. Original tiếp tục là baseline tốt nhất trong ba nhánh.
