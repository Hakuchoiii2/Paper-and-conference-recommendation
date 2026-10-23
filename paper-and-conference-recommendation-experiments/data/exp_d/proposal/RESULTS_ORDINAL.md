# Bảng cập nhật: tám phương pháp, một policy ranking

Đã chạy `ordinal_common_20261021_01`: **5.472 predictions**, 8 phương pháp × 114 phiên × 6 điều kiện phản ứng. Đây là lựa chọn phương pháp trên **pilot mock đã được xem trước**, không phải test độc lập. Không sinh lại dữ liệu, sửa baseline gốc hoặc chọn ngưỡng để method mới thắng.

## Bảng chính

| Phương pháp | Dùng tín hiệu gì? | Accuracy hướng | Coverage | nDCG@10 | Bài đúng nhu cầu ở hạng 1 |
|---|---|---:|---:|---:|---:|
| fixed_similar | Không tín hiệu phiên; luôn similar, trọng số đều | 50,00% | 100,00% | 0,8029 | 50,00% |
| profile_similar | Không tín hiệu phiên; luôn similar, trọng số C | 50,00% | 100,00% | 0,8019 | 50,00% |
| QUERY-ONLY | Chỉ query | 33,33% | 33,33% | 0,8623 | 66,44% |
| DELTA / direction_behavior | Chỉ phản ứng; baseline gốc | 95,83% | 96,80% | 0,9597 | 93,63% |
| **DELTA + query / direction_search** | **Query + phản ứng; baseline gốc** | **96,91%** | **97,84%** | **0,9632** | **94,56%** |
| VOTE | Query + phiếu dấu phản ứng | 91,74% | 92,05% | 0,9523 | 91,59% |
| BAYES-H | Query + posterior từ dấu phản ứng | 91,51% | 91,82% | 0,9518 | 91,36% |
| Ordinal-Intent — mới | Query + posterior từ mức chênh phản ứng, kể cả hòa | 81,13% | 81,13% | 0,9374 | 87,00% |

Accuracy hướng tính trên toàn bộ phiên, unknown tính sai. Coverage là tỷ lệ có trả lời hướng tại focus thật, do evaluator chấm. Không coi fallback ranking là một dự đoán hướng. QUERY-ONLY chỉ suy được hướng khi query rõ; 33,33% không có nghĩa đoán ngẫu nhiên sai nhiều. Joint focus–direction, joint coverage và phân nhóm có trong output; hai baseline always-similar không xác định một focus duy nhất nên joint accuracy = 0.

Các điểm được trung bình lần lặp trong thiết kế, thiết kế trong nhóm công trình của anchor, rồi 12 nhóm. Không coi 684 biến thể session/condition là 684 nội dung độc lập.

## Ranking đã cố định thế nào?

Mọi dòng dùng **cùng `intent_scores` gốc và adapter R_active**:

1. Chỉ có một facet ngoài context được dự đoán similar/different: giữ context và facet đó; đặt các facet còn lại ignore.
2. Không có/mơ hồ focus: fallback always-similar với profile đã khóa; không dùng nhãn ẩn để chọn focus.
3. Vector, candidates và C weights giữ nguyên. Riêng fixed_similar giữ trọng số đều đúng baseline gốc; các dòng còn lại dùng cùng trọng số C.

Raw directions của bảy method cũ không đổi. Chỉ ranking nhận thêm `ranking_directions` qua policy chung. Accuracy/coverage cũ tái hiện chính xác. Không được lấy nDCG cũ 0,8418 của DELTA+query so với method khác ở policy mới rồi gọi là cải thiện estimator.

Policy chung làm bảng so estimator công bằng hơn so với chỉ cho một method dùng ignore. Khi so DELTA với no-signal, khác biệt vẫn bao gồm khả năng suy scope. Để kiểm riêng dấu hướng, probe trước có đối chứng **cùng focus/mask nhưng luôn similar**: nDCG 0,8944, thấp hơn 0,9632 của hướng DELTA+query; chênh +0,0688, khoảng paired theo anchor [0,0388; 0,0889]. Đây vẫn là phân tích thăm dò.

## Method mới thực sự làm gì?

Ordinal-Intent dùng cùng các cặp phản ứng hợp lệ và parser gốc. Xét tối đa 8 giả thuyết `(focus, direction)`. Với chênh lệch thứ hạng phản ứng d từ −4 đến 4:

`P(d | sign, strength) ∝ (5 − |d|) × exp(strength × sign × d)`.

Năm action được giả định có thứ hạng cách đều. Baseline trung tính cho chênh lệch là phân phối tam giác của hai thứ hạng độc lập đều. Nếu cặp không thay facet của giả thuyết đang xét thì dùng strength=0. Hòa có xác suất dương, không bị bỏ đi.

Marginalize strength trên grid cố định [0,25; 0,75; 1,5], prior đều; đây là nuisance về độ mạnh bằng chứng, **không phải ước lượng trực tiếp noise thật của generator**. Query có likelihood mềm 0,8. Quyết định cần posterior ≥0,25 và gap ≥0,10; không có query rõ thì cần ít nhất 2 contrast của focus dự đoán. Các ngưỡng không sweep theo kết quả. Không train hoặc lấy utility/threshold/noise ẩn của simulator làm likelihood đúng đáp án.

Ordinal-Intent trả lời đúng trên phần nó chấp nhận trong lượt này nhưng abstain nhiều; coverage 81,13%, so với DELTA+query 97,84%. Vì vậy không chọn method mới chỉ dựa vào accuracy có điều kiện trên số phiên đã trả lời. Đặc biệt ở noise 0,5, accuracy toàn bộ còn 68,83% so với 93,83% của DELTA+query. Posterior chưa calibrated; giả định likelihood chưa đủ phù hợp với bộ mock này.

Đây là adaptation riêng của dự án, không gọi là reproduction hoặc tính mới đã được chứng minh. Tham khảo hướng ordinal: [Reward Modeling with Ordinal Feedback, ICML 2025](https://proceedings.mlr.press/v267/liu25az.html); không gán công thức trên cho bài đó.

## Kết luận được tới đâu?

| Luận điểm | Bằng chứng trên pilot | Kết luận |
|---|---|---|
| Phản ứng giúp suy hướng | DELTA 95,83% so với profile_similar 50,00% | Được hỗ trợ trong mô phỏng hiện tại |
| Query bổ sung cho phản ứng | DELTA+query 96,91% so với DELTA 95,83%; tăng 1,08 điểm %, khoảng paired [0,39; 1,85] | Có ích nhưng mức tăng nhỏ; khi query rõ vốn rất dễ |
| Hướng suy được giúp ranking | Cùng policy: nDCG 0,8019 → 0,9632; đối chứng cùng mask/luôn similar cũng thấp hơn | Được hỗ trợ trong phép thử kiểm soát; không đồng nhất scope với dấu hướng |
| Method mới tốt hơn | Ordinal thấp hơn DELTA+query: accuracy −15,78 điểm %, nDCG −0,0257, khoảng paired nDCG [−0,0379; −0,0163] | **Không được hỗ trợ; không chọn Ordinal làm method tốt nhất** |

**Chốt cho pilot: chọn DELTA + query với R_active chung.** Đây là baseline gốc đang thắng các đối chứng bổ sung, không tự trở thành thuật toán mới chỉ vì đứng đầu bảng. Có thể trình bày đóng góp là thiết kế/đánh giá cơ chế trong mô phỏng; claim phương pháp mới hoặc khái quát sang người dùng thật cần bằng chứng thêm. Không tiếp tục thử tùy ý chỉ để tìm một method thắng trên cùng dữ liệu đã xem.

## Data đang đo và vị trí

| Thành phần | Nguồn / vị trí | Tính chất |
|---|---|---|
| Nguồn đầu vào đã khóa | `inputs/base_v1/` | Bài thật từ corpus, facets silver A, users/history C mock |
| Bộ benchmark thực sự | `datasets/observation_v1/` | 19 thiết kế, 12 anchors, 114 phiên; 20 candidates/phiên |
| Candidates | 15 thiết kế chỉ bài thật; 4 thiết kế problem có bổ sung tổng hợp | 4 candidate facet records tổng hợp duy nhất; không phải paper/abstract thật |
| Observation, query, phản ứng D, đáp án | Generator D của proposal | Mô phỏng có kiểm soát; observation tách khỏi candidates |
| Nguồn cào thêm ngoài corpus | Trong backup; không đưa vào lượt này | Không dùng |
| Kết quả mới | `results/ordinal_common_20261021_01/` | Giữ nguyên hai lượt kết quả trước |

Chi tiết provenance ở [README_DATA](README_DATA.md). Không gọi đây là benchmark có nhãn chính thức của corpus hoặc phản ứng người dùng thật.

Code mới: `scripts/exp_d/proposal/ordinal_intent.py`, `common_ranking.py`, `run_ordinal_benchmark.py`, `test_ordinal_intent.py`. Đã chạy 26 tests. Runner kiểm hashes dữ liệu/baseline/kết quả cũ, tái hiện các chỉ số intent cũ, lưu predictions trước khi đọc đáp án; manifest phải có status complete.

Chạy lại với một thư mục output mới từ thư mục experiments:

```powershell
python -B scripts/exp_d/proposal/run_ordinal_benchmark.py --output data/exp_d/proposal/results/ordinal_common_repeat
```
