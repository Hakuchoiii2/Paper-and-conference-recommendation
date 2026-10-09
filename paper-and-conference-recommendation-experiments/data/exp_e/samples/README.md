# Pilot Exp E — Thích ứng sở thích theo thời gian

Dùng corpus chính và full silver A đã được xác minh; chỉ giảm số query/user/session/event trong config.
Đặt output_dir/truth_dir dưới `data/exp_e/samples/generated` và `samples/ground_truth`.
Đặt users_path tới users.jsonl của C pilot kèm C manifest; D cũng lấy C logs tại cùng directory.
Dữ liệu pilot dùng contract 2.0 và dataset_kind=mock; không ghi test fixtures vào corpus thật.
Xem [README exp](../README.md) và [protocol](../../../docs/EXPERIMENT_PROTOCOL.md).
