# Bộ bài thật dùng chung để kiểm tra nhanh

`papers.jsonl` chứa 50 bài thật thuộc corpus IT, lấy mẫu với seed 42. Nội dung và
`paper_id` giữ nguyên so với corpus. Mục đích là chạy thử nhanh khi phát triển A–E,
không phải tạo dataset cuối, gold, dữ liệu mock hoặc tập chia train/test.

Corpus đầy đủ vẫn ở `../processed/papers.jsonl`. Có thể xử lý trực tiếp trên toàn
corpus; không bắt buộc annotation/thực nghiệm phải bắt đầu từ 50 bài này.
Tái tạo bộ mẫu từ thư mục gốc:

```powershell
python scripts/build_fixture.py --seed 42
```

`manifest.json` ghi checksum nguồn, seed, số bài và phiên bản/hash generator.
Không có `facets.jsonl` vì bài chưa được gán nhãn theo năm facet. Không tạo tệp toàn
list rỗng để giả làm annotation, và không coi nhãn câu gốc của nguồn là gold.
