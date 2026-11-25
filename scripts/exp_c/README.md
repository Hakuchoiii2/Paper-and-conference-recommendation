# Exp C — Suy profile từ lịch sử và tìm kiếm

[Chỉ mục script](../README.md) · [Generator C](../../data/exp_c/README.md) · [Giao diện chung](../BASELINE_GUIDE.md)

## 1. C kiểm tra điều gì?

Các bài user đọc/thích/không thích và câu tìm kiếm có giúp suy profile để khuyến nghị bài tiếp theo không? Phân biệt **score xếp hạng bài** và **importance của năm facet**.

Baseline có popularity, text_history, facet_no_search, facet_history. Đây là estimator lexical, chưa có encoder/model học tham số. Latent profile được generator sinh trước hành vi và giữ kín.

## 2. Một user và một case gồm gì?

| Dữ liệu quan sát | Cách dùng |
|---|---|
| `users.jsonl` | Danh tính chung C/D/E |
| `interactions_train.jsonl` | Mục tiêu 30 phản ứng đầu/user |
| `search_events.jsonl` | Query trước cutoff |
| `exposures.jsonl` | Bài hiển thị, query, thứ tự |
| `cases.jsonl` | user_id, 20 candidate_ids, cutoff |
| Corpus/full silver A | Title/abstract và năm concept sets |

Evaluator đọc riêng latent_user_profiles và interactions_test. Mục tiêu 300 users × 50 events = 9.000 history + 6.000 holdout, 300 cases.

Candidate IDs là 20 bài holdout từ simulator; **phản ứng tương lai bị giấu**. C chưa retrieval toàn corpus.

## 3. Generator tạo đáp án thế nào?

```text
concept thích/không thích + importance thật
→ chọn bài/exposure/query
→ utility từ profile ẩn + noise
→ feedback → tách 30 lịch sử / 20 holdout
```

Profile thật có trước log, nên có đáp án chấm importance mà không cần bộ profile kiểm duyệt. Đáp án là mô phỏng, chưa phải sở thích người thật. [Generator C](../../data/exp_c/README.md) giải thích utility/sampling cụ thể.

## 4. Profile baseline cộng evidence thế nào?

Feedback weights: **dislike −1, view 0, click 1, save 2, like 3**.

Với mỗi facet của bài tương tác, chia feedback weight đều cho các concept của facet đó, rồi cộng qua lịch sử. Facet rỗng không góp evidence.

Search parser đọc concept có trong A, hỗ trợ facet prefix và mock patterns như `method: more papers using GNN`, `method: alternatives to GNN`, `without ...`. Include góp +1, exclude góp −1. Chưa hiểu query tự nhiên tùy ý bằng model ngữ nghĩa.

Ví dụ facet method:

| Quan sát | Đóng góp |
|---|---|
| Like bài chỉ có GNN | GNN +3 |
| Save bài có GNN và contrastive learning | Mỗi concept +1 |
| Dislike bài chỉ có SVM | SVM −1 |
| Search include GNN | GNN +1 |

Tổng **[GNN:5, contrastive:1, SVM:−1]**, normalize L2 → khoảng **[.962,.192,−.192]**.

Bài khác trong exposure chưa phản ứng không được coi là dislike. Exposure kiểm tra quan hệ quan sát; profile hiện dùng phản ứng và query đã ghi.

## 5. Importance và candidate score tính riêng thế nào?

```text
mass_f = Σ |signed count của concept trong facet f|
importance_f = mass_f / Σ mass của năm facet
profile_vector_f = unit_vector(signed counts)
candidate_vector_f = unit_vector({concept của candidate: 1})
score = Σ importance_f × dot(profile_vector_f, candidate_vector_f)
```

Tổng mass 0 → importance 1/5. Estimator đo evidence còn lại sau cộng/trừ; chưa tách hoàn toàn quan tâm facet khỏi sở thích concept.

Trong ví dụ method: candidate chỉ GNN nhận dot .962; chỉ SVM nhận −.192; GNN+contrastive nhận khoảng .816. Đây là không gian **concept chính xác**, khác facet TF-IDF ở B/D.

Ví dụ importance [.15,.15,.45,.10,.15]:

| Candidate | Dot problem/task/method/dataset/contribution | Score |
|---|---|---:|
| Y1 | [.7,.6,.96,.3,.4] | .717 |
| Y2 | [.8,.6,−.19,.6,.5] | .2595 |

Y1 lên trước vì hợp method user thích; negative preference kéo điểm xuống. Hòa điểm theo paper_id.

## 6. Bốn model so sánh gì?

| Model | Profile/ranking | Search? | Importance MAE? |
|---|---|---|---|
| `popularity` | Tổng feedback dương toàn bộ users trong history | Không | N/A |
| `text_history` | Pooling TF-IDF title/abstract theo signed feedback, thêm vector query rồi normalize | Có | N/A |
| `facet_no_search` | Concept profile từ phản ứng | Không | Có |
| `facet_history` | Cùng profile, thêm include/exclude query | Có | Có |

Text_history cũng có search để so biểu diễn với facet_history cùng nguồn tín hiệu. Facet_no_search vs facet_history là **search ablation**.

Popularity bỏ dislike, view không góp điểm; đối chứng không cá nhân hóa. Không tự gán importance MAE 0 cho model không trả importance.

## 7. Runner và evaluator làm gì?

1. Kiểm tra corpus/A/C manifests.
2. Nhóm cases theo cutoff, lọc reactions/queries/exposures timestamp < cutoff.
3. Xây bốn kiểu profile/score.
4. Xếp 20 candidates/user/model.
5. Evaluator đổi holdout dislike/view/click/save/like thành relevance 0/0/1/2/3.
6. Chấm ranking và so importance với latent weights.
7. Xuất kết quả từng case, tổng hợp và manifest.

“Học profile” hiện là cộng evidence, **không gradient training**. Model trainable không được fit/tune bằng holdout đang chấm.

## 8. Chạy và đọc output

```powershell
python data/exp_c/build_exp_c.py --dry-run
python data/exp_c/build_exp_c.py
python data/exp_c/build_exp_c.py --validate-only
python scripts/exp_c/run_exp_c.py --dry-run
python scripts/exp_c/run_exp_c.py --ks 5 10
```

Mặc định dưới `results/exp_c/`; dùng output mới/overwrite. Đủ 300 cases có 1.200 predictions.

So **nDCG/Recall/Precision/MRR** trên holdout và **importance_mae** cho hai facet models. MAE thấp = gần năm latent weights hơn; ranking tốt = bài có feedback tích cực/cao lên đầu. Hai điểm có thể không cùng cải thiện.

Evaluator chưa có chỉ số riêng chấm độ khôi phục từng concept preference. Importance MAE không có nghĩa toàn bộ profile đã đúng.

Đọc report.md/report.json/details.jsonl; [baseline guide](../BASELINE_GUIDE.md) giải thích sáu tệp/công thức.

## 9. Thành viên C phát triển gì?

Thử encoder freeze để pooling embedding bài/facet theo reactions và queries; giữ baseline lexical. Câu hỏi chính là profile và giá trị của search.

Thay encoder chỉ đổi biểu diễn/ranking. Nếu giữ estimator mass, **importance MAE không tự đổi**; muốn cải thiện MAE phải nghiên cứu importance estimator.

Bàn giao generator C complete sớm để D/E chạy riêng. D/E không cần predictions C; profile model mới tích hợp sau qua phiên bản đã thống nhất.
