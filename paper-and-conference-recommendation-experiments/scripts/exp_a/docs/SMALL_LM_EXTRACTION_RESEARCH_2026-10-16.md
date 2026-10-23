# Mô hình nhỏ và sai lệch khi trích xuất facet

Ngày tra cứu: 2026-10-16. Đã đọc toàn văn 5 nguồn sơ cấp; vị trí trích dẫn dưới đây dùng số trang PDF, bắt đầu từ 1. Ghi chú đối chiếu kết quả hiện tại của exp_a với nghiên cứu; các phương án sửa tiếp vẫn cần thử nghiệm riêng.

## Kết luận ngắn

Hướng có cơ sở nhất là làm rõ **quy tắc gán nhãn và đơn vị thông tin**, đưa ví dụ phân biệt các trường hợp dễ nhầm, rồi mới cân nhắc huấn luyện chuyên biệt. “Tách thành nhiều lời gọi” tự nó chưa giải quyết việc một thông tin thuộc method, contribution hay background.

Bằng chứng mạnh cho mô hình 7B–8B chủ yếu đến từ **fine-tuning**, không phải chỉ sửa prompt. Một thay đổi có thể tăng F1 trung bình nhưng làm một số nhãn giảm; cần xét precision, recall và lỗi theo từng facet. Các số từ bài báo không thể so trực tiếp với semantic F1 của exp_a.

## Đối chiếu trực tiếp với kết quả hiện tại

Đã đọc lại evaluation của bốn nhánh matrix v2, replay ablation và các lần sinh local đã lưu. Lượt nghiên cứu này không chạy thêm generator, không đổi extractor và không push kernel. Các số dưới đây dùng cùng 50 paper dev và AI reference đóng băng, ngưỡng embedding 0.85, ghép một-một.

Nhánh tốt nhất trong bốn cấu hình đã thử vẫn là **8b_original: micro F1 56.36, macro F1 56.89**. `4b_original` đạt micro 54.27; hai nhánh source-first lần lượt chỉ đạt 42.77 (4B) và 44.36 (8B).

| Facet | F1 4B original | F1 8B original | TP / FP / FN của 8B | Tỷ trọng FP+FN của 8B |
|---|---:|---:|---:|---:|
| problem | 38.46 | 44.44 | 16 / 25 / 15 | 11.9% |
| task | 59.42 | 54.05 | 40 / 24 / 44 | 20.2% |
| method | 59.84 | 65.38 | 85 / 31 / 59 | 26.8% |
| dataset | 75.86 | 70.59 | 12 / 6 / 4 | 3.0% |
| contribution | 47.45 | 50.00 | 64 / 65 / 63 | 38.1% |

**Method + contribution chiếm 218/336 = 64.9% số lượt nhãn không khớp** của baseline tốt nhất. Đây là FP+FN do scorer ghi nhận, không phải 218 lỗi thực tế độc lập: một label sai cách diễn đạt có thể đồng thời tạo một FP và một FN. Hai facet này cũng chiếm 271/402 = 67.4% nhãn tham chiếu, nên có ảnh hưởng lớn lên micro F1.

### Vì sao facet này tăng, facet khác giảm?

1. **F1 phụ thuộc cả nhãn khớp và nhãn thừa.** Contribution từ 4B sang 8B có TP giảm 65→64 nhưng FP giảm 82→65, nên F1 vẫn tăng 47.45→50.00. Dataset có TP tăng 11→12 nhưng FP tăng 2→6, nên F1 giảm 75.86→70.59. Tăng recall riêng chưa bảo đảm tăng F1.
2. **Đơn vị nhãn ảnh hưởng trực tiếp phép ghép.** P000669: 8B original xuất riêng `conditional random fields`, `morphosyntactic features`, `semantic roles features`, đạt 3 TP method. Source-first gộp cả ba vào một label dài và bị chấm 0 TP, 1 FP, 3 FN. Đây có phần là sai granularity so với reference, không thể diễn giải thành model hoàn toàn không nhận ra ba kỹ thuật.
3. **Có nhãn được nhắc tới nhưng scorer chưa nhận là khớp.** P001389: 8B original đã xuất tên JTV kèm mục đích sử dụng trong contribution; reference chỉ có tên model. Evaluation vẫn ghi tên model là thiếu. Trường hợp này cần người kiểm tra và hiệu chỉnh chính sách đơn vị nhãn; không nên hạ threshold chỉ để tăng điểm.
4. **Cỡ mẫu nhỏ và khác checkpoint.** Dataset chỉ có 16 nhãn tham chiếu. Hai model còn khác cách instruction tuning/checkpoint, không chỉ số tham số. Chênh lệch từng facet trên 50 bài không đủ để kết luận tăng kích thước gây ra một trade-off cố định.

Đã tính paired bootstrap theo paper, 20,000 lượt, seed 20261016: chênh lệch micro F1 8B−4B là **+2.09 điểm**, khoảng percentile 95% **[−3.37; +7.25] điểm**. Đây chỉ là mô tả biến thiên khi resample cohort dev đã dùng lặp lại, không xử lý thiên lệch chọn cấu hình hay sai lệch AI reference, và không phải khoảng tin cậy cho human accuracy trên dữ liệu mới.

### Nhóm hiện tượng cần sửa

Các trường hợp kiểm tra lại từ source và evaluation cho thấy:

- **Sai vai trò thông tin:** P003579 source-first đưa `F-values` và `news classification datasets` vào method. P002586 đưa background về các cách xử lý dữ liệu vào contribution. Có trong source chưa đủ để trở thành đúng facet hoặc đóng góp của bài hiện tại.
- **Gộp/tách nhãn không thống nhất:** P000669 gộp model và features; P000268 gộp Unigram, bigram, LDA. Method cần có quy ước về thành phần độc lập; contribution có thể cần giữ cả mệnh đề kết quả, không áp dụng cùng một quy tắc tách ngắn cho mọi facet.
- **Thiếu quan hệ, điều kiện hoặc phủ định:** P002586 kết quả cần giữ ngữ cảnh Tamil và điều kiện lượng test data lớn hơn training data; P004047 original bỏ phát hiện không tăng BLEU. Source-first phục hồi phát hiện không tăng BLEU nhưng làm mất method và thêm contribution không khớp, nên một ca sửa được chưa làm tổng điểm tăng.
- **Sai evidence ID, copy span và OCR:** Các lần sinh local có concept đúng hướng nhưng trỏ sai câu hoặc sửa khoảng trắng OCR nên bị loại. Đây là ma sát thật, nhưng chưa giải thích phần lớn mức giảm của source-first.

Chưa gán taxonomy thủ công cho toàn bộ FP/FN, nên **chỉ có thể xếp hạng định lượng theo facet**; không khẳng định đã đo được tỷ lệ toàn corpus của từng hiện tượng trên.

### Những giả thuyết đã bị ablation làm yếu đi

- Giữ nguyên raw output của 50 paper 8B source-first: bỏ riêng kiểm tra enum `kind` chỉ làm micro tăng **44.36→45.12**; bỏ kind và sửa span không verbatim đạt **45.07**. Khoảng cách với original 56.36 vẫn lớn. Riêng method vẫn 55 TP, so với 85 TP của original. Vì vậy sửa parser/gate đơn lẻ chưa đủ.
- Chấp nhận pool candidate chưa qua grounding cũng chỉ đạt micro **45.37** trên 8B, kèm nhiều FP. Đây không phải một upper bound toán học hay cấu hình an toàn để triển khai.
- Sinh mới 4 paper khó bằng 4B, chung validation: bỏ yêu cầu sinh span trong prompt làm F1 gộp method+contribution **22.22→41.38**. Chỉ bỏ kind đạt 16.67. Kết quả này ủng hộ thử đơn giản hóa schema, nhưng chỉ trên bốn ca chọn sẵn, một lần sinh không review.
- Prompt method atomic trên 3 paper làm method F1 **12.50→44.44**, nhưng phần lớn tăng đến từ P000669; hai ca khác vẫn lỗi role/evidence. Đây là bằng chứng một lỗi cụ thể sửa được, chưa chứng minh giải pháp tổng quát.

Suy luận ưu tiên: **quy tắc vai trò + đơn vị nhãn + độ trung thực của claim** đang là nút thắt đáng xử lý nhất. Không có bằng chứng để quy hiện tượng này cho gradient conflict của multi-task training, vì exp_a hiện chưa fine-tune.

### Thứ tự đề xuất cho vòng kế tiếp

1. Giữ `8b_original` làm baseline. Dùng khoảng 20 ca khó để thống nhất policy và ví dụ đối chiếu; đây là tập phát triển hướng dẫn, không được đưa sang test như dữ liệu chưa thấy. Cho phép một model mới vừa là method được dùng vừa là artifact contribution; không ép facet loại trừ nhau.
2. Trong cùng một matrix, giữ cố định checkpoint/decoding/scorer, thử lần lượt baseline; policy ngắn; policy + ví dụ đúng/sai theo role; và biến thể tốt trước đó bỏ field span do model sinh, lấy câu nguồn bằng evidence ID. Mỗi so sánh phải thay một yếu tố, dùng cùng ngân sách generation/review và lưu cả output thô.
3. Đánh giá trên một tập paper mới được người kiểm tra, báo cáo P/R/F1 theo facet, evidence correctness và lỗi claim. Giữ benchmark AI cũ như thước đo phụ để không nhầm cải thiện cách khớp reference với cải thiện nội dung.
4. Nếu lỗi role/granularity vẫn lặp lại, chuyển sang thử SFT/QLoRA theo đúng policy với dữ liệu teacher được kiểm tra, có facet vắng mặt và nhầm lẫn khó. Đây là hướng có bằng chứng từ model 7B–8B; số lượng dữ liệu đủ dùng và chi phí trên GPU hiện có chưa được xác nhận.

Mục tiêu chọn cấu hình là tăng chất lượng tổng và giảm các hồi quy quan trọng theo facet trên tập mới. Không có cơ sở bảo đảm mọi facet đều tăng trong từng lượt thử.

## Bằng chứng đã kiểm tra

| Nguồn | Mô hình thực sự được thử | Can thiệp | Bằng chứng trong toàn văn | Giới hạn khi chuyển sang exp_a |
|---|---|---|---|---|
| [GoLLIE, ICLR 2024](https://arxiv.org/pdf/2310.03668) | Code-LLaMA **7B**, thêm 13B/34B để khảo sát kích thước (§4.2, tr.5). | Fine-tune với định nghĩa nhãn, ví dụ tiêu biểu và regularization; biểu diễn bằng code (§3). | Ablation: **55.3** F1; bỏ ví dụ tiêu biểu: **49.9**; bỏ toàn bộ thành phần, gồm guidelines: **42.3** (Table4, tr.8). §6, tr.9 ghi nhận lỗi nhãn quá rộng và xung đột mức chi tiết. | Đây là mô hình đã học cách tuân thủ guidelines. Không chứng minh thêm guidelines vào Qwen chưa fine-tune sẽ đạt mức tăng tương tự; nhãn NER/EE khác facet khoa học. |
| [UniversalNER, ICLR 2024](https://arxiv.org/pdf/2308.03279) | LLaMA **7B/13B**; teacher gpt-3.5-turbo-0301 (§3.1, §5.1). | Distillation theo nhiệm vụ; truy vấn loại thực thể vắng mặt có đích **[]** (§3.2, tr.4). | UniNER-7B, 7 tập OOD: không negative sampling **31.5**, uniform **47.7**, frequency **53.4** F1 (Table4, tr.8). | Đây là negative supervision khi **huấn luyện**. Loại vắng mặt khác candidate có thật nhưng sai vai trò. Không phải bằng chứng rằng thêm câu “không được hallucinate” vào prompt là đủ. |
| [Classify First, and Then Extract, NLLP 2024](https://aclanthology.org/2024.nllp-1.25.pdf) | GPT-3.5-turbo-0125 phân loại; GPT-4-1106-preview / GPT-4o-mini-2024-07-18 trích xuất (§3, tr.4–5). **Bài không nêu số tham số**. | Phân loại event trước, chọn ví dụ theo event; extractor vẫn nhận danh sách loại đầy đủ (§3.2). | GPT-4o mini, OOD: event 5-shot **35.04→42.13**; entity 1-shot **55.11→51.06** (Table2, tr.7). | “Mini” không xác nhận đây là mô hình 4B/8B. Task là di chúc pháp lý. §6.2 cảnh báo thiếu ví dụ khi 1-shot. Không bảo đảm mọi kiểu chaining đều tốt. |
| [Revisiting Task Definition Biases, Findings EMNLP 2024](https://aclanthology.org/2024.findings-emnlp.601.pdf) | Probe: Llama-v2 **13B**, Flan-T5 **11B**; giải pháp dùng Flan-T5 11B (§3.2, §6). | Đo khác biệt quy ước nhãn; bias-aware fine-tuning rồi LoRA theo dataset (§5). | Đổi tên nguồn sang nguồn sai làm NER F1 giảm trung bình **12.6/18.4 điểm** tương ứng hai model; nickname hầu như không đổi (Table3, tr.6). | Kết quả phụ thuộc mô hình đã được source-prompt tuning; không phải hiệu ứng đổi tên facet tùy ý. Chỉ nghiên cứu NER/RE; không trực tiếp xác nhận trên Qwen3 hoặc contribution. |
| [GuideX, arXiv 2025](https://arxiv.org/pdf/2506.00649v1) | Teacher Llama3.1-Instruct **70B**; student Llama3.1-base **8B**, QLoRA (§5.1/5.4, tr.6). | Sinh schema, guidelines và annotations từ văn bản, rồi fine-tune (§3). | Synthetic-only: mean **30.08→37.14**. Synthetic rồi gold: **62.77→64.15**, nhưng Literature **65.41→63.79** (Table2, tr.7). Music Other **15.99→13.02** (Table4, tr.9). | Sinh theo document, đánh giá sentence-level NER; chưa kiểm chứng document facets (Limitations, tr.9). Schema/code hợp lệ không tự chứng minh nội dung đúng. |

**Phạm vi của “mô hình nhỏ”:** trong các nguồn này, bằng chứng gần cấu hình 4B/8B nhất là GoLLIE-7B, UniNER-7B và GuideX-8B. Những biến thể 11B/13B/34B hoặc API đóng không nên được trình bày như kết quả đã xác nhận cho Qwen3-4B/8B. Không nguồn nào ở đây đo trực tiếp cấu hình greedy + NF4 của exp_a.

**Ý nghĩa của “zero-shot”:** một số mô hình vẫn đã được fine-tune trên nhiều dữ liệu IE; “zero-shot” nói về schema/domain đánh giá chưa dùng làm supervision tương ứng. Nó không đồng nghĩa với dùng model gốc và một prompt không có huấn luyện.

## Các hướng có thể kiểm chứng trong dự án

Các mục sau là **đề xuất suy luận cho exp_a**, chưa phải kết luận thực nghiệm.

1. **Chốt một annotation policy ngắn cho từng facet.** Quy định rõ thông tin của bài hiện tại hay nghiên cứu trước; method được dùng hay được đề xuất; contribution là artifact hay phát hiện; task khác problem ở đâu. Định nghĩa cách xử lý điều kiện, phủ định, kết quả không cải thiện, tên viết tắt và nhãn ghép. Mỗi quy tắc nên có một ví dụ được nhận và một trường hợp gần giống bị loại.

2. **Thử ví dụ đối chiếu trước khi thêm pipeline.** Giữ nguyên model, decoding, input và metric; so baseline với guidelines ngắn, rồi guidelines + vài ví dụ khó đã kiểm tra. Ví dụ cần dạy cách phân biệt role và granularity, không chỉ minh họa JSON. Dùng trường hợp facet vắng mặt với output rỗng, nhưng không ép số lượng nhãn cố định. Đo riêng 4B và 8B; một prompt không nhất thiết tốt cho cả hai.

3. **Nếu thử classify-first, tách đúng quyết định đang sai.** Phân loại evidence/candidate vào các vai trò dự kiến trước, rồi tạo label theo facet. Cần đo recall của bước phân loại, chạy một điều kiện định tuyến đúng do người kiểm tra để ước lượng tiềm năng, và giữ trường hợp chưa chắc thay vì loại cứng. Ma trận source-first hiện tại chỉ tách lời gọi tạo method/contribution; nó **chưa thử cơ chế chọn ví dụ theo phân loại** của NLLP. Không thể dùng thất bại đó để bác bỏ bài báo, cũng không thể lấy bài báo để bảo đảm pipeline mới sẽ tăng điểm.

4. **Kiểm tra đơn vị output như một biến độc lập.** So label ngắn/atomic với label ghép; giữ riêng evidence ID và câu chứng minh. Với method, tên kỹ thuật thường khác một câu mô tả quy trình; với contribution, mệnh đề có điều kiện có thể là đơn vị cần giữ. Chỉ thay một yếu tố mỗi ablation. Nếu cần copy span chính xác, thử gắn span sau bước tạo label, rồi đo cả lỗi nội dung và lỗi evidence.

5. **Chỉ xét SFT/QLoRA sau khi policy và đánh giá ổn định.** Tạo tập train nhỏ có người kiểm tra, gồm nhãn đúng, facet vắng mặt và các nhầm lẫn role/granularity thực tế. Dữ liệu teacher/synthetic cần audit; không chuyển toàn bộ output AI thành “gold”. Huấn luyện trên dữ liệu theo đúng policy là hướng được các nguồn hỗ trợ tốt hơn giả định rằng model tự đọc lại output sẽ sửa được lỗi. “Hard negative sai role” là giả thuyết mở rộng cần kiểm chứng, khác negative type vắng mặt của UniNER.

## Cách đánh giá để tránh tối ưu nhầm

Bối cảnh được cung cấp: exp_a dùng 50 paper dev đã được thử nhiều lần, 402 nhãn AI reference đóng băng, semantic embedding F1 với ngưỡng 0.85 và ghép một-một. Reference này phản ánh một quy ước của AI; chưa phải human gold độc lập.

- Dành một tập paper mới, có người kiểm tra annotation policy, trước khi chọn cấu hình cuối. Không đưa ví dụ từ paper đánh giá vào prompt/train.
- Báo cáo P/R/F1 và số dự đoán theo facet, cùng micro tổng. Với ablation, so chênh lệch trên cùng paper; nếu ước lượng bất định thì resample theo paper.
- Audit một mẫu FP/FN bằng văn bản nguồn: sai role, thiếu thông tin, nhãn quá rộng/hẹp, split/merge, phủ định/điều kiện, evidence sai và reference có vấn đề. Đây là các loại lỗi để kiểm tra, chưa phải taxonomy đã được đếm đầy đủ.
- Giữ điểm benchmark hiện tại để so nội bộ, nhưng bổ sung tỷ lệ nhãn được người kiểm tra chấp nhận và độ đúng của evidence. Nhờ vậy có thể phân biệt tiến bộ nội dung với tiến bộ do khớp cách diễn đạt reference.
- Không có bằng chứng trong năm nguồn rằng **intrinsic self-review**, chỉ yêu cầu cùng model tự phê bình mà không có tín hiệu ngoài, là cách sửa đã được xác nhận cho cấu hình này.

## Dữ liệu kiểm tra tại local

- [Matrix v2: điểm bốn nhánh](<D:/KHAI/mon hoc/năm 3/HK1 2025-2026/DS300/Đồ án/paper-and-conference-recommendation-experiments/data/exp_a/evaluation/facet_matrix_v2/experiment_table.md>).
- [Chẩn đoán hiện tại, hash input và bootstrap](<D:/KHAI/mon hoc/năm 3/HK1 2025-2026/DS300/Đồ án/paper-and-conference-recommendation-experiments/data/exp_a/evaluation/facet_ablation_local/current_diagnosis_2026-10-16.json>).
- [Replay 50 paper, giữ nguyên raw output](<D:/KHAI/mon hoc/năm 3/HK1 2025-2026/DS300/Đồ án/paper-and-conference-recommendation-experiments/data/exp_a/evaluation/facet_ablation_local/ablation_summary.json>).
- [So sánh các lần sinh local với validation chung](<D:/KHAI/mon hoc/năm 3/HK1 2025-2026/DS300/Đồ án/paper-and-conference-recommendation-experiments/data/exp_a/evaluation/facet_ablation_local/common_validation_summary.json>).
- [Văn bản nguồn của pilot50](<D:/KHAI/mon hoc/năm 3/HK1 2025-2026/DS300/Đồ án/paper-and-conference-recommendation-experiments/data/exp_a/pilot50/ai_reference_v1/source_papers.jsonl>).

## Nguồn toàn văn

- [Sainz et al. — GoLLIE: Annotation Guidelines improve Zero-Shot Information-Extraction](https://arxiv.org/abs/2310.03668), ICLR 2024.
- [Zhou et al. — UniversalNER: Targeted Distillation from Large Language Models for Open Named Entity Recognition](https://arxiv.org/abs/2308.03279), ICLR 2024.
- [Kwak et al. — Classify First, and Then Extract: Prompt Chaining Technique for Information Extraction](https://aclanthology.org/2024.nllp-1.25/), NLLP 2024.
- [Huang et al. — Is There a One-Model-Fits-All Approach to Information Extraction? Revisiting Task Definition Biases](https://aclanthology.org/2024.findings-emnlp.601/), Findings EMNLP 2024.
- [De La Fuente et al. — GuideX: Guided Synthetic Data Generation for Zero-Shot Information Extraction](https://arxiv.org/abs/2506.00649v1), bản arXiv v1, 2025. Các số ở ghi chú lấy từ bảng toàn văn, không lấy số làm tròn trong abstract.

