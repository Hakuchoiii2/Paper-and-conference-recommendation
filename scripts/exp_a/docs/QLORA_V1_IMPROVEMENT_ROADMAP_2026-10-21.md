# Hướng cải tiến tiếp theo cho QLoRA v1

Ngày: 21/10/2026. Trạng thái: **đề xuất để triển khai và thử nghiệm**, chưa sửa pipeline, prompt, nhãn hoặc adapter; chưa chạy pilot/training mới.

**Cập nhật lựa chọn dữ liệu, 22/10/2026:** người dùng chọn pilot50 có sẵn thay cho việc chọn 50 bài từ dev100 ở mục 7. Dùng `facet_matrix_v2/8b_original` làm R0 (Micro F1 56,36; Macro F1 56,89), đã kiểm đủ 50 raw drafts và không giao QLoRA train/dev/test. R0 không cần inference lại; R2 dùng draft đã lưu và tối đa 2 calls review/repair mới để giữ cap 3 calls tính cả draft. Pilot này đã được dùng phát triển nhiều lần, không phải bộ xác nhận độc lập. Xem [bộ dữ liệu/R0 đã chuẩn bị](../../../data/exp_a/evaluation/base_v1_improvement_pilot50_20261022/README.md). R1/R2 chưa chạy.

## 1. Mục tiêu và lựa chọn hướng đi

Mục tiêu là cải thiện **v1 đang có**, ưu tiên trích đúng và đủ method/contribution, sửa được lỗi evidence và giữ đủ điều kiện của finding. Điểm F1 phải đi cùng độ đúng nguồn; không tăng điểm bằng cách giữ nhãn bị validator báo lỗi hoặc rút finding đến mất nghĩa.

Ba hướng có thể chọn:

| Hướng | Lợi ích | Chi phí/rủi ro | Đề xuất |
|---|---|---|---|
| Cải thiện inference/review của v1, giữ adapter và schema | Đo được tác dụng sớm, thay đổi nhỏ, giữ cách đặt nhãn đang hiệu quả | Prompt mới vẫn có thể lệch phân phối adapter đã học | **Làm trước**, từng thay đổi riêng trên dev |
| Rà nhãn train/dev rồi train một adapter kế tiếp | Xử lý thói quen bỏ finding, sai role và quá ngắn từ dữ liệu học | Tốn rà nguồn và GPU; phải giữ validation riêng | Làm sau khi chốt quy tắc nhãn và có bằng chứng inference không đủ |
| Thay toàn bộ bằng pipeline/schema v2 | Hỗ trợ evidence nhiều câu và policy rõ hơn ở một số ca | Hiện giảm agreement, review yếu, nhãn dài/gộp; thay nhiều biến cùng lúc | Chưa chọn làm hướng chính |

Tên “v1.1” trong tài liệu chỉ là tên dự kiến cho nhánh thử nghiệm kế tiếp, không phải một adapter đã tồn tại hoặc đã được chứng minh tốt hơn.

## 2. Bằng chứng dùng làm điểm xuất phát

### 2.1. Kết quả đã đo của v1

100 bài test đóng băng; 467 train / 100 dev. Adapter v1 dùng checkpoint 118, epoch 2, chọn bằng dev loss.

| Chỉ số | Base với pipeline v1 | Adapter v1 |
|---|---:|---:|
| Micro F1 | 47,44 | **59,28** |
| Macro F1 | 46,99 | **61,00** |
| Problem F1 | 37,45 | 53,04 |
| Task F1 | 48,06 | 62,14 |
| Method F1 | 54,17 | 64,66 |
| Dataset F1 | 51,02 | 73,17 |
| Contribution F1 | 44,24 | 52,00 |
| Fallback / 100 bài | 69 | 9 |

Adapter v1 còn 324 FP + 363 FN = **687 sự kiện lỗi theo reference**. Method chiếm 200, contribution 240: tổng 440/687 = **64,05%**. Đây là lý do ưu tiên hai facet này; không có nghĩa mọi FP/FN đều là lỗi nội dung thực tế.

Trên nhóm reference additional, mức tăng so với base chỉ khoảng 3,42 điểm; nhóm existing khoảng 18,98 điểm. Cần theo dõi cả hai nhóm, chưa đủ bằng chứng kết luận nguyên nhân là overfit hay nguồn nhãn.

### 2.2. Bài học từ đối chiếu v2

- Hai base dùng cùng Qwen3-8B/revision. Với cùng 100 nguồn/reference, base pipeline v1 đạt 47,44; v2 đạt 26,52. Replay với cùng grounding v2 vẫn là 44,98 và 26,52. Không thể giải thích toàn bộ bằng khác biệt cách lọc.
- Adapter v1 có 9 draft lỗi; review sửa thành hợp lệ **0/9**. Sáu draft lỗi được lượt review đầu tiên lặp nguyên văn. Adapter v2 cũng sửa **0/15**, cả 15 lặp nguyên văn. Thêm lượt tự rà không tự bảo đảm sửa lỗi.
- Nhãn cuối adapter v1 trung bình 5,27 từ; v2 13,85 từ. Nhãn ngắn có thể mất nghĩa, nhãn dài có thể gộp nhiều đơn vị; **không lấy độ dài làm mục tiêu tối ưu trực tiếp**.
- V2 có các ca giữ tốt hơn subject, comparator, metric, điều kiện và evidence nhiều câu. Chỉ tiếp thu phần có căn cứ; chưa thay toàn bộ v1 bằng v2.

Các số trên là kết quả lịch sử, **không phải kết quả của bản cải tiến**. Reference là GPT/Codex AI reference, human review pending. So sánh cũ còn khác prompt/schema/budget/review, không chứng minh nhân quả riêng cho một thành phần.

## 3. Giữ cố định những gì trước khi thử

Trong vòng cải thiện inference đầu tiên, giữ:

- Base model/revision, adapter weights v1 đã xác minh và tokenizer tương ứng.
- Schema v1: `concept` + một `evidence_id`. Không đổi thành `evidence_ids` trong cùng thí nghiệm sửa review.
- Greedy decoding, max 2048 token/lượt, tối đa 3 lượt gồm draft/review/repair; mọi arm có cùng giới hạn. Ghi số lượt thực dùng, không gọi thêm cho một arm mà không báo.
- Quy tắc source-only, sentence IDs, thuật toán chia câu và source text nguyên trạng.
- Bộ semantic matcher, embedding model/revision và threshold 0,85. Không thêm alias riêng cho các bài test đã xem.
- Tập bài, reference, manifest và chữ ký cấu hình đã khóa cho từng vòng.
- Cơ chế inventory/coverage, bảo toàn method/contribution hợp lệ và named-resource filtering của v1 làm mốc.

Nếu cần đổi một yếu tố này, phải tạo arm/phiên bản riêng để biết phần nào tạo chênh lệch. Bản mốc luôn chạy nguyên trạng; không sửa bản cũ rồi gọi đó là baseline.

## 4. Ưu tiên P0 — sửa review và quản lý output lỗi

### Vấn đề

V1 có thể tiếp tục giữ best available output dù nhãn bị cảnh báo evidence/word-order. Đây là thông tin audit hữu ích nhưng không đồng nghĩa toàn bộ nhãn cuối đã được nguồn hỗ trợ. Review hiện tại cũng có thể lặp lại đúng lỗi cũ.

### Hướng sửa

1. Giữ raw draft bất biến. Với mỗi lỗi, gửi feedback có cấu trúc: facet/index, concept, evidence_id, nguyên văn câu đã chọn và loại lỗi. Phân biệt sai field/ID, sai từ/thứ tự, duplicate, mất quantity/negation/caveat; không chỉ gửi “hãy rà lại”.
2. Yêu cầu sửa **item cụ thể**: chọn lại câu thực sự hỗ trợ hoặc lấy lại cụm từ từ câu đã chọn. Không có căn cứ thì bỏ item và ghi lý do; không tạo synonym để che lỗi.
3. Đối với item nguồn hợp lệ, chỉ thay khi có lý do rõ: sửa role, tách ý, bổ sung qualifier hoặc loại duplicate. Không khôi phục tự động một item đã được review xác định sai role chỉ vì nó khớp từ nguồn.
4. Parse và validate lại sau review. Nếu vẫn có lỗi và còn lượt thứ ba, dùng lượt đó để repair mục tiêu; không gửi lại cùng feedback tổng quát.
5. Tách rõ **output đủ điều kiện sử dụng** và **item lỗi giữ trong audit**. Khi hết budget, item lỗi không được lẫn vào tập nhãn được công bố là grounded. Bài vẫn nằm trong mẫu số đánh giá; ghi fallback và lượng thông tin bị loại.
6. Không nới validator để hợp thức hóa đầu ra. Nếu chính validator có false positive, ghi ca nguồn và sửa quy tắc bằng thí nghiệm riêng.

### Cần đo

- Số draft lỗi; số draft lỗi được sửa thành final hợp lệ; tỷ lệ repair thành công chỉ tính khi mẫu số > 0.
- Bao nhiêu concept hợp lệ bị mất sau review; bao nhiêu item bị thay evidence_id và thay đúng hay sai khi đọc nguồn.
- Số item lỗi còn sót trong output sử dụng, số item bị loại, fallback và F1 sau lọc.
- Số lần review lặp nguyên draft **trong nhóm draft lỗi**, thay vì coi mọi lần lặp là lỗi.

**Giả thuyết:** feedback cụ thể và validate lại giúp sửa lỗi thực sự. Chưa có số đo chứng minh mức tăng. Nếu dev có quá ít draft lỗi, chỉ báo số đếm; dùng thêm bộ ca khó từ train để kiểm chức năng, không biến tỷ lệ trên ca chọn lọc thành tỷ lệ toàn corpus.

## 5. Ưu tiên P1 — phục hồi coverage của method/contribution

### Method: một kỹ thuật hoặc một bước có vai trò độc lập

Giữ tên gọn nhưng đủ phân biệt phương pháp đang dùng. Quét từng câu để nhận diện thuật toán, model, feature group, representation, procedure và workflow. Một workflow chỉ được giữ cùng component khi nó bổ sung sequencing/decision thực sự, không chỉ lặp tên các component.

Tách nhóm rõ ràng: phương pháp tác giả dùng/phát triển; baseline chỉ để đối chiếu; background/prior work; future work. Trong nghiên cứu so sánh, kỹ thuật thực sự được chạy có thể là method; không loại mọi baseline bằng một regex chung.

Giữ cơ chế gợi ý câu chưa được trích của v1 nhưng xem đó là **ứng viên cần đọc**, không bắt mỗi câu tạo nhãn. Không chia mọi tính từ, hyperparameter hay ví dụ thành method.

### Contribution: kiểm artifact và finding thành hai lượt

- Lượt artifact: mô hình/công cụ/resource/procedure nào thực sự được giới thiệu, sửa đổi, mở rộng hoặc phát hành? Có nhiều phát triển độc lập thì không gom thành một tên chung.
- Lượt finding: phát hiện tích cực, âm/null, so sánh, giới hạn nào được báo cáo? Không lấy một câu performance thay thế toàn bộ artifact, hoặc chỉ giữ artifact rồi bỏ findings.
- Existing tool không tự động là contribution. Cần phân biệt tên công cụ có sẵn với phần tác giả đã phát triển trên công cụ đó.

Mẫu kiểm về ý nghĩa của finding, **không phải schema đầu ra mới**:

> Ai/cái gì → đạt hoặc không đạt điều gì → metric/quantity nào → so với gì → trên phạm vi nào → có điều kiện/caveat nào cần giữ?

Không trường nào bắt buộc phải được bịa thêm. Chỉ giữ thông tin có nguồn và cần để không làm đổi nghĩa. Finding có thể dài; method/resource thường cần tên compact.

### Ví dụ minh họa và giới hạn sử dụng

Phân tích test đã thấy v1 bỏ các thay đổi NWChem/FoX/Avogadro và rút kết quả patent NMT quá ngắn. Đây là **bằng chứng chẩn đoán**, không đưa các bài này vào few-shot prompt, train hay chọn cấu hình. Ví dụ cho prompt mới phải tự tạo theo nguyên tắc hoặc lấy từ train đã được rà nguồn, không sao chép test.

Đo riêng method/contribution precision và recall: chỉ tăng số nhãn không đủ; recovery phải là ý có căn cứ, không phải các mảnh từ thừa.

## 6. Ưu tiên P1 — ổn định role, granularity và qualifier

| Facet | Quy tắc cần làm rõ | Lỗi cần tránh |
|---|---|---|
| Problem | Hạn chế/câu hỏi cụ thể, gắn chủ thể và bối cảnh cần thiết | Chủ đề phổ biến; ví dụ minh họa bị tách thành problem thứ hai; nhãn chỉ còn “this/these” |
| Task | Mục tiêu vận hành/nghiên cứu chính và bối cảnh phân biệt | “Propose a model” hoặc mỗi bước annotate/train đều thành task |
| Method | Kỹ thuật thực sự được áp dụng, một đơn vị có ý nghĩa | Background model bị gán thành method; gom các kỹ thuật độc lập thành câu dài |
| Dataset | Resource có tên và thực sự dùng/giới thiệu | Ngôn ngữ, số mẫu, platform hoặc collection vô danh bị coi là dataset |
| Contribution | Artifact mới/phát triển và findings có căn cứ | Công cụ cũ thành artifact mới; mất comparator, phủ định, điều kiện hoặc quantity |

Ba việc cụ thể:

1. Ghi quy tắc tách/gộp theo đơn vị ngữ nghĩa, có ví dụ train/synthetic đúng–sai; không đặt số từ hay số nhãn bắt buộc.
2. Kiểm qualifier theo **role**. Guard finding không áp máy móc cho mọi tên artifact trong contribution. Một artifact name không nhất thiết phải mang tất cả số liệu có trong câu evidence.
3. Phân biệt “FP theo reference” với “sai nguồn”. Ghi riêng alias, granularity, reference omission và lỗi model; không dùng phân loại này để tự sửa test/matcher.

V1 hiện không có field phân biệt artifact/finding trong schema. Giai đoạn đầu có thể ghi phân loại trong audit phục vụ review; không thay interface train/inference chỉ để thêm field này. Nếu cần thay schema thật, chuyển sang vòng riêng ở mục 9.

## 7. Thiết kế pilot dev 50–100 bài

### Tập bài và reference

- Dùng 100 dev IDs hiện có, chọn trước 50 bài thử ban đầu bằng seed `20261021`, phân tầng theo nhóm reference existing/additional và corpus nếu khả thi. Phân bổ theo tỷ lệ thực tế; không ép 25/25 khi một nhóm không đủ.
- Chọn bằng metadata và seed, không chọn theo lỗi student hoặc F1. Phân bố khó/nhãn rỗng cần báo sau chọn; không đổi seed để lấy mẫu thuận lợi.
- Lưu manifest gồm IDs, source hashes, split/group và quy tắc phân bổ trước khi sinh đầu ra các arm mới.
- 50 dev còn lại dùng để kiểm lại nội bộ sau khi chọn candidate. **Cả 100 dev đã tham gia chọn checkpoint bằng loss**, nên không gọi phần còn lại là holdout độc lập hoặc bằng chứng generalization mới.
- Muốn kết luận tổng quát hóa cần bộ nguồn mới đã khóa, không trùng train/dev/test cũ hoặc pilot50 đã dùng phát triển. Đóng băng reference từ nguồn trước prediction, reviewer không xem output/điểm để sửa nhãn.
- Lượt rà AI cần ghi đúng nguồn gốc, không gắn human gold. Nếu chưa có người duyệt, báo agreement và source-review evidence với giới hạn tương ứng.

### Các arm đầu tiên

| Arm | Thay đổi so với baseline | Câu hỏi cần trả lời |
|---|---|---|
| A0 | V1 nguyên trạng: adapter, prompt 3.7, schema và review hiện có | Mốc dev thực tế là bao nhiêu? |
| A1 | Chỉ thêm feedback/repair mục tiêu và tách item lỗi khỏi output sử dụng | Có sửa được lỗi mà không làm mất ý hợp lệ? |
| A2 | Chỉ bổ sung kiểm kê artifact/finding và các ý method độc lập | Có tăng coverage method/contribution mà không tăng lỗi role? |
| A3 | Kết hợp phần đã đạt của A1 và A2 | Hai thay đổi còn có ích khi đi cùng nhau? |

Chạy A0–A1 trước; chỉ chạy A2/A3 khi có lý do và budget. Không thêm đồng thời schema mới, retraining, threshold mới hay decoder mới. Nếu thử wording/qualifier riêng, tạo arm kế tiếp sau khi đã loại hoặc chốt các arm trên.

Mọi arm có cùng cap 3 calls × 2048 output tokens/bài và cùng model/quantization. Một arm ít dùng call hơn vẫn được phép, nhưng phải báo actual calls/tokens/time. Với 50 bài, trần mỗi arm là 150 calls; bốn arm là tối đa 600 calls, không phải ETA. Quyết định arm tiếp theo từ bằng chứng, tránh chạy toàn bộ ma trận ngay từ đầu.

## 8. Cách đánh giá và tiêu chí chọn candidate

### Báo cáo bắt buộc

1. Micro/Macro F1, precision/recall và từng facet; TP/FP/FN giữ đủ bài lỗi trong mẫu số.
2. Kết quả từng nhóm reference, số bài mỗi nhóm; không chỉ báo pooled score.
3. Draft schema-valid, draft validator-valid, final validator-valid, fallback; tách output raw, output đã xử lý và item bị loại.
4. Repair success, coverage bị mất sau review và số item lỗi còn trong output được sử dụng.
5. Source review theo lỗi: role, unsupported concept, missing meaning, granularity/duplicate, negation/comparator/quantity/caveat và reference ambiguity.
6. Calls, input/output tokens, generation time và số lần bị dừng/không parse được. Không cộng thời gian các worker song song thành wall-clock.

Chấm source review với arm được che tên và thứ tự xáo trộn khi có thể. Rà tất cả ca có thay đổi method/contribution và tất cả ca repair trong pilot; nếu chỉ rà mẫu, ghi cách chọn và mẫu số. Người rà thấy nguồn, không dựa vào F1 để quyết định nhãn nào đúng.

### Gate đề xuất, chưa phải kết quả đã đạt

Các ngưỡng dưới đây là quy tắc vận hành cần khóa **trước** khi chạy; không bảo đảm power thống kê trên 50 bài.

- Nhánh coverage A2/A3: đặt mục tiêu tăng ít nhất 2 điểm phần trăm Micro F1 trên pilot; method/contribution phải cải thiện theo reference và source review không cho thấy tăng lỗi role/unsupported claim.
- Nhánh repair A1: ưu tiên sửa lỗi thật. Đặt mục tiêu sửa ít nhất 30% draft lỗi khi số ca đủ để diễn giải; nếu rất ít ca, báo số đếm và chưa kết luận tỷ lệ. Không chấp nhận item đã xác nhận sai nguồn xuất hiện như output grounded.
- Candidate không làm giảm hơn 0,5 điểm phần trăm ở Micro F1 hoặc một facet vốn ổn định mà không có giải thích source-reviewed. Đây là biên sàng lọc, không phải kết luận non-inferiority thống kê.
- Nếu bỏ item sai làm F1 giảm nhưng tăng độ đúng nguồn, ghi rõ trade-off và giữ bản như nhánh chất lượng/repair; **không tự gọi đó là bản thay thế tốt hơn toàn diện**. Cần review trước khi thay baseline.
- Khi đủ tín hiệu, chạy kiểm lại trên toàn 100 dev với candidate đã khóa; báo chênh lệch từng bài và paired bootstrap CI, không tune tiếp trên cùng kết quả rồi coi đó là xác nhận độc lập.
- Có lỗi nghiêm trọng mới làm đảo phủ định, gán sai hệ thống/metric hoặc đổi comparator thì candidate chưa đạt gate source quality, dù F1 tăng.

Không chọn candidate chỉ dựa trên dev loss. Loss token và chất lượng generation là hai phép đo khác nhau.

## 9. Khi nào mới sửa dữ liệu và train lại?

Chuyển sang vòng dữ liệu khi dev/source review cho thấy lỗi lặp có hệ thống và inference fixes không đủ: findings thường mất qualifier, methods bị gom, sai role prior work, tên resource bị bỏ hoặc phong cách nhãn không nhất quán.

Trình tự:

1. Chốt policy và schema của nhánh mới; rà train/dev từ nguồn theo policy đó. Không copy nguyên nhãn v2 vào train v1 vì hai phiên bản khác schema, granularity và coverage review.
2. Lưu nhãn cũ/mới, source evidence, lý do đổi, reviewer và tình trạng đồng thuận. Reviewer độc lập kiểm các sửa quan trọng; ca chưa rõ không được gắn “đã xác nhận”.
3. Cân bằng kiểm tra existing/additional reference, chú ý corpus ít đại diện. Có thể lấy ca khó ở train để sửa học liệu, nhưng không báo tỷ lệ lỗi trên mẫu chọn lọc như toàn tập.
4. Nếu vẫn schema v1, chỉ dùng nhãn một câu hỗ trợ đủ nghĩa. Nếu cần nhiều câu để gắn antecedent/condition, ghi hạn chế; không giả một quote ghép là một câu nguồn.
5. Nếu chuyển schema nhiều câu, tạo dataset/version và adapter mới; đồng bộ prepare/train/inference/validator/evaluator. Adapter v1 chạy với prompt schema mới chỉ là probe compatibility, không phải phép đánh giá chuẩn cho adapter đó.
6. Giữ hyperparameters v1 làm mốc trong vòng train dữ liệu mới để đo ảnh hưởng dữ liệu trước; chưa tăng epoch/rank hoặc grid-search LR cùng lúc. Chọn checkpoint từ dev và xác nhận generation theo protocol đã khóa.
7. Nếu tiếp tục train từ adapter v1 thay vì từ base, ghi thành thí nghiệm riêng. Không mặc định hai phương án tương đương.

## 10. Thứ tự triển khai đề xuất

| Bước | Việc cụ thể | Đầu ra để review | Điều kiện chuyển bước |
|---|---|---|---|
| 0 | Khóa artifact v1, manifest và protocol pilot | Hashes, IDs, bảng baseline và giới hạn | Reproduce baseline và không có split/source mismatch |
| 1 | Chuẩn hóa taxonomy lỗi, feedback và test chức năng repair | Ca train/synthetic cho wrong ID, lexical order, duplicate, qualifier và failed review | Test kiểm lỗi thật; raw/audit không bị ghi đè |
| 2 | Chạy A0/A1 trên dev50 | Bảng score, source review, repair/fallback/cost | Có cải thiện đúng nghĩa hoặc thấy rõ vì sao không đạt |
| 3 | Thử A2, rồi A3 nếu các phần hữu ích | So sánh coverage/precision của method/contribution | Không tăng unsupported/role errors; không chỉ tăng số nhãn |
| 4 | Kiểm lại candidate khóa trên dev100 | Báo cáo paired, subgroup và uncertainty | Chọn được candidate hoặc giữ v1 nếu không đạt |
| 5 | Rà dữ liệu và retrain nếu có bằng chứng cần thiết | Label provenance, dataset/model release riêng | Schema/policy thống nhất và quality checks đạt |
| 6 | Xác nhận trên nguồn mới rồi mới quyết định trích corpus | Reference khóa trước prediction, kết quả và audit | Không dựa vào test cũ đã dùng phân tích để tuyên bố bản mới thắng |

Không cần làm đủ sáu vòng nếu A1/A2 đã giải quyết mục tiêu. Nếu A0/A1 không cho tín hiệu tốt, dừng mở rộng GPU và xem lại feedback/source cases trước.

## 11. Vị trí liên quan khi triển khai sau này

Đây là bản đồ phạm vi, không phải yêu cầu sửa tất cả file:

| Thành phần hiện có | Vai trò cần xem |
|---|---|
| `data/exp_a/extraction_v3.py` | Annotate/review, assess_attempt, preserve_review_items, coverage_candidates và validation |
| `data/exp_a/prompts/extraction_v3_7.md` | Prompt v1 làm mốc; candidate dùng file/version riêng |
| `data/exp_a/finetuning/experiment.py` | Load adapter v1, predict và chấm paired |
| `data/exp_a/.kaggle/matrix/matrix.py` | Record hash/signature và score_rows |
| `data/exp_a/finetuning/label_revision_v2/schema.py` | Tham chiếu cho evidence nhiều câu ở vòng riêng |
| `scripts/exp_a/evaluate_exp_a.py` | Matcher/embedding; giữ nguyên trong vòng sửa inference |
| `scripts/exp_a/pilot/`, `scripts/exp_a/finetuning/` | Các test hiện có để chọn seam và kiểm regression liên quan |

Mỗi run tương lai cần output directory riêng: manifest/arm config, hashes, record từng bài, raw/applied output, validation errors, repair decisions, metrics và source-review ledger. Không ghi đè sealed v1 hoặc các báo cáo lịch sử.

## 12. Tài liệu bằng chứng và giới hạn

- [Kết quả v1 đã xác minh](../../../data/exp_a/finetuning/build/result_review_v1.md).
- [Đối chiếu base và adapter v1/v2](BASE_V1_V2_COMPARISON_2026-10-20.md).
- [Kết quả test v2](QLORA_V2_TEST_RESULT_2026-10-20.md).
- [Phân tích lỗi v1 dạng JSON](../../../data/exp_a/finetuning/build/error_analysis_v1.json).
- [Replay chung grounding và verification](../../../data/exp_a/finetuning/v2/build/base_comparison_common_gate_20261020/verification.json).

Tài liệu này định hướng **sửa v1 từng phần và kiểm chứng**, không khẳng định các đề xuất đã tăng điểm. Test cũ đã được mở để phân tích lỗi; dùng nó làm mô tả lịch sử, không làm tập lựa chọn bản sửa. Một reference mới theo policy mới là benchmark riêng, không đổi nhãn test cũ rồi so điểm như cùng thước đo.
