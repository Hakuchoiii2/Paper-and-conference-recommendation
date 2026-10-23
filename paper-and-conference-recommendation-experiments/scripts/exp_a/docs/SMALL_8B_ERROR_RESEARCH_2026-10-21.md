# Lỗi hiện tại và hướng giải quyết từ nghiên cứu mô hình 7–8B

Ngày kiểm nguồn: **21/10/2026**. Phạm vi: trích xuất có cấu trúc từ văn bản khoa học, guideline/đơn vị nhãn, grounding và sửa lỗi trên model khoảng 7–8B. Đây là nghiên cứu có chọn lọc theo vấn đề dự án, không phải systematic review toàn bộ lĩnh vực.

**Kết luận:** có bằng chứng model 7–8B làm tốt hơn khi task, guideline, examples và dữ liệu huấn luyện được thiết kế đúng. Chưa có nguồn đã kiểm nào chứng minh giải quyết trọn bộ `problem/task/method/dataset/contribution` của dự án, hoặc bảo đảm một sửa prompt sẽ cho mức tăng như fine-tuning trong bài báo. Hướng hợp lý vẫn là **cải thiện và đo pipeline trên base v1 trước; khóa protocol rồi mới fine-tune phiên bản kế tiếp**.

Không chạy inference, embedding hoặc training mới trong lượt nghiên cứu này. Đã đọc lại artifact lỗi hiện có và kiểm nguồn sơ cấp. Không sửa prompt, schema, matcher, reference hoặc adapter.

## 1. Các lỗi hiện tại: điều đã đo và điều chưa biết

| Nhóm vấn đề | Bằng chứng local | Diễn giải có thể bảo vệ |
|---|---|---|
| Method/contribution chưa đủ hoặc sai đơn vị | Adapter v1: method 93 FP + 107 FN; contribution 119 FP + 121 FN, tổng 440/687 = **64,05%** FP+FN | Hai facet nên được ưu tiên. Một label khác cách tách có thể tạo cả FP và FN; không coi 440 là 440 lỗi sự thật độc lập |
| Nhãn sai từ/thứ tự/evidence | Base v2: **765 raw → 351 final**, 414 item không qua source-word/order; cùng gate áp raw base v1 còn 662 label sau xử lý | Có vấn đề thật về tuân thủ nguồn, nhưng nguồn chưa đủ chứng minh role hoặc entailment |
| Review không sửa được draft lỗi | Adapter v1 **0/9**, v2 **0/15** draft lỗi trở thành final hợp lệ; cả 15 draft lỗi v2 lặp nguyên văn | Lượt review hiện chưa chứng minh khả năng repair; draft đúng được giữ nguyên không phải lỗi |
| Mất điều kiện hoặc viết quá dài | Nhãn cuối v1 trung bình **5,27 từ**, v2 **13,85 từ**; các ca patent NMT và NWChem có thay đổi nghĩa/coverage | Không tối ưu độ dài chung cho mọi facet: tên technique khác một finding đầy đủ |
| Sai role | Source review có background sequence-to-sequence model bị đưa vào method; artifact cũ và phát triển mới dễ lẫn | Cần phân biệt vai trò trong bài hiện tại; chưa có taxonomy thủ công toàn bộ FP/FN để báo tỷ lệ lỗi role |
| Khác quy ước reference | CLIR/DeepCopy/FRENK có khác tách/gộp, tên ngắn/dài và giữ chủ thể | F1 hiện là agreement với AI reference policy cũ, không phải human accuracy |

Nguồn local: [phân tích lỗi v1](../../../data/exp_a/finetuning/build/error_analysis_v1.json), [đối chiếu v1/v2](BASE_V1_V2_COMPARISON_2026-10-20.md), [replay cùng grounding](../../../data/exp_a/finetuning/v2/build/base_comparison_common_gate_20261020/comparison.json). Chưa xác định được tỷ lệ riêng của “thiếu ý”, “sai role”, “khác granularity” trên toàn bộ 100 bài; không gán nguyên nhân đó chỉ từ tổng F1.

## 2. Bằng chứng nghiên cứu sát quy mô 7–8B

Các số ở mỗi hàng chỉ so được **bên trong cùng thí nghiệm của bài đó**. Không xếp hạng model giữa các hàng, và không so trực tiếp với semantic F1 59,28 của v1.

| Công trình và model thật | Họ đã làm gì, kết quả đã kiểm | Liên hệ và giới hạn |
|---|---|---|
| **SciRIFF — Llama3.1-8B-Instruct** | SFT theo instruction khoa học; Table 2: SciERC **30,6 → 56,8**. | Bằng chứng gần miền scientific IE nhất; SciERC là typed entity lists, không phải đầy đủ claim contribution. [EMNLP 2025, Table 2](https://aclanthology.org/2025.emnlp-main.310.pdf) |
| **GoLLIE — CodeLlama7B + QLoRA** | Học từ guideline và annotation candidates. Table 3: **42,3 → 55,3** zero-shot IE average; baseline đã SFT, không phải raw base. Table 4 bỏ candidates còn **49,9**. | Ủng hộ quy tắc nhãn và ví dụ ranh giới; không chứng minh thêm guideline lúc inference là đủ. [ICLR 2024, §3–6](https://arxiv.org/html/2310.03668v5) |
| **GuideX — Llama3.1-base-8B, teacher 70B** | Synthetic data theo guideline rồi QLoRA. Table 2: synthetic-only **30,08 → 37,14**; gold-only **62,77**, synthetic rồi gold **64,15**. | Hướng dữ liệu cho lần train sau; teacher không phải 8B, synthetic không thay kiểm nguồn và có miền bị giảm. [arXiv v1, Table 2](https://arxiv.org/html/2506.00649v1) |
| **UniversalNER — UniNER7B** | Distillation có negative entity types vắng trong passage, đích `[]`. Table 4: none **31,5**, uniform **47,7**, frequency **53,4** trên 7 OOD NER sets. | Dạy biết trả rỗng; negative “type không có” khác “span có nhưng sai role”. Đây là training, không phải chỉ nhắc model đừng bịa. [ICLR 2024, §3.2/5.4](https://proceedings.iclr.cc/paper_files/paper/2024/file/34678d08b36076de986df95c5bbba92f-Paper-Conference.pdf) |
| **Grammar-Constrained Decoding — LLaMA7B** | Không downstream fine-tuning; 4-shot closed IE, Table 1: F1 **11,9 → 23,5** nhờ grammar. | Có bằng chứng inference-only ở model nhỏ. Task dùng entity/relation trong KB, không phải tự do viết finding. [EMNLP 2023, §3.4/Table 1](https://aclanthology.org/2023.emnlp-main.674.pdf) |
| **JSONSchemaBench — Llama3.1-8B-Instruct ở phần quality** | Nghiên cứu constrained decoding, schema coverage và task quality; quality tasks là reasoning, không phải extraction năm facet. | Hữu ích cho syntax và valid IDs; JSON Schema không tự kiểm đúng role/nguồn. [Bản v3, §5–6](https://arxiv.org/html/2501.10868v3) |
| **Dark Side of Intrinsic Self-Correction — Llama3.1-8B** | BoolQ Yes/No: review 49,2% accuracy; nhắc lại câu hỏi 52,4%; SFT 70,3% trong Table 4. | Cảnh báo review và cho hướng luyện hành vi giữ/sửa; không phải F1 extraction. [§3/6, Table 4](https://arxiv.org/html/2412.14959v2) |
| **LEADS — Mistral7B-Instruct-v0.3** | Instruction tuning cho search/screening và bốn tác vụ extraction khoa học y sinh; dùng cùng prompts để so các model. | Bổ trợ hướng chuyên biệt hóa và kiểm text/numbers riêng. Dataset hàng trăm nghìn instructions, không chứng minh 467 train của mình đủ. [Nature Communications, Methods](https://www.nature.com/articles/s41467-025-62058-5) |

Ghi chú bốn paper SFT có kiểm chi tiết và mốc bảng tại [evidence note](research_evidence_8b_2026-10-21.md). Với SciRIFF, dùng bản hội nghị EMNLP2025 chứa 8B; không trộn các số Llama2-7B của bản arXiv cũ.

## 3. Ghép nghiên cứu với từng vấn đề của dự án

### 3.1. Sai role và granularity: cần guideline kèm ví dụ phân biệt

GoLLIE cho thấy model được huấn luyện có thể dùng guideline và candidates đại diện; phần error analysis còn chỉ ra reference không theo guideline và xung đột độ hạt. Vì vậy việc thêm nhiều lời hướng dẫn mà chưa thống nhất đơn vị annotation có thể chỉ làm output đổi phong cách. [GoLLIE, §5.3–6](https://arxiv.org/html/2310.03668v5).

**Suy luận áp dụng, cần thử:** giữ prompt v1 làm mốc, thêm một nhóm ít ví dụ synthetic/train cho các ranh giới: method thực sự dùng / prior work; artifact mới / công cụ cũ; limitation / ví dụ minh họa; một compound name / nhiều technique độc lập. Mỗi ví dụ giải thích vì sao loại hoặc giữ, không chỉ đưa một output đẹp. Không lấy test đã phân tích làm few-shot.

Không kết luận “tách thành 5 calls” sẽ tốt hơn: tách call không tự sửa policy, có thể tăng chi phí và mất liên hệ vai trò. Nếu thử decomposition, giữ budget tổng tương đương và báo cả label recall lẫn FP.

### 3.2. Sai grounding: phân biệt ràng buộc cấu trúc với ràng buộc nội dung

GCD cho phép output space phụ thuộc input; đây là cơ sở cho ý tưởng ràng buộc những lựa chọn như IDs/candidate vocabulary. JSONSchemaBench cũng chỉ rõ vấn đề engine quá chặt/quá lỏng. Hai công trình không chứng minh một grammar chỉ kiểm JSON sẽ xác nhận nghĩa của finding. [GCD, §2/4](https://aclanthology.org/2023.emnlp-main.674.pdf), [JSONSchemaBench, §5–6](https://arxiv.org/html/2501.10868v3).

**Suy luận áp dụng:** thử mức đơn giản trước: cùng schema `concept/evidence_id`, giới hạn `evidence_id` trong những ID thực sự có ở bài; giữ kiểm source-word/order phía sau. ID hợp lệ vẫn có thể trỏ sai câu, nên cần tách “ID tồn tại” và “câu đó hỗ trợ concept”.

Một hướng xa hơn là chọn candidate/span được chương trình giữ nguyên văn, rồi gán facet. Đây là thay đổi representation cần arm riêng; exact contiguous span có thể làm mất label hợp lệ vốn lấy các từ không liền nhau hoặc cần nhiều câu. Không dùng fuzzy matching để âm thầm gán evidence cho một concept mơ hồ.

**Điểm quan trọng:** v1 selected schema-valid 100/100, base v2 cũng 100/100. Chỉ sửa JSON không đánh trúng phần lớn lỗi hiện tại. Các nghiên cứu này chưa kiểm chứng stack Qwen3-8B NF4/attention của dự án; cần đánh giá compatibility và latency trước khi chọn engine.

### 3.3. Review lặp nguyên draft: không suy ra chỉ cần review nhiều lần hơn

Trong nghiên cứu intrinsic self-correction, Llama3.1-8B bị giảm 20,4 điểm accuracy ở thiết lập BoolQ; Table 4 cho thấy nhắc lại câu hỏi chỉ phục hồi 3,2 điểm, vẫn chưa về mốc ban đầu. SFT hành vi cho kết quả tốt hơn ở thí nghiệm đó. Không suy ra vài mẫu BoolQ đủ sửa extractor của mình. [Dark Side, Table 1/4 và §6](https://arxiv.org/html/2412.14959v2).

**Khác biệt cần giữ:** pipeline hiện tại đã có nguồn và validation feedback; không phải intrinsic review thuần túy. Vì vậy paper không chứng minh nguyên nhân 0/9 của mình. Nó chỉ làm yếu giả định “bảo cùng model nghĩ lại là sẽ sửa”.

**Suy luận áp dụng:** cung cấp facet/index lỗi, concept, câu evidence, loại lỗi và nhiệm vụ sửa cụ thể; giữ những item đã xác nhận đúng, validate sau sửa. Nếu không sửa được, fallback minh bạch thay vì coi lần review đã hoàn tất là quality guarantee. Đo cả invalid→valid và valid→invalid/coverage lost.

Nếu review có output khác nhưng vẫn không sửa đúng, chưa đủ lý do tăng budget. Giai đoạn fine-tuning sau có thể thử cặp draft lỗi + feedback nguồn → output sửa, cùng cặp draft đúng → giữ nguyên; đây là đề xuất cần kiểm riêng, không phải kết quả đã được xác nhận cho facet extraction.

### 3.4. Thiếu ý, sai role lặp lại: dữ liệu có giám sát quan trọng hơn việc kéo dài prompt

SciRIFF cung cấp bằng chứng trực tiếp cho instruction tuning trên văn bản khoa học; GuideX cho thấy có thể tạo dữ liệu guideline-conditioned để huấn luyện 8B nhưng các benchmark không tăng đồng đều. LEADS củng cố hướng chuyên biệt hóa, đồng thời cho thấy quy mô dữ liệu và input context có thể khác rất lớn bài toán hiện tại. [SciRIFF](https://aclanthology.org/2025.emnlp-main.310.pdf), [GuideX](https://arxiv.org/html/2506.00649v1), [LEADS](https://www.nature.com/articles/s41467-025-62058-5).

**Suy luận áp dụng:** sau khi pipeline base ổn, chuẩn hóa train theo đúng policy đã khóa: method compact độc lập, finding đủ qualifier, role boundaries, facet rỗng khi thiếu căn cứ, và repair examples nếu muốn model học sửa. Teacher là bên tạo đề xuất; không coi schema-pass hoặc đồng thuận AI là human gold.

UniversalNER hỗ trợ ví dụ `[]` cho loại thông tin vắng mặt. Mở rộng thành “có tên method trong nguồn nhưng chỉ là prior work” là **role hard negative mới cần thử**. Không gán mức tăng 31,5→53,4 của paper cho đề xuất mở rộng này. [UniversalNER, §3.2/5.4](https://proceedings.iclr.cc/paper_files/paper/2024/file/34678d08b36076de986df95c5bbba92f-Paper-Conference.pdf).

## 4. Những hướng không nên ưu tiên từ bằng chứng hiện có

- **Chỉ tăng epoch/rank:** lỗi role/đơn vị nhãn và không repair chưa được chứng minh do thiếu capacity. Đây sẽ thêm biến trước khi biết bottleneck.
- **Chỉ thêm chain-of-thought hoặc review tổng quát:** chưa có bằng chứng trực tiếp trên năm facet; có nguy cơ đổi đáp án đúng hoặc chỉ tăng token.
- **Chỉ ép JSON:** schema hiện đã gần như đúng; vấn đề chính còn ở nghĩa và source support.
- **Bỏ grounding để tăng điểm:** raw base v2 chỉ đạt 32,19 so raw base v1 47,07; nới gate chưa giải quyết được chất lượng đầu ra, còn hợp thức hóa item lỗi.
- **RAG web/full-text cho mọi paper:** input hợp đồng hiện là title/abstract. Đưa thông tin ngoài vào sẽ đổi bài toán và có thể tạo nhãn không được nguồn đánh giá cho phép. Trước hết cần đọc đầy đủ nguồn đã có.
- **Thêm mọi field reasoning/kind/span vào schema:** [nghiên cứu local cũ](SMALL_LM_EXTRACTION_RESEARCH_2026-10-16.md) đã ghi các thử source-first có regression; không lặp lại nguyên thiết kế đó rồi coi là hướng mới chưa thử.
- **Điều chỉnh matcher/reference theo output:** sẽ làm lẫn cải tiến model với cải tiến cách chấm. Reference ambiguity cần audit độc lập và benchmark version riêng.

## 5. Thử gì trước trên base v1?

Đây là đề xuất thí nghiệm, chưa triển khai. Giữ cùng Qwen3-8B revision, greedy, max 2048 output tokens/call, tối đa 3 calls/bài, nguồn và reference đóng băng.

| Arm | Chỉ thay đổi | Kỳ vọng cần kiểm |
|---|---|---|
| R0 | Base + pipeline v1 nguyên trạng | Mốc dev; không lấy test 47,44 làm target tune |
| R1 | Guideline/ví dụ ranh giới và granularity, giữ schema | Method/contribution đúng role hơn, ít gộp/tách lệch, coverage không giảm |
| R2 | Feedback theo item + repair mục tiêu, prompt draft giữ v1 | Có invalid→valid thực sự; không làm mất hoặc làm sai item đúng |
| R3, tùy lỗi | Giới hạn cấu trúc/IDs khi decode, không đổi policy | Giảm lỗi cấu trúc/ID; vẫn phải kiểm grounding và semantics |
| R4 | Chỉ ghép những phần đã có tín hiệu tốt | Kiểm tương tác; không giả định hiệu quả cộng dồn |

Chạy R0/R1/R2 trên 50 dev đã chọn trước bằng metadata/seed, cùng budget. R3 chỉ ưu tiên nếu baseline pilot có lỗi cấu trúc/ID đáng kể hoặc muốn khảo sát source-dependent constraints ở một arm riêng; không triển khai decoder phức tạp chỉ vì một paper tăng điểm ở task khác.

Đo theo bài và facet: P/R/F1, source/role correctness, missing independent concepts, grounding-valid items, raw/final label counts, repair success, correct→wrong, token/call/time. Số lượng nhãn tăng không đồng nghĩa recall nghĩa tăng; source review cần kiểm cả omissions.

Nếu chọn được pipeline, khóa trước khi train adapter mới. So **base chưa fine-tune và adapter mới dưới cùng pipeline**, rồi kiểm trên nguồn mới để kết luận generalization. Dev đã dùng chọn checkpoint; test cũ đã dùng phân tích lỗi, không coi bất kỳ tập đó là xác nhận độc lập mới. Chi tiết protocol tại [roadmap v1](QLORA_V1_IMPROVEMENT_ROADMAP_2026-10-21.md).

## 6. Mức độ chắc chắn của kết luận

| Nhận định | Mức bằng chứng |
|---|---|
| 7–8B có thể cải thiện IE bằng SFT theo task/guideline | Trực tiếp trong nhiều paper đã kiểm; hiệu quả phụ thuộc task/data |
| Constraints có thể cải thiện structured tasks mà không downstream SFT | Có bằng chứng trên LLaMA7B; chưa đồng nhất với scientific findings |
| Review thêm luôn sửa lỗi | Không được hỗ trợ; có thí nghiệm 8B cho kết quả ngược |
| Guideline/examples/repair được đề xuất sẽ tăng điểm Qwen3-8B của mình | Giả thuyết, phải đo trên dev |
| Mọi FP của v2 là nhãn sai | Không đủ bằng chứng; có ca role thật và ca granularity/reference mismatch |
| Có thể giữ số liệu paper làm mục tiêu F1 dự án | Không hợp lệ do khác task/metric/reference |

Tài liệu nghiên cứu không đặt lại kết quả đã công bố và không thay hướng đi người dùng đã chọn. Nó bổ sung cơ sở để **thử nhỏ, đo từng yếu tố trên base, rồi huấn luyện theo pipeline thống nhất**.
