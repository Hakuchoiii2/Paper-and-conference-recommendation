# Nhật ký thay đổi cải tiến D và hướng dẫn backup/restore

Ngày thực hiện: 16/10/2026. Lượt chạy: `improve_m0_20261016_v1`. Đây là **thử nghiệm phát triển M0 và ablation active-facets** theo [improve_plan.md](improve_plan.md), chưa phải triển khai RankNet/LambdaMART hoặc đánh giá cuối trên test độc lập.

## 1. Đã thay đổi những file nào?

**Chỉ thêm file mới; không sửa bất kỳ file nguồn đã có nào trong lượt triển khai này.** Vì vậy baseline vẫn chạy như trước, không cần khôi phục code gốc để trở lại baseline.

Đường dẫn dưới đây tính từ gốc `paper-and-conference-recommendation-experiments/`:

| File mới | Chức năng |
|---|---|
| `scripts/exp_d/intent_priority.py` | Hai public reranker không huấn luyện: `priority` và `active`; chọn focus từ directions/confidence dự đoán, không nhận hidden intent/labels |
| `scripts/exp_d/run_improve_trial.py` | Đọc snapshot và predictions baseline đã lưu, kiểm hash, chạy reranking trên canonical + 6 cấu hình pilot, chấm bằng evaluator cũ và xuất kết quả riêng |
| `scripts/exp_d/test_intent_priority.py` | 5 kiểm tra hành vi: tác dụng của direction, fallback, facet thiếu, weights và ranh giới public/oracle/candidate pool |
| `data/exp_d/docs/changed_improve.md` | Chính nhật ký này: phạm vi, lệnh chạy, kết quả và restore |
| `data/exp_d/results/improve_m0_20261016_v1/` | Toàn bộ output mới; không ghi đè kết quả baseline |

Chưa thay `run_baseline_pipeline.py` hay `run_synthetic_observation_pilot.py`: dùng runner thử nghiệm riêng để đọc output đã có, giữ simulator và lựa chọn phiên cố định. `scripts/exp_d/run_exp_d.py` và bản `run_exp_d copy.py` của người dùng được giữ nguyên. Không sửa corpus, A/C, generator D, config chung, scorer/evaluator/validator dùng chung hoặc dữ liệu nguồn.

## 2. Hai phương án mới làm gì?

### `intent_priority_behavior` / `intent_priority_search`

Giữ nguyên directions và confidence từ `direction_behavior` / `direction_search`. Focus dự đoán là facet ngoài context có direction similar/different và confidence dương mạnh nhất duy nhất. Không có evidence hoặc hòa confidence giữa nhiều facet thì giữ nguyên ranking baseline.

Nếu suy được focus, chia candidates theo **quan sát**:

1. Có đủ context/focus, overlap context và thỏa hướng focus dự đoán.
2. Có đủ context/focus, overlap context nhưng không thỏa hướng focus dự đoán.
3. Không overlap context hoặc thiếu dữ liệu context/focus cần dùng.

Ưu tiên nhóm 1 rồi 2 rồi 3. Trong cùng nhóm giữ thứ tự điểm baseline, hòa điểm dùng paper ID theo quy tắc baseline. Điểm mới mã hóa thứ tự nhóm, không phải xác suất relevance.

Khác với scorer cũ: sử dụng concept overlap trực tiếp và ưu tiên điều kiện intent trước tổng điểm mềm; facet ngoài context/focus không làm candidate bị loại vì thiếu annotation. Đây là thay đổi policy có chủ đích, không phải sửa một bug được xác nhận. M0 thay nhiều đặc tính scorer nên chưa thể quy kết toàn bộ lợi ích cho riêng weights hay missingness.

### `intent_active_behavior` / `intent_active_search`

Giữ cùng cách chọn focus dự đoán, cùng TF-IDF và hàm score cũ. Chỉ giữ importance C ở context và focus đã suy được rồi chuẩn hóa lại; các facet khác weight 0. Không lấy weights thật 0,6/0,4 từ ground truth. Thiếu evidence hoặc tổng weights active bằng 0 thì fallback baseline.

Phương án này giúp tách một phần tác dụng của việc tập trung vào facet có evidence khỏi policy overlap/priority. Nó vẫn đồng thời thay weights và phạm vi missing-facet gate theo các weight active; muốn tách từng hiệu ứng cần ablation tiếp.

Hai phương án đều không học tham số, không tune threshold theo kết quả và không tải model/package mới. Estimator không đổi nên direction metrics không tăng.

## 3. Input và phép so

| Thành phần | Nguồn chỉ đọc |
|---|---|
| Input A/C/corpus và baseline helpers | `data/exp_d/workspace_baseline_20261016_v1/` |
| Canonical đã xuất | `data/exp_d/results/baseline_20261016_v1/` |
| Pilot 30 phiên/28 anchors và 6 cấu hình observation | `data/exp_d/results/baseline_20261016_v1_synthetic/` |

Runner không sinh lại dataset hoặc phản ứng. Nó dùng **predictions baseline đã lưu** làm đầu vào public, thêm các reranker mới, rồi chấm lại toàn bộ baseline và phương pháp mới trên cùng candidates/nhãn/cutoff. Directions/confidence và weights C ban đầu từ public baseline không chứa hidden intent. Hidden focus/labels chỉ dùng ở evaluator, không truyền vào `rerank`.

Đây là replay/reranking trial, không phải huấn luyện mới hoặc chạy lại estimator từ raw logs. Kết quả cũ được kiểm hash và kiểm tra tính tái lập của report trước khi so. Tất cả input được kiểm hash lại sau lượt chạy.

## 4. Lệnh đã chạy và cách chạy lại

Từ gốc project thực nghiệm, CMD hoặc PowerShell:

```powershell
python -B -m unittest discover -s scripts/exp_d -p test_intent_priority.py
python -B scripts/exp_d/run_improve_trial.py
```

Nếu thư mục output đã tồn tại, chương trình từ chối ghi đè. Chọn tên output mới khi chạy lại:

```powershell
python -B scripts/exp_d/run_improve_trial.py --output data/exp_d/results/improve_m0_repeat_v1
```

Có thể chỉ định `--source-root`, `--baseline`, `--synthetic` cho một bộ nguồn tương thích khác. Snapshot phải validate được và các hashes phải khớp; không sửa manifest để vượt kiểm tra. Lượt thử này chưa được nối vào pipeline baseline cũ.

## 5. Kết quả thực tế

### Canonical: cùng 1.500 phiên

| Phương pháp | nDCG@10 | Compliance@5 | So với baseline search |
|---|---:|---:|---|
| `direction_search` | 0,8779 | 0,4989 | Baseline giữ nguyên |
| `intent_active_search` | 0,9160 | 0,5315 | Tăng cả hai chỉ số |
| `intent_priority_search` | 0,9189 | 0,5348 | nDCG +0,0409; compliance +0,0359 (khoảng 3,59 điểm phần trăm) |

Ở `intent_priority_search`, nDCG@10 tăng trong 195 phiên, giữ trong 1.305 phiên, không giảm trong lượt này; compliance@5 tăng trong 129 phiên, giữ trong 1.371 phiên. Có 1.000 phiên fallback vì không suy được focus; không chọn phiên theo metrics để chạy cải tiến.

Hai phương án behavior trên canonical giữ nguyên kết quả vì không có phản ứng D và cả 1.500 phiên fallback. Điều này đúng mục tiêu giữ baseline khi không có evidence.

### Pilot: cùng 30 phiên, điều kiện có synthetic observation

| Cấu hình | Phương pháp | nDCG@10 | Compliance@5 |
|---|---|---:|---:|
| Seed 42, noise 0,2 | `direction_behavior` | 0,8284 | 0,4533 |
| Seed 42, noise 0,2 | `intent_active_behavior` | 0,9873 | 0,5733 |
| Seed 42, noise 0,2 | `intent_priority_behavior` | 1,0000 | 0,6000 |
| Seed 42, noise 0,5 | `direction_behavior` | 0,8284 | 0,4533 |
| Seed 42, noise 0,5 | `intent_active_behavior` | 0,9310 | 0,5267 |
| Seed 42, noise 0,5 | `intent_priority_behavior` | 0,9619 | 0,5467 |

Trong cả 6 cấu hình, priority-behavior có delta nDCG@10 khoảng +0,1335 đến +0,1716; delta compliance@5 khoảng +0,0933 đến +0,1467 so với behavior baseline cùng cấu hình và cùng điều kiện observation. Không có phiên giảm hai metric này trong phép so priority-behavior hiện tại. Bảng đầy đủ có cả search và điều kiện không observation trong [report tổng hợp](../results/improve_m0_20261016_v1/report.md).

**Diễn giải giới hạn:** priority có thể đạt nDCG 1,0 và vượt oracle cũ ở pilot dễ vì nó ưu tiên trực tiếp cấu trúc overlap của benchmark khi intent suy đúng, còn oracle cũ vẫn dùng hàm score mềm. Không có hidden intent đầu vào mới, không có bằng chứng phương pháp hiểu ngữ nghĩa/người dùng thật tốt hơn, và oracle cũ không phải trần toán học. Đây là M0 chẩn đoán, chưa phải phương pháp trong các bài RankNet/LambdaMART đã tìm.

## 6. Kết quả nằm ở đâu và mở file nào?

```text
data/exp_d/results/improve_m0_20261016_v1/
├── report.md                         MỞ TRƯỚC: delta so với baseline cùng điều kiện
├── comparison.json                   Delta và số phiên tăng/giữ/giảm, số fallback
├── manifest.json                     Hash code/input/output, source_unchanged
├── canonical/
│   ├── report.md                     Điểm tuyệt đối baseline + phương pháp mới
│   ├── summary.csv / report.json
│   ├── predictions.jsonl / details.jsonl
│   ├── focus_metrics.json            Directions giữ nguyên
│   ├── comparison.json
│   ├── anchor_groups.json            Nhóm để phân tích, KHÔNG phải train/test split
│   └── manifest.json
└── synthetic/
    ├── seed_42_noise_0.2/             Cùng cấu trúc canonical/, có cả hai điều kiện
    ├── seed_42_noise_0.5/
    └── ...                           Đủ 6 cấu hình từ bundle pilot cũ
```

Mỗi canonical có 9 models × 1.500 phiên = 13.500 predictions; mỗi pilot có 18 models × 30 phiên = 540 predictions. Tổng 16.740 predictions: gồm 9.300 predictions cũ giữ nguyên và 7.440 predictions mới. Các output này là bản kết quả chấm lại, không thay thế các thư mục baseline.

## 7. Kiểm tra sau thay đổi

- 5 unit tests pass.
- Chạy xong canonical và đủ 6 cấu hình pilot.
- Kiểm lại toàn bộ hashes input/output/code của lượt mới: khớp.
- So predictions baseline được chép vào kết quả mới với file gốc: giữ nguyên nội dung.
- Kiểm directions/confidence của mỗi prediction mới bằng baseline tương ứng: khớp.
- Candidate pool giữ nguyên; mọi fallback giữ nguyên ranking baseline.
- Tính lại details và report summary từ toàn bộ 16.740 predictions bằng evaluator snapshot: khớp file đã xuất.
- Theo dõi input trước/sau: không đổi. Không sửa file `run_exp_d copy.py` đang mở trong IDE.

## 8. Backup và restore về cách chạy cũ

**Khôi phục hành vi cũ:** dừng gọi `run_improve_trial.py`, tiếp tục dùng `run_baseline_pipeline.py` hoặc runner baseline như trước. Không có thay đổi tích hợp nào cần đảo ngược; các file cũ và dữ liệu cũ vẫn còn nguyên.

**Backup phần cải tiến:** lưu bốn file mới ở mục 1 và thư mục output mới. Output có thể bị Git ignore nên cần copy riêng nếu muốn giữ kết quả; không mặc định Git đã backup chúng. `manifest.json` trong run lưu hashes để kiểm tra nội dung backup. Nhật ký này chưa nằm trong manifest run vì được viết sau khi chạy.

**Nếu muốn gỡ phần cải tiến:** chỉ gỡ ba file Python mới và tùy chọn thư mục `results/improve_m0_20261016_v1/` sau khi đã backup; giữ nhật ký để tra cứu. Không xóa toàn bộ `data/exp_d`, `scripts/exp_d` hoặc thư mục baseline. Không dùng `git reset --hard` hay `git clean` để restore vì workspace có các file riêng của người dùng.

Hashes của các file cũ quan trọng tại lượt kiểm tra (SHA-256):

| File giữ nguyên | Hash |
|---|---|
| `scripts/exp_d/run_exp_d.py` | `91fb83b4365501f2c858d41b3a450880156fecf29c4adefe27946dbebbf086ef` |
| `scripts/exp_d/run_exp_d copy.py` | `91fb83b4365501f2c858d41b3a450880156fecf29c4adefe27946dbebbf086ef` |
| `scripts/baseline_common.py` | `12dad1b9b7eb42c148b45cdcdd072a00403ae8024699c937360cead4c15309ad` |
| `data/exp_d/run_synthetic_observation_pilot.py` | `8b424a6056a3b180fd7b4cf8eaac76ace9722c705f82ef8de5140745cd9033b2` |

Có thể kiểm một file bằng PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath 'scripts/exp_d/run_exp_d.py'
```

## 9. Việc chưa làm

Chưa cài/train RankNet hoặc LambdaMART, chưa thay encoder, chưa đổi simulator và chưa tạo dev/test split. Lượt chạy không dùng tham số học hoặc chọn ngưỡng theo kết quả, nhưng vẫn sử dụng benchmark/pilot đã quan sát để phát triển ý tưởng, nên không gọi là test cuối độc lập hoặc kết luận có ý nghĩa thống kê.

Bước tiếp: chốt split theo anchor trước khi tune; bổ sung ablation tách ảnh hưởng của gate, weights và lexical priority nếu muốn giải thích cơ chế; sau đó mới quyết định có cần supervised ranker và overlay lớn hơn hay không.

## 10. Bổ sung lượt thử model Hugging Face: SBERT — 16/10/2026

Đã tải và chạy frozen encoder [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), revision cố định `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Đây là checkpoint thuộc hệ Sentence Transformers, không phải train lại toàn bộ phương pháp SBERT gốc. Model dùng embedding 384 chiều; encode concept text của từng facet, giới hạn 256 wordpieces, chuẩn hóa vector. Không fine-tune, không dùng labels để chọn checkpoint hoặc trọng số hybrid.

### File thêm/sửa trong lượt SBERT

| File | Thao tác / vai trò |
|---|---|
| `.gitignore` của project thực nghiệm | Thêm `/data/exp_d/model/` để bỏ qua checkpoint, cache và embedding |
| `scripts/exp_d/model_storage.py` | Mới: đặt đường dẫn model/cache/temp dưới `data/exp_d/model/` trước khi import Hugging Face/PyTorch |
| `scripts/exp_d/prepare_sbert_model.py` | Mới: tải đúng các file inference cần thiết, trọng số safetensors, pin revision và tạo manifest/hash |
| `scripts/exp_d/semantic_ranker.py` | Mới: dense full, dense active và hybrid active 50–50; giữ estimator và lexical context gate |
| `scripts/exp_d/run_sbert_trial.py` | Mới: inference offline từ model local, cache embedding, chấm canonical và 6 cấu hình pilot |
| `scripts/exp_d/test_semantic_ranker.py` | Mới: 4 tests ràng buộc context, missingness, fallback và weights |
| `data/exp_d/docs/changed_improve.md` | Bổ sung mục 10; phần M0 trước đó vẫn giữ nguyên |
| `data/exp_d/model/` | Model/checkpoint/cache mới trên ổ E, đã Git ignore |
| `data/exp_d/results/improve_sbert_20261016_v1/` | Kết quả mới; không ghi đè M0 hoặc baseline |
| `data/exp_d/backups/sbert_20261016_v1/` | Bản `.gitignore` trước thay đổi và nhật ký trước khi bổ sung mục này |

Không sửa code baseline, M0, dữ liệu A/C/D, snapshot, simulator hoặc evaluator. Không cần cài package mới vì môi trường Python hiện có đủ torch/transformers/sentence-transformers. Trọng số tải về là safetensors và không dùng `trust_remote_code`.

### Model, cache và dung lượng ổ E

```text
data/exp_d/model/
├── all-MiniLM-L6-v2/                 Checkpoint local, tokenizer, pooling và model card
├── sbert_download_manifest.json     Repo/revision, hashes và số bytes checkpoint
├── embeddings/<hash>.npz            Cache 11.240 facet texts duy nhất × 384 chiều
├── hf_home/                         Hugging Face hub/xet/assets cache
├── sentence_transformers/           Cache Sentence Transformers
├── torch/ và torch_inductor/        Cache torch
├── cache/                           XDG cache
└── tmp/                             TEMP/TMP/TMPDIR của tiến trình
```

Checkpoint cần thiết: 91.578.415 bytes (~91,6 MB); toàn bộ thư mục model sau lượt này: 108.388.802 bytes (~108,4 MB). Không tải các bản ONNX/OpenVINO/TensorFlow hay trọng số PyTorch `.bin` trùng chức năng. Không di chuyển/xóa model khác của người dùng đã có trên ổ C; cấu hình chuyển đường dẫn áp dụng cho các tiến trình D mới này, không đổi biến môi trường toàn hệ thống.

Các biến `HF_HOME`, `HF_HUB_CACHE`, `HF_XET_CACHE`, `HF_ASSETS_CACHE`, `SENTENCE_TRANSFORMERS_HOME`, `TORCH_HOME`, cache torch/XDG và temp được đặt vào thư mục trên. Khi inference dùng model local và `HF_HUB_OFFLINE=1`; không tải model ngầm sang ổ C. Git ignore đã được xác nhận bằng `git check-ignore -v` trên `model.safetensors`.

### Các phép thử encoder

- `semantic_full_*`: chỉ thay similarity TF-IDF bằng dense cosine (clip [0,1]); giữ weights C, directions, unknown fallback-to-similar trong term, lexical context gate và chính sách missing-facet của baseline. Không cần suy được focus mới chạy.
- `semantic_active_*`: chỉ dùng context và focus dự đoán, cùng weights chuẩn hóa như M0 active, nhưng thay bằng dense similarity. Thiếu focus hoặc hòa confidence thì giữ ranking baseline.
- `hybrid_active_*`: giống active, similarity = 0,5 lexical + 0,5 dense. Trọng số chốt trước chạy, không tune theo điểm.
- `intent_active_*`: chạy lại đối chứng lexical active từ M0 để tách ảnh hưởng của encoder. Directions/confidence của mọi biến thể giữ nguyên.

Tất cả dùng cùng candidate pools, nhãn và cutoff cũ; overlay chỉ phục vụ estimator baseline đã lưu, không được thêm vào corpus encode để thay biểu diễn candidates. Phương pháp mới không nhận true focus, directions, labels hoặc provenance.

### Kết quả canonical: cùng 1.500 phiên, nhánh search

| Phương pháp | nDCG@10 | Compliance@5 |
|---|---:|---:|
| Baseline `direction_search` | 0,8779 | 0,4989 |
| SBERT full | 0,8478 | 0,4663 |
| SBERT active | 0,9076 | 0,5201 |
| Hybrid active 50–50 | 0,9145 | 0,5289 |
| Lexical active, đối chứng M0 | 0,9160 | 0,5315 |
| Lexical priority, lượt M0 trước | 0,9189 | 0,5348 |

### Ví dụ pilot: seed 42, noise 0,2, behavior có synthetic observation

| Phương pháp | nDCG@10 | Compliance@5 |
|---|---:|---:|
| Baseline behavior | 0,8284 | 0,4533 |
| SBERT full | 0,7803 | 0,4200 |
| SBERT active | 0,9478 | 0,5400 |
| Hybrid active 50–50 | 0,9832 | 0,5600 |
| Lexical active, đối chứng M0 | 0,9873 | 0,5733 |
| Lexical priority, lượt M0 trước | 1,0000 | 0,6000 |

**Kết luận lượt này:** chưa có bằng chứng thêm SBERT tốt hơn lexical active/priority đã thử. Full dense giảm điểm; active/hybrid tăng so baseline cũ nhưng không vượt lexical active, nên không quy kết mức tăng đó cho encoder. Nhãn overlap concept của D có thể khác mục tiêu semantic similarity, nhưng chưa có phân tích độc lập để xác nhận đây là nguyên nhân duy nhất. Không chọn checkpoint khác hoặc tune tỷ lệ hybrid bằng test này để gọi là đánh giá cuối.

### Lệnh chạy và nơi xem kết quả

Từ gốc project thực nghiệm:

```powershell
# Lần đầu: tải checkpoint vào ổ E; cần kết nối Hugging Face.
python -B scripts/exp_d/prepare_sbert_model.py --revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41

# Inference dùng model local; tự chọn CUDA nếu có, ngược lại CPU.
python -B scripts/exp_d/run_sbert_trial.py

# Chạy lại bằng output mới; tái sử dụng embedding cache đã kiểm hash.
python -B scripts/exp_d/run_sbert_trial.py --output data/exp_d/results/improve_sbert_repeat_v1

# Kiểm tra ràng buộc scorer, không cần tải model khi chạy tests.
python -B -m unittest discover -s scripts/exp_d -p test_semantic_ranker.py
```

Đã chạy trên CUDA bằng thư viện có sẵn. Versions và revision/embedding hash được ghi trong manifest output; lần này encode 11.240 texts trong khoảng vài giây sau thời gian nạp thư viện và kiểm tra nguồn.

Mở [report SBERT tổng hợp](../results/improve_sbert_20261016_v1/report.md), [report canonical](../results/improve_sbert_20261016_v1/canonical/report.md) hoặc [report pilot seed 42 noise 0,2](../results/improve_sbert_20261016_v1/synthetic/seed_42_noise_0.2/report.md). Bảng tổng hợp so cả baseline gốc và lexical active để tránh nhầm lợi ích của active weights với lợi ích encoder.

Kiểm tra sau chạy: 4 tests semantic pass; canonical + 6 cấu hình pilot hoàn tất; đối chiếu toàn bộ model/code/input/output hashes, vector hữu hạn và chuẩn hóa; predictions baseline/directions/fallback giữ nguyên; tính lại metrics từ **24.180 predictions** khớp reports. Đây vẫn là development diagnostic, chưa tạo train/test split hoặc kiểm định generalization.

### Backup/restore phần SBERT

Backup trước thay đổi ở `data/exp_d/backups/sbert_20261016_v1/`:

- `project.gitignore.before`: bản Git HEAD của project `.gitignore`, khi bắt đầu lượt này chưa có thay đổi khác trong file đó.
- `changed_improve.md.before`: nguyên bytes nhật ký ngay trước khi bổ sung mục 10.

Trở lại M0/baseline: ngừng dùng `run_sbert_trial.py` và chạy runner cũ; không cần sửa lại scorer hay dataset. Các file SBERT mới độc lập, có thể giữ để tham chiếu hoặc gỡ riêng sau backup. Muốn bỏ ignore model thì chỉ bỏ rule `/data/exp_d/model/` vừa thêm; lưu ý việc đó sẽ làm weights xuất hiện trong Git status, không nên commit chúng.

Nếu khôi phục `.gitignore` hoặc nhật ký từ backup, trước tiên đối chiếu các chỉnh sửa người dùng có thể đã thêm sau lượt này; không chép đè mù quáng. Không xóa toàn bộ `exp_d` để restore. Model local đã có có thể giữ lại để tránh tải lại; embeddings có thể được tái sinh từ checkpoint và input tương ứng.

## 11. Bổ sung đối chứng chứng minh luận điểm D — 16/10/2026

Đã đọc lại `data/exp_d/README.md` và `docs/EXPERIMENT_PROTOCOL.md` phiên bản 2.0. **Không sửa README/protocol, corpus/A/C, dữ liệu canonical, baseline/scorer/evaluator/validator, snapshot, model hoặc simulator gốc.** Phép so chính giữ nguyên scorer, weights C, context gate và missingness theo protocol; M0 và synthetic overlay được ghi rõ là phân tích mở rộng riêng.

### File bổ sung

| File | Vai trò |
|---|---|
| `scripts/exp_d/evidence_controls.py` | Chia nhóm anchor và chọn panel bằng hash public IDs, xáo action trong phiên, tạo ba nhánh predicted/similar/flipped cùng focus dự đoán |
| `scripts/exp_d/run_evidence_suite.py` | Chạy đối chứng scorer strict/M0, overlay riêng trên 171 phiên/57 anchors, 6 cấu hình và 10 lần xáo/cấu hình; cluster bootstrap và case studies |
| `scripts/exp_d/test_evidence_controls.py` | 5 tests cho chỉ can thiệp direction, không rò rỉ qua điểm phá hòa, fallback, shuffle và chia/chọn theo ID |
| `scripts/exp_d/summarize_evidence.py` | Tạo báo cáo, gộp 3 seed ở mức phiên trước bootstrap, kiểm tra pool và tái sử dụng oracle evaluator riêng |
| `data/exp_d/docs/evidence_report.md` | Báo cáo tiếng Việt về thiết kế, số liệu, luận điểm được hỗ trợ và giới hạn |
| `data/exp_d/results/evidence_20261016_v1/` | Output mới và manifests; `analysis/report.md` là báo cáo tổng hợp |
| `data/exp_d/backups/evidence_20261016_v1/changed_improve.md.before` | Backup nhật ký trước mục 11 |

Ngoài các file mới, chỉ bổ sung mục 11 vào nhật ký này. Không thay bất kỳ file Python có sẵn nào trong lượt evidence. Dừng gọi runner evidence là trở lại cách chạy cũ; muốn gỡ chỉ gỡ các file bổ sung và output tương ứng sau backup. Không restore toàn repository vì có file riêng của người dùng.

### Các kiểm soát quan trọng

- Ba nhánh strict dùng đúng scorer cũ và weights C; chỉ đổi direction ở focus dự đoán, context giữ similar. Unknown/tie focus giữ nguyên ranking ở cả ba nhánh. Không dùng focus thật cho public scorer.
- M0 dùng cùng scorer priority giữa các nhánh, nhưng lần này secondary score để phá hòa được lấy từ all-similar cố định: tránh đưa direction dự đoán ngược vào nhánh đối chứng qua điểm baseline. Đây là phép phân tích mới có tên model riêng, không thay kết quả M0 đã chạy.
- Panel chọn 3 phiên/anchor bằng hash case ID, không dùng labels/metrics để chọn. Giữ nguyên candidates/query/intents/labels/cutoff; thêm synthetic observation trong bundle riêng và validate bằng checker hiện hành. Không tạo paper/facet giả trong canonical để bù quota.
- 684 exposures/1.368 interactions mỗi cấu hình; 3 seeds × 2 noise. Xáo action 10 lần trong từng phiên, giữ nguyên timestamps/IDs và phân bố action. Đây là negative control có chủ đích, không gọi là dữ liệu utility gốc.
- Anchor groups 34 development / 12 validation / 11 audit, không trùng anchor giữa nhóm. **Đây là chia lại dữ liệu đã xem, không phải test untouched.** Không train/tune hoặc chọn threshold theo nhóm audit.
- CI dùng 2.000 cluster bootstrap theo anchor. Khi gộp seed, lấy trung bình theo phiên trước, không coi các lần sinh phản ứng là người dùng/nội dung độc lập.
- Oracle cho 171 phiên lấy từ predictions evaluator nguồn với đúng sessions/pools; lưu riêng trong analysis, không đưa vào public scorer.

### Kết quả quan trọng và điều chỉnh cách diễn giải trước đó

1. **Có bằng chứng về suy hướng trong simulator:** noise 0,2, behavior focus accuracy 99,42–100%; xáo phản ứng trung bình 34,04–36,26%; không phản ứng accuracy/coverage focus bằng 0. Noise 0,5, accuracy có evidence 87,72–92,40%, sau xáo trung bình 38,01–39,94%.
2. **Chưa có bằng chứng mạnh về cải thiện ranking riêng do direction:** strict search canonical nDCG@10 delta +0,000050, CI 95% [-0,000269; +0,000385]; compliance@5 delta +0,000533, nhỏ về độ lớn thực tế. Overlay nDCG delta hơi âm với CI chứa 0; compliance delta dương nhỏ với CI chạm 0.
3. **M0 predicted và M0 always-similar bằng nhau về nDCG/compliance** trên canonical và panel mở rộng trong phép so mới. Không lấy mức tăng M0 so baseline cũ làm bằng chứng riêng cho direction.
4. **Phát hiện giới hạn pool:** 750/750 phiên different trong canonical không có candidate grade 1; chỉ 88/750 phiên similar có cả grade 1 và 2. Panel tương ứng different 87/87 không có grade 1. Phép thử hiện khó kiểm chứng việc chọn đúng hướng different giữa những bài cùng context.

Kết quả trước đây không bị đổi hoặc xóa; phần này bổ sung bằng chứng để sửa **cách quy kết nguyên nhân tăng điểm**, không phủ nhận các điểm số đã tính đúng.

### Lệnh đã chạy và kiểm tra

```powershell
python -B -m unittest discover -s scripts/exp_d -p test_evidence_controls.py
python -B scripts/exp_d/run_evidence_suite.py
python -B scripts/exp_d/summarize_evidence.py
```

5 tests pass. Đã tính lại details/summary/focus metrics, kiểm tra baseline canonical nguyên vẹn, cùng weights/focus/context giữa nhánh, fallback, hashes input/code/output và accuracy xáo: khớp. Tổng **44.652 predictions ranking** và **10.260 direction predictions từ xáo**. `manifest.json` của suite và `analysis/manifest.json` theo dõi riêng output và phần tổng hợp.

Suite không ghi đè output. `summarize_evidence.py --refresh` chỉ tạo lại phần analysis/báo cáo từ output đã kiểm hash, không chạy hoặc sửa dataset/nhãn/estimator. Chưa có dataset mới thật sự được giữ riêng trước nghiên cứu.

Xem [evidence_report.md](evidence_report.md). Kết luận đúng để báo cáo: **đã kiểm chứng được suy hướng dưới simulator; chưa chứng minh thuyết phục tác dụng riêng của direction lên ranking do hiệu ứng nhỏ và giới hạn candidate pool.** Muốn củng cố vế ranking, cần benchmark đối chứng riêng có candidates cạnh tranh cả hai hướng trong cùng context, giữ ràng buộc nguồn/thời gian/truth và không sửa nhãn bộ cũ.

## 12. Dọn tài liệu và ghi hai luận điểm — 16/10/2026

Thêm [luandiem.md](luandiem.md) ghi ngắn hai câu hỏi D cần kiểm chứng và [README docs](README.md) chỉ thứ tự đọc. Chuyển 11 tài liệu giai đoạn trước sang [old/](old/README.md), gồm báo cáo baseline/observation cũ, checklist, progress, workspace và nhật ký generator; không xóa file. Mỗi tài liệu lưu trữ có ghi chú và được sửa đường dẫn tương đối.

Giữ overview, guideline_pipeline, improve_plan, changed_improve và evidence_report ở thư mục chính; giữ nguyên PDF về E. Sửa liên kết bị ảnh hưởng trong docs, đường dẫn tham khảo ở `data/exp_d/guideline_pipeline.md` và `SYNTHETIC_OBSERVATION_PILOT.md`; cập nhật chỉ dẫn đọc/trạng thái ngắn ở overview. Không sửa README yêu cầu gốc, code, dữ liệu, kết quả hay các snapshot/manifest đã chạy.

Backup nguyên bytes của 18 tài liệu trước dọn ở `data/exp_d/backups/docs_cleanup_20261016_v1/`. `manifest.json` ghi đường dẫn cũ → mới, hashes và file được sửa liên kết. Muốn restore, đối chiếu manifest rồi chuyển từng file về vị trí cũ và khôi phục tài liệu bị sửa từ backup sau khi kiểm tra thay đổi mới; không restore toàn repository.

## 13. Gom code phương pháp về scripts/exp_d — 16/10/2026

Theo yêu cầu sắp xếp code, chuyển **10 file** từ `data/exp_d/` sang `scripts/exp_d/`:

```text
evidence_controls.py
model_storage.py
prepare_sbert_model.py
run_evidence_suite.py
run_improve_trial.py
run_sbert_trial.py
summarize_evidence.py
test_evidence_controls.py
test_intent_priority.py
test_semantic_ranker.py
```

`intent_priority.py`, `semantic_ranker.py` đã ở scripts/exp_d nên giữ nguyên. Không sửa baseline `run_exp_d.py`, bản `run_exp_d copy.py`, hoặc thuật toán các phương pháp. Không để bản code thực thi trùng ở data/exp_d; khi chạy dùng đường dẫn mới `python -B scripts/exp_d/<runner>.py`.

### Đường dẫn và import đã điều chỉnh

- Các runner tính project root từ vị trí scripts/exp_d, rồi trỏ data root về `PROJECT/data/exp_d`; default dataset, snapshot và output không đổi.
- `model_storage.py` luôn trỏ cache/checkpoint/temp về `data/exp_d/model/` trên ổ E, không tạo `scripts/exp_d/model/` hoặc chuyển cache về ổ C.
- Module phương pháp/hỗ trợ import nhau tại thư mục scripts/exp_d; evidence runner thêm đường dẫn data/exp_d khi import overlay generator vẫn giữ ở đó.
- Danh sách code hashes của lượt chạy mới trỏ tới vị trí mới. Báo cáo, manifest, snapshot và backup đã chạy trước đó không bị sửa; đường dẫn code lịch sử trong manifest cũ có thể tra lại qua backup mapping bên dưới, không ghi lại hash để giả đã dùng layout mới.
- Tài liệu hiện hành và template sinh báo cáo cập nhật lệnh mới. Docs/old, backup và báo cáo kết quả lịch sử giữ nguyên; nội dung nghiên cứu và số liệu không đổi.

Giữ tại `data/exp_d/`: generator `build_exp_d.py`, overlay generator `run_synthetic_observation_pilot.py`, workspace/export và pipeline dữ liệu cùng tests của chúng. Chúng không phải các module phương pháp đã tách. Data/model/results/docs cũng giữ vị trí.

### Kiểm tra sau chuyển

```powershell
python -B -m unittest discover -s scripts/exp_d -p 'test_*.py'
python -B scripts/exp_d/run_improve_trial.py --output data/exp_d/evaluation/layout_verify_20261016_v1/m0
python -B scripts/exp_d/run_sbert_trial.py --output data/exp_d/evaluation/layout_verify_20261016_v1/sbert
```

- **14 tests pass**; cả 5 CLI `--help` của runners/downloader khởi động được từ vị trí mới; kiểm tra import overlay generator và đường dẫn data/model khớp vị trí cũ.
- Đã chạy lại đầy đủ canonical và 6 cấu hình pilot cho cả M0 và SBERT, dùng embedding cache có sẵn, không tải model lại.
- **74 so sánh artifact đều giống từng byte trước/sau chuyển**: predictions/details/report.json/summary.csv/focus metrics của từng cấu hình, cùng report và comparison tổng hợp. Manifest mới khác đường dẫn/code hashes là thay đổi dự kiến.
- Hash `run_exp_d.py` và `run_exp_d copy.py` vẫn bằng giá trị ghi ở mục 8. Dataset và kết quả trước đây không đổi.
- Chưa chạy lại toàn bộ suite evidence dài; core đối chứng có tests pass, CLI và các import/path mới đã được kiểm tra. Không tuyên bố có một lượt evidence mới từ layout này khi chưa chạy.

### Backup và restore layout

Backup tại `data/exp_d/backups/method_layout_20261016_v1/`. `manifest.json` ghi mapping vị trí cũ → mới và hashes các bản trước sửa; backup chứa đủ 10 file Python gốc, scripts README và docs hiện hành trước đổi lệnh.

Muốn quay lại layout cũ: sau khi so với thay đổi mới của người dùng, khôi phục 10 file nguyên trạng từ backup về `data/exp_d/`, gỡ các bản chuyển tương ứng trong `scripts/exp_d/`, rồi khôi phục tài liệu từ backup nếu cần. Không gỡ `intent_priority.py`, `semantic_ranker.py`, baseline hoặc model vì chúng không nằm trong danh sách chuyển. Không reset/clean toàn repository.

## 14. Benchmark cặp intent và proposal theo evidence — 16/10/2026

Mục tiêu: tăng bằng chứng cho hai câu hỏi D bằng đối chứng phân biệt được tác dụng của hướng. Không sửa canonical, A/C/corpus, baseline, scorer/evaluator/validator, config chung, simulator overlay cũ, model hoặc kết quả đã chạy. Cải thiện bằng thiết kế **benchmark cơ chế riêng** và một phương pháp public mới, không đổi nhãn cũ để lấy điểm cao.

### File mới

| File | Vai trò |
|---|---|
| `scripts/exp_d/audit_contrast_pool.py` | Khảo sát corpus thật; quota 1 same/9 different/10 outside không có thiết kế khả thi |
| `data/exp_d/build_contrast_sessions.py` | Generator cặp phiên cùng pool/user/cutoff nhưng intent đối lập; chỉ dùng candidates và facets thật |
| `scripts/exp_d/proposal_ranker.py` | Evidence-guided facet reranking, không train và không nhận hidden focus/labels |
| `scripts/exp_d/run_contrast_proposal.py` | Chốt thiết kế trước metrics, tạo/validate bundle riêng, chạy baseline/proposal/strict/negative controls |
| `scripts/exp_d/summarize_contrast_proposal.py` | Bảng kết quả, CI theo anchor sau trung bình seed và leave-one-anchor-out |
| `scripts/exp_d/test_contrast_proposal.py` | Tests paired pools/nhãn/quota/cutoff/contract và can thiệp direction public |
| `data/exp_d/docs/proposal.md` | Proposal và giả thuyết kiểm chứng |
| `data/exp_d/docs/contrast_report.md` | Báo cáo mới, luận điểm và giới hạn |

Output mới: `data/exp_d/evaluation/contrast_feasibility_v1/` (giữ cả kết quả không khả thi), `data/exp_d/results/contrast_proposal_20261016_v1/` (bundle và kết quả). Docs README/luandiem, scripts README và nhật ký này được bổ sung; backup trước sửa tại `data/exp_d/backups/contrast_proposal_20261016_v1/`.

### Thiết kế không chọn theo metrics

Corpus có 15 thiết kế khả thi/8 anchors với cả hai phía focus. Dùng toàn bộ; không có anchor chưa từng xuất hiện trong các lượt trước. Có task/method/dataset/contribution, chưa có problem-focus. Sau audit không thể lấy 9 different, chốt pool **1 same + 1 different + 18 outside** trước mọi đánh giá mới.

Mỗi thiết kế × 2 directions × 3 query modes = 90 phiên/1.800 labels. Các cặp giữ nguyên user, cutoff, anchor, context và 20 candidates duy nhất; intent đặt trước query/reactions/labels. Mỗi phiên có chính xác 1 grade 2, 1 grade 1, 18 grade 0. Shortfall so target canonical 1.500 là 1.410; báo diagnostic/partial, không nhân bản để tự nhận đủ quota.

Nguồn observation vẫn là overlay synthetic riêng theo generator đã có: 4 cặp/phiên, 360 exposures/720 interactions mỗi cấu hình; 3 seeds × noise 0,2/0,5. Chạy checker `check_d` cho bộ không observation và cả 6 overlay; không nhập synthetic vào corpus/A silver hoặc gọi là phản ứng thật.

Proposal active context/focus suy được, chuẩn hóa weights C trên hai facet, gate không overlap context hoặc thiếu dữ liệu active, ưu tiên thỏa direction rồi dùng cosine/weights C làm secondary key **không phụ thuộc direction**. Thiếu evidence/hòa focus thì fallback. Ba nhánh predicted/similar/flipped giữ nguyên focus, weights, gate và secondary; chỉ đổi direction. Baseline/scorer strict giữ công thức gốc và được báo riêng; không quy mức tăng giữa hai scorer thành tác dụng riêng của direction.

### Kết quả và luận điểm

- Noise 0,2: behavior focus accuracy/coverage 100% ở cả 3 seed; sau xáo action trong phiên accuracy trung bình 32,67–34,78%; không observation focus accuracy 0 vì unknown.
- Noise 0,5: behavior accuracy 87,78–91,11%; sau xáo trung bình 35,33–38,67%.
- Seed 42, noise 0,2: proposal behavior predicted nDCG@10 **1,0000**, always-similar **0,8984**, top-1 intent compliance **1,0 so với 0,5**. So trong cùng ranker nên có bằng chứng trực tiếp cho tác dụng direction ở benchmark này.
- Trung bình 3 seed: proposal behavior delta nDCG@10 +0,101646 ở noise 0,2; +0,087340 ở noise 0,5, CI 95% theo anchor khoảng [0,079686; 0,097882] ở noise cao. Leave-one-anchor-out vẫn dương. Scorer strict gốc có delta nhỏ và CI chứa 0; giữ nguyên kết quả này.
- Compliance@5 của proposal có thể giữ 0,2 vì đó là trần pool (1 grade 2/5), không phải bài đúng chưa lên đầu. Primary chốt trước là nDCG@10; compliance@1 chỉ chẩn đoán bổ sung, không đổi primary sau chạy.

Kết luận: hỗ trợ cả hai luận điểm **trong benchmark cơ chế mô phỏng mới với proposal này**. Chưa có bằng chứng generalization sang anchors/corpus mới hoặc người dùng thật; 8 anchors, 4/5 focus, nhãn overlap và observation dựng có kiểm soát là giới hạn. Không tuyên bố novelty thuật toán chỉ từ kết quả này. Giữ kết quả null của bộ cũ và báo thiết kế mới là lý do có khả năng kiểm chứng direction tốt hơn.

### Lệnh chạy và kiểm tra

```powershell
python -B scripts/exp_d/audit_contrast_pool.py
python -B -m unittest discover -s scripts/exp_d -p 'test_*.py'
python -B scripts/exp_d/run_contrast_proposal.py
python -B scripts/exp_d/summarize_contrast_proposal.py
```

Các lệnh không ghi đè output. Đã chạy đủ no-observation và 6 cấu hình: **10.710 predictions ranking**, 5.400 predictions xáo; **16 tests pass**. Tính lại details/summary/focus, kiểm paired pools/users/cutoffs, 1/1/18 grades, cùng weights/focus/gates giữa proposal arms, fallback và input/code/output hashes: khớp. Hash các kết quả baseline/M0/SBERT trước đó giữ nguyên.

Restore: ngừng dùng runner contrast để trở về các runner cũ; chỉ gỡ các file mới/bundle mới sau backup nếu cần. Khôi phục docs từ backup sau khi đối chiếu chỉnh sửa mới; không reset toàn repo hoặc thay bộ canonical. Xem [proposal](proposal.md) và [báo cáo contrast](contrast_report.md).
