# Đề xuất pilot bổ sung focus problem cho bộ dữ liệu phụ

> **Cập nhật 20/10/2026:** phần sinh và kiểm tra dữ liệu theo hướng này đã được triển khai trong `../build_observation_data.py`, cấu hình `../observation_config.json`; xem [hướng dẫn hiện hành](../README.md). Chỉ làm dữ liệu, chưa chạy phương pháp/ranking mới. Các mục ghi “chưa triển khai” bên dưới mô tả bản đề xuất ngày 19/10 được giữ để truy vết. Code/kết quả cũ và tài liệu tham chiếu khác đã chuyển vào `../backup/20261020_data_reset/`; hai tài liệu Word được người dùng yêu cầu giữ tại chỗ. Nguồn synthetic hiện là bản ghi facet có kiểm soát (mức 1), không phải bài có title/abstract giả.

Ngày viết: 19/10/2026.

**Trạng thái: tài liệu giải thích và đề xuất. Chưa sinh thêm bài, ứng viên, observation, phản ứng hoặc kết quả thực nghiệm theo phương án này.**

## 1. Ý tưởng trong một đoạn

Giữ nguyên corpus và các bộ dữ liệu gốc. Tạo một pilot riêng cho những thiết kế đang thiếu focus `problem`: dùng bài mốc thật, tận dụng ứng viên thật đang có, rồi **sinh ứng viên tổng hợp cho phía còn thiếu**. Tiếp tục tạo các cặp observation tổng hợp và phản ứng mô phỏng để phương pháp suy intent, sau đó xếp hạng tập ứng viên của pilot. Mục đích là kiểm tra cơ chế suy intent và ranking khi có đủ cấu trúc đối lập, chưa phải chứng minh hiệu quả trên người dùng thật.

Điểm mới so với bộ phụ hiện tại là: **cho phép một phần candidates của pilot là tổng hợp**, thay vì chỉ tổng hợp observation và phản ứng.

## 2. Trước hết cần phân biệt hai nhóm bài

Một phiên có hai nhóm bài khác nhau:

| Nhóm | Dùng để làm gì? | Có được xếp hạng để tính kết quả không? |
|---|---|---|
| Bài quan sát — observation | Hiển thị trước để nhận phản ứng, giúp suy người dùng muốn giống hay khác | Không thuộc tập candidates được chấm của phiên |
| Bài ứng viên — candidates | Là những bài phương pháp cần sắp xếp sau khi suy intent | Có |

Luồng xử lý:

```text
Bài mốc A + context được cho sẵn
                ↓
Hiển thị các bài observation → nhận phản ứng mô phỏng
                ↓
Phương pháp suy focus và hướng similar/different
                ↓
Xếp hạng một nhóm candidates khác
                ↓
Đánh giá suy intent và ranking
```

**Sinh thêm observation không tự tạo thêm candidates.** Đây là lý do bộ phụ hiện có observation tổng hợp nhưng vẫn thiếu focus `problem`.

## 3. Vì sao bộ phụ thiếu problem?

Để so sánh hai intent đối lập trên cùng tập ứng viên, với một bài mốc A và một context cố định, cần có cả:

- B: cùng context và cùng problem với A.
- C: cùng context nhưng khác problem với A.

Trong snapshot đã dùng cho bộ phụ, không tổ hợp bài mốc/context nào có đồng thời cả B và C theo quy tắc giao concept hiện tại. Có tổ hợp chỉ có B, có tổ hợp chỉ có C. Không có quy tắc cấm chọn `problem` làm focus.

Ví dụ thực tế đã kiểm tra: bài mốc `P001380`, context = `task`, có `P003553` ở phía cùng problem nhưng không có bài ở phía khác problem trong cùng context theo quy tắc đang dùng.

Các con số 1.536 bài có problem và 25 bài chia sẻ concept problem thuộc **snapshot dùng cho benchmark**, không mặc định mô tả corpus đang được cập nhật. Xem [phân tích và audit chi tiết](problem_focus_analysis.md).

## 4. Pilot sẽ bổ sung đúng phần nào?

Ví dụ dưới đây chỉ minh họa ý tưởng, không phải ba bài đã thu thập hoặc đã được sinh.

Chọn context = `method`, focus = `problem`:

| Vai trò | Method | Problem | Nguồn |
|---|---|---|---|
| A — bài mốc | CNN | Thiếu nhãn huấn luyện | Bài thật |
| B — ứng viên cùng problem | CNN | Thiếu nhãn huấn luyện | Tận dụng bài thật nếu có |
| C — ứng viên khác problem | CNN | Mất cân bằng lớp | Sinh tổng hợp nếu phía này đang thiếu |

Ý nghĩa: người dùng vẫn quan tâm các nghiên cứu dùng CNN, nhưng có thể muốn tiếp tục xem vấn đề thiếu nhãn hoặc chuyển sang vấn đề khác.

Trong ví dụ này, **không cần sinh lại A và B**. Chỉ bổ sung C để có đủ hai phía trong candidates. Nếu dữ liệu chỉ có phía khác problem, làm ngược lại: sinh phía cùng problem.

Pilot tối thiểu có thể thử pool 20 candidates:

| Thành phần | Số lượng dự kiến | Nguồn |
|---|---:|---|
| Cùng context, cùng problem | 1 | Bài thật hoặc phía tổng hợp còn thiếu |
| Cùng context, khác problem | 1 | Bài thật hoặc phía tổng hợp còn thiếu |
| Ngoài context, có đủ facet cần xét | 18 | Ưu tiên bài thật, cần kiểm tính khả thi |

Đây là **thiết kế đề xuất**, chưa phải pool đã được tạo. Chỉ giữ thiết kế đáp ứng đủ các điều kiện; không tự coi bài thiếu nhãn problem là bài khác problem.

## 5. Sau khi có candidates, observation được tạo thế nào?

Tạo một nhóm observation riêng, chẳng hạn 4 cặp/phiên theo cấu hình bộ phụ trước đây:

- Mỗi cặp có một phía cùng problem và một phía khác problem so với A.
- Hai phía cùng context; trạng thái overlap/thiếu dữ liệu ở các facet ngoài focus phải đáp ứng matching của protocol.
- Observation không trùng bài mốc hoặc candidates của phiên.
- Simulator đặt intent trước, rồi sinh phản ứng có nhiễu theo intent đó.

Nếu intent là “tìm problem khác”, phía khác problem có xu hướng nhận phản ứng tích cực hơn, nhưng vẫn có thể có phản ứng trái hướng do nhiễu. Phương pháp chỉ thấy dữ liệu công khai và phản ứng; không được đọc intent thật hoặc nhãn đáp án.

**Không lấy chính B/C trong candidates làm observation.** Làm vậy sẽ đổi câu hỏi đánh giá sang xếp hạng bài đã có phản ứng trực tiếp, trong khi protocol hiện tại kiểm tra chuyển thông tin intent sang nhóm bài khác.

Bốn cặp với bốn lần lấy nhiễu không mặc nhiên tương đương bốn nội dung độc lập. Nếu các mô tả/facet lặp lại thì phải ghi nhận mức lặp đó.

## 6. Tại sao cần hai intent trên cùng pool?

Giữ nguyên A, context và 20 candidates, tạo hai phiên đối lập:

| Phiên | Intent thật | Bài phù hợp hơn trong ví dụ |
|---|---|---|
| Phiên similar | Tìm cùng problem với A | B |
| Phiên different | Tìm problem khác A nhưng giữ context | C |

Nếu phương pháp suy được intent và sử dụng hướng đó để ranking, nó cần thay đổi ưu tiên giữa B và C theo phiên.

Query và phản ứng được tạo tương ứng với từng intent. Trong mỗi cặp so sánh, giữ cùng user/profile C, cutoff, bài mốc và pool; không thay candidates chỉ để làm một phương pháp đạt điểm cao hơn.

Nhãn vẫn theo quy tắc hiện hành: đúng context và đúng hướng focus → grade 2; đúng context nhưng sai hướng → grade 1; ngoài context hoặc thiếu facet cần xét → grade 0.

## 7. Có đụng corpus gốc không?

**Không cần thay đổi corpus gốc nếu triển khai thành phần bổ sung riêng.**

| Thành phần | Cách xử lý dự kiến |
|---|---|
| `data/processed/papers.jsonl` | Giữ nguyên |
| Annotation A gốc | Giữ nguyên; không chèn bài tổng hợp và gọi là A silver thật |
| Lịch sử/profile và handoff C gốc | Giữ nguyên |
| Sessions, candidates và nhãn D gốc | Giữ nguyên |
| Bộ phụ 90 phiên đã có | Giữ nguyên để đối chiếu |
| Candidates/observation mới | Nạp thêm trong pilot riêng, ID và vai trò rõ ràng |
| Dự đoán/kết quả pilot | Đánh giá riêng, có nhận diện nguồn tổng hợp |

“Giữ nguyên corpus” không có nghĩa chương trình hiện tại tự chạy được phương án này. Cần bổ sung cách nạp và kiểm tra **synthetic candidates**, vì hỗ trợ observation tổng hợp trước đây chưa đồng nghĩa hỗ trợ candidates tổng hợp.

Khi chạy pilot, chương trình cần thấy facets của các bài thật và các bản ghi tổng hợp liên quan. Nhưng tập candidates phải được chỉ định rõ, không đưa mọi bản ghi tổng hợp vào một kho chung rồi để chúng vô tình trở thành anchor/candidate/observation sai vai trò. Validator cần phân biệt đúng các vai trò này; không bỏ kiểm tra matching, thời gian hoặc tách observation–candidates.

## 8. “Sinh bài tổng hợp” cần hiểu ở mức nào?

Có hai mức, cần chọn và công bố trước khi chạy:

1. **Bản ghi facet có kiểm soát:** tạo một đối tượng tổng hợp với các concept cần thiết để kiểm cơ chế. Không gọi đây là bài báo thật hoặc bằng chứng rằng nội dung nghiên cứu đó tồn tại.
2. **Mô tả bài tổng hợp có nội dung:** tạo title/abstract và facets nhất quán, rồi review tính hợp lý của tổ hợp context/problem. Không tự tạo DOI, nguồn xuất bản hoặc kết quả nghiên cứu rồi trình bày như thật.

Nếu chỉ kiểm cơ chế trên concept, mức 1 có thể phù hợp và không bắt buộc dùng LLM. Nếu muốn mô phỏng bài có nội dung để đọc/đánh giá, mức 2 cần bước kiểm chất lượng nội dung. Chỉ ghép một problem từ bài này với method từ bài khác chưa bảo đảm mô tả mới hợp lý.

Dù chọn mức nào, phải có cờ synthetic và nguồn gốc xây dựng. Không sao chép một bản ghi thành nhiều ID rồi tính thành nhiều nội dung độc lập.

## 9. Pilot kiểm tra được gì và chưa kiểm tra được gì?

**Có thể kiểm tra:**

- Phương pháp có suy được focus/hướng problem khi có observation mang tín hiệu không?
- Khi giữ cùng candidate pool, dùng hướng dự đoán có tốt hơn luôn-similar không?
- Kết quả thay đổi thế nào khi tăng nhiễu hoặc bỏ/xáo phản ứng?
- Cơ chế có hoạt động trên đủ 5 focus trong các điều kiện đã thiết kế không?

**Chưa thể tự kết luận:**

- Người dùng thật sẽ phản ứng theo cùng phân bố.
- Phương pháp khuyến nghị bài thật tốt hơn trên một corpus mới.
- Có thêm phiên/seed nghĩa là có thêm người dùng hoặc nội dung độc lập.
- Điểm cao trên candidates tổng hợp tương đương điểm cao trên candidates thật.

Đặc biệt, nếu dữ liệu được dựng đúng theo quy tắc overlap mà phương pháp cũng dùng để ưu tiên ranking, điểm gần hoàn hảo có thể chủ yếu xác nhận tính nhất quán của cơ chế. Cần báo điều này cùng kết quả, không dùng điểm đó làm bằng chứng độc lập cho relevance ngữ nghĩa.

## 10. Cách đánh giá đề xuất

1. **Audit trước khi sinh:** chọn thiết kế problem thiếu đúng một phía, kiểm đủ bài ngoài context và tính độc lập của bài mốc/công trình.
2. **Chốt thiết kế trước khi tính điểm:** quy tắc sinh candidates, matching, số cặp, seed, nhiễu và tiêu chí kiểm chất lượng.
3. **Sinh intent trước query/phản ứng/nhãn:** giữ đáp án và provenance ẩn khỏi estimator/ranker.
4. **So trên cùng dữ liệu:** baseline và phương pháp đề xuất cùng dùng pool, phản ứng và cutoff của từng điều kiện.
5. **Có đối chứng:** luôn-similar, hướng dự đoán, hướng đảo; không observation hoặc xáo phản ứng. Khi báo ranking của một đối chứng phải thực sự chạy ranking trong điều kiện đó.
6. **Báo hai loại kết quả:** khả năng suy focus/hướng và chất lượng ranking. Suy intent tốt hơn chưa bảo đảm ranking tốt hơn.
7. **Kiểm độ nhạy:** có thể giữ ba seed 42/43/44 và hai mức noise 0,2/0,5 để thuận đối chiếu; đây là cấu hình đề xuất, không phải kết quả đã có.
8. **Báo đúng số đơn vị:** số bài mốc, thiết kế, nội dung tổng hợp và phiên. Gom các biến thể của cùng bài mốc/công trình khi chia tập hoặc ước lượng độ bất định.

Ví dụ về quy mô: nếu chọn được 4 thiết kế problem, mỗi thiết kế có 2 hướng × 3 query mode thì có 24 phiên. Đây chỉ là ví dụ tính số lượng; 24 phiên đó vẫn xuất phát từ 4 thiết kế, chưa phải 24 bài mốc độc lập. Chưa có cam kết hiện tại chọn được đúng 4 thiết kế.

## 11. Có hợp lý để đưa vào bài báo không?

**Có thể đưa vào như thực nghiệm bổ sung mô phỏng có kiểm soát**, với câu hỏi: khi thiếu cấu trúc đối lập được bổ sung có chủ đích, cơ chế suy intent và sử dụng intent để ranking có hoạt động không?

Cần báo tách:

- Kết quả trên bộ phụ hiện có với candidates thật.
- Kết quả pilot problem có một phần candidates tổng hợp.
- Nếu tổng hợp kết quả đủ 5 focus, phải kèm phân tích theo focus và nguồn candidates để người đọc thấy các điều kiện khác nhau.

Không chỉ thêm các phiên problem tổng hợp vào 90 phiên cũ rồi tiếp tục mô tả toàn bộ candidates là bài thật. Chênh lệch điểm giữa hai bộ còn chịu ảnh hưởng từ thành phần pool và mức dễ của dữ liệu.

Đoạn diễn đạt dự kiến, chỉ dùng sau khi thực sự triển khai và kiểm tra:

> Chúng tôi xây dựng một pilot riêng để khảo sát focus problem khi corpus hiện có thiếu tập ứng viên đối lập trong cùng context. Pilot giữ nguyên corpus nguồn, sử dụng bài mốc thật và bổ sung ứng viên tổng hợp ở phía còn thiếu, cùng observation và phản ứng mô phỏng có kiểm soát. Các phương pháp được so sánh trên cùng candidate pool. Thực nghiệm này kiểm tra cơ chế sử dụng intent trong điều kiện tổng hợp, chưa xác nhận hiệu quả trên hành vi người dùng thật.

Việc có pilot hợp lý không tự bảo đảm bài được chấp nhận; sức mạnh kết luận còn phụ thuộc đóng góp phương pháp, chất lượng dữ liệu và các thực nghiệm còn lại.

## 12. Phạm vi công việc hiện tại

Hiện mới viết tài liệu này theo yêu cầu. Phương án sinh dữ liệu và thay đổi chương trình chưa được triển khai. Trước khi tạo thêm file hoặc triển khai, cần báo rõ các file dự kiến và mục đích cho người thực hiện.

Nguồn đối chiếu nội bộ:

- [Báo cáo exposure/interaction cũ và cập nhật pilot](old/bao_cao_exposure_interaction_D.md).
- [Phân tích nguyên nhân thiếu problem và số liệu snapshot](../backup/20261020_data_reset/docs/problem_focus_analysis.md).
- [Báo cáo bộ phụ nhiều ứng viên cũ](../backup/20261020_data_reset/docs/multicandidate_report.md).
- [Generator thiết kế candidates thật cũ](../backup/20261020_data_reset/build_contrast_sessions.py).
- [Pilot observation tổng hợp cũ](../backup/20261020_data_reset/run_synthetic_observation_pilot.py).
