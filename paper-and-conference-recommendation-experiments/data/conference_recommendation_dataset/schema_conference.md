# Schema chung cho Conference Recommendation

Chỉ gồm bài CSFCube. Mỗi dòng JSONL là một record; `null` nghĩa là chưa biết hoặc chưa xác định. Title/abstract lấy từ corpus chung bằng `paper_id`.

## Mapping bài – hội nghị: `output/paper_conference_links.jsonl`

| Trường | Kiểu / ý nghĩa |
|---|---|
| `paper_id` | string; ID bài sau gộp trùng |
| `source`, `source_ids` | nguồn csfcube và danh sách ID raw của bài |
| `conference_id` | string/null; có giá trị khi matched |
| `mapping_status` | matched / excluded / unresolved |
| `venue_type` | conference / journal / workshop / auxiliary / preprint / unknown |
| `reason` | mã lý do của quyết định |
| `verification_level` | raw_mapping / metadata_checked / metadata_review / source_checked |
| `year` | int/null; năm raw duy nhất thống nhất giữa các alias |
| `year_source` | csfcube_raw.metadata.year |
| `year_status` | available / missing / conflicting |
| `year_candidates` | mảng các năm raw hợp lệ, duy nhất, tăng dần |
| `publication_year` | int/null; năm được metadata xuất bản ủng hộ, tách riêng với year |
| `edition_year` | hiện null; chưa xác định năm tổ chức hội nghị |
| `evidence` | mảng chứng cứ raw: ID/dòng nguồn, venue, journal, năm, định danh và quy tắc mapping |

Năm raw được chuẩn hóa thành số nguyên 1000–2100; thiếu hoặc có nhiều năm khác nhau thì `year=null`, không tự suy năm tổ chức.

Trường mở rộng, nếu có: `metadata_evidence` giữ metadata và kiểm tra danh tính; `baseline_*`, `expanded_raw_*`, `pre_review_*` giữ quyết định trước xử lý; `review_correction` ghi chỉnh sửa có nguồn.

`catalog_evidence` nếu có ghi tên raw, ID danh mục và URL đối chiếu; scope=venue_name_only chỉ kiểm tra tên venue, chưa xác minh từng bài/track.

## Bảng tên venue: `venue_mapping.csv`

| Nhóm trường | Ý nghĩa |
|---|---|
| `venue_raw`, `venue_normalized` | tên gốc và tên đã chuẩn hóa |
| `raw_record_count`, `canonical_paper_count` | số bản ghi/bài có tên này; không cộng các dòng để suy tổng bài duy nhất |
| `mapping_status`, `venue_type`, `conference_id` | quyết định cho tên venue; ID rỗng nếu chưa matched |
| `rule_id`, `note`, `review_status` | quy tắc, giải thích và trạng thái unreviewed/rule_reviewed |
| `origin`, `metadata_record_count` nếu có | nguồn xuất hiện của tên và số metadata liên quan |
| `catalog_match_method`, `catalog_venue_ids`, `catalog_source_urls` nếu có | cách khớp tên, ID và URL danh mục ngoài |

## Catalog, nhóm bài và hồ sơ kiểm tra

| Tệp | Nội dung |
|---|---|
| `output/conference_catalog.jsonl` | mỗi ID hội nghị một dòng: canonical_name, acronym, is_joint, aliases, in_target_catalog, selection_reason, registry_sources, verification_level |
| `output/conference_papers.jsonl` | conference_id, paper_ids duy nhất và paper_count; chỉ nhóm matched |
| `output/manifest.json` | phiên bản, nguồn, thời điểm, đường dẫn/hash đầu vào và đầu ra, số lượng, kết quả kiểm tra |
| `output/comparison.csv` nếu có | quyết định trước/sau theo paper_id, lý do và cờ changed |
| `review/` nếu có | mẫu kiểm tra, chứng cứ nguồn, chỉnh sửa và manifest của lượt đối chiếu |

`matched` là nhãn được quy tắc nhận diện; `excluded` là ngoài loại đích; `unresolved` là chưa đủ căn cứ chốt. `unknown` mô tả loại venue chưa rõ, không đồng nghĩa với trạng thái unresolved. Mức kiểm tra nguồn/quy tắc chưa phải xác nhận độc lập từng bài.

Nhóm bài chưa chia train/dev/test; khi đánh giá, chỉ dùng train để xây profile hội nghị.
