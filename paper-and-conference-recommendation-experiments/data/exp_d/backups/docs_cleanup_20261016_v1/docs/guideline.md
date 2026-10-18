# Hướng dẫn chạy baseline exp_d trong CMD của IDE

**Quy trình mới nhất (2026-10-16):** nếu muốn bắt đầu từ code hiện tại và workspace mới, dùng [guideline_pipeline.md](guideline_pipeline.md). Tài liệu dưới đây chỉ hướng dẫn chạy trên snapshot cũ đã có; không dùng nó để mặc định code mới đã được đồng bộ. Pipeline mới tự sinh lại D, chạy baseline và xuất kết quả về `data/exp_d/results/`.

Cập nhật: 2026-10-15. Chạy baseline theo protocol hiện hành; cải tiến để sau. Các lệnh dưới đây dùng **Command Prompt (CMD)**. Nếu terminal hiện `PS ...>`, hãy chọn profile **Command Prompt** và mở terminal mới trong IDE.

## 1. Phân biệt checkout hiện tại và workspace

| Vị trí | Đường dẫn | Dùng làm gì? |
|---|---|---|
| Gốc project thực nghiệm ở checkout hiện tại | `E:\08_Project\Paper-and-conference-recommendation\paper-and-conference-recommendation-experiments` | Chứa nguồn chung, tài liệu D và công cụ audit |
| Workspace dùng để chạy | `E:\08_Project\Paper-and-conference-recommendation\paper-and-conference-recommendation-experiments\data\exp_d\workspace` | Bản sao code/config/data đã được kiểm tra; chạy baseline tại đây |
| Tài liệu đang chỉnh trong IDE | `<gốc project>\data\exp_d\docs` | `guideline.md`, `step_baseline.md`, `progress.md` |
| Kết quả chạy thực tế | `<workspace>\results\exp_d\baseline_current_v1` | Chứa sáu file output của baseline |

Workspace được tạo để xử lý khác biệt LF/CRLF ở bản sao, giữ nguyên file dùng chung. **Không tạo lại workspace, không sinh lại dataset và không sửa manifest để chạy baseline.**

Workspace là snapshot, không tự đồng bộ với checkout. Ví dụ, khi chạy trong workspace, script thực thi là `<workspace>\scripts\exp_d\run_exp_d.py`, không phải `<gốc project>\scripts\exp_d\run_exp_d.py`. Tương tự với config và dữ liệu. Sửa file ngoài workspace không tự thay đổi phiên bản đang chạy.

## 2. Kiểm tra đầu vào nếu cần

Lượt kiểm tra gần nhất đã pass A complete, C validate, D validate và dry-run 1.500 cases; checksum khớp. Nếu workspace không thay đổi, có thể sang bước 3. Nếu cần kiểm tra lại, đứng ở **gốc project thực nghiệm**:

```cmd
cd /d E:\08_Project\Paper-and-conference-recommendation\paper-and-conference-recommendation-experiments
python -B data/exp_d/audit/audit_step1.py --root data/exp_d/workspace --report-prefix step1_workspace_audit
```

Đọc hai file ở checkout hiện tại, không phải trong workspace:

- `data\exp_d\audit\step1_workspace_audit.md`: log kiểm tra dễ đọc.
- `data\exp_d\audit\step1_workspace_audit.json`: kiểm tra `step1_complete` là `true`, mọi `returncode` bằng `0`, các `checksum_checks` có `status` là `match`, `watched_files_changed` rỗng. Xem `checked_at` để biết thời điểm kiểm tra.

Audit chỉ validate/dry-run, chưa tạo metrics baseline. Nếu fail, giữ nguyên đầu vào và xem lỗi cụ thể trước khi chạy scoring.

## 3. Chuyển vào workspace

Chạy lệnh sau trong CMD, dù terminal đang ở thư mục nào:

```cmd
cd /d E:\08_Project\Paper-and-conference-recommendation\paper-and-conference-recommendation-experiments\data\exp_d\workspace
cd
```

Lệnh `cd` cuối in ra thư mục hiện tại. Phải kết thúc bằng `\data\exp_d\workspace`. File đang mở trong IDE không quyết định thư mục thực thi của terminal.

## 4. Chạy baseline

Nếu muốn xác nhận riêng lệnh chạy trước scoring, chạy dry-run tại **workspace**:

```cmd
python -B scripts/exp_d/run_exp_d.py --config configs/exp_d.json --output results/exp_d/baseline_current_v1 --ks 5 10 --dry-run
```

Kỳ vọng: `DRY RUN D: 1500 cases; session_prefix`. Dry-run không ghi các file metrics.

Chạy thật tại **cùng thư mục workspace**:

```cmd
python -B scripts/exp_d/run_exp_d.py --config configs/exp_d.json --output results/exp_d/baseline_current_v1 --ks 5 10
```

Một lệnh chạy `fixed_similar`, `profile_similar`, `direction_behavior`, `direction_search`; evaluator tự thêm `oracle_intent`. Không cần chạy scorer C trước. `--ks 5 10` yêu cầu chấm top 5 và top 10. Chờ tiến trình kết thúc và báo `PASS D: 1500 cases; ...`.

**Giữ nguyên dấu `/` trong `--config configs/exp_d.json`.** Validator hiện so chuỗi đường dẫn với key trong manifest. Viết `configs\exp_d.json` có thể mở đúng file trên Windows nhưng vẫn gây `Missing or extra input hashes`. Lệnh trong hướng dẫn đã dùng đúng dạng `/`.

Output phải nằm dưới `results/` của workspace. Không đổi thành `--output data/exp_d/results/...`. Nếu thư mục lượt chạy đã có kết quả, đổi `baseline_current_v1` thành `baseline_current_v2` trong các lệnh liên quan; không dùng `--overwrite` để giữ kết quả cũ.

## 5. Xem metrics và thông số ở đâu?

Tất cả output của lệnh trên nằm tại:

```text
E:\08_Project\Paper-and-conference-recommendation\paper-and-conference-recommendation-experiments\data\exp_d\workspace\results\exp_d\baseline_current_v1
```

Từ CMD đang ở **workspace**, kiểm tra danh sách file và mở thư mục:

```cmd
dir results\exp_d\baseline_current_v1
start "" "results\exp_d\baseline_current_v1"
```

| File cần kiểm tra | Nội dung / mục đích |
|---|---|
| `report.md` | Đọc trước: báo cáo tổng hợp metrics của các phương pháp và các nhóm do evaluator xuất |
| `summary.csv` | Bảng kết quả để xem hoặc tổng hợp bằng Excel |
| `report.json` | Kết quả tổng hợp dạng JSON, thuận tiện xử lý tiếp |
| `details.jsonl` | Kết quả đánh giá chi tiết từng case/model để phân tích lỗi |
| `predictions.jsonl` | Ranking, directions, importance và confidence dự đoán |
| `manifest.json` | Tham số/config, input hashes, code hashes và metadata lượt chạy để đối chiếu/tái lập |

Config đầu vào đã dùng là `<workspace>\configs\exp_d.json`. Không sửa config sau đó rồi coi đó là config của lượt cũ; dùng manifest kết quả để đối chiếu.

Đọc `report.md` ngay trong terminal hoặc mở bằng ứng dụng liên kết:

```cmd
type results\exp_d\baseline_current_v1\report.md
start "" "results\exp_d\baseline_current_v1\report.md"
```

Có thể mở trực tiếp các file trên trong IDE. `start` phụ thuộc ứng dụng mặc định của Windows.

## 6. Kiểm tra sau khi chạy

- Có đủ sáu file và năm tên phương pháp gồm oracle; mỗi phương pháp dự kiến có 1.500 predictions, tổng 7.500 dòng predictions.
- Đọc direction macro-F1/accuracy/coverage, nDCG/Recall/Precision/MRR@5/10 và intent compliance@5/10. Không dùng ranking một mình để kết luận suy hướng tốt.
- D hiện có 0 exposures/0 interactions. Protocol cho phép thiếu cặp và abstain; không phải lỗi cần sinh thêm dữ liệu trước baseline.
- `direction_behavior` có thể giữ focus `unknown`, nhưng context được cung cấp vẫn là `similar`; không kỳ vọng coverage tổng bằng 0.
- `direction_search` có thể suy hướng từ query rõ. Đọc nhóm clear/ambiguous/none và số mẫu thực tế trong báo cáo.
- `unknown` vẫn được giữ trong prediction khi chấm hướng, dù ranking fallback similar. Không đổi unknown thành dự đoán đúng.
- Ghi kết quả thực tế vào `data\exp_d\docs\progress.md` ở checkout hiện tại. Không đánh dấu hoàn thành scoring chỉ dựa trên dry-run.

## 7. Sau khi kiểm tra xong: sao chép để bàn giao nếu cần

Không cần chép output sau mỗi lần chạy. Kết quả trong workspace đã là bộ đầy đủ. Nếu muốn tập trung bản bàn giao ở thư mục kết quả của **gốc project thực nghiệm**, sao chép toàn bộ thư mục lượt chạy sau khi xác nhận thành công.

Từ CMD đang ở workspace, chuyển về gốc project bằng đường dẫn tuyệt đối:

```cmd
cd /d E:\08_Project\Paper-and-conference-recommendation\paper-and-conference-recommendation-experiments
```

Kiểm tra đích chưa có kết quả:

```cmd
dir results\exp_d\baseline_current_v1
```

Nếu đích chưa tồn tại, sao chép bằng:

```cmd
xcopy "data\exp_d\workspace\results\exp_d\baseline_current_v1" "results\exp_d\baseline_current_v1\" /E /I
dir results\exp_d\baseline_current_v1
```

Nếu đích đã có kết quả, chọn tên đích mới thay vì trộn hoặc ghi đè. Giữ nguyên sáu file, đặc biệt `manifest.json`; giữ bản gốc trong workspace để đối chiếu. Bản sao là artifact của lượt chạy trong workspace, không có nghĩa đã chạy baseline trên checkout gốc. Không sửa đường dẫn/hashes trong manifest để làm như chạy ở vị trí khác.

Thư mục `results` bàn giao ở đây là `<gốc project thực nghiệm>\results\exp_d\...`, khác `<workspace>\results\exp_d\...`. Bước sao chép này chỉ là hướng dẫn thao tác thủ công khi cần bàn giao; hiện công cụ chỉ chủ động ghi trong `data/exp_d/` theo phạm vi đã chốt. Nếu nhóm yêu cầu một đích bàn giao khác, dùng đúng đích đó.

## 8. Xử lý lỗi thường gặp

| Hiện tượng | Kiểm tra / xử lý |
|---|---|
| `Missing or extra input hashes` sau khi dùng `--config configs\exp_d.json` | Chạy lại với `--config configs/exp_d.json`; không sửa manifest |
| `Results already exist` | Dùng output mới như `baseline_current_v2` |
| Không tìm thấy script/config | Dùng `cd` xem thư mục hiện tại; chuyển vào workspace bằng bước 3 |
| `Input checksum mismatch` hoặc `Generator hashes changed` | Đối chiếu đúng snapshot và audit bước 2; không bỏ validator hoặc tự cập nhật hash |
| Không thấy metrics sau dry-run | Chạy lệnh thật không có `--dry-run`, rồi xem output trong workspace |
| Trong checkout gốc không thấy kết quả | Lệnh đang chạy trong workspace nên kết quả nằm ở workspace; xem bước 5 hoặc sao chép theo bước 7 |

Checklist đầy đủ về phân tích và bàn giao: [step_baseline.md](step_baseline.md). Hướng dẫn snapshot: [workspace.md](workspace.md).
