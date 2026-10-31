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

Bản 5 thêm `mapping_review_v5`: trạng thái/phạm vi review, cờ metadata raw, `usable_for_split`, `human_verified=false` và lý do/URL nếu có; `pre_v5_review` giữ quyết định trước khi sửa. Chỉ các bài matched của bản 4 thuộc phạm vi review này.

`catalog_evidence` nếu có ghi tên raw, ID danh mục và URL đối chiếu; scope=venue_name_only chỉ kiểm tra tên venue, chưa xác minh từng bài/track.

## Bảng tên venue: `venue_mapping.csv`

| Nhóm trường | Ý nghĩa |
|---|---|
| `venue_raw`, `venue_normalized` | tên gốc và tên đã chuẩn hóa |
| `raw_record_count`, `canonical_paper_count` | số bản ghi/bài có tên này; không cộng các dòng để suy tổng bài duy nhất |
| `mapping_status`, `venue_type`, `conference_id` | quyết định cho tên venue; ID rỗng nếu chưa matched |
| `rule_id`, `note`, `review_status` | quy tắc, giải thích và trạng thái unreviewed / rule_reviewed / ai_name_reviewed / paper_context_required |
| `origin`, `metadata_record_count` nếu có | nguồn xuất hiện của tên và số metadata liên quan |
| `catalog_match_method`, `catalog_venue_ids`, `catalog_source_urls` nếu có | cách khớp tên, ID và URL danh mục ngoài |

## Catalog, nhóm bài và hồ sơ kiểm tra

| Tệp | Nội dung |
|---|---|
| `output/conference_catalog.jsonl` | mỗi ID hội nghị một dòng: canonical_name, acronym, is_joint, aliases, in_target_catalog, selection_reason, registry_sources, verification_level |
| `output/conference_papers.jsonl` | conference_id, paper_ids duy nhất và paper_count; chỉ nhóm matched |
| `output/conference_statistics.csv` nếu có | conference_id, acronym, conference_name, paper_count; số bài matched theo hội nghị |
| `output/manifest.json` | phiên bản, nguồn, thời điểm, đường dẫn/hash đầu vào và đầu ra, số lượng, kết quả kiểm tra |
| `output/comparison.csv` nếu có | quyết định trước/sau theo paper_id, lý do và cờ changed |
| `review/` nếu có | mẫu kiểm tra, chứng cứ nguồn, chỉnh sửa và manifest của lượt đối chiếu |

`matched` là nhãn được quy tắc nhận diện; `excluded` là ngoài loại đích; `unresolved` là chưa đủ căn cứ chốt. `unknown` mô tả loại venue chưa rõ, không đồng nghĩa với trạng thái unresolved. Mức kiểm tra nguồn/quy tắc chưa phải xác nhận độc lập từng bài.

## Train/test bản 5: `5_mapping_reviewed/splits/temporal_2015_2016_2019/`

`train.jsonl` và `test.jsonl` **cùng schema**, có sẵn title/abstract; khác giá trị `split` và khoảng năm, không cần hai schema riêng.

| Trường | Kiểu / ý nghĩa |
|---|---|
| `paper_id`, `source`, `source_ids` | string, string, string[]; giữ ID/nguồn của mapping |
| `title`, `abstract` | string; văn bản từ corpus chung, đầu vào mô hình |
| `conference_id`, `conference_name` | string; nhãn đích và tên hội nghị |
| `label_index` | int 0–29; nhãn số chung cho train/test, tra trong label_map.json |
| `mapping_status`, `mapping_review_status` | matched và trạng thái từ mapping_review_v5.status |
| `split` | train / test |
| `year`, `year_source`, `year_status` | int; csfcube_raw.metadata.year; available |

Train lấy năm ≤ 2015 (602 bài), test lấy 2016–2019 (186 bài), cùng 30 hội nghị. Chỉ dùng matched đã review, hội nghị có tổng ≥ 5 bài và ít nhất 3 train + 1 test; loại năm thiếu/mâu thuẫn hoặc ngoài khoảng. Chỉ train dùng xây profile, test để đánh giá; chưa có dev. Không đưa các trường nhãn vào văn bản đầu vào.

Tệp kèm theo: `label_map.json` là mảng `{label_index, conference_id, conference_name, acronym}`; `conference_catalog.jsonl` giữ hội nghị được chọn theo schema catalog ở trên, thêm `label_index`, `train_paper_count`, `test_paper_count`. `conference_split_statistics.csv` ghi số matched, số bài theo khoảng năm, cờ chọn, số train/test và lý do loại từng hội nghị; `excluded_from_split.csv` ghi bài không vào split và lý do. `split_config.json` lưu quy tắc; `manifest.json` lưu số lượng, hash và kết quả kiểm tra.

Quyết định theo từng bài trong `paper_conference_links.jsonl` được ưu tiên hơn mapping tên venue khi có ngoại lệ.
