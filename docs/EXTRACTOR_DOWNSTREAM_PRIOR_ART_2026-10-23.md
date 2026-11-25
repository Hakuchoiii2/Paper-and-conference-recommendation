# Prior art: thay extractor và đo downstream

Tra cứu có chọn lọc ngày 2026-10-23; không phải systematic review. Mục tiêu đối chiếu: cùng prompt/schema, nhiều LLM extractor, giữ encoder/ranker, đo extraction và paper retrieval cùng manuscript–conference ranking. Chưa tìm thấy công trình khớp toàn bộ thiết kế trong các nguồn đã kiểm tra; điều đó không chứng minh thiết kế là mới.

## Các bằng chứng gần nhất

| Nguồn sơ cấp | Thí nghiệm xác minh | Khác thiết kế dự kiến |
|---|---|---|
| [RAS, v3 29/1/2026, Table 3](https://arxiv.org/html/2502.10996v3) | Thay triple extractor Flan-T5-Large, LLaMA-3.2-3B, Claude-3.5-Sonnet; đo QA trên TQA/2WQA/PopQA và throughput. | Extraction tạo triples sau retrieval; downstream là generation, không phải ranking paper/venue từ facet. Các extractor có cách huấn luyện khác nhau, không coi là cùng-prompt comparison. |
| [ChainRAG, ACL 2025, §4.8.1–4.8.2](https://aclanthology.org/2025.acl-long.1089.pdf) | So spaCy với Qwen2.5-72B trong entity recognition, báo final QA F1; phân tích lỗi decomposition/entity recovery. | Entity extraction và multi-hop QA; không phải nhiều LLM scientific-facet extractors hay conference ranking. QA F1 không phải extraction F1. |
| [Entity-Augmented Neuroscience Knowledge Retrieval, arXiv 2025, §II.B–C và IV.A–B](https://arxiv.org/pdf/2506.03145) | So nhiều LLM ở extraction; retrieval thử trọng số entity-centric spans. | Retrieval spans được tạo bằng Llama-3.3-70B; bảng extraction nhiều model không phải bảng downstream cho từng model. Không diễn giải hai bảng thành phép so extractor→retrieval trực tiếp. |
| [Scideator, v7 sửa 16/5/2026, §4.2 và Appendix F](https://arxiv.org/html/2409.14634v7) | Facet purpose/mechanism/evaluation; retrieval ablation và classifier ablation. | So module/representation, không phải thay extractor model có kiểm soát. Mặc định gpt-4o-2024-08-06; novelty checking khác paper relevance/conference fit. |
| [FaBle, ACL 2025, §3 và Appendix B](https://aclanthology.org/2025.acl-long.1388.pdf) | LLaMA2-13B decomposition/generation/recomposition tạo dữ liệu học retrieval. | Tác dụng đi qua augmentation/training; không phải benchmark nhiều extractor cố định downstream. Facet summaries không mặc định là gold concepts. |
| [An LLM-Powered Semantic Alignment Framework for Journal Recommendation, arXiv 26/6/2026](https://arxiv.org/html/2606.27930v1) | DeepSeek-V3 đối chiếu nội dung manuscript với journal scope; §7 nêu hạn chế single-model. | Direct ranking, journal thay conference, không có trung gian năm facet hoặc extraction F1. Single-model limitation ở một bài không chứng minh cross-model research chưa có toàn ngành. |
| [Context Selection for Hypothesis and Statistical Evidence Extraction, arXiv 22/3/2026](https://arxiv.org/abs/2603.21193) | Theo abstract: bốn LLM extractors, biến thể retrieval/context và oracle paragraphs. | Hướng tác động retrieval→extraction, ngược với extraction→retrieval dự kiến. |

## Hệ quả cho cách phát biểu đóng góp

- Không phát biểu “đầu tiên nghiên cứu extractor ảnh hưởng downstream”: RAS/ChainRAG đã có thí nghiệm trực tiếp liên quan.
- Có thể nghiên cứu hẹp: scientific-facet extraction quality có dự báo được paper retrieval và venue ranking không, dưới downstream được kiểm soát.
- Chọn một prompt không tạo kết luận model-intrinsic. Kết luận chỉ đúng cho model + prompt + schema + decoding đã thử. Thử thêm một prompt tương đương trên subset để kiểm tra độ bền nếu nguồn lực cho phép.
- Có nhiều downstream không tự tạo novelty. Cần phát hiện định lượng, phân tích lỗi, nhãn độc lập và kết luận có giới hạn.
- Không so trực tiếp con số giữa các công trình khác task, dataset, metric, pool và split.

## Phạm vi xác minh

Đã đọc các phần thí nghiệm nêu trên của RAS, ChainRAG, Neuroscience Retrieval, Scideator và FaBle; nguồn journal recommendation được đối chiếu toàn văn công khai. Context Selection được đối chiếu abstract, chưa audit toàn bộ experiment. Không chạy tái lập hoặc xác minh mọi số liệu tác giả báo cáo. Các trang arXiv được dẫn theo phiên bản; không tự suy trạng thái peer review.
