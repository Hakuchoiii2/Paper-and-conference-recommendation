# Tiền lệ học thuật cho semantic scorer — 24/10/2026

## Kết luận

Có nghiên cứu dùng embedding similarity để đánh giá đầu ra LLM, kể cả extraction. Tuy nhiên, có tiền lệ không chứng minh scorer cụ thể của Exp A đã chính xác. Cần phân biệt: semantic similarity, tương đương thông tin, và groundedness.

## 1. KPEval — tiền lệ mạnh nhất về keyphrase và meta-evaluation

Wu, Yin và Chang. **KPEval: Towards Fine-Grained Semantic-Based Keyphrase Evaluation**, Findings ACL 2024.

- §5.1: cosine giữa embedding của từng phrase; SemP và SemR lấy trung bình điểm khớp tốt nhất theo hai chiều, rồi harmonic mean thành SemF1.
- Đây là soft score, không phải threshold TP/FN và không ràng buộc một-một.
- §7, B.2: trực tiếp đánh giá LLM zero/five-shot `text-davinci-003`.
- Có meta-evaluation với người; faithfulness được đo riêng. Điều này ủng hộ đánh giá nhiều chiều, không coi cosine là chứng nhận đúng nội dung.

[Bản chính thức, §5–7](https://aclanthology.org/2024.findings-acl.117.pdf) · [Mã tác giả](https://github.com/uclanlp/KPEval).

## 2. VarEx — cấu trúc gần scorer hiện tại nhất, nhưng là preprint

Pradhan và cộng sự. **A Pilot Project Leveraging Large Language Models for Automated Screening and Variable Extraction in Observational Studies**, medRxiv v2, 24/06/2026.

§2.4.3: nhúng tên biến bằng PubMedBERT, cosine mọi cặp, Hungarian assignment một-một; cặp đạt 0,60 thành TP; tính precision/recall/F1. Có strict score yêu cầu đúng cả biến và category. Appendix H khảo sát threshold trên 10 bài, 101 reference covariates.

Đây là tiền lệ trực tiếp cho LLM scientific extraction. Chưa qua peer review; khảo sát threshold nhỏ không xác lập ngưỡng phổ quát. Bài chỉ nói Hungarian assignment; không được tự đồng nhất với mục tiêu max-cardinality trước, max-weight sau của Exp A.

[Toàn văn v2 và Appendix H](https://pmc.ncbi.nlm.nih.gov/articles/PMC13308080/).

## 3. MultPAX — tiền lệ cosine threshold từ trước làn sóng chat LLM

Zahera và cộng sự. **MultPAX: Keyphrase Extraction Using Language Models and Knowledge Graphs**, ISWC 2022.

§5.2 dùng embedding và cosine, threshold >0,5 cho semantic matching; báo cáo semantic R@10/R@20 đối với absent keyphrase. Đây là tiền lệ keyphrase gần miền bài toán, nhưng không phải bằng chứng dùng scorer để đánh giá chat LLM hiện đại. Không nên lấy ngưỡng của họ áp sang encoder/domain khác. Ví dụ quan hệ “Cryptocurrency”–“Bitcoin” trong bài cũng nhắc rằng relatedness rộng hơn equivalence.

[Bản hội nghị, §5.2](https://iswc2022.semanticweb.org/wp-content/uploads/2022/11/978-3-031-19433-7_18.pdf).

## 4. SoftKeyScore — bằng chứng cần kiểm định encoder

Kundu, Chowdhury và Caragea. **Neural Keyphrase Generation: Analysis and Evaluation**, arXiv 2023.

SoftKeyScore tổng quát hóa set-level F1 bằng partial/semantic matching, thử BERTScore với nhiều encoder. Đánh giá 500 tài liệu KP20k: Pearson với người của F1@M là 0,3664; bản DeBERTa 0,3910; SciBERT 0,3543. Tác giả nhận xét SciBERT quá hào phóng. Chỉ một sinh viên chấm chính, tác giả kiểm 25%; không phải bằng chứng encoder nào cũng tốt hơn exact match.

[Toàn văn, bảng 5 và mục Human evaluation](https://arxiv.org/pdf/2304.13883).

## Hàm ý cho Exp A — đề xuất của người khảo sát

1. Gọi đúng là custom semantic matching F1; không gọi là KPEval/BERTScore nếu công thức khác.
2. Báo cáo song song exact/normalized match, semantic matching và human audit, tách groundedness.
3. Tạo tập cặp do người chấm độc lập: tương đương, liên quan nhưng khác, mâu thuẫn; có phủ định, số lượng, chủ thể, vai trò và điều kiện.
4. Chọn encoder/ngưỡng trên tập calibration, khóa trước test; báo cáo false match và độ nhạy xếp hạng R0/R1/R2 theo ngưỡng.
5. Mô tả rõ mục tiêu assignment; Hungarian tối đa tổng cosine và matching ưu tiên số cặp hợp lệ có thể cho kết quả khác nhau.

Ghi chú này là khảo sát tài liệu, không thay đổi code hay kết quả pilot.

## 5. Generative Information Extraction from Biographical Sources — LLM IE trực tiếp

Winkle, Kreutel và Stede, LaTeCH-CLfL/SIGHUM 2026, trang 311–322. §4.4 chấm các field string bằng embedding cosine, phối hợp similarity theo kiểu dữ liệu và lấy best match để tổng hợp precision/recall/F1. Thực nghiệm đánh giá Qwen-2.5-32B và Llama-3-70B-Instruct. Không phải one-to-one thresholded TP/F1 giống hệt Exp A. §6.2 cũng ghi nhận reference bỏ sót và metric sai alias; semantic matching không loại hết lỗi đánh giá.

[Paper và metadata](https://aclanthology.org/2026.latechclfl-1.30/) · [§4.4–6.2](https://aclanthology.org/2026.latechclfl-1.30.pdf).

## 6. Tiền lệ dùng đúng Qwen3-Embedding-0.6B

Mehta và cộng sự. **Large language model enhanced embeddings for knowledge aware recommender systems**, Discover Artificial Intelligence 6, 477, 21/05/2026. Strategy 2 dùng embedding soft precision/recall/F1 cho LLM-extracted KG triples. Strategy 4/5 so triple được trích với reference, nearest cosine; Strategy 5 dùng Qwen3-Embedding-0.6B, threshold 0,80. Không được gộp các strategy này thành khẳng định paper dùng đúng scorer Exp A. Tác giả cho biết thay encoder làm similarity và số match thay đổi mạnh; đây là tiền lệ triển khai, chưa chứng nhận equivalence hoặc ngưỡng 0,85 của Exp A.

[Bài chính thức, Strategies 2/4/5](https://link.springer.com/article/10.1007/s44163-026-01404-y).
