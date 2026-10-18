# Đọc tài liệu D theo thứ tự nào?

| File hiện hành | Dùng khi nào? |
|---|---|
| [luandiem.md](luandiem.md) | Đọc trước: hai câu hỏi D cần kiểm chứng |
| [overview.md](overview.md) | Tra thuật ngữ, dữ liệu, sơ đồ và cách đọc kết quả |
| [contrast_report.md](contrast_report.md) | Kết quả mới nhất: hai luận điểm trong benchmark cặp intent; đọc cùng giới hạn 8 anchors/mô phỏng |
| [proposal.md](proposal.md) | Phương pháp đề xuất, giả thuyết, đối chứng và phạm vi áp dụng |
| [evidence_report.md](evidence_report.md) | Đối chứng trên bộ cũ và lý do cần benchmark cặp intent riêng |
| [guideline_pipeline.md](guideline_pipeline.md) | Chạy lại pipeline baseline; lệnh cho các lượt cải tiến ở nhật ký bên dưới |
| [changed_improve.md](changed_improve.md) | Code đã thêm, lệnh chạy M0/SBERT/evidence, kết quả, backup/restore |
| [improve_plan.md](improve_plan.md) | Kế hoạch và bài báo tham khảo; đọc cùng evidence mới, không coi mọi hướng trong plan là đã triển khai |

Yêu cầu gốc vẫn ở [README dữ liệu D](../README.md), [README scorer D](../../../scripts/exp_d/README.md) và [protocol 2.0](../../../docs/EXPERIMENT_PROTOCOL.md).

Code phương pháp/runner/test đã gom ở `scripts/exp_d/`; xem [bảng file và lệnh chạy mới](../../../scripts/exp_d/README.md). Dữ liệu, model/cache, kết quả, generator và công cụ pipeline vẫn ở `data/exp_d/`.

Các checklist, tiến độ và báo cáo baseline trước cải tiến đã chuyển sang [old/](old/README.md). Giữ chúng để truy lịch sử; không cần đọc hết và không dùng số liệu cũ thay kết luận hiện tại. Không xóa dataset, code hoặc output thực nghiệm trong đợt dọn tài liệu này.

`expE-16.10.26.pdf` được giữ nguyên vì là tài liệu về E, chưa xác định là tài liệu lỗi thời của D.
