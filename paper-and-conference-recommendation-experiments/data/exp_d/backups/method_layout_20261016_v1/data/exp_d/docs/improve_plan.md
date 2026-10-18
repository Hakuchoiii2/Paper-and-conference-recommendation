> **Prompt dùng cho Deep Research:** Tôi đang nghiên cứu thực nghiệm D về khuyến nghị bài báo theo ý định từng phiên, dùng bài mốc và 5 facet problem/task/method/dataset/contribution, context được cho sẵn nhưng focus/hướng similar–different phải suy từ query và phản ứng trước cutoff, lịch sử C cung cấp importance dài hạn; baseline hiện dùng parser lexical, chênh lệch feedback matched pairs và tổng TF-IDF cosine có trọng số, canonical có 1.500 phiên/57 anchors/20 candidates mỗi phiên nhưng không có phản ứng D, pilot chọn 30 phiên/28 anchors và thêm observation tổng hợp có nhiễu với đối chứng cùng candidates/query/nhãn, đã đạt focus accuracy 100% ở noise 0,2 nhưng nDCG@10 giảm từ 0,8305 xuống 0,8284 và compliance@5 giữ 0,4533, nhãn relevance 0/1/2 dựa trên overlap concept và missing facets, vậy hãy tìm và phản biện các bài báo có DOI cùng mã nguồn hoặc phương án triển khai khả thi về intent-aware learning-to-rank, tách sở thích dài hạn với nhu cầu phiên, suy preference có độ bất định và faceted scientific-document similarity để ưu tiên xử lý việc suy đúng intent nhưng ranking chưa cải thiện, nêu cách áp dụng cụ thể, dữ liệu và tài nguyên cần có, ablation, chia dev/test theo anchor, nguy cơ leakage và lệch giữa similarity ngữ nghĩa với nhãn overlap, phân biệt chứng cứ trong bài gốc với giả thuyết áp dụng cho D và không cam kết thắng baseline khi chưa thực nghiệm.

# Kế hoạch tìm và áp dụng phương pháp cải thiện D

Ngày tra cứu: 16/10/2026. Đây là kế hoạch nghiên cứu, **chưa cài package, tải model, huấn luyện hoặc thay baseline**. DOI và thông tin phương pháp được đối chiếu từ trang nhà xuất bản, ACL Anthology, trang tác giả và repository chính thức. Đây là danh sách chọn theo vấn đề của D, không phải tổng quan đầy đủ mọi công trình mới nhất.

## 1. Kết luận lựa chọn

**Ưu tiên: kiểm tra ranker theo intent bằng một đối chứng quy tắc đơn giản, sau đó thử LambdaMART với đặc trưng theo facet; dùng RankNet tuyến tính làm đối chứng học ít tham số.** Chỉ thêm mô hình bất định hoặc encoder khi phép thử tách thành phần chỉ ra nhu cầu đó.

Không có bài báo nào bảo đảm phương pháp sẽ thắng trên D. Bằng chứng đã công bố nằm trên dataset/mục tiêu khác; những cách chuyển sang D dưới đây là đề xuất cần kiểm chứng. Có thể bảo đảm định nghĩa và tính tái lập của phép so, chưa thể bảo đảm mức tăng metrics.

| Ưu tiên | Phương án | Vì sao phù hợp với trạng thái D? | Điều kiện triển khai |
|---|---|---|---|
| 0 | Ranker quy tắc ưu tiên thỏa intent dự đoán | Kiểm tra xem direction đúng đã được dùng đúng trong ranking chưa | Không cần train hoặc model tải ngoài; đây là đối chứng tự thiết kế, không nhận là thuật toán của bài báo |
| 1 | LambdaMART + đặc trưng facet/intent | Học cách phối hợp context, hướng và missingness thay tổng trọng số cố định | Có nhãn train, split theo anchor; LightGBM trên CPU là lựa chọn triển khai |
| 1, đối chứng | RankNet tuyến tính hoặc MLP nhỏ | Kiểm tra liệu học trọng số/tương tác đơn giản đã đủ chưa | PyTorch hoặc tự tối ưu logistic pairwise; ít tham số trước |
| 2 | Preference xác suất lấy cảm hứng Bradley–Terry | Xử lý phản ứng có nhiễu và truyền bất định xuống ranker | Cần regularization và dữ liệu nhiều hơn pilot nếu muốn học tham số ổn định |
| 3 | SBERT theo facet; ASPIRE cho similarity khía cạnh bài khoa học | Thử hạn chế biểu diễn lexical, sau khi tách được vấn đề scorer | Download checkpoint khi triển khai; ASPIRE còn cần ánh xạ facet sang câu có ngữ cảnh |

## 2. Chẩn đoán từ code và kết quả hiện tại

Nguồn nội bộ: [review mức sẵn sàng](old/readiness_review_20261016.md), [README baseline D](../../../scripts/exp_d/README.md), [baseline_common.py](../../../scripts/baseline_common.py), [report pilot seed 42 noise 0,2](../results/baseline_20261016_v1_synthetic/seed_42_noise_0.2/results/report.md).

Baseline công khai có các đặc điểm:

- `direction_estimate` trả directions và confidence heuristic; query rõ có thể cập nhật hướng từ behavior.
- `intent_scores` sử dụng directions và importance từ C; confidence chưa tham gia tính ranking.
- Direction `unknown` vẫn dùng similarity khi ranking; các facet chưa có evidence vẫn có thể ảnh hưởng tổng điểm và gate thiếu facet.
- Score là trung bình có trọng số trên các facet được dùng; hướng different lấy `1 − cosine`. Đây là ưu tiên mềm, không bảo đảm đồng thời thỏa context và focus.
- Nhãn benchmark xét giao concept, trong khi score xét cosine TF-IDF; ngay cả hai thước đo lexical này cũng không đồng nhất hoàn toàn.

**Giả thuyết cần kiểm chứng, chưa phải nguyên nhân đã xác nhận:** importance dài hạn và các facet chưa có evidence có thể làm yếu ảnh hưởng của hướng phiên; missing-facet gate có thể gây nhiều điểm bằng nhau; độ lớn cosine chưa khớp yêu cầu nhãn; confidence chưa được tận dụng.

Pilot noise 0,2 có focus accuracy/coverage 100% nhưng ranking chưa tăng. Vì vậy chỉ thay estimator không trực tiếp giải quyết bằng chứng hiện tại. Canonical không có behavior; ambiguous/none không cung cấp tín hiệu hướng rõ thì không được kỳ vọng một parser mới tự tạo ra thông tin không tồn tại.

## 3. Các bài báo và cách chuyển sang D

### 3.1. LambdaMART — lựa chọn chính cho reranking

**Qiang Wu, Christopher J. C. Burges, Krysta M. Svore, Jianfeng Gao. “Adapting boosting for information retrieval measures.” Information Retrieval 13, 254–270, 2010; xuất bản online 2009.**

- DOI: [10.1007/s10791-009-9112-1](https://doi.org/10.1007/s10791-009-9112-1).
- Nguồn: [Springer](https://link.springer.com/article/10.1007/s10791-009-9112-1), [Microsoft Research](https://www.microsoft.com/en-us/research/publication/adapting-boosting-for-information-retrieval-measures/).
- Giải thích thêm: [From RankNet to LambdaRank to LambdaMART — Microsoft Research](https://www.microsoft.com/en-us/research/publication/from-ranknet-to-lambdarank-to-lambdamart-an-overview/); đây là technical report bổ sung, không gán DOI của bài Wu cho report này.

**Bài gốc đóng góp gì:** kết hợp boosted trees với ý tưởng LambdaRank để học ranking gắn với thước đo IR. Không phải công trình riêng về intent giống/khác theo facet.

**Đề xuất cho D:** mỗi session là một nhóm ranking gồm 20 candidates. Đặc trưng chỉ từ thông tin quan sát: overlap/cosine từng facet, cờ thiếu facet hai phía, context, directions dự đoán, confidence, số cặp hợp lệ, độ mạnh phản ứng, dấu hiệu query và importance C. Thêm tương tác giữa hướng dự đoán với similarity để ranker học rằng similarity cao có thể tốt hoặc xấu tùy nhu cầu phiên. Không dùng user/case/paper ID làm đặc trưng học thuộc.

Train bằng relevance 0/1/2 của **train split**; validation chọn cấu hình, test chỉ chấm. Nhãn train được dùng làm target supervised là hợp lệ; nhãn test và hidden focus/directions không được làm feature. Train bằng directions dự đoán, không thay bằng true intent rồi dùng predicted intent ở test.

**Khả thi:** [LightGBM LGBMRanker](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMRanker.html) và [tham số ranking chính thức](https://lightgbm.readthedocs.io/en/stable/Parameters.html) hỗ trợ `lambdarank`, group và `label_gain`. Chọn gain khớp evaluator gốc, không sửa gain để làm report đẹp hơn. Không cần GPU cho bước thử với dữ liệu nhỏ này; thời gian cụ thể cần đo khi triển khai.

**Rủi ro:** 1.500 phiên chỉ có 57 anchors; học cây có thể overfit nội dung hoặc quy tắc simulator. Pilot 30 phiên quá nhỏ để làm cả train, tune và test đáng tin cậy. Ranker cũng không khôi phục được intent khi input thiếu evidence. Mức tăng nDCG không tự bảo đảm tăng compliance.

### 3.2. RankNet — đối chứng học ranking gọn

**Christopher Burges và cộng sự. “Learning to rank using gradient descent.” ICML 2005.**

- DOI: [10.1145/1102351.1102363](https://doi.org/10.1145/1102351.1102363).
- Nguồn: [ACM qua DOI](https://doi.org/10.1145/1102351.1102363), [trang tác giả Microsoft Research](https://www.microsoft.com/en-us/research/publication/learning-to-rank-using-gradient-descent/), [PDF tác giả](https://www.microsoft.com/en-us/research/wp-content/uploads/2005/08/icml_ranking.pdf).

**Bài gốc:** học hàm điểm bằng loss xác suất trên các cặp có thứ tự ưu tiên.

**Đề xuất cho D:** dùng cùng features với LambdaMART, bắt đầu hàm điểm tuyến tính có regularization. Trong mỗi phiên train, tạo cặp có relevance khác nhau; bài grade cao cần có score cao hơn. Có thể dùng loss `log(1 + exp(−(s_i − s_j)))` khi `y_i > y_j`. Cặp 2–1 đặc biệt liên quan tới việc phân biệt đúng context nhưng sai hướng với đúng intent.

Triển khai bằng tensor và optimizer trong PyTorch; không cần pretrained encoder. Nếu thêm trọng số ưu tiên cặp 2–1, phải ghi là biến thể đề xuất, chọn trọng số trên validation và giữ evaluator chung. Khi dự đoán chỉ cần features, không cần labels. Pairwise training không tự tối ưu đúng compliance@5, nên vẫn phải đo cả compliance và nDCG.

**Vai trò trong kế hoạch:** nếu RankNet nhỏ đạt tương đương LambdaMART, chọn phương án gọn hơn; nếu cả hai không thắng đối chứng quy tắc, không mặc định tăng độ sâu mạng sẽ giải quyết được.

### 3.3. Bradley–Terry — cơ sở cho preference có xác suất

**Ralph Allan Bradley, Milton E. Terry. “Rank Analysis of Incomplete Block Designs: The Method of Paired Comparisons.” Biometrika 39(3–4), 324–345, 1952.**

- DOI nhà xuất bản: [10.1093/biomet/39.3-4.324](https://doi.org/10.1093/biomet/39.3-4.324).
- Nguồn: [Oxford Academic](https://academic.oup.com/biomet/article-abstract/39/3-4/324/326091).

**Bài gốc:** mô hình hóa xác suất một đối tượng được ưu tiên hơn đối tượng khác trong so sánh cặp.

**Đề xuất cho D, không phải thuật toán được bài gốc kiểm chứng trên D:** từ các matched pairs, suy phân bố hướng thay một ngưỡng delta duy nhất. Cần chuyển phản ứng thứ bậc thành bằng chứng so sánh, xử lý tie rõ ràng và dùng regularization; chỉ bốn cặp mỗi phiên không phù hợp để fit tham số tự do riêng từng phiên. Có thể học tham số dùng chung trên train hoặc dùng prior cố định được chọn trên validation.

Nếu ước lượng được `p_f = P(similar | evidence)`, thử term kỳ vọng `p_f*S_f + (1−p_f)*(1−S_f)` thay quyết định cứng. Đây là quy tắc kỳ vọng đề xuất cho D, không phải công thức ranking của bài Bradley–Terry. Giữ confidence heuristic hiện tại tách biệt với xác suất mới; không lấy confidence cũ thế trực tiếp cho `p_f`.

**Khả thi:** mô hình logistic nhỏ, tối ưu số thông thường, không cần LLM/GPU. Cần kiểm tra chất lượng xác suất bằng calibration/Brier trên phần phù hợp. Nếu học chỉ từ thắng/thua, sẽ mất độ mạnh phản ứng; ordinal model hoặc likelihood theo thresholds simulator là các đối chứng khác, không nên gọi chung là Bradley–Terry nguyên bản.

### 3.4. Sentence-BERT — encoder facet dễ thử hơn

**Nils Reimers, Iryna Gurevych. “Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.” EMNLP-IJCNLP 2019.**

- DOI: [10.18653/v1/D19-1410](https://doi.org/10.18653/v1/D19-1410).
- Nguồn: [ACL Anthology và PDF](https://aclanthology.org/D19-1410/).
- Công cụ: [Sentence Transformers chính thức](https://github.com/huggingface/sentence-transformers).

**Bài gốc:** học sentence embeddings có thể so bằng cosine, phục vụ similarity và các ứng dụng biểu diễn câu.

**Đề xuất cho D:** encode riêng concept text của mỗi facet, cache vector, thêm semantic cosine làm feature hoặc kết hợp với lexical overlap. Giữ encoder frozen trong thử nghiệm đầu để tách hiệu ứng biểu diễn khỏi training ranker. Giữ missing mask và điều kiện context của protocol; không xem vector của chuỗi rỗng là facet hợp lệ. Tên checkpoint, revision, cách pooling và chuẩn hóa phải được ghi khi triển khai; SBERT là phương pháp, không phải tên duy nhất của một checkpoint.

**Khả thi:** tải một checkpoint phù hợp tiếng Anh khi triển khai, chạy batch bằng `sentence-transformers`; CPU có thể dùng cho thử nhỏ, GPU thuận tiện khi encode nhiều bài. Không cần fine-tune ngay.

**Rủi ro lớn:** nhãn D dựa trên overlap concept, chưa phải semantic relevance người chấm. Hai concept gần nghĩa nhưng không giao vẫn có thể bị nhãn different. Vì thế embedding hiểu ngữ nghĩa hơn vẫn có thể giảm metrics hiện tại. Phải so lexical-only, semantic-only, hybrid; không thay nhãn để thiên vị encoder mới.

### 3.5. ASPIRE — hướng sát faceted scientific-paper similarity

**Sheshera Mysore, Arman Cohan, Tom Hope. “Multi-Vector Models with Textual Guidance for Fine-Grained Scientific Document Similarity.” NAACL 2022.**

- DOI: [10.18653/v1/2022.naacl-main.331](https://doi.org/10.18653/v1/2022.naacl-main.331).
- Nguồn: [ACL Anthology và PDF](https://aclanthology.org/2022.naacl-main.331/).
- Code/checkpoint: [repository tác giả allenai/aspire](https://github.com/allenai/aspire).

**Bài gốc:** biểu diễn nhiều vector ở mức câu có ngữ cảnh để so khía cạnh của tài liệu khoa học; có single-match và matching bằng optimal transport.

**Đề xuất cho D:** thử nhánh single-match trước, dùng các câu abstract/evidence liên quan đến facet rồi so các câu trong ngữ cảnh. Repo có checkpoint computer science và ví dụ inference. Cần kiểm tra A có đủ evidence/câu nguồn để ánh xạ năm facets của D; các aspect của ASPIRE không tự tương đương 1–1 với problem/task/method/dataset/contribution. Nếu chỉ encode các concept rời như SBERT thì phải mô tả là adaptation, không nhận là tái lập đầy đủ ASPIRE.

**Khả thi nhưng công sức cao hơn SBERT:** cần checkpoint, tokenizer, xử lý câu và code matching; chưa cần tái huấn luyện trên co-citation corpus. Bắt đầu frozen inference; ghi rõ model artifacts khi dùng.

**Giới hạn:** similarity facet tốt hơn không tự suy được hướng muốn khác, cũng không giải quyết việc importance hoặc score sử dụng sai intent. Thử ASPIRE sau ablation ranker, không chọn chỉ vì là mô hình cho bài báo khoa học.

## 4. Phương pháp thử đầu tiên: intent phải tác động rõ tới ranking

Đây là **đối chứng quy tắc tự thiết kế**, dùng để chẩn đoán benchmark; không gán DOI của các bài trên cho nó và không coi là đóng góp thuật toán mới mặc định.

### M0: ưu tiên mức thỏa intent suy được

1. Giữ nguyên estimator để nhận directions/confidence và evidence hợp lệ. Context lấy từ session như baseline.
2. Chỉ chọn focus dự đoán từ evidence ở các facet ngoài context, không đọc `focus_facet` thật. Trường hợp nhiều facet hoặc xung đột phải có quy tắc công khai và tie-break cố định; trường hợp thiếu evidence thì fallback baseline.
3. Khi có focus dự đoán, kiểm tra candidate có context overlap, có đủ facet cần dùng và thỏa hướng focus dự đoán bằng concept sets quan sát.
4. Xếp theo nhóm thỏa context + hướng trước, chỉ thỏa context sau, ngoài context/thiếu dữ liệu cần xét cuối; trong nhóm dùng score baseline để phá hòa.
5. Tách riêng biến thể dùng TF-IDF và chỉ reweight active facets để biết tác động đến từ hard priority, overlap hay bỏ gate ở facet chưa có evidence.

M0 có thể khớp trực tiếp quy tắc benchmark nếu focus/hướng suy đúng. Đây là lý do nó hữu ích để chẩn đoán, đồng thời là giới hạn nghiên cứu: tăng điểm trên nhãn overlap không chứng minh cải thiện semantic relevance thực tế.

**Bảo đảm có điều kiện:** chỉ trong phiên suy đúng focus và direction, nếu phân nhóm dùng đúng quy tắc relevance hiện hành và đủ dữ liệu quan sát thì đưa toàn bộ grade 2 trước grade 1/0 sẽ tối ưu compliance và thứ tự relevance của pool đó; không suy ra bảo đảm tăng trung bình trên mọi phiên, vì intent có thể sai/unknown và baseline có thể đã đạt trần.

### M1: học ranking, giữ estimator cố định

Chạy RankNet nhỏ và LambdaMART trên cùng feature set, input directions từ estimator cũ. Chưa thêm encoder để tách hiệu ứng học ranking. Mục tiêu là xem học tương tác theo intent có tốt hơn tổng TF-IDF với importance dài hạn không. Không hardcode weights thật context 0,6/focus 0,4 vào public method bằng cách đọc truth.

### M2 và M3: chỉ thêm khi có bằng chứng cần thiết

- M2 thay phần evidence/confidence bằng preference xác suất; so với M1 giữ nguyên ranker/features còn lại. Tập trung noise 0,5 và nhóm xung đột/thiếu evidence, không chỉ noise 0,2 đã bão hòa.
- M3 thêm semantic features bằng SBERT, sau đó cân nhắc ASPIRE; giữ nguyên estimator và loss. Không đổi đồng thời encoder, gate, estimator và weights rồi quy kết cải thiện cho một thành phần.

## 5. Thiết kế thực nghiệm trước khi cài đặt

### Chia dữ liệu và tránh dùng đáp án sai chỗ

Canonical có 57 anchors; pilot 30 phiên/28 anchors chỉ phù hợp chẩn đoán hiện tại. Trước khi tune cần ghi manifest chia train/validation/test theo nhóm anchor, mọi phiên cùng anchor vào cùng phần. Kiểm tra lại phân bố focus/direction/query mode sau chia; không ép một tỷ lệ chia cố định nếu làm nhóm test quá nhỏ. Nếu cross-validation, phải có phần chọn tham số bên trong và báo số anchor, không xem mọi phiên là mẫu độc lập.

Với behavior learning, nếu pilot không đủ mẫu thì cần thiết kế thêm overlay cho các phiên thuộc những phần anchor đã chốt và chạy lại toàn bộ baseline trên overlay đó. Đây là mở rộng benchmark riêng, không phải bắt buộc sinh lại A/C. Không chỉ đổi seed/noise rồi gọi là test độc lập. Nếu đòi hỏi generalization sang user hoặc candidate chưa thấy, phải thêm split/kiểm tra tương ứng; anchor split chưa bảo đảm các tiêu chí đó.

| Thông tin | Train | Khi dự đoán validation/test |
|---|---|---|
| Anchor, facets A, context, candidate pool, lịch sử C và D logs trước cutoff | Được dùng | Được dùng |
| Relevance labels | Chỉ làm target train | Chỉ evaluator chấm; validation dùng chọn cấu hình, không tạo feature |
| True focus/directions/weights | Không làm feature public; nếu làm target phụ phải khai báo rõ | Chỉ evaluator/oracle; public model tự dự đoán |
| Synthetic provenance có vai trò same/different và focus thật | Chỉ simulator/kiểm tra dữ liệu | Không truyền vào public estimator/ranker |
| Phản ứng trên chính candidates hoặc sau cutoff | Không bổ sung trái protocol | Không dùng |

Giữ baseline gốc làm đối chứng chưa train. Nhớ rằng phương pháp supervised mới có thêm nhãn train; báo rõ ngân sách supervision thay vì gọi là cùng chế độ zero-training. Nếu estimator cũng được train, tạo predictions out-of-fold cho train ranker để hạn chế lệch giữa intent train/test.

### Bảng ablation dự kiến

| Mã | Estimator | Ranker/biểu diễn | Câu hỏi |
|---|---|---|---|
| B | Baseline hiện có | TF-IDF + weights C | Mốc gốc cùng split và điều kiện |
| A0 | Giữ nguyên | Chỉ đổi weights theo evidence, vẫn TF-IDF | Importance phiên có giúp không? |
| A1 | Giữ nguyên | M0 ưu tiên intent dự đoán | Có phải score mềm chưa chuyển được intent thành thứ tự? |
| A2 | Giữ nguyên | RankNet hoặc LambdaMART, lexical features | Học ranking có vượt quy tắc và tổng trọng số không? |
| A3 | Preference xác suất | Ranker A2 cố định | Độ bất định có giúp khi phản ứng nhiễu không? |
| A4 | Estimator A2 | A2 + SBERT features | Semantic feature có thêm giá trị ngoài overlap không? |
| O | Intent thật, đánh dấu privileged | Ranker kiểm tra riêng | Chẩn đoán khi bỏ sai số suy intent; không làm kết quả public |

`O` là đối chứng chẩn đoán có đặc quyền. Nếu thay ranker hoặc policy, giữ thêm oracle gốc để tránh nhầm hai oracle là cùng phương pháp. Oracle mới cũng không mặc định là trần toán học.

### Chỉ số và tiêu chí quyết định

- Chốt trước chỉ số chính: nếu mục tiêu là đúng nhu cầu, chọn compliance@5; nDCG@10 là chỉ số ranking bổ sung và báo cả hai, không chỉ chọn chỉ số tăng.
- Báo focus accuracy/coverage/macro-F1 riêng, cùng kết quả theo focus, hướng, query mode và seed/noise.
- Với ranker-only, directions không đổi thì không tuyên bố direction F1 cải thiện.
- So paired trên cùng phiên; tính khoảng bất định theo nhóm anchor, chẳng hạn cluster bootstrap. Nhiều seed của cùng phiên không phải nhiều người dùng/nội dung độc lập.
- Báo trần pool: canonical hiện compliance@5 tối đa trung bình 0,60, @10 là 0,45; overlay mới hoặc test subset phải tính lại trần của chính nó.
- Đếm score ties, tỷ lệ score −1, các case đổi hướng nhưng ranking không đổi, và chất lượng nhóm missing facets. Đây là chẩn đoán, không mặc định gate hiện tại là bug.
- Chỉ giữ phương pháp nếu cải thiện có ý nghĩa thực tế và ổn định trên phần giữ lại; nếu chưa rõ do ít anchors thì báo chưa đủ bằng chứng. Không chọn ngưỡng hoặc phương pháp bằng test cuối.

## 6. Vị trí tích hợp dự kiến, chưa sửa code

| Thành phần | Nơi liên quan | Cách triển khai khi bắt đầu |
|---|---|---|
| Baseline gốc | `scripts/exp_d/run_exp_d.py`, `scripts/baseline_common.py` | Giữ nguyên để so; thêm entrypoint/module mới cho phương pháp đề xuất |
| Features và ranker | Module D mới, tên sẽ chốt khi triển khai | Nhận observable inputs, trả ranking/directions/weights theo contract; model artifact chứa config và train-split hash |
| Synthetic pilot | `data/exp_d/run_synthetic_observation_pilot.py` | Cần adapter chạy phương pháp mới ở cả hai điều kiện; runner hiện chỉ liệt kê baseline, chưa tự nhận model mới |
| Evaluator | `scripts/experiment_runner.py` | Giữ labels/metrics như cũ; không chuyển ground truth vào feature builder |
| Dataset/split | Manifest bổ sung riêng | Lưu case/anchor IDs, hashes và seed; không sửa dataset đã chạy để biến kết quả cũ thành kết quả phương pháp mới |
| Results | Tên run mới, thư mục riêng | Lưu model config, train/evaluation hashes, predictions, report và ablations; không ghi đè baseline |

Trước khi chạy toàn pipeline, chuẩn hóa đường dẫn test sang snapshot hiện tại như ghi trong [readiness review](old/readiness_review_20261016.md). Tài liệu này mới xác nhận có phương án triển khai và nguồn tham khảo; tương thích package/checkpoint với môi trường Windows cụ thể sẽ kiểm tra lúc cài đặt.

## 7. Đề xuất để trình bày với nhóm

> Em đề xuất kiểm tra và cải thiện phần ranking sử dụng intent trước, vì pilot đã suy đúng focus ở nhiễu thấp nhưng chưa tăng compliance; em sẽ làm đối chứng quy tắc để xác định giới hạn scorer, sau đó thử LambdaMART và RankNet nhỏ với features theo facet, chỉ mở rộng sang uncertainty hoặc semantic encoder khi ablation cho thấy cần thiết, và đánh giá trên phần dữ liệu tách theo anchor với cùng candidates, nhãn và điều kiện observation.

Nếu chỉ đọc hai bài đầu tiên: đọc **Wu et al. về LambdaMART** để xây ranker, rồi **Mysore et al. về ASPIRE** để hiểu similarity theo khía cạnh trong bài khoa học. Nếu cần code gọn để thử trước, dùng **RankNet tuyến tính**; chưa cần train transformer hay dùng LLM simulator.
