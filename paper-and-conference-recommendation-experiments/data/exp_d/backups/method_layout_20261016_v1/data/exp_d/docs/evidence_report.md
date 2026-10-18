# Kết quả bổ sung bằng chứng cho thực nghiệm D

Ngày chạy: 16/10/2026. Đọc lại README D và protocol 2.0 trước triển khai. Không sửa dataset canonical, nhãn, baseline, scorer/evaluator/validator hoặc simulator gốc.

## 1. Thiết kế và phạm vi kết luận

- Kết quả chính: giữ nguyên scorer, weights C, missingness và gate context của protocol; chỉ can thiệp hướng tại focus dự đoán: predicted / always-similar / flipped. Context luôn giữ similar, unknown giữ nguyên.
- Kết quả phụ: cùng M0 priority trong ba nhánh, với điểm phá hòa lấy từ all-similar để direction dự đoán không lọt vào nhánh đối chứng qua secondary score. M0 là mở rộng policy, không phải scorer gốc của protocol.
- Canonical: 1.500 phiên/57 anchors. Overlay mở rộng riêng: 171 phiên/57 anchors, chọn tối đa 3 phiên mỗi anchor bằng hash public case ID, không chọn theo điểm/nhãn; giữ nguyên candidates/query/intent/relevance/cutoff nguồn.
- Overlay có 684 exposures/1.368 interactions mỗi cấu hình, 3 seeds × 2 noise. Synthetic chỉ dành cho observation; matching, thời gian và nhãn được check_d hiện hành kiểm tra. Không nhập chúng vào corpus/A silver.
- Xáo action trong từng phiên, giữ nguyên IDs, exposures, timestamps và phân bố action; 10 lần xáo mỗi cấu hình. Đây là negative control, không gọi là phản ứng simulator gốc hợp lệ về utility.
- Chia anchor bằng hash: {'audit': 11, 'development': 34, 'validation': 12}. Các phần không trùng anchor, nhưng canonical đã được xem trong các lượt trước, vì vậy đây là retrospective audit, chưa phải test hoàn toàn chưa chạm.
- Không train/tune hoặc đổi threshold. CI 95% dùng 2.000 cluster bootstrap theo anchor; gộp seed bằng trung bình theo phiên trước khi bootstrap, không coi ba seed là ba cohort độc lập. Nhiều phép so mang tính thăm dò, không diễn giải CI riêng lẻ thành chứng minh tổng quát.

## 2. Bằng chứng phản ứng giúp suy hướng

| Cấu hình | Accuracy có phản ứng đúng liên kết | Accuracy không phản ứng | Accuracy xáo trung bình | Coverage xáo trung bình |
|---|---:|---:|---:|---:|
| seed_42_noise_0.2 | 1.0000 | 0.0000 | 0.3404 | 0.6807 |
| seed_42_noise_0.5 | 0.8772 | 0.0000 | 0.3801 | 0.7468 |
| seed_43_noise_0.2 | 0.9942 | 0.0000 | 0.3626 | 0.6889 |
| seed_43_noise_0.5 | 0.9240 | 0.0000 | 0.3965 | 0.7561 |
| seed_44_noise_0.2 | 1.0000 | 0.0000 | 0.3596 | 0.7018 |
| seed_44_noise_0.5 | 0.8772 | 0.0000 | 0.3994 | 0.7678 |

Accuracy được tính trên focus thật khi đánh giá; unknown tính chưa đúng. Xáo làm thay đổi cả coverage nên không chỉ so accuracy trên những phiên đã quyết định. Việc xác định focus từ cấu trúc cặp được kiểm soát cũng là giả định của simulator.

## 3. Tác dụng riêng của direction với scorer gốc

Delta = predicted − always-similar, cùng focus dự đoán và cùng scorer. Bảng overlay đã trung bình 3 seed ở mỗi noise.

| Bộ / noise | Nhánh | Metric | Delta | CI 95% theo anchor |
|---|---|---|---:|---|
| Canonical | strict_behavior_predicted | ndcg@10 | 0.000000 | [0.000000, 0.000000] |
| Canonical | strict_behavior_predicted | intent_compliance@5 | 0.000000 | [0.000000, 0.000000] |
| Canonical | strict_search_predicted | ndcg@10 | 0.000050 | [-0.000269, 0.000385] |
| Canonical | strict_search_predicted | intent_compliance@5 | 0.000533 | [0.000124, 0.001127] |
| Overlay noise 0.2 | strict_behavior_predicted | ndcg@10 | -0.000703 | [-0.002453, 0.000744] |
| Overlay noise 0.2 | strict_behavior_predicted | intent_compliance@5 | 0.001170 | [0.000000, 0.003509] |
| Overlay noise 0.2 | strict_search_predicted | ndcg@10 | -0.000703 | [-0.002453, 0.000744] |
| Overlay noise 0.2 | strict_search_predicted | intent_compliance@5 | 0.001170 | [0.000000, 0.003509] |
| Overlay noise 0.5 | strict_behavior_predicted | ndcg@10 | -0.000843 | [-0.002610, 0.000517] |
| Overlay noise 0.5 | strict_behavior_predicted | intent_compliance@5 | 0.000780 | [0.000000, 0.002339] |
| Overlay noise 0.5 | strict_search_predicted | ndcg@10 | -0.000899 | [-0.002671, 0.000485] |
| Overlay noise 0.5 | strict_search_predicted | intent_compliance@5 | 0.000780 | [0.000000, 0.002339] |

Xem summary.csv/report.md của từng cấu hình để đọc điểm tuyệt đối và nhóm focus, query mode, intent similar/different, anchor audit. Các so sánh với flipped có trong paired_comparisons.json và seed_averaged_comparisons.json.

## 4. Đối chứng M0 và giới hạn pool

| Bộ | Intent thật | Phiên | Phiên có cả grade 1 và 2 | Tổng candidate grade 1 |
|---|---|---:|---:|---:|
| canonical | similar | 750 | 88 | 186 |
| canonical | different | 750 | 0 | 0 |
| expanded | similar | 84 | 12 | 34 |
| expanded | different | 87 | 0 | 0 |

Grade 1 là đúng context nhưng sai hướng focus. Khi các phiên different không có grade 1, ranker không phải lựa chọn giữa hai hướng trong cùng context; do đó khó kiểm chứng lợi ích riêng của different. Không sửa nhãn hoặc đổi pool trong lượt kiểm tra này.

| Bộ / noise | Nhánh M0 | Metric | Delta predicted − similar | CI 95% |
|---|---|---|---:|---|
| Overlay noise 0.2 | m0_behavior_predicted | ndcg@10 | 0.000000 | [0.000000, 0.000000] |
| Overlay noise 0.2 | m0_behavior_predicted | intent_compliance@5 | 0.000000 | [0.000000, 0.000000] |
| Overlay noise 0.2 | m0_search_predicted | ndcg@10 | 0.000000 | [0.000000, 0.000000] |
| Overlay noise 0.2 | m0_search_predicted | intent_compliance@5 | 0.000000 | [0.000000, 0.000000] |
| Overlay noise 0.5 | m0_behavior_predicted | ndcg@10 | 0.000000 | [0.000000, 0.000000] |
| Overlay noise 0.5 | m0_behavior_predicted | intent_compliance@5 | 0.000000 | [0.000000, 0.000000] |
| Overlay noise 0.5 | m0_search_predicted | ndcg@10 | 0.000000 | [0.000000, 0.000000] |
| Overlay noise 0.5 | m0_search_predicted | intent_compliance@5 | 0.000000 | [0.000000, 0.000000] |

So predicted với flipped (trung bình 3 seed, nhóm overall):

| Noise | Nhánh | Metric | Delta predicted − flipped | CI 95% |
|---|---|---|---:|---|
| 0.2 | strict_behavior_predicted | ndcg@10 | 0.037907 | [0.015410, 0.063133] |
| 0.2 | strict_behavior_predicted | intent_compliance@5 | 0.009357 | [0.003509, 0.016374] |
| 0.2 | m0_behavior_predicted | ndcg@10 | 0.015641 | [0.005209, 0.027589] |
| 0.2 | m0_behavior_predicted | intent_compliance@5 | 0.003509 | [0.000000, 0.009357] |
| 0.5 | strict_behavior_predicted | ndcg@10 | 0.035722 | [0.014043, 0.060107] |
| 0.5 | strict_behavior_predicted | intent_compliance@5 | 0.008187 | [0.002729, 0.014815] |
| 0.5 | m0_behavior_predicted | ndcg@10 | 0.014697 | [0.005067, 0.025804] |
| 0.5 | m0_behavior_predicted | intent_compliance@5 | 0.003509 | [0.000000, 0.009357] |

Đảo hướng có thể làm giảm kết quả ở các phiên similar có candidates cạnh tranh, nhưng predicted thắng flipped chưa đủ chứng minh tốt hơn đối chứng luôn-similar; phải đọc cả hai phép so.

## 5. Luận điểm được hỗ trợ và điều chưa chứng minh

**Luận điểm 1 — có bằng chứng:** trong simulator matched-pair hiện tại, phản ứng gắn đúng bài mang tín hiệu để suy similar/different; đối chứng không phản ứng và xáo action giúp phân biệt tín hiệu này khỏi việc chỉ có thêm log.

**Luận điểm 2 — cần đọc theo độ lớn thực tế:** phép so strict ở mục 3 mới tách tác dụng hướng khỏi scorer/weights/gate. Không lấy mức tăng M0 so baseline cũ làm mức tăng riêng của direction. Chênh lệch nhỏ hoặc CI chứa 0 không đủ cho khẳng định mạnh.

**Giới hạn quyết định:** pool hiện tại thiếu hoàn toàn grade 1 ở nhóm different. M0 có điểm cao trên nhãn overlap không tự chứng minh hiểu nhu cầu muốn khác; nếu predicted bằng always-similar thì phải báo đó là kết quả không phân biệt được tác dụng.

**Chưa chứng minh:** hiệu quả với người thật, quan hệ nhân quả trên log thực, semantic relevance độc lập, tính mới thuật toán, hoặc generalization trên test chưa từng quan sát.

## 6. Bước tiếp đúng protocol

Nếu mục tiêu bắt buộc chứng minh tác dụng different, thiết kế benchmark đối chứng riêng có cả bài cùng/khác focus trong cùng context, dùng corpus/facet thật và báo shortfall nếu không đủ; chốt intent trước sinh query/reaction/labels, giữ observation ngoài pool và tôn trọng cutoff. Không thay nhãn canonical cũ. Cần một phần dữ liệu/corpus được giữ riêng thật sự trước phát triển tiếp.

Không cần tiếp tục tải model để khắc phục thiếu đối chứng trong candidate pool. Có thể hoàn thành báo cáo thực nghiệm mô phỏng bằng cả phát hiện tích cực lẫn giới hạn này.

## 7. File và tái lập

- `data/exp_d/run_evidence_suite.py`: runner suite; output mặc định `data/exp_d/results/evidence_20261016_v1/`.
- `data/exp_d/summarize_evidence.py`: tạo báo cáo phân tích sau khi suite hoàn tất.
- `analysis/oracle_reference.json`: đối chứng đặc quyền từ evaluator cũ cho đúng 171 phiên/pools; oracle không dùng cho public scorer và không đổi theo observation.
- Mỗi condition có predictions/details/report/summary/focus metrics, paired comparisons và case studies. Không có case giảm ở một nhóm thì không bịa case giảm.
- `design.json` ghi quy tắc cố định trước khi đánh giá; `manifest.json` kiểm input/code/output; analysis có manifest riêng.

```powershell
python -B -m unittest discover -s data/exp_d -p test_evidence_controls.py
python -B data/exp_d/run_evidence_suite.py
python -B data/exp_d/summarize_evidence.py
```

Suite từ chối ghi đè output; nếu chạy lại cần --output tên mới và điều chỉnh đường dẫn input của summarizer tương ứng.

## 8. Ví dụ phiên và cách đọc kết quả

Các ví dụ chọn sau đánh giá để giải thích, không phải tiêu chí chọn dataset.

| Bộ | Family / loại | Case | Focus / intent thật | Delta compliance@5 predicted − similar |
|---|---|---|---|---:|
| canonical | strict / gain | D00904 | problem / different | +0.2000 |
| canonical | strict / tie | D00001 | problem / similar | +0.0000 |
| canonical | m0 / tie | D00001 | problem / similar | +0.0000 |
| noise 0,2 | strict / gain | D00888 | contribution / different | +0.2000 |
| noise 0,2 | strict / tie | D00002 | method / different | +0.0000 |
| noise 0,2 | m0 / tie | D00002 | method / different | +0.0000 |
| noise 0,5 | strict / tie | D00002 | method / different | +0.0000 |
| noise 0,5 | m0 / tie | D00002 | method / different | +0.0000 |

Case tie có thể do thiếu evidence (mọi nhánh fallback), candidate pool không có bài phân biệt hướng, hoặc scorer/gate cho các thứ tự không đổi; xem predictions cùng case_id để xác định từng trường hợp, không mặc định mọi tie cùng nguyên nhân.
Case gain/loss trong strict là chênh lệch khi chỉ đổi direction ở focus dự đoán. Grade 1 trong pool là điều kiện để tách được đúng/sai hướng trong cùng context; thiếu nó hạn chế khả năng diễn giải điểm cao của M0.
