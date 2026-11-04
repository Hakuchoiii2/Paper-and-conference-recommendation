# Qwen — Kaggle pilot 50 bài

## Lượt hiện hành: prompt 3.6, T4 ×2

**Kernel version 8 đã push, CLI xác nhận RUNNING.** Review theo scope
problem/dataset và facet có lỗi; giữ các facet hợp lệ khác, đổi feedback khi lặp,
ưu tiên review mới khi hòa điểm và giữ whether trong câu hỏi nguồn. Dataset rà
cả câu findings và tách resource độc lập. Engine3.7; scorer/validator3.1 và filter
named-resource cũ, evaluator,
reference/ngưỡng và cùng50 ID giữ nguyên. Output `generated_v3_6_pilot50/`,
hai worker25 bài/GPU; 165 test qua. Chưa có điểm semantic3.6.
Xem [phạm vi, thử offline và xác minh push](archive/README.md).

## Lượt đã hoàn tất: prompt 3.5, T4 ×2

Kernel **version 7 đã COMPLETE**, tải và chấm đủ 50 bài; log xác nhận hai Tesla T4
thực tế, 25 bài/GPU, ~38 phút. Problem F1 **14,63% → 43,14%**; micro
**53,82% → 53,88%**, gần như đứng yên vì task/dataset/contribution giảm.
Ưu tiên problem: nhận diện limitation có căn cứ trong background, kiểm tra trước
khi để [], bỏ nhóm ví dụ problem để tránh chép nhầm. Giữ cùng 50 ID,
evaluator/reference/ngưỡng, scorer/ranking, validator và dataset filter.
Output `generated_v3_5_pilot50/`, engine 3.6; đã kiểm hash/replay merged output
và hai shard. 159 test qua trước push. Xem [kết quả và lỗi còn lại](archive/README.md).

## Lượt đã hoàn tất: prompt 3.4, T4 ×2

**Kernel version 6 đã COMPLETE, khôi phục 50 bài sau lỗi merge của v5.**
V5 đã sinh đủ 25 bài trên mỗi T4; merger dùng nhầm vị trí trong toàn corpus.
Merger 1.1 sửa theo selected cohort; v6 chỉ resume/gộp, không gọi lại Qwen.
Micro-F1 v3.4 **53,82%**, so với v3.3 52,57%; problem/dataset vẫn hồi quy.
Sửa review cho output rỗng và phân biệt
problem/task/finding; giữ scoring/ranking 3.1, method/contribution của v3.3.
Hai process chạy song song, mỗi GPU 25 bài, checkpoint riêng; gộp sau khi kiểm
đủ 50 ID/provenance. Config dùng prompt 3.4, engine 3.5, `gpu_workers=2` và
output `generated_v3_4_pilot50/`. 157 test qua; source remote khớp bản gửi,
log xác nhận hai T4 và phục hồi đủ các phần.
Xem [hồ sơ v3.4](archive/README.md),
[push report](../../../data/exp_a/.kaggle/pilot/push_report.json) và
[xác minh v3.4](../../../data/exp_a/.kaggle/review/pilot50_v3_4_recovery_verification.json).

## Lượt đã hoàn tất: prompt 3.3

Đã push kernel **version 4** ngày 15/10/2026; hiện CLI xác nhận **COMPLETE**.
Đã tải đủ 50 bài, kiểm hash/replay và chấm đạt **52,57% micro-F1**, tăng
**0,68 điểm %** so với v3.1 có filter. 31 validation pass, 19 fallback.
Xem [kết quả và lỗi v3.3](archive/README.md) và
[xác minh hoàn tất](../../../data/exp_a/.kaggle/review/pilot50_v3_3_verification.json).
Dataset private version 4 đã ready trước khi push. Mã tải lại khớp SHA-256
bản gửi; metadata xác nhận đúng owner, private, GPU T4 và Internet bật.
147 test qua (87 project, 60 exp_A), review độc lập không còn lỗi chặn push.
Push provenance v3.3 được giữ trong `kaggle_runs.prompt_3_3` của
[comparison.json](../../../data/exp_a/evaluation/pilot50_comparison_ai_v1/comparison.json).

Lượt này chỉ sửa extraction: method tách thành kỹ thuật/tên mô hình gọn;
task giữ mục tiêu và setting; contribution lấy đủ artifact và findings dương/âm,
giữ số liệu đúng metric/setting; problem cần hạn chế hoặc câu hỏi có trong nguồn.
Prompt và review dùng ví dụ tổng hợp, không chèn nhãn của pilot/reference.
Giữ validation/scoring/ranking 3.1 và bộ lọc dataset named resource đã cải thiện
điểm; không bật lại cách gộp method hoặc inventory dài của prompt 3.2.

Config của lượt này dùng `extraction_v3_3.md`, prompt 3.3, guideline/policy 3.1,
engine 3.4 và `dataset_resource_filter=true`. Output riêng:
`data/exp_a/generated_v3_3_pilot50/`; không resume nhãn cũ.
Giữ cùng 50 ID, seed, model/revision, NF4, do_sample=false, ngân sách ba lượt,
corpus, reference AI và evaluator/ngưỡng 0.85. Không sửa nguồn dữ liệu.
**F1 v3.3 là 52,57%**; mốc so sánh là bản v3.1 có filter đạt 51,89%.
Pilot này đã dùng phát triển nên kết quả là đối chiếu trên dev.

## Bản được giữ sau đối chiếu offline

Mốc đối chứng được giữ dùng prompt/guideline/scoring/ranking 3.1 và bật
`dataset_resource_filter=true`; chỉ áp guard named resource 3.2 sau khi chọn
attempt. Engine 3.3 ghi audit các nhãn bị lọc, replay được từ raw đã lưu và
không tự gọi lại Qwen cho các bản v3 đã hoàn tất self-review khi resume.
Output đối chứng: `data/exp_a/generated_v3_1_filtered_pilot50/`, được dẫn xuất
từ v3.1 và chấm lại đạt 51,89% micro-F1 trên cùng reference/ngưỡng 0.85.
Hai output v3.1/v3.2 gốc giữ nguyên. Bản có filter được dẫn xuất offline;
lượt sinh mới bằng prompt 3.3 ở trên dùng nó làm mốc so sánh.
Xem [bản được giữ và lỗi v3.1 còn lại](archive/README.md).

## Lượt chạy lại v3.2

**Đã COMPLETE, nhưng chất lượng hồi quy:** micro-F1 50,41% → 35,94%,
validation pass 26 → 17 và fallback 24 → 33 trên cùng reference/evaluator.
Xem [báo cáo v3.2](archive/README.md).
Config v3.2 để tái hiện nằm trong provenance của output gốc; config chạy hiện hành
đã chuyển sang prompt 3.3 có dataset filter ở trên. Chưa chạy toàn corpus.

Đã push thành kernel version 3 ngày 15/10/2026, xác nhận RUNNING trên GPU T4.
Dataset đã ready trước khi push; mã tải lại khớp SHA-256 bản gửi. Metadata remote
xác nhận đúng owner, private và Internet bật. 139 test qua (87 project, 52 exp_A),
review độc lập không còn lỗi chặn push. Hash/cấu hình/trạng thái lúc push được ghi
trong `kaggle_runs.prompt_3_2` của
[comparison.json](../../../data/exp_a/evaluation/pilot50_comparison_ai_v1/comparison.json);
hai tệp push_report/verification hiện hành đã chuyển sang lượt prompt 3.3.

Lượt v3.2 giữ đúng 50 ID, seed, checkpoint model/revision, NF4, do_sample=false và ngân
sách ba lượt của v3.1. Config của lượt đó trỏ tới
`data/exp_a/generated_v3_2_pilot50/`; không resume output v3.1 với policy mới.
Prompt/guideline của lượt đó là `extraction_v3_2.md` và `facet_guideline_v3_2.md`.
Các prompt 3.1 được giữ để đọc lại mốc đối chứng.

- Bỏ thưởng theo số facet có nhãn và độ sao chép nguyên chữ; điểm 3.2 là tỷ lệ
  item qua validator, vẫn không phải độ tin cậy ngữ nghĩa. Facet rỗng hợp lý
  không làm giảm điểm. Nếu điểm bằng nhau, fallback ưu tiên review rồi lượt mới.
- Review lập danh sách ý từ nguồn trước khi đối chiếu draft: task, kỹ thuật,
  resource, artifact mới, findings dương/âm và điều kiện áp dụng.
- Chặn các dạng dataset chung chung/tên ngôn ngữ rõ ràng; giữ named benchmark.
  Quy tắc vẫn là heuristic, chưa chứng minh mọi proper name là dữ liệu.
- Giữ câu hỏi whether, leading conditions (when/if/under/for), và phân biệt phủ
  định ở background với finding đối lập. Bổ sung cờ thiếu finding thực nghiệm
  âm có tín hiệu rõ; không coi phủ định trong method/class label là finding.
- Gắn cờ abstract có dấu hiệu cụt hoặc lỗi encoding; giữ nguyên nguồn.
- Metadata ghi policy 3.2 và replay đúng policy. Các output v3.1/v2 được đọc bằng
  policy tương ứng và migration chỉ nhận đúng fingerprint đã biết.

Matcher, reference pilot50 và ngưỡng 0.85 giữ nguyên để đối chiếu extraction.
Pilot50 đã dùng phát triển các sửa này; kết quả chạy lại là phép so trên dev,
không phải test chất lượng độc lập. Điểm sau run được ghi trong báo cáo ở trên.

## Mốc v3.1 và cách vận hành

Owner Kaggle: `htnkhi`. Chọn ngẫu nhiên 50 trong 3.810 bài ngoài reference 400,
seed `20261014`, không chọn theo điểm Qwen. Danh sách và hash nằm trong
`data/exp_a/pilot50/selection.json`; bản nhãn cũ cùng 50 ID nằm ở
`data/exp_a/pilot50/baseline_silver.jsonl` để so sánh sau.

Config: `data/exp_a/config_v3_pilot50.json`. Giữ checkpoint
`Qwen/Qwen3-4B-Instruct-2507`, revision `cdbee75f17c01a7cc42f958dc650907174af0554`,
NF4 4-bit, float16, `do_sample=false`. Lượt đầu trích, các lượt tiếp theo rà/sửa
nguồn và bản trích kể cả khi nháp còn lỗi. Ngân sách tối đa ba lần sinh; không
gọi model judge. Mỗi lượt có điểm bám nguồn theo validator v3, không áp ngưỡng
retention 70% của luồng local cũ và không diễn giải điểm thành độ tin cậy ngữ nghĩa.

Prompt và guideline mới ở `data/exp_a/prompts/`. Mỗi nhãn có evidence ID; validator
cho rút gọn bằng từ nguồn theo thứ tự, chặn mất phủ định trong span hoặc ngay
trước finding, số liệu nằm trong span finding và điều kiện/caveat ngay sau claim.
Prompt 3.1 có ví dụ chọn evidence, không đổi từ/đảo thứ tự, không biến bối cảnh
"growing interest" thành problem và không bỏ giới hạn "partially successful".
Kiểm tra này không chứng minh
đúng facet hoặc đầy đủ ngữ nghĩa; lượt rà Qwen cũng chưa phải kiểm định độc lập.

V3.1 lưu kết quả đã qua rà hợp lệ với `validation_passed=true`. Nếu hết lượt vẫn
lỗi, chọn best attempt theo điểm, giữ nguyên các lỗi, ghi `fallback_used=true`
và `validation_passed=false`. Bản nháp hợp lệ nhưng không có lượt rà hợp lệ cũng
phải mang cờ fallback. Mọi raw response, lỗi theo facet/index/evidence và điểm
được lưu tại `attempt_audits/<paper_id>.json` sau từng lượt; metadata/manifest
giữ audit và danh sách fallback. Missing/failed dùng cho bài chưa có bản ghi.
Source-quality flags phát hiện boilerplate tải sách hoặc dấu hiệu vỡ từ; không
tự nối từ hay sửa corpus, và không ép điền facet khi nguồn không có bằng chứng.
Luồng v2 vẫn cần cho kiểm tra silver hiện hành và các caller cũ; pilot bật v3 bằng
`extraction_protocol=two_pass_v3`, có hash module riêng trong provenance.

Chạy từ gốc project bằng PowerShell:

```powershell
& ./data/exp_a/.kaggle/pilot/kaggle.ps1 build
& ./data/exp_a/.kaggle/pilot/kaggle.ps1 push
& ./data/exp_a/.kaggle/pilot/kaggle.ps1 status
& ./data/exp_a/.kaggle/pilot/kaggle.ps1 download
```

`push` xác minh account thực tế bằng CLI rồi so với settings; dataset và kernel
private, GPU T4, Internet để tải checkpoint/package. Kernel ID:
`htnkhi/exp-a-qwen-v3-pilot50`; dataset ID: `htnkhi/exp-a-qwen-v3-pilot50-inputs`.

Gói upload dùng allowlist code và corpus, có SHA-256 và archive member checks;
không mang credential, reference, nhãn baseline hoặc embedding matcher vào runtime.
Cache model nằm ở `/tmp/exp_a_huggingface` để không đóng gói weights trong output.
Kaggle dùng torch sẵn có, pin transformers 4.57.6, accelerate 1.15.0,
bitsandbytes 0.50.2 theo môi trường local đã kiểm tra.

Output Kaggle:
- `pilot_run_summary.json`: số bài lưu, số qua validation, số fallback, cờ chất
  lượng nguồn, failed/missing và thời gian. Count=50 không có nghĩa 50 bài đúng ngữ nghĩa.
- `exp_a_run/data/exp_a/generated_v3_4_pilot50/`: silver, metadata (mọi raw
  responses và evidence), manifest, checkpoint và `attempt_audits/` từng bài.

Lần v3.0 cũ hoàn thành 5/50 bài; output tải về được giữ trong `.kaggle/downloads/`.
Không resume checkpoint v3.0 với policy mới. V3.1 dùng output_dir riêng nhưng giữ
nguyên 50 ID và seed để so sánh. Xem [báo cáo lỗi lần đầu](archive/README.md).

Để resume qua phiên Kaggle, tải output đã lưu về đúng output_dir local rồi build
lại: packager kiểm tra provenance/hash trước khi đưa ba tệp export vào input.
V3 xuất JSONL/manifest sau từng bài đã commit. Nếu phiên bị ngắt cứng trước khi
export hoàn tất, packager kiểm tra provenance và từng annotation trong SQLite,
phục hồi lại export mà không gọi model. Runtime phục hồi checkpoint từ export
và chỉ trích bài còn thiếu. Không dùng kết
quả 50 bài làm silver toàn corpus, không ghi đè `data/exp_a/generated/`.

Đã có [điểm thử nghiệm pilot50 ngày 15/10/2026](archive/README.md):
v3.1 lưu đủ 50 bài, 26 qua validation và 24 fallback. Trên cùng tham chiếu AI
source-only đã chốt trước khi mở nhãn mới, micro-F1 tăng từ 39,41% của silver cũ
lên 50,41%, giữ nguyên evaluator/ngưỡng 0.85. Đây là agreement với AI reference,
chưa phải human-confirmed semantic F1. Chưa chạy lại 4.210 bài.

Lần v3.0 được push version 1 lên [kernel private](https://www.kaggle.com/code/htnkhi/exp-a-qwen-v3-pilot50),
trạng thái tại thời điểm push là RUNNING lúc 00:13 ngày 15/10/2026 (UTC+7). Metadata remote
xác nhận owner htnkhi, private, GPU T4 và Internet; source tải lại khớp bản gửi.
Lần push đầu có 115 kiểm tra code qua. Hai tệp push_report/verification hiện
theo dõi lần push mới nhất; không dùng chúng làm bằng chứng hash cho lần đầu.

V3.1 đã push thành kernel version 2 ngày 15/10/2026. Trạng thái sau push được
xác nhận RUNNING; dataset ready, kernel private, GPU T4, Internet bật. Source
tải lại từ Kaggle khớp SHA-256 bản gửi. 125 kiểm tra qua (87 project, 38 exp_A),
review độc lập không có lỗi chặn push. Tại thời điểm push chưa có điểm ngữ nghĩa;
kết quả sau khi hoàn tất được ghi trong báo cáo pilot50 ở trên. Không suy ra
chất lượng nhãn từ trạng thái RUNNING hay số bài được lưu.
