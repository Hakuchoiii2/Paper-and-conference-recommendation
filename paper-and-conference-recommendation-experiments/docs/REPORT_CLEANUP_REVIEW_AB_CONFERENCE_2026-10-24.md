# Rà soát báo cáo đồ án: giữ A, B và conference

Ngày rà soát: 24/10/2026. Phạm vi: tài liệu và artifact trên máy, không kiểm tra trạng thái Kaggle trực tuyến, không chạy lại thực nghiệm. Chỉ tạo báo cáo này; chưa sửa, di chuyển hoặc xóa tài liệu cũ, code, config, dữ liệu hay model.

## 1. Báo cáo gần nhất và kết luận

Báo cáo định hướng mới nhất là [PAPER_STRUCTURE_SHARED_FACET_WEIGHTS_2026-10-23.md](PAPER_STRUCTURE_SHARED_FACET_WEIGHTS_2026-10-23.md), sửa lúc 22:57 ngày 23/10/2026 theo thời gian tệp trên máy. Đây là đề cương nghiên cứu, chưa phải báo cáo kết quả A/B/conference đã hoàn tất.

Hướng này phù hợp với dự kiến hiện tại:

- A: so sánh chất lượng trích năm facet và evidence giữa các extractor.
- B: trên một bộ facet tham chiếu cố định, so whole abstract, equal facet và weighted facet.
- Phép thử kết nối: khóa encoder/ranker/trọng số, thay đầu ra extractor để đo downstream.
- Conference: manuscript-based conference ranking, dùng hồ sơ các bài lịch sử trước cutoff.
- C/D/E cũ về profile, session direction và temporal adaptation: bỏ khỏi phạm vi nghiên cứu chính. Giữ code cùng tài liệu vận hành của chúng để tra cứu.

Không đổi tên conference thành C để tránh lẫn với C cũ. Không dùng profile, suy intent phiên hoặc thích ứng sở thích làm đóng góp chính khi đã bỏ các thực nghiệm kiểm chứng chúng.

## 2. Những điểm lệch giữa tài liệu mới và tài liệu cũ

| Vấn đề | Bằng chứng tại máy | Cách xử lý tài liệu |
|---|---|---|
| Hai định hướng đang cùng được trình bày như hiện hành | README gốc và EXPERIMENT_PLAN_FINAL vẫn mô tả A–E; bản PAPER_STRUCTURE mới tập trung A/B/conference | Lấy PAPER_STRUCTURE làm tài liệu định hướng chính; cập nhật chỉ mục và lưu kế hoạch A–E như lịch sử |
| Tài liệu cũ mô tả B–E chưa có dữ liệu | EXPERIMENT_PLAN_FINAL ghi chưa có generated/ground_truth; B hiện đã có manifest và generation report | Không dùng trạng thái ngày 10/10 làm tiến độ hiện tại |
| B không đạt quy mô cấu hình | data/exp_b/generated/manifest.json ghi 18 query, 1.800 labels; generation_report.json ghi shortfall 282 query và mục tiêu 300 query/30.000 cặp | Khi viết báo cáo phân biệt mục tiêu và số đã sinh; không viết đã có 300 query |
| Nhãn mock thiên về cách biểu diễn đang đánh giá | Manifest B dùng dataset_kind=mock và label_rule_version=weighted_overlap_v2 | Kết quả cũ phục vụ baseline/mô phỏng; thiết kế mới cần nhãn relevance độc lập để bảo vệ kết luận về lợi ích facet |
| Thiết kế trọng số khác nhau | B hiện được tài liệu hóa với fixed weights [.4,.2,.2,.1,.1]; đề cương mới đề xuất tìm trọng số trên train/dev rồi khóa | Ghi rõ baseline đang có và nghiên cứu dự kiến; không sửa mô tả code thành tính năng chưa triển khai |
| Hai ghi chú mới chưa thống nhất về conference weights | FOCUSED đề xuất tune riêng venue; PAPER_STRUCTURE mới hơn để mở lựa chọn transfer w_B hoặc venue-tuned shared w_V | Ưu tiên bản PAPER_STRUCTURE; chưa coi tune riêng venue là quyết định đã chốt |
| Điểm extraction không đồng nhất với human gold | Báo cáo so v1/v2 và pilot dùng AI reference; EVALUATE_QWEN nêu quy trình người review | Giữ loại reference, cohort, matcher và ngưỡng cùng mỗi điểm; không gọi các điểm này là human-gold F1 |

B vẫn cần facet đầu vào, nhưng không cần chờ A chọn extractor tốt nhất hoặc chờ điểm test A. Một bộ trọng số chung giữa extractor cũng không tự đồng nghĩa phải dùng chung trọng số giữa paper và conference.

## 3. Tài liệu trong docs: giữ, cập nhật, lưu lịch sử

Đường dẫn trong bảng tính từ thư mục docs/.

| Tài liệu | Đề xuất | Lý do |
|---|---|---|
| PAPER_STRUCTURE_SHARED_FACET_WEIGHTS_2026-10-23.md | GIỮ CHÍNH | Đề cương mới nhất, đúng A/B/conference và phép thử kết nối |
| EXTRACTOR_DOWNSTREAM_PRIOR_ART_2026-10-23.md | GIỮ | Prior art sát câu hỏi extractor ảnh hưởng downstream |
| FOCUSED_FACET_PAPER_VENUE_RESEARCH_2026-10-23.md | GIỮ THAM KHẢO | Có nền tảng retrieval/conference; phần quyết định thiết kế phải nhường bản PAPER_STRUCTURE |
| DATASET_B_SOURCES_2026-10-23.md | GIỮ, CẬP NHẬT | Nguồn B vẫn hữu ích; bỏ vai trò ranking D khỏi mô tả phạm vi chính; nguồn được khảo sát chưa tự thành dữ liệu đã nhập |
| ASPIRE_EXPERIMENT_NOTES.md | GIỮ | Đối chứng và cách đọc metric faceted retrieval |
| FABLE_EXPERIMENT_NOTES.md | GIỮ | Kết quả và điều kiện so sánh FaBle; không gộp điểm khác protocol |
| READING_LIST_VERIFIED_2026-10-23.md | GIỮ, LỌC ƯU TIÊN | Giữ thư mục nguồn; ưu tiên extraction/retrieval/venue, giảm phần profile/session/temporal |
| FACET_GUIDELINE.md | GIỮ | Định nghĩa năm facet, nền tảng A và downstream |
| ANNOTATION_PROMPT.md | GIỮ THEO PHIÊN BẢN | Prompt là thành phần thí nghiệm; đối chiếu snapshot từng run trước khi gọi là prompt đang dùng |
| EVALUATE_QWEN.md | GIỮ, CẬP NHẬT | Quy trình đánh giá; cần phản ánh nhiều extractor và phân biệt AI reference/human gold |
| IT_SCOPE.md | GIỮ | Phạm vi corpus, provenance và điều kiện lọc vẫn cần cho A/B |
| INGESTION_REPORT.md | GIỮ LÀ HỒ SƠ NGUỒN | Có số liệu nhập corpus và lỗi metadata; trạng thái chưa có facet là snapshot năm 2026 ngày 02–03/10, không phải tiến độ mới |
| PROJECT_OPERATIONS.md | GIỮ, CẬP NHẬT | Quy tắc provenance/handoff vẫn hữu ích; tách quy trình C/D/E khỏi hướng đang tiếp tục |
| RUN_EXPERIMENTS.md | GIỮ, CẬP NHẬT CHỈ MỤC | Giữ lệnh cũ để chạy code hiện có; đánh dấu C/D/E ngừng ưu tiên, conference chưa có quy trình chạy riêng trong tài liệu đã đọc |
| EXPERIMENT_PROTOCOL.md | GIỮ NHƯ PROTOCOL CODE HIỆN CÓ | Vẫn mô tả schema/evaluator A–E; không xóa khi code giữ nguyên. Cần protocol nghiên cứu A/B/conference riêng hoặc phần bổ sung phân biệt rõ |
| EXPERIMENT_PLAN_FINAL.md | LƯU LỊCH SỬ | Bản chốt 10/10 đã bị hướng 23/10 thay thế; tên FINAL dễ gây hiểu lầm |
| FACET_RECOMMENDATION_RESEARCH.md | LƯU LỊCH SỬ / TRÍCH NỘI DUNG CÒN DÙNG | Khảo sát theo hướng profile/intent/temporal cũ; đã có khảo sát tập trung mới hơn |
| ASPIRE_FABLE_GAP_AUDIT_2026-10-23.md | LƯU THAM KHẢO LỊCH SỬ | Khuyến nghị central claim cũ tập trung C2/session direction; giữ cảnh báo sai novelty, không dùng làm định hướng hiện tại |
| DATASET_C_SOURCES_2026-10-23.md | BỎ KHỎI BỘ ĐỌC CHÍNH, LƯU LỊCH SỬ | Phục vụ cá nhân hóa/profile C đã dự kiến bỏ |
| DATASET_D_SOURCES_2026-10-23.md | BỎ KHỎI BỘ ĐỌC CHÍNH, LƯU LỊCH SỬ | Phục vụ session logs D đã dự kiến bỏ |
| DATA_FIRST_REFERENCE.md | LƯU LỊCH SỬ | Đã tự ghi là tài liệu trước protocol 2.0; nghĩa C/D và workflow cũ |
| GENERATOR_TIMING.md | LƯU LỊCH SỬ | Đo 05/10, thứ tự C/D cũ; vẫn là bằng chứng timing theo cấu hình lúc đo |
| VALIDATION_STATUS.md | GIỮ LÀ NHẬT KÝ CŨ | Test 94 passed là lần kiểm tra cũ, không phải xác nhận trạng thái code hôm nay |
| EXPERIMENT_DATASETS_SPEC.md | CÓ THỂ BỎ SAU KHI SỬA LINK | Chỉ dẫn sang protocol/contract, gần như không có đặc tả độc lập; hiện không cần xóa ngay |
| EXPERIMENT_README_TEMPLATE.md | GIỮ TIỆN ÍCH, NGOÀI BỘ BÁO CÁO | Mẫu tổ chức README, không phải báo cáo nghiên cứu |
| superpowers/specs/2026-10-19-exp-a-v2-training.md | LƯU LỊCH SỬ | Thiết kế lần train v2 đã có báo cáo kết quả |
| superpowers/plans/2026-10-19-exp-a-v2-training.md | LƯU LỊCH SỬ | Nhật ký triển khai v2, không phải kế hoạch chạy lại |
| superpowers/plans/2026-10-22-base-v1-r1-r2.md | GIỮ ĐỂ ĐỐI CHIẾU ĐỢT A GẦN NHẤT | Ghi snapshot R1/R2, lỗi mount v1 và correction v2; RUNNING là trạng thái lịch sử, chưa xác minh cloud trong lần rà soát này |

## 4. Báo cáo trong scripts/exp_a/docs

Không bỏ đồng loạt báo cáo A khi tiếp tục A. Báo cáo kết quả vẫn là bằng chứng kể cả phương án đó không được chọn làm pipeline chính.

| Tài liệu hoặc nhóm | Đề xuất | Lý do |
|---|---|---|
| BASE_V1_V2_COMPARISON_2026-10-20.md | GIỮ ƯU TIÊN | So sánh 100 bài và giải thích khác biệt pipeline; v1/v2 dùng cùng Qwen3-8B revision, không phải hai base model độc lập |
| QLORA_V1_PROGRESS_2026-10-16.md | GIỮ KẾT QUẢ | Bằng chứng thực thi v1 |
| QLORA_V2_TRAINING_RESULT_2026-10-19.md | GIỮ KẾT QUẢ | Provenance training/checkpoint; câu chưa có F1 là snapshot lúc train, cần đọc cùng test report |
| QLORA_V2_TEST_RESULT_2026-10-20.md | GIỮ KẾT QUẢ | Paired test base/adapter v2 |
| MATCHER_REFERENCE_REPORT.md | GIỮ | Thay reference/matcher làm thay đổi điểm; cần để diễn giải các bảng cũ |
| SEMANTIC_REVIEW_PROTOCOL.md | GIỮ | Tiêu chí evidence, vai trò facet và độ đầy đủ |
| QLORA_V1_IMPROVEMENT_ROADMAP_2026-10-21.md | GIỮ GHI CHÚ A | Có cập nhật pilot50 ngày 22/10; cần đọc cùng execution plan, không lấy trạng thái chưa chạy làm trạng thái live |
| SMALL_8B_ERROR_RESEARCH_2026-10-21.md | GIỮ THAM KHẢO | Phân tích lỗi và hướng cải tiến A |
| research_evidence_8b_2026-10-21.md | GIỮ THAM KHẢO | Bằng chứng nguồn cho nghiên cứu 7–8B |
| LLM_SCIENTIFIC_FACET_EVALUATION_RESEARCH_2026-10-16.md | GIỮ THAM KHẢO | Thiết kế và giới hạn đánh giá extraction |
| KAGGLE_FACET_MATRIX_V2_EVALUATION_2026-10-16.md | GIỮ | Chứa 8b_original làm R0 pilot50 của đợt R1/R2; không bỏ như một pilot không còn liên quan |
| FOLDER_LAYOUT.md | GIỮ TIỆN ÍCH | Hướng dẫn bố trí A, không thuộc bản thảo nghiên cứu |
| KAGGLE_POLICY_MATRIX_V4_EVALUATION_2026-10-16.md | LƯU LỊCH SỬ KẾT QUẢ | Thử policy đã chạy; giữ để truy vết, không ưu tiên bộ đọc chính |
| KAGGLE_PILOT50_V3_7_EVALUATION_2026-10-16.md | LƯU LỊCH SỬ KẾT QUẢ | Kết quả pilot 4B, không trộn với R0 8B |
| KAGGLE_PILOT50_V3_7_COVERAGE_2026-10-16.md | LƯU LỊCH SỬ | Nhật ký chuẩn bị/push đã có evaluation report đầy đủ hơn |
| KAGGLE_PILOT.md | LƯU LỊCH SỬ SAU KHI ĐỔI LINK | Còn ghi kernel v8 RUNNING; README A đang trỏ vào nên không xóa trực tiếp |
| QLORA_V1_DESIGN_2026-10-16.md | LƯU LỊCH SỬ | Thiết kế lần train đã thực hiện; giữ cho provenance |
| QLORA_V2_PRETRAIN_COMPARISON_2026-10-18.md | LƯU LỊCH SỬ | Preflight trước training, không phải kết quả v2 cuối |
| QLORA_V2_DECODING_PROBE_RESULT_2026-10-19.md | LƯU LỊCH SỬ KẾT QUẢ | Probe draft với base/adapter v1, không phải test adapter v2 |
| SMALL_LM_EXTRACTION_RESEARCH_2026-10-16.md | LƯU THAM KHẢO CŨ | Nội dung gần nhóm nghiên cứu lỗi 8B mới hơn; giữ nguồn nếu được trích |
| archive/README.md và historical-2026-10-18.zip | GIỮ NGUYÊN | Đã có đợt lưu 20 tài liệu lịch sử kèm manifest; không cần giải nén hoặc xóa lại |

Đặc biệt giữ `data/exp_a/evaluation/base_v1_improvement_pilot50_20261022/` và `facet_matrix_v2/8b_original/`: tài liệu xác định đây là dữ liệu/R0 tái sử dụng của R1/R2. Prompt Markdown, policy, README adapter, review/adjudication, signatures, manifests, records và references trong data/ là thành phần tái lập thực nghiệm, không phân loại là báo cáo thừa chỉ dựa vào đuôi .md hoặc ngày cũ.

## 5. Các tài liệu ngoài repository đang nằm trong Thực hành

| Đường dẫn từ Thực hành/ | Đề xuất |
|---|---|
| output/bao_cao_exposure_interaction_D.md | Bỏ khỏi bộ báo cáo chính, lưu lịch sử: chỉ phục vụ D/exposure/interaction đã dự kiến dừng |
| output/venue_research_2026-10-23.md | Giữ: khảo sát riêng conference/venue; có chi tiết nguồn hữu ích cho nhánh tiếp tục |
| outputs/facet-literature-20261023/references.json | Giữ nguồn tham khảo; không xóa cùng báo cáo C/D/E theo tên thư mục |

Các file bài thực hành BTTH, tài liệu hành chính và tài liệu không liên quan đồ án nằm ngoài đợt dọn này.

## 6. Những file cần giữ vì code vẫn để nguyên

- README.md, DATA_CONTRACT.md; data/README.md; scripts/README.md; scripts/BASELINE_GUIDE.md.
- README của data/exp_a, exp_b và scripts/exp_a, exp_b.
- README của data/exp_c, exp_d, exp_e và scripts/exp_c, exp_d, exp_e: giữ cạnh code, có thể ghi ngừng ưu tiên ở chỉ mục sau này.
- Data raw/processed, giấy phép, schemas, config, corpus/facet snapshots, checkpoints, adapters, prediction/evaluation outputs và test fixtures.

Giữ một file mô tả code cũ không có nghĩa phải đưa thực nghiệm đó vào paper mới. Không thay schema/contract đang chạy chỉ để làm tài liệu trông khớp đề cương.

## 7. Bộ tài liệu nên đọc và dùng để viết báo cáo tiếp

1. PAPER_STRUCTURE_SHARED_FACET_WEIGHTS_2026-10-23.md: đề tài, RQs và bố cục paper.
2. FACET_GUIDELINE.md và prompt/snapshot thực tế từng run: định nghĩa và phương pháp A.
3. Các báo cáo kết quả A: BASE_V1_V2_COMPARISON, QLORA_V1_PROGRESS, QLORA_V2_TRAINING_RESULT, QLORA_V2_TEST_RESULT, MATCHER_REFERENCE_REPORT.
4. README dữ liệu B, README runner B, manifest/generation report thực tế: phân biệt baseline đã có với nghiên cứu dự kiến.
5. FOCUSED_FACET_PAPER_VENUE_RESEARCH, EXTRACTOR_DOWNSTREAM_PRIOR_ART, DATASET_B_SOURCES và khảo sát venue ngoài repository: related work và dữ liệu.
6. Protocol nghiên cứu mới còn cần chốt: danh sách extractor, F_ref, encoder, independent labels, shared weights, missing/failure policy, temporal conference catalog/split và metrics.

Đề xuất dọn: chuyển các mục LƯU LỊCH SỬ ra khỏi bộ đọc chính, giữ nguyên đường dẫn hoặc sửa đầy đủ liên kết khi di chuyển. README, PROJECT_OPERATIONS, VALIDATION_STATUS và README A hiện vẫn có link đến một số tài liệu này; xóa ngay sẽ để lại link hỏng. Chưa có bằng chứng một nhóm báo cáo lớn là bản sao hoàn toàn để xóa vĩnh viễn. Mục có thể loại bỏ rõ nhất là EXPERIMENT_DATASETS_SPEC.md, sau khi đảm bảo liên kết được thay bằng protocol/contract.

## 8. Giới hạn kiểm tra

Đã đọc đề cương mới nhất, các phần nội dung/đầu mục của tài liệu liên quan, kiểm tra chỉ mục/link tham chiếu và manifest/generation report B trên máy. Chưa kiểm toán mọi record dữ liệu, chưa xác minh lại nguồn học thuật trên web và chưa kiểm tra trạng thái cloud R1/R2. Không có thay đổi code hoặc lần chạy thí nghiệm nào trong đợt rà soát này.
