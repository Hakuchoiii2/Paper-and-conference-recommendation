# Báo cáo: Exposure, interaction và phương án bổ sung dữ liệu cho thực nghiệm D

**Ngày lập:** 15/10/2026.  
**Phạm vi ban đầu:** Tổng hợp trao đổi, đối chiếu `overview.md`, mã nguồn và bộ D đã xuất. Các mục 1–11 mô tả bộ D gốc và đề xuất tại thời điểm viết; xem cập nhật triển khai ngay dưới đây để biết trạng thái hiện tại.

## Cập nhật triển khai theo lựa chọn của người thực hiện — 15/10/2026

Đã chọn và triển khai **pilot observation tổng hợp riêng, giữ anchors/candidates thật**, bằng quy tắc có nhiễu, không dùng LLM hoặc tải dữ liệu ngoài. Không sửa corpus, annotation A, C, validator hay estimator chung. Vì vậy các nhận định “chưa triển khai” trong phần báo cáo gốc bên dưới là lịch sử, không còn áp dụng cho pilot này.

- Mã nguồn: [run_synthetic_observation_pilot.py](../run_synthetic_observation_pilot.py). Hướng dẫn CMD, cấu trúc output và giới hạn: [SYNTHETIC_OBSERVATION_PILOT.md](../SYNTHETIC_OBSERVATION_PILOT.md).
- Nguồn là snapshot A/C/D đã validate. Chọn nguyên 30 phiên, mỗi tổ hợp focus × direction × query mode một phiên; đủ 30 anchor riêng. Giữ nguyên query, 20 candidates/phiên, nhãn và cutoff.
- Mỗi cấu hình tạo riêng 240 mô tả observation có cờ synthetic, 120 exposures và 240 interactions. Facet được dựng có kiểm soát từ concept nguồn; không gọi chúng là paper thật hoặc silver A, không nối vào corpus canonical.
- Dùng 3 seed (42/43/44) × 2 noise_std (0,2/0,5), so cả bốn baseline + oracle trong hai điều kiện không observation/có observation trên cùng các phiên. Giữ profile C và TF-IDF candidate cố định để tránh lẫn tác động thay biểu diễn.
- Matching vẫn chính xác ngoài focus; sử dụng checker `check_d` hiện hành trên overlay, không bỏ validation. Public scorer chỉ nhận facet/log quan sát; hidden intent chỉ vào simulator/evaluator. Provenance mô phỏng được lưu riêng trong ground_truth.
- 5 tests pass; 6 cấu hình pass structural/matching/time/label checks, tái lập cùng seed, đối chứng khớp predict baseline nguồn và source hashes không đổi. Đã kiểm tra 77 hashes output của pilot.
- Behavior không observation có focus coverage/accuracy 0. Với synthetic và noise 0,2: cả ba seed đạt focus accuracy/coverage 1,0. Với noise 0,5: accuracy 0,7333–0,8333, coverage 0,8000–0,9333. Đây là kết quả dưới simulator được thiết kế, không xác nhận hành vi người thật.
- Ranking chưa cải thiện: trên cùng pilot, behavior nDCG@10 từ 0,9223 xuống 0,9196; compliance@5 từ 0,2533 xuống 0,2467. Không dùng việc có thêm exposure hoặc direction đúng hơn để tuyên bố ranker tốt hơn.
- Output: `data/exp_d/evaluation/synthetic_observation_pilot_v1/`; xem `focus_sensitivity.json`, các file `seed_*/results/report.md` và manifest gốc của pilot.

Lưu ý: bốn cặp có bốn lần lấy nhiễu riêng nhưng các cấu hình facet same-focus có thể lặp; không coi là bốn bài thật hay bốn nội dung độc lập. Đây là bundle overlay dùng runner riêng, không giả làm dataset chuẩn real/A silver để nạp bằng runner canonical.

## 1. Kết luận chính

D hiện có bài mốc, phiên, queries, candidates và nhãn đánh giá, nhưng hai file exposure và interaction của D đang rỗng. Nguyên nhân trực tiếp trên bộ đã kiểm tra là: sau khi chọn candidates và loại chúng khỏi nguồn bài quan sát, không còn bài cùng context và cùng focus để ghép cặp.

Interaction của C vẫn tồn tại và được D kế thừa để khai thác sở thích dài hạn. Phần thiếu là phản ứng trong phiên D, dùng để thử suy nhu cầu hiện tại so với bài mốc.

Có thể nghiên cứu bổ sung bài quan sát và tương tác mô phỏng. Tuy nhiên, ngẫu nhiên và nhiễu cần được thiết kế theo intent; chúng không tự bảo đảm tính thực tế hoặc tự giải quyết việc thiếu bài. Nếu bổ sung bài tổng hợp, kết luận phải gắn với điều kiện mô phỏng đã thiết kế.

Thay đổi corpus gốc ảnh hưởng đến annotation và provenance của các bước phụ thuộc. Cần phân biệt **không sửa logic generator C** với **không cần tạo lại hoặc điều chỉnh handoff C**; hai việc này không tương đương trong pipeline hiện tại.

## 2. Các thành phần cần phân biệt

| Thành phần | Ý nghĩa trong D |
|---|---|
| Corpus | Toàn bộ tập bài nguồn mà pipeline biết tới; file hiện tại là `data/processed/papers.jsonl` |
| Bài mốc / anchor | Bài người dùng đang đọc, dùng làm điểm tham chiếu |
| Context | Khía cạnh cần giữ liên quan với bài mốc để xác định phạm vi phiên |
| Focus | Khía cạnh muốn so sánh với bài mốc theo hướng giống hoặc khác |
| Bài quan sát | Bài được hiển thị trước cutoff để lấy phản ứng và suy intent |
| Exposure | Bản ghi lượt hiển thị; trong D hiện tại, mỗi exposure chứa một cặp bài trong `paper_ids` |
| Interaction | Phản ứng trên từng bài của exposure: view, click, save, like hoặc dislike |
| Candidates | 20 bài cần xếp hạng để đánh giá; tách khỏi bài quan sát của phiên |
| Intent mô phỏng | Nhu cầu ẩn do generator đặt ra; phương pháp phải suy từ thông tin được quan sát |

**Ngoài candidates không có nghĩa là ngoài corpus.** Một bài có thể thuộc corpus nhưng được dành riêng cho phần quan sát. Nếu dùng bài ngoài corpus hiện tại, phải cung cấp bài và facet tương ứng cho pipeline.

### 2.1. Exposure và interaction được lưu như thế nào?

Ví dụ minh họa, chưa phải log thực tế:

| Bản ghi | Nội dung |
|---|---|
| Exposure E1 | Hiển thị `paper_ids = [B, C]` |
| Interaction 1 | Click bài B, liên kết tới E1 |
| Interaction 2 | Save bài C, liên kết tới E1 |

Exposure chứa danh sách bài được hiển thị. Interaction được lưu riêng, nối với exposure bằng `exposure_id` và xác định bài bằng `paper_id`.

Trong generator D hiện tại, ghép được cặp mới tạo exposure; sau đó mới sinh interaction trên các bài của exposure đó.

## 3. Hai bài quan sát giống và khác ở đâu?

Ví dụ minh họa: context là **nhận diện bệnh trên lá cây**, focus là **phương pháp**.

| Bài | Tác vụ | Phương pháp | Vai trò |
|---|---|---|---|
| A | Nhận diện bệnh trên lá cây | CNN | Bài mốc |
| B | Nhận diện bệnh trên lá cây | CNN | Quan sát phía giống focus |
| C | Nhận diện bệnh trên lá cây | Transformer | Quan sát phía khác focus |

Cặp quan sát là **B–C**. Cả hai đều cùng context với A; một bài giống và một bài khác focus so với A. Bài mốc A không được tính là một trong hai bài quan sát.

Một bài về dự đoán giá nhà không đáp ứng context của ví dụ, nên không dùng làm B hoặc C.

Matching hiện hành còn yêu cầu hai bài có trạng thái overlap hoặc thiếu tương đương trên mọi facet ngoài focus. Điều này nhằm giảm việc phản ứng khác nhau do các khía cạnh khác cùng thay đổi. Nó chưa chứng minh quan hệ nhân quả trên hành vi người thật.

Trong code, overlap là giao concept sau chuẩn hóa, không phải độ giống ngữ nghĩa. Hai cách diễn đạt gần nghĩa chưa chắc được tính là overlap.

### 3.1. Nhãn relevance khác với phản ứng như thế nào?

Generator đặt intent mô phỏng trước, rồi tính nhãn cho candidates từ annotation facet:

| Điều kiện | Relevance |
|---|---:|
| Có context overlap và thỏa hướng focus | 2 |
| Có context overlap nhưng sai hướng focus | 1 |
| Không thỏa context hoặc thiếu facet cần xét | 0 |

Sau đó, generator sinh phản ứng cho các bài quan sát theo intent đó. Phương pháp dùng phản ứng để thử suy ngược intent đã giấu. Các nhãn này là ground truth mô phỏng theo quy tắc, chưa phải nhãn được người dùng thật xác nhận.

## 4. Interaction của C khác interaction của D thế nào?

| Nội dung | C | D |
|---|---|---|
| Thời điểm | Lịch sử trước các phiên D | Quan sát đầu phiên D, trước cutoff |
| Thông tin chính | Sở thích qua lịch sử người dùng | Hướng giống/khác bài mốc trong phiên đang xét |
| Cách dùng hiện tại | D kế thừa lịch sử C để tính importance của các facet | Nhánh behavior so phản ứng giữa các bài quan sát để suy directions |
| Loại hành động | View, click, save, like, dislike | Cùng các loại hành động, nhưng gắn với phiên và exposure của D |

Ví dụ: lịch sử C cho thấy user thường lưu bài CNN. Trong phiên D hiện tại, user có thể muốn tìm phương pháp khác CNN cho cùng tác vụ. Lịch sử cũ vẫn hữu ích nhưng chưa xác định được nhu cầu thay đổi trong phiên này.

Do đó, cách diễn đạt rõ hơn cho hạn chế là: **“Thiếu exposure và interaction quan sát trong phiên D.”** Không nên diễn đạt thành cả hệ thống chưa có dữ liệu hành vi.

## 5. Kết quả kiểm tra bộ D đã xuất

Các số liệu sau được kiểm tra trên bộ D hiện có trong repository, gồm 1.500 phiên. Đây không phải kết quả của output generator mới trong bộ nhớ được mô tả trong `overview.md`.

| Chỉ số | Kết quả |
|---|---:|
| Số bài trong corpus | 4.210 |
| Số bài còn lại sau bộ lọc annotation hiện hành | 3.240 |
| Số phiên D | 1.500 |
| Số dòng nhãn session–candidate | 30.000 |
| Số dòng exposure D | 0 |
| Số dòng interaction D | 0 |
| Phiên có đúng một bài cùng context và giống focus, trước khi loại candidates | 762 |
| Phiên không có bài cùng context và giống focus, trước khi loại candidates | 738 |
| Phiên ghép được cặp theo matching đầy đủ, trước khi loại candidates | 30 |
| Tổng số cặp theo matching đầy đủ, trước khi loại candidates | 30 |
| Phiên còn bài cùng context và giống focus sau khi loại candidates | 0 |
| Phiên ghép được cặp sau khi loại candidates | 0 |

**Phạm vi số liệu:** Phân bố 762/738 mô tả các thiết kế anchor/context/focus của 1.500 phiên đã xuất; không phải thống kê tất cả tổ hợp có thể có trong corpus.

**Cách đối chiếu:** Nạp concept sets với cùng bộ lọc annotation của pipeline; đọc anchor/context từ sessions và focus từ ground truth chỉ cho mục đích chẩn đoán; dựng lại nhóm matching trước và sau khi loại `candidate_ids`. Việc đọc ground truth trong phép chẩn đoán không có nghĩa scorer được phép đọc đáp án này.

Trường `actual_pairs = 30000` trong generation report đếm các cặp **session–candidate có nhãn**, không phải 30.000 cặp quan sát.

### 5.1. Vì sao exposure và interaction bằng 0?

Luồng hiện hành trong generator:

```text
Chọn bài mốc, context, focus và hướng intent
                    ↓
Chọn 20 candidates cho phần ranking
                    ↓
Loại candidates khỏi tập bài quan sát
                    ↓
Ghép một bài giống focus với một bài khác focus
trong cùng context và cùng trạng thái các facet còn lại
                    ↓
Có cặp → tạo exposure → sinh interaction
Không có cặp → giữ phiên, không tạo hai loại log này
```

Trong các phiên có bài phía giống focus, bài đó đã nằm trong candidates. Sau khi loại candidates, phía này rỗng và không thể ghép cặp, dù có thể vẫn còn bài phía khác focus.

Ví dụ thực tế: phiên `D00023`, anchor `P003875`, context `method`, focus `task`. Trước khi loại candidates có một cặp matching hợp lệ. Bài cùng context và giống focus duy nhất là `P000035`, nhưng bài này đã nằm trong candidates, nên sau khi loại không còn cặp.

Nguồn logic: [generator D](../../../data/exp_d/build_exp_d.py).

### 5.2. Không đủ hai cặp có phải nguyên nhân không ghi exposure?

Cần tách hai quy tắc:

- **Generator:** Có thể ghi số cặp thực tế, tối đa `observation_pairs`; không bắt buộc phải đủ hai cặp mới ghi exposure.
- **Estimator hiện tại:** Cần ít nhất `min_direction_pairs = 2` và chênh lệch phản ứng đủ lớn mới kết luận hướng từ behavior.

Vì vậy, bộ đang kiểm tra có 0 exposure do **không còn cặp sau lọc**. Nếu một phiên chỉ có một cặp, generator vẫn có thể ghi log nhưng estimator có thể chưa đủ bằng chứng để kết luận.

## 6. Vì sao không dùng lại candidates làm bài quan sát?

Protocol hiện tại muốn kiểm tra khả năng dùng phản ứng trên một nhóm bài để hiểu nhu cầu và xếp hạng **nhóm bài khác**.

Ví dụ: user lưu bài C trong phần quan sát. Nếu C cũng nằm trong candidates, kết quả xếp C cao có thể chịu ảnh hưởng từ việc đã thấy phản ứng trên chính C. Việc tách nhóm giúp đánh giá khả năng chuyển thông tin về intent sang các bài chưa có feedback trong phiên.

Đây là lựa chọn thiết kế của D, không phải yêu cầu bắt buộc cho mọi hệ khuyến nghị. Cho phép trùng là một thiết kế khác và cần định nghĩa lại mục tiêu, cách chấm, protocol và validator tương ứng.

Validator hiện tại kiểm tra giao giữa `exposure.paper_ids` và `candidate_ids` phải rỗng. Nguồn: [kiểm tra D](../../../scripts/validate_experiments.py).

## 7. Có thể dùng LLM để sinh thêm dữ liệu không?

Có thể cân nhắc, nhưng cần phân biệt các cách làm:

| Phương án | Có giải quyết thiếu bài quan sát không? | Phạm vi kết luận |
|---|---|---|
| LLM sinh thêm phản ứng trên bài hiện có | Không tự giải quyết thiếu cặp hợp lệ | Kết quả dưới simulator phản ứng mới |
| Bổ sung bài thật từ nguồn khác và annotation tương ứng | Có thể, cần đo lại số cặp khả thi | Kết quả trên corpus thật đã mở rộng |
| Sinh bài quan sát tổng hợp, facet và phản ứng | Có thể chủ động tạo thêm cặp theo thiết kế | Kết quả dưới điều kiện quan sát tổng hợp |

LLM đã được nghiên cứu như user simulator, chẳng hạn [SimUSER, ACL 2025](https://aclanthology.org/2025.acl-industry.5/). Điều đó hỗ trợ tính khả thi của hướng mô phỏng, không xác nhận rằng một prompt bất kỳ sẽ tạo được hành vi phù hợp với bài toán D.

Một phương án thử nghiệm là giữ bài mốc và candidates thật, chỉ bổ sung bài quan sát tổng hợp:

```text
Bài mốc thật
    ↓
Bài quan sát tổng hợp + phản ứng mô phỏng
    ↓
Suy intent
    ↓
Xếp hạng candidates thật
```

Phép thử này trả lời được câu hỏi: **“Với bằng chứng mô phỏng được kiểm soát, phương pháp có suy intent và cải thiện ranking không?”** Nó chưa tự chứng minh hiệu quả khi người thật tương tác với bài thật.

Nếu cặp tổng hợp luôn khác nhau rất rõ ở đúng focus và phản ứng gần như luôn khớp intent, phép thử có thể trở nên dễ hơn dữ liệu thực. Nghiên cứu về user simulator bằng LLM đã ghi nhận các sai lệch so với người dùng thật: [Yoon và cộng sự, NAACL 2024](https://aclanthology.org/2024.naacl-long.83/).

## 8. Ngẫu nhiên và nhiễu cần được thiết kế thế nào?

### 8.1. Ngẫu nhiên có điều kiện theo intent

Nếu user mô phỏng muốn phương pháp khác bài mốc, phản ứng tích cực với bài khác phương pháp nên có xu hướng cao hơn, nhưng không phải lúc nào cũng cao hơn. User vẫn có thể xem lướt, thích cả hai bài hoặc phản ứng trái với nhu cầu đã đặt.

Nếu loại interaction được chọn hoàn toàn độc lập với nội dung và intent, phản ứng không mang tín hiệu về intent. Khi đó, nhánh behavior không có cơ sở để suy hướng tốt hơn.

Exposure cũng cần được lấy mẫu trong các ràng buộc của câu hỏi nghiên cứu. Xáo ngẫu nhiên một số bài bất kỳ không tự tạo được cặp cùng context và tương đương ở các facet phụ.

### 8.2. D đã có cơ chế phản ứng kèm nhiễu

Generator hiện tại tính:

```text
utility = (0,7 nếu bài thỏa intent; 0,05 nếu không)
          + nhiễu Gaussian có trung bình 0 và độ lệch chuẩn noise_std
```

Cấu hình hiện hành dùng `noise_std = 0.2`, rồi ánh xạ utility qua thresholds thành dislike/view/click/save/like. Đây là tham số simulator, không phải xác suất hoặc tham số được ước lượng từ hành vi người thật.

Nguồn: [khối sinh phản ứng D](../../../data/exp_d/build_exp_d.py).

### 8.3. Điều cần kiểm chứng khi dùng simulator mới

- Giữ quan hệ có ý nghĩa giữa intent, nội dung bài và phân bố phản ứng.
- Chốt cách sinh trước khi đánh giá; mọi phương pháp được so sánh trên cùng dataset, candidates và cutoff.
- Thử nhiều seed và mức nhiễu; xem mức cải thiện có ổn định hay chỉ xuất hiện ở một cấu hình thuận lợi.
- Cho simulator biết intent ẩn để đóng vai user là hợp lệ trong mô phỏng; không đưa các trường ground truth trực tiếp cho estimator hoặc ranker. Query clear vẫn có thể diễn đạt nhu cầu theo thiết kế của protocol.
- Không diễn giải nhiều dòng interaction mô phỏng thành nhiều người dùng thật hoặc nhiều nội dung độc lập.

LLM không bắt buộc nếu chỉ cần sinh các loại click/save theo phân bố xác suất. Generator bằng quy tắc hiện có dễ kiểm soát hơn cho bước khảo sát ban đầu. LLM có thể được cân nhắc khi cần phản hồi ngôn ngữ tự nhiên hoặc hành vi phong phú hơn và có cách đánh giá simulator tương ứng.

Rò rỉ thông tin trong lịch sử hoặc phản hồi của simulator cũng có thể làm tăng giả tạo kết quả; vấn đề này đã được phân tích trong [How Reliable is Your Simulator?, 2024](https://arxiv.org/abs/2403.16416).

## 9. Thêm bài vào papers.jsonl rồi chạy lại D có đủ không?

**Chưa đủ trong pipeline hiện tại.** D tạo thiết kế phiên từ concept sets của A, không tự trích facet cho các bài mới được thêm vào corpus.

Luồng phụ thuộc là:

```text
papers.jsonl: ID, title, abstract và metadata nguồn
    ↓
Annotation A: facets_silver + annotation_metadata + manifest
    ↓
Lọc annotation theo cờ chất lượng
    ↓
Generator D + handoff C hợp lệ
    ↓
Dataset D mới → validate → chạy baseline
```

Các điểm cần xử lý nếu chọn hướng này:

1. **Nguồn gốc bài:** Phân biệt bài thật bổ sung và bài tổng hợp. Bài do LLM tạo cần được nhận diện là synthetic; không gắn provenance của corpus thật cho chúng.
2. **Facet:** Bài mới cần facet dùng được và nhất quán với nội dung. Chỉ thêm ID hoặc title/abstract chưa làm D nhận được bài đó trong tập concept sets.
3. **Provenance A:** Loader kiểm tra annotation, độ phủ, hashes và manifest. Sửa corpus có thể làm các đầu ra A hiện có không còn khớp đầu vào. Đường nạp A hiện còn yêu cầu dataset/annotation thuộc loại `real`, nên bài tổng hợp cần một thiết kế nguồn dữ liệu riêng hoặc điều chỉnh contract phù hợp.
4. **Handoff C:** Loader kiểm tra hashes đầu vào và đầu ra của C, đồng thời yêu cầu C và D dùng cùng đường dẫn corpus/facets. Sửa corpus gốc khiến handoff C cũ không còn vượt qua nguyên trạng các kiểm tra đó.
5. **Vai trò bài mới:** Generator hiện chọn anchors và candidates từ tập facets chung. Nếu chỉ thêm bài tổng hợp vào tập chung, chúng có thể trở thành anchor hoặc candidate, không chỉ là observation. Muốn giữ bài giả chỉ ở phần quan sát thì cần quy tắc phân vai rõ ràng.

Nguồn: [loader annotation A](../../../scripts/experiment_io.py), [kiểm tra handoff C](../../../scripts/experiment_io.py).

Về nguyên tắc nghiên cứu, các thực nghiệm độc lập không bắt buộc dùng cùng corpus. Tuy nhiên, C và D trong repository đang có quan hệ handoff và ràng buộc nguồn dữ liệu cụ thể. Muốn tách corpus cần thiết kế cách nối profile, ID, facet và provenance tương ứng.

### 9.1. Có cần sửa generator C không?

Chưa có lý do bắt buộc thay logic sinh sở thích/lịch sử của C chỉ để bổ sung bằng chứng trong D. Tuy nhiên:

- Nếu mở rộng corpus chung theo contract hiện hành, cần tạo lại hoặc thiết kế lại handoff/provenance của các bước phụ thuộc cho phù hợp; không thể mặc định C cũ vẫn dùng nguyên trạng.
- Nếu D nạp một tập observation bổ sung riêng, có thể giữ lịch sử C cũ về mặt thiết kế, nhưng phải điều chỉnh luồng nạp và validation để biểu diễn đúng hai nguồn dữ liệu.

Đây là lựa chọn thiết kế chưa được triển khai trong cuộc trao đổi này.

## 10. Hướng thử nghiệm đề xuất

Mục tiêu gần nhất nên là xác định liệu nguồn bài quan sát bổ sung có tạo được bằng chứng hữu ích cho D, trước khi sinh hàng loạt dữ liệu hoặc tích hợp LLM vào toàn pipeline.

1. Giữ bộ D cũ làm mốc và tạo một phiên bản thử nghiệm riêng.
2. Giữ anchors/candidates thật nếu muốn tách riêng tác động của observation mới.
3. Thử trên một nhóm phiên nhỏ, chẳng hạn 20–50 phiên; ghi rõ nguồn và vai trò của các bài bổ sung.
4. Kiểm tra số cặp hợp lệ còn lại sau khi tách candidates; kiểm tra mức tối thiểu và matching mà estimator thực sự sử dụng.
5. Sinh phản ứng theo intent có nhiễu bằng quy tắc hiện có trước; chỉ thêm LLM khi cần khả năng simulator mà quy tắc chưa đáp ứng.
6. Validate và chạy lại đầy đủ baseline trên cùng bộ thử nghiệm; phân tích theo query mode và focus.
7. Báo riêng khả năng suy focus. Coverage tổng có thể bao gồm context được cung cấp sẵn, nên không dùng riêng chỉ số đó để kết luận behavior đã hoạt động.
8. Thử độ nhạy với seed/nhiễu. Khi mở rộng đánh giá, tách phần phát triển và đánh giá theo nhóm anchor để hạn chế việc nội dung lặp làm kết quả quá lạc quan.

Tăng số exposure hoặc số positives là thay đổi dữ liệu. Chỉ được quy kết cải thiện cho phương pháp khi baseline và phương pháp được so sánh trên cùng điều kiện; không dùng chênh lệch điểm giữa hai dataset để khẳng định thuật toán tốt hơn.

## 11. Trạng thái thực hiện và nguồn đối chiếu

| Công việc | Trạng thái trong cuộc trao đổi |
|---|---|
| Đọc overview và giải thích các khái niệm | Đã thực hiện |
| Đọc generator/protocol/validator/loader trong repository | Đã thực hiện |
| Dựng lại thống kê ghép cặp trên 1.500 phiên đã xuất | Đã thực hiện, kết quả trình bày ở mục 5 |
| Sinh thêm bài hoặc interaction | Chưa thực hiện |
| Thay đổi corpus, annotation hoặc generator | Chưa thực hiện |
| Chạy lại A, C, D hoặc baseline | Chưa thực hiện |
| Tích hợp LLM simulator | Chưa thực hiện |

Nguồn nội bộ chính:

- [overview.md người dùng cung cấp](overview.md).
- [Protocol thực nghiệm](../../../docs/EXPERIMENT_PROTOCOL.md).
- [README dữ liệu D](../../../data/exp_d/README.md).
- [Manifest bộ D đã xuất](../../../data/exp_d/generated/manifest.json).
- [Estimator direction](../../../scripts/baseline_common.py).

Các kết quả mới của generator được mô tả trong `overview.md` cần được kiểm tra trên output phiên bản tương ứng khi xuất ra. Báo cáo này không dùng thống kê của bộ D đã xuất để xác nhận thay cho phiên bản đó.
