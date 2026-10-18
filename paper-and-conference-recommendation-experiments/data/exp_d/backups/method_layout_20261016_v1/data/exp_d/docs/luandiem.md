# Hai câu hỏi cần kiểm chứng của thực nghiệm D

1. **Suy intent:** từ query/phản ứng đầu phiên, có suy được người dùng muốn bài giống hay khác bài mốc ở facet nào không?
2. **Tác dụng lên ranking:** dùng hướng suy được đó có giúp xếp bài phù hợp nhu cầu lên đầu không?

Đây là hai câu hỏi nghiên cứu, không bắt buộc kết quả đều là “có”. Để kiểm tra câu 2, giữ nguyên scorer, weights, candidates và chỉ thay hướng; suy đúng intent chưa tự bảo đảm ranking tốt hơn.

**Hiện tại:** có bằng chứng hỗ trợ câu 1 trong mô phỏng; chưa có bằng chứng mạnh cho câu 2. Xem [kết quả và giới hạn](evidence_report.md).
