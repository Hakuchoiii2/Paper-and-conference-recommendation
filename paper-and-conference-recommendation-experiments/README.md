# DS300 — Khuyến nghị bài báo và hội nghị theo năm facet

Dự án nghiên cứu khuyến nghị **bài báo và hội nghị (conference)** dựa trên **problem, task, method, dataset, contribution**. Corpus dùng chung hiện gồm 4.210 title/abstract; A trích facet bằng Qwen local, B–E cung cấp baseline khuyến nghị bài báo để từng thành viên nghiên cứu và bổ sung phương pháp. Nhánh khuyến nghị hội nghị thuộc phạm vi đề tài, đang cần dữ liệu và thiết kế thực nghiệm riêng.

B–E hiện dùng dữ liệu khuyến nghị mô phỏng trên bài báo thật và facet silver. Encoder ngữ nghĩa, retrieval toàn corpus và reranker là hướng phát triển; chưa phải thành phần đã tích hợp trong baseline.

## Tổng quan đề tài

Đề tài hướng tới hệ khuyến nghị hỗ trợ người nghiên cứu **tìm bài báo để tham khảo và tìm hội nghị phù hợp với hướng nghiên cứu hoặc nội dung bài viết**. Khuyến nghị bài báo sử dụng nội dung đang đọc, sở thích tích lũy và nhu cầu ở phiên hiện tại. Một bài có thể liên quan về vấn đề nghiên cứu nhưng khác phương pháp; sở thích của người dùng cũng có thể đổi theo quá trình đọc và tìm kiếm.

Mỗi bài được mô tả qua năm góc nhìn: **problem** — vấn đề nghiên cứu; **task** — nhiệm vụ cụ thể; **method** — phương pháp; **dataset** — dữ liệu sử dụng; **contribution** — đóng góp được bài báo trình bày. Concept trích xuất đi kèm câu dẫn chứng để truy nguồn và kiểm tra.

Ví dụ, người dùng đang đọc bài về phân loại nút trên đồ thị bằng GNN và muốn tìm **cùng vấn đề nhưng dùng phương pháp khác**. Hệ thống hướng tới việc kết hợp bài mốc, phản ứng và câu tìm kiếm để suy nhu cầu này, điều chỉnh cách xếp hạng theo từng facet, rồi cập nhật profile khi có hành vi mới.

Với hội nghị, hướng đề xuất là đối chiếu năm facet của bài viết hoặc profile nghiên cứu với hồ sơ chủ đề của từng conference. Hồ sơ conference dự kiến được xây từ mô tả phạm vi/chủ đề và các bài đã công bố có nguồn, mốc thời gian rõ ràng. Đầu ra hướng tới danh sách hội nghị được xếp hạng kèm lý do phù hợp theo facet; mức phù hợp nội dung không phải dự đoán khả năng được nhận bài.

Luồng nghiên cứu chung gồm: **trích facet có dẫn chứng → biểu diễn bài và sở thích nghiên cứu → xếp hạng bài báo hoặc hội nghị phù hợp**. Nhánh bài báo bổ sung suy hướng tương tự/khác biệt trong phiên và cập nhật profile theo thời gian. A–E hiện kiểm tra chất lượng extraction và các thành phần khuyến nghị bài báo; nhánh conference chưa có generator, scorer hoặc bộ đánh giá riêng trong A–E.

## Tính mới đề xuất và đóng góp

Trọng tâm đóng góp dự kiến là **kết hợp profile dài hạn với ý định theo facet của phiên hiện tại, đồng thời thích ứng khi sở thích thay đổi**, trên cùng hệ biểu diễn năm facet có dẫn chứng; từ đó nghiên cứu sử dụng biểu diễn này cho cả khuyến nghị bài báo và hội nghị.

| Hướng đóng góp | Nội dung đề xuất | Thực nghiệm kiểm chứng |
|---|---|---|
| C1 — Biểu diễn năm facet có dẫn chứng | Tổ chức nội dung bài thành năm loại thông tin, giữ liên kết concept–evidence và đánh giá tác dụng của việc tách/gán trọng số facet | A kiểm tra extraction; B so whole-text, equal-facet và weighted-facet |
| C2 — Xếp hạng theo hướng của phiên | Giữ ngữ cảnh liên quan, suy facet người dùng muốn tương tự hoặc khác biệt từ query/phản ứng, rồi sử dụng hướng dự đoán để xếp hạng | D so mặc định similar, suy hướng từ hành vi và bổ sung search; đo cả direction và compliance |
| C3 — Profile thích ứng từ hành vi và tìm kiếm | Suy concept preferences/importance, kết hợp tín hiệu đọc và search, cập nhật ảnh hưởng của lịch sử theo thời gian | C kiểm tra profile/search; E so static, recent và decay trên nhóm stable/drift |
| C4 — Khuyến nghị hội nghị theo facet | Đối chiếu nội dung bài viết hoặc profile nghiên cứu với hồ sơ conference, hướng tới xếp hạng và giải thích mức phù hợp theo từng facet | Cần catalog conference, nhãn phù hợp và thực nghiệm riêng; dự kiến so biểu diễn toàn văn với biểu diễn theo facet, chưa được A–E kiểm chứng |

Đây là **định hướng tính mới cần chứng minh**. Việc dùng facet, embedding hoặc profile riêng lẻ đã có tiền lệ; dùng năm facet hay ghép các thành phần chưa đủ để khẳng định mới so với nghiên cứu trước. Nhóm cần đối chiếu các phương pháp gần nhất và dùng ablation để xác định phần cải tiến thực sự có ích. Kết quả mock hiện phục vụ kiểm tra cơ chế, chưa xác nhận hiệu quả với người dùng thật.

Chi tiết đối chiếu công trình và phạm vi đề xuất nằm trong [nghiên cứu liên quan](docs/FACET_RECOMMENDATION_RESEARCH.md) và [kế hoạch thực nghiệm A–E](docs/EXPERIMENT_PLAN_FINAL.md).

## Bắt đầu từ đâu?

| Cần làm gì? | Đọc tài liệu |
|---|---|
| Hiểu dữ liệu và thứ tự chuẩn bị | [Chỉ mục dữ liệu](data/README.md) |
| Chọn thực nghiệm và hiểu cách chạy | [Chỉ mục script thực nghiệm](scripts/README.md) |
| Có dữ liệu rồi, cần lệnh chạy nhanh | [Quy trình chạy](docs/RUN_EXPERIMENTS.md) |
| Kiểm tra schema, nhãn và phạm vi kết luận | [Protocol A–E](docs/EXPERIMENT_PROTOCOL.md) |
| Viết scorer mới và hiểu evaluator chung | [Giao diện baseline](scripts/BASELINE_GUIDE.md) |

## Năm thực nghiệm

| Exp | Câu hỏi nghiên cứu | Chuẩn bị đầu vào | Chạy và đọc kết quả |
|---|---|---|---|
| A | Qwen trích năm facet đúng và đủ đến đâu? | [Generator, chia phần, gộp, gold](data/exp_a/README.md) | [So silver với human gold](scripts/exp_a/README.md) |
| B | Xếp hạng theo facet có tốt hơn theo toàn văn? | [Bài mốc, 100 ứng viên, nhãn, split](data/exp_b/README.md) | [Scorer retrieval và so sánh baseline](scripts/exp_b/README.md) |
| C | Lịch sử và tìm kiếm giúp suy ra profile thế nào? | [Users, profile ẩn, hành vi](data/exp_c/README.md) | [Profile, ranking, importance MAE](scripts/exp_c/README.md) |
| D | Nhận biết muốn tương tự/khác biệt có giúp ranking? | [Phiên, cặp quan sát, intent ẩn](data/exp_d/README.md) | [Suy hướng, chấm intent, compliance](scripts/exp_d/README.md) |
| E | Cập nhật profile theo thời gian có theo kịp đổi sở thích? | [Stable/drift, các kỳ, rolling cutoff](data/exp_e/README.md) | [Static/recent/decay và đánh giá](scripts/exp_e/README.md) |

**Conference/C4:** chưa có thực nghiệm riêng trong bảng trên. Cần chốt nguồn dữ liệu, định danh conference, hồ sơ chủ đề và ground truth trước khi bổ sung generator/scorer/evaluator; xem [phạm vi và điều kiện triển khai](docs/PROJECT_OPERATIONS.md).

## Kiến trúc tổng thể và workflow thực nghiệm

Sơ đồ dưới đây nối các khối xử lý hiện có và vị trí kiểm chứng của từng thực nghiệm A–E trong cùng một luồng. **Đường liền** là luồng dữ liệu/xử lý của baseline; **đường nét đứt** là dữ liệu chỉ dùng đánh giá, quan hệ dùng lại thành phần hoặc hướng chưa triển khai, được ghi rõ trên từng cạnh.

```mermaid
flowchart TB
    Source["Nguồn bài báo thật<br/>Title, abstract và metadata"]
    Corpus["Chuẩn hóa và kiểm tra corpus<br/>4.210 bài có paper_id thống nhất"]
    Source --> Corpus

    subgraph A["Exp A · Trích xuất và đánh giá năm facet"]
        Extract["Qwen local<br/>Trích concept và câu dẫn chứng"]
        Validate["Kiểm tra schema và bám nguồn<br/>Retry / checkpoint / gộp các phần"]
        Silver["Biểu diễn bài báo dùng chung<br/>problem · task · method · dataset · contribution<br/>Silver + evidence + metadata + manifest"]
        RefA["Reference để đánh giá extraction<br/>Hiện là AI reference; chờ human review"]
        EvalA["Ghép nhãn exact / embedding<br/>Precision · Recall · F1 theo facet, micro/macro"]
        Extract --> Validate --> Silver
        Silver --> EvalA
        RefA -. "nhãn tham chiếu" .-> EvalA
    end
    Corpus --> Extract

    Ready["Kiểm tra silver complete và provenance<br/>Lọc bài fallback / còn lỗi khỏi pool khuyến nghị"]
    Silver --> Ready

    subgraph B["Exp B · Khuyến nghị theo bài đang đọc"]
        DataB["Bài mốc + 100 ứng viên cố định<br/>Chia train / dev / test theo bài mốc"]
        RankB["Chấm độ tương tự và xếp hạng<br/>Random / whole-text TF-IDF<br/>Equal-facet / weighted-facet"]
        DataB --> RankB
    end

    subgraph C["Exp C · Suy sở thích dài hạn"]
        DataC["Sinh users và log mô phỏng<br/>Phản ứng đọc + search + exposure"]
        ProfileC["Chỉ lấy log trước cutoff<br/>Suy concept preferences + facet importance"]
        RankC["Xếp hạng ứng viên holdout<br/>Popularity / text-history<br/>Facet không search / có search"]
        DataC --> ProfileC --> RankC
    end
    Ready --> DataB
    Ready --> DataC

    subgraph D["Exp D · Suy ý định theo facet trong phiên"]
        DataD["Sinh phiên: bài mốc + context + ứng viên<br/>Phản ứng và query trước cutoff"]
        IntentD["Tính importance từ log C<br/>Suy hướng similar / different / unknown<br/>Từ hành vi hoặc hành vi + search"]
        RankD["Xếp hạng theo context và hướng dự đoán<br/>Fixed-similar / profile-similar<br/>Direction-behavior / direction-search"]
        DataD --> IntentD --> RankD
    end

    subgraph E["Exp E · Thích ứng khi sở thích thay đổi"]
        DataE["Sinh stream riêng cho users C<br/>Hai nhóm stable / drift, bốn kỳ"]
        UpdateE["Tại mỗi rolling cutoff, chỉ dùng quá khứ<br/>Tính lại profile: static / recent / decay"]
        RankE["Xếp hạng ứng viên kỳ kế tiếp<br/>So với popularity và giữa các cách cập nhật"]
        DataE --> UpdateE --> RankE
    end
    Ready --> DataD
    Ready --> DataE
    DataC -->|"handoff users + history / search / exposure"| DataD
    DataC -->|"handoff users; E sinh stream riêng"| DataE
    ProfileC -. "Dùng lại profile builder, không chờ kết quả C" .-> UpdateE

    Truth["Ground truth mô phỏng B–E, giữ riêng<br/>Relevance / latent profiles / session intents<br/>Phản ứng tương lai và profile theo kỳ"]
    Eval["Evaluator chung, tách khỏi scorer<br/>B–E: nDCG / Recall / Precision / MRR<br/>C–E: importance MAE<br/>D: direction F1 / accuracy / coverage + compliance<br/>E: tổng hợp theo stable / drift và từng kỳ"]
    RankB --> Eval
    RankC --> Eval
    RankD --> Eval
    RankE --> Eval
    Truth -. "Chỉ evaluator đọc; D thêm oracle-intent riêng" .-> Eval
    Report["Kết quả từng phương pháp và báo cáo so sánh<br/>Predictions · điểm từng case · bảng tổng hợp<br/>Manifest để truy nguồn và tái lập"]
    Eval --> Report

    Conference["Hướng khuyến nghị hội nghị · CHƯA TRIỂN KHAI<br/>Cần catalog, hồ sơ chủ đề và nhãn phù hợp<br/>Đối chiếu facet bài / profile với conference"]
    Silver -. "Hướng mở rộng, chưa có thực nghiệm riêng" .-> Conference

    classDef input fill:#e8f1f8,stroke:#426b85,color:#17364a;
    classDef representation fill:#fff3d9,stroke:#c58e35,color:#604414;
    classDef profile fill:#eaf5ed,stroke:#45915a,color:#214d2d;
    classDef intent fill:#f1eafa,stroke:#8b5cba,color:#50326e;
    classDef evaluation fill:#fff0f0,stroke:#c96b72,color:#72363b;
    classDef future fill:#f5f5f5,stroke:#999,color:#555,stroke-dasharray:5 5;
    class Source,Corpus,DataB,DataC,DataD,DataE input;
    class Extract,Validate,Silver,Ready representation;
    class ProfileC,UpdateE,RankC,RankE profile;
    class IntentD,RankD,RankB intent;
    class RefA,EvalA,Truth,Eval,Report evaluation;
    class Conference future;
```

B–E là các phép thử thành phần trên cùng nền corpus/facet, mỗi nhánh có đầu ra xếp hạng và đánh giá riêng. Baseline hiện dùng TF-IDF hoặc concept counts; encoder embedding ở A phục vụ **ghép nhãn đánh giá**, chưa phải encoder của ranker B–E. Retrieval toàn corpus, reranker và việc ghép B–E thành một vòng tương tác online là hướng phát triển.

Các generator B–E sinh cả dữ liệu quan sát lẫn ground truth, nhưng scorer chỉ nhận phần quan sát. Nhãn ẩn đi thẳng tới evaluator; mũi tên này không đưa đáp án vào bước suy profile, suy intent hay xếp hạng. Sơ đồ mô tả luồng xử lý và hợp đồng, không xác nhận mọi dataset đã được sinh đủ.

B/C cần silver A đầy đủ, metadata và manifest hợp lệ. D/E cần thêm bộ dữ liệu C hoàn chỉnh; **không cần chạy scorer C, huấn luyện model C hoặc đợi điểm C**. Human gold A phục vụ đánh giá extraction, không chặn generator B–E.

Runner B–E chạy CPU bằng Python 3.11+ và thư viện chuẩn. Phần Qwen/GPU, checkpoint, chia bài cho thành viên nằm trong README dữ liệu A. Điều kiện và lệnh cụ thể nằm ở từng exp; có corpus thật chưa đồng nghĩa đã có dataset khuyến nghị.

## Tài liệu chính khác

- [Corpus canonical](data/processed/README.md) và [nguồn dữ liệu gốc](data/raw/README.md).
- [Hợp đồng dữ liệu](DATA_CONTRACT.md) và [quản lý corpus, bàn giao, Git, giới hạn đề tài](docs/PROJECT_OPERATIONS.md).
- [Định nghĩa facet](docs/FACET_GUIDELINE.md), [prompt extraction](docs/ANNOTATION_PROMPT.md), [review và đánh giá Qwen](docs/EVALUATE_QWEN.md).
- [Trạng thái kiểm chứng có ngày ghi nhận](docs/VALIDATION_STATUS.md).
- [Kế hoạch phát triển A–E](docs/EXPERIMENT_PLAN_FINAL.md) và [ghi chú nghiên cứu liên quan](docs/FACET_RECOMMENDATION_RESEARCH.md).
- [Mẫu README theo từng tầng](docs/EXPERIMENT_README_TEMPLATE.md).

Các điểm B–E đo hành vi trên quy tắc mô phỏng và nhãn sinh từ silver. Khi báo cáo, cần nêu rõ giới hạn này; không diễn giải chúng thành chất lượng khuyến nghị đã được người dùng thật kiểm chứng.
