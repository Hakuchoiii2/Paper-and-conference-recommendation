# Các bước hoàn thành thí nghiệm D

Ngày lập: 2026-10-15, múi giờ Asia/Saigon.

**Chỉ tạo/sửa file trong `data/exp_d/`.** Được đọc và chạy công cụ bên ngoài để kiểm tra, nhưng mọi output chủ động tạo phải nằm trong D. Không sửa A, C, corpus, config hoặc helper/runner dùng chung ngoài D.

Tài liệu giải thích: [Understand_D.md](Understand_D.md). Trạng thái thực tế: [progress.md](progress.md). Lịch sử thay đổi: [changed.md](changed.md).

## Bước 0 — Chỉ chốt những quyết định thiết kế cần bạn

Không yêu cầu bạn hoàn thành các bài tập đọc/tự audit trước khi tiếp tục. Công cụ sẽ tự đọc code, chẩn đoán và xử lý kỹ thuật thường lệ. Audit bổ sung để sau theo yêu cầu.

- [ ] Khi phải đổi protocol, nhãn, cách matching hoặc phạm vi câu hỏi nghiên cứu: báo bạn ngay, giải thích lựa chọn và chờ bạn chốt trước khi sửa phần phụ thuộc.
- [ ] Trước khi triển khai phương pháp nghiên cứu mới ở bước 4: chốt một giả thuyết cải tiến và phép so tương ứng với bạn, dựa trên lỗi baseline thực tế.

**Quyết định đang chờ ở bước 2:** matching theo exact concept overlap hiện không cung cấp đủ hai cặp cho bất kỳ tổ hợp nào trong corpus đã lọc. Cần chọn giữa thiết kế matching ngữ nghĩa trong D, bổ sung dữ liệu giữ protocol, hoặc pilot search-only có giới hạn. Chưa tự chọn và chưa đổi nhãn/ngưỡng.

## Bước 1 — Xác nhận và giải quyết đầu vào

**TRẠNG THÁI MỚI NHẤT: HOÀN THÀNH trong workspace riêng ngày 2026-10-15.** Đã chốt dùng `data/exp_d/workspace/`, không sửa checkout chung. A complete handoff, C validate, D validate và D runner dry-run đều exit 0; 47/47 checksum checks khớp, không có file được theo dõi thay đổi trong audit. Những mô tả lỗi nguồn phía dưới được giữ làm lịch sử, không còn là blocker khi chạy trong workspace.

Xem [hướng dẫn workspace](workspace.md), [nhật ký snapshot](../audit/workspace_snapshot.json), [audit workspace](../audit/step1_workspace_audit.md) và [JSON đầy đủ](../audit/step1_workspace_audit.json). Workspace là snapshot không tự đồng bộ; thay đổi D ở các bước sau phải xác định rõ phiên bản đang chạy và ghi provenance.

- [x] Chạy lại validator D và runner dry-run để ghi nhận lỗi hiện tại.
- [x] Đối chiếu hashes của input, output và generator trong manifest; phân biệt khác biệt xuống dòng với thay đổi nội dung.
- [x] Ghi danh sách file ngoài D không hợp lệ để chuyển người phụ trách dữ liệu/hạ tầng.
- [x] Tạo bản sao đầu vào trong workspace riêng, khôi phục LF chỉ cho hai bản sao và kiểm tra lại A → C → D.
- [x] Xác nhận validator và runner dry-run đều pass trong workspace riêng.
- [x] Xác nhận 69 file nguồn được sao chép giữ nguyên hash; không sửa manifest hoặc bỏ validator.

Lệnh kiểm tra mới từ gốc `paper-and-conference-recommendation-experiments`:

```powershell
python -B data/exp_d/audit/audit_step1.py --root data/exp_d/workspace --report-prefix step1_workspace_audit
```

Không sửa checksum hoặc bỏ kiểm tra để làm chương trình pass. Nếu lỗi thuộc A/C/corpus/code chung, ghi rõ phụ thuộc và tiếp tục phần chẩn đoán D độc lập; không tự vượt phạm vi sửa file.

**Hoàn thành khi:** đầu vào được validator chấp nhận và runner dry-run pass. Hash tự đối chiếu khớp chưa thay cho validator đầy đủ.

**Lịch sử audit nguồn trước khi chọn workspace (đã được xử lý bằng snapshot):** lúc đó hoàn thành ba mục kiểm tra; hai mục cuối chưa đạt. A báo `Output provenance changed`; C/D và runner D báo checksum corpus không khớp. Hai file ngoài phạm vi D cần nhận lại đúng bytes LF là `data/processed/papers.jsonl` và `scripts/build_corpus.py`. Chưa thay đổi chúng, chưa gửi thông báo cho người khác và không bỏ kiểm tra. Xem [báo cáo bước 1](../audit/step1_audit.md) và [hash/log chi tiết](../audit/step1_audit.json). Kết luận chưa hoàn thành này chỉ áp dụng cho lượt audit nguồn ban đầu; workspace hiện tại đã pass.

### Lịch sử: vì sao bước 1 ban đầu chưa hoàn thành ở checkout nguồn?

Manifest lưu SHA-256 của từng file tại lúc tạo dữ liệu. Validator so hash trên **bytes thực tế**, không chỉ nội dung hiển thị. LF và CRLF đều biểu diễn xuống dòng nhưng có bytes khác nhau, nên cùng câu chữ vẫn cho hash khác.

Trong workspace hiện tại, chuyển CRLF thành LF trong bộ nhớ cho hai file trên tạo đúng hash đã ghi. Điều đó xác nhận khác biệt bytes của hai file là kiểu xuống dòng; không cho phép bỏ qua kiểm tra toàn bộ provenance/schema.

- A kiểm tra provenance gồm hash corpus nên đang báo `Output provenance changed`.
- C và D kiểm tra corpus nên dừng ở `Input checksum mismatch`.
- Sau lỗi corpus, hash generator còn có khác biệt ở `scripts/build_corpus.py`; chỉ sửa một file chưa chắc đủ.
- C handoff được D kiểm tra lại. Chỉ sửa code/manifest D không sửa được tính hợp lệ của nguồn C; đổi hash để vượt kiểm tra làm mất khả năng đối chiếu nguồn.

Ban đầu công việc dừng ở chẩn đoán vì hai file ngoài phạm vi D. Theo quyết định mới, đã xử lý bằng snapshot trong D và bốn gate đều pass; không cần chờ người khác sửa checkout nguồn. Đây chưa phải bằng chứng thiếu bài báo hay cần chạy lại extraction A.

Việc exposures/reactions D rỗng thuộc bước 2, là vấn đề khác. Khắc phục checksum không tự tạo thêm hành vi.

## Bước 2 — Chẩn đoán và tạo pilot có tín hiệu hành vi

**Cập nhật quyết định:** đã hủy lựa chọn A theo yêu cầu. Bước 2 hiện CHƯA CHỌN PHƯƠNG ÁN; xem lại A/B/C/D tại [buoc2.md](buoc2.md). Chờ bạn chọn hướng mới trước khi triển khai phần phụ thuộc; chưa thay đổi generator hoặc dữ liệu.

**Đang chờ quyết định thiết kế; chưa tạo pilot.** Với 3.240 bài vượt bộ lọc A: kiểm tra 32.218 tổ hợp anchor/context/focus cho thấy 32.214 tổ hợp không có cặp, 4 tổ hợp có đúng một cặp, không tổ hợp nào có hai cặp. Trong 1.500 phiên hiện có, trước khi chọn candidates có 30 phiên được một cặp, còn lại không có; sau khi loại candidates thì tất cả về 0. Vì vậy chỉ đổi thứ tự sampling không đủ để đáp ứng estimator hiện tại.

Không tự hạ `min_direction_pairs`, nhân đôi cùng một cặp, nới matching hoặc giả lập concept mới để ép có tín hiệu. Thiết kế matching/ngưỡng/nhãn mới cần người thực hiện chốt. Audit mở rộng chưa làm; chẩn đoán này chỉ phục vụ quyết định bước 2.

- [x] Đếm dữ liệu hiện có và phân bố số cặp/phiên; 1.500 phiên đều còn 0 cặp sau khi loại candidates.
- [x] Đọc generator, kiểm tra exact-overlap/matching trên toàn corpus đã lọc; xác nhận không có tổ hợp đạt hai cặp ngay cả trước candidate sampling.
- [x] Chạy chẩn đoán chỉ đọc và lưu [kết quả](../audit/step2_pair_diagnosis.json); đã báo người thực hiện khi cần đổi thiết kế.
- [ ] Nếu cần, sửa logic trong D và bổ sung kiểm tra phù hợp; giữ ranh giới bài quan sát khác candidates, truth tách khỏi scorer và timestamp trước cutoff.
- [ ] Tạo config pilot riêng trong D, dùng đường dẫn output/truth riêng và không ghi đè bộ cũ.
- [ ] Sinh pilot sau khi đầu vào hợp lệ, rồi validate.
- [ ] Báo cáo tỷ lệ phiên có 0/1/ít nhất 2 cặp, số reactions và các nhóm clear/ambiguous/none, similar/different, context/focus.

Pilot có thể giảm số phiên/candidates nhưng vẫn cần A complete và C handoff hợp lệ. Dùng C đầy đủ đã bàn giao nếu chưa có C pilot; không tự tạo file bên C. Không thêm paper/facet giả để bù.

**Hoàn thành khi:** pilot vượt validation, có phiên đủ ít nhất hai cặp hợp lệ để thử estimator và có thống kê thiếu tín hiệu. Không coi vài phiên có cặp là đủ đại diện cho benchmark chính; phải đánh giá coverage của toàn bộ bộ dữ liệu được chọn.

## Bước 3 — Chạy và kiểm tra baseline

- [ ] Chạy pilot qua baseline hiện có, đặt `--output` bên trong D.
- [ ] Kiểm tra đủ `fixed_similar`, `profile_similar`, `direction_behavior`, `direction_search` và oracle do evaluator tạo.
- [ ] Kiểm tra đủ prediction/case/model, thứ tự ranking và trường directions/importance/confidence.
- [ ] Đọc direction F1/accuracy/coverage, ranking @5/10 và compliance@5/10; kiểm tra một số case cụ thể.
- [ ] Chạy trên dataset D chính đã chốt nếu pilot đạt; giữ manifest, config và phiên bản dữ liệu.
- [ ] Xác minh tính tái lập bằng một lượt chạy riêng khi cần, so prediction/metrics và giải thích phần metadata có thể khác.

**Hoàn thành khi:** có baseline hợp lệ, tái lập được và hiểu các lỗi chính. Chưa cần cam kết baseline nào thắng.

## Bước 4 — Triển khai phương pháp riêng trong D

- [ ] Chọn giả thuyết cải tiến cụ thể từ lỗi baseline: query parser, evidence reactions/search, confidence hoặc abstention.
- [ ] Chốt cách phát triển/tune và phần đánh giá cuối trước khi thử tham số; giữ cutoff và tránh tune trên tập đánh giá cuối.
- [ ] Viết phương pháp và runner riêng trong D, sử dụng helper/evaluator ngoài D qua import nếu phù hợp.
- [ ] Giữ giao diện `predict(papers, facets, cases, history, options)` và output contract.
- [ ] Không truyền true focus/directions/weights hoặc relevance labels vào scorer thường.
- [ ] Thêm kiểm tra tập trung cho logic mới: tín hiệu thiếu, xung đột query/phản ứng, cutoff và abstention khi liên quan.
- [ ] Chạy phương pháp mới trên cùng dataset/candidates với baseline.

Không sửa `scripts/exp_d/run_exp_d.py`, `scripts/baseline_common.py` hoặc evaluator chung. Nếu cần đổi contract ngoài D, ghi thành yêu cầu tích hợp cho người phụ trách. Thay encoder ranking không tự cải thiện direction F1.

**Hoàn thành khi:** phương pháp mới có thể chạy qua evaluator, có kiểm tra phù hợp và không dùng thông tin ẩn.

## Bước 5 — So sánh và phân tích

- [ ] Dùng cùng phiên bản data, candidates, cutoff, evaluator và profile C khi so direction.
- [ ] Lập bảng baseline/phương pháp mới cho direction, ranking và compliance.
- [ ] Phân nhóm query mode, similar/different, facet và mức có/thiếu evidence khi đủ mẫu; ghi số mẫu từng nhóm.
- [ ] Thực hiện ablation gắn với cải tiến đã chọn để xác định nguồn thay đổi điểm.
- [ ] Phân tích ví dụ đúng/sai và trường hợp unknown; báo cáo cả kết quả giảm điểm.

Grade 1 vẫn positive cho Recall/MRR nhưng có thể sai hướng; đọc compliance và direction cùng ranking. Không so trực tiếp điểm giữa các dataset có nhãn/candidates khác nhau.

**Hoàn thành khi:** có số liệu và phân tích trả lời giả thuyết, không chỉ một bảng điểm tổng.

## Bước 6 — Viết và bàn giao

- [ ] Viết mô tả bài toán, dữ liệu, phương pháp, đối chứng và protocol.
- [ ] Ghi rõ corpus thật, facet silver và hành vi/intent/relevance mô phỏng.
- [ ] Bàn giao sáu file kết quả: `predictions.jsonl`, `details.jsonl`, `report.json`, `summary.csv`, `report.md`, `manifest.json`.
- [ ] Kèm code/config, phiên bản dữ liệu, hashes và lệnh chạy lại từ gốc project.
- [ ] Ghi thay đổi và kiểm tra trong `changed.md`; cập nhật `progress.md`.
- [ ] Kiểm tra phạm vi diff: mọi thay đổi chủ động nằm trong D.

**Hoàn thành khi:** người khác có đủ code/config/data handoff để chạy lại và hiểu giới hạn kết luận. Các file trong `docs/` bị Git bỏ qua; nếu cần bàn giao các ghi chú này, phải chia sẻ riêng hoặc thống nhất lại quy tắc ignore.

## Quy tắc cập nhật sau mỗi lượt làm

1. Trong `progress.md`, ghi bước hiện tại, việc vừa làm, bằng chứng/lệnh kiểm tra, vấn đề tồn tại và việc kế tiếp.
2. Trong `changed.md`, ghi file thay đổi, lý do, ảnh hưởng và kiểm tra; phân biệt thay đổi code với tài liệu/config/data.
3. Chỉ đánh dấu checklist hoàn thành sau khi có bằng chứng. Các checkbox trong file này là kế hoạch mới; tiến độ đã xác minh trước đó được ghi ở `progress.md`.
