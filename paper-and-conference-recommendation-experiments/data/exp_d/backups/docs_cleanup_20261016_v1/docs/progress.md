# Tiến độ thí nghiệm D

Cập nhật: 2026-10-15, múi giờ Asia/Saigon.

## Đang ở đâu?

**Lượt người thực hiện baseline_20261016_v1 đã hoàn thành và được review (2026-10-16):** canonical đủ 7.500 predictions/details; synthetic đủ 6 cấu hình × 300 predictions. Export hashes (6 + 78 files), input/code hashes và 9.300 rankings đều vượt kiểm tra. Canonical mean positives 4,5, 57 anchors; pilot 30 phiên/28 anchors. Behavior suy focus dưới synthetic simulator nhưng ranking chưa tăng (pilot nDCG@10 0,8305 → 0,8284; compliance@5 giữ 0,4533). Xem [review lượt chạy](../audit/baseline_20261016_v1_review.md). Mốc chạy baseline đã xong; tiếp theo là chọn và kiểm chứng giả thuyết cải tiến, không coi đây là đã hoàn thành toàn bộ nghiên cứu D.

**Cập nhật mới nhất 2026-10-16:** đã chạy end-to-end `run_baseline_pipeline.py --name pipeline_check_20261016 --with-synthetic`. Workspace mới chứa generator hiện tại, D được sinh lại đủ 1.500 phiên/30.000 nhãn, validate/dry-run/scoring pass. Baseline tự xuất về `data/exp_d/results/pipeline_check_20261016/`; 6 cấu hình synthetic xuất về `data/exp_d/results/pipeline_check_20261016_synthetic/`. Pipeline complete, nguồn đã snapshot không đổi, workspace cũ giữ nguyên. Xem [guideline_pipeline.md](guideline_pipeline.md) để tái lập từ đầu. Các trạng thái ngày 15/10 phía dưới mô tả phiên bản trước.

**Trạng thái mới nhất — pilot synthetic observation (2026-10-15):** baseline cũ đã có và giữ nguyên. Đã triển khai `data/exp_d/run_synthetic_observation_pilot.py` theo `bao_cao_exposure_interaction_D.md`, không sửa corpus/A/C hoặc shared validator/scorer. Pilot overlay riêng giữ nguyên 30 phiên/30 anchors thật, candidates/nhãn/query/cutoff; mỗi cấu hình có 120 exposures và 240 interactions mô phỏng. Chạy 3 seeds × 2 noise, đủ 6 cấu hình pass; 5 tests pass, control khớp baseline nguồn, source hashes không đổi.

Output tại `data/exp_d/evaluation/synthetic_observation_pilot_v1/`. Xem [hướng dẫn pilot](../SYNTHETIC_OBSERVATION_PILOT.md) và [báo cáo cập nhật](bao_cao_exposure_interaction_D.md). Focus behavior accuracy ở noise 0,2 là 1,0; noise 0,5 là 0,7333–0,8333. Ranking chưa tăng: nDCG@10 0,9223 → 0,9196, compliance@5 0,2533 → 0,2467. Chưa có bằng chứng phương pháp ranking tốt hơn hoặc hiệu quả người dùng thật. Các trạng thái chờ chạy baseline/chưa có observation phía dưới là lịch sử của dataset canonical, được cập nhật này thay thế cho pilot mới.

**Quyết định mới nhất (2026-10-15): hoàn thành baseline theo protocol hiện hành, cải tiến để sau.** Kế hoạch thực thi hiện hành là [step_baseline.md](step_baseline.md); thay yêu cầu chọn A/B/C/D hoặc tạo pilot đủ cặp trước baseline trong các ghi chú cũ. Không chờ quyết định đổi thiết kế để chạy baseline.

Đã chạy lại `python -B data/exp_d/audit/audit_step1.py --root data/exp_d/workspace --report-prefix step1_workspace_audit`: A complete, C validate, D validate và runner dry-run đều exit 0; đủ 1.500 cases/30.000 labels; 47 checksum checks khớp; không có watched input/code/manifest thay đổi; `step1_complete=true`. Timestamp chi tiết và logs ở [audit workspace](../audit/step1_workspace_audit.json). **Sẵn sàng chạy toàn bộ baseline trong workspace; lượt này chưa chạy scoring.**

D vẫn có 0 exposures/0 interactions. Protocol cho phép giữ số cặp thực tế và abstain; đây là giới hạn đánh giá behavior, không phải blocker baseline. Các đoạn chờ thiết kế bên dưới là lịch sử, được quyết định này thay thế cho giai đoạn baseline.

**Bước 1 đã hoàn thành. Bước 2 đã chẩn đoán xong khả năng ghép cặp và đang chờ người thực hiện chốt hướng thiết kế.** Chưa tạo pilot hoặc chấm baseline. Project thực thi là `data/exp_d/workspace/`; checkout nguồn giữ nguyên. Xem [audit workspace](../audit/step1_workspace_audit.md), [JSON đầy đủ](../audit/step1_workspace_audit.json) và [hướng dẫn chạy](workspace.md).

Phạm vi: chỉ tạo/sửa file trong `data/exp_d/`. Kế hoạch chi tiết: [step.md](step.md). Thay đổi: [changed.md](changed.md).

| Bước | Trạng thái | Bằng chứng/kết quả |
|---|---|---|
| 0. Quyết định thiết kế | Đã rút gọn theo yêu cầu | Chỉ hỏi khi đổi protocol/nhãn/matching hoặc chọn giả thuyết nghiên cứu |
| 1. Đầu vào | HOÀN THÀNH trong workspace | A/C/D và D runner dry-run đều exit 0; 47/47 hash checks khớp |
| 2. Tín hiệu/pilot D | Đã chẩn đoán; chờ quyết định thiết kế | Toàn corpus không có tổ hợp đủ hai cặp; chưa sửa generator/tạo pilot |
| 3. Baseline | Chưa chấm điểm | Dry-run workspace đã pass 1.500 cases; chưa chạy scoring |
| 4. Phương pháp riêng | Chưa triển khai | Chưa sửa thuật toán hoặc thêm scorer |
| 5. So sánh | Chưa thực hiện | Chưa có metrics baseline/phương pháp mới |
| 6. Bàn giao | Đã chuẩn bị ghi chú cá nhân | Chưa có bộ kết quả thực nghiệm để bàn giao |

## Những việc đã làm và xác minh

### Kết quả mới nhất — workspace riêng

- Đã tạo snapshot 69 file, 49.041.454 bytes trong D; chỉ chuẩn hóa CRLF → LF ở hai bản sao corpus và build_corpus.py. Manifest giữ nguyên bytes, không sửa validator/hash.
- Hash toàn bộ nguồn trước/sau copy và sau lượt chạy khớp nhật ký; snapshot khớp hash. Prepare từ chối ghi đè workspace đã tồn tại.
- A complete handoff PASS (4.210 papers/facets/metadata); C validate PASS (300 users); D validate PASS (1.500 sessions/30.000 labels); D runner dry-run PASS (1.500 cases, session_prefix).
- Audit 47 checksum references: tất cả khớp; không có input/code/manifest được theo dõi bị thay đổi trong audit.
- Chạy lại: `python -B data/exp_d/audit/audit_step1.py --root data/exp_d/workspace --report-prefix step1_workspace_audit` từ gốc project nguồn.
- Output runner phải là `results/exp_d/...` tương đối từ workspace. Đường dẫn vật lý vẫn nằm trong D. Lệnh cũ `--output data/exp_d/results/...` không đúng quy tắc runner chung.

### Lịch sử kiểm tra checkout nguồn trước khi chọn workspace

- Đọc README gốc và các tài liệu liên quan đến dữ liệu, protocol, runner, baseline và kế hoạch D.
- Xác nhận notebook `paper-extractio-experimentA.ipynb` thuộc extraction A part 5, không phải D.
- Xác nhận protocol hiện hành: C suy profile, D suy similar/different theo phiên, E temporal.
- Đếm corpus/A silver/A metadata: mỗi bộ 4.210 bản, ID riêng biệt; 970 bản A có cờ bị bộ lọc hiện hành loại.
- Đếm C: 300 user IDs riêng biệt.
- Đếm D: 1.500 sessions, mỗi session 20 candidates; 30.000 labels; 1.500 search events; 0 exposures và 0 interactions.
- Ground truth D có 500 phiên mỗi query mode clear/ambiguous/none.
- Đã chạy `python data/exp_d/build_exp_d.py --validate-only` và `python scripts/exp_d/run_exp_d.py --dry-run`: cả hai lỗi `Input checksum mismatch: data/processed/papers.jsonl`.
- Đối chiếu hash cho thấy corpus khớp hash đã ghi khi chuẩn hóa CRLF về LF; `scripts/build_corpus.py` cũng có khác biệt xuống dòng tương tự trong generator hashes C/D. Hash các file đầu ra được liệt kê trong manifest C/D khớp tại lần kiểm tra.
- Đã tạo `Understand_D.md` và quy tắc ignore cho `docs/`. Đã kiểm tra các link tương đối trong tài liệu này đều tồn tại.
- Đã tạo `step.md`, `progress.md`, `changed.md` để theo dõi công việc theo phạm vi D.
- `git diff` cho D tại lúc chuẩn bị các ghi chú này không có thay đổi code được Git theo dõi. Đây là so với checkout hiện tại, không chứng minh lịch sử toàn repo chưa từng sửa D.

Đã chạy lại bằng `python -B data/exp_d/audit/audit_step1.py`. Xem [báo cáo](../audit/step1_audit.md) và [JSON đầy đủ](../audit/step1_audit.json). Script gọi bộ kiểm tra A complete, C validate, D validate và D runner dry-run; cả bốn trả exit 1. Script audit cũng trả exit 1 để phản ánh bước 1 chưa đạt, không phải đã sửa thành công.

Đã đối chiếu input/file hashes A và input/output/generator hashes C/D. Có hai đường dẫn khác bytes: `data/processed/papers.jsonl` và `scripts/build_corpus.py`; cả hai khớp hash đã ghi nếu chỉ chuyển CRLF thành LF. Các file đầu ra A/C/D được kiểm tra đều khớp hash. Đây không phải bằng chứng mọi kiểm tra schema/provenance phía sau sẽ pass sau khi khôi phục hai file; cần chạy lại toàn bộ.

Audit không thay đổi bytes của các input/code/manifest được theo dõi trước và sau lượt chạy. Chạy subprocess với `-B` để không tạo bytecode ngoài D. Chỉ ghi script và báo cáo trong `data/exp_d/docs/`.

## Vấn đề còn tồn tại

1. Checkout nguồn vẫn có khác biệt xuống dòng; không còn chặn D khi dùng workspace đã pass. Workspace là snapshot, không tự đồng bộ sửa đổi ở nguồn; cần xác định rõ bản code/data đang chạy cho các bước sau.
2. D đủ quota phiên/nhãn nhưng không có evidence phản ứng trong phiên. Chưa xác định đầy đủ nguyên nhân; cần đo pool và quy trình ghép cặp, không khẳng định chạy lại là đủ.
3. Chưa có config pilot riêng, dataset D mới, phương pháp riêng hoặc bộ metrics được tạo trong công việc này.

## Bước tiếp theo

Có thể làm ngay bước 0A trong `step.md` để hiểu bài toán và ghi các câu hỏi cần thống nhất với nhóm. Bước 0B làm sau khi có lỗi baseline thực tế, trước bước 4; không đánh dấu thay người thực hiện.

1. Dùng workspace riêng theo quyết định đã chốt; không cần chờ sửa file chung. Người thực hiện tự hoàn thành checklist 0A.
2. Bắt đầu bước 2: chẩn đoán chỉ đọc trong D, thống kê pool same/different và số cặp còn lại sau candidate sampling, matching các facet khác.
3. Xác định phiên bản generator/config và cách cập nhật snapshot có chủ đích trước khi sửa; không chạy prepare đè workspace cũ.
4. Dựa trên kết quả, chọn thay đổi generator/config pilot trong D. Sau khi đầu vào hợp lệ, tạo pilot mới, validate rồi chạy baseline với output nằm trong D.

Lượt thực hiện bước 1 chỉ thêm công cụ audit và báo cáo; chưa sửa thuật toán, sinh data hoặc chạy model.

## Nhật ký cập nhật

| Ngày | Việc thực hiện | Kết quả |
|---|---|---|
| 2026-10-15 | Đọc tài liệu, kiểm tra notebook, đếm dữ liệu, chạy validator/dry-run, đối chiếu hash | Xác định lỗi checksum và thiếu evidence D; chưa có baseline thành công |
| 2026-10-15 | Tạo hướng dẫn và ba file quản lý công việc trong docs D | Có kế hoạch, tiến độ và nhật ký thay đổi; chưa thay đổi thuật toán |
| 2026-10-15 | Thực hiện kiểm tra bước 1 và lưu audit | A/C/D vẫn chưa pass; xác định hai file ngoài D lệch CRLF/LF; tick 3/5 mục, giữ hai mục chưa đạt |
| 2026-10-15 | Thêm bước 0 và giải thích blocker bước 1 | Có checklist tự hiểu/brainstorm; chưa đổi code hoặc khắc phục đầu vào |
| 2026-10-15 | Tạo workspace riêng, chuẩn hóa hai bản sao và kiểm tra đầy đủ | A/C/D và runner dry-run pass; 47/47 hash checks khớp; bước 1 hoàn thành trong workspace |

Cập nhật sắp xếp file: script/báo cáo kiểm tra và JSON snapshot đã chuyển sang `../audit/`; tài liệu vẫn ở `docs/`. Bước 1 vẫn hoàn thành theo kết quả workspace đã xác minh; chưa thực hiện thêm bước 2.

## Cập nhật bước 2 — kết quả mới nhất

- Đã thêm `audit/diagnose_pairs.py`, chỉ đọc corpus A/sessions/truth trong workspace để chẩn đoán dữ liệu; script này không phải scorer và không truyền truth vào mô hình.
- Chạy `python -B data/exp_d/audit/diagnose_pairs.py`: 3.240 bài hợp lệ, 32.218 tổ hợp anchor/context/focus; chỉ 4 tổ hợp có một cặp, còn lại 0; tối đa một cặp ngay cả trước khi chọn candidates.
- 1.500 phiên hiện tại: 1.470 phiên không có cặp trước sampling, 30 phiên chỉ có một; sau khi loại candidates, cả 1.500 phiên đều không có cặp.
- Kết luận: không thể đạt hai cặp cho estimator hiện tại chỉ bằng resampling hoặc đổi thứ tự chọn candidates. Chưa kết luận semantic matching sẽ giải quyết được trước khi thiết kế và thử nghiệm.
- Đã gửi lựa chọn thiết kế cho người thực hiện. Trong lúc chờ, chỉ cập nhật tài liệu; không đổi generator, ngưỡng, nhãn hoặc tạo pilot phụ thuộc quyết định.
- Bước 0 đã rút gọn: không buộc tự đọc/tự audit trước khi làm; chỉ chốt quyết định nghiên cứu cần thiết. Audit bổ sung để sau.

**Việc tiếp theo hiện hành:** nhận lựa chọn thiết kế, ghi protocol/config phiên bản D mới nếu cần, rồi triển khai pilot theo lựa chọn. Những mục “bước tiếp theo” cũ phía trên là lịch sử trước lượt chẩn đoán này.

## Cập nhật theo yêu cầu xem phương án bước 2

Trạng thái hiện hành: lựa chọn A đã được hủy theo yêu cầu. Bước 2 chưa chọn phương án; xem A/B/C/D tại [buoc2.md](buoc2.md). Không tiếp tục bổ sung dữ liệu cho tới khi có quyết định mới. Kết quả chẩn đoán giữ nguyên; chưa có code/data phương án A cần rollback.
