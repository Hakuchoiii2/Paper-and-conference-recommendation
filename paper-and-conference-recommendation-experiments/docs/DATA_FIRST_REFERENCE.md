> **Tài liệu lịch sử, trước thiết kế 2.0 ngày 2026-10-09.** C/D và các quota/giới hạn ở dưới dùng nghĩa cũ; không dùng làm hướng dẫn hiện hành.
> Xem [protocol 2.0](EXPERIMENT_PROTOCOL.md) và [lệnh chạy mới](RUN_EXPERIMENTS.md). Yêu cầu hiện tại đã bao gồm code thực nghiệm.

# DS300 — README triển khai giai đoạn Data-first

> Cập nhật ngày 2026-10-03 theo yêu cầu Khải: mọi exp đọc trực tiếp
> `data/processed/papers.jsonl`; đã bỏ thư mục mẫu bài và script lấy mẫu.
> Yêu cầu mới nhất: chạy A bằng Qwen3 local để trích facet thật trước. B–E dùng
> `data/exp_a/generated/facets_silver.jsonl`; mock query/intent/nhãn theo rule/users/hành vi.
> B/C/D làm song song sau silver; E còn cần danh sách users D.
> Nội dung bên dưới lưu kế hoạch lịch sử; các hướng dẫn tạo fixture/corpus mock
> và lệnh build_fixture không còn áp dụng. Dùng [README hiện tại](../README.md)
> và [contract](../DATA_CONTRACT.md) làm hướng dẫn thực hiện.

> Tài liệu bàn giao cho GPT Work/Codex để bootstrap repository ở local, chuẩn bị dữ liệu cho Experiments A–E và tạo đợt push GitHub đầu tiên. Chỉ triển khai phần dữ liệu; chưa triển khai embedding, ranking model hoặc chạy thực nghiệm mô hình.

## 1. Nguồn, phạm vi và nguyên tắc thực hiện

Nguồn đã đọc: hội thoại **“Ghi nhớ cấu trúc file”**, ID `6abfa41e-3528-83ec-8a64-07e6dd38b3de`, gồm các lượt về data-first, phân công, global contract, mock data và quy mô dataset. Quyết định mới nhất trong hội thoại được ưu tiên hơn đề xuất cũ.

**Giới hạn nguồn:** bản kế hoạch DS300 được nhắc là đã upload nhưng không có trong workspace hoặc danh sách đính kèm truy cập được khi tạo README này. Vì vậy đây là execution plan dựa trên hội thoại đã đọc, gồm nội dung plan gốc được hội thoại tóm tắt; chưa phải bản đối chiếu trực tiếp với file DS300. Khi có file gốc, đối chiếu tên experiment, định nghĩa facet, nguồn nhãn và yêu cầu đánh giá trước khi freeze dataset thật. Những quy ước chi tiết bổ sung dưới đây là mặc định triển khai đề xuất, do Khải duyệt.

Mục tiêu hiện tại:

- Có repository tối thiểu, tài liệu và contract thống nhất để 5 người bắt đầu làm dữ liệu.
- Có một fixture chung 50 mock papers, samples A–E, generator tái lập được và validator chạy được.
- Chuẩn bị ingestion CSFCube + SciFact song song với các nhánh mock data.
- Tách input, nhãn đánh giá, latent truth và dữ liệu tương lai.
- Chuyển từ mock sang dữ liệu thật bằng cách chạy lại pipeline, giữ nguyên schema.

Không thuộc đợt triển khai này: chọn SPECTER2/SBERT, quyết định embedding dimension, cosine/dot product, huấn luyện, temporal decay model, UI hoặc báo cáo kết quả mô hình. Annotation bằng LLM cho silver là công việc dữ liệu, nhưng chưa gọi API hàng loạt khi chưa có cấu hình và ngân sách.

**Mock data không cần đợi embedding hoặc unified corpus.** Điều kiện mở việc là global contract nhỏ đã chốt và fixture chung hợp lệ. Dataset thật cuối cùng vẫn cần corpus, facet và nguồn nhãn tương thích.

## 2. Phân công và quyền sở hữu

| Người | Ownership hiện tại | Deliverables | Ranh giới trách nhiệm |
|---|---|---|---|
| **Khải — nhóm trưởng** | Global contract, repo convention, corpus và tích hợp | `DATA_CONTRACT.md`, fixture chung, corpus ingestion/dedup/ID map/splits, validator chung, review PR | Chốt schema và quy ước dùng chung; không giao quyền quyết định này riêng cho Kiên |
| **Kiên** | Exp A — facet annotation | `data/exp_a/README.md`, `docs/FACET_GUIDELINE.md`, annotation prompt, sample silver/gold, review protocol | Đề xuất định nghĩa/normalization facet; Khải chốt contract; embedding spec để sau |
| **Phi** | Exp B — facet retrieval dataset | README B, queries/candidates, relevance labels, quy tắc chuyển nhãn nguồn, generator | Không tạo corpus hoặc ID paper riêng |
| **Quỳnh** | Exp C — explicit intent dataset | README C, intent templates/constraints, generator và satisfaction labels | Dùng facet vocabulary và paper IDs chung |
| **Phú** | Exp D/E — implicit preference và temporal dataset | README D/E, users, interactions, latent profiles, temporal profiles, holdout | E dùng cùng user IDs của D; một người giữ hai phần để tránh lệch user schema |

Khải chịu trách nhiệm review thay đổi global contract. Mỗi owner chịu trách nhiệm chất lượng, documentation và validation dataset mình. Đợt bootstrap do GPT Work thực hiện không thay thế việc human review gold annotation.

## 3. Quy mô: smoke test trước, target sau

| Dataset | Minimum trong hội thoại | Target làm việc được đề xuất |
|---|---:|---:|
| Unified corpus | 3.000 unique papers | **6.000**, khoảng thực dụng 5.000–8.000 |
| A — gold | 200 papers | **400**, khoảng 300–500 |
| A — silver | Toàn bộ corpus đủ điều kiện | **6.000** nếu corpus đạt 6.000 |
| B — retrieval | 100 queries | **300 queries × 100 candidates ≈ 30.000 pairs** |
| C — intent | 500 cases | **1.500 cases**, 5–10 intent types |
| D — users/behavior | 100 users | **300 users × 50 interactions = 15.000** |
| E — temporal | 100 users, 3–5 periods | **Cùng 300 users của D × 4 periods = 1.200 profiles**, khoảng 15.000–20.000 interactions |

Đây là mục tiêu workload, không phải bảo đảm statistical power hoặc số lượng nguồn có sẵn. Sau ingestion phải báo cáo unique count thực tế. Nếu CSFCube + SciFact hoặc nhãn chuẩn không đủ đạt target, giữ số thực, ghi gap và đề xuất nguồn bổ sung; không duplicate paper/query để đạt chỉ tiêu. Không dùng nhãn SciFact như relevance labels cho B nếu chưa có mapping được kiểm chứng.

Đợt bootstrap chỉ cần: 50 mock papers có facet; A có sample silver và sample gold minh họa; B có 5 queries × 10 candidates; C có 20 cases phủ các intent types; D có 5 users × 10 interactions; E có cùng 5 users × 4 periods, tối thiểu 2 interactions/period. Đây là kích thước smoke test đề xuất, không thay target dataset cuối.

Với C, một phân bổ đúng tổng 1.500: 6 types × 200 và 2 types × 150. Ví dụ 8 types: `same_problem`, `same_problem_different_method`, `same_method_different_problem`, `similar_task`, `different_dataset`, `same_problem_same_method`, `similar_contribution`, `mixed_intent`. Owner phải định nghĩa constraints cụ thể cho từng type; không chỉ dựa vào tên type. Hội thoại có vài danh sách intent khác nhau: dùng một danh sách versioned sau khi Khải chốt, không trộn chúng ngầm.

## 4. Repository bootstrap tối thiểu

Nếu đã có repo, kiểm tra và tái sử dụng cấu trúc đang có; không tạo repo thứ hai hoặc ghi đè file người khác. Nếu `.codegraph/` tồn tại ở repo root, dùng CodeGraph trước khi tìm/đọc code. Không tự index repository mới.

```text
ds300/
├── README.md                         # Có thể dùng tài liệu này làm README ban đầu
├── DATA_CONTRACT.md                  # Một nguồn chuẩn cho mọi experiment
├── .gitignore
├── configs/
│   └── data.json                     # Seed, paths, sample sizes, contract version
├── docs/
│   ├── FACET_GUIDELINE.md
│   └── EXPERIMENT_README_TEMPLATE.md
├── schemas/
│   └── ...                          # Schema theo từng loại record thực sự sử dụng
├── data/
│   ├── raw/                         # CSFCube/SciFact; không commit bản tải lớn
│   ├── processed/                   # Corpus thật, ID map, splits; tạo sau ingestion
│   ├── fixtures/
│   │   ├── papers.jsonl
│   │   ├── facets.jsonl
│   │   └── manifest.json
│   ├── exp_a/
│   │   ├── README.md
│   │   └── samples/
│   ├── exp_b/
│   │   ├── README.md
│   │   └── samples/
│   ├── exp_c/
│   │   ├── README.md
│   │   └── samples/
│   ├── exp_d/
│   │   ├── README.md
│   │   └── samples/
│   └── exp_e/
│       ├── README.md
│       └── samples/
├── scripts/
│   ├── build_fixture.py
│   ├── build_corpus.py               # Khi triển khai ingestion thật
│   ├── build_exp_a.py
│   ├── build_exp_b.py
│   ├── build_exp_c.py
│   ├── build_exp_d.py
│   ├── build_exp_e.py
│   └── validate_all.py
└── tests/
    └── test_data_validation.py        # Một check nhỏ gồm positive/negative cases
```

Chỉ tạo script có chức năng chạy được; không thêm framework hoặc hàng loạt module rỗng. Bắt đầu bằng Python stdlib + JSON/JSONL; thêm dependency khi công việc thực tế cần. Corpus thật có thể xuất thêm `papers.parquet` nếu project đã dùng Parquet; mọi experiment vẫn tham chiếu canonical `paper_id`. Chốt một định dạng corpus chính trong contract, tránh hai bản độc lập dễ lệch nhau.

`samples/` chứa bộ nhỏ được commit, theo cùng cấu trúc file như dataset hoàn chỉnh. Output lớn tạo vào `data/exp_x/generated/` và được ignore. File manifest của mỗi bộ ghi contract version, mock/real, seed, generator version/commit, input dataset version/checksum và record counts.

## 5. Global data contract — Khải chốt trước

Viết một `DATA_CONTRACT.md` ở root; các README A–E link về đây thay vì định nghĩa lại.

| Hạng mục | Quy ước triển khai đề xuất |
|---|---|
| Encoding/format | UTF-8; JSONL: một object trên một dòng; JSON cho manifest/config/splits |
| Contract version | `1.0`; thay đổi field/meaning phải cập nhật version và docs |
| Paper ID | `P000001`, regex `^P[0-9]{6}$` |
| User ID | `U0001`, regex `^U[0-9]{4}$` |
| Intent/query ID | `I0001`, `Q0001`, lần lượt `^I[0-9]{4}$`, `^Q[0-9]{4}$` |
| Facet keys | Chính xác `problem`, `task`, `method`, `dataset`, `contribution` |
| Facet values | List string; có thể nhiều giá trị; missing = `[]`, không dùng `null`/string |
| Direction | `similar`, `different`, `ignore`; constraints có đủ 5 keys, mặc định `ignore` |
| Interaction | `click`, `view`, `save`, `like`, `dislike` |
| Timestamp | ISO-8601 có timezone; mặc định UTC `2026-01-10T10:00:00Z` |
| Seed | `42`; ghi seed/input version vào manifest; ổn định thứ tự trước sampling |
| Split | Chính sách cố định, mapping versioned; không tự chia lại trong mỗi generator |

Các ví dụ cũ trong hội thoại có `P0001`, `P0102`, `I000123`: chuẩn hóa về độ rộng trên trong đợt bootstrap. Không đưa nhiều kiểu ID vào dataset mới.

Canonical paper record:

```json
{"paper_id":"P000001","source":"mock","source_id":"mock-001","title":"Mock paper 001","abstract":"Synthetic abstract for pipeline testing.","year":null,"domain":"synthetic"}
```

Với corpus thật: lưu ID nguồn dưới dạng string, title/abstract đã chuẩn hóa, year integer hoặc null, domain theo metadata có bằng chứng. Không gán toàn bộ SciFact thành computer science. Khải duy trì mapping `(source, source_id) → paper_id`; paper trùng giữa nguồn giữ toàn bộ provenance trong ID map. ID đã cấp không đổi khi bổ sung hoặc đổi thứ tự corpus.

Mock và real được tách bằng thư mục + manifest `dataset_kind`, không được merge fixture vào corpus thật. Cùng một chuỗi ID trong hai bộ độc lập không có nghĩa là cùng paper. Generator phải đọc đúng catalog của bộ đang chạy.

Facet record:

```json
{"paper_id":"P000001","problem":["cold-start recommendation"],"task":["recommendation"],"method":["graph contrastive learning"],"dataset":["MovieLens"],"contribution":[]}
```

Guideline A phải phân biệt problem/task và method/contribution; dùng tên concept nhất quán qua alias map; không đoán facet không có bằng chứng trong title/abstract. Corpus thô giữ nguyên nội dung nguồn; normalization facet không sửa abstract gốc.

## 6. README riêng cho từng experiment

Mỗi `data/exp_x/README.md` có đúng 7 phần cốt lõi sau, có thể dùng tiêu đề tiếng Anh để đồng bộ:

1. **Purpose:** câu hỏi experiment, owner, giới hạn mock/synthetic.
2. **Input format:** paths, required fields, reference tới global contract; trường nào model được đọc.
3. **Output format:** file names, đơn vị record, input/labels/hidden truth tách thế nào.
4. **Field definitions:** meaning, type, enum, missing values, uniqueness key.
5. **Example:** ít nhất một input/output pair hợp lệ dùng fixture chung.
6. **Generation rules:** nguồn, seed, sampling, positives/negatives, sizes, splits, lệnh chạy.
7. **Validation rules:** structural và semantic checks, leakage checks, acceptance criteria.

Không cần một bản đặc tả lớn chặn các owner bắt đầu. Chốt format nhỏ trước; chi tiết generator được bổ sung qua PR, giữ schema chung.

## 7. Dataset và mock-data preparation cho A–E

### A — Facet annotation

- Input: canonical paper catalog, cùng guideline/prompt version.
- Output: `facets_silver.jsonl` và `facets_gold.jsonl`; giữ annotation provenance và review status trong metadata riêng keyed by `paper_id`.
- Silver: annotation tự động; gold thật: human review, không đổi tên silver thành gold để đủ số.
- Gold 400 là subset của corpus; có thể overlap silver để so sánh. Split gold papers độc lập với việc chỉnh prompt; không dùng held-out gold để tối ưu prompt.
- Mock gold chỉ là expected fixture cho kiểm thử, manifest ghi `mock`; không đưa vào số gold thật.
- Kiên chuẩn bị guideline, alias/normalization rules, prompt, ví dụ khó và quy trình xử lý disagreement. Human review một subset chung bởi hai người trước khi mở rộng để kiểm tra mức thống nhất.

### B — Facet retrieval

Observable `retrieval_queries.jsonl`:

```json
{"query_id":"Q0001","query_paper_id":"P000001","target_facet":"method","candidate_ids":["P000002","P000003"]}
```

Ground truth `retrieval_labels.jsonl`:

```json
{"query_id":"Q0001","candidate_id":"P000002","relevance":2}
```

- Mặc định internal relevance `0/1/2` = irrelevant/partial/high; ghi mapping nguồn riêng. Giữ raw source label, không ép label nguồn khác scale mà không giải thích.
- Candidate set có positive, hard negative và easy negative; mock có thể chọn bằng facet overlap/alias đã chốt, chưa cần embedding.
- Không có query paper trong candidate set; không duplicate candidate; tối thiểu một positive mỗi query được giữ để đánh giá.
- Chưa biết label thì chưa judged; không tự coi là negative. Các pair benchmark đã release phải có nhãn hoặc chính sách unjudged rõ ràng.
- Nếu bổ sung query hoặc facet không có native judgments, ghi `synthetic`/`human` trong label provenance, tách thống kê khỏi native benchmark.

### C — Explicit intent

Observable `intents.jsonl`:

```json
{"intent_id":"I0001","query_paper_id":"P000001","intent_type":"same_problem_different_method","constraints":{"problem":"similar","task":"ignore","method":"different","dataset":"ignore","contribution":"ignore"},"candidate_ids":["P000002","P000003"]}
```

Ground truth `intent_labels.jsonl`:

```json
{"intent_id":"I0001","candidate_id":"P000002","satisfies_intent":true}
```

- Sinh bằng code từ fixture/corpus facets; templates và direction semantics được versioned.
- Mock dùng exact normalized concept/alias hoặc rule được công bố, không dùng embedding chưa có. Rule này kiểm tra pipeline; không đại diện đầy đủ semantic similarity trên dữ liệu thật.
- Missing facet không tự động thỏa `different`; mặc định candidate thiếu facet đang constrain là ineligible, phải ghi rule trong README.
- Mỗi case có candidate thỏa và không thỏa; hard negatives chỉ vi phạm một constraint khi khả thi. Trường hợp không có candidate đủ điều kiện phải skip và báo số lượng, không bịa positive.
- Seed tái lập được; số intent độc lập không đồng nghĩa số query papers độc lập. Split nhóm theo query paper để tránh cùng anchor xuất hiện ở train/test.

### D — Implicit user preference

Observable `users.jsonl` chỉ chứa user IDs/metadata quan sát được. `interactions_train.jsonl` và `interactions_test.jsonl` chứa behavior:

```json
{"user_id":"U0001","paper_id":"P000002","interaction_type":"like","timestamp":"2026-01-10T10:00:00Z"}
```

`ground_truth/latent_user_profiles.jsonl`:

```json
{"user_id":"U0001","latent_preferences":{"problem":{"cold-start recommendation":0.8},"method":{"graph contrastive learning":1.0,"matrix factorization":-0.5}}}
```

- Sinh latent profile trước, rồi sinh exposure/interaction theo preferences + noise có seed; không random behavior hoàn toàn rồi gán preference ngược lại.
- Weights mặc định trong `[-1,1]`; rule từ affinity sang interaction type được ghi rõ và tái lập được.
- Target 50 interactions/user: 30 past + 20 future, split theo thời gian từng user. Test chỉ evaluation loader đọc, không dùng để xây profile.
- Nếu tương lai cần ranking evaluation, lưu exposure/candidate pool của từng sự kiện; không coi mọi unobserved paper là negative.
- Hidden latent preferences không nằm trong `users.jsonl` observable. Synthetic behavior dùng để kiểm tra giả thuyết simulator, không được trình bày như dữ liệu user thật.

### E — Temporal preference

- Dùng cùng `users.jsonl` và user IDs của D; tạo temporal scenario riêng, không tính E thành thêm 300 users mới.
- `ground_truth/temporal_profiles.jsonl` chứa `(user_id, period)` và preference weights cùng format D; 4 periods mặc định: old interest → transition → new interest → stabilization.
- Quy định `start_timestamp`, `end_timestamp` theo interval `[start,end)`; periods liên tiếp, không overlap.
- Sinh interactions theo profile của mỗi period. E có stream riêng để biểu diễn drift; không cần byte-identical interactions với D.
- Có nhóm stable và nhóm drift theo tỷ lệ cấu hình; ghi tỷ lệ trong manifest để phân biệt drift effect với random noise.
- Holdout theo thời gian, ví dụ periods 1–3 làm history, period 4 làm test; không xây observable profile bằng truth của period tương lai.
- Các time cutoffs của D/E khác nhau phải công khai, không tái sử dụng nhãn split của D cho E mà không kiểm tra lại.

## 8. Corpus thật và thay fixture

Khải triển khai song song:

1. Xác định release/source thực của CSFCube và SciFact, điều kiện sử dụng/chia sẻ, version và checksum; chưa có URL xác nhận thì ghi TODO, không đoán URL.
2. Import metadata vào canonical schema; không mất source IDs hoặc nhãn nguồn.
3. Deduplicate bằng identifier có sẵn, sau đó normalized title và kiểm tra các trường hợp nghi ngờ. Không gộp paper chỉ vì chủ đề giống nhau.
4. Cấp canonical IDs qua ID map ổn định, xuất unique counts và thống kê domain/source/overlap/missing abstracts.
5. Freeze paper split mapping. Giữ native benchmark split nếu có; split mới dùng seed và rule được công bố.
6. Cung cấp subset corpus thật có facet đã review để B/C/D/E chuyển sang dữ liệu thật trước khi silver toàn corpus hoàn tất.
7. Chạy lại generator với catalog/facets thật; rebuild labels và manifests. Không chỉ search-replace mock IDs vì quan hệ facet/ground truth cũng thay đổi.

Gold A và native relevance B cần người kiểm tra; không yêu cầu full gold/silver hoàn tất mới cho mọi người viết generator.

## 9. Validation và chống leakage

`python scripts/validate_all.py --dataset-kind mock` là acceptance gate đầu tiên. Validator lỗi phải trả exit code khác 0 và chỉ rõ file, dòng/key và nguyên nhân. Lệnh real chỉ chạy khi dữ liệu thật tồn tại; không silent-pass bằng cách bỏ qua file bắt buộc bị thiếu.

Các checks tối thiểu:

- Parse JSON/JSONL, required fields/types/enums, facet keys và timezone timestamps đúng contract.
- ID unique trong catalog; foreign keys resolve trong catalog đang chạy; compound keys B/C labels và E profiles unique.
- A: một record/paper/tier, đủ 5 facet lists; gold subset corpus; provenance/review status phân biệt mock/silver/gold.
- B/C: candidate sets hợp lệ, query không là candidate; labels thuộc candidate set; không thiếu/nhân đôi nhãn theo chính sách của bộ judged.
- C: constraints phù hợp template; label đúng rule công bố; đủ positive/negative hoặc case bị skip có lý do.
- D/E: user/paper refs hợp lệ; weights hữu hạn trong range; periods/timestamps đúng boundary; mỗi user có history và holdout.
- Tái lập: chạy cùng seed + input version cho cùng nội dung output; bỏ thời điểm build khỏi so sánh nội dung deterministic.
- Split leakage: query anchors/group IDs không tràn giữa train/dev/test; không yêu cầu candidate corpus disjoint nếu protocol là shared retrieval catalog. Nếu muốn đánh giá unseen-paper thì định nghĩa protocol riêng.
- Temporal leakage: latest train event trước earliest test event theo user; events cùng timestamp nằm cùng phía cutoff.
- Label leakage: prediction/profile-building inputs không chứa relevance, satisfaction labels, latent weights hoặc future interactions. Folder separation phải đi kèm loader allowlist/explicit paths.
- Không có mock refs trong dataset real; manifests thống nhất version và actual counts.

Để kiểm tra validator thực sự bắt lỗi, giữ một self-check nhỏ với valid fixture và ít nhất các corrupted cases: unknown paper ref, invalid facet key, timestamp thiếu timezone và temporal train/test overlap. Không chỉ chạy validator trên bộ đúng rồi kết luận chống leakage đã đủ.

## 10. Git workflow và đợt push đầu tiên

Branches theo hội thoại:

```text
main
data/core-corpus        # Khải
data/exp-a-facets       # Kiên
data/exp-b-retrieval    # Phi
data/exp-c-intent       # Quỳnh
data/exp-de-user        # Phú
```

- Bootstrap contract/fixture/validator chung được merge trước để mọi owner branch từ cùng baseline.
- Mỗi owner làm PR cho README + samples + generator; Khải review schema/integration.
- Thay đổi `DATA_CONTRACT.md`, shared schemas, configs, ID map hoặc split policy phải được Khải review trước khi merge. Đây là quy ước review; bật branch protection/CODEOWNERS nếu repo hỗ trợ và nhóm yêu cầu.
- Không commit raw corpus lớn, generated full datasets, embeddings, API keys, `.env`, caches hoặc môi trường Python. Commit docs, code, schemas, small samples và metadata tái tạo dữ liệu. Lưu output lớn theo nguồn/lưu trữ được nhóm chốt.
- Kiểm tra diff trước commit, stage đúng file task; không force-push hoặc ghi đè lịch sử có sẵn.
- Repo path và GitHub remote chưa được cung cấp trong hội thoại. GPT Work phải đọc remote đã cấu hình hoặc lấy URL từ Khải trước thao tác push; không tự đoán owner/repo, visibility hoặc tạo remote khác.

Ví dụ thứ tự lệnh sau khi đã ở đúng repository và biết remote:

```bash
git status
git remote -v
python scripts/build_fixture.py --seed 42
python data/exp_a/build_exp_a.py --dataset-kind mock --seed 42
python scripts/build_exp_b.py --dataset-kind mock --seed 42
python scripts/build_exp_c.py --dataset-kind mock --seed 42
python scripts/build_exp_d.py --dataset-kind mock --seed 42
python scripts/build_exp_e.py --dataset-kind mock --seed 42
python scripts/validate_all.py --dataset-kind mock
python tests/test_data_validation.py
git diff --check
```

Đây là CLI cần implement, không phải bằng chứng các script đã tồn tại/chạy. Sau khi kiểm tra staged diff, commit với message ví dụ `Bootstrap DS300 data contracts and mock datasets`; push branch bootstrap vào remote được xác nhận và tạo PR. Không claim đã push khi chưa có kết quả remote. README hiện tại chỉ là tài liệu bàn giao; không tự thực hiện GitHub push từ việc tạo file này.

## 11. Thứ tự thực hiện ngay

### Đợt 0 — GPT Work bootstrap ở local

1. Kiểm tra repo/path/current branch/remote và file có sẵn; đọc instructions áp dụng. Không sửa project khác.
2. Dựng structure tối thiểu ở mục 4, README root, `.gitignore` và README template.
3. Viết `DATA_CONTRACT.md` theo mục 5; ghi defaults mới để Khải review một lần trước khi cả nhóm dùng.
4. Tạo fixture chung 50 papers với nhiều facet values, missing facets và cặp positive/hard-negative đủ cho mock cases.
5. Tạo 5 README A–E cùng samples nhỏ; implement generator chạy được cho các samples. Không tạo samples JSON hàng loạt bằng tay mà thiếu generator.
6. Viết validator và self-check; generate hai lần để kiểm tra reproducibility; sửa lỗi trước commit.
7. Kiểm tra diff/manifest/counts, commit/push bootstrap khi remote sẵn sàng; ghi branch/commit/PR và lệnh chạy vào handoff.

### Đợt 1 — 5 người triển khai song song

- Khải: ingestion + ID map + dedup + frozen splits, hỗ trợ validator.
- Kiên: guideline/prompt/review protocol, pilot real annotations.
- Phi: B sampling và mapping nhãn nguồn.
- Quỳnh: C templates/constraints/label rules và coverage.
- Phú: D latent profiles/behavior; E periods/drift/time holdout dùng cùng user identities.

Không chờ corpus hoàn chỉnh hoặc embedding. Owner dùng fixture chung để hoàn thiện generator và interface trước.

### Đợt 2 — Tích hợp dữ liệu thật

Khải xuất corpus version đầu → Kiên cung cấp pilot facets → B/C/D/E rerun trên subset thật → validate/refine rules → scale dần tới targets khả thi → review gold/labels → freeze dataset release. Ghi rõ phần chưa đạt target và chất lượng/nguồn nhãn, thay vì lấp bằng synthetic không công bố.

## 12. Definition of Done của phase hiện tại

**Bootstrap hoàn tất khi:**

- [ ] Global contract có owner/version và được Khải chốt.
- [ ] A–E có README đủ 7 phần, examples hợp lệ và team ownership rõ.
- [ ] Fixture chung, generators và manifests tái lập được.
- [ ] Validator/self-check pass, negative cases bị bắt và hidden truth/future data được tách.
- [ ] Repo diff sạch, không chứa secret/output lớn; commit/branch và trạng thái push được báo đúng.
- [ ] Nhóm có thể checkout baseline và bắt đầu từng nhánh ngay.

**Data-first release hoàn tất khi:**

- [ ] Corpus thật có provenance, stable ID map, dedup report và split mapping.
- [ ] Dataset A–E có counts thực tế, source/label provenance, rules và manifests.
- [ ] Gold thật đã review, nhãn retrieval/intent được kiểm tra, synthetic limitations được công bố.
- [ ] Validation/leakage checks pass trên dữ liệu thật và các loaders dự kiến.
- [ ] Bản kế hoạch DS300 gốc được đối chiếu khi truy cập được; mọi khác biệt được ghi lại trước freeze.

Đợt push đầu tiên chỉ cần đạt bootstrap; không cần giả vờ đã có full dataset hoặc model results. Sau data release mới mở phase embedding/model/evaluation theo kế hoạch DS300 được xác nhận.
