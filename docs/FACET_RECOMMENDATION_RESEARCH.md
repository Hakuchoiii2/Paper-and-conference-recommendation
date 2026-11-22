# Nghiên cứu liên quan và đề xuất cho khuyến nghị paper theo năm facet

Ngày đối chiếu: 2026-10-09. Đây là ghi chú nghiên cứu và đề xuất thiết kế; chưa thay đổi protocol 2.0, configs, dữ liệu hoặc scorer hiện tại.

**Cập nhật sau trao đổi:** xem [bản chốt A–E](EXPERIMENT_PLAN_FINAL.md) để biết phạm vi đề xuất hiện tại, đầu vào, generator, phép so và trạng thái dữ liệu. Nhóm giữ corpus/năm facet, không chọn CSFCube cho phương án đánh giá này; các mục CSFCube bên dưới là ghi chú literature. Chấm relevance B/D bằng người/LLM và reranker là mở rộng có thể để sau, không phải yêu cầu để chạy mock. Bản chốt được ưu tiên khi khác với lộ trình nghiên cứu ban đầu ở đây.

## Kết luận thiết kế

Hướng phù hợp với corpus khoảng 4.210 bài và A–E hiện tại là: trích facet có evidence → embedding ngữ nghĩa cho toàn bài và từng facet → profile concept từ lịch sử/search → ranking theo profile và hướng phiên → cập nhật theo thời gian.

Một mô hình cross-encoder reranker riêng là lựa chọn cần đánh giá, không phải điều kiện để mọi phép xếp hạng trở thành một phương pháp hợp lệ. Hàm xếp hạng có thể dùng biểu diễn đã học và công thức ghép điểm. Phần cần kiểm chứng là biểu diễn, tín hiệu đầu vào, nhãn relevance và phép so sánh với đối chứng.

Các đề xuất áp dụng bên dưới là suy luận cho dự án này, không phải kiến trúc được sao chép nguyên vẹn từ một bài báo.

## Các nghiên cứu sát nhất

| Công trình | Họ làm gì | Ý nghĩa cho dự án |
|---|---|---|
| [CSFCube, NeurIPS Datasets and Benchmarks 2021](https://arxiv.org/abs/2103.12906) | Đánh giá query-by-example theo facet bằng relevance được chuyên gia gán nhãn. | Thêm benchmark độc lập cho B; giữ nguyên nghĩa facet và giao thức gốc. |
| [ASPIRE, NAACL 2022](https://aclanthology.org/2022.naacl-main.331/) | Mã hóa câu trong ngữ cảnh title/abstract; học từ co-citation contexts. So khớp một cặp vector tốt nhất hoặc nhiều cặp bằng optimal transport. | Mỗi facet có biểu diễn riêng; giữ ngữ cảnh của concept. Có thể dùng model công bố để làm đối chứng thay vì tái huấn luyện từ đầu. |
| [Specialized Document Embeddings, JCDL 2022](https://arxiv.org/abs/2203.14541) | Học embedding chuyên biệt cho task, method, dataset từ Papers with Code; dùng cosine/nearest neighbors để khuyến nghị. | Gần trực tiếp ba facet của dự án; embedding toàn bài và embedding theo facet cần được so riêng. |
| [LACE, SIGIR 2023](https://arxiv.org/abs/2304.04250) | Profile gồm concept dễ đọc và giá trị vector cá nhân hóa; ghép nội dung lịch sử với concept bằng optimal transport, rồi dùng profile để ranking. Có offline evaluation và user study. | C nên giữ tên concept, dấu thích/không thích và evidence để giải thích sở thích; bản đơn giản dùng tổng hợp có trọng số chỉ là phương pháp lấy cảm hứng từ LACE. |
| [mCTRL, Information Processing & Management 2025](https://doi.org/10.1016/j.ipm.2024.103879) | Dùng token điều khiển để học biểu diễn toàn bài và nhiều aspect cùng lúc; hierarchical loss gắn aspect với chủ đề chung. | Định hướng nâng cấp khi có nhãn huấn luyện đủ tốt; trước mắt kiểm tra độ chuyên biệt và độ trùng giữa năm facet. |
| [FaBle, ACL 2025](https://aclanthology.org/2025.acl-long.1388/) | Tách, sinh và ghép lại facet bằng LLM để tạo positive/negative cho huấn luyện contrastive; thêm hard negatives. | Học cách thiết kế cặp khó: giống problem nhưng khác method, giống method nhưng khác dataset. Dữ liệu sinh thêm chỉ thuộc training và phải khai báo synthetic. |
| [SciFACE, arXiv 2026](https://arxiv.org/abs/2604.16329) | Huấn luyện cross-encoder riêng cho Background và Method trên cặp paper thật được LLM gán nhãn và đối chiếu với human judgments. | Ví dụ cụ thể cho reranker theo facet; không dùng kết quả hai facet để chứng minh trực tiếp hiệu quả năm facet của dự án. |
| [UniFAR, arXiv 2026, bản sửa 2026-08-31](https://arxiv.org/abs/2602.23766) | Kết hợp paper–paper và question–paper, dùng learnable facet anchors và aggregation nhiều mức. | Tách kiểm tra query là paper và query là câu hỏi tự nhiên; một encoder tốt cho paper–paper chưa tự bảo đảm chất lượng search. |
| [T-CTR, BIRNDL 2018](https://ceur-ws.org/Vol-2132/paper2.pdf) | Dùng content và interactions để ước lượng drift theo user, giảm ảnh hưởng tương tác cũ; đánh giá theo thứ tự thời gian. | E cần temporal splits và rolling evaluation; adaptive decay là hướng mở rộng sau fixed decay. |
| [PaperFlow, arXiv 2026](https://arxiv.org/abs/2606.07454) | Tổ chức profiling → daily ranking → feedback/adaptation; benchmark có simulated users, hidden labels và ranh giới thời gian. | Gần C/E về quy trình cập nhật; kết quả mô phỏng và pilot người thật phải được báo cáo riêng. |

SciFACE, UniFAR và PaperFlow được dùng ở đây như preprint arXiv; ghi chú này chưa xác nhận tình trạng phản biện của các bản tương ứng. Không so trực tiếp con số giữa các bài khi pool, labels, split hoặc metric khác nhau.

## Biểu diễn bài và facet

Giữ năm facet `problem`, `task`, `method`, `dataset`, `contribution` theo guideline hiện tại. Đây là lựa chọn thiết kế của dự án; các công trình kể trên dùng những hệ facet khác nhau.

Lưu đồng thời: concept, câu evidence gốc, trạng thái thiếu thông tin và nguồn annotation. Annotation metadata A đã có evidence nên có thể dùng lại để tạo đầu vào encoder. Một tên như “transformer” đứng riêng có thể không đủ phân biệt phương pháp thực sự dùng trong bài.

Đề xuất baseline semantic đầu tiên: dùng một encoder pretrained cố định, cache vector toàn bài và vector từng facet. So hai cách tạo facet text trên dev: concept đơn thuần và concept kèm evidence; chốt cách làm trước test. Toàn bộ các biến thể B dùng cùng encoder để đo tác động của việc chia/gán trọng số facet.

[Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) là ứng viên chung cho text/facet/query. [SPECTER2](https://huggingface.co/allenai/specter2_base) là đối chứng scientific paper–paper: dùng adapter proximity `allenai/specter2` theo tài liệu chính thức. Không mặc định dùng raw base checkpoint hoặc coi model toàn bài là đã được huấn luyện cho từng facet.

Với corpus hiện tại, nên thử tìm kiếm cosine chính xác trên vector đã cache trước khi thêm ANN/vector database. Thời gian chạy và bộ nhớ phải đo trên máy thực tế; chưa có benchmark trong ghi chú này.

## Retrieval và ranking theo hướng phiên

Giữ hai giao thức đánh giá có tên và output riêng:

1. **Fixed judged pools:** các phương pháp chấm cùng candidates, dùng cùng labels để cô lập chất lượng scorer. Đây cũng là cách benchmark CSFCube đánh giá ranking trong [hướng dẫn gốc](https://github.com/iesl/CSFCube).
2. **Full-corpus retrieval:** tìm candidates từ toàn corpus rồi ranking; đo thêm Recall@K của bước retrieval khi có tập bài liên quan đã được judge. Ranking tốt trong pool chưa chứng minh retrieval tìm được đủ bài.

Đề xuất pipeline hệ thống: dùng bài đang đọc và query trước cutoff để chọn pool liên quan; chấm lại pool bằng độ phù hợp profile và yêu cầu facet của phiên. Với nhu cầu “cùng problem, khác method”, có thể chọn pool bằng context/problem trước, rồi chấm method và các tín hiệu còn lại. Cần so với retrieval toàn bài để kiểm tra pool nào bỏ sót ít bài liên quan hơn.

Hàm cộng điểm theo trọng số là phương pháp chính có thể đánh giá. Learned reranker là một biến thể mạnh hơn để so sánh, không tự thay thế các câu hỏi về profile, intent hoặc temporal.

Nếu dùng [Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B), cung cấp điều kiện facet/hướng phiên bằng instruction và chỉ dùng thông tin quan sát được. Kiểm tra cùng problem/khác method bằng cases độc lập; khả năng instruction-following không bảo đảm model hiểu đúng mọi constraint. Dùng reranker relevance mặc định có thể ưu tiên các bài quá giống nhau đối với nhu cầu tìm phương pháp khác.

Một similarity thấp chưa phải bằng chứng hai method khác nhau theo nghĩa hữu ích. Cần relevance gate theo ngữ cảnh và nhãn relation được review. Thiếu facet không được xem là khác facet. Dataset identity cần alias/ID được kiểm chứng; tên dataset gần nhau về embedding không đủ kết luận cùng dataset. Contribution là nội dung bài khẳng định, không phải điểm chất lượng hoặc độ mới đã được thẩm định.

## Áp dụng vào A–E

| Exp | Phương pháp và đối chứng nên có | Điều cần kiểm tra |
|---|---|---|
| A | Giữ Qwen silver so với human gold độc lập. | P/R/F1 và review ngữ nghĩa; giữ cohort/prompt separation. Chưa cần thêm LLM thứ hai chỉ để tăng số model. |
| B | Giữ TF-IDF; thêm whole-text semantic, equal-facet semantic, fixed-weight facet semantic trên cùng encoder. Thêm một đối chứng scientific có sẵn như SPECTER2 hoặc ASPIRE nếu tích hợp được. | Ranking theo từng facet, macro giữa facets, missing-facet strata. Đánh giá native CSFCube và bộ năm facet riêng. |
| C | Giữ popularity, text-history, facet-no-search, facet-history; bổ sung profile semantic nhưng vẫn giữ concept/evidence dễ đọc. | Ablation search có cùng nguồn tín hiệu giữa đối chứng; scorer chỉ dùng prefixes trước cutoff. Trọng số importance ẩn trong mock chỉ phục vụ kiểm tra simulator. |
| D | Giữ fixed-similar/profile-similar/behavior/search và oracle riêng; áp dụng cùng semantic backend. Với query tự nhiên, so parser hiện có với một phương pháp suy intent ngữ nghĩa. Reranker theo instruction là phép so thêm. | Gold focus/direction từ review riêng; query clear/ambiguous/none; F1, abstention coverage, ranking, compliance. Oracle không được coi là phương pháp triển khai thực tế. |
| E | Giữ static/recent/fixed-decay trên cùng semantic scorer; chỉ thay cách dùng lịch sử. Adaptive decay là bước sau nếu còn thời gian. | Rolling cutoffs, stable/drift, ranking sau drift. Có thể thêm thời gian thích ứng nếu định nghĩa và labels cho phép. |

Các thay đổi biểu diễn phải có config/version và hash riêng. Giữ bộ CPU hiện tại làm đối chứng; không diễn giải lại kết quả lexical cũ thành semantic results.

## Nhãn và đánh giá độc lập

Ba loại gold cần phân biệt:

- **Gold extraction A:** facet được trích đúng từ một bài hay chưa.
- **Gold relevance B/D:** hai bài có liên quan trên facet hoặc thỏa yêu cầu phiên hay chưa.
- **Feedback C/E:** người dùng thật chọn/đọc/thích gì theo thời gian, hoặc latent truth đã công bố của simulator.

400 bài review A không tự tạo relevance judgments cho B hoặc behavioral ground truth cho C/E. Nhãn hiện tại sinh từ overlap concept cùng hệ facet nên có thể thuận lợi cho scorer có giả định tương tự. Kết quả đó phù hợp kiểm tra mô phỏng; muốn đánh giá ngữ nghĩa cần nhãn độc lập từ paper text và ý định phiên.

Đề xuất pilot human relevance: khoảng 20–30 anchors, mỗi anchor 20–30 candidates lấy từ union của lexical, whole-text semantic và facet methods; thêm các trường hợp khó. Đây là mục tiêu công việc đề xuất, không phải số mẫu đã đủ để khẳng định mọi hiệu quả. Review mù tên model/score, gán graded relevance theo guideline năm facet, có một subset được hai người chấm và xử lý bất đồng. Nếu dùng để tune, phải tách một phần test chưa được dùng chọn tham số.

Native CSFCube dùng background/method/result, không phải bộ năm facet của dự án. Chạy benchmark gốc với IDs, judged pools, splits và metrics gốc; nếu lọc/mapping corpus làm mất records, công bố coverage hoặc dùng nguyên catalog gốc. Không chuyển result thành contribution hay background thành problem/task một cách mặc định. ASPIRE/FaBle báo nDCG%20 là cutoff theo phần trăm pool; không đồng nhất với nDCG@20.

Với C/E, giữ mock benchmark có ranh giới thời gian để kiểm tra cơ chế; nếu triển khai được thì thêm một pilot nhỏ với người thật và công bố đúng là pilot. Hành vi người giả lập không thể được trình bày như log triển khai thực tế.

## Thứ tự thực hiện đề xuất

1. Chốt nghĩa năm facet và guideline relevance; chuẩn bị gold extraction A và relevance pilot theo hai mục đích riêng.
2. Tích hợp một encoder pretrained cố định và cache; chạy các ablation semantic B trên fixed pools. Đánh giá thêm native CSFCube.
3. Đưa cùng biểu diễn semantic vào C/D/E, giữ cutoffs, truth separation và các đối chứng hiện tại.
4. Tích hợp full-corpus retrieval để đo cả candidate recall và ranking.
5. Thêm một reranker theo facet/instruction và so có/không rerank; fine-tune chỉ khi đã có train/dev/test labels đủ đáng tin.

Đóng góp nên được trình bày quanh khả năng tự suy sở thích/hướng phiên và thích ứng thời gian trên hệ năm facet có evidence, rồi kiểm chứng từng thành phần bằng ablation. Chia facet, dùng embedding hay profile concept đã xuất hiện trong nghiên cứu trước; tổ hợp đề xuất này chưa được chứng minh là mới chỉ bằng ghi chú literature này.

## Giới hạn của ghi chú

Đã đối chiếu phương pháp và phần đánh giá trong các nguồn chính thức/primary liên kết ở trên. mCTRL được đối chiếu từ abstract và phần mô tả phương pháp công khai của nhà xuất bản, chưa đọc đủ toàn văn. Chưa chạy checkpoint, đo thời gian/VRAM, tái lập số liệu hoặc thực hiện systematic literature review. Không sửa code, contract hay dữ liệu thật; tên model nêu ở đây là ứng viên cần benchmark, không phải lựa chọn đã được chứng minh tốt nhất cho corpus này.
