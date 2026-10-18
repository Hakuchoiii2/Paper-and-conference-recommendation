# Kiểm tra mức sẵn sàng của dataset và baseline D

Ngày kiểm tra: 16/10/2026. Đối chiếu các yêu cầu trong [bao_cao_exposure_interaction_D.md](bao_cao_exposure_interaction_D.md) với output thực tế của `baseline_20261016_v1` và `baseline_20261016_v1_synthetic`.

## Kết luận

**Đã sẵn sàng để bắt đầu phát triển/cải tiến phương pháp dưới protocol mô phỏng. Chưa sẵn sàng để coi kết quả hiện tại là đánh giá cuối về khả năng tổng quát hóa.**

- Canonical dùng cho phát triển ranking/query trên bộ chính; không kiểm chứng được lợi ích behavior vì không có phản ứng D.
- Synthetic pilot dùng để phát triển và kiểm tra cơ chế suy hướng từ phản ứng, cũng như cách chuyển direction thành ranking. Đây là evidence mô phỏng có kiểm soát.
- Trước khi tune và đánh giá cuối, cần chốt phần phát triển/đánh giá tách theo anchor. Đổi seed phản ứng không tạo ra test set có anchor mới.
- Không cần đợi có người dùng thật hoặc sửa lại A/C để bắt đầu nghiên cứu trong phạm vi này. Nếu mục tiêu là chứng minh hiệu quả trên phản ứng người thật, bộ hiện tại chưa đáp ứng.

## Các kiểm tra đã thực hiện lại

| Yêu cầu | Kết quả kiểm tra hiện tại |
|---|---|
| Canonical hợp lệ theo pipeline | Chạy `build_exp_d.py --validate-only` trong snapshot hiện tại: COMPLETE; 1.500 sessions, 30.000 labels, 1.500 search events, 0 exposures/interactions |
| Đúng phiên bản input/code/output | 221 lượt đối chiếu SHA-256 đều khớp: canonical manifest, pilot manifest, source hashes và export receipts |
| Pilot giữ nguyên dữ liệu cần ranking | So trực tiếp sessions, queries, intents và labels với phần tương ứng trong canonical: khớp |
| Nhỏ, có phân tầng | 30 phiên, đủ 30 tổ hợp 5 focus × 2 direction × 3 query mode; 28 anchors riêng |
| Synthetic chỉ làm observation | Mỗi cấu hình có 240 observation, 120 exposures và 240 reactions; `validate_overlay` pass cả 6 cấu hình, gồm tách anchor/candidates và provenance |
| Matching, nhãn và thời gian | Checker `check_d` hiện hành pass trên cả 6 overlay đã lưu |
| Phản ứng phụ thuộc intent và có nhiễu | Tái sinh observation/provenance/exposures/reactions bằng seed/noise ghi trong từng manifest: khớp dữ liệu đã lưu ở cả 6 cấu hình |
| So cùng dữ liệu và baseline | Tính lại public predictions ở hai điều kiện bằng helper snapshot và vector corpus thật cố định: khớp output cả 6 cấu hình |
| Metrics có thể kiểm tra lại | Tính lại details và summary từ 7.500 predictions canonical + 1.800 predictions pilot: khớp output sau chuẩn hóa JSON; tính lại focus accuracy/coverage/macro-F1: khớp |
| Tests hợp đồng overlay | 5 tests pass khi nạp dependency từ snapshot `workspace_baseline_20261016_v1` |
| Dev/test độc lập theo anchor | Chưa thấy cơ chế chia dev/test theo anchor trong pipeline/pilot hiện tại; không coi sáu seed/noise là sáu bộ test độc lập |

Lưu ý tái lập tests: lệnh unittest ghi trong tài liệu hiện thất bại ở import `experiment_io`, vì test hardcode `data/exp_d/workspace/` cũ. Khi thêm `workspace_baseline_20261016_v1/scripts` và root snapshot hiện tại vào `sys.path` trước khi discover tests, cả 5 tests pass. Đây là vấn đề đường dẫn chạy tests cần chỉnh khi chuẩn hóa pipeline, không phải bằng chứng dataset bị sai. Đợt review này không sửa mã test hay dataset.

## Kết quả và giới hạn cần giữ khi cải tiến phương pháp

| Nội dung | Hiện tại | Ý nghĩa cho bước tiếp |
|---|---|---|
| Độ phủ canonical | 1.500 phiên nhưng chỉ 57 anchors | Không chia ngẫu nhiên từng dòng phiên rồi mặc định nội dung độc lập; cần chia theo nhóm anchor |
| Positives theo intent | Trung bình 4,5 bài grade 2/20 candidates | Trần compliance theo pool: @5 = 0,60; @10 = 0,45; tăng điểm cần đọc cùng giới hạn pool |
| Behavior focus, noise 0,2 | Accuracy/coverage 100% ở cả 3 seed | Điều kiện dễ đã bão hòa; khó dùng riêng điều kiện này để chứng minh estimator mới tốt hơn |
| Behavior focus, noise 0,5 | Accuracy 83,33% / 100% / 90%; coverage 86,67% / 100% / 93,33% | Báo tất cả seed, không chỉ chọn seed thuận lợi |
| Behavior ranking pilot | Cả 6 cấu hình: nDCG@10 0,8305 → 0,8284; compliance@5 0,4533 → 0,4533 | Evidence đã giúp suy hướng, nhưng ranking chưa tốt hơn; có cơ sở để phân tích scorer/weights/biểu diễn, chưa đủ để xác định nguyên nhân |

## Cách chuyển sang giai đoạn phương pháp

1. Chốt câu hỏi: cải thiện suy hướng, ranking theo intent, hay cả hai; ghi riêng đóng góp muốn kiểm chứng.
2. Giữ pilot hiện tại làm bộ phát triển/chẩn đoán. Xác định phần đánh giá giữ lại theo anchor trước khi tune; kiểm tra độ phủ facet/direction/query mode sau chia. Với chỉ 57 anchors, cần báo rõ giới hạn độ phủ, có thể phải mở rộng thiết kế đánh giá nếu phép chia quá ít mẫu.
3. Cố định phiên bản input, candidate pools, nhãn, cutoff, simulator và các seed/noise cho phép so. Chạy baseline và phương pháp mới trên cùng phần dữ liệu và cùng điều kiện observation.
4. Báo focus-only và ranking/compliance tách biệt; giữ oracle làm đối chứng đặc quyền. Nếu thay nhiều thành phần, thêm phép thử tách tác dụng của direction, weights hoặc biểu diễn.
5. Chỉ tuyên bố cải tiến theo kết quả trên phần đánh giá giữ lại. Không so trực tiếp report canonical 1.500 phiên với pilot 30 phiên để quy kết tác dụng của thuật toán.

## Vì sao số trong báo cáo exposure/interaction khác?

[Báo cáo ngày 15/10](bao_cao_exposure_interaction_D.md) ghi pilot cũ `synthetic_observation_pilot_v1`: 30 anchors và các metrics khác. Mục 1–11 còn giữ trạng thái lịch sử trước triển khai. Các con số đó không mô tả lượt hiện tại.

Lượt được review ở đây lấy từ canonical mới trong `workspace_baseline_20261016_v1/`; pilot chọn 30 phiên/28 anchors từ bộ này. Giữ các kết quả lịch sử để tham chiếu, nhưng không trộn thành cùng một lượt chạy.

Kết quả để xem: [canonical report](../results/baseline_20261016_v1/report.md), [pilot report seed 42 noise 0,2](../results/baseline_20261016_v1_synthetic/seed_42_noise_0.2/results/report.md), [focus qua seed/noise](../results/baseline_20261016_v1_synthetic/focus_sensitivity.json).
