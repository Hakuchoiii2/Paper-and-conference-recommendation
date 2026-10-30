# Đối chiếu riêng phần mở rộng/enrichment của bản 2

**Kiểm tra mẫu bằng nguồn metadata, không phải human gold. Không sửa đè output/nhãn bản 2.**

Mẫu 50 bài, seed 20261031, tối đa 10 bài ngẫu nhiên mỗi nhóm thay đổi; không phải mẫu ngẫu nhiên đều của toàn corpus.
Tra theo định danh từ raw/metadata mục tiêu; không dùng nhãn cũ làm đáp án. Lượt lấy URL mới: 0. Nguồn nằm trong snapshot chung của bản 3.

| Nhóm | Cỡ nhóm | Số kiểm tra |
|---|---:|---:|
| added_from_metadata | 400 | 10 |
| added_from_raw_aliases | 20 | 10 |
| changed_conference_id | 17 | 10 |
| removed_or_withheld | 154 | 10 |
| retained_with_metadata | 406 | 10 |

| Kết quả đối chiếu | Số mẫu |
|---|---:|
| identity_review | 5 |
| no_reference_available | 2 |
| reference_agreement | 34 |
| unresolved_with_reference | 5 |
| venue_or_track_unresolved | 4 |

reference_agreement là nguồn ủng hộ quyết định mục tiêu; reference_contradiction là nguồn chỉ khác conference hoặc ngoài main. Các kết quả unresolved/identity/track/no_reference vẫn cần kiểm tra; không tự coi nhãn sai hoặc đúng. Chưa dùng tỷ lệ này làm precision/recall của toàn bản 2 và chưa đánh giá độc lập bằng người chấm.

Bản 2 vẫn là snapshot đối chứng, bao gồm các rule cũ. Các sửa tên của bản 3 chưa được áp ngược vào bản 2. Khi chốt bản enriched dùng thực nghiệm, phải hợp nhất sửa rule có nguồn và xem lại các ca bất đồng thay vì cộng nhãn cho tăng số lượng.
