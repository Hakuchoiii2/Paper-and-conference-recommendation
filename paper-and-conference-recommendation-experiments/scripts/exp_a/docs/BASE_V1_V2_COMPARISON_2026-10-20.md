# Base v1 và v2 — đối chiếu 100 bài, 20/10/2026

## Kết luận

Pipeline v1 hiện tốt hơn pipeline v2 trên cùng 100 bài và cùng AI reference. Hai base là cùng Qwen/Qwen3-8B, cùng revision; đây không phải hai bộ trọng số base khác nhau. Đổi prompt/schema/review/fallback làm thay đổi kết quả. V2 có cải tiến về vai trò, evidence nhiều câu và giữ điều kiện; chưa có bằng chứng để thay toàn bộ v1 bằng v2.

Không chạy lại inference/pilot hoặc upload Kaggle. Tái sử dụng đủ 400 record đã sinh (100 cho mỗi base/adapter), kiểm SHA-256/signature/ID, chấm lại bằng một bộ embedding offline trên RTX 4060. Cả bốn bộ TP/FP/FN được tái tạo đúng kết quả lịch sử. Đây là so sánh pipeline trên test đã có, không phải pilot mới hoặc ablation chỉ đổi một biến.

## Cơ sở đối chiếu

- Test IDs, source hash, reference hash, base model/revision đều giống nhau; test không giao train/dev.
- Reference hash: `924983ac81f4c1036d01b105ad925be00843a8848c901e9d546c144bc521eba9`.
- Greedy, 2048 token/call ở cả hai. V1 cho tối đa 3 lượt, thực tế base 271 calls; v2 tối đa 2 lượt, thực tế base 200 calls.
- Cùng Qwen3-Embedding-0.6B/revision/hash weights, source-aware matcher và threshold 0.85.
- V1: instruction prompt 3.7 có ví dụ, evidence_id một câu, review có gợi ý câu chưa trích, giữ nhãn method/contribution hợp lệ khi merge, lọc named resources.
- V2: prompt 2.2 không có ví dụ tương đương, evidence_ids nhiều câu; review tổng quát, chọn một attempt và lọc từng item grounding. Validator v2 kiểm structure/word order, không tái dùng đầy đủ các guard qualifier/quantity/negation/resource của v1. Không nên gọi v2 là chặt hơn trên mọi phương diện.

## Thực nghiệm replay

| Phép đo Micro F1 | Base pipeline v1 | Base pipeline v2 | Adapter v1 | Adapter v2 |
|---|---:|---:|---:|---:|
| Đầu ra pipeline đã công bố | 47.44 | 26.52 | 59.28 | 47.02 |
| Raw attempt đã được chọn, trước xử lý (*) | 47.07 | 32.19 | 59.88 | 46.49 |
| Cùng bộ grounding v2 (**) | 44.98 | 26.52 | 59.69 | 47.02 |

(*) Raw chỉ đo agreement để chẩn đoán; vẫn có item sai evidence, role, schema/grounding. Không được dùng điểm raw làm chất lượng triển khai hoặc khuyến nghị bỏ lọc. JSON không parse được giữ bài trong mẫu số với dự đoán rỗng. Đây là raw của attempt được pipeline chọn, không phải cùng một draft hay cùng số lượt gọi.

(**) Chuyển evidence_id v1 thành evidence_ids một phần tử, giữ nguyên concept và nguồn; chạy assess_new/ground_response v2 rồi cùng matcher. Không thêm từ, sửa nhãn hay tái sinh. V2 replay khớp chính xác nhãn đầu ra gốc ở cả hai arm. Cổng này chỉ kiểm grounding/shape, không phải một semantic policy thống nhất. Đầu ra v1/v2 vẫn được sinh dưới prompt/review/budget khác nhau; không chứng minh nhân quả riêng cho prompt, số lượt hay schema.

Điểm chính: raw base v2 đã thấp hơn v1 (32.19 so với 47.07), nên lỗi không chỉ nằm ở hậu xử lý. Áp cùng grounding vẫn còn khoảng cách 18.46 điểm (44.98 so với 26.52).

## Grounding, độ phủ và review

| Chỉ số / 100 bài | Base v1 | Base v2 | Adapter v1 | Adapter v2 |
|---|---:|---:|---:|---:|
| Số nhãn raw đã chọn | 863 | 765 | 837 | 733 |
| Số nhãn cuối | 819 | 351 | 824 | 715 |
| Calls | 271 | 200 | 212 | 200 |
| Fallback | 69 | 96 | 9 | 15 |
| Selected validator-valid | 31 | 4 | 91 | 85 |
| Review đầu tiên lặp nguyên draft | 58 | 28 | 79 | 96 |
| Số từ trung bình / nhãn cuối | 8.8 | 8.36 | 5.27 | 13.85 |

Base v2 mất 414 item do không theo từ/thứ tự nguồn; 765 raw → 351 giữ lại. Với cùng kiểm tra item v2, raw base v1 có 663/863 item đạt (sau deduplicate còn 662), base v2 có 351/765 đạt. V1 fallback vẫn có thể giữ item được báo lỗi lexical: 31/100 bài validator-valid không có nghĩa chỉ 31 bài được chấm. Đây là lý do phải báo cả agreement và grounding.

Adapter v2 có 15 draft không hợp lệ; cả 15 được review lặp nguyên văn và không draft lỗi nào được sửa thành final hợp lệ. Adapter v1 cũng sửa 0/9 draft lỗi; 6/9 được review lặp lại. Do đó review cần cải thiện cho cả hai, đặc biệt không thể coi lượt review thứ hai là bảo đảm sửa lỗi. Draft đúng có thể được giữ nguyên hợp lý; tỷ lệ lặp tự nó không chứng minh sai.

V2 adapter dài hơn rõ: 13.85 từ/nhãn cuối, v1 5.27. Không được ép tất cả nhãn ngắn: findings phải giữ điều kiện, còn method/resource cần đơn vị độc lập rõ ràng.

## Đọc nguồn: v1 thiếu gì, v2 được và mất gì

Các ví dụ sau được đọc title/abstract và cả bốn output. Chọn nhằm chẩn đoán, không phải mẫu blind hay ước lượng tỷ lệ lỗi toàn tập.

- **P004079 — patent NMT:** v1 adapter rút finding thành “substantial improvement of up to 3.1 BLEU points”, mất RIBES, đối chứng và phần so sánh NMT. Evidence SMT chọn A3 về unknown token, không hỗ trợ SMT. V2 giữ bối cảnh Japanese–Chinese, hai cặp BLEU/RIBES và hai đối chứng; đây là cải thiện có căn cứ nguồn dù nhãn dài hơn. V2 vẫn fallback ở bài này, nên nghĩa tốt hơn không đồng nghĩa toàn record đã hợp lệ.
- **P000566 — NWChem/FoX/Avogadro:** v1 adapter chỉ giữ vài tên artifact, bỏ nhiều thay đổi cụ thể: sửa NWChem, mở rộng FoX, dictionary entries, mở rộng Avogadro. V2 khôi phục các phát triển này. Tuy nhiên method v2 còn dài/gộp, và “CML CompChem” ở dataset cần người duyệt vai trò, không mặc định mọi XML convention/framework là dataset.
- **P003080 — Wizard of Wikipedia:** v1 adapter gán sequence-to-sequence models (được nêu như hạn chế của prior work) vào method, thiếu resource trong dataset. V2 loại background method đó và có Wizard of Wikipedia trong dataset. Nhưng method retrieval/reading/conditioning/generation bị gộp; problem “few convincing demonstrations of this to date” vẫn có “this” không rõ nếu đứng một mình dù word-order validator qua.
- **P001494 — FRENK:** v1 giữ nhiều procedure độc lập; v2 có nhãn resource rõ hơn nhưng bỏ analysis of annotation distributions/inter-annotator agreement và gộp sampling/schema. Cả hai có task phrasing đáng rà lại: thao tác annotate trong nguồn không tự động là mục tiêu nghiên cứu chính.
- **P001117 — CLIR:** reference tách mismatching query terms, lexical ambiguity, untranslated terms; v2 giữ cả câu gom ba nguyên nhân và một câu poor performance. FP/FN ở đây có phần do khác granularity; không thể coi mọi FP là thông tin bịa.
- **P001868 — DeepCopy:** v2 thêm chủ thể neural sequence-to-sequence models và các điều kiện vào hai problem có nguồn hỗ trợ, trong khi reference là hai cụm ngắn. Điều này làm giảm agreement nhưng không đủ chứng minh v2 sai nghĩa. Vẫn cần kiểm tra việc nối nhiều câu có giữ thứ tự và antecedent đúng.
- **P003602 — Semantic Hilbert Space:** v2 giữ cả limitation semantic linearity và ví dụ ivory tower như hai problem. Ví dụ hỗ trợ limitation, chưa chắc là một problem độc lập: cần tránh nhãn giải thích trùng ý.

## Ưu tiên cải thiện

1. **Giữ v1 làm mốc hiện tại.** Pipeline v1 tốt hơn ở cả đầu ra gốc và replay chung grounding; chưa thay adapter chỉ vì v2 có dev loss thấp hơn. Không gọi v1 là human-validated hoặc mọi nhãn v1 đều đúng.
2. **Mang phần vận hành tốt của v1 sang một thử nghiệm dev:** ví dụ chép nguồn đúng/sai, inventory từng facet, gợi ý câu chưa trích, bảo toàn item nguồn hợp lệ khi review; cho repair bổ sung khi có lỗi cụ thể. Chưa chứng minh riêng từng thay đổi tăng F1, cần ablation cùng budget trên dev.
3. **Giữ cải tiến policy v2:** evidence nhiều câu tối thiểu, phân biệt prior-work/baseline với method đang dùng, findings giữ scope/comparator/metric/caveat. Tránh quay về nhãn quá ngắn của v1 để chỉ tăng agreement.
4. **Sửa cơ chế repair:** yêu cầu sửa item lỗi cụ thể và đối chiếu nguồn, xác nhận lỗi thực sự hết; đo riêng draft-invalid → final-valid và coverage bị mất. Không lặp thêm lượt tự rà giống hệt chỉ để đủ số lượt. Không nới grounding để giữ paraphrase chưa được hỗ trợ.
5. **Chuẩn hóa đơn vị nhãn trong train/dev:** method/resource compact độc lập; finding đủ chủ thể/đối chứng/điều kiện; không gom 3 methods thành một câu, không tạo thêm problem từ ví dụ minh họa, không duplicate parent/child. Rà độc lập các nhãn v2 chưa được review.
6. **Giữ kiểm tra chất lượng nhưng áp đúng role:** quantity/negation/caveat cho finding; không áp máy móc cho mọi artifact trong contribution. Replay guard v1 đã gắn cờ TACRED dataset vì câu evidence chứa 119,474 examples — đây có thể là false positive đối với artifact name, không phải lý do xóa TACRED.
7. **Đánh giá ngữ nghĩa theo policy đã chốt:** reference hiện là AI theo policy cũ. Một benchmark v2 cần trích nhãn từ nguồn, reviewer không nhìn prediction/điểm, báo song song với benchmark v1. Không sửa test cũ/matcher/threshold theo các ca vừa xem.

Nếu triển khai cải tiến, dùng pilot dev 50 bài được khóa trước (cân bằng reference groups), cùng model, decoder, max attempts/tokens và evaluator. Đổi từng yếu tố prompt/repair/schema trong các arm riêng; chọn trên dev, rồi xác nhận trên bộ nguồn chưa dùng. Phân tích test hiện tại chỉ dùng để mô tả lỗi; không lấy các bài này làm ví dụ train/prompt hoặc điểm chọn bản sửa.

## Artifact và giới hạn

- Script: `data/exp_a/finetuning/v2/build/compare_base_versions_20261020.py`.
- JSON tổng hợp và 12 báo cáo scoring: `data/exp_a/finetuning/v2/build/base_comparison_common_gate_20261020/`.
- Embedding vectors được lưu để tái dùng, không phải model weights mới. 400 record đầu vào được hash trước và kiểm lại sau phân tích: không thay đổi.
- Không training/inference mới, không publish, không thay prompt/schema/labels hoặc automation. Chỉ chạy lại embedding/scoring offline.
- Không tuyên bố causal effect của từng thành phần hoặc accuracy với human gold. Các score raw/common-grounding là phép replay chẩn đoán, không phải một run inference kiểm soát mới.
