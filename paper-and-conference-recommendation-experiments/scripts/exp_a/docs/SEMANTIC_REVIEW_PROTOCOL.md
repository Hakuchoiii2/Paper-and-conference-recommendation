# Kiểm tra ngữ nghĩa cho exp_A

Phiên bản 1.0, 2026-10-14. Áp dụng guideline năm facet trong
[FACET_GUIDELINE.md](../../../docs/FACET_GUIDELINE.md). Đây là quy trình kiểm tra bản nhãn hiện có,
không phải một kết quả semantic precision/recall đã được đo.

## Tiêu chí chốt một nhãn

Một nhãn đạt khi **đồng thời** có căn cứ trong nguồn, đúng vai trò facet và giữ
nguyên ý nghĩa của tuyên bố. Tìm thấy chữ trong abstract chỉ kiểm tra được sự có
mặt; câu nguồn phải thực sự hỗ trợ ý nghĩa của nhãn.

| Câu hỏi bắt buộc | Cách kiểm tra | Loại nếu |
|---|---|---|
| Nguồn có nói điều này không? | Đọc cả câu dẫn chứng và câu trước/sau nếu có đại từ | Chỉ trùng từ, phải suy thêm thuật toán/dataset/tính mới |
| Facet có đúng vai trò không? | Xác định nhãn là vấn đề, mục tiêu, cách làm, resource hay artifact/finding | Input hoặc người tham gia bị coi là method; ứng dụng tương lai bị coi là task đã làm |
| Nhãn có thể hiểu độc lập không? | Xác định chủ thể, hành động/quan hệ và đối tượng chính | Chỉ còn “latent”, “many subjects do not”, “8 percentage points” |
| Có mất điều kiện làm đổi nghĩa không? | Gạch chân phủ định, comparator, metric, phạm vi và các từ chỉ mức chắc chắn | Bỏ “when”, “than”, “may”, “we aim”, “we postulate”, “tend to predict” |
| Đóng góp có được tuyên bố không? | Tách cái tác giả tạo/giới thiệu hoặc kết quả họ báo cáo khỏi dữ liệu/phương pháp sẵn có | Quy mô corpus, giả định hay thuật toán nền bị gọi là artifact mới |
| Nguồn có đủ để chốt không? | Kiểm tra abstract bị cắt, macro LaTeX và tên resource bất thường | Phải đoán tên hoặc bổ sung phần abstract thiếu |

Với nhãn là tên artifact (ví dụ SCAN), không ép thêm một câu dài; giữ câu chứng
minh tác giả giới thiệu artifact ấy trong evidence. Với nhãn là kết quả/quan hệ,
giữ các thành phần cần thiết để tránh đổi nghĩa, dù nhãn dài hơn. Không tách chủ
thể và predicate thành hai nhãn rồi làm mất quan hệ giữa chúng.

## Phân biệt năm facet

| Facet | Câu kiểm tra | Ví dụ bẫy |
|---|---|---|
| problem | Hạn chế hoặc câu hỏi nào thúc đẩy nghiên cứu? | “completion rates” chưa nói vấn đề; “completion rates are low” có hạn chế |
| task | Tác giả thực hiện mục tiêu tác nghiệp nào? | “detect student stopout” khác “detect student”; số đo accuracy không nằm trong task |
| method | Tác giả dùng cách làm nào để đạt mục tiêu? | “crowdworkers” là người; “collect scores from crowdworkers” mô tả thủ tục |
| dataset | Tên dữ liệu/resource được sử dụng hay giới thiệu có rõ không? | Không tự lấy tên trường, bảo tàng, dự án hay nền tảng làm tên một corpus chưa được đặt tên |
| contribution | Artifact hoặc finding mới nào được tác giả tuyên bố? | “986 networks” là mẫu phân tích, chưa phải finding hay dataset được phát hành |

Một concept có thể có hai vai trò nếu hai vai trò đều được nguồn hỗ trợ. Ví dụ
artifact mới được đề xuất có thể xuất hiện trong contribution và method nếu tác
giả thực sự triển khai nó. Không ép mọi concept chỉ vào một facet.

Với các trường hợp resource bị audit đánh dấu, bản sửa hiện dùng lựa chọn thận
trọng: giữ corpus/benchmark/database/lexicon có tên và căn cứ sử dụng; bỏ tên
dự án, cơ quan, nền tảng hoặc công cụ tìm kiếm khi chưa xác định được resource
dữ liệu cụ thể. `[]` nghĩa là không đủ thông tin để ghi một tên theo quy tắc này,
không có nghĩa nghiên cứu không dùng dữ liệu. Đây là cách xử lý các trường hợp
đã audit, chưa chứng nhận mọi tên resource ở các bài còn lại.

## Hai lượt kiểm tra để tránh bị nhãn dẫn dắt

1. **Đọc nguồn trước, che nhãn.** Từ title/abstract, viết năm facet dự kiến và câu
   evidence. Phân biệt phần background, phần tác giả làm và ứng dụng tương lai.
   Lượt này giúp phát hiện ý chính bị thiếu trong nhãn hiện tại.
2. **Đối chiếu từng nhãn với nguồn.** Mở bản GPT và evidence, áp dụng sáu câu hỏi
   bắt buộc ở trên. Tìm một cách hiểu của nhãn mà abstract không hỗ trợ; nếu có,
   sửa để giữ qualifier hoặc loại nhãn. Đọc cả câu thay vì chỉ vùng từ trùng.
3. **Đối chiếu các mục bị thiếu.** Kiểm tra lại task chính, technique chính,
   artifact mới và finding quan trọng. Không ép mọi chi tiết hoặc mọi ứng dụng
   minh họa thành một concept riêng.
4. **Chốt và lưu lý do.** Dùng một trong bốn quyết định: `accept`, `revise`,
   `remove`, `source_confirmation_pending`. Ghi nhãn cuối, quote và lý do;
   chưa đủ nguồn thì để pending, không đoán để lấp trường trống.
5. **Rà độc lập.** Nếu tiếp tục dùng GPT, dùng lượt/chat riêng chỉ có guideline
   và nguồn ở bước 1; sau khi có nhãn độc lập mới cho xem bản hiện tại ở bước 2.
   Hai lượt GPT vẫn là kiểm tra AI. Để chốt human gold, người đọc cần xác nhận
   nhãn cuối; xem qua snapshot trước sửa chưa xác nhận các sửa mới.

Nếu chỉ rà một mẫu, chọn mẫu ngẫu nhiên và rà thêm mọi bài nguồn có vấn đề. Báo
cáo kết quả của mẫu; không tuyên bố cả 400 bài đã được kiểm tra độc lập. Muốn
chốt toàn bộ 400 bài, từng bài đều phải đi qua bước đối chiếu và chốt.

## Ví dụ từ chính cohort

| Bài | Nhãn bị lỗi | Điều phải giữ |
|---|---|---|
| P001366 | tweets ... are abusive at substantially higher rates | Chủ thể là **classifiers**, quan hệ là **tend to predict**; finding nói về bias của bộ phân loại |
| P002765 | RNNs fail spectacularly | Điều kiện **when generalization requires systematic compositional skills** |
| P002084 | User-Created Personas reveal specific characteristics | Nguồn nói **we postulate**; không chốt thành kết quả đã chứng minh |
| P000428 | method: online handwriting data | Đây là input; phương pháp là **image data generation pipeline** |
| P000474 | 90% of monolingual performance | **about**, **combined resources**, **retrieving Chinese documents** |

## Prompt kiểm tra có thể dùng lại

```text
Bạn là người kiểm tra ngữ nghĩa của nhãn năm facet.
Chỉ dùng title/abstract được cung cấp và guideline; không dùng output Qwen,
điểm evaluator hay kiến thức bên ngoài để bổ sung nhãn.

Lượt 1 (chưa có nhãn): đọc nguồn, phân biệt background/công việc hiện tại/
ứng dụng tương lai, rồi đề xuất problem, task, method, dataset, contribution
kèm câu nguồn. Để [] nếu thiếu căn cứ. Đánh dấu nguồn bị cắt hoặc tên chưa rõ.

Lượt 2 (sau khi có bản nhãn): với từng nhãn, trả về:
paper_id, facet, current_label, decision, final_labels, exact_quote,
source_entails_label, facet_role_correct, necessary_qualifiers_preserved,
reason, source_confirmation_pending.

Thử chỉ ra cách nhãn có thể bị hiểu rộng hơn/sai khác so với nguồn.
Kiểm tra chủ thể, quan hệ, đối tượng, phủ định, phạm vi, điều kiện, metric,
comparator và trạng thái hypothesis/goal/finding. Quote có mặt không đủ để accept.
Với contribution, không coi dữ liệu/phương pháp sẵn có là thứ được tạo mới.
Với task, không coi mọi background/downstream example là nhiệm vụ chính.
Kiểm tra cả ý chính bị thiếu và nhãn thừa. Không sửa nhãn để làm tăng exact F1.
```

## Kiểm tra bằng máy và đọc điểm đúng cách

Sau khi sửa nhãn, kiểm tra số ID/cohort, năm facet, nhãn trùng, evidence còn đúng
văn bản nguồn, mapping concept–evidence, hash và bản backup. Khi đổi nhãn phải
cập nhật evidence cùng lúc. Nhãn diễn đạt lại được chấp nhận nếu evidence hỗ
trợ trọn ý và có lý do; không bắt buộc nhãn là substring của câu gốc.

Nếu đánh giá output mô hình theo ngữ nghĩa, so từng facet với reference đã chốt,
ghép concept tương đương theo nghĩa một–một, và ghi quyết định cho từng cặp:
`equivalent`, `partial`, `wrong_facet`, `unsupported`. Giữ qualifier làm thay đổi
nghĩa; không dùng substring/similarity threshold để tự quyết định equivalent.
Một nhãn không được ghép với nhiều reference để tăng số match; nhãn chứa nhiều
concept phải được xử lý cùng quy tắc độ chi tiết cho cả hai bên.

Chỉ các cặp `equivalent` được tính TP; nhãn dự đoán không được ghép là FP và
reference không được ghép là FN. Khi cả hai concept có mặt nhưng chỉ khớp một
phần, ghi `partial` và không tính thành đúng đầy đủ (để FP/FN của hai phía).
Ghi sổ quyết định và bất đồng trước khi tính semantic precision/recall/F1.

Evaluator hiện có hai chế độ: `--matching exact` đo khớp chữ; mặc định
`--matching embedding --threshold 0.85` dùng Qwen3-Embedding-0.6B, chuẩn hóa
tên/alias có nguồn và chặn một số khác biệt số liệu, metric, phủ định/thao tác
trước khi ghép một–một. Cặp canonical lưu cosine thật và assignment score riêng.
Thử 100 cặp thật chưa đủ cơ sở hạ ngưỡng; xem [báo cáo hiện hành](MATCHER_REFERENCE_REPORT.md).
Điểm embedding là đồng thuận xấp xỉ theo quy tắc/ngưỡng, không
thay thế quyết định equivalent được review theo quy trình trên. Báo cáo giữ cả
baseline lexical và từng cặp/similarity để kiểm tra. Tách lỗi trích xuất của mô
hình khỏi lỗi hoặc bất đồng ở reference.

## Năm bài chưa đủ nguồn để chốt

P000042 (`\\miniI`), P004138 (`iciest`), P001758 (`perception algorithm`),
P002171 (abstract bị cắt), P003362 (`FameNet II`). Bản sửa đã bỏ identifier
nghi vấn và giữ phần có căn cứ; vẫn cần xác minh bản nguồn để kiểm tra tính đầy
đủ. Không tự đổi những tên này thành tên được cho là đúng từ trí nhớ.
