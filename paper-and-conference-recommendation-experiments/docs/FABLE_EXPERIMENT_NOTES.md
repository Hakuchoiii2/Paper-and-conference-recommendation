# FaBle: kiểm chứng thực nghiệm

Nguồn: [PDF gốc](https://aclanthology.org/2025.acl-long.1388.pdf), §5–6, Bảng 1–2, Phụ lục B/D.

- CSFCube: 50 cặp abstract–facet; NDCG%20 dùng K=0,2×số ứng viên, không phải @20.
- Bảng 2 (NDCG%20/MAP): SPECTER 53,28/34,23; +FaBle 56,60/35,60. Method: 37,41/22,44→44,97/25,98. Background MAP giảm 43,95→42,66.
- FaBleSpec+HN: Method 49,43/32,57, vượt ASPIRE tốt nhất 48,20/28,86; tổng 59,76/38,73 vẫn dưới OT-ASPIRE 61,41/40,79.
- “1K” chính xác 1.017 abstracts S2ORC; 40.680 triplets/facet. Đây là dữ liệu bổ sung: SPECTER đã pretrained; FaBleSpec còn kế thừa 1,3M co-citation examples.
- Ba seeds; batch 30; hai epochs; learning-rate 1e-5; margin 1; train/validation 9:1 trên dữ liệu sinh. Không mô tả rõ chia theo abstract gốc: cần kiểm tra nguy cơ các tổ hợp chung nguồn lọt hai split; chưa đủ căn cứ kết luận leakage.
- Bảng 1: FEIR có 8 queries/facet, 23/80/70 ứng viên Story/Question/Options; train 717 items. Đánh giá nhỏ, chỉ hai miền, chưa chứng minh tổng quát rộng.
- Bài không giải thích rõ inference conditioning/separate-model-per-facet; không suy diễn thành encoder đa facet điều khiển tùy ý.
