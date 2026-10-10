# Bản chốt thực nghiệm A–E và phần bổ sung

Đối chiếu ngày 2026-10-10 với code, configs, protocol 2.0 và tệp xuất hiện có. Đây là bản chốt đề xuất sau trao đổi, không xác nhận các model mới đã được tích hợp và không thay đổi contract đang chạy.

## Quyết định về phạm vi

- Giữ nguyên năm facet `problem`, `task`, `method`, `dataset`, `contribution` và corpus của nhóm. Không dùng CSFCube làm phương án đánh giá trong bản chốt này.
- Dùng tiếp facet và evidence đã trích. Không chạy lại toàn corpus chỉ để bổ sung evidence.
- Mục tiêu bàn giao hiện tại là baseline đúng và có giao diện để từng thành viên nghiên cứu tiếp; xem [hướng dẫn mở rộng scorer](../scripts/BASELINE_GUIDE.md). Semantic model/reranker không phải điều kiện bàn giao baseline.
- Hướng phát triển tiếp: một encoder pretrained cố định, cache biểu diễn toàn bài và từng facet, dùng chung cho B–E. Giữ các phương pháp lexical hiện có làm đối chứng.
- Ứng viên đầu tiên: [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B). Đây là lựa chọn để thử, chưa có số liệu trên corpus hoặc đo runtime/VRAM của dự án. Không cần huấn luyện năm encoder riêng.
- Chấm relevance B/D bằng người hoặc LLM, retrieval toàn corpus, reranker riêng, fine-tuning và adaptive decay là các bước mở rộng. Không coi chúng là điều kiện bắt buộc để chạy bộ mô phỏng hiện tại.
- Gold A đánh giá extraction là công việc khác với relevance B/D. Generator B–E không yêu cầu phải hoàn tất gold A trước.

## Trạng thái thực tế

| Hạng mục | Đã có | Chưa có hoặc chưa hoàn tất |
|---|---|---|
| Corpus | 4.210 paper IDs, title/abstract | Không kiểm tra lại chất lượng ngữ nghĩa của từng abstract trong lần đối chiếu này |
| A silver | Đủ 4.210 IDs riêng biệt ở parts 1–5, mỗi part 842; không thiếu/trùng/ngoài corpus | Chưa có manifest A gộp; đủ IDs chưa thay kiểm tra provenance/hash |
| Evidence A | Metadata kèm dẫn chứng đã có; lần kiểm tra trước xác nhận liên kết concept–evidence cho các bản xuất | Sự tồn tại của evidence không chứng minh phân facet đúng hoặc trích đủ ý |
| Cờ chất lượng A | 970 bản có `fallback_used` hoặc `validation_errors` | B–E hiện loại toàn bộ bản có cờ; chưa review hoặc thay đổi chính sách lọc |
| A gold | Có selector tạo form và evaluator | Chưa có review queue/gold trong thư mục ground_truth hiện tại; selector không tự tạo đáp án |
| B/C/D/E data | Có config, generator, validator, runner/evaluator | Chưa có dataset generated/ground_truth hay manifest cho B–E |
| Semantic model B–E | Đã xác định ứng viên và thiết kế so sánh | Chưa có bước build embedding cache và scorer semantic tích hợp vào runners |
| Kiểm chứng bổ sung | Có đề xuất | Chưa có generator chấm relevance B/D bằng LLM, dữ liệu người dùng thật hay reranker tích hợp |

Theo chính sách lọc hiện tại, 3.240 trong 4.210 bản xuất không có hai loại cờ trên. Đây là số bản vượt bộ lọc cờ, chưa phải số anchors/candidates đủ điều kiện cho mọi trường hợp. Một bản có cờ không đồng nghĩa mọi concept của bài đều sai.

Các con số này lấy từ JSONL đã xuất; không đọc tiến độ mới hơn còn nằm trong checkpoint đang chạy. Gộp A còn cần kiểm tra provenance/config/hash của các phần. B–E hiện yêu cầu A complete, không tự chấp nhận một part partial.

## Generator, runner và model làm ba việc khác nhau

Generator A gọi Qwen pretrained để trích annotation từ paper thật. Generator B–E không gọi Qwen để sinh paper/facet hay train recommender; chúng dùng facet A để tạo các trường hợp mô phỏng và đáp án kiểm tra. Dữ liệu quan sát được để riêng với hidden truth. Runner chuyển dữ liệu quan sát cho scorer, scorer tính ranking/profile/direction, evaluator mới đối chiếu hidden truth.

| Exp | Model pretrained đang có/đề xuất | Phần được tính hoặc cập nhật khi chạy | Có fine-tune trong phương án đầu không? |
|---|---|---|---|
| A | Qwen3-4B-Instruct-2507 đang được dùng | Concept/evidence từ prompt; retry là suy luận lại, không train | Không |
| B | Thêm Qwen3-Embedding-0.6B | Vector, cosine và tổng điểm facet | Không; train split hiện chưa cập nhật tham số |
| C | Dùng lại encoder B | Profile theo phản ứng/search, importance suy từ evidence | Không; thay đổi profile không phải thay trọng số encoder |
| D | Dùng lại encoder B; parser LLM là mở rộng khi dùng search tự nhiên | Hướng phiên từ tín hiệu quan sát, sau đó ranking theo hướng | Không; bộ suy hướng hiện tại là quy tắc |
| E | Dùng lại encoder B/C | Profile thay đổi theo prefix thời gian và static/recent/decay | Không; chưa cần model drift riêng |

Thêm một bước build embedding cache sau A: toàn title+abstract tạo vector whole; concept kèm evidence tạo vector cho từng facet có nội dung. Facet thiếu giữ trạng thái missing, không tự điền concept. B–E dùng lại cache; chưa cần tải/nạp một encoder riêng cho mỗi exp. Các query search quan sát được có thể được encode và cache riêng để xây profile semantic. Chốt checkpoint và cách tạo vector trước test.

B/C độc lập sau A. D dùng dữ liệu users/history của C nhưng không cần C predictions; E chỉ tái sử dụng danh tính C và sinh stream riêng. Các runners hiện xếp hạng candidates đã được generator chọn: B 100/case, C 20/user holdout, D 20/session, E 15/user/period; retrieval toàn corpus là một bước khác.

## A — Trích năm facet

**Ý nghĩa:** kiểm tra chất lượng đầu vào của cả hệ thống: Qwen có trích đúng, đủ và đặt concept vào đúng facet không?

**Đầu vào:** title/abstract của corpus; prompt/guideline; cấu hình Qwen3-4B-Instruct-2507. Đánh giá cần silver và gold độc lập trên cùng paper IDs, mặc định 400 bài.

**Đã có và generator:** `data/exp_a/build_exp_a.py` sinh silver/metadata; `merge_exp_a.py` gộp parts; `select_gold_review.py` tạo form pending; `scripts/exp_a/evaluate_exp_a.py` chấm gold đã review. Chưa có gold thật trong thư mục mặc định.

**Phần bổ sung chốt:** hoàn tất gộp và kiểm tra handoff A, dùng evidence hiện có. Để báo cáo chất lượng extraction theo evaluator hiện tại, hoàn tất gold A. Không bổ sung encoder/reranker cho A và không tự lấy silver làm gold.

**So sánh/output:** facet do Qwen trích với facet do người review trên cùng bài; nhãn khớp, dư, thiếu và khả năng nhầm facet. Đây là đánh giá extraction, không phải bảng thắng/thua giữa recommender và baseline. Đối chứng extraction khác chỉ thêm khi nghiên cứu cần so nhiều extractor.

**Điểm:** Precision/Recall/F1 từng facet, micro-F1, macro-F1; exact match có trong báo cáo. Evaluator hiện so concept sau chuẩn hóa Unicode/case/khoảng trắng, chưa chấm đồng nghĩa tự động. Điểm chọn attempt 0–100 của generator là điểm theo quy tắc bám nguồn, không phải accuracy/F1.

**Output hiện có của evaluator:** `summary.json`, `per_paper.jsonl`, `report.md`, `manifest.json` dưới `data/exp_a/evaluation/gold_400/` sau khi chạy.

## B — Biểu diễn toàn bài hay theo năm facet

**Ý nghĩa:** đo riêng việc chia nội dung thành năm facet và gán trọng số có giúp xếp hạng bài liên quan hơn không, trước khi thêm cá nhân hóa.

**Đầu vào:** A complete; bài mốc, các bài ứng viên và relevance giữ riêng cho evaluator. Config đặt mục tiêu 300 bài mốc × 100 candidates; chia theo bài mốc 70/15/15. Mặc định runner chấm test. B hiện không có lựa chọn target facet từ người dùng.

**Đã có và generator:** `data/exp_b/build_exp_b.py` sinh queries/candidate pools, splits, labels và provenance; chưa chạy sinh dataset. Labels hiện là tổng overlap năm facet có trọng số: bằng tập concept = 2, có giao = 1, không giao/thiếu = 0. Trọng số problem/task/method/dataset/contribution = 0,4/0,2/0,2/0,1/0,1.

**So sánh đã có:** `random`, `text_tfidf`, `equal_facets`, `weighted_facets`.

**Phần bổ sung chốt:** thêm ba biến thể semantic, dùng cùng encoder và cùng candidates/labels: toàn title+abstract; trung bình năm facet; tổng năm facet theo trọng số cố định. Giữ ba biến thể TF-IDF tương ứng để đối chiếu semantic với lexical. Text facet dùng concept kèm evidence hiện có; concept-only là ablation mở rộng, không phải thêm một mô hình extraction.

**Điểm xếp hạng đề xuất:** cosine giữa vector toàn bài, hoặc tổng có trọng số cosine giữa các facet tương ứng. Chính hàm này tạo ranking, không cần cross-encoder reranker mới có thể xếp hạng. Đầu vào/chuẩn hóa/missing-facet policy phải được chốt thống nhất trước test.

**Điểm đánh giá:** nDCG@5/10, Recall@5/10, Precision@5/10, MRR@5/10. Ưu tiên đọc nDCG@10; đây là lựa chọn trình bày đề xuất, runner vẫn xuất toàn bộ metrics.

**Diễn giải phép so:** weighted-semantic với equal-semantic đo trọng số; equal-semantic với whole-semantic đo chia facet; các cặp semantic/TF-IDF tương ứng đo encoder. Nhãn overlap hiện tại chỉ chứng minh mức khớp với bài toán mô phỏng.

**Mở rộng có thể để sau:** chấm relevance năm facet trên corpus nhóm bằng người/LLM; full-corpus candidate retrieval; reranker có/không. B hiện xếp hạng pool cho sẵn, chưa đo retrieval toàn corpus.

## C — Suy profile từ lịch sử đọc và search

**Ý nghĩa:** đo khả năng dùng hành vi để cá nhân hóa, và đóng góp riêng của search.

**Đầu vào:** A complete; user IDs, tương tác, search và exposure trước cutoff. Generator tạo latent preferences/importance trước hành vi, giữ chúng riêng để chấm. Mục tiêu 300 users × 50 phản ứng: 30 history + 20 holdout mỗi user. Đây là profile mô phỏng, không phải 300 người thật.

**Đã có và generator:** `data/exp_c/build_exp_c.py` sinh toàn bộ users, logs, cases và hidden truth; chưa có dataset xuất. C tạo danh tính dùng chung cho D/E.

**So sánh đã có:** `popularity`, `text_history` có search, `facet_no_search`, `facet_history` có search.

**Phần bổ sung chốt:** dùng encoder chung cho profile toàn văn có search và hai profile theo facet không/có search. Giữ concept có dấu thích/không thích để giải thích profile; vector semantic dùng để so với candidates. Không cần thêm model huấn luyện profile riêng trong phiên bản đầu.

**Điểm xếp hạng đề xuất:** tổng có trọng số mức phù hợp giữa profile từng facet và candidate. Importance suy từ evidence hành vi/search; chỉ dùng thông tin trước cutoff. Các phép có/không search dùng cùng encoder, candidates và cách tổng hợp.

**Điểm đánh giá:** ranking @5/10; `importance_mae` giữa importance dự đoán và latent importance, càng thấp càng tốt. Popularity/whole-text không xuất importance thì MAE là N/A. Nhãn relevance holdout từ phản ứng: like = 3, save = 2, click = 1, view/dislike = 0.

**Diễn giải phép so:** facet+search với facet không search đo lợi ích search; facet+search với whole-text+search đo biểu diễn facet khi cùng nguồn tín hiệu; so popularity đo cá nhân hóa. Ranking và importance MAE chưa chấm trực tiếp độ đúng của mọi concept preference trong profile.

**Mở rộng có thể để sau:** pilot người thật hoặc đối chiếu profile; không cần tạo bộ profile đã kiểm duyệt mới để chạy generator C/D.

## D — Suy ý định similar/different theo phiên

**Ý nghĩa:** phân biệt sở thích dài hạn với điều người dùng muốn ở phiên hiện tại. Ví dụ vẫn nghiên cứu cùng problem nhưng phiên này muốn method khác.

**Đầu vào:** A; users và C history/search/exposure; bài đang đọc; context facet quan sát được; phần đầu phiên trước cutoff. Focus/direction thật nằm trong hidden truth. Mỗi phiên hiện giữ một context facet similar và một focus facet similar/different; cả năm facet có thể làm focus, chưa có nhiều focus đồng thời.

**Đã có và generator:** `data/exp_d/build_exp_d.py` sinh phiên, query clear/ambiguous/none, matched observations, phản ứng và intent/relevance truth. Mục tiêu 300 users × 5 phiên × 20 candidates; có thể shortfall khi thiếu cặp hợp lệ. Chưa có dataset xuất. Không bắt buộc chạy runner C để có predictions trước D; D suy lại profile từ lịch sử C.

**So sánh đã có:** `fixed_similar` dùng trọng số đều; `profile_similar` dùng importance suy từ C; `direction_behavior` thêm hướng từ phản ứng; `direction_search` thêm search. `oracle_intent` do evaluator thêm riêng, biết true directions/importance và được đánh dấu dùng thông tin đặc quyền.

**Phần bổ sung chốt:** đưa cùng biểu diễn semantic vào các biến thể D, giữ cùng profile/candidates trong phép so các bộ suy direction. Không thay bộ suy direction hiện tại chỉ vì thêm embedding. Query parser ngữ nghĩa là bước mở rộng khi chuyển từ query mô phỏng theo mẫu sang câu tìm kiếm tự nhiên.

**Baseline D đã sửa theo protocol:** `intent_scores` chỉ dùng `1-similarity` khi direction là `different`; `unknown` dùng similarity mặc định và vẫn giữ nhãn unknown để chấm F1/coverage. Relevance gate dùng đúng `context_facet`. Regression tests kiểm tra điểm cụ thể, facet thiếu và cả năm lựa chọn context, thay fixture một ký tự từng làm test pass dù chưa kiểm tra được scorer.

**Điểm xếp hạng theo thiết kế:** ưu tiên similarity cho facet muốn similar và khác biệt cho facet muốn different, đồng thời giữ ngữ cảnh liên quan. Không thưởng different khi facet candidate thiếu dữ liệu. Các quy tắc fallback/context cần được kiểm tra lại khi tích hợp semantic scorer.

**Điểm đánh giá:** direction macro-F1, accuracy, coverage trên active facets; ranking @5/10; intent compliance@5/10. Grade 2 = liên quan và đúng hướng; grade 1 = liên quan nhưng sai hướng; grade 0 = ngoài ngữ cảnh. Coverage cho biết bao nhiêu hướng được dự đoán thay vì unknown; unknown không được đổi thành dự đoán đúng khi chấm.

**Diễn giải phép so:** profile-similar với fixed-similar đo cá nhân hóa; direction-behavior với profile-similar đo suy hướng từ hành vi; direction-search với direction-behavior đo search; oracle chỉ là mốc biết sẵn ý định, không bảo đảm trần toán học hoặc phép so cùng thông tin.

**Mở rộng có thể để sau:** chấm relevance theo intent bằng người/LLM trên corpus năm facet, search tự nhiên, reranker hiểu intent. Gold intent dùng khi tạo/chấm nhãn phải tách khỏi input của các phương pháp thông thường.

## E — Theo kịp thay đổi sở thích

**Ý nghĩa:** đo liệu cách giảm ảnh hưởng lịch sử cũ có giúp khi sở thích đổi, đồng thời tránh làm giảm chất lượng ở người có sở thích ổn định.

**Đầu vào:** A và danh tính C; E sinh stream riêng, không lấy nguyên profile/history C làm stream E. Mục tiêu 300 users × 4 periods × 15 phản ứng = 18.000 phản ứng; 150 stable/150 drift; 1.200 hidden profiles và 900 cases đánh giá đầu periods 2/3/4.

**Đã có và generator:** `data/exp_e/build_exp_e.py` sinh temporal profiles, interactions/search/exposure, metadata stable/drift và rolling cases; chưa có dataset xuất.

**So sánh đã có:** `popularity`, `static`, `recent`, `decay`.

**Phần bổ sung chốt:** dùng cùng semantic profile/ranker đã chốt cho mọi chính sách thời gian. Không thêm model mới riêng cho E. Static dùng mọi lịch sử trước mốc với trọng số thời gian bằng nhau; recent dùng period liền trước; decay giảm theo tuổi sự kiện, half-life mặc định 30 ngày. Static không có nghĩa đóng băng profile từ period 1.

**Điểm xếp hạng đề xuất:** giống C, chỉ thay trọng số thời gian của phản ứng/search. Giữ encoder, feedback weights, candidates và cách xếp hạng cố định giữa các biến thể.

**Điểm đánh giá:** ranking @5/10 và importance MAE theo từng mốc, overall, stable/drift và từng nhóm theo period. Nhãn holdout từ phản ứng như C. Chỉ đưa log trước cutoff cho scorer; phản ứng period hiện tại chấm mốc hiện tại và chỉ được dùng làm lịch sử ở mốc sau.

**Diễn giải phép so:** recent/decay với static đo lợi ích quên lịch sử cũ; decay với recent đo giảm dần so với cửa sổ cứng. Đọc cả drift và stable, không chỉ trung bình toàn bộ.

**Mở rộng có thể để sau:** adaptive decay theo user, stream từ người thật. Không cần huấn luyện model drift riêng để chạy so sánh đầu tiên.

## Cách đọc điểm và output chung

| Điểm | Ý nghĩa | Hướng tốt |
|---|---|---|
| nDCG@k | Các bài có grade cao có được đưa lên đầu không? | Cao |
| Recall@k | Top-k lấy được bao nhiêu bài positive trong pool đã chấm? | Cao |
| Precision@k | Tỷ lệ bài positive ở top-k | Cao |
| MRR@k | Bài positive đầu tiên xuất hiện sớm đến đâu? | Cao |
| Extraction F1 | Cân bằng concept trích đúng và concept còn thiếu | Cao |
| Importance MAE | Sai số trung bình của năm trọng số quan tâm | Thấp |
| Direction macro-F1 | Chất lượng dự đoán similar/different, tính cả dự đoán bỏ lỡ | Cao |
| Direction coverage | Tỷ lệ active facets có dự đoán thay vì unknown | Đọc cùng F1; cao riêng lẻ chưa đủ |
| Intent compliance@k | Tỷ lệ top-k vừa liên quan vừa thỏa hướng của phiên | Cao |

nDCG hiện dùng gain `2^grade - 1`. Recall/Precision/MRR coi grade > 0 là positive; ở D, grade 1 vẫn positive dù sai hướng, nên cần đọc compliance riêng. Case không có positive có nDCG/Recall/MRR N/A và denominator được báo. Recall trên pool chưa phải recall toàn corpus.

Score cosine/tổng có trọng số là điểm thuật toán dùng để sắp xếp. F1/nDCG/MAE/compliance là điểm evaluator dùng để so phương pháp; không đồng nhất hai loại điểm này.

B–E hiện xuất `predictions.jsonl`, `details.jsonl`, `report.json`, `summary.csv`, `report.md`, `manifest.json`. B mặc định ở `results/exp_b/test/`; C/D/E ở `results/exp_*/holdout/`. Những tệp này là output sau khi chạy, không phải kết quả đã có trên corpus hiện tại. Scorer semantic cần nối vào cùng evaluator để có phép so thống nhất.

## Thứ tự thực hiện

1. Hoàn tất handoff A: IDs hiện đã đủ; đối chiếu provenance/hash, gộp, giữ rõ cờ chất lượng và tập bị loại. Không chạy lại toàn bộ để lấy evidence.
2. Sinh B và C; sau C users/handoff sinh D/E. Các generator này đã có và chỉ sinh mock.
3. Chạy bộ lexical hiện có để có kết quả tham chiếu. Gold A thực hiện song song nếu muốn báo cáo extraction F1; B–E không chờ gold này.
4. Khi phát triển phương pháp mới, bổ sung build embedding cache và semantic scorers; chốt thiết lập trên dev hoặc trước test. So whole/equal/weighted B, search/profile C, direction D, time policies E với cùng các điều kiện còn lại. Baseline D đã có sửa lỗi fallback/context; các thành viên dùng giao diện scorer chung và giữ baseline làm đối chứng.
5. Khi cần bằng chứng gần ngữ nghĩa/người dùng thật hơn, thêm chấm relevance B/D hoặc pilot. LLM judgments vẫn là nhãn tự động, không tự trở thành human gold.

Không cam kết phương pháp đề xuất phải thắng. Điểm trên mock phản ánh giả định simulator và quy tắc sinh nhãn; chưa đủ để kết luận người dùng thật thích kết quả hoặc chứng minh tính mới. A–E hiện chưa đánh giá khuyến nghị conference/venue.

## Nguồn và giới hạn kiểm tra

Đối chiếu [protocol hiện tại](EXPERIMENT_PROTOCOL.md), [README scripts](../scripts/README.md), configs B–E, nguồn generator/scorer/evaluator qua CodeGraph, counts/IDs/cờ trong parts A và sự tồn tại của generated/ground_truth. Chưa chạy extraction mới, gộp, sinh B–E, tải/chạy embedding/reranker, đo hiệu năng hoặc đánh giá relevance mới trong lần chốt này. Chỉ thay đổi tài liệu; code/config/data giữ nguyên.
