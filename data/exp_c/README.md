# Dữ liệu C — Users, profile ẩn và lịch sử tìm kiếm

[Chỉ mục dữ liệu](../README.md) · [Scorer C](../../scripts/exp_c/README.md) · [Protocol](../../docs/EXPERIMENT_PROTOCOL.md)

## 1. Generator tạo gì?

C tạo users, latent profiles, query/exposure/phản ứng, rồi tách lịch sử và holdout. C sở hữu danh tính users dùng chung cho D/E.

Mục tiêu 300 users × 50 phản ứng: 30 history + 20 holdout/user. Profile thật được **sinh trước hành vi**, không suy đáp án bằng chính baseline C.

## 2. Nguyên liệu và config

Corpus canonical + full silver A/metadata/complete manifest. Loại bài fallback/còn validation errors; không đổi title/abstract hoặc sinh concept giả.

Config `configs/exp_c.json`: seed 42, concepts_per_facet 2, targeted_exposure_fraction .8, search_fraction .6, exposure_size 4, noise_std .15. B/C độc lập sau A; C không cần output B hoặc human gold A.

## 3. Sinh profile ẩn của một user

1. Chọn hai bài thật có evidence làm nguồn concept.
2. Mỗi facet lấy concept thích từ bài thứ nhất; lấy concept tránh từ bài thứ hai, loại trùng concept thích.
3. Với config hai concepts/facet, lấy tối đa một liked và phần còn lại avoided; nếu nguồn thiếu thì giữ số thực tế.
4. Preference liked lấy trong [.5,1], avoided trong [−1,−.5].
5. Với facet có preference, lấy raw importance ngẫu nhiên [.05,1], facet không có preference nhận 0.
6. Normalize importance để tổng năm weights bằng 1; lưu vào latent_user_profiles.

Ví dụ chỉ minh họa: method thích GNN .9, tránh SVM −.7; method importance .4. Những giá trị này thuộc truth, scorer không nhìn thấy.

## 4. Sinh events, query và exposure

Mỗi user có 50 timestamps, bắt đầu 2026-01-01, cách nhau một ngày. Bài được chọn cho phản ứng không lặp trong chuỗi 50 events/user.

Pool targeted gồm bài có concept nằm trong profile với preference khác 0, gồm cả concept thích và tránh. Với xác suất .8 chọn trong targeted pool nếu còn, còn lại chọn pool chung.

Với xác suất .6, tạo query bằng concept ưa thích ở facet được chọn theo latent importance, khi có concept phù hợp. Đây là xác suất, không phải cam kết đúng 60% events có query. Reformulation liên kết query trước qua parent_query_id.

Thời gian: query trước phản ứng 2 giây, exposure trước 1 giây. Exposure chứa bốn bài được xáo thứ tự; chỉ một bài có phản ứng ghi lại. Ba bài còn lại **không tự trở thành dislike**.

## 5. Utility biến thành feedback thế nào?

```text
facet_affinity_f = trung bình preference của các concept trong facet bài
                   (concept ngoài profile nhận 0, facet rỗng nhận 0)
utility = Σ importance_f × facet_affinity_f + Gaussian noise(.15)
```

| Utility sau noise | Feedback |
|---|---|
| < −.25 | dislike |
| [−.25,.05) | view |
| [.05,.20) | click |
| [.20,.40) | save |
| ≥ .40 | like |

Ví dụ method GNN preference .9 × importance .4 góp .36 vào utility; các facet khác và noise còn có thể đổi loại feedback. Do đó không phải “có concept thích là chắc chắn like”.

## 6. Cắt history và holdout

30 events đầu là history, 20 events sau là holdout. Cutoff đặt trước query/exposure/phản ứng của event thứ 31. Case có user_id, 20 holdout candidate_ids, cutoff.

Quan sát được có IDs của ứng viên; feedback/query/exposure holdout giữ riêng. Scorer không dùng latent profile hoặc feedback tương lai.

| Phần | Tệp | Mục tiêu |
|---|---|---:|
| generated | `users.jsonl` | 300 users |
| generated | `interactions_train.jsonl` | 9.000 reactions |
| generated | `search_events.jsonl`, `exposures.jsonl` | Prefix logs |
| generated | `cases.jsonl` | 300 cases |
| ground_truth | `latent_user_profiles.jsonl` | 300 profiles |
| ground_truth | `interactions_test.jsonl` | 6.000 reactions |
| ground_truth | `search_events_test.jsonl`, `exposures_test.jsonl` | Holdout logs |

Có report/manifest ghi hashes, seed, actual counts và behavior_counts lịch sử. Số query thực tế phụ thuộc simulator.

Evaluator đổi feedback thành grade 0/0/1/2/3 để chấm ranking; latent importance dùng chấm MAE. [README scorer C](../../scripts/exp_c/README.md) giải thích profile dự đoán và ví dụ cộng evidence.

## 7. Sinh và kiểm tra

```powershell
python data/exp_c/build_exp_c.py --dry-run
python data/exp_c/build_exp_c.py
python data/exp_c/build_exp_c.py --validate-only
```

Chạy từ gốc với Python 3.11+/stdlib. Dùng config riêng và output/truth mới cho [pilot](samples/README.md); không dùng fixtures thay corpus/facet thật.

Giữ contract 2.0. Output 1.0 cần đường dẫn mới; không trộn hai schema hoặc chạy đồng thời vào cùng output.

## 8. Bàn giao cho D/E mà không chờ scorer C

Bàn giao trọn bộ C complete, manifest và config được tham chiếu. D/E trỏ users_path tới users.jsonl; loader kiểm tra hash/provenance toàn bộ handoff C.

D lấy thêm history/search/exposure cùng thư mục để dựng importance. E chỉ dùng danh tính rồi sinh stream riêng. **Không cần C predictions hoặc model checkpoint**.

Profile ẩn C chỉ evaluator đọc. Phương pháp C mới tích hợp sang D/E sau qua phiên bản rõ ràng; baseline các thành viên có thể nghiên cứu độc lập ngay khi có dataset.
