# Bước 2 — Các phương án cần ra quyết định

Ngày cập nhật: 2026-10-15. Chỉ ghi trong `data/exp_d/`; môi trường chạy là workspace riêng. Tài liệu này để xem xét thiết kế, chưa triển khai phương án mới.

**Trạng thái hiện tại: CHƯA CHỌN PHƯƠNG ÁN.** Bạn đã hủy lựa chọn A để cân nhắc lại A/B/C/D. Chưa có phương án nào được triển khai; không mặc định tiếp tục bổ sung dữ liệu.

## 1. Vấn đề thực tế cần giải quyết

D suy hướng từ phản ứng bằng cách so hai bài: một bài giống anchor ở focus, một bài khác ở focus. Cả hai phải giữ context liên quan và có trạng thái overlap/missing tương đương ở các facet còn lại. Các bài quan sát phải khác candidate pool cuối phiên. Estimator hiện yêu cầu ít nhất hai cặp hợp lệ.

Kết quả [chẩn đoán](../audit/step2_pair_diagnosis.json):

| Phạm vi kiểm tra | Kết quả |
|---|---|
| Corpus hiện có | 4.210 bài, 3.240 bài vượt bộ lọc chất lượng A |
| 1.500 phiên trước khi loại candidates | 1.470 phiên có 0 cặp, 30 phiên có 1 cặp |
| 1.500 phiên sau khi loại candidates | Tất cả 0 cặp |
| Toàn bộ 32.218 tổ hợp anchor/context/focus hợp lệ | 32.214 tổ hợp có 0 cặp; 4 tổ hợp có 1 cặp |
| Số cặp tối đa trên một tổ hợp, trước khi loại candidates | 1; không đủ yêu cầu 2 |

Vì vậy, chỉ chạy lại generator hoặc lấy cặp trước candidates không đủ để đạt yêu cầu hiện tại. Kết luận này áp dụng cho corpus và bộ lọc/matching đang dùng, không khẳng định mọi corpus đều thiếu cặp.

Đây là vấn đề khác với LF/CRLF: bước 1 đã pass trong workspace; không cần xử lý lại lỗi đó để xem xét bước 2.

## 2. Các hướng chính

| Phương án | Thay đổi gì? | Ưu điểm | Chi phí / giới hạn | Giữ nguyên protocol hiện tại? |
|---|---|---|---|---|
| **A. Bổ sung bài thật có đủ cặp** | Thêm bài có title/abstract và facet hợp lệ, tìm các cụm thỏa matching hiện tại | Giữ ý nghĩa đối chứng behavior và quy tắc nhãn | Cần thu thập, extraction/kiểm tra chất lượng và handoff mới; thêm nhiều bài chưa đảm bảo đủ cặp | Có thể giữ quy tắc, nhưng phải version lại dataset và provenance |
| **B. Matching theo ngữ nghĩa** | Đổi cách quyết định “giống” từ giao concept nguyên văn sang khái niệm chuẩn hóa hoặc độ tương đồng ngữ nghĩa | Có thể tận dụng corpus hiện có, giảm phụ thuộc câu chữ | Cần chốt mô hình/ontology, ngưỡng và nhãn; có nguy cơ scorer và generator dùng cùng tiêu chí tạo bias | Không; cần protocol D phiên bản mới |
| **C. Nới thiết kế cặp hoặc ngưỡng** | Chẳng hạn yêu cầu 1 cặp, hoặc giảm điều kiện matching các facet còn lại | Có thể tạo pilot cơ chế nhanh hơn | Một cặp hiện chỉ xuất hiện ở 4 tổ hợp, rất hẹp; nới matching có thể gây nhiễu giữa các facet | Không; là ablation hoặc thiết kế mới |
| **D. Pilot search-only trước** | Giữ dữ liệu quan sát hiện có, chỉ nghiên cứu đóng góp query/search; behavior có thể unknown | Có thể chạy scorer hiện có mà chưa bổ sung cặp | Không trả lời đầy đủ câu hỏi suy hướng từ phản ứng; cần ghi rõ giới hạn phạm vi | Không cần đổi scorer hiện có, nhưng thu hẹp mục tiêu đánh giá |

Không có bảo đảm phương án B/C sẽ tạo được benchmark tốt trước khi thử nghiệm. Phương án D là việc có thể làm trước, không thay thế nhánh behavior.

## 3. Các quyết định cần chốt theo từng phương án

### Phương án A — Chỉ áp dụng nếu bạn chọn bổ sung dữ liệu

#### A1. Lấy dữ liệu bổ sung ở đâu?

- **Bài thật mới cùng chủ đề với anchors:** tìm cụm bài có cùng context và gồm cả same-focus/different-focus; lựa chọn nguồn cụ thể chưa chốt. Thu thập có mục tiêu phù hợp hơn chỉ tăng số lượng ngẫu nhiên.
- **Review lại các bản A đang bị loại:** chỉ là nguồn ứng viên cần kiểm tra lại, không tự bỏ cờ hoặc đưa cả 970 bản vào. Phải sửa annotation theo evidence và xác minh chất lượng; chưa biết có tạo đủ cặp không.
- **Nguồn raw đang có:** báo cáo corpus cho thấy các bản CSFCube hiện có đã được đưa vào quá trình tạo corpus; phần lớn SciFact ngoài corpus bị loại theo phạm vi IT. Chưa có sẵn một bộ bổ sung vừa đúng phạm vi vừa có năm facet hợp lệ để chỉ việc nối vào D. Không tự lấy các bài bị loại về lĩnh vực để bù số lượng.

**Cần bạn quyết định:** ưu tiên thu thập bài mới có mục tiêu hay phối hợp review annotation bị loại. Không tự kết luận rằng tăng corpus sẽ giải quyết được matching.

#### A2. Ai làm extraction và xác nhận đầu vào?

Bài mới cần facet/evidence theo schema hiện hành, metadata chất lượng và manifest hợp lệ. Không được gán concept thủ công chỉ để tạo đúng cặp mong muốn rồi xem như silver độc lập.

Hai cách tổ chức:

1. Nhận handoff bổ sung từ người phụ trách corpus/A; nhóm thống nhất ID, schema và phiên bản trước khi đưa vào D.
2. Thử nghiệm trong workspace riêng bên trong D, giữ nguồn chung nguyên vẹn; vẫn phải chốt nguồn bài và quy trình extraction/kiểm tra. Việc sửa bản sao A/C chỉ hợp lệ nếu được ghi nhận như phiên bản dataset riêng, không gọi đó là handoff gốc giữ nguyên.

**Cần bạn/nhóm quyết định:** ai cung cấp facet đạt chất lượng, có dùng pipeline/model A hiện hành không, và dataset thử nghiệm riêng D có được chấp nhận để báo cáo không. Chưa tự chạy GPU, tải model hoặc extraction mới.

#### A3. Chọn quy mô và độ phủ pilot

Chốt trước khi tạo pilot:

- Các context/focus và nhóm similar/different nào cần có mặt? Pilot kỹ thuật có thể hẹp, nhưng phải báo phạm vi hẹp đó.
- Giữ ít nhất hai cặp quan sát hợp lệ mỗi phiên dùng để kiểm tra behavior; cần thêm candidates riêng biệt và giữ chính sách nhãn hiện tại.
- Cần bao nhiêu anchors/cụm bài độc lập? Lặp cùng vài bài cho nhiều user không tạo thêm bằng chứng nội dung độc lập.
- Có yêu cầu cân bằng query clear/ambiguous/none không? Đánh giá cuối phải nêu số phiên từng nhóm.

**Đề xuất kỹ thuật:** thử một cụm nhỏ có đủ cặp và candidates trước, kiểm tra khả thi rồi mới tăng quy mô. Chưa chốt con số hoặc coi pilot nhỏ là benchmark chính.

#### A4. Handoff và tái lập sau khi thêm dữ liệu

Generator hiện buộc corpus canonical và kiểm tra A/C bằng hashes. Thêm corpus/facet làm hash thay đổi, nên không thể chỉ nối bài vào `sessions.jsonl` hoặc sửa mỗi manifest D.

Trong workspace riêng cần:

1. Dataset corpus/A phiên bản mới với ID ổn định, metadata và provenance hợp lệ.
2. Handoff C tương ứng theo các validator hiện hành; nếu phải tạo lại C, ghi rõ và giữ C cũ để đối chiếu.
3. Sinh D mới vào output/truth riêng; giữ nguyên phiên bản D hiện có.
4. Chạy mọi đối chứng trên cùng D mới. Kiểm tra tối thiểu trước chạy vẫn cần; audit mở rộng có thể làm sau như yêu cầu.

Đây là việc quản lý phiên bản dữ liệu, không phải tự sửa hash để vượt kiểm tra. Không cần sửa file nguồn ngoài D để làm thử nghiệm riêng, nhưng việc đưa phiên bản mới vào nghiên cứu chung cần nhóm thống nhất.

### Phương án B — Nếu chọn matching theo ngữ nghĩa

Cần chốt:

- Dùng chuẩn hóa concept về nhãn chung hay similarity từ encoder? Hai cách này có chi phí và giả định khác nhau.
- Thay matching chỉ để tìm cặp quan sát hay thay cả quy tắc tạo relevance labels? Hai phạm vi phải được ghi rõ, không tự coi tương đương.
- Ngưỡng giống/khác và quy tắc facet thiếu là gì? Dùng dữ liệu nào để chọn ngưỡng, tránh tune trên đánh giá cuối?
- Kiểm chứng chất lượng cặp bằng cách nào, và tránh để cùng một scorer vừa tạo nhãn vừa tự được chấm bằng nhãn đó ra sao?

Có thể tận dụng bài hiện có nhưng chưa bảo đảm đủ cặp. Phải ghi protocol/config D phiên bản mới và dùng cùng phiên bản cho mọi đối chứng. Không tự chọn encoder hoặc tải model trước khi chốt phạm vi.

### Phương án C — Nếu chọn nới điều kiện hoặc ngưỡng

Cần chốt:

- Nới điều kiện nào: số cặp tối thiểu, matching các facet không phải focus, hay tiêu chí context?
- Nhiễu có thể tăng như thế nào? Có còn tách được tác dụng của focus khỏi những facet khác không?
- Đây là pilot cơ chế, ablation, hay protocol chính mới? Không trình bày như giữ nguyên protocol cũ.

Chỉ hạ ngưỡng từ hai xuống một cặp chưa đủ tạo benchmark đa dạng: corpus hiện chỉ có bốn tổ hợp có một cặp trước khi loại candidates. Không nhân đôi cùng cặp để giả thành hai bằng chứng độc lập.

### Phương án D — Nếu chọn pilot search-only trước

Cần chốt:

- Mục tiêu tạm thời là kiểm tra pipeline/ranking hay nghiên cứu query parser?
- Báo cáo nhóm clear/ambiguous/none như thế nào, và ghi unknown do thiếu hành vi ra sao?
- Nhánh behavior sẽ được bổ sung bằng hướng nào sau pilot? Chạy search-only không hoàn thành toàn bộ mục tiêu D ban đầu.

Có thể dùng runner/dataset hiện có trong workspace mà chưa sinh thêm phản ứng. Oracle vẫn chỉ evaluator được dùng. Nếu chỉ chạy đối chứng hiện tại thì chưa phải phương pháp nghiên cứu mới.

## 4. Quyết định nào bạn cần tự chốt, việc nào công cụ tự làm?

| Cần bạn/nhóm chốt | Công cụ tự xử lý khi hướng đã rõ |
|---|---|
| Giữ quy tắc hiện tại hay đổi matching/nhãn/phạm vi? | Thống kê pool, phân bố và điều kiện còn thiếu |
| Nguồn dữ liệu và ai chịu trách nhiệm facet/evidence bổ sung? | Viết script chuẩn bị config, sampling và báo cáo trong D |
| Phạm vi pilot/đánh giá cuối và mức chấp nhận dataset riêng? | Giữ nguồn cũ, version output và chạy kiểm tra cần thiết |
| Nếu đổi phương pháp: giả thuyết và phép so cần chứng minh? | Triển khai, chạy đối chứng, tổng hợp metrics và case lỗi |

Không yêu cầu bạn tự làm checklist đọc tài liệu hoặc audit dài trước khi code. Sẽ báo ngay nếu một thay đổi kỹ thuật kéo theo đổi câu hỏi nghiên cứu hoặc ý nghĩa nhãn.

## 5. Chọn lại phương án

**Không có phương án được chọn sẵn.** Đánh dấu một hướng chính sau khi bạn quyết định:

- [ ] A — Giữ quy tắc hiện tại, bổ sung dữ liệu/facet hợp lệ.
- [ ] B — Thiết kế matching theo ngữ nghĩa trên corpus hiện có.
- [ ] C — Nới điều kiện/ngưỡng và đánh giá như thiết kế mới hoặc ablation.
- [ ] D — Chạy pilot search-only trước, ghi rõ phần behavior chưa được giải quyết.

Có thể chọn D làm bước tạm thời rồi A/B/C làm hướng chính, nhưng cần nói rõ thứ tự và mục tiêu. Chưa tự ghép các phương án thay bạn.

Sau khi chọn hướng mới:

1. Chốt các quyết định thiết kế tương ứng trong mục 3; việc kỹ thuật thường lệ công cụ sẽ tự xử lý.
2. Ghi phương án vào `step.md` và `progress.md`.
3. Triển khai trong D, giữ dữ liệu cũ và ghi phiên bản mới nếu thay protocol/data.
4. Tạo/chạy pilot và kiểm tra kết quả; audit mở rộng để sau theo yêu cầu.

Đã hoàn thành chẩn đoán, chưa sửa generator, hạ ngưỡng, thay nhãn, bổ sung bài hoặc tạo pilot mới. Việc hủy A không cần rollback code/data vì A chưa được triển khai. Xem [step.md](step.md), [progress.md](progress.md), [changed.md](changed.md).
