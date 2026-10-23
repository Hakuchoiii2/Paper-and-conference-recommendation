# Thực nghiệm D — bản giải thích bổ sung

**Bản improve · 22/10/2026.** Sao chép từ bản báo cáo ngắn; bổ sung những chỗ cần hiểu rõ. Bản gốc được giữ nguyên.

**Một benchmark · tám phương pháp · một bảng chính và các bảng phụ giải thích kết quả.** Oracle là mốc dùng đáp án ẩn. Bảng phụ lấy từ cùng lượt chạy, không phải các thực nghiệm mới. Mỗi bảng có ghi mục đích và cách đọc.

## 1. D kiểm tra điều gì?

- **Query/phản ứng có giúp suy nhu cầu giống–khác không?**
- **Nhu cầu suy được có giúp xếp bài phù hợp lên trên không?**

Ví dụ: đang đọc bài về **gợi ý bài báo khi thiếu lịch sử người dùng**. Context là task “gợi ý bài báo”; focus là problem. Muốn **giống problem** thì ưu tiên bài cũng xử lý thiếu lịch sử; muốn **khác problem** thì ưu tiên bài xử lý problem khác nhưng vẫn cùng task.

## 2. Dữ liệu và hình tổng quát

![Hình 1. Bài toán D: tín hiệu công khai, ranking và đáp án riêng](figures/d_bai_toan.png)

**Luồng tổng quát:** từ bài báo thật và facets A, ta dựng các phiên mô phỏng, mỗi phiên có observation riêng và một pool candidates. Hệ thống nhìn query/phản ứng trên observation trước cutoff để suy người dùng muốn giống hay khác ở khía cạnh nào. Cùng dự đoán ấy được **chấm trực tiếp xem suy hướng đúng không**, đồng thời **đưa vào ranking để xếp candidates**. Evaluator đối chiếu với intent/nhãn đã giấu và xuất bảng kết quả. Vì vậy khối suy directions có hai đường ra: một đường chấm hướng, một đường sử dụng hướng để xếp bài.

- **Candidates:** những bài cần xếp hạng. Ưu tiên bài thật, tổng hợp phía còn thiếu.
- **Observation:** các cặp riêng để tạo phản ứng trước cutoff; tách khỏi candidates đánh giá.
- **Hidden intent/labels:** simulator đặt nhu cầu và nhãn trước; chỉ evaluator/Oracle được dùng làm đáp án.

Bộ `datasets/observation_v1` có **19 thiết kế trên 12 bài mốc**. Mỗi thiết kế tạo 2 hướng × 3 chế độ query → **114 phiên**; lặp với 3 seeds × 2 mức nhiễu phản ứng.

**15 thiết kế** dùng pool 20 candidates thật; **4 thiết kế** dùng 19 thật + 1 tổng hợp. “4” là số thiết kế, không phải cả nhóm chỉ có bốn bài. Observation/query/phản ứng vẫn là mô phỏng ở cả hai nhóm.

Mỗi pool có một candidate đúng context và đúng hướng (**grade 2**), một candidate đúng context nhưng sai hướng (**grade 1**) và 18 bài ngoài context (**grade 0**). Hai nhu cầu đối lập giữ cùng pool.

### 2.1. Corpus, candidates, observation và cutoff khác nhau thế nào?

- **Corpus gốc = kho nguyên liệu:** 4.210 bản ghi bài báo thật của dự án. Không phải cả kho được đưa vào một lượt ranking. Facets silver A là khía cạnh trích tự động, chưa phải nhãn chuyên gia.
- **Candidate pool = đề cần xếp hạng:** mỗi phiên có 20 bản ghi thật/bổ sung tổng hợp. Hệ thống phải sắp thứ tự chúng, không được nhận nhãn grade 0/1/2 trước khi dự đoán.
- **Observation = bằng chứng để suy nhu cầu trước khi làm đề:** bốn cặp, tức tám bản ghi facet tổng hợp riêng trong mỗi phiên. Hai phía cùng context, đối lập tại focus đang kiểm tra; các facet nền giữ tương ứng. Phản ứng trên những cặp này giúp estimator suy hướng.
- **Exposure = nhật ký hiển thị:** ghi cặp observation nào được đưa ra, cho ai, trong phiên nào và lúc nào. Reaction ghi view/click/save/like/dislike sau đó. Observation là nội dung; exposure/reaction là sự kiện trên nội dung đó.
- **Cutoff = thời điểm chốt thông tin được phép nhìn:** chỉ query/exposure/reaction đúng user, đúng phiên, có timestamp **nhỏ hơn cutoff** mới được dùng. Đây là ranh giới quan sát, không phải cách chia train/dev/test.

**Ví dụ thời gian:** 09:59 query → 09:59:30 hiển thị observation → 09:59:31 phản ứng → **10:00 cutoff** → suy hướng và xếp candidates. Sự kiện đúng 10:00 hoặc muộn hơn bị loại.

**Quan hệ:** corpus cung cấp nguyên liệu; observation cung cấp bằng chứng; candidates là bài cần xếp. Observation không nằm trong pool đánh giá. Estimator không nhận danh sách pool hay phản ứng trên chính candidates để suy hướng; ranking nhận candidates để tính điểm.

### 2.2. “C weights được khóa chung” nghĩa là gì?

**C weights là năm trọng số quan tâm dài hạn của từng user.** Hàm profile gốc tổng hợp bằng chứng concept từ phản ứng/query lịch sử C trước cutoff, rồi chuẩn hóa thành năm trọng số có tổng bằng 1. Lịch sử C hiện cũng là mô phỏng.

Ví dụ minh họa một user có `(problem=.40, task=.30, method=.10, dataset=.10, contribution=.10)`:

- Tính profile từ prefix lịch sử C rồi dùng nguyên bộ số ấy cho user đó ở profile_similar, QUERY-ONLY, DELTA, DELTA+query, VOTE, BAYES-H và Ordinal-Intent.
- Không để từng method sửa weights theo điểm benchmark hoặc thêm phản ứng D vào profile C. Nhờ vậy không có method được cấp riêng một profile tốt hơn để thắng.
- **Khóa chung không có nghĩa mọi user có cùng weights.** User khác có thể có profile khác. Mask ignore còn làm thay tập facet/mẫu số của scorer, dù weights đầu vào không đổi.
- Hai ngoại lệ: fixed_similar dùng năm weights đều .20; Oracle dùng weights phiên ẩn (context .60, focus .40, facet khác 0), không dùng weights C dự đoán.

### 2.3. Cơ chế sinh data — sinh những gì?

**“Sinh” trong D là dựng bằng quy tắc:** ghép facet records có nguồn, tạo query theo template và mô phỏng phản ứng bằng số. Bài thật được giữ nguyên; không phải toàn bộ bài báo đều do LLM tạo.

1. **Chốt nguồn:** bài thật + facets A đã lọc + users/history C → `inputs/base_v1/`. Đây là snapshot nguyên liệu, chưa phải bộ đánh giá cuối.
2. **Chọn thiết kế:** chọn bài mốc, context và focus khác context. Tìm bài thật cùng context, có cả phía giống/khác focus. Phía thiếu mới ghép facet record bổ sung, giữ context và ghi nguồn từng facet; không bịa abstract/DOI.
3. **Dựng pool:** một phía giống + một phía khác + 18 ngoài context. Giữ pool cho hai hướng và ba query modes. Catalog facet thật/tổng hợp ở `catalog/`.
4. **Dựng observation riêng:** lấy background nguồn khác, giữ context/facets nền, thay focus để tạo hai phía. Validator kiểm tách observation khỏi candidate IDs/nội dung cần kiểm. Có **152 observation records**, được dùng lại theo thiết kế, không sinh riêng một bộ mới cho mỗi phiên.
5. **Sinh phiên và đáp án:** mỗi thiết kế tạo 2 hướng × 3 modes; gán user/cutoff. Context luôn similar; focus theo hướng đặt trước; facet khác ignore. Ghi `generated/sessions.jsonl`; intent và nhãn 2/1/0 lưu riêng trong `ground_truth/` (**2.280 nhãn candidate**).
6. **Sinh query:** clear có câu context rồi câu nêu focus/hướng rõ; ambiguous chỉ context; none không có query. Ghi `generated/search_events.jsonl`. Query clear đang được dựng khớp intent, không mô phỏng query sai hướng.
7. **Sinh exposure/phản ứng:** xáo thứ tự hai phía observation, ghi exposure trước cutoff. Bài thỏa intent có utility nền .70, không thỏa .05; cộng Gaussian noise rồi lượng tử thành dislike/view/click/save/like. Ghi `conditions/*/generated/`. Utility/noise/grade dùng kiểm tra nằm trong provenance ẩn, không đưa vào estimator.
8. **Lặp và kiểm:** 3 seeds × noise .2/.5 tạo sáu điều kiện trên cùng thiết kế. Noise là độ lệch chuẩn, không phải tỷ lệ 20%/50% phản ứng sai. Ghi provenance/config/manifest; kiểm nguồn, nhãn, thời gian, checksum và tách observation–candidates; khóa `datasets/observation_v1/`.

**Đầu ra sinh được:** catalog facet bổ sung, thiết kế/phiên, query, exposure, reaction, intent ẩn, relevance labels và provenance. Benchmark chỉ đọc bộ đã khóa, không sinh data khác nhau cho từng method.

## 3. Code chạy và phương pháp khác nhau ở đâu?

![Hình 2. Luồng code dựng dữ liệu và chạy benchmark hoàn chỉnh](figures/d_hien_thuc.png)

**Các phương pháp thay phần suy directions:**

- **Bốn baseline gốc:** fixed_similar (luôn giống, weights đều), profile_similar (luôn giống, weights C), DELTA (chỉ phản ứng), DELTA + query.
- **Đối chứng bổ sung:** QUERY-ONLY, VOTE, BAYES-H và Ordinal-Intent. Tất cả không train.
- **Oracle Intent:** evaluator dùng directions và trọng số phiên đúng; không phải phương pháp thực tế để chọn thắng.

DELTA hỏi: **“Trong những cặp có thể đối chiếu, người dùng phản ứng tốt hơn với phía giống hay phía khác bài mốc?”** Phản ứng được đổi thành điểm rồi lấy chênh lệch. Phần 6.4 giải từng con số; DELTA không phải hàm chấm điểm candidates.

### 3.1. Ranking nhận gì, trả gì?

**Đầu vào:** bài mốc, context, 20 candidates, directions vừa dự đoán, vector biểu diễn facet và C weights đã khóa. **Đầu ra:** mỗi candidate có một điểm; sắp điểm cao xuống thấp để được danh sách gợi ý. Khối này không suy lại intent và không nhận nhãn grade 0/1/2.

Ba thứ đóng vai trò khác nhau:

- **Cosine S:** candidate giống bài mốc đến đâu ở một facet, theo vector TF-IDF; 1 là rất giống, 0 là không có tương đồng theo biểu diễn này.
- **Direction:** người dùng muốn ưu tiên phía giống hay khác tại facet đó.
- **Weight:** facet đó quan trọng đến mức nào khi cộng vào điểm cuối.

### 3.2. Bước trước scorer: R_active chọn facet tham gia

Giả sử estimator trả về **task=similar, problem=different**, các facet khác unknown. Có duy nhất một focus ngoài context là problem → R_active giữ task/problem và đặt method/dataset/contribution thành ignore. Đây là scope suy được, không dùng focus thật trong đáp án.

Nếu chưa xác định được một focus duy nhất, policy dùng fallback always-similar. Directions ban đầu vẫn giữ khi chấm: unknown không được biến thành một lần suy đúng nhờ fallback.

### 3.3. Scorer gốc intent_scores tính điểm từng candidate

Tiếp tục cùng bài mốc: **task = gợi ý bài báo**, **problem = thiếu lịch sử người dùng**.

1. **Giữ context trước:** nếu candidate thiếu task hoặc cosine task ≤ 0, cho điểm −1. Bài ngoài task không được ưu tiên chỉ vì problem của nó khác.
2. **Đổi similarity thành mức đáp ứng hướng:** muốn similar thì dùng **S**; muốn different thì dùng **1−S**. Ví dụ cosine problem=0,95: rất tốt khi muốn giống (term=0,95), nhưng ít phù hợp khi muốn khác (term=0,05).
3. **Cộng theo trọng số và chia cho tổng weights đang dùng:** `Score = Σ(weight × term) / Σweight`. Điểm cao hơn được đứng trước.

**Tính cụ thể với C weights đã minh họa ở mục 2.2:** task=.30, problem=.40, ba facet còn lại mỗi facet .10. R_active chỉ giữ task/problem nên mẫu số là **.30+.40=.70**; không phải thay profile C thành weights của Oracle.

- **Candidate A:** cosine task=.90, problem=.95 — cùng task và rất giống problem bài mốc.
- **Candidate B:** cosine task=.85, problem=.20 — cùng task nhưng ít giống problem bài mốc theo cosine.

**Nếu muốn giống problem:**

```text
A: (.30 × .90 + .40 × .95) / .70 = .9286
B: (.30 × .85 + .40 × .20) / .70 = .4786
→ A đứng trước B.
```

**Nếu muốn khác problem:** context task vẫn dùng S; chỉ term problem đổi thành 1−S.

```text
A: (.30 × .90 + .40 × (1−.95)) / .70 = .4143
B: (.30 × .85 + .40 × (1−.20)) / .70 = .8214
→ B đứng trước A.
```

**Cùng candidates, cosine và weights; chỉ đổi hướng problem đã làm đổi thứ tự.** Đây là ý nghĩa của ranking theo intent. Điểm .8214 là điểm xếp hạng, không phải xác suất user thích B hay nhãn grade của B.

Quy tắc biên của hàm gốc: ignore không tham gia; unknown đi theo nhánh S nếu được đưa vào scorer. Candidate thiếu facet active có weight nhận −1; facet thiếu ở anchor bị bỏ; hết weights dùng cosine context; hòa điểm xếp theo ID. R_active là policy trước scorer, còn **intent_scores là công thức chấm điểm gốc được giữ nguyên**.

Vectors/candidates dùng chung; ngoài fixed_similar, các phương pháp dùng cùng C weights. Oracle là mốc riêng dùng weights phiên ẩn.

Ở đây **scope là tập facet đang tham gia nhu cầu/ranking**, thường là context + focus. Workgroup trong phần tổng hợp số liệu là nhóm công trình liên quan tới bài mốc; mục đích là tránh coi các phiên sinh từ cùng nội dung thành nhiều bằng chứng độc lập.

## 4. Metrics, bảng chính và phân tích kết quả

### Bảng tra cứu metrics

Bảng này giải nghĩa chỉ số. Bảng chính so các phương pháp trên toàn bộ benchmark; các bảng phụ ở mục 7 phân tích cùng kết quả theo nguồn candidates, query, nhiễu, mức từ chối trả lời và định nghĩa metrics gốc.

| Chỉ số | Đo điều gì? | Cách đọc trong D |
|---|---|---|
| Accuracy focus ↑ | Tỷ lệ đoán đúng hướng tại focus thật | Unknown tính sai; không phải accuracy toàn pipeline |
| F1 focus ↑ | Trung bình F1 của similar và different | Cân bằng precision–recall; đọc kèm coverage. Tạo confusion theo thiết kế trong workgroup rồi lấy mean groups |
| Coverage focus ↑ | Tỷ lệ có trả lời similar/different tại focus thật | Trả lời nhiều chưa chắc đúng; luôn similar coverage 100% nhưng accuracy 50% |
| Joint accuracy ↑ | Đúng cả focus suy được và direction | Không tính context cho sẵn thành tự suy ra; có trong kết quả chi tiết |
| nDCG@5/@10 ↑ | Bài grade cao có lên cao trong top K không | Gain=2^grade−1; 0,9632 không phải 96,32% chọn đúng |
| Grade-2@1 ↑ | Bài đúng context và đúng hướng đứng đầu | DELTA+query đạt 94,56%; trực tiếp về bài hạng 1 |
| Compliance@5/@10 ↑ | Số grade 2 trong top K chia K | Một grade 2/phiên → trần .20/.10; .10 ở @10 có thể đã tối đa |
| Recall@K ↑ | Bao nhiêu positive được lấy vào top K | Gốc nhận grade 1 và 2 là positive; có thể cao dù ưu tiên sai hướng |
| Precision@K ↑ | Tỷ lệ positive trong top K | Hai positive/pool → trần @5=.40, @10=.20 |
| MRR@K ↑ | Nghịch đảo hạng positive đầu tiên; 0 nếu top K không có | Grade 1 đứng đầu vẫn MRR=1; cần đọc cùng Grade-2@1/Compliance |
| Importance MAE ↓ | Sai lệch trung bình năm weights so với weights phiên ẩn | Methods cùng C weights có cùng MAE; không đo riêng chất lượng suy hướng |

Accuracy/F1/Coverage ở bảng chính chỉ chấm **focus**. Bản gốc chấm cả **context + focus**: luôn similar đạt 75% ở bản gốc nhưng chỉ 50% tại focus. Bảng chính tổng hợp theo thiết kế/nhóm anchor; bảng legacy giữ tổng hợp gốc. Không trộn các định nghĩa khi so số.

### Bảng chính — so sánh các phương pháp trên toàn bộ benchmark

| Phương pháp | Accuracy | F1 | Coverage | nDCG@10 | Grade-2@1 | C@5 | C@10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed_similar | 50,00% | 0,3333 | 100,00% | 0,8029 | 50,00% | 0,1722 | 0,0903 |
| profile_similar | 50,00% | 0,3333 | 100,00% | 0,8019 | 50,00% | 0,1722 | 0,0903 |
| QUERY-ONLY | 33,33% | 0,5000 | 33,33% | 0,8623 | 66,44% | 0,1815 | 0,0935 |
| DELTA | 95,83% | 0,9734 | 96,80% | 0,9597 | 93,63% | 0,1981 | 0,0993 |
| **DELTA + query** | 96,91% | 0,9793 | 97,84% | 0,9632 | 94,56% | 0,1985 | 0,0995 |
| VOTE | 91,74% | 0,9545 | 92,05% | 0,9523 | 91,59% | 0,1962 | 0,0988 |
| BAYES-H | 91,51% | 0,9533 | 91,82% | 0,9518 | 91,36% | 0,1962 | 0,0988 |
| Ordinal-Intent | 81,13% | 0,8934 | 81,13% | 0,9374 | 87,00% | 0,1940 | 0,0979 |
| Oracle — đặc quyền | 100,00% | 1,0000 | 100,00% | 0,9862 | 100,00% | 0,2000 | 0,1000 |

**Đọc cột:** Accuracy/F1/Coverage chấm tại focus; unknown tính sai trong accuracy. nDCG đo thứ hạng, không phải phần trăm đoán đúng. C@K là Compliance@K = số grade 2 trong top K / K; một grade 2/phiên nên trần C@5=0,20 và C@10=0,10.

**Bảng chính đã bao gồm nhiễu:** kết quả được tổng hợp trên **3 feedback seeds (42, 43, 44) × 2 mức nhiễu phản ứng Gaussian (σ=0,2 và σ=0,5)** của cùng 114 phiên. Trong mỗi điều kiện, các phương pháp sử dụng phản ứng nhận **cùng bộ phản ứng đã sinh**; query, candidates, vector, C weights và policy ranking được giữ chung theo các ngoại lệ baseline đã nêu. Tham số của từng phương pháp giữ nguyên qua các điều kiện, không được nhận σ thật để chọn cách xử lý. Các mốc không đọc phản ứng vẫn là đối chứng, không bị nhiễu phản ứng tác động trực tiếp.

Ví dụ DELTA+query: accuracy **100,00%** ở σ=0,2 và **93,83%** ở σ=0,5; tổng hợp thành **96,91%** trong bảng chính. **Bảng P3** tách kết quả theo nhiễu để thấy mức suy giảm. σ là độ lệch chuẩn, không phải tỷ lệ 20%/50% phản ứng sai. Các lần lặp seed/noise không được coi là các nội dung độc lập mới.

Bảng chính dùng trung bình theo thiết kế rồi nhóm bài mốc. Metrics gốc tính cả context + focus và Recall/Precision/MRR được đưa vào P5–P6 ở mục 7 của chính báo cáo này; không trộn hai định nghĩa. [Báo cáo tự sinh đầy đủ](results/benchmark_complete_20261021_01/report.md) vẫn được giữ để đối chiếu.

### Vì sao baseline DELTA + query đạt kết quả cao nhất?

**Điểm cao tuyệt đối và đứng đầu các methods là hai câu hỏi khác nhau.** Các số dưới đây là kết quả quan sát; giải thích về cơ chế là suy luận phù hợp với code/dataset, chưa phải chứng minh nhân quả bằng ablation từng thành phần.

1. **Phép thử có cấu trúc thuận lợi cho suy hướng.** Bốn cặp observation được thiết kế để giữ nền/context và đối lập ở focus; phản ứng được sinh từ mức thỏa intent. DELTA cộng trực tiếp các chênh lệch này, nên có tín hiệu rõ để suy hướng. Đây là giải thích về độ phù hợp giữa baseline và simulator, không phải bằng chứng DELTA luôn tốt trên log tự nhiên. Ở noise .2, cả DELTA và DELTA+query đạt 100% accuracy (bảng P3).
2. **Query rõ là tín hiệu rất sạch.** Trong bộ hiện tại, clear query được dựng đúng hướng và parser gốc đọc được; quy tắc override có thể sửa hướng/unknown do phản ứng. Accuracy của DELTA tăng 95,83% → 96,91% khi thêm query. Tuy nhiên VOTE/BAYES-H/Ordinal cũng đạt 100% ở clear, nên riêng query không giải thích được toàn bộ ưu thế giữa các methods (bảng P2).
3. **Lợi thế quan sát được chủ yếu là coverage.** DELTA+query chỉ unknown 2,16%, so với VOTE 7,95%, BAYES-H 8,18% và Ordinal 18,87%. Các phương pháp bổ sung có ít lỗi khi đã trả lời, nhưng bỏ nhiều phiên hơn; accuracy toàn bộ coi unknown là sai. Vì vậy không nên viết rằng DELTA chính xác hơn ở mọi tình huống hoặc trên mọi phần phiên đã trả lời (bảng P1).
4. **Ngưỡng và likelihood của method bổ sung có thể chưa hợp dữ liệu ít cặp.** VOTE bỏ hòa, yêu cầu đủ phiếu và đồng thuận; Bayes/Ordinal dùng giả định likelihood và ngưỡng posterior/gap. Chúng có thể chưa đủ tự tin dù tổng chênh lệch đã đủ cho DELTA. Bảng P1/P3 cho thấy abstain nhiều và giảm điểm ở nhiễu cao; để quy bao nhiêu tổn thất cho từng ngưỡng/likelihood cần ablation riêng, hiện chưa có. Không kết luận Bayes nói chung kém DELTA.
5. **Ranking cao còn nhờ cấu trúc pool và policy chung.** Pool có 18 bài ngoài context, chỉ hai bài đúng context; context gate và R_active làm phép thử dễ hơn retrieval toàn corpus. Thành phần này dùng chung cho các methods, nên giải thích một phần mức điểm cao tuyệt đối, không tự giải thích vì sao chỉ DELTA+query đứng đầu. Do suy hướng đúng ở nhiều phiên và ít fallback hơn, nó thường đưa ranking vào đúng scope/hướng hơn. Liên hệ này phù hợp số liệu; chưa tách được toàn bộ ảnh hưởng bằng một phép so chỉ thay coverage.

**Cách viết kết luận:** “Trong benchmark mô phỏng hiện tại, DELTA+query kết hợp bằng chứng phản ứng có cấu trúc với query rõ, đạt độ phủ cao và chất lượng ranking tốt nhất trong các phương pháp public đã thử.” Không mở rộng thành phương pháp tối ưu cho mọi dữ liệu/người dùng. **Các bảng P1–P6 ở mục 7 giúp kiểm tra cách giải thích này.**

“Đứng đầu” ở đây nói về accuracy hướng và nDCG toàn bộ, không phải cao nhất ở mọi chỉ số: các mốc always-similar vẫn có coverage 100% và có thể MRR gốc cao do cách tính positive khác mục tiêu đúng hướng.

## 5. Kết luận — luận điểm và minh chứng

### Luận điểm 1: query/phản ứng giúp suy hướng nhu cầu phiên

**Minh chứng:** DELTA chỉ phản ứng đạt accuracy focus **95,83%**, so với **50,00%** của profile_similar không đọc tín hiệu phiên (+45,83 điểm %). Thêm query đạt **96,91%**, tăng **1,08 điểm %** so với DELTA. Khoảng paired 95% theo nhóm anchor cho phần tăng do query là **[0,39; 1,85] điểm %**, nằm trên 0 trong pilot.

**Diễn giải:** phản ứng cung cấp bằng chứng mạnh; query bổ sung một mức cải thiện nhỏ. QUERY-ONLY coverage 33,33% vì chỉ mode clear nêu đủ hướng. Chưa thể kết luận hiểu tốt mọi query tự nhiên hoặc query sai hướng.

### Luận điểm 2: intent suy được, qua cùng policy/scorer, giúp ranking phù hợp nhu cầu hơn

**Minh chứng:** DELTA+query đạt nDCG@10 **0,9632**, so với **0,8019** của profile_similar, tăng **0,1613**; khoảng paired 95% là **[0,1081; 0,2159]**. Bài đúng nhu cầu đứng hạng 1 ở **94,56%**, so với **50,00%** của profile_similar. Chỉ xét candidates thật, nDCG cũng tăng **0,7537 → 0,9483**.

**Diễn giải:** lợi ích không chỉ xuất hiện trong nhóm có candidate tổng hợp. Phép so thay khả năng suy scope lẫn dấu hướng, dù cùng policy; không quy toàn bộ chênh lệch cho riêng dấu similar/different. Hai nhóm thật/mixed khác focus/context nên không dùng chênh lệch giữa nhóm làm bằng chứng nhân quả cho tác dụng tổng hợp.

### Kết quả lựa chọn phương pháp: DELTA+query vẫn tốt nhất trong các methods đã thử

**Minh chứng:** DELTA+query có accuracy/nDCG **96,91% / 0,9632**, cao hơn VOTE **91,74% / 0,9523**, BAYES-H **91,51% / 0,9518** và Ordinal-Intent **81,13% / 0,9374**. Oracle đạt **100% / 0,9862** nhưng dùng đáp án ẩn nên không tham gia chọn method tốt nhất.

**Kết luận lựa chọn:** dùng **DELTA+query gốc + R_active chung + intent_scores gốc** cho pilot. Chưa có bằng chứng method bổ sung vượt baseline; baseline đứng đầu không tự trở thành thuật toán mới.

**Giới hạn của hai luận điểm:** mô phỏng có kiểm soát, chỉ 12 bài mốc, query/cặp thuận lợi và phần lớn candidates ngoài context; các methods được chọn sau khi đã xem pilot. Khoảng theo nhóm không biến đây thành test độc lập. Chưa xác nhận với người dùng thật hoặc nội dung mới chưa dùng để chọn thiết kế.

Nguồn: [lượt chạy complete](results/benchmark_complete_20261021_01/report.md), 5.472 public predictions + 684 Oracle. Chạy lại từ thư mục experiments bằng `python -B scripts/exp_d/proposal/run_benchmark.py`.

## 6. Ví dụ cụ thể cho từng phương pháp

### Ngữ cảnh chung: người dùng đang đọc bài gì và quan sát những gì?

**Bài mốc:** bài nghiên cứu task **gợi ý bài báo** (`paper recommendation`), xử lý problem **thiếu lịch sử người dùng** (`cold start`). Context task đã được cho sẵn. Hệ thống phải suy người dùng có đang quan tâm problem và muốn giống hay khác problem đó không.

Chuẩn bị **bốn cặp observation riêng**. Trong cặp i:

- **Sᵢ — phía giống:** task vẫn gợi ý bài báo, problem vẫn cold start.
- **Dᵢ — phía khác:** task vẫn gợi ý bài báo, problem khác, chẳng hạn đa dạng hóa gợi ý.
- Các facet nền của hai phía được giữ tương ứng. Giống/khác được xác định từ facet so với bài mốc, **không phải nhìn phản ứng rồi mới gọi tên hai phía**. Bốn cặp gồm tám bản ghi; chúng không phải candidates A/B của ví dụ ranking.

Trước cutoff, simulator ghi phản ứng lên từng bản ghi. Quy tắc đổi phản ứng thành điểm của baseline là **dislike=−1, view=0, click=1, save=2, like=3**. Trong ví dụ, mỗi phía Sᵢ nhận view, phía Dᵢ nhận like:

```text
Cặp 1: S₁ được view (0); D₁ được like (3) → d₁ = 3−0 = +3
Cặp 2: S₂ được view (0); D₂ được like (3) → d₂ = 3−0 = +3
Cặp 3: S₃ được view (0); D₃ được like (3) → d₃ = 3−0 = +3
Cặp 4: S₄ được view (0); D₄ được like (3) → d₄ = 3−0 = +3
```

**Vậy `[3,3,3,3]` là bốn chênh lệch phản ứng của bốn cặp.** Mỗi số 3 nghĩa là trong cặp đó, phía khác được phản ứng cao hơn phía giống 3 điểm. Chúng không phải bốn bài báo, bốn nhãn relevance hoặc bốn điểm ranking.

Query còn có câu `problem: more papers using cold start`, tức **muốn giống problem**. Câu này trái với xu hướng phản ứng vừa quan sát. DELTA chỉ phản ứng sẽ không đọc câu này; các method có query sẽ xử lý nó theo quy tắc riêng.

Giả sử đáp án ẩn thật là **similar**; phản ứng trong ví dụ bị nhiễu nên nghiêng về phía khác. Đây là **tình huống minh họa cách quyết định, không trích một phiên benchmark**. Các posterior phía dưới đã kiểm bằng code trên đúng cấu hình bằng chứng này; không dùng ví dụ để chọn method thắng.

### 6.1. fixed_similar — baseline gốc

**Cơ chế:** không đọc query/phản ứng phiên, luôn đặt năm facets similar, weights đều **.20**.

**Ví dụ:** dù bốn cặp đều nghiêng different, vẫn đặt problem=similar. Không suy một focus duy nhất nên R_active dùng fallback all-similar; ranking tính cả năm facets với weights đều.

### 6.2. profile_similar — baseline gốc

**Cơ chế:** cũng luôn similar nhưng dùng C weights của user.

**Ví dụ:** profile minh họa `(problem=.40, task=.30, method=.10, dataset=.10, contribution=.10)` vẫn cho problem=similar, với weight .40 thay vì .20 của fixed_similar. Hai baseline khác weights, không khác cách suy hướng; đều không dùng tín hiệu phiên.

### 6.3. QUERY-ONLY — chỉ query

**Cơ chế:** parser gốc, không đọc phản ứng.

**Ví dụ:** `more papers using cold start` include concept problem của anchor → **problem=similar**, context task=similar, facets khác unknown. R_active giữ task/problem. Nếu không có query focus rõ thì các facet ngoài context còn unknown.

### 6.4. DELTA / direction_behavior — baseline gốc

**DELTA là cách suy hướng từ chênh lệch phản ứng.** Nó không đọc query; cũng không chấm điểm 20 candidates ở bước này.

**Bước 1 — chênh lệch của từng cặp:** `dᵢ = điểm phản ứng phía khác − điểm phản ứng phía giống`. Ví dụ phía khác like=3, phía giống view=0 → dᵢ=+3. Nếu đổi hai phản ứng thì dᵢ=−3, tức bằng chứng nghiêng về phía giống.

**Bước 2 — gom bằng chứng của các cặp hợp lệ:** gọi n là số cặp dùng được. Baseline gốc tính:

```text
delta = (d₁ + d₂ + ... + dₙ) / (n + 2)
```

Số **+2 trong mẫu số** làm co mức bằng chứng khi số cặp ít. Nó không có nghĩa thêm hai cặp quan sát giả hay hai candidates. Đây là quy tắc cố định của baseline.

**Bước 3 — thay số trong ví dụ:** có n=4 cặp, mỗi cặp dᵢ=+3.

```text
Tổng chênh lệch = 3+3+3+3 = 12
Mẫu số          = 4+2 = 6
delta           = 12/6 = +2
```

**Bước 4 — đổi delta thành direction:** cần n≥2. Nếu delta≥+.25 → different; delta≤−.25 → similar; còn lại unknown.

Vì có bốn cặp và delta=+2, kết luận **problem=different**: người dùng có vẻ muốn bài khác problem cold start, nhưng vẫn giữ task gợi ý bài báo. Số 2 là độ chênh tổng hợp, không phải xác suất, số bài đúng hay điểm ranking; delta có thể lớn hơn 1.

Kết quả directions ở đây là `task=similar, problem=different`, các facet khác unknown. Sau đó R_active giữ task/problem và ranking dùng term **1−S_problem**, nên có xu hướng đưa candidate B của mục 3 lên trước A.

**Vì sao vẫn có thể sai?** Đáp án ẩn của ví dụ là similar, nhưng phản ứng nhiễu đang nghiêng về different. DELTA chỉ nhìn bằng chứng phản ứng nên bị đánh lừa. Tới mục 6.5, query rõ mới được thêm vào để cập nhật kết luận.

### 6.5. DELTA + query / direction_search — baseline gốc

**Cơ chế:** DELTA rồi query override theo parser/thứ tự thời gian gốc.

**Ví dụ:** DELTA ban đầu different; query rõ include `cold start` → output cuối **problem=similar**. Query thắng phản ứng trong trường hợp này; đây là quy tắc override, không phải posterior fusion.

### 6.6. VOTE — phiếu dấu phản ứng, có query override

**Cơ chế:** bỏ hòa; ít nhất hai phiếu và tối thiểu 75% cùng dấu mới chốt hướng, rồi áp dụng query override.

**Ví dụ:** bốn dấu dương → 4/4 phiếu cho different. Query rõ muốn giống sau đó đổi output cuối thành **similar**. Chênh +1 hay +3 đều chỉ là một phiếu; DELTA còn dùng độ lớn chênh lệch.

### 6.7. BAYES-H — kết hợp bằng chứng mềm

**Cơ chế:** xét tối đa tám giả thuyết `(focus, direction)`, gộp likelihood dấu phản ứng và query. Query không tự động ghi đè.

Posterior có thể hiểu là độ tin cho mỗi giả thuyết **sau khi gộp các bằng chứng**, theo giả định xác suất của method.

**Ví dụ:** bốn phiếu different đủ mạnh để vượt query similar. Posterior `(problem,different)` khoảng **0,4939**, hypothesis thứ hai khoảng **0,0754**. Đạt posterior≥.25 và gap≥.10 → **different**. Ví dụ này suy sai intent ẩn; posterior là độ tin theo mô hình, chưa phải xác suất hiệu chuẩn.

### 6.8. Ordinal-Intent — giữ mức chênh lệch và hòa

**Cơ chế:** posterior focus–direction dùng giá trị chênh ordinal, giữ xác suất hòa và marginalize strength trên grid cố định [.25,.75,1.5].

**Ví dụ:** bốn chênh +3 là bằng chứng mạnh cho different. Với cùng query similar, posterior `(problem,different)` khoảng **0,9375** → **different**. Khác BAYES-H ở likelihood mức chênh, không chỉ dấu phiếu. Tin cao vẫn có thể sai khi phản ứng nhiễu hoặc likelihood không phù hợp; không có nghĩa phương pháp tốt hơn.

### 6.9. Oracle Intent — mốc đặc quyền

**Cơ chế:** evaluator cấp directions và weights phiên đúng từ simulator, không cần suy từ query/phản ứng.

**Ví dụ:** đáp án đã đặt problem=similar, task=similar, weights task=.60/problem=.40, facet khác ignore/0. Oracle dùng đúng các số ấy, nên không bị bốn cặp phản ứng nhiễu kéo sang different. Đây không phải hệ thống triển khai thực tế vì người dùng không đưa sẵn đáp án ẩn.

## 7. Các bảng phụ — mục đích, số liệu và cách đọc

**Tất cả bảng dưới đây lấy từ cùng lượt `benchmark_complete_20261021_01`; không sinh data hoặc chạy method mới.** P1–P4 giữ cách tổng hợp theo thiết kế/nhóm anchor như bảng chính. P5–P6 dùng evaluator và cách tổng hợp gốc, được tách tên rõ.

### P1. Đúng, sai và unknown — baseline thắng vì trả lời đúng hơn hay trả lời nhiều hơn?

**Mục đích:** phân biệt lỗi dự đoán với unknown tại focus thật, để giải thích accuracy và coverage. Tỷ lệ đều đã lấy trung bình theo nhóm như bảng chính.

| Phương pháp | Đúng / toàn bộ | Sai / toàn bộ | Unknown / toàn bộ | Coverage |
| --- | ---: | ---: | ---: | ---: |
| DELTA + query | 96,91% | 0,93% | 2,16% | 97,84% |
| VOTE | 91,74% | 0,31% | 7,95% | 92,05% |
| BAYES-H | 91,51% | 0,31% | 8,18% | 91,82% |
| Ordinal-Intent | 81,13% | 0,00% | 18,87% | 81,13% |

**Cách đọc:** ba cột đúng + sai + unknown cộng xấp xỉ 100% (do làm tròn). Ordinal không sai trên phần nó trả lời trong lượt này, nhưng bỏ 18,87% phiên; vì vậy không được chỉ báo accuracy có điều kiện rồi gọi nó là tốt nhất. DELTA+query trả lời rộng hơn, song vẫn có 0,93% sai.

### P2. Phân nhóm query — query thực sự giúp ở đâu?

**Mục đích:** tách query rõ, query chỉ nêu context và không có query; kiểm tra riêng giá trị của query so với phản ứng. Mỗi mode có 38 phiên, lặp sáu điều kiện phản ứng.

| Query mode | QUERY-ONLY acc. | DELTA acc. | DELTA+query acc. | VOTE acc. | BAYES-H acc. | Ordinal acc. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Rõ — clear | 100,00% | 96,76% | 100,00% | 100,00% | 100,00% | 100,00% |
| Mơ hồ — ambiguous | 0,00% | 93,98% | 93,98% | 86,46% | 85,76% | 66,78% |
| Không query — none | 0,00% | 96,76% | 96,76% | 88,77% | 88,77% | 76,62% |

**Cách đọc:** clear giúp tất cả methods có query đạt 100%; không phải chỉ DELTA+query. Khi query mơ hồ/không có, DELTA+query giống DELTA và vẫn hơn các methods bổ sung trong bảng. QUERY-ONLY khi ấy abstain, không phải đoán sai tất cả. Các modes có phản ứng được lấy mẫu riêng, nên chênh accuracy DELTA giữa các hàng không phải tác động của query; phép so method trong cùng hàng dùng cùng phản ứng.

### P3. Phân nhóm nhiễu — kết quả giữ được khi phản ứng kém rõ không?

**Mục đích:** xem độ nhạy với hai mức nhiễu Gaussian của simulator. Đây là độ lệch chuẩn, không phải tỷ lệ phản ứng sai 20%/50%. Mỗi hàng trung bình ba seeds và mọi query modes.

| Noise σ | DELTA acc. | DELTA+query acc. | VOTE acc. | BAYES-H acc. | Ordinal acc. |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0,2 | 100,00% | 100,00% | 99,54% | 99,54% | 93,44% |
| 0,5 | 91,67% | 93,83% | 83,95% | 83,49% | 68,83% |

**Cách đọc:** ở nhiễu thấp, các phương pháp gần trần; ở nhiễu .5, DELTA+query còn 93,83%, Ordinal còn 68,83%. Kết quả cho thấy mức suy giảm trong simulator này, chưa xác nhận độ bền với mọi kiểu nhiễu hoặc người dùng thật.

### P4. Nguồn candidates — lợi ích có chỉ đến từ bản ghi tổng hợp không?

**Mục đích:** kiểm tra kết quả có còn xuất hiện khi pool hoàn toàn là bài thật, và công khai nhóm nào đã được bổ sung tổng hợp.

| Nhóm | Thiết kế / phiên | nDCG profile_similar | nDCG DELTA+query | nDCG Oracle |
| --- | ---: | ---: | ---: | ---: |
| Toàn bộ | 19 / 114 | 0,8019 | 0,9632 | 0,9862 |
| Chỉ candidates thật | 15 / 90 | 0,7537 | 0,9483 | 0,9839 |
| Có bổ sung tổng hợp | 4 / 24 | 0,8984 | 0,9929 | 0,9910 |

**Cách đọc:** nhóm candidates thật vẫn tăng 0,7537 → 0,9483. Bốn thiết kế mixed hiện là focus problem nên nguồn candidates và focus bị gắn với nhau; không dùng bảng để chứng minh tổng hợp làm bài toán dễ hơn. Oracle đôi khi thấp hơn method public về nDCG nhóm vì dùng weights riêng và cosine mềm không trùng hoàn toàn nhãn overlap; Oracle không phải trần toán học.

### P5. Chỉ số intent/weights theo định nghĩa gốc — đối chiếu giao thức nhóm trưởng

**Mục đích:** giữ các độ đo gốc trong báo cáo: direction chấm cả context+focus; weights so với intent phiên ẩn. Bảng này dùng trung bình case-condition và F1 gộp confusion của code gốc, không phải trung bình nhóm anchor như bảng chính.

| Phương pháp | Accuracy context+focus | F1 context+focus | Coverage context+focus | Importance MAE ↓ |
| --- | ---: | ---: | ---: | ---: |
| fixed_similar | 75,00% | 0,4286 | 100,00% | 0,2400 |
| profile_similar | 75,00% | 0,4286 | 100,00% | 0,2328 |
| QUERY-ONLY | 66,67% | 0,6875 | 66,67% | 0,2328 |
| DELTA | 97,88% | 0,9815 | 98,46% | 0,2328 |
| DELTA + query | 98,46% | 0,9868 | 98,98% | 0,2328 |
| VOTE | 95,91% | 0,9702 | 96,05% | 0,2328 |
| BAYES-H | 95,83% | 0,9694 | 95,98% | 0,2328 |
| Ordinal-Intent | 90,20% | 0,9256 | 90,20% | 0,2328 |
| Oracle — đặc quyền | 100,00% | 1,0000 | 100,00% | 0,0000 |

**Cách đọc:** always-similar đạt accuracy 75% vì context được cho sẵn luôn similar; tại focus vẫn chỉ 50%. Các methods dùng cùng C weights có cùng MAE 0,2328 ở cách tổng hợp này, nên MAE không phân biệt chất lượng suy hướng của chúng. MAE Oracle bằng 0 do được cấp weights thật.

### P6. Retrieval metrics gốc — kiểm tra việc lấy bài liên quan, không chỉ đúng hướng

**Mục đích:** đưa nDCG/Recall/Precision/MRR@5 và @10 gốc vào cùng báo cáo, thay vì chỉ liệt kê tên metric. Trong mỗi ô, số trước là @5, số sau là @10.

| Phương pháp | nDCG @5 / @10 | Recall @5 / @10 | Precision @5 / @10 | MRR @5 / @10 |
| --- | ---: | ---: | ---: | ---: |
| fixed_similar | 0,7940 / 0,8027 | 0,8684 / 0,8947 | 0,3474 / 0,1789 | 1,0000 / 1,0000 |
| profile_similar | 0,7902 / 0,7989 | 0,8684 / 0,8947 | 0,3474 / 0,1789 | 1,0000 / 1,0000 |
| QUERY-ONLY | 0,8474 / 0,8573 | 0,8904 / 0,9298 | 0,3561 / 0,1860 | 1,0000 / 1,0000 |
| DELTA | 0,9440 / 0,9571 | 0,9276 / 0,9942 | 0,3711 / 0,1988 | 0,9890 / 0,9890 |
| DELTA + query | 0,9467 / 0,9599 | 0,9291 / 0,9963 | 0,3716 / 0,1993 | 0,9890 / 0,9890 |
| VOTE | 0,9381 / 0,9514 | 0,9254 / 0,9927 | 0,3702 / 0,1985 | 0,9898 / 0,9898 |
| BAYES-H | 0,9378 / 0,9511 | 0,9254 / 0,9927 | 0,3702 / 0,1985 | 0,9898 / 0,9898 |
| Ordinal-Intent | 0,9211 / 0,9334 | 0,9181 / 0,9788 | 0,3673 / 0,1958 | 0,9915 / 0,9915 |
| Oracle — đặc quyền | 0,9851 / 0,9901 | 0,9737 / 1,0000 | 0,3895 / 0,2000 | 1,0000 / 1,0000 |

**Cách đọc:** code gốc nhận grade 1 và 2 là positive cho Recall/Precision/MRR. Vì vậy profile_similar có thể MRR=1 dù chỉ đúng hướng 50%; grade 1 đứng đầu vẫn được tính positive. Đánh giá đáp ứng nhu cầu phải đọc cùng Grade-2@1 và Compliance ở bảng chính. nDCG của P6 khác đôi chút bảng chính vì khác đơn vị tổng hợp, không phải hai lượt chạy cho kết quả mâu thuẫn.

**Nguồn kiểm tra:** `summary.json` cho bảng chính/P1–P4; `legacy_summary.json` cho P5–P6. Tất cả nằm trong [thư mục kết quả complete](results/benchmark_complete_20261021_01/). Các phân nhóm focus/direction và paired diagnostics đầy đủ vẫn có ở [groups.csv](results/benchmark_complete_20261021_01/groups.csv); báo cáo không in lại mọi tổ hợp để tránh lặp số.
