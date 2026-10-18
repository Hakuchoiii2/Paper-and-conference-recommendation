# Hiểu bài toán D và báo cáo kết quả với nhóm

Ngày đối chiếu: 2026-10-16. Kết quả được trích từ lượt **baseline_20261016_v1** và pilot **baseline_20261016_v1_synthetic**, không lấy số của các lượt thử cũ để thay cho lượt hiện tại.

**Nếu chỉ đọc một file để hiểu và báo cáo D, đọc chính file này.** Mục 1–5 giải thích bài toán và dữ liệu; mục 6–7 giải thích metrics/kết quả; mục 8–10 nêu code thay đổi, trạng thái và lời trình bày mẫu; mục 12 là bản đồ thư mục. Các file khác chỉ cần mở khi muốn xem bằng chứng hoặc chạy lại.

## 1. D đang cố trả lời câu hỏi gì?

**Trong phiên hiện tại, người dùng muốn bài giống hay khác bài đang đọc ở khía cạnh nào? Khi suy được điều đó, hệ thống có đề xuất đúng nhu cầu hơn không?**

Ví dụ: một người thường đọc bài dùng CNN cho nhận diện bệnh lá cây. Phiên này họ muốn **giữ cùng bài toán nhưng tìm phương pháp khác CNN**. Đề xuất thêm CNN có thể hợp lịch sử dài hạn nhưng sai nhu cầu hiện tại.

| Thành phần ví dụ | Vai trò trong D |
|---|---|
| Bài CNN đang đọc | Anchor / bài mốc |
| Nhận diện bệnh lá cây | Context: phạm vi cần giữ liên quan |
| Phương pháp | Focus: khía cạnh cần xác định hướng |
| Khác CNN | Direction của focus là different |
| Câu tìm kiếm hoặc phản ứng đầu phiên | Evidence để phương pháp suy intent |
| 20 bài chưa có phản ứng trong phần quan sát của phiên | Candidates để ranking và đánh giá |

Đây là ví dụ giải thích, không phải một case thực tế được lấy từ output.

**D có hai câu hỏi cần báo cáo tách biệt:**

1. **Suy intent:** từ thông tin quan sát, suy đúng hướng similar/different ở focus không?
2. **Khuyến nghị:** dùng hướng dự đoán có làm các bài thỏa intent lên đầu ranking không?

Đúng câu 1 không tự bảo đảm đúng câu 2. Kết quả hiện tại minh họa chính điểm này.

## 2. Những khái niệm bắt buộc phải biết

| Khái niệm | Cần hiểu và nói đúng |
|---|---|
| Facet | Một trong problem/task/method/dataset/contribution. Focus có thể là bất kỳ facet nào |
| Context | Facet do benchmark cung cấp sẵn; D hiện không đánh giá tự suy context |
| Focus | Facet quan tâm trong intent thật; phương pháp không được biết sẵn nhãn focus |
| Intent | Ngữ cảnh, hướng mong muốn và mức quan trọng của các facet trong phiên |
| Session/case | Một phiên đánh giá; một user mô phỏng có nhiều phiên |
| Similar/different | Trong nhãn hiện hành, có/không có giao concept khi facet có dữ liệu; không mặc định là giống/khác về ngữ nghĩa thực |
| Ignore | Facet không thuộc intent thật của phiên; không tính như một facet active khi chấm hướng |
| Unknown | Phương pháp chưa đủ evidence; không phải ignore. Ranking fallback similar nhưng khi chấm hướng vẫn giữ unknown |
| Silver | Facet được máy trích ở A, chưa phải annotation được người kiểm duyệt đầy đủ |
| Exposure/interaction | Lượt hiển thị bài và phản ứng sau đó. Hai loại log khác nhau, nối bằng exposure_id |
| Oracle | Đối chứng biết directions và importance thật; được evaluator tạo, không phải phương pháp cùng đầu vào |
| Canonical | Dataset D theo pipeline chính dùng nguồn bài thật; không có nghĩa users/intent/nhãn đều là dữ liệu người thật |
| Synthetic overlay | Nguồn observation tổng hợp riêng, không được nhận là corpus thật hoặc silver A |

**Phân biệt thật và mô phỏng:** bài gốc là thật; facets là silver; danh tính user, intent, query và relevance của D là mô phỏng. Pilot thêm cả mô tả bài quan sát tổng hợp và phản ứng mô phỏng. Không có người dùng thật tham gia các lượt này.

## 3. Phương pháp được thấy gì, phải dự đoán gì?

```text
Bài mốc + context + lịch sử C + query/phản ứng D trước cutoff
                              |
                              v
               Dự đoán directions theo facet
                              |
                              v
     Dùng importance từ C và similarity để xếp 20 candidates
                              |
                              v
        Evaluator đối chiếu hidden intent và relevance
```

Phương pháp thấy ID phiên/user, anchor, context, candidates, cutoff, facet và log quan sát hợp lệ. **Không thấy focus/directions/importance thật, query_mode thật hoặc relevance labels.** Simulator được biết intent để sinh hành vi; evaluator được biết intent để chấm. Không đưa các đáp án này trực tiếp vào scorer công khai.

Lịch sử C cung cấp importance dài hạn; phản ứng D cung cấp evidence về hướng trong phiên. Có lịch sử C không thay cho có phản ứng D.

Trong phiên thật đã mô phỏng, context luôn similar; focus là similar hoặc different; ba facet còn lại ignore. Vì context đã được cho sẵn, cần xem **focus riêng**, không chỉ direction score tổng.

## 4. Chúng ta đã chạy những baseline nào?

| Tên | Importance | Cách xác định hướng | Mục đích phép so |
|---|---|---|---|
| fixed_similar | Đều trên năm facets | Luôn similar | Mốc đơn giản |
| profile_similar | Suy từ C | Luôn similar | So với fixed để xem ảnh hưởng importance cá nhân hóa |
| direction_behavior | Cùng importance C | So phản ứng same/different trong phiên; thiếu thì unknown | So với profile để xem vai trò evidence behavior |
| direction_search | Cùng importance C | Behavior + parser query lexical | So với behavior để xem đóng góp query |
| oracle_intent | Importance thật của phiên | Directions thật | Đối chứng đặc quyền; thay cả weights và directions nên không coi chênh lệch là tác dụng riêng của direction |

Đây là baseline bằng quy tắc và TF-IDF, không có bước train/fine-tune model D. Chạy script không có nghĩa đã huấn luyện một mô hình mới.

## 5. Tại sao có hai nhánh chạy?

### Nhánh A: baseline canonical

Generator hiện tại sinh 1.500 phiên, 20 candidates/phiên, 30.000 labels. Toàn bộ bài mốc/candidates lấy từ corpus thật đã lọc. Không có cặp quan sát hợp lệ sau tách candidates nên exposures/interactions vẫn rỗng. Protocol cho phép giữ thiếu cặp và abstain.

Nhánh này kiểm tra baseline trên thiết kế nguồn thật hiện tại. Nó **không kiểm chứng được suy hướng từ phản ứng**, vì không có phản ứng D.

### Nhánh B: pilot synthetic observation

Chọn 30 phiên từ chính dataset canonical mới, giữ nguyên anchor/candidates/query/labels/cutoff. Lượt này có **28 anchor riêng**, không phải 30 nội dung độc lập.

Tạo thêm 4 cặp observation tổng hợp mỗi phiên: giữ các facet ngoài focus, thay focus bằng concept có sẵn trong corpus để có hai phía same/different. Phản ứng sinh theo utility thỏa intent 0,7/không thỏa 0,05 cộng Gaussian noise, rồi chuyển thành action bằng thresholds nguồn.

Mỗi cấu hình có 120 exposures và 240 interactions. Chạy 3 seeds × 2 noise = 6 cấu hình. Các ID synthetic riêng không có nghĩa các nội dung facet độc lập; đây là cặp được dựng có kiểm soát, không phải bài thật mới được thu thập.

Trong mỗi cấu hình chạy cả bốn baseline + oracle ở hai điều kiện:

| Điều kiện | Khác biệt duy nhất cần kiểm chứng |
|---|---|
| no_observations | Không cung cấp observation và phản ứng |
| synthetic_observations | Có observation tổng hợp và phản ứng mô phỏng |

Cùng 30 phiên, query, labels, candidates, profile C và vector ranking. Vector TF-IDF được giữ từ corpus thật để thêm observation không vô tình thay IDF. Đối chứng không observation được kiểm tra khớp hàm predict baseline nguồn.

**Không lấy điểm nhánh A (1.500 phiên) so trực tiếp nhánh B (30 phiên) rồi tuyên bố synthetic/phương pháp tốt hơn.** Phép so hợp lệ cho tác động observation là giữa hai điều kiện trên cùng pilot.

## 6. Metrics đang nói điều gì?

| Metric | Câu hỏi nó trả lời | Cách đọc |
|---|---|---|
| Focus accuracy | Trong các phiên, hướng tại focus thật được dự đoán đúng bao nhiêu? | Unknown tính là chưa đúng; đọc cùng coverage |
| Focus coverage | Bao nhiêu phiên có kết luận similar/different tại focus? | Coverage cao chưa bảo đảm đúng |
| Direction macro-F1 tổng | Dự đoán hai lớp similar/different trên context + focus active tốt đến đâu? | Có đóng góp context cho sẵn; không thay cho focus-only |
| nDCG@10 | Bài grade cao được xếp gần thứ tự lý tưởng của pool đến đâu? | 0,88 không có nghĩa 88% bài trong top 10 đúng intent |
| Compliance@5 | Tỷ lệ bài trong top 5 có grade 2, tức thỏa context và hướng focus | 0,4984 tương ứng trung bình khoảng 2,492/5 bài thỏa intent |
| Recall/Precision/MRR | Khả năng tìm/đưa bài positive lên đầu | Positive là grade > 0; grade 1 vẫn positive dù sai hướng. Phải đọc cùng compliance |

Nhãn: grade 2 = liên quan và đúng hướng; grade 1 = liên quan nhưng sai hướng; grade 0 = không thỏa điều kiện. Score -1 là chính sách gate của scorer, **không phải relevance -1**, không phải lỗi thực thi.

`direction_confidence` của baseline là điểm heuristic, chưa phải xác suất được hiệu chuẩn. Không diễn giải confidence 0,8 thành “80% chắc chắn đúng”.

## 7. Kết quả của chính lượt baseline_20261016_v1

### 7.1. Canonical: đọc thế nào?

| Model | Direction macro-F1 tổng | Focus accuracy | Focus coverage | nDCG@10 | Compliance@5 |
|---|---:|---:|---:|---:|---:|
| fixed_similar | 0,4286 | 50,00% | 100,00% | 0,8769 | 0,4979 |
| profile_similar | 0,4286 | 50,00% | 100,00% | 0,8779 | 0,4984 |
| direction_behavior | 0,4000 | 0,00% | 0,00% | 0,8779 | 0,4984 |
| direction_search | 0,6875 | 33,33% | 33,33% | 0,8779 | 0,4989 |
| oracle_intent | 1,0000 | 100,00% | 100,00% | 0,9915 | 0,5861 |

Giải thích:

- Fixed/profile đúng focus 50% vì luôn đoán similar và bộ này có hai hướng cân bằng, không phải đã hiểu phiên.
- Behavior focus 0% vì toàn unknown, không phải đã thử phản ứng rồi đoán sai tất cả. Coverage tổng 50% của nó đến từ context được cho sẵn.
- Search đúng focus 33,33% trên toàn bộ vì có 500/1.500 phiên clear và parser xử lý đúng các mẫu này. Hai nhóm ambiguous/none không có evidence hướng focus trong bộ canonical.
- Search cải thiện khả năng suy hướng trên query rõ; ranking/compliance chỉ khác rất ít. Chưa có kiểm định để nói chênh lệch nhỏ này có ý nghĩa thống kê hoặc tổng quát hóa.
- Oracle biết cả directions và weights thật nên là mốc đặc quyền, không chứng minh chỉ cần sửa parser sẽ đạt điểm oracle.

**Pool giới hạn compliance:** trung bình 4,5 bài grade 2/20; trần compliance@5 theo pool là **0,60**, @10 là **0,45**. Oracle đạt @5 khoảng 0,5861, gần trần pool đó. Không kỳ vọng top 5 luôn có 5 bài đúng khi nhiều phiên không có đủ 5 bài grade 2.

### 7.2. Pilot: đã chứng minh được gì?

| Seed | Noise | Behavior focus accuracy: không observation | Có synthetic | Coverage có synthetic |
|---|---:|---:|---:|---:|
| 42 | 0,2 | 0% | 100% | 100% |
| 43 | 0,2 | 0% | 100% | 100% |
| 44 | 0,2 | 0% | 100% | 100% |
| 42 | 0,5 | 0% | 83,33% | 86,67% |
| 43 | 0,5 | 0% | 100% | 100% |
| 44 | 0,5 | 0% | 90,00% | 93,33% |

Đây là kết quả kỳ vọng của cặp dễ, có kiểm soát và phản ứng gắn intent. **Nó xác nhận estimator hoạt động với simulator này**, không chứng minh simulator giống hành vi thật.

Ranking behavior trên cùng pilot ở cả sáu cấu hình:

| Metric | Không observation | Có synthetic | Kết luận |
|---|---:|---:|---|
| nDCG@10 | 0,8305 | 0,8284 | Giảm nhẹ; chưa có cải thiện |
| Compliance@5 | 0,4533 | 0,4533 | Không tăng |

**Kết luận đúng:** bổ sung evidence mô phỏng làm focus có thể suy được; ranking hiện tại chưa chuyển thành kết quả tốt hơn. Cần phân tích scorer/weights/biểu diễn và độ nhạy ranking, chưa kết luận nguyên nhân cụ thể nếu chưa có ablation.

## 8. Đã đổi gì so với code cũ?

| Nhóm | Thay đổi | Có phải phương pháp mới không? |
|---|---|---|
| Generator gốc | Cân bằng focus, ưu tiên tổ hợp nhiều positives, tăng mẫu query và thống kê độ phủ | Thay thiết kế lấy mẫu dữ liệu; chưa phải estimator/ranker mới |
| Synthetic pilot | Thêm runner riêng, nguồn observation tổng hợp, simulator noise và đối chứng cùng điều kiện | Thiết kế thực nghiệm bổ sung; vẫn dùng baseline cũ |
| Workspace/pipeline/export | Tạo snapshot, xử lý LF ở bản sao, sinh lại D, chạy và copy kết quả có kiểm hash | Hạ tầng tái lập, không phải đóng góp thuật toán |
| Tests | Kiểm tra hợp đồng dữ liệu, không ghi đè, không rò rỉ đường dẫn/nhãn/thời gian | Kiểm tra kỹ thuật |

File gốc đã sửa: `data/exp_d/build_exp_d.py`. Sáu script Python bổ sung: `prepare_workspace.py`, `run_baseline_pipeline.py`, `export_results.py`, `run_synthetic_observation_pilot.py`, `test_export_results.py`, `test_synthetic_observation_pilot.py`.

**Không sửa** scorer/evaluator/validator dùng chung, corpus/A/C, config chung hoặc README gốc (README đã hoàn tác). `README_changed.md` là file mới đang hiện Git; không tự quy nó thành thay đổi thuật toán. Bảng chi tiết đối chiếu code cũ/mới ở [changed.md](changed.md).

## 9. Trạng thái cần báo cáo với nhóm

| Đã hoàn thành | Chưa thể tuyên bố |
|---|---|
| Chạy baseline canonical đầy đủ và kiểm tra output | Đã có thuật toán mới tốt hơn baseline |
| Pilot synthetic chạy 6 cấu hình, behavior có evidence | Đã bổ sung phản ứng thật hoặc giải quyết nguồn cặp bài thật |
| Phân bố focus cân bằng, mean positives tăng | Dataset mới tốt hơn toàn diện: anchor giảm từ 409 ở bộ cũ xuống 57 |
| Có pipeline tái lập và xuất kết quả | Toàn bộ mục tiêu nghiên cứu D đã hoàn thành |

Lượt hiện tại có 7.500 predictions canonical và 1.800 predictions pilot. Hash export, input/code và 9.300 rankings đã được kiểm tra; điều này xác nhận tính toàn vẹn kỹ thuật, không thay cho review chất lượng ngữ nghĩa hoặc kiểm định thống kê.

Nội dung cần trao đổi với nhóm tiếp:

1. Câu hỏi nghiên cứu chính sẽ là ranking theo intent, suy hướng từ query hay behavior dưới simulator? Chọn rõ để thiết kế bằng chứng tương ứng.
2. Có chấp nhận nguồn observation tổng hợp và kết luận trong phạm vi simulator không? Không gọi nó là dữ liệu người dùng thật.
3. Có chấp nhận sampling tập trung 57 anchors để tăng positives không, hay cần cân bằng lại độ phủ?
4. Nếu đề xuất phương pháp mới, sẽ thay thành phần nào, giữ thành phần nào cố định và ablation nào kiểm chứng tác dụng?
5. Chốt phần phát triển/đánh giá cuối theo anchor để tránh rò rỉ; không tune trên pilot rồi gọi chính pilot là test cuối.

## 10. Đoạn trình bày ngắn có thể dùng trong buổi báo cáo

> Em phụ trách D: suy ý định muốn giống/khác theo facet trong phiên rồi dùng hướng đó để ranking. Em đã chạy đủ baseline và hoàn thiện pipeline tái lập. Dữ liệu nguồn thật chưa có cặp observation hợp lệ nên nhánh behavior không suy được focus. Em làm pilot riêng trên 30 phiên thật với observation tổng hợp và phản ứng theo intent có nhiễu, giữ nguyên candidates/nhãn để so có và không evidence. Estimator suy được focus trong simulator, nhưng ranking/compliance chưa tăng. Vì vậy hiện em hoàn thành mốc dữ liệu/pilot/baseline, chưa có phương pháp mới thắng đối chứng. Bước tiếp là chốt hướng cải tiến và phép so, đồng thời thống nhất giới hạn synthetic và độ phủ anchor với nhóm.

## 11. Mở file nào để đối chiếu khi nhóm hỏi?

| Cần xem | File |
|---|---|
| Kết quả canonical | `data/exp_d/results/baseline_20261016_v1/report.md` |
| Kết quả focus pilot theo seed/noise | `data/exp_d/results/baseline_20261016_v1_synthetic/focus_sensitivity.json` |
| Ranking/detail pilot | `.../baseline_20261016_v1_synthetic/seed_42_noise_0.2/results/report.md` và `details.jsonl` |
| Phiên/nhãn canonical đã chạy | `data/exp_d/workspace_baseline_20261016_v1/data/exp_d/generated/` và `ground_truth/` |
| Provenance và xác nhận copy | `manifest.json`, `export_receipt.json`, `pipeline_receipt.json` trong result tương ứng |
| Code đổi gì | [changed.md](changed.md) |
| Chạy lại bằng CMD | [guideline_pipeline.md](guideline_pipeline.md) |
| Thiết kế synthetic và giới hạn | [SYNTHETIC_OBSERVATION_PILOT.md](../SYNTHETIC_OBSERVATION_PILOT.md) |

Không so điểm ở report cũ ngày 15/10 với report của dataset mới để kết luận cải tiến thuật toán. Các con số trên chỉ mô tả run được ghi ở đầu tài liệu.

## 12. Cây thư mục: mỗi file nằm ở khâu nào của D?

Cây dưới đây tính từ `paper-and-conference-recommendation-experiments/`, chỉ mở rộng phần cần hiểu của D. Các nhánh seed/noise cùng cấu trúc nên chỉ minh họa một nhánh.

```text
data/exp_d/
│
├── docs/                                     GIẢI THÍCH, không phải data cho model
│   ├── bao_cao_nhom_D.md                      ĐỌC FILE NÀY để hiểu và báo cáo D
│   ├── changed.md                            Code cũ → code mới, phạm vi và kết quả
│   ├── guideline_pipeline.md                 Quy trình CMD chi tiết
│   ├── bao_cao_exposure_interaction_D.md      Phân tích thiếu cặp và đề xuất synthetic
│   └── ...                                   Các ghi chú khác; không bắt buộc đọc hết
│
├── build_exp_d.py                            TẠO DATA D canonical từ facet A/users C
├── run_synthetic_observation_pilot.py         TẠO/RUN overlay observation tổng hợp riêng
├── run_baseline_pipeline.py                  ĐIỀU PHỐI toàn bộ luồng chạy và tự export
├── prepare_workspace.py                      COPY code/input vào snapshot mới, xử lý LF
├── export_results.py                         COPY output đã kiểm hash về results/
├── test_export_results.py                    Tests tính toàn vẹn và an toàn khi export
├── test_synthetic_observation_pilot.py        Tests hợp đồng observation tổng hợp
│
├── README.md                                README gốc, giữ nguyên
├── README_changed.md                        Bản README riêng; không phải kết quả/model
├── guideline_pipeline.md                    Bản hướng dẫn ở gốc D hiện có
├── SYNTHETIC_OBSERVATION_PILOT.md             Thiết kế và giới hạn nguồn synthetic
│
├── generated/                               DATA NGUỒN đã có trước lượt chạy mới
│   ├── sessions.jsonl                       Thông tin phiên, anchor/context/candidates
│   ├── search_events.jsonl                  Query và reformulation
│   ├── exposures.jsonl                      Cặp bài được hiển thị; bộ nguồn cũ rỗng
│   ├── interactions_train.jsonl             Phản ứng D; bộ nguồn cũ rỗng
│   ├── generation_report.json               Quota, phân bố, thống kê sinh dữ liệu
│   └── manifest.json                        Phiên bản/hash/provenance nguồn
├── ground_truth/                            ĐÁP ÁN nguồn, chỉ để sinh mô phỏng/chấm
│   ├── session_intents.jsonl                Focus/directions/weights/query_mode thật
│   └── intent_labels.jsonl                  Relevance từng session–candidate
│
├── workspace_baseline_20261016_v1/           SNAPSHOT thực sự chạy lượt hiện tại
│   ├── configs/exp_d.json                   Config đã dùng
│   ├── scripts/exp_d/run_exp_d.py            Runner baseline có sẵn trong snapshot
│   ├── scripts/baseline_common.py           Estimator/ranker baseline dùng chung
│   ├── scripts/experiment_runner.py         Evaluator/oracle và xuất metrics
│   ├── data/exp_d/
│   │   ├── build_exp_d.py                   Bản generator tại thời điểm copy
│   │   ├── generated/                      DATA CANONICAL MỚI đã sinh và chạy
│   │   └── ground_truth/                   Đáp án tương ứng của data mới
│   └── results/exp_d/baseline_20261016_v1/   Output canonical gốc trước export
│
├── evaluation/                              NƠI CHẠY pilot trước export
│   └── baseline_20261016_v1_synthetic/       Bundle synthetic gốc, cùng nội dung đã xuất
│
├── results/                                 KẾT QUẢ ĐÃ XUẤT, dùng xem/bàn giao
│   ├── baseline_20261016_v1/                 NHÁNH CANONICAL, 1.500 phiên
│   │   ├── report.md                       MỞ TRƯỚC: bảng metrics dễ đọc
│   │   ├── summary.csv                     Bảng metrics cho Excel
│   │   ├── report.json                     Metrics tổng hợp dạng JSON
│   │   ├── predictions.jsonl               Model đã dự đoán/ranking thế nào?
│   │   ├── details.jsonl                   Từng case/model được chấm thế nào?
│   │   ├── manifest.json                   Input/code hashes của lượt scoring
│   │   ├── export_receipt.json             Nguồn copy và hash các file xuất
│   │   └── pipeline_receipt.json           Liên kết workspace và hai nhánh result
│   │
│   └── baseline_20261016_v1_synthetic/       NHÁNH PILOT, 30 phiên/28 anchors
│       ├── manifest.json                   Chọn case nào, seeds/noise, nguồn/hashes
│       ├── export_receipt.json             Xác nhận copy bundle
│       ├── focus_sensitivity.json          MỞ TRƯỚC: focus qua 6 cấu hình
│       ├── generated/                      30 sessions và queries thật giữ nguyên
│       ├── ground_truth/                   Intent/labels thật của 30 phiên chọn
│       └── seed_42_noise_0.2/               Một trong 3 seed × 2 noise
│           ├── generated/
│           │   ├── observation_papers.jsonl  Mô tả synthetic, không phải bài thật
│           │   ├── observation_facets.jsonl  Facet dựng có kiểm soát
│           │   ├── exposures.jsonl           120 cặp quan sát
│           │   └── interactions_train.jsonl  240 phản ứng mô phỏng
│           ├── ground_truth/
│           │   └── observation_provenance.jsonl  Nguồn dựng/nhãn vai trò ẩn
│           └── results/
│               ├── report.md               Ranking/compliance trên cùng pilot
│               ├── focus_metrics.json      Focus accuracy/coverage/F1 riêng
│               ├── predictions.jsonl       300 dòng: 30 phiên × 5 model × 2 điều kiện
│               ├── details.jsonl
│               ├── report.json
│               ├── summary.csv
│               └── manifest.json
│
├── audit/                                   Bằng chứng kiểm tra, không phải model
├── samples/                                 Hướng dẫn pilot ban đầu
└── __pycache__/                             Cache Python, không cần đọc/bàn giao
```

### Những vị trí dễ nhầm nhất

| Hai vị trí / loại file | Phân biệt thế nào? |
|---|---|
| `data/exp_d/generated/` và `workspace_.../data/exp_d/generated/` | Vị trí đầu là nguồn có sẵn; vị trí sau là data mới thực sự dùng trong run hiện tại. Không lấy số của nguồn cũ để mô tả run mới |
| `build_exp_d.py` gốc và bản cùng tên trong workspace | Workspace giữ code tại lúc tạo snapshot; sửa file gốc sau đó không tự đổi lượt đã chạy |
| `evaluation/..._synthetic/` và `results/..._synthetic/` | Evaluation là output chạy gốc; results là bản xuất có kiểm hash để xem/bàn giao. Không phải hai pilot độc lập |
| `predictions.jsonl` và `details.jsonl` | Predictions là đầu ra phương pháp; details là đầu ra đánh giá có nhãn/metrics. Không đưa details vào scorer |
| `generated/` và `ground_truth/` | Generated chứa quan sát; ground_truth chứa đáp án/provenance ẩn. Không dùng đáp án làm đầu vào dự đoán |
| `manifest.json` và `export_receipt.json` | Manifest mô tả lượt sinh/chạy; receipt mô tả lần copy. Receipt không thay đổi nơi scoring đã diễn ra |

### Thứ tự đọc tối thiểu khi báo cáo

1. Đọc chính tài liệu này, đặc biệt mục 1, 5, 7, 8 và 10 để nắm câu chuyện.
2. Khi cần chỉ bằng chứng, mở `results/baseline_20261016_v1/report.md` cho canonical.
3. Mở `results/baseline_20261016_v1_synthetic/focus_sensitivity.json`, rồi một `seed_*/results/report.md` cho pilot.
4. Chỉ mở code hoặc manifest khi nhóm hỏi về cách triển khai/tái lập. Không cần đọc hết file JSONL để hiểu bài toán.
