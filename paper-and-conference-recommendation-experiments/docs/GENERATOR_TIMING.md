# Đo thời gian generator A–E — 2026-10-05

Đã chạy thử trên máy hiện tại: RTX 4060 Laptop 8 GB, CPU Intel có 20 luồng,
Python 3.11.16. Ước lượng dưới đây dành cho **sinh dataset**; chạy mô hình
thực nghiệm và người review 400 bài gold tính riêng.

## Kết quả và thời gian dự trù

| Exp | Quy mô full hiện tại | Đo thực tế | Thời gian dự trù full |
|---|---|---|---|
| A | 4.210 bài, Qwen 4-bit, tối đa 3 attempts/bài | 3 bài mới: 204,2 giây gồm nạp model; log 819 bài: 64,04 giây/bài gồm retry | Khoảng 75–90 giờ trên một GPU tương đương |
| B | 300 queries × 100 candidates = 30.000 cặp | Trung vị 4,04 giây trên bộ thử 4.210 bài | Dự trù 10–30 giây khi có full silver |
| C | 1.500 cases × 20 candidates = 30.000 cặp | Trung vị 9,94 giây trên bộ thử 4.210 bài | Dự trù 20–60 giây khi có full silver |
| D | 300 users × 50 events = 15.000 events | Trung vị 4,31 giây trên bộ thử 4.210 bài | Dự trù 10–30 giây khi có full silver |
| E | 300 users × 4 periods × 15 = 18.000 events | Trung vị 9,79 giây trên bộ thử 4.210 bài | Dự trù 20–60 giây sau D |

B–E cộng lại đo được khoảng 28 giây trên dữ liệu thử. Với silver thật,
dự trù khoảng 1–3 phút vì metadata/evidence lớn hơn, kiểm tra đầu vào tốn
thêm thời gian và mức trùng concept khác dữ liệu thử. Đây là khoảng dự trù,
chưa phải số đo full trên silver thật.

## A: chạy Qwen thật và đối chiếu log

Chạy generator thật với cấu hình hiện hành, chỉ đổi khoảng bài thành [843,845]
và output thành thư mục riêng. Model dùng cache local, revision
`cdbee75f17c01a7cc42f958dc650907174af0554`, tối đa 2.048 output tokens/attempt,
seed 42. Generator và config chính được giữ nguyên.

| ID thử | Thời gian inference, gồm retry | Attempts | Kết quả lưu |
|---|---:|---:|---|
| P000843 | 77,125 giây | 3 | Best available, có lỗi chất lượng được audit |
| P000844 | 54,626 giây | 3 | Best available, có lỗi chất lượng được audit |
| P000845 | 30,672 giây | 1 | Qua kiểm tra chất lượng tự động |

Inference cộng lại 162,423 giây; toàn lượt chạy 204,186 giây, phần chênh
gồm nạp model, chuẩn bị và lưu dữ liệu. Kiểm tra output riêng mất 0,098 giây
và qua gate partial. Kết quả thử ở
`data/exp_a/generated/timing_probe_20261005/timing_result.json`;
ba bài này là mẫu đo riêng, không phải toàn bộ part_2.
Hash các JSON/JSONL của part_1 được đối chiếu trước/sau và giữ nguyên.

Ước lượng full ưu tiên **819 records policy 2.3 có attempt_scores** trong
log part_1, thay vì suy rộng từ ba bài mới:

- Trung bình 64,044 giây/bài; trung vị 46,407 giây.
- P90 138,890 giây; P95 171,314 giây; bài chậm nhất 338,391 giây.
- 277 bài dùng một attempt, 245 bài dùng hai, 297 bài dùng ba;
  trung bình 2,024 attempts/bài. generation_seconds đã cộng các attempts.
- Abstract trung bình trong mẫu 158,36 từ, toàn corpus 158,06 từ.
  Mẫu vẫn là part_1, chưa bảo đảm đại diện mọi nguồn/chủ đề.
- 4.210 × 64,044 / 3.600 = **74,90 giờ inference**.
  Dự trù 75–90 giờ cho tải model, lưu dữ liệu và biến động tốc độ máy.
- Một phần 842 bài: khoảng **15–18 giờ**.
- Bốn phần còn lại, 3.368 bài: khoảng **60–72 giờ** trên một GPU.
- Năm GPU tương đương chạy năm phần độc lập: khoảng **15–18 giờ** theo
  tốc độ mẫu; thời gian kết thúc phụ thuộc phần/máy chậm nhất.
- Nếu corpus tăng lên 6.000 bài: mốc tuyến tính 106,74 giờ, dự trù 107–128 giờ.

Các mốc này giả định giữ cấu hình/model, GPU tương đương và mức retry gần mẫu.
Thời gian thực tế thay đổi theo độ dài output, số retry và công suất GPU.

## B–E: chạy đủ số lượng mục tiêu

Dùng lại fixture và PipelineChecks của tests, mở rộng pattern facet thử
đến 4.210 paper IDs riêng biệt. Dữ liệu là synthetic test-only trong thư mục
tạm, không ghi vào corpus hay dataset thật. Mỗi generator chạy ba lần qua
`generate()`: load/validate A, sinh records, ghi files/hashes và validate đầu ra.
Sau mỗi lần chạy còn gọi validator độc lập; mọi bộ đều status complete và đủ quota.
E dùng handoff users của D.

| Exp | Ba lần generate + write + validate, giây | Kiểm tra độc lập thêm, giây |
|---|---|---|
| B | 2,546; 4,040; 4,084 | 1,554; 1,591; 1,571 |
| C | 10,011; 9,940; 9,780 | 1,550; 1,500; 1,481 |
| D | 4,336; 4,308; 4,256 | 1,074; 1,109; 1,059 |
| E | 9,832; 9,568; 9,789 | 1,186; 1,175; 1,189 |

Đo B–E trong lúc mẫu A đang chạy trên GPU. Các mốc này đo full kích thước
corpus và số records yêu cầu, nhưng fixture có evidence ngắn và các concept
trùng có chủ đích để kiểm tra quota. Không suy ra độ đúng ngữ nghĩa từ tốc độ.

## Chẩn đoán trên silver thật hiện có

Snapshot part_1 hiện có 842 annotations; **192 bài bị fallback/lỗi**, còn
650 bài hợp lệ cho sampling B–E. Con số này mới hơn snapshot một fallback
trong báo cáo kiểm tra trước đó.

Đã gọi trực tiếp hàm build từng exp trên 650 bài hợp lệ để chẩn đoán,
giữ nguyên config/quota. Output chỉ ở bộ nhớ:

| Exp | Thời gian riêng phần build | Số lượng thực tế |
|---|---:|---|
| B | 0,091 giây | 52/300 queries, 5.200 cặp; thiếu 248 queries |
| C | 0,698 giây | 16/1.500 cases, 320 cặp; thiếu 1.484 cases |
| D | 0,331 giây | Đủ 300 users, 15.000 events |
| E | 0,766 giây | Đủ 300 users, 18.000 events |

B/C thiếu cặp positive/negative theo rule concept_overlap_v1. B chưa có
query hợp lệ cho problem; nhiều template C thiếu positive. Full silver có
thể bổ sung cặp phù hợp, nhưng **chưa bảo đảm đủ quota B/C trên dữ liệu thật**.
Cần kiểm tra lại coverage khi đủ A trước khi chốt dataset thực nghiệm.
CLI chính vẫn yêu cầu manifest A complete; các phép chẩn đoán này không
phát hành dataset B–E từ part_1.

Generator A SHA256 khi đo:
`48ff88ceca3c0e259675a34e684a6ad871bfe0f3e24afc599f7d1fff81d48d72`.
