# Dữ liệu mới cho D — QUAN SÁT v1

Phần này được tách vào `data/exp_d/proposal/`. Bộ gốc ở `../generated`, `../ground_truth`, `../samples` và `../build_exp_d.py` đã được khôi phục, không bị phần mới ghi đè.

## Phân biệt hai thư mục

- `inputs/base_v1/`: snapshot đã kiểm của corpus/facet A và lịch sử C công khai. Đây là nguồn để dựng dataset, không phải code gốc D. Không xuất hidden profiles/future logs C.
- `datasets/observation_v1/`: dataset mới để chuẩn bị thực nghiệm. Có catalog facet, sessions/query, observation/reactions, nhãn ẩn và manifest. Không dùng runner canonical gốc nạp trực tiếp dataset có synthetic candidates.

**Chốt nơi chạy thực nghiệm: `data/exp_d/proposal/datasets/observation_v1/`.** `inputs` là nguyên liệu để tạo lại bộ này, không phải bộ đánh giá cuối. Phần `datasets` không phải dữ liệu cào ngoài corpus.

Nguồn bài từng tìm thêm ở ngoài corpus đã nằm trong `../backup/20261020_data_reset/real_extension_20261020/`, không được nạp vào source bundle hoặc dataset đang dùng. Đã đối chiếu 4.210 bản ghi bài thật trong corpus gốc, inputs và catalog dataset: nội dung bằng nhau. Candidates tổng hợp chỉ là bản ghi facet có nguồn, không phải bài thật cào thêm.

| Dữ liệu cần lấy | Vị trí trong dataset đang dùng |
|---|---|
| Bài thật và facet thật/tổng hợp | `catalog/` |
| Lịch sử C công khai | `history/` |
| Phiên, anchor/context/candidate IDs và query | `generated/` |
| Observation/exposure và phản ứng theo seed/noise | `conditions/*/generated/` |
| Đáp án và provenance ẩn, chỉ evaluator/simulator đọc | `ground_truth/` và `conditions/*/ground_truth/` |

Trạng thái đã chốt: dùng được cho benchmark **facet mock có kiểm soát**, sau các kiểm tra cấu trúc/nguồn/nhãn/thời gian và tách observation–candidate đã qua. Không bắt buộc xác nhận tổ hợp facet là một bài nghiên cứu thực tế trước khi chạy phạm vi mock này. Đã chạy benchmark 7 cấu hình; [kết quả và diễn giải](RESULTS_BENCHMARK.md). Không có human validation.

## Chạy

Chạy từ thư mục `paper-and-conference-recommendation-experiments`:

```powershell
python -B data/exp_d/proposal/prepare_source.py --output data/exp_d/proposal/inputs/base_v2
python -B data/exp_d/proposal/build_observation_data.py --source data/exp_d/proposal/inputs/base_v2 --output data/exp_d/proposal/datasets/observation_v2
python -B data/exp_d/proposal/validate_observation_data.py data/exp_d/proposal/datasets/observation_v2
python -B -m unittest discover -s data/exp_d/proposal -p test_observation_data.py -v
```

Mỗi lần chọn output mới; không ghi đè v1. `--dry-run` của builder chỉ báo quy mô, không ghi file. Mọi output mới phải trong proposal; không ghi ra corpus hoặc D gốc.

## Thiết kế hiện tại

### Nguồn gốc từng thành phần — không phải benchmark D công khai có sẵn

Trong metadata của corpus hiện tại có 4.182 bản ghi nguồn `csfcube` và 28 nguồn `scifact`. D dùng nội dung bài từ corpus này; **không kế thừa nhãn đánh giá chính thức của CSFCube/SciFact làm nhãn intent D**. Facet A là silver tự động, còn users/history/intent/query/reactions/labels trong các bước C/D là mô phỏng của dự án.

| Thành phần | Nguồn và cách tạo | Thật hay mô phỏng? | Quy mô / vai trò |
|---|---|---|---|
| Corpus bài báo | `data/processed/papers.jsonl`, metadata source CSFCube/SciFact | Nội dung bài thật trong corpus dự án | 4.210 bản ghi; không retrieval toàn corpus khi chấm D |
| Facet bài thật | `data/exp_a/generated/facets_silver.jsonl`; prepare_source.py loại fallback/validation errors, chuẩn hóa concept | Silver A tự động, không là nhãn human gold | 3.240 bài hợp lệ cho nguồn facet |
| Danh tính và lịch sử C | `data/exp_c/generated/`; manifest C ghi dataset_kind=mock, build_exp_c.py mô phỏng users/preferences/events | Mô phỏng từ corpus, không phải log người thật | 300 users, prefix 9.000 reactions, 5.373 queries và 9.000 exposures; tính profile C chung |
| Anchor/context/focus/intent | build_observation_data.py chọn thiết kế từ nguồn đã kiểm; hai direction × ba query mode mỗi thiết kế | Anchor thật; thiết kế nhu cầu/phiên là mô phỏng | 12 anchors, 19 thiết kế, 114 phiên |
| Candidates xếp hạng | Lấy bài thật có overlap đúng context; chỉ bù phía focus thiếu bằng bản ghi facet có nguồn | 15 thiết kế toàn thật; 4 mixed/problem, mỗi thiết kế thêm 1 bản ghi facet tổng hợp | 20 candidates/phiên: 1 cùng focus, 1 khác focus, 18 ngoài context; tổng 4 candidate records tổng hợp |
| Observation | Ghép facet từ bài nguồn thành cặp cùng background/context và đối lập focus; tách khỏi candidates | Toàn bộ là bản ghi facet tổng hợp, không có abstract/DOI bịa | 152 profile; 4 cặp/phiên, dùng lại theo thiết kế |
| Query đầu phiên | Generator dùng concept anchor và template; clear nói rõ hướng, ambiguous chỉ nêu context, none không có query | Mô phỏng, không phải câu tìm kiếm người thật | 3 mode, tổng 114 query events |
| Phản ứng D | Utility .7 nếu thỏa intent/.05 nếu không, cộng Gaussian noise rồi lượng tử thành dislike/view/click/save/like | Hoàn toàn mô phỏng theo intent đã đặt trước | Seeds 42/43/44 × noise .2/.5; mỗi condition 456 exposures, 912 reactions |
| Nhãn chấm candidates | Quy tắc concept overlap và intent ẩn: đúng context+hướng=2, đúng context+sai hướng=1, ngoài context/thiếu=0 | Ground truth quy tắc của mock, không phải human relevance | 2.280 nhãn; chỉ evaluator đọc |

**Bộ thực sự được chấm** là `datasets/observation_v1`, không phải 4.210 bài như một test retrieval, cũng không phải bộ D gốc cũ ở `../generated`. Sáu conditions không làm tăng số anchors hoặc thiết kế độc lập. `inputs/base_v1` chỉ là snapshot nguyên liệu để tái tạo bộ trên.

- 19 thiết kế, 12 anchors, 114 phiên; hai direction và ba query mode dùng cùng pool cho mỗi thiết kế.
- 15 thiết kế candidates thật; 4 thiết kế problem bổ sung một candidate tổng hợp ở phía thiếu. Candidate tổng hợp chỉ có facet có nguồn, không bịa abstract/DOI.
- Mỗi pool 1 cùng focus, 1 khác focus, 18 ngoài context. 152 observation facet riêng, không lấy chính candidates để sinh phản ứng.
- 3 feedback seeds × 2 mức noise; dùng cùng cấu trúc nội dung, không coi sáu điều kiện là mẫu người dùng độc lập.
- Ground truth/provenance ẩn chỉ cho simulator/evaluator. Phương pháp chỉ đọc catalog và dữ liệu quan sát trước cutoff.
- `structurally_valid` là kiểm cấu trúc/nguồn/nhãn/thời gian. Metadata `semantic_review: pending` giữ nguyên: chưa kiểm tính thực tế của tổ hợp ngữ nghĩa, không phải human gold. Trạng thái đó không là điều kiện chặn benchmark mock; kết luận phải giới hạn vào protocol mô phỏng.

## Chuyển thư mục ngày 21/10/2026

Bản dữ liệu trước chuyển được giữ nguyên trong `../backup/20261021_layout_before/datasets/observation_v1/`, cùng snapshot code trước chuyển. Source bundle giữ nguyên bytes; chỉ sửa đường dẫn project mặc định của code mới để hoạt động từ thư mục proposal.

Dataset ở vị trí mới được sinh lại từ đúng nguồn/config cũ, thay vì sửa checksum để bỏ qua validator. Đối chiếu hashes ghi tại `layout_report.json`. Việc chuyển thư mục không là một lần benchmark và không tạo kết quả thuật toán.

`cleanup_report.json` trong thư mục này là nhật ký lịch sử của lần dọn 20/10; đường dẫn trong đó mô tả thời điểm cũ. Kế hoạch thực nghiệm hiện hành ở `../README_PROPOSAL.md`.
