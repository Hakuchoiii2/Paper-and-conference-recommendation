# Workspace riêng cho D

**Cập nhật 2026-10-16:** xem [guideline_pipeline.md](guideline_pipeline.md) để tạo workspace mới từ code hiện tại. `prepare_workspace.py` nay mặc định `--mode current`: sau khi copy phải sinh lại D trước validate/scoring. Hướng dẫn phía dưới mô tả snapshot cũ đã validate, không còn là toàn bộ quy trình khi generator D đã thay đổi. Không cần xóa snapshot cũ.

Quyết định: dùng bản sao tại `data/exp_d/workspace/`, không sửa corpus/code/manifest dùng chung của checkout nguồn.

## Cách tạo và kiểm tra lại

Từ gốc `paper-and-conference-recommendation-experiments`:

```powershell
# Chỉ chạy tạo khi workspace chưa tồn tại.
python -B data/exp_d/prepare_workspace.py

# Kiểm tra đầy đủ A/C/D và runner D trong workspace.
python -B data/exp_d/audit/audit_step1.py --root data/exp_d/workspace --report-prefix step1_workspace_audit
```

`prepare_workspace.py` sao chép code/config/schema và các file cần bởi manifest A/C/D; không sao chép model, virtualenv, checkpoints hoặc workspace lồng nhau. Script xác nhận fingerprints theo manifest trước khi ghi. Chỉ hai bản sao sau được đổi CRLF thành LF:

- `workspace/data/processed/papers.jsonl`
- `workspace/scripts/build_corpus.py`

Manifest được sao chép nguyên bytes. Không sửa hash, không bỏ validator và không monkeypatch kiểm tra. Script kiểm tra nguồn không đổi và hash bản sao sau khi ghi. Nhật ký sao chép: [workspace_snapshot.json](../audit/workspace_snapshot.json).

Đây là snapshot có version theo hashes, không tự đồng bộ. Chạy lại prepare khi workspace đã tồn tại sẽ bị từ chối để giữ nguyên thí nghiệm đã chạy. Khi nguồn hoặc phương pháp D thay đổi, cần cập nhật snapshot có chủ đích, ghi lại provenance và xem có cần sinh lại dataset không; không mặc định file ngoài workspace tự có hiệu lực trong workspace.

## Chạy lệnh trực tiếp trong workspace

```powershell
Set-Location data/exp_d/workspace
python -B data/exp_d/build_exp_d.py --validate-only
python -B scripts/exp_d/run_exp_d.py --output results/exp_d/baseline_initial --dry-run
```

Sau khi chuyển vào workspace, mọi đường dẫn tương đối của pipeline tính từ đây. Runner chung bắt buộc output nằm dưới `results/` của project đang chạy. Vì project đang chạy nằm trong D, output thực tế sẽ là:

```text
data/exp_d/workspace/results/exp_d/baseline_initial/
```

Không dùng `--output data/exp_d/results/...` với runner chung: runner từ chối đường dẫn đó vì không thuộc project/results. Hướng dẫn trước đã đề xuất đường dẫn này chưa đúng; dùng đường dẫn trong lệnh trên.

Lượt bước 1 chỉ validate và dry-run, chưa chấm ranking, chưa sinh dataset D mới. Logs hành vi D rỗng vẫn cần chẩn đoán ở bước 2, kể cả khi bước 1 pass.

## Báo cáo

- [Audit nguồn ban đầu](../audit/step1_audit.json): giữ nguyên để so sánh lỗi LF/CRLF.
- [Audit workspace](../audit/step1_workspace_audit.json): kết quả mới nhất khi chạy lệnh audit bên trên; chỉ đọc kết luận sau khi lượt chạy hoàn tất.

Thư mục workspace được Git ignore bằng quy tắc trong `data/exp_d/.gitignore`. Code chuẩn bị workspace nằm ở `data/exp_d/prepare_workspace.py`; snapshot dữ liệu/code bên trong workspace không tự được commit.
