# Quản lý corpus và bàn giao dự án

[Tổng quan](../README.md) · [Chỉ mục dữ liệu](../data/README.md) · [Protocol](EXPERIMENT_PROTOCOL.md)

Tài liệu này chứa quy tắc vận hành trước đây nằm trong README gốc. Cách generator/scorer hoạt động nằm trong README từng exp.

## 1. Hợp đồng và phạm vi

Corpus canonical trong `data/processed/` là nguồn title/abstract duy nhất. Giữ paper_id ổn định, checksum và alias nguồn trong id_map. Các exp dùng năm facet problem/task/method/dataset/contribution; tên A–E theo protocol hiện hành.

Khi đổi schema, ý nghĩa nhãn, quy tắc thời gian hoặc nguồn dữ liệu, cập nhật [DATA_CONTRACT](../DATA_CONTRACT.md) và [protocol](EXPERIMENT_PROTOCOL.md), rồi để Khải review trước khi tích hợp. Config B–E nằm trong `configs/exp_*.json`; config A nằm trong `data/exp_a/config.json`; config corpus và validator nằm trong `configs/`.

## 2. Review phạm vi corpus

Bộ lọc IT là heuristic, chưa phải gold do người kiểm duyệt. Review override phải có source/source_id, include/exclude, reviewer và lý do; lưu có phiên bản trong cấu hình, rồi rebuild. Đọc scope_audit và corpus_report để kiểm tra bài ngoài phạm vi, metadata thiếu, trùng lặp và gap target.

Không chỉnh trực tiếp paper records để đổi phạm vi, xóa id_map để cấp lại ID hoặc đổi nguồn đại diện tùy tiện. Khi thêm alias, giữ primary source và ID đã cấp. Xung đột cùng tiêu đề nhưng khác abstract phải được review trước khi gộp.

Nguồn raw giữ archive, bản giải nén, giấy phép và source_manifest. SciFact URL latest được khóa bởi hash bản đã tải. Khi đổi release, giữ provenance cũ và tạo bản mới có phiên bản. Không bổ sung bài không đúng phạm vi chỉ để đủ quota.

Cách rebuild/gate: [README corpus](../data/processed/README.md). Không chạy đồng thời nhiều builder vào cùng output.

## 3. Freeze và thứ tự bàn giao

A được coi là đầu vào hợp lệ cho B–E khi có toàn bộ silver, annotation_metadata và manifest complete đúng corpus. Phần 842 bài hoàn thành vẫn là partial so với toàn corpus. Gộp bằng tool A, không lấy manifest một part làm manifest chung.

Giữ checkpoint và raw audit của A để resume; bài fallback/còn validation errors được giữ để review và bị loại khỏi pool khuyến nghị. Evidence đã nằm trong metadata của extraction hiện tại; không cần chạy lại toàn bộ chỉ để thêm evidence.

Sau khi freeze A, tạo B/C. Bàn giao C complete cùng manifest và các tệp được kiểm tra hash trước khi chạy D/E. Nếu input, config hay generator thay đổi, tạo dataset phiên bản tương ứng; không trộn nhãn từ hai lần sinh vào một manifest.

Gold A là bộ người review độc lập. Selector chỉ tạo hàng đợi pending; không copy silver thành gold hoặc ghi đè queue đã có. Đọc [review Qwen](EVALUATE_QWEN.md).

## 4. Split và chống nhìn đáp án

| Exp | Ranh giới cần giữ |
|---|---|
| A | Gold giữ riêng; loại bài P000001 đã dùng phát triển prompt |
| B | Chia theo query/anchor; ứng viên có thể xuất hiện ở nhiều split |
| C | Chỉ dùng lịch sử/search/exposure trước cutoff |
| D | Dùng prefix C và tín hiệu phiên trước cutoff; giấu intent và labels |
| E | Rolling prefix trước từng kỳ; không đọc sự kiện của kỳ đang chấm |

Query trước exposure và phản ứng phải giữ đúng thời gian/quan hệ liên kết. Không coi mọi bài đã hiển thị nhưng chưa phản ứng là dislike. Với D, oracle là comparator đặc quyền do evaluator tạo; không truyền intent thật vào scorer nghiên cứu.

TF-IDF baseline B dùng văn bản toàn corpus không có nhãn: đây là thiết lập transductive. Nếu nghiên cứu mô hình cần học tham số, ghi rõ dữ liệu fit/tune và giữ split/cutoff. Ground truth sinh từ silver vẫn có bias chung với phương pháp facet; split đúng không loại hết bias đó.

## 5. Kiểm tra và nghiệm thu

Từ gốc dự án:

```powershell
python scripts/validate_all.py --dataset-kind real --phase corpus
python scripts/validate_all.py --dataset-kind real --phase experiments
python scripts/validate_all.py --dataset-kind mock --phase experiments
python -m unittest discover -s tests -v
```

Validator A toàn corpus khác validator part/pilot có allow-partial. B–E validate theo các config đầu vào; xem [lệnh từng bước](RUN_EXPERIMENTS.md). Ghi lại output thực tế trước khi kết luận đủ điều kiện chạy.

Một bàn giao có thể tái lập cần code/config/docs, input có hash và provenance, manifest complete, số lượng thực tế, quy tắc labels, split/cutoff, seeds và giới hạn chất lượng. Fixtures/tests kiểm tra logic, không thay thế việc chạy trên dataset thật.

[VALIDATION_STATUS](VALIDATION_STATUS.md) là snapshot có ngày ghi nhận. Kết quả test thành công không tự chứng minh có dataset B–E, gold A đã review hoặc chất lượng model đủ tốt.

## 6. Git và dữ liệu lớn

Commit code, tests, configs và tài liệu. Trước khi bàn giao, kiểm tra .gitignore: môi trường Python, model/cache, checkpoint, kết quả sinh và báo cáo lớn thường được bỏ qua. Raw/processed được phép commit/push theo quy ước dự án hiện tại. Generated/ground_truth của A–E, kể cả samples, giữ trên máy và được .gitignore bỏ qua; giữ giấy phép/attribution khi chia sẻ.

Dữ liệu được bàn giao ngoài Git phải đi theo **trọn bộ manifest và các tệp nó tham chiếu**. Không sửa/xóa dữ liệu gốc chỉ để làm sạch working tree. Giữ nhánh thay đổi rõ mục đích, review diff trước khi tích hợp; không force-push làm mất công việc thành viên.

Các kế hoạch data-first cũ là tài liệu lịch sử, không phải xác nhận nhánh/dataset đã được tạo. Trạng thái hiện hành lấy từ manifest, code và validation snapshot.

## 7. Nguồn và phạm vi kết luận

Giữ attribution và giấy phép từ [CSFCube](https://github.com/iesl/CSFCube/releases/tag/v1.1) và [SciFact](https://github.com/allenai/scifact); chi tiết release/checksum nằm trong [raw](../data/raw/README.md). Dùng title/abstract từ nguồn không đồng nghĩa dùng benchmark relevance ba facet CSFCube cho hệ năm facet.

Phần khuyến nghị hội nghị/conference C4 thuộc phạm vi đề tài, nhưng chưa có thực nghiệm riêng trong A–E. Hướng đề xuất là đối chiếu facet của bài viết hoặc profile nghiên cứu với hồ sơ chủ đề conference để xếp hạng và giải thích mức phù hợp. Cần chốt đầu vào/nhãn/đánh giá trước khi đặt tên thực nghiệm và triển khai. B–E hiện kiểm tra khuyến nghị bài báo trên dữ liệu mô phỏng; điểm của chúng chưa kiểm chứng C4.

Đọc [kế hoạch A–E](EXPERIMENT_PLAN_FINAL.md) và [ghi chú nghiên cứu](FACET_RECOMMENDATION_RESEARCH.md) để biết hướng encoder/profile/intent/temporal tiếp theo. README runner phải nói rõ model nào đã có và model nào mới là đề xuất.

## 8. Tài liệu vận hành liên quan

- [Phạm vi IT và override](IT_SCOPE.md), [báo cáo ingestion](INGESTION_REPORT.md).
- [Đo thời gian generator](GENERATOR_TIMING.md): các phép đo có ngày, không phải tiến độ live.
- [Bàn giao data-first](DATA_FIRST_REFERENCE.md): kế hoạch lịch sử, đối chiếu protocol hiện hành.

Data-first release đầy đủ cần corpus đã review scope/dedup/provenance, dataset A–E
hợp lệ và gold thật đã review nếu báo cáo chất lượng extraction. B–E chạy mock
không cần chờ human gold; báo cáo phải giữ rõ giới hạn synthetic.

Venue metadata nguồn có thể thiếu/không đồng nhất, chưa phải đáp án conference phù hợp
cho bài mới. Triển khai C4 cần mục tiêu, catalog/IDs conference, phạm vi IT, hồ sơ chủ đề
và relevance ground truth riêng trước khi chốt schema/split/evaluation. Nếu dùng các bài
đã công bố để xây hồ sơ conference, chỉ dùng thông tin có trước mốc đánh giá; không đưa
chính bài đang được chấm hoặc dữ liệu tương lai vào hồ sơ. Baseline dự kiến so biểu diễn
toàn văn với biểu diễn theo facet trên cùng tập conference ứng viên. Đây là thiết kế đề xuất,
chưa phải pipeline đã triển khai hoặc kết quả đã được kiểm chứng.
