# Hai câu hỏi cần kiểm chứng của thực nghiệm D

1. **Suy intent:** từ query/phản ứng đầu phiên, có suy được người dùng muốn bài giống hay khác bài mốc ở facet nào không?
2. **Tác dụng lên ranking:** dùng hướng suy được đó có giúp xếp bài phù hợp nhu cầu lên đầu không?

Đây là hai câu hỏi nghiên cứu, không bắt buộc kết quả đều là “có”. Để kiểm tra câu 2, giữ nguyên scorer, weights, candidates và chỉ thay hướng; suy đúng intent chưa tự bảo đảm ranking tốt hơn.

**Hiện tại:** có bằng chứng hỗ trợ cả hai trong [benchmark cặp intent mô phỏng mới](contrast_report.md), với [proposal xếp hạng theo evidence](proposal.md). Kết luận có điều kiện trên 8 anchors/4 loại focus và nhãn overlap; chưa chứng minh hiệu quả với người thật hoặc anchors mới. Bộ canonical cũ vẫn chưa cho bằng chứng mạnh riêng cho câu 2; xem [đối chứng trước đó](evidence_report.md).
