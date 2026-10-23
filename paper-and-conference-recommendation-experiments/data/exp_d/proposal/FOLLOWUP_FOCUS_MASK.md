# Vì sao điểm cao, baseline có thể là proposal, và thử cải tiến nào?

Ngày 21/10/2026. Bản này bổ sung sau benchmark bảy cấu hình, không sửa điểm hoặc thay thế lịch sử kế hoạch trước chạy.

## 1. Baseline tốt có bắt buộc thêm method không?

Không. Hai luận điểm D có thể được kiểm chứng bằng một phương pháp tốt và các đối chứng phù hợp. Không cần thêm model chỉ để tạo một hàng thắng baseline.

“Baseline” là vai trò trong phép so. Nếu direction_search là thiết kế của nhóm, có thể trình bày nó như phương pháp chính và dùng fixed/profile-similar, query-only, behavior-only làm đối chứng/ablation. Nhưng điểm cao không chứng minh tính mới, và không được gọi quy tắc quen thuộc là thuật toán mới chỉ vì đổi nhãn từ baseline sang proposal.

Git cho thấy runner bốn baseline và direction_search đã có từ commit `8206521` (feat: add behavior-driven A-E experiment protocol), trước lượt viết benchmark hiện tại. Đây không phải method mới do lượt này tạo ra. Code đang dùng là quy tắc riêng của dự án, chưa được xác nhận là reproduction của một bài cụ thể. Git không đủ chứng minh ai là người đầu tiên nghĩ ra ý tưởng trong literature; cần đối chiếu và trích nguồn khi viết bài.

## 2. Điểm đang đo trên dữ liệu nào?

`data/exp_d/proposal/datasets/observation_v1/`:

- Nguồn có 4.210 bài thật, 3.240 bài qua bộ lọc facet A. Không dùng nguồn cào ngoài corpus.
- Chỉ 12 anchors, 19 thiết kế và 114 phiên; mỗi phiên xếp hạng pool có sẵn 20 candidates, không retrieval trong toàn corpus 4.210 bài.
- 15 thiết kế có candidates toàn thật; 4 thiết kế problem bổ sung đúng một candidate facet tổng hợp ở phía thiếu.
- Observation là 152 bản ghi facet tổng hợp riêng. Mỗi phiên có 4 cặp matched, được dựng để chỉ focus khác nhau; phản ứng mô phỏng có xu hướng đúng intent, cộng nhiễu.
- Query clear dùng template có concept/facet đã biết. Query ambiguous/none không cung cấp hướng rõ cho parser gốc.
- So trên concept/facet và TF-IDF facet; không phải đánh giá khả năng đọc hiểu abstract tự nhiên hoặc phản hồi người thật.

Sáu seed/noise conditions là lần lặp trên cùng cấu trúc này, không tạo thêm anchors/người dùng độc lập.

## 3. Vì sao nDCG và accuracy trông cao?

Pool gồm 1 candidate grade 2, 1 grade 1 và 18 grade 0 ngoài context. Scorer đã có gate context, nên việc loại 18 bài dễ hơn nhiều so với retrieval giữa nhiều bài gần nghĩa.

Chỉ cần hai bài liên quan nằm top 2, dù **đảo thứ tự** grade 1 lên trên grade 2, nDCG@10 vẫn bằng:

`(1 + 3/log2(3)) / (3 + 1/log2(3)) = 0.7967`.

Vì vậy nDCG xấp xỉ .80 không có nghĩa chọn đúng nhu cầu 80%. Bổ sung tỷ lệ điểm grade 2 cao hơn grade 1 giúp nhìn đúng lỗi đổi hướng: baseline direction_search chỉ đạt 70,37% ở chỉ số này dù accuracy hướng đạt 96,91%.

Accuracy cao cũng đúng với mức đơn giản của mock: noise .2 cho DELTA 100%; query clear cho parser 100%; mỗi cặp đã cô lập focus. Điều đó kiểm tra được cơ chế trong mô phỏng, chưa chứng minh mô hình mạnh ngoài thực tế.

Độ khó giữa nhóm khác nhau: baseline direction_search nDCG .7656 ở candidates toàn thật và .9942 ở nhóm mixed/problem. Hai nhóm khác cả focus lẫn nguồn candidate, không suy riêng ảnh hưởng synthetic từ chênh lệch đó.

## 4. Chẩn đoán trước khi cố tăng accuracy hướng

Đã chạy riêng hai oracle dùng đáp án ẩn **chỉ trong evaluator**, không là method cạnh tranh:

| Chẩn đoán | nDCG@10 |
|---|---:|
| DELTA + query thật sự chạy | .8418 |
| Biết focus/hướng thật, facet khác vẫn unknown | .8427 |
| Biết toàn bộ intent, gồm facet nào ignore | .9711 |

Các oracle vẫn dùng trọng số C gốc, không đọc hidden weights. Chúng là mốc chẩn đoán, không là trần toán học của mọi cấu hình scorer.

Khoảng .8418 → .8427 rất nhỏ: với chính sách facet khác unknown hiện tại, suy đúng thêm vài direction không đủ làm nDCG nhảy lên gần 1. Vấn đề lớn nằm ở việc scorer xử lý unknown như similar và tiếp tục xét các facet ngoài nhu cầu phiên, gồm cả lỗi missing ở các facet đó.

## 5. Một hướng mới đã code và thử: DELTA-ACTIVE

Không thay estimator dấu của DELTA và không sửa hàm `intent_scores`:

1. Lấy directions từ DELTA + query gốc.
2. Nếu duy nhất một facet ngoài context có direction xác định, coi đó là focus suy được.
3. Giữ context/focus, đánh dấu các facet còn lại `ignore`.
4. Nếu focus chưa xác định hoặc nhiều focus, giữ nguyên fallback gốc.

Code `focus_masked.py` chỉ nhận context và directions đã suy được. Không nhận truth, candidate IDs, scores hoặc nhãn. Các predictions hợp lệ được tính/lưu trước khi nạp truth. Oracle được tạo sau và ghi file riêng.

Scorer, vector và trọng số C **đầu vào** giữ nguyên. Nhưng khi dùng ignore, tập facet hoạt động và mẫu số chuẩn hóa trong scorer đổi; tức trọng số hiệu dụng thay đổi. Vì vậy đây là cải tiến **dự đoán scope/active facets của intent**, không chỉ cải thiện dấu similar/different và không được mô tả là weights hiệu dụng hoàn toàn bất biến.

Đối chứng `active_similar` dùng cùng focus suy được và cùng mask, nhưng luôn đặt hướng similar. Nó tách lợi ích của hướng khỏi lợi ích chọn facet.

## 6. Kết quả thăm dò

| Phương pháp hợp lệ | Accuracy hướng | nDCG@10 | Điểm grade 2 > grade 1 |
|---|---:|---:|---:|
| DELTA + query gốc | 96,91% | .8418 | 70,37% |
| Cùng focus/mask, luôn similar | 48,88% | .8944 | 50,00% |
| **DELTA-ACTIVE** | **96,91%** | **.9632** | **97,34%** |

DELTA-ACTIVE không làm accuracy hướng tăng; nó dùng hướng đã suy được trên tập facet phù hợp hơn. Chênh nDCG so với baseline là +.1214; khoảng paired theo anchor [.0434, .2018]. So với đối chứng cùng mask nhưng always-similar là +.0688, khoảng [.0388, .0889]. Đây là khoảng thăm dò, không điều chỉnh cho việc chọn hướng nghiên cứu sau khi xem kết quả cũ.

Theo nguồn candidates: nhóm toàn thật .7656 → .9483; nhóm mixed/problem .9942 → .9929. Không thắng mọi nhóm: mixed đã gần bão hòa và giảm nhẹ. Không đổi dataset hoặc thresholds để làm điểm đẹp.

Đã chạy 21 tests (16 benchmark + 5 mask), đối chiếu lại điểm baseline bằng evaluator của probe. Bản benchmark bảy cấu hình và mọi input/scorer gốc giữ nguyên.

## 7. Đọc kết quả và chọn proposal

Hướng DELTA-ACTIVE đáng tiếp tục hơn việc thêm một mô hình Bayes đếm phiếu chỉ đổi dấu: nó nhắm đúng chỗ gây mất ranking. Có thể chọn làm **proposal ứng viên cho pilot**, giữ DELTA + query là đối chứng không mask và active_similar là đối chứng không dùng hướng.

Tuy nhiên method này được đề xuất sau khi xem benchmark. Không trình bày điểm .9632 như kết quả trên test độc lập hoặc tự nhận có novelty. Cần khóa thiết kế rồi kiểm chứng trên nội dung độc lập nếu muốn claim ưu thế tổng quát. Dataset mock hiện tại có một focus và các facet khác thực sự ignore theo thiết kế; mask đang khớp giả định đó, chưa giải quyết intent đa focus hoặc relevance ngữ nghĩa ngoài protocol.

Nếu muốn cải tiến riêng estimator sau này: [AMPLe, ACL 2025](https://aclanthology.org/2025.acl-long.1590/) nghiên cứu posterior có sửa đổi cho feedback so sánh có nhiễu; [RecPO, ACL 2026](https://aclanthology.org/2026.acl-long.656/) cho thấy vai trò của cường độ preference và thời gian trong LLM sequential recommendation. Có thể lấy cảm hứng giữ cường độ action thay vì chỉ phiếu +/-; không cắm nguyên hai pipeline đó vào D hoặc gọi mask này là reproduction của chúng.

## File để kiểm tra

- [Report probe](results/focus_probe_20261021_01/report.md)
- [Bảng chính probe](results/focus_probe_20261021_01/summary.csv)
- [Phân nhóm](results/focus_probe_20261021_01/groups.csv)
- [Manifest và nguồn benchmark cũ](results/focus_probe_20261021_01/manifest.json)
- [Code method](../../../scripts/exp_d/proposal/focus_masked.py)
- [Code chạy probe](../../../scripts/exp_d/proposal/probe_focus_mask.py)

Tái lập từ gốc project thực nghiệm với output mới:

```powershell
python -B -m unittest discover -s scripts/exp_d/proposal -p "test_*.py" -v
python -B scripts/exp_d/proposal/probe_focus_mask.py --output data/exp_d/proposal/results/my_new_focus_probe
```
