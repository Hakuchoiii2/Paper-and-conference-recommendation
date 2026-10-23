# Pilot50 v3.7 — bổ sung coverage và bảo toàn bản sửa review

**Cập nhật sau chạy:** kernel9 đã COMPLETE, đủ50 bài, hash/audit replay qua.
Micro-F1 **54,27%**, macro **56,21%**; method/task tăng nhưng contribution/
problem/dataset giảm. Xem [đánh giá output và lỗi còn lại](KAGGLE_PILOT50_V3_7_EVALUATION_2026-10-16.md).
Các mục dưới ghi trạng thái và kiểm tra tại thời điểm chuẩn bị/push.

Đã push **kernel version 9**, Kaggle CLI xác nhận **RUNNING**. Source tải lại
khớp SHA-256 bản gửi; metadata xác nhận private, GPU/Internet bật và cấu hình
NvidiaTeslaT4. Hai worker, cùng50 ID, output riêng
`data/exp_a/generated_v3_7_pilot50/`; không resume output cũ. Chưa có điểm mới
hoặc log runtime để xác nhận tên hai GPU thực tế.

## Thay đổi

- Method/contribution luôn được review, kể cả list rỗng và không có lỗi lexical.
  Task ngoài scope vẫn giữ nguyên nếu không có lỗi; problem/dataset giữ hướng3.6.
- Giữ item draft qua validator khi review bỏ sót; nhận bổ sung có evidence.
  Khi cùng evidence sentence, nhãn mở rộng có đầy đủ các từ cũ theo đúng thứ tự
  thay cho nhãn ngắn; review rút ngắn không làm mất điều kiện đã có. So sánh
  ordered subsequence, không dùng tỷ lệ mật độ từ để quyết định containment.
  Item draft lỗi được phép sửa; raw review sai schema không được che bằng merge.
  Duplicate/error trong review vẫn được ghi và không được âm thầm xóa để pass.
- Rà nguồn từng câu cho kỹ thuật/feature/procedure, artifact được giới thiệu
  và finding âm. Review nhận thêm các evidence ID có cue nhưng chưa được cite
  ở facet tương ứng. Đây là ứng viên cần đọc, không phải yêu cầu sinh nhãn;
  background/prior work hoặc sai vai trò vẫn phải bỏ qua.
- Giữ ngân sách3 generations, greedy decoding, seed42, Qwen3-4B/revision/NF4,
  guideline3.1, dataset filter và công thức scoring/ranking3.6. Không chèn
  ID/đáp án pilot hoặc nhãn reference vào prompt.
- Prompt3.7, engine3.8; audit ghi `coverage_preserving_v3_7` cùng raw/applied
  output và scope. Legacy3.1–3.6 giữ behavior khi replay; chỉ các generator/
  protocol hash đã xác định được migrate, không resume3.6 làm3.7.

## Bằng chứng trước push

**178 test qua:88 project +90 exp_A**, gồm13 test3.7. Đã xem test thất bại
trước sửa cho bảo toàn item/điều kiện, inserted-word expansion, duplicate errors,
malformed facet và duplicate chứa evidence ID hỏng. P002586 dùng raw thật3.6:
review2 giữ `semi-supervised training`, `speaker adaptation`, Tamil và điều
kiện test data/training data, thay vì bị scope loại; applied output replay qua.

Test dual-T4 chạy export/merge/resume3.7 với fake inference, không chứng nhận
chất lượng model. Sáu version cũ replay đủ50 bài mỗi bản. Corpus/reference/
evaluator và output cũ khớp snapshot; config mới chỉ đổi output_dir/prompt/
prompt_version. Bundle13 file không có reference, baseline hoặc output cũ.

Rà độc lập đã tìm hai lỗi biên trong merge mới (inserted-word expansion và
duplicate evidence ID hỏng); đã tái hiện, sửa và kiểm lại. Không còn blocker
trước push. Source/kernel/bundle được kiểm hash lại sau push thực tế.

## Giới hạn và đánh giá sau chạy

Bảo toàn item theo lexical support vẫn có thể giữ nhãn sai vai trò hoặc nhãn
gộp quá rộng; containment không chứng minh tương đương nghĩa. Coverage cues
không bảo đảm tìm đủ artifact/method/finding. Các ý không có trong bất kỳ raw
attempt3.6 nào cần run sinh mới để đo; test không chứng minh chúng đã phục hồi.

Sau COMPLETE, kiểm đủ50 ID, hash/replay và chấm cùng reference AI v1/evaluator/
ngưỡng0,85. Báo cả micro/macro và từng facet. Rà riêng method rỗng, artifact
JTV/TARN/MCMM, negative BLEU finding, qualifier và số nhãn dư do preservation.
Mốc3.6:micro53,8462%, method58,30%, contribution48,25%, dataset80,00%.

[Xác minh push/kernel9](../../../data/exp_a/.kaggle/review/pilot50_v3_7_push_verification.json) ·
[Chẩn đoán ưu tiên trước sửa](archive/README.md)
