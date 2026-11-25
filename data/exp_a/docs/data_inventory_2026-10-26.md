# Dữ liệu exp_A hiện có — 26/10/2026

Kiểm kê từ các JSONL và manifest đang nằm trên máy; không chạy model và không thay dữ liệu.

| Nhóm | Nội dung/quy mô thực tế | Vị trí chính |
|---|---|---|
| Nguồn bài báo thật | Raw CSFCube và SciFact; corpus chuẩn hóa 4.210 bài, gồm 4.182 CSFCube và 28 SciFact | `data/raw/`, `data/processed/papers.jsonl` |
| Silver toàn corpus | 4.210 bộ năm facet do Qwen3-4B-Instruct-2507 sinh; 970 bài fallback; cả 4.210 unreviewed | `data/exp_a/generated/` |
| Reference đánh giá 400 bài | 400 bài, 3.322 concept; review AI, human_review_status=pending; chọn thiên về silver sạch/đủ, không đại diện toàn corpus | `data/exp_a/ground_truth/gold_review/` |
| Pilot50 | Nguồn/selection, baseline silver và AI reference riêng 50 bài; output các prompt v3.5/v3.6/v3.7 mỗi bản 50 | `data/exp_a/pilot50/`, `generated_v3_5_pilot50/`, `generated_v3_6_pilot50/`, `generated_v3_7_pilot50/` |
| Teacher/reference mở rộng | Reviewed pool 312 nguồn; frozen subset 303 bài; annotation/evidence/audit riêng, vẫn reference AI | `data/exp_a/finetuning/teacher/reviewed_pool/`, `teacher/frozen/` |
| Fine-tuning v1 | 467 train +100 dev +100 test; train/dev ở dạng messages cho SFT, test source/reference tách riêng | `data/exp_a/finetuning/data/` |
| Pilot sửa quy ước nhãn | 40 bài; blind labels, adjudication, evidence nhiều câu, alias và kiểm tra nguồn, nhiều phiên bản chính sách | `data/exp_a/finetuning/label_revision_v2/pilot40/` |
| Fine-tuning v2 | 567 train/dev sources với nhãn sửa theo schema/policy v2; 98 accepted qua review AI riêng (85 train,13 dev), 469 source_authored_unreviewed (382 train,87 dev); toàn bộ human review pending | `data/exp_a/finetuning/v2/review/`, `v2/training_data/` |
| Kết quả/audit thực nghiệm | Prediction và raw attempts, signed records, evidence IDs, flags, token/time, score per facet/per paper; baseline/matrix/QLoRA/R1/R2/R2a-V/P/full/Source-first/V-recall | `data/exp_a/evaluation/`, `.kaggle/`, `finetuning/downloads/`, `finetuning/v2/downloads/` |
| Mẫu chấm/diagnostic | Matcher/threshold pairs; semantic-review spike 8 bài/74 existing items, cảnh báo không áp dụng sửa nhãn | `data/exp_a/samples/`, `semantic_review_local/` |

## Dạng bản ghi

- Corpus: paper_id, title, abstract, source/source_id, domain/scope_evidence, year.
- Silver: paper_id và các danh sách problem/task/method/dataset/contribution. Metadata riêng lưu câu evidence, nguồn, model/revision, raw attempts và trạng thái validation/fallback.
- Reference: nhãn năm facet cùng provenance review; ở một số bộ có evidence/decisions riêng. Từ `gold_review` trong tên thư mục không xác nhận human gold.
- Fine-tuning: messages gồm instruction/source/assistant annotation, paper_id, provenance và token lengths. V2 có schema evidence nhiều câu và chính sách riêng, không tự trộn vào output V.
- Experimental records: output của từng cấu hình và audit chi phí/nguồn; không tự nâng thành reference hoặc nhãn training.

## Quan hệ giữa các bộ

- Không cộng tất cả số lượng thành số bài mới: đây phần lớn là các tập con hoặc phiên bản nhãn của corpus 4.210 bài.
- Pilot50 không trùng ID với reference400 hoặc train/dev/test v1. Cả ba split v1 cũng không trùng nhau theo manifest và kiểm tra IDs pilot.
- Train/dev v2 giữ đúng paper IDs của train/dev v1; là phiên bản nhãn khác của cùng 567 bài, không phải 567 nguồn mới.
- Reference400 không trùng với 303 bài teacher frozen. Fine-tuning v1 manifest ghi 703 input references, 667 eligible sau kiểm tra; không tự coi toàn bộ nguồn reference đều đủ điều kiện training.
- V/V-recall/Source-first gần đây cùng dùng cohort pilot50 đóng băng, không phải corpus 4.210 bài được sinh lại.
- Bản full silver `generated/` chưa được thay bởi kết quả V hoặc V-recall pilot.

## Mức độ tin cậy

Có corpus thật, silver tự động, reference AI, nhãn AI đã được review bổ sung một phần và output thực nghiệm. Các bộ reference chính kiểm tra được vẫn ghi human_review_status=pending; không gọi chúng là human gold. Bộ 400 bài có selection bias; pilot50 đã dùng nhiều lần để phát triển. Bộ test100 cần giữ tách khỏi việc chỉnh prompt.

Số liệu được đếm trực tiếp từ JSONL và đối chiếu manifest; đây là inventory, chưa phải kiểm tra lại toàn bộ checksum/chất lượng ngữ nghĩa từng nhãn.
