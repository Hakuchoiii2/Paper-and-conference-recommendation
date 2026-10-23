# Hai câu hỏi cần kiểm chứng của thực nghiệm D

1. **Suy intent:** từ query/phản ứng đầu phiên, có suy được người dùng muốn bài giống hay khác bài mốc ở facet nào không?
2. **Tác dụng lên ranking:** dùng hướng suy được đó có giúp xếp bài phù hợp nhu cầu lên đầu không?

Đây là hai câu hỏi nghiên cứu, không bắt buộc kết quả đều là “có”. Để kiểm tra câu 2, giữ nguyên scorer, weights, candidates và chỉ thay hướng; suy đúng intent chưa tự bảo đảm ranking tốt hơn.

**Hiện tại:** có bằng chứng hỗ trợ cả hai trong [benchmark cặp intent v1](contrast_report.md), với [proposal xếp hạng theo evidence](proposal.md). [Bộ phụ v2 nhiều ứng viên](multicandidate_report.md) giữ nguyên evidence và mở rộng 6/15 thiết kế: delta nDCG@10 predicted − always-similar là +0,0920/+0,0788 ở noise 0,2/0,5; compliance@5 tăng +0,0267/+0,0222 trên cùng pool v2. Khả năng suy intent giữ nguyên; nhóm similar ở noise cao có giảm và scorer strict vẫn có CI chạm 0. Kết luận có điều kiện trên 8 anchors/4 loại focus và nhãn overlap; chưa chứng minh hiệu quả với người thật hoặc anchors mới. Bộ canonical cũ vẫn chưa cho bằng chứng mạnh riêng cho câu 2; xem [đối chứng trước đó](evidence_report.md).
