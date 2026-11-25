# Dữ liệu D — Phiên intent và cặp quan sát

[Chỉ mục dữ liệu](../README.md) · [Scorer D](../../scripts/exp_d/README.md) · [Dữ liệu C](../exp_c/README.md)

## 1. Generator phục vụ câu hỏi nào?

D kiểm tra suy similar/different từ đầu phiên và tác dụng của hướng đó lên ranking. Generator tạo intent ẩn, tín hiệu quan sát trước cutoff và nhãn của pool ứng viên cuối phiên.

Mục tiêu 300 users C × 5 phiên × 20 candidates = 1.500 sessions/30.000 labels. Không cần kết quả scorer C.

## 2. Đầu vào

Corpus canonical, full silver A/metadata/complete manifest, **C complete handoff** gồm users/history/search/exposure và config/manifest hợp lệ.

Config `configs/exp_d.json`: users_path tới C generated/users.jsonl, seed 42, observation_pairs 4, positive_fraction .5, hard_negative_fraction .5, noise_std .2, direction_margin .25, min_direction_pairs 2.

D bắt đầu 2026-03-01, sau lịch sử C trong cấu hình chính. Không chỉnh dates khiến log nguồn nằm sau cutoff mà vẫn coi là quan sát hợp lệ.

## 3. Chọn anchor và intent ẩn

1. Chọn anchor có ít nhất hai facet không rỗng.
2. Chọn context từ facet có evidence; chọn focus khác context.
3. Context luôn similar; focus luân phiên similar/different.
4. Hidden weights context .6, focus .4; facet khác direction ignore và weight 0.
5. Query mode luân phiên clear/ambiguous/none.

Cả năm facet có thể là context/focus. Context là điều kiện benchmark cung cấp cho scorer; focus/hướng/weights/mode thật được giấu. Chưa tạo phiên nhiều focus đồng thời.

## 4. Ground truth và 20 ứng viên

Ứng viên cần có dữ liệu ở context và focus. Xét overlap concept với anchor:

```text
context không overlap / thiếu facet → grade 0
context overlap + thỏa hướng focus → grade 2
context overlap + sai hướng focus  → grade 1
```

Similar focus = có giao; different focus = không giao khi có dữ liệu. Nhãn không dùng cosine/scorer prediction.

Mục tiêu pool 50% thỏa intent và phần còn lại không thỏa; hard negatives liên quan context nhưng sai focus. Lấy theo pool thực tế, đủ 20 IDs riêng và xáo thứ tự. Không đủ pool thì ghi shortfall, không bù bài/facet giả.

## 5. Cặp quan sát khác candidate pool thế nào?

Generator tìm tối đa bốn cặp: một bài same-focus, một bài different-focus với anchor, có cùng context và các facet khác tương đương theo overlap/missing states. Hai bài trong cặp được xáo thứ tự hiển thị.

Các cặp nằm **ngoài pool 20 bài cuối phiên**. Scorer dùng phản ứng các cặp để suy hướng; evaluator chấm ranking ở các bài khác.

Phản ứng được sinh bằng utility nền .7 nếu bài thỏa intent (grade 2), .05 nếu không, cộng Gaussian noise .2 rồi qua thresholds −.25/.05/.2/.4 như C.

Thiếu cặp hợp lệ giữ số thực tế. Không đủ hai cặp hoặc phản ứng yếu thì baseline có thể unknown. Matching kiểm soát simulator, chưa chứng minh quan hệ nhân quả trên log người thật.

## 6. Query và thời gian trong phiên

| Mode | Query quan sát |
|---|---|
| clear | Query context rồi reformulation focus rõ similar/different |
| ambiguous | Chỉ query context |
| none | Không có query |

Ví dụ minh họa clear: context problem rồi `method: alternatives to GNN` hoặc `method: more papers using GNN`, tùy hướng ẩn. Query là text, không gửi nhãn direction cho scorer.

Query, exposure và phản ứng cặp đều trước cutoff; parent_query_id giữ cùng user/session và thời gian sớm hơn. Các case cuối phiên chỉ chứa anchor/context/candidates/cutoff.

## 7. Output và ranh giới truth

| Phần | Tệp | Ai dùng? |
|---|---|---|
| generated | `sessions.jsonl` | Scorer: thông tin case quan sát |
| generated | `interactions_train.jsonl` | Phản ứng đầu phiên |
| generated | `search_events.jsonl` | Query/reformulation trước cutoff |
| generated | `exposures.jsonl` | Cặp hiển thị/thứ tự |
| ground_truth | `session_intents.jsonl` | Evaluator: focus/directions/weights/mode |
| ground_truth | `intent_labels.jsonl` | Evaluator: relevance từng ứng viên |

Report/manifest ghi số sessions/labels/cặp thực tế, shortfall, hashes và nguồn C. Scorer dùng C prefix để tính importance baseline; true session weights chỉ evaluator/oracle dùng.

## 8. Sinh, kiểm tra, chạy tiếp

```powershell
python data/exp_d/build_exp_d.py --dry-run
python data/exp_d/build_exp_d.py
python data/exp_d/build_exp_d.py --validate-only
```

Từ gốc repository, Python 3.11+. Thiếu quota → partial/exit 2; allow-shortfall chỉ phục vụ khảo sát, không đổi dữ liệu sai thành hợp lệ. Output contract cũ dùng đường dẫn mới; không chạy hai generator cùng output.

[Scorer D](../../scripts/exp_d/README.md) giải thích estimator delta, unknown, relevance gate và F1/compliance. [Pilot D](samples/README.md) hướng dẫn dùng C pilot complete.

D không cần thêm bộ profile kiểm duyệt để chạy mock. Chất lượng trên ngữ nghĩa/người dùng thật là kiểm chứng tiếp theo, không được suy ra chỉ từ điểm simulator.
