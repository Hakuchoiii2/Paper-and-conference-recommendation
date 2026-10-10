# Giao thức thực nghiệm A–E — phiên bản 2.0, 2026-10-09

Thứ tự mới: **A trích facet → B truy xuất → C suy profile → D suy direction theo phiên → E thích ứng thời gian**.
C mới thay D cũ; D mới thay C cũ. B độc lập với C sau A; D/E dùng danh tính C.
D sử dụng lại lịch sử C và cùng hàm suy profile; không bắt buộc chạy runner C để có tệp prediction trước D.

Khuyến nghị sử dụng bài đang đọc, lịch sử và searching đã xảy ra. Các truy vấn là hành vi tìm kiếm
quan sát được trong quá trình sử dụng. Phiên không có search vẫn được đánh giá.
B là phép kiểm tra biểu diễn có trọng số cố định; trọng số không phải một form yêu cầu người dùng.

| Exp | Câu hỏi | So sánh | Chỉ số | Contribution |
|---|---|---|---|---|
| A | Trích đúng năm facet không? | Silver với human gold độc lập | P/R/F1 từng facet, micro/macro | C1 |
| B | Tách và gán trọng số facet giúp truy xuất không? | Random, whole-text TF-IDF, equal-facets, fixed-weight facets | nDCG/Recall/Precision/MRR @5/10 | C1, phần xếp hạng C2 |
| C | Lịch sử đọc/search giúp suy profile và mức quan tâm không? | Popularity, text-history có search, facet không search, facet có search | Ranking; MAE trọng số facet với latent importance | C3 |
| D | Suy similar/different rồi sử dụng nó có cải thiện khuyến nghị không? | Fixed-similar; profile-similar; direction từ phản ứng; direction thêm search; oracle riêng | Macro-F1 direction, coverage, accuracy, ranking, intent compliance | C2 + C3 |
| E | Có theo kịp thay đổi sở thích không? | Popularity; static; recent; decay | Ranking, importance MAE theo period và stable/drift | C3 temporal |

Các exp đo hiệu quả thành phần, không tự chứng minh tính mới so với nghiên cứu trước.
A–E chưa đánh giá contribution C4 về conference/venue.

## Dữ liệu và ranh giới quan sát

Corpus và năm facet A dùng nguyên paper IDs. A cần manifest complete; bài fallback/quality flag bị loại.
B–E luôn ghi dataset_kind=mock. Generator sinh profile/intent trước, rồi sinh hành vi, không suy truth ngược từ log.

Contract corpus/A giữ phiên bản riêng hiện có; manifest B–E và evaluation dùng **2.0**.
Dữ liệu cũ 1.0 được từ chối: chọn output_dir/truth_dir mới nếu cần giữ cùng dự án.
Generator không ghi đè thư mục có tệp lạ. Không chạy hai generator cùng output.

| Record | Trường |
|---|---|
| Search | query_id, user_id, session_id, text, parent_query_id, timestamp |
| Exposure | exposure_id, user_id, session_id, query_id (nullable), paper_ids theo thứ tự hiển thị, timestamp |
| Interaction | user_id, paper_id, interaction_type, timestamp, session_id, exposure_id |
| Case C | case_id, user_id, candidate_ids, cutoff |
| Session D | case_id, user_id, query_paper_id, context_facet, candidate_ids, cutoff |
| Case E | case_id, user_id, period, candidate_ids, cutoff |
| Hidden profile C/E | user_id, latent_preferences, facet_importance; E thêm period/start/end |
| Hidden intent D | case_id, focus_facet, directions, facet_importance, query_mode |

Search trước exposure, exposure trước phản ứng. parent_query_id phải cùng user/session và có thời gian sớm hơn.
Exposure lưu thứ tự, không đảm bảo người thật chú ý mọi kết quả; trong mock đây là giả định được kiểm soát.
Bài chưa quan sát không được coi là dislike. View=0 và không click chỉ là bằng chứng yếu.

Runner lọc **history, query và exposure** theo timestamp < cutoff trước mỗi lần gọi scorer.
C: 30 events đầu là lịch sử, 20 events sau tạo judged candidate pool.
D: dùng C history cộng phần đầu phiên; bài của cặp quan sát không xuất hiện trong candidate pool cuối phiên.
E: đánh giá đầu periods 2/3/4; chỉ các periods trước mốc được đưa cho scorer.

E lưu phản ứng periods 2/3 cả trong history dùng cho mốc sau và truth dùng cho mốc hiện tại.
Các bản sao phải giống nhau. Đây là đánh giá rolling, không dùng toàn bộ interactions_train làm input cho mọi mốc.
Candidate IDs được chọn trước phản ứng từ simulator; điểm/nhãn tương lai chỉ evaluator đọc.

## B — Biểu diễn có trọng số

300 anchors × 100 candidates. Query không còn target_facet.
Trọng số cố định trong config: problem .4, task .2, method .2, dataset .1, contribution .1.
Nhãn = tổng có trọng số của grade concept-overlap: 2 nếu bằng tập concept, 1 nếu có giao, 0 nếu không giao/thiếu.
positive_grade=.6 chỉ dùng tạo pool high/low relevance; evaluator dùng nguyên grade liên tục.
Sampling mục tiêu 20% high relevance và 50% low-relevance hard negatives nếu pool cho phép.
Chia nhóm anchor 70/15/15; cùng anchor không qua hai split.
Whole-text và facet dùng cùng bộ TF-IDF/IDF, fit đồng thời trên tài liệu chưa gán nhãn.

Đây là nhãn quy tắc, không phải expert judgments độc lập. Muốn kết luận hiệu quả trên ngữ nghĩa thật cần bộ judged riêng.

## C — Profile có searching

300 users × 50 phản ứng; 9.000 history + 6.000 holdout.
Sinh concept preferences [-1,1] và importance không âm, tổng bằng 1, trước mọi phản ứng.
Utility là tổng theo importance của preference trung bình trên concept của mỗi facet; cộng noise trước khi chuyển thành feedback.
Exposure phối hợp pool chung và pool có concept profile; query chọn facet theo latent importance rồi lấy concept ưa thích.
Search_fraction=.6 là xác suất sinh query, không phải tỷ lệ bắt buộc đạt.
Mỗi exposure C/E chứa bốn bài; chỉ phản ứng đã ghi mới được dùng xây profile.

Facet model cộng click=1/save=2/like=3/dislike=-1/view=0 trên concept của bài, và query evidence trọng số 1.
Trong query, concept bị phủ định nhận dấu âm. Importance ước lượng từ độ lớn evidence từng facet rồi chuẩn hóa.
Đây là estimator đơn giản cần kiểm thử; không khẳng định phân biệt hoàn toàn importance khỏi concept preference.
Text-history cũng nhận query để phép so sánh biểu diễn có cùng nguồn tín hiệu.
Popularity/text-history không trả facet importance, nên MAE của chúng là N/A.

## D — Similar/different theo phiên

300 users C × 5 sessions × 20 candidates, mục tiêu 1.500 cases/30.000 labels.
Mỗi phiên có một context facet giữ similar để xác định ngữ cảnh liên quan, và một focus facet similar hoặc different.
Context được chọn từ facets có evidence của bài mốc trước khi chọn direction, như một điều kiện truy xuất được kiểm soát.
context_facet quan sát được; focus/direction/importance/query_mode thật nằm trong ground_truth.
Cả năm facets đều có thể làm focus; các tổ hợp nhiều focus đồng thời chưa thuộc bộ phiên đầu tiên này.
Không đánh giá khả năng tự chọn context_facet trong D.

Có ba nhóm query: clear (query + reformulation có nội dung hướng), ambiguous (chỉ context), none.
Dùng nguyên văn query, không cung cấp nhãn directions cho scorer.
Mỗi phiên có tối đa bốn cặp bài same/different ở focus, cùng overlap/missing states trên các facet còn lại.
Thiếu cặp hợp lệ thì giữ số cặp thực tế; estimator có thể abstain. Không tạo bài/facet để bù.
Thứ tự hai bài được xáo ngẫu nhiên; chưa mô phỏng position-dependent attention.
Candidate pool khác phần quan sát; mục tiêu 50% thỏa intent, hard negatives liên quan nhưng sai focus direction.

Estimator phản ứng so chênh lệch mean feedback giữa nhóm khác/giống, với smoothing +2 ở mẫu số.
Cần ít nhất hai cặp và |delta| >= .25 (config cố định trước test).
Query rõ như "method: alternatives to GNN" hoặc "method: more papers using GNN" bổ sung hướng.
Các query được xử lý theo thời gian; query rõ mới nhất có thể cập nhật hướng cũ.
Tên một concept khác đơn thuần chưa được coi là bằng chứng chắc chắn muốn different.

Trọng số lấy từ cùng C profile cho profile-similar/direction-behavior/direction-search.
Unknown giữ ranking similar theo ngữ cảnh mặc định, nhưng prediction vẫn là unknown khi chấm F1/coverage.
Các phương pháp dùng cùng chính sách facet thiếu và cùng relevance gate theo context.
Với facet có dữ liệu, g(S)=S khi similar, g(S)=1-S khi different; tổng có trọng số chuẩn hóa.
Facet thiếu phía bài mốc bị bỏ qua; thiếu phía candidate trên facet hoạt động không được thưởng different.
Score là ưu tiên mềm, không bảo đảm mọi điều kiện AND; evaluator đo compliance riêng.

Oracle_intent được thêm **bên trong evaluator**, dùng true direction/importance và cùng scorer.
Đây là đối chứng đặc quyền, không phải phương pháp có cùng thông tin và không phải bảo đảm trần toán học.
Direction macro-F1 được tính từ confusion pooled trên active facets, cho hai lớp similar/different.
Unknown gây false negative; true ignore không được đổi thành unknown hay dùng làm nhãn dự đoán chính xác.
Coverage = tỷ lệ active facets có dự đoán similar/different.
Ranking grade 2: liên quan và thỏa hướng; grade 1: liên quan nhưng sai hướng; grade 0: ngoài ngữ cảnh.
Intent compliance@k = tỷ lệ grade 2 ở top-k.

Query parser là tham chiếu lexical cho mock: facet-prefixed query, concept có trong A,
các mẫu "alternatives to"/"more papers using" và phủ định. Cần parser ngữ nghĩa trước khi áp dụng search log tự nhiên.

## E — Temporal

Dùng lại danh tính C, stream E riêng; 4 periods × 15 events/user = 18.000 phản ứng.
150 stable/150 drift; concepts và importance nội suy với hệ số [0,.5,1,1].
18.000 là số phản ứng độc lập, không cộng các bản sao rolling.
Có 1.200 hidden profiles và 900 rolling cases (300 users × 3 mốc).
History file chứa periods 1–3; truth file chứa periods 2–4 để chấm từng mốc.
Static/recent/decay có cùng facets, queries, feedback weights và ranker.
Recent chỉ dùng period trước mốc; decay dùng half-life 30 ngày, cố định trước test.
Report có overall, stable/drift, period_2/3/4 và stable/drift từng period.

## Kết quả và kiểm tra

Mỗi runner xuất predictions.jsonl, details.jsonl, report.json, summary.csv, report.md, manifest.json.
MAE importance chỉ dành cho mô hình có output importance. nDCG dùng gain 2^grade-1;
Recall/Precision/MRR coi grade > 0 là positive. Case không có positive có nDCG/Recall/MRR=N/A và denominator riêng.
Không tuning trên test, không cam kết đề xuất phải thắng baseline.
Scorers CPU dùng stdlib, không tải model. Semantic encoders và đánh giá với người thật là bước khác.

Xem [lệnh chạy](RUN_EXPERIMENTS.md), [contract](../DATA_CONTRACT.md) và [trạng thái kiểm tra](VALIDATION_STATUS.md).
