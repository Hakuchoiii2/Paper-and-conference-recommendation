# Exp A — Đánh giá Qwen bằng embedding hoặc khớp chữ

[Generator A](../../data/exp_a/README.md) · [Quy trình review](docs/SEMANTIC_REVIEW_PROTOCOL.md) · [Kết quả matcher](docs/MATCHER_REFERENCE_REPORT.md)

[Kaggle pilot 50 bài](docs/KAGGLE_PILOT.md) · [Kết quả QLoRA v1](docs/QLORA_V1_PROGRESS_2026-10-16.md) · [Báo cáo lịch sử](docs/archive/README.md)

**[Policy matrix v4 COMPLETE và đã chấm lại](docs/KAGGLE_POLICY_MATRIX_V4_EVALUATION_2026-10-16.md)**
Qwen3-8B trên 30 paper dev: original **60,65%**, policy **50,43%**, policy_examples
**52,51%** micro F1. 90 signed records, 60 raw replay và 450 ô scoring khớp local.
Nhánh có ví dụ mất 26 TP so original và chỉ giảm 1 FP; method/contribution chiếm
64,9% lỗi của nhánh này. Có cả lỗi coverage/role và giới hạn matching tên/nhãn dài.
Giữ reference/evaluator/ngưỡng và baseline original; không sửa prompt hoặc fine-tune.
Output `data/exp_a/evaluation/policy_matrix_kaggle_v4/`; vẫn AI reference trên dev.

**[Matrix v2 COMPLETE và đã chấm lại](docs/KAGGLE_FACET_MATRIX_V2_EVALUATION_2026-10-16.md)**
4 cấu hình ×50 bài, 200 replay và 1.000 phép so theo bài/facet khớp local. 8B original
micro **56,36%**, macro **56,89%**, method **65,38%**, contribution **50,00%**.
Source-first giảm điểm ở cả hai model; schema kind/span loại nhiều item, đồng thời
có thêm nhãn sai vai trò/gộp ý. Giữ threshold 0,85 và frozen AI reference.
Output `data/exp_a/evaluation/facet_matrix_v2/`; chưa coi đây là human gold hoặc held-out quality.

**[Pilot v3.7 đã COMPLETE và được chấm](docs/KAGGLE_PILOT50_V3_7_EVALUATION_2026-10-16.md)**
ở kernel version9, đủ50 bài trên hai Tesla T4; hash/raw-applied replay qua.
Micro-F1 **54,27%** (v3.6:53,85%), macro **56,21%** (v3.6:56,83%). Method
**59,84%**, contribution **47,45%**, dataset **75,86%**; thêm11 TP nhưng24 FP.
P002586 giữ được hai method, finding vẫn thiếu điều kiện; artifact/finding âm
còn bỏ sót. 29 fallback, tăng từ23. Output `generated_v3_7_pilot50/`.

Code/test pilot ở `pilot/`; code/test matrix và policy ở `matrix/`.
Kaggle entrypoints tương ứng là `data/exp_a/.kaggle/pilot/kaggle.ps1` và
`data/exp_a/.kaggle/matrix/matrix.ps1`. Evaluator và test evaluator dùng chung
ở thư mục này. Từ gốc project chạy toàn bộ test A:

```powershell
python -B -m unittest discover -s scripts/exp_a -t . -v
```

Output/evaluation pilot v3.1–v3.4 và test riêng v3.4 đã xóa; giữ từ v3.5 trở đi.
Báo cáo/audit cũ đã gom vào [file lưu trữ](docs/archive/README.md); xem
[cleanup manifest](../../data/exp_a/cleanup_manifest_2026-10-16.json).
Baseline `data/exp_a/generated/` còn dùng bởi pilot builder và B–E nên vẫn giữ.

`evaluate_exp_a.py` đọc silver đã lưu, không chạy Qwen trích xuất lại.
Reference hiện hành là AI v2: 400 bài / 3.322 concept, sửa 18 bài / 21 facet
theo nguồn; chưa phải human gold. Encoder dùng Qwen3-Embedding-0.6B local,
mặc định cosine **0.85**.

## Cách ghép và tính điểm

1. Kiểm tra hash silver/corpus, ID cohort và schema/status của reference.
2. Giữ exact pairs sau NFKC, casefold và chuẩn hóa khoảng trắng; giữ dấu câu.
3. Embed nhãn còn lại bằng last non-padding token + L2, không thêm instruction.
4. Chuẩn hóa hậu tố dataset/corpus/collection; alias cần có định nghĩa trong nguồn.
5. Chặn một số bất đồng về số liệu, metric, phủ định, mức đạt/mức tăng và thao tác task.
6. Trong cùng paper/facet, cặp canonical được nhận theo định danh; cặp khác cần cosine
   ≥ ngưỡng. Mỗi nhãn chỉ dùng một lần; tối đa số cặp rồi tổng assignment score.
7. Cặp ghép được là TP; Qwen dư là FP; reference thiếu là FN. Tính P/R/F1
   từng facet, micro/macro; mẫu số bằng 0 báo N/A.

Exact có `similarity=1.0` theo quy ước. Canonical có `assignment_score=1.0`,
nhưng `similarity` vẫn là cosine thật. Cặp embedding dùng cosine cho cả hai.
`rejected_pairs` ghi các ứng viên vượt ngưỡng bị chặn và lý do.
`exact_papers` đếm khớp chữ; `matched_papers` đếm bài ghép đủ cả năm facet.

## Chạy từ gốc project

~~~powershell
.\.venv-qwen\Scripts\python.exe -B scripts/exp_a/evaluate_exp_a.py
.\.venv-qwen\Scripts\python.exe -B scripts/exp_a/evaluate_exp_a.py --threshold 0.85
.\.venv-qwen\Scripts\python.exe -B scripts/exp_a/evaluate_exp_a.py --matching exact --output data/exp_a/evaluation/gold_400
.\.venv-qwen\Scripts\python.exe -B scripts/exp_a/test_qwen_evaluation.py
~~~

Model cache được kiểm tra SHA-256, nằm dưới
`data/exp_a/evaluation/embedding_probe/.model_cache/`.
Không cần thêm package hay LLM judge. `--source`, `--gold`, `--output` và
`--expected-count` vẫn được hỗ trợ. Exact mode không nạp encoder.
Source partial được phép nếu đủ ID reference; không làm source đủ điều kiện
bàn giao B–E. P000001 dùng phát triển prompt và bị loại khỏi cohort.

## Kết quả 400 bài ngày 2026-10-14

| Lượt | TP | FP | FN | Precision | Recall | Micro F1 |
|---|---:|---:|---:|---:|---:|---:|
| Reference v1 + matcher cũ | 1266 | 2087 | 2034 | 37.76% | 38.36% | 38.06% |
| Reference v2 + matcher cũ | 1284 | 2069 | 2038 | 38.29% | 38.65% | 38.47% |
| **Reference v2 + matcher mới** | **1298** | **2055** | **2024** | **38.71%** | **39.07%** | **38.89%** |

Output mặc định hiện hành: `data/exp_a/evaluation/embedding_400_revised/`.
`embedding_400/` và `reference_only_400/` là hai mốc lịch sử để đối chiếu;
khác hash reference/code. Baseline lexical trên reference v2 là 21.21%.

- `report.md`: điểm từng facet, baseline và giới hạn.
- `summary.json`: counts, micro/macro, encoder/runtime, corpus audit và diagnostics matcher.
- `per_paper.jsonl`: raw silver/gold, matched/rejected pairs, nhãn dư/thiếu và evidence.
- `manifest.json`: hash input/code/model/output.

## Giới hạn và code đã dọn

Đã thử 56 cặp hiệu chỉnh và 44 cặp kiểm tra ở 12 bài khác. Ứng viên 0.78 chưa
đạt precision 90% theo gate đặt trước, nên giữ mặc định 0.85. Các cặp do Codex
rà, chưa được người xác nhận. Matcher vẫn có thể nhầm phạm vi, điều kiện và
nhãn gộp nhiều ý; điểm là agreement với AI reference, chưa phải semantic accuracy.
Cohort ưu tiên silver đầy đủ và không đại diện ngẫu nhiên toàn corpus.

Giữ một evaluator và file test `scripts/exp_a/test_qwen_evaluation.py`.
Không giữ script probe/calibration riêng; log/cache test tạm được dọn.
Báo cáo/audit lịch sử được nén trong `docs/archive/`; output pilot giữ từ v3.5 trở đi.
