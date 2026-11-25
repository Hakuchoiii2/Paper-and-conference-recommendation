# Ưu tiên chất lượng nhãn — pilot 40 / quy tắc v2.2 candidate, 2026-10-18

Đã thực hiện bước quy tắc và pilot 40 bài theo yêu cầu. Chưa mở rộng 667 bài
hoặc trích lại corpus: cần mẫu kiểm chứng train/dev mới cho các quy tắc vừa làm rõ sau pilot, cùng
quyết định về ba đầu vào còn thiếu thông tin/scope trước khi coi quy tắc ổn định. Nhãn là AI reference; human review pending.

## Quy tắc và schema

- [Quy tắc v2.2 candidate](policy_v2_2.md): vai trò facet, tách/gộp, tên/viết tắt,
  finding giữ điều kiện/phủ định, phân biệt phương pháp nền và cách thực sự dùng.
- [Prompt v2.2 candidate](prompt_v2_2.md), [JSON schema](response_schema.json),
  [validator và grounding](schema.py).
- Mỗi item v2.1 có `concept` và `evidence_ids`, ví dụ
  `{"concept":"ORBIT improves recall by 12% on noisy queries","evidence_ids":["A0","A1"]}`.
  Đây là ví dụ giả lập. Danh sách ID không rỗng, không trùng, theo thứ tự nguồn;
  một câu vẫn dùng danh sách một phần tử. Sidecar giữ từng câu nguyên văn.
- Kiểm tra schema/từ nguồn không chứng minh entailment, đúng vai trò hay đồng tham
  chiếu. Reviewer phải đọc nguồn, giữ điều kiện và không ghép các câu không liên quan.
- Bản v2.0 trước khi người dùng yêu cầu nhiều evidence được giữ nguyên cùng hash.
  `prepare/train` và prompt/schema v1 chưa chuyển sang định dạng mới. Không nạp
  file v2.1 vào pipeline v1 hoặc dùng adapter v1 như thể đã được train bằng v2.1.

## Mẫu và cách tránh bị nhãn cũ dẫn dắt

| Split | Nguồn nhãn có sẵn | Nguồn nhãn bổ sung | Tổng |
|---|---:|---:|---:|
| Train | 10 | 10 | 20 |
| Dev | 10 | 10 | 20 |

37 CSFCube + cả 3 SciFact hiện có trong train/dev; seed 20261018. Mẫu không chọn
bằng nhãn, dự đoán hoặc lỗi student. Việc đưa cả SciFact vào là chủ đích tăng
đại diện nguồn hiếm, nên không dùng kết quả làm ước lượng tỷ lệ lỗi toàn corpus.
Không trùng ID/title/source với 100 bài test hoặc pilot50.

Lượt đầu của `/root` chỉ xem source/evidence, lưu đủ 40 bản trích và hash trước khi
mở targets cũ. Lượt đối chiếu sau đó cho phép cả bản mới và nhãn cũ sai: các mục cũ
hợp lệ bị lượt blind bỏ sót đã được phục hồi. Sau khi người dùng chọn nhiều câu
evidence, bản đối chiếu được chuyển sang schema v2.1; không gọi đó là lượt blind
mới dưới v2.1. Một reviewer AI ở context mới đã trích lại đủ 40 nguồn theo v2.1, khóa hash
riêng trước khi mở bản đối chiếu, rồi đọc và quyết định đủ 200 facet. Sau sửa,
reviewer kiểm tra lại và chấp nhận bản 345 nhãn; không còn bất đồng ngữ nghĩa
trọng yếu trong lượt kiểm tra này. Hai quy tắc làm rõ thành v2.2 cần được kiểm
chứng mới, không được coi như đã áp dụng từ đầu vào lượt blind v2.1.

## Kết quả cuối sau rà chéo AI

- 200 facet đã được so sánh; 354 concept cũ → 315 concept ở lượt đầu → 337 concept
  trong bản tự đối chiếu v2.1 → 345 concept sau rà chéo và sửa.
- 108/200 facet có thay đổi về nhãn hoặc evidence: problem 20, task 24,
  method 30, dataset 2, contribution 32. Đây là số khác biệt biểu diễn/dẫn chứng,
  **không phải 108 lỗi ngữ nghĩa**, cũng không phải accuracy hay điểm F1.
- 24 nhãn dùng nhiều câu để giữ chủ thể, scope, finding và điều kiện.
- Rà độc lập ban đầu: 174 facet chấp nhận, 21 facet trọng yếu cần sửa/bổ sung
  evidence hoặc chốt quy tắc, 5 góp ý độ chi tiết. 25 facet được cập nhật sau
  rà chéo; hai quyết định policy có thể giữ cùng nhãn nhưng cần định nghĩa rõ.
  [Kết quả kiểm tra lại cuối](pilot40/independent_review/final_acceptance.json)
  xác nhận không còn bất đồng ngữ nghĩa trọng yếu ở pilot đã sửa.
- Cách viết artifact có thể rất ngắn; finding giữ đủ điều kiện có thể dài.
  Không ép số nhãn hay số từ bằng nhau giữa bài hoặc giữa nguồn.

Các mẫu thay đổi đáng chú ý: finding chỉ còn “higher response rates” cần giữ
đối chứng và mức `suggest/may`; kết quả parser phải giữ `when starting from valid
symbols`; UCI là nơi chứa Landsat, không thêm dataset thứ hai; baseline siRNA và
reflexive diary chỉ được khuyến nghị không tự trở thành method đã thực hiện.

Đọc [sổ đối chiếu từng bài/facet](pilot40/ADJUDICATION.md) hoặc
[quyết định dạng JSONL](pilot40/facet_decisions.jsonl). Bản cuối sau rà chéo đang ở
[pilot40/adjudicated_annotations.jsonl](pilot40/adjudicated_annotations.jsonl),
[kèm từng câu evidence](pilot40/review_evidence.jsonl). Các tên alias có căn cứ
chỉ được ghi theo từng source; matcher toàn cục không thay đổi.

## Nguồn và các quyết định cần kiểm tra

5 ca được flag ban đầu, trong đó 2 đã xác minh/giải quyết và 3 còn quyết định
về input/scope; [xác minh nguồn](pilot40/SOURCE_VERIFICATION.md) và
[sổ việc còn chờ](pilot40/source_confirmation_pending.jsonl) ghi chi tiết:

- P003168: full text xác nhận dùng BioProp, nhưng title/abstract chỉ nêu availability.
  Nhãn trích từ abstract không được thêm PropBank hoặc chi tiết chỉ có full text.
  Finding 97% bị tạm bỏ vì input không nêu mẫu số/comparator; vẫn giữ câu gốc ở audit.
- P000271: input là đoạn mở đầu, thiếu phần mô tả computer test thực sự.
- P001234: chính abstract nguồn ghi OpenStreatMap; body dùng OpenStreetMap. Giữ
  input/raw label, ghi xác minh riêng thay vì tự sửa tên trong dữ liệu v1.
- P000779: catalog xác nhận đây là sách; cần quyết định eligibility/scope cho v2.
- P004191: full text xác nhận model tốt nhất thuộc hybrid được test accuracy 0.80;
  reviewer đã kiểm tra và chấp nhận liên kết A9+A10 trong input; không thêm chi tiết ngoài abstract.

## Kiểm chứng và bảo toàn v1

88 test dự án + 36 test fine-tuning, gồm 8 test schema mới: PASS khi TEMP/TMP
trỏ thư mục tạm trong workspace. Lần chạy đầu dùng Windows sandbox TEMP bị
PermissionError; log lỗi và log chạy lại đều giữ trong pilot40. Không sửa mã
hiện tại để che lỗi môi trường.

Validator đã đọc đủ 40 bài/345 nhãn, kiểm tra shape, evidence IDs, thứ tự từ,
quote mapping, đủ 200 quyết định và không overlap test/pilot50. Thư viện
`jsonschema` không có trong venv; xác thực dữ liệu dùng validator Python của v2.1,
không tuyên bố đã chạy validator JSON Schema bên ngoài.

Prompt v2.2 + schema + input/output của 40 bài đã kiểm token bằng tokenizer
local của adapter v1: tối đa 2522/4096 token mỗi sequence và 486/2048 token
completion, không truncate. Đây là kiểm ngân sách token, chưa chạy inference
hoặc train adapter v2. Xem [token_budget_v2_2.json](pilot40/token_budget_v2_2.json).

38 file v1 được kiểm hash không thay đổi, gồm train/dev/test, nhãn/evidence,
corpus hiện hành, adapter và điểm gốc. Điểm micro F1 gốc 47.44 → 59.28 ở threshold
0.85 là kết quả v1; chưa có điểm mô hình mới từ pilot này. Xem
[validation_report.json](pilot40/validation_report.json) và
[CODE_REVIEW.md](pilot40/CODE_REVIEW.md).

## Điều kiện mở rộng

1. Hoàn tất: hai lượt source-first, đối chiếu 200 facet và review lại bản sửa.
   Ba ca input/scope còn cần quyết định version nguồn.
2. [Quy tắc được làm rõ](POLICY_CLARIFICATIONS.md): survey chỉ giữ procedure
   thực sự làm; comparative experiments giữ techniques thực sự chạy; demonstration
   cần ví dụ/cách vận hành. Ontology có tên có thể là structured knowledge resource.
   Cần mẫu train/dev chưa dùng cho policy v2.2 trước rollout.
3. Nếu phải đổi quy tắc ngữ nghĩa, lưu version mới và thử train/dev chưa dùng;
   không đánh dấu stable chỉ từ pass test hoặc đồng thuận chữ.
4. Khi đạt, rà toàn bộ 667 ID thành phiên bản riêng, không đảo split. Nhãn test
   v2 là benchmark mới; người sửa chỉ thấy nguồn/quy tắc, không thấy predictions
   hay điểm từng bài. Giữ test v1 và điểm v1 nguyên vẹn để so sánh.
5. Sau đó khóa adapter/prompt/schema rồi trích lại corpus. Ưu tiên review evidence
   sai, thiếu facet và bất đồng; không chạy trước khi nhãn tham khảo đã đủ ổn định.
