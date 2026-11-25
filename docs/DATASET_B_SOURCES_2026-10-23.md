# Nguồn dữ liệu B và phần ranking của D

Ngày tra cứu: 2026-10-23. Chỉ xác minh trang nguồn và nội dung file qua web; chưa tải toàn bộ dataset. Không thay đổi quyết định hay config thực nghiệm hiện có.

## CSFCube

- [Repo chính thức](https://github.com/iesl/CSFCube), [releases](https://github.com/iesl/CSFCube/releases).
- [File query CSV đã đọc](https://raw.githubusercontent.com/iesl/CSFCube/master/queries-release.csv): 50 dòng query–facet; một paper ID có thể xuất hiện nhiều facet. Không diễn giải thành 50 bài độc lập.
- [README/schema](https://raw.githubusercontent.com/iesl/CSFCube/master/README.md): title/abstract ở `abstracts-csfcube-preds.jsonl`; relevance/pool ở `test-pid2anns-csfcube-{background,method,result}.json`; có evaluator và split. CC BY-NC 4.0.
- Đề xuất: benchmark ngoài cho B, kiểm tra facet-conditioned ranking cho D. Không có user history, session hoặc nhãn different.
- Không tự ánh xạ ba facet gốc thành năm facet nhóm. Nếu giữ phạm vi cũ không dùng CSFCube, chỉ coi đây là lựa chọn bổ sung chưa được chấp thuận triển khai.

## DORIS-MAE v1

- [Zenodo có file tải công khai](https://zenodo.org/records/8299749), [repo tác giả](https://github.com/kwang927/Doris-Mae-Dataset).
- File chính `DORIS-MAE_dataset_v1.json` khoảng 1.1 GB; embedding pickle riêng khoảng 1.3 GB, không bắt buộc dùng lại embeddings.
- Zenodo ghi 100 query nhiều điều kiện, pool 99–138 abstracts/query; 363,133 abstracts. Relevance chủ yếu ChatGPT; tập 250 cặp có nhãn ba người. [README](https://raw.githubusercontent.com/kwang927/Doris-Mae-Dataset/main/README.md) cũ ghi 50 query, nên dùng phiên bản phát hành và đếm file khi nhập dữ liệu. Dataset CC-BY-NC theo repo.
- Đề xuất: B dạng query–paper và D có intent được phát biểu. Không có chuỗi tương tác thật; không đánh giá được suy intent từ hành vi hoặc chính xác trọng số profile.

## SciDocs / SciRepEval — dự phòng

- [SciDocs](https://github.com/allenai/scidocs) có co-view/co-read và recomm tasks; các cặp từ hoạt động không mặc định là log phiên công khai.
- [SciRepEval](https://github.com/allenai/scirepeval) là hướng thay thế được AI2 khuyến nghị; metadata và labelled tests trên [HF](https://huggingface.co/datasets/allenai/scirepeval) và [HF test](https://huggingface.co/datasets/allenai/scirepeval_test). Chưa kiểm tra schema từng config trong lần này, không xếp vào lựa chọn đầu cho C/D.

## Điều chỉnh protocol được đề xuất, chưa triển khai

Giữ corpus và năm facet nội bộ để đánh giá riêng. Benchmark ngoài chạy theo định nghĩa gốc, dùng facet system của nhóm làm biểu diễn nếu phù hợp nhưng giữ nguyên ý nghĩa labels. Nếu chỉ lấy giao với corpus hiện tại, phải tính lại số query/pool/positive và công bố coverage. Không gộp nhãn từ các nguồn thành một thang relevance chung khi chưa định nghĩa phép chuyển đổi.
