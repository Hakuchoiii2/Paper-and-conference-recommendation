# ASPIRE: kiểm chứng thực nghiệm

[Nguồn gốc: NAACL 2022](https://aclanthology.org/2022.naacl-main.331.pdf), §4, Appendices G–I.

NDCG%20 dùng K=20% số ứng viên/query; không phải NDCG@20. Bốn dataset: CSFCUBE, TRECCOVIDRF, RELISH, SCIDOCS. CSFCUBE đánh giá background/method/result; ba bộ còn lại xét abstract. SCIDOCS có bốn task.

Table 1, CSFCUBE Aggregated:

| Model | MAP | NDCG%20 |
|---|---|---|
| SPECTER | 34.23 | 53.28 |
| TS | 40.26 | 60.71 |
| OT | 40.79 | 61.41 |
| TS+OT | 40.26 | 60.86 |

TS+OT không luôn thắng. TS thắng method; OT thắng result, aggregate và TRECCOVIDRF; TS+OT thắng RELISH (Table 2). Ba lượt chạy; CSFCUBE dùng 2-fold CV. Appendix I: độ lệch chuẩn; chênh nhỏ chưa chứng minh ý nghĩa thống kê.

Appendix H: A1 ủng hộ co-citation text; A2 attention thắng aggregate CSFCUBE, thua biomedical; A3: ảnh hưởng initialization.

Sparsity của OT tuyến tính không đảm bảo cho entropy-regularized Sinkhorn (§3.2.3, F). Giới hạn: English, title+abstract; OT chậm; SCIDOCS Citations thua SPECTER.
