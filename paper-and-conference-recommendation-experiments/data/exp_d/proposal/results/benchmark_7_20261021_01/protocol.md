# Kế hoạch chốt D — một benchmark so baseline và method suy intent

Cập nhật 21/10/2026 sau khi đọc bản deep research người dùng cung cấp. Bản này thay các lựa chọn trước: giữ scorer gốc; chọn DELTA, VOTE và BAYES-H (thay Bayes đếm phiếu Beta–Binomial). Chưa viết hoặc chạy runner benchmark mới.

## 1. Phạm vi dữ liệu đã chốt

Dataset sử dụng: `proposal/datasets/observation_v1/`. Đây là benchmark **facet mock có kiểm soát**, candidates ưu tiên bài thật và bổ sung phía thiếu bằng bản ghi facet tổng hợp; observation cũng là bản ghi facet có nguồn. Không dùng nguồn bài cào ngoài corpus.

Không bắt buộc xác nhận các tổ hợp facet tổng hợp có thể trở thành bài báo thật, cũng không đòi human study trước khi chạy benchmark mock. Yêu cầu trước đó coi review ngữ nghĩa là điều kiện chặn benchmark đã nặng hơn phạm vi này và được bỏ.

Vẫn phải kiểm tính nhất quán nhãn/facet, nguồn, thời gian, tách observation–candidate và không rò đáp án. Dataset đã qua validator và 17 tests dữ liệu. Có thể dùng để triển khai/chạy benchmark theo phạm vi mô phỏng. Metadata `semantic_review: pending` giữ nguyên để phản ánh chưa xác nhận độ thực tế ngữ nghĩa, không sửa manifest/checksum để đổi trạng thái này; đây không còn là gate cho mock. Kết quả không chứng minh chất lượng recommendation/hài lòng với người thật.

Giữ nguyên dataset/config/seeds; không sinh lại để làm proposal thắng. 114 phiên thuộc 19 thiết kế/12 anchors, 3 feedback seeds × 2 mức nhiễu là các lần lặp, không phải 684 người/công trình độc lập. Báo riêng 15 thiết kế candidates toàn thật và 4 thiết kế problem có candidate tổng hợp; problem và mixed hiện bị gắn với nhau nên không quy khác biệt nhóm cho riêng nguồn synthetic.

## 2. Method mới được cắm ở đâu?

```text
Cùng dữ liệu công khai trước cutoff
     -> suy intent/directions: DELTA hoặc VOTE hoặc BAYES-H
     -> cùng interface directions
     -> intent_scores gốc + cùng profile C/vector/candidate pool
     -> chấm cả intent lẫn ranking
```

Chỉ tổ chức **một benchmark, một bảng kết quả chính**. Các hàng là baseline/method; các cột chấm đồng thời intent và ranking. Query/phản ứng có ích không, directions giúp ranking không và proposal tốt hơn không đều đọc từ bảng này, không đặt tên thành nhiều thực nghiệm A1/A2/A3/B/C riêng. Viết đủ 7 cấu hình dưới đây rồi chạy một batch có manifest cấu hình. Chạy lại chỉ khi sửa lỗi/code/data hoặc đổi phạm vi.

## 3. Danh sách method và cấu hình chạy

| ID | Method/cấu hình | Query phiên | Phản ứng phiên | Vai trò |
|---|---|---|---|---|
| F | fixed_similar gốc | Không | Không | Mốc trọng số đều, giữ nguyên để tham chiếu |
| N | profile_similar gốc | Không | Không | Mốc không dùng tín hiệu phiên, cùng profile C với so sánh chính |
| Q | QUERY-ONLY, parser gốc | Có | Không | Đối chứng tách tác dụng query, không là thuật toán mới |
| D-R | direction_behavior gốc — DELTA | Không | Có | Baseline suy hướng từ phản ứng |
| D-QR | direction_search gốc — DELTA + query | Có | Có | Baseline suy hướng có cả hai tín hiệu |
| V-QR | VOTE + parser gốc | Có | Có | So cùng nguồn thông tin với D-QR |
| H-QR | BAYES-H + query evidence | Có | Có | Proposal kết hợp query/phản ứng |

**Tổng cộng 7 cấu hình: 4 baseline gốc + QUERY-ONLY + VOTE và BAYES-H cùng dùng query/phản ứng.** Bỏ hai nhánh chỉ phản ứng của VOTE/BAYES-H vì baseline gốc đã đủ đối chứng tách nguồn tín hiệu. Chỉ có 3 họ suy từ phản ứng: DELTA, VOTE, BAYES-H. Không thêm GP, LLM hay ranker học ở lượt này. Các method không train trọng số từ nhãn tập đánh giá; Bayes chỉ cập nhật belief trong phiên. Không train là lựa chọn giữ phạm vi gọn, không phải điều kiện bắt buộc của công bằng.

Giữ nguyên logic bốn baseline gốc. F có trọng số khác nên chỉ là tham chiếu; so tác dụng directions chủ yếu dùng N và các dòng cùng profile C. Q gọi estimator/parser gốc với query nhưng không cung cấp logs phản ứng/exposure phiên. Các nhánh mới dùng cùng điểm phản ứng và cặp hợp lệ của baseline; không dùng focus thật hoặc evaluation candidate IDs/scores/labels để suy intent.

## 4. Một bảng kết quả chính và cách đọc

Mỗi dòng trong bảng method ở mục 3 xuất bốn cột: **accuracy hướng, joint focus–direction accuracy, coverage, nDCG@10**. Unknown tính sai trong hai accuracy toàn bộ. Coverage là tỷ lệ có dự đoán hợp lệ, tránh coi abstain nhiều là thắng. Các giá trị chưa có, không điền số minh họa thành kết quả.

Từ cùng bảng đó chỉ đọc ba ý:

1. **Tín hiệu giúp suy intent:** Q và D-R so với N; D-QR so với Q/D-R cho biết hai nguồn có bổ sung không. So các cột accuracy; query mode none là đối chứng tự nhiên khi không có query.
2. **Directions giúp ranking:** so cột nDCG@10 của N với Q/D-R/D-QR/V-QR/H-QR, giữ cùng scorer/profile/vector/pool. Các chênh lệch dương là bằng chứng hỗ trợ; accuracy tăng không tự bảo đảm ranking tăng.
3. **Method nào tốt nhất trong phạm vi đã so:** so D-QR, V-QR, H-QR vì cùng query và phản ứng. BAYES-H là proposal ứng viên, chưa có kết quả chứng minh tốt hơn. Đọc đồng thời accuracy toàn bộ, coverage và nDCG; không đòi một method phải thắng mọi chỉ số hoặc mọi nhóm mới báo được kết quả.

Nếu chọn method thắng bảng pilot để làm phương án triển khai cuối cùng, ghi rõ đây là lựa chọn trên benchmark này. Muốn khẳng định lợi thế trên test độc lập thì phải chọn/khóa trên dev trước test, không xem test rồi đổi tên method thắng thành proposal có sẵn từ đầu. Không bắt buộc thêm một pipeline riêng chỉ để chọn method trong lượt pilot này.

Không đặt trước mốc 80%/90% hoặc sửa dữ liệu để làm điểm đẹp. N luôn đoán similar đạt đúng 50% về direction tại focus thật trong dataset cân bằng hai hướng hiện tại; đây không phải mốc cho joint accuracy hoặc ranking. Nếu intent tốt hơn nhưng nDCG không tăng, chỉ hỗ trợ luận điểm suy hướng, chưa hỗ trợ lợi ích ranking.

Các nguồn dữ liệu, query mode, noise/seeds và real_only/mixed chỉ là phân nhóm tự động từ cùng kết quả, đưa phần diễn giải/phụ lục khi cần; không tổ chức thành các thực nghiệm mới. Grade-2-over-grade-1 và paired-direction success vẫn có thể xuất chẩn đoán, không cần thêm cột vào bảng chính.

## 5. Scorer và cách chấm cố định

Giữ `intent_scores` trong `scripts/baseline_common.py`, runner gốc `scripts/exp_d/run_exp_d.py`. Scorer kiểm context, tổng hợp cosine với similar hoặc 1-cosine với different, giữ weights/vector/missing/fallback/phá hòa gốc. Không thay R1 từng đề xuất. `unknown` gốc dùng nhánh cosine như similar; giữ cho mọi method và báo riêng coverage, không coi unknown là ignore.

Mỗi estimator xuất directions trên các facet; context luôn similar như baseline. BAYES-H nếu chấp nhận một hypothesis thì chỉ đặt hướng focus tương ứng, các facet còn lại unknown. Nếu abstain thì context similar và các facet còn lại unknown. Không thêm hidden weights; không cho confidence đổi ranker.

Chấm direction tại focus thật chỉ là thao tác evaluator; phương pháp không nhận focus thật. Chấm cả joint focus–direction: nếu duy nhất một facet ngoài context có hướng similar/different thì lấy làm predicted focus, không có/nhiều facet thì focus unknown. Dùng cùng phép chuyển cho baseline/method; không chọn bằng confidence khác thang đo. Không tính context được cho sẵn là thành tích. Cấu trúc cặp mock khiến focus dễ nhận ra, nên không mở rộng kết luận thành khám phá focus tự do ngoài thực tế.

Accuracy toàn bộ tính unknown là sai; báo coverage và accuracy phần đã trả lời. Đối chiếu coverage–risk ở các ngưỡng định trước, hoặc báo so sánh trên cùng phần phiên mà các phương pháp cùng trả lời kèm tỷ lệ giao; không gọi hai dòng có coverage rất khác là tương đương.

Ranking: nDCG@10 dùng gain 2^grade−1. Grade-2-over-grade-1 là tỷ lệ bài grade 2 đứng trước grade 1. Paired-direction success yêu cầu ưu tiên đúng ở cả hai phiên đối lập cùng pool; hòa tính chưa đúng. Compliance@5/@10 có trần .2/.1 trong pool hiện tại nên không dùng làm chỉ số chính.

So paired trên cùng session/seed/noise; gộp các lần lặp theo thiết kế rồi anchor/công trình liên quan khi báo khoảng bất định. Chênh lệch dương ổn định giữa anchors/seeds là bằng chứng tốt hơn một lượt may mắn; khoảng tin cậy paired theo nhóm có thể dùng khi số nhóm cho phép. Nếu khoảng còn chạm 0 thì ghi chưa đủ chắc, không khẳng định đã chứng minh mạnh. Không yêu cầu từng subgroup đều thắng, nhất là subgroup rất nhỏ.

## 6. Đặc tả method đã chọn, không dựa vào nhãn test

### DELTA và VOTE

Giữ mapping gốc dislike=-1, view=0, click=1, save=2, like=3 vì đây là thứ tự action của simulator đang dùng, không khẳng định đó là thang utility chung cho người thật. Cặp cho d=điểm(phía khác)−điểm(phía giống). Mỗi exposure chỉ lấy phản ứng cuối hợp lệ cho mỗi bản ghi, không nhân các sự kiện trong cùng chuỗi thành nhiều bằng chứng độc lập.

DELTA gốc giữ minimum_pairs=2, margin=.25, delta=sum(d)/(n+2). VOTE bỏ hòa, ít nhất 2 phiếu; chọn hướng nếu có ít nhất 75% phiếu cùng hướng, còn lại unknown. V-QR dùng cùng parser và quy tắc query override của D-QR.

### BAYES-H — proposal adaptation

Tên H chỉ hypothesis. Thay Beta–Binomial đếm phiếu từng facet bằng posterior trên hypothesis `(focus, direction)`. Đây là adaptation của ý tưởng Bayesian preference inference, không là bản tái hiện OPEN/DECISIVE/AMPLe.

- Một context đã biết và khác focus, nên có **tối đa 4×2=8 hypotheses**, không phải 10 như bài toán tổng quát trong research. Chỉ bỏ facet anchor không có dữ liệu bằng thông tin công khai; không lọc bằng focus thật.
- Prior đều trên các hypotheses hợp lệ. Không dùng profile/weights thật, noise condition thật hoặc labels để đặt prior.
- Reaction evidence là **pseudo-comparison** từ cặp phản ứng mô phỏng, không gọi là explicit user choice. Dùng các cặp matched cùng quy tắc baseline. Với hypothesis có facet không thay đổi hoặc không xác định qua cặp, likelihood trung tính .5. Với cặp không hòa có thể phân biệt hypothesis, likelihood .8 nếu phía phản ứng cao hơn tương thích hypothesis, .2 nếu trái hướng. Hòa đóng góp cùng một likelihood cho mọi hypothesis nên không đổi posterior. Dùng log-space và normalize; không tính lại likelihood trên từng event thành đếm đôi cặp.
- Query evidence dùng cùng parser gốc. Chỉ anchor-concept include/exclude rõ nghĩa ở ngoài context mới tạo evidence; lấy câu mới nhất trước cutoff có duy nhất một focus ngoài context. Nếu không có thì trung tính. Likelihood .8 cho hypothesis khớp và .2/(K−1) cho mỗi hypothesis còn lại, với K là số hypotheses; lặp lại cùng câu không nhân thêm bằng chứng. Đây là cách fusion mềm, khác hard override của D/V, và là một phần proposal cần kiểm tra.
- Posterior tỉ lệ prior × likelihood query × tích likelihood reaction. Khác bản Beta cũ vì xét đồng thời focus–direction và query có thể bị phản ứng trái chiều điều chỉnh lại.
- Mặc định quyết định: MAP phải có posterior >=.25 và cách hypothesis thứ hai ít nhất .10; nếu không có query rõ thì cần ít nhất 2 cặp không hòa có thể dùng. Nếu không đạt trả unknown. Các con số là heuristic định trước, không là xác suất đã calibrated hoặc ngưỡng suy từ bài báo. Không chọn lại theo test.
- Lượt benchmark tối thiểu dùng reaction reliability=.8 đã định trước; không sweep để chọn theo test. Độ nhạy .7/.9 và coverage–risk là phân tích bổ sung nếu cần kiểm độ phụ thuộc giả định, chưa là yêu cầu của bảng chính. Không dùng simulator noise=.2/.5 để gán reliability đúng đáp án; không sinh lại dataset cho các phân tích này.

Cùng evidence ở đầu vào không đòi các estimator phải dùng cùng phép tổng hợp; đó chính là thành phần đang so. Bộ parser, cặp hợp lệ và mapping actions không thay chỉ cho proposal. BAYES-H query fusion khác override phải được mô tả rõ, không quy toàn bộ lợi ích kênh QR cho riêng reaction update.

## 7. Đối chiếu research và nguồn gốc

Đã đọc toàn bộ bản deep research đính kèm. Nhận định không có bài khớp nguyên thiết lập là lý do dùng adaptation và không gọi tên method mới là reproduction.

Nguồn gốc đã đối chiếu trực tiếp:

- [OPEN — Bayesian Preference Elicitation with Language Models, arXiv 2024](https://arxiv.org/abs/2403.05534): kết hợp Bayesian optimal experimental design với LM cho featurization/verbalization. D đã có facets và log cố định nên không dùng khối LM/active question selection.
- [AMPLe — Comparison-based Active Preference Learning for Multi-dimensional Personalization, ACL 2025](https://aclanthology.org/2025.acl-long.1590/): comparative feedback, Bayesian posterior sửa đổi và active selection. Phản ứng ordinal mock của D không tự trở thành explicit comparisons nguyên bản.
- [DECISIVE — Guiding User Decisions with Optimal Preference Elicitation from Unstructured Documents, ACL 2026](https://aclanthology.org/2026.acl-long.1465/): tách bằng chứng tài liệu khỏi preference inference. Không chuyển nguyên importance weights hoặc ngưỡng dừng quyết định của bài sang nhãn focus–direction.

BAYES-H dùng exact enumeration trên tối đa 8 hypotheses, không cần particle approximation. Likelihood và thresholds nêu trên là thiết kế riêng cho mock, không được gán là công thức của các bài tham khảo. Chưa có bằng chứng proposal tốt hơn và không cam kết tính mới chỉ nhờ dùng Bayes.

## 8. Trạng thái và file được giữ nguyên

Giữ toàn bộ bộ gốc trong README.md/build_exp_d.py/generated/ground_truth/samples và runner gốc. Phần mới nằm trong proposal; `inputs/base_v1` là nguồn, `datasets/observation_v1` là bộ dùng chạy. Nguồn bài từng tìm thêm vẫn ở backup/20261020_data_reset/real_extension_20261020, không dùng.

Lần tinh gọn này chỉ cập nhật README_PROPOSAL.md: một benchmark, 7 cấu hình, một bảng chính. Không sửa generator, dataset/manifest, scorer, baseline hay luandiem.md. Chưa cài QUERY-ONLY/VOTE/BAYES-H hoặc chạy benchmark mới.
