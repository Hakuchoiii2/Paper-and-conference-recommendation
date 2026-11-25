# Corpus canonical dùng chung

[Chỉ mục dữ liệu](../README.md) · [Hợp đồng](../../DATA_CONTRACT.md) · [Review phạm vi](../../docs/IT_SCOPE.md)

## 1. Corpus này là gì?

`papers.jsonl` là kho title/abstract duy nhất cho các exp. Mọi generator giữ nguyên paper_id và nội dung bài, không tạo một catalog paper mẫu khác để làm mock.

Snapshot ingestion gồm **4.210 canonical records**, gộp từ CSFCube v1.1 và SciFact sau lọc phạm vi. Có 4.182 bài nguồn đại diện CSFCube và 28 SciFact. Các số ingestion và giới hạn nằm trong [báo cáo nguồn](../../docs/INGESTION_REPORT.md); tiến độ A/B–E phải xem manifest riêng.

Số lượng còn chờ review phạm vi và năm nhóm cùng title nhưng khác abstract; SciFact có 15 bản ghi giáp ranh tạm loại. Corpus thiếu 1.790 so với mục tiêu làm việc 6.000; không thêm dữ liệu trùng/giả để bù.

## 2. Tệp và đơn vị dữ liệu

| Tệp | Nội dung |
|---|---|
| `papers.jsonl` | Một bài canonical/dòng: paper_id, source/source_id, title, abstract, year, domain, scope_evidence |
| `id_map.jsonl` | Alias ID nguồn → paper_id, checksum, active/primary |
| `scope_audit.jsonl` | Quyết định giữ/loại từng bản ghi nguồn, evidence/reviewer |
| `corpus_report.json` | Counts, duplicates, metadata thiếu, title conflicts, gap target |
| `native_split_policy.json` | Giữ split nguồn và giải thích phạm vi sử dụng |
| `manifest.json` | Version, seed, input/output hashes và actual counts |

source_id là string; year là integer hợp lệ hoặc null. Abstract chỉ nối câu/thu gọn whitespace; raw giữ nội dung nguồn. Corpus không chứa relevance, intent, user preference hoặc đáp án khuyến nghị.

## 3. ID và gộp trùng

Paper ID có dạng P + sáu chữ số. Khóa (source,source_id) là alias tới ID canonical; một bài có đúng một alias active primary làm nguồn đại diện.

Ưu tiên identifier chung, rồi title + abstract tương đương theo rule. Cùng title nhưng abstract khác giữ riêng để review, không gộp vì chủ đề giống. Khi thêm alias phải giữ nguồn đại diện/ID đã cấp. Không xóa id_map để cấp ID lại; alias inactive giữ lịch sử.

Split query/claim của nguồn chưa phải split train/dev/test của toàn catalog. B tự split anchor; C/D/E dùng cutoff thời gian riêng.

## 4. Rebuild và kiểm tra

Từ gốc repository:

```powershell
python scripts/build_corpus.py
python scripts/validate_all.py --dataset-kind real --phase corpus
```

Config corpus là `configs/data.json`; scope policy/overrides là `configs/scope.json`. Muốn đổi phạm vi, sửa rule/override có reviewer + reason và phiên bản, rebuild trên id_map hiện có rồi đọc report/gate.

Không sửa trực tiếp papers.jsonl hoặc archive nguồn. Builder dừng khi xung đột nguồn/ID cần review. Không chạy đồng thời nhiều builder vào cùng output.

Gate kiểm tra schema/text/year/evidence, IDs/aliases/primary, hashes, provenance và coverage audit. Gate pass không chứng minh subject/facet do người kiểm duyệt đúng hoàn toàn.

## 5. Corpus được dùng tiếp ở đâu?

- [A](../exp_a/README.md) đọc title/abstract để trích năm facet silver.
- [B](../exp_b/README.md) và [C](../exp_c/README.md) cần thêm full silver A hợp lệ.
- [D](../exp_d/README.md) và [E](../exp_e/README.md) cần thêm C handoff complete.

Bài thật không tự tạo gold/facet hoặc logs khuyến nghị thật. Chi tiết freeze, thay nguồn và bàn giao nằm trong [quản lý dự án](../../docs/PROJECT_OPERATIONS.md); raw/provenance ở [nguồn gốc](../raw/README.md).
