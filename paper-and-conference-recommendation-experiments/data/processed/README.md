# Corpus bài báo IT dùng chung

`papers.jsonl` là kho đầy đủ duy nhất cho xử lý bài thật. Bản hiện tại có 4.210
bản ghi sau lọc và gộp; số này còn chờ review phạm vi và 5 trường hợp cùng tiêu đề
nhưng khác abstract. Không nhầm corpus này với bộ mẫu 50 bài trong `../fixtures/`.

| Tệp | Vai trò |
|---|---|
| `papers.jsonl` | Title, abstract, metadata chuẩn hóa và ID canonical |
| `id_map.jsonl` | Mọi ID nguồn, ID chung, checksum bản ghi và nguồn đại diện |
| `scope_audit.jsonl` | Quyết định giữ/loại từng bản ghi nguồn, bằng chứng và reviewer |
| `corpus_report.json` | Số lượng thực tế, trùng lặp, metadata thiếu và gap target |
| `native_split_policy.json` | Giữ split nguồn; chưa chia lại toàn corpus |
| `manifest.json` | Phiên bản, seed, checksum đầu vào/output và số bản ghi |

Tạo lại từ thư mục gốc:

```powershell
python scripts/build_corpus.py
```

Các tệp trên là output được tạo bằng code. Muốn đổi phạm vi thì sửa quy tắc/review
override có phiên bản trong cấu hình, rồi rebuild và kiểm tra. Không sửa trực tiếp
paper records hoặc xóa `id_map.jsonl` sau bàn giao để cấp lại ID. Nguồn đại diện
và ID đã cấp phải được bảo toàn khi bổ sung alias. Script dừng khi gặp xung đột
nguồn/ID cần review thay vì tự đổi nghĩa bài.

Sau khi lấy mẫu, chạy validator theo README chính. Corpus còn tạm thời; chưa có
silver/gold hoặc dataset A–E chỉ vì các bài đã là dữ liệu thật.
