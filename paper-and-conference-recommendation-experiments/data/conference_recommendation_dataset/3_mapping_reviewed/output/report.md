# Kết quả mapping sau kiểm tra nguồn

**Bản 3: sửa quy tắc tên và áp dụng các chỉnh sửa mẫu có nguồn được lưu. Không phải human gold; không sửa raw hoặc ghi đè bản 1/2.**

| Chỉ tiêu | Số lượng |
|---|---:|
| Bản ghi CSFCube raw | 4207 |
| Bài CSFCube sau tiền xử lý chung | 4182 |
| Matched conference | 882 |
| Excluded ngoài loại đích | 810 |
| Unresolved chưa rõ | 2490 |
| Hội nghị/joint IDs có bài | 36 |

Đã sửa nhầm PRIME→ICPR và tách joint EMNLP/VLC. Một bài workshop ICLR được loại, một bài ACL được chuyển sang joint ACL-IJCNLP, một ca có bản conference/journal giữ unresolved. Chứng cứ và giới hạn kiểm tra nằm trong ../review/report.md; không coi mọi bài chưa bị phát hiện lỗi là đã được xác minh.

Matched là nhãn ánh xạ từ raw, **chưa phải đã xác minh nơi công bố hoặc human gold**. Kiểm tra tự động chỉ xác nhận tính nhất quán; chưa đo precision/recall nhãn.

## Phân loại venue

| Loại | Số bài |
|---|---:|
| auxiliary | 14 |
| conference | 882 |
| journal | 646 |
| preprint | 1118 |
| unknown | 1372 |
| workshop | 150 |

## Hội nghị và danh sách bài

| ID | Tên | Số bài |
|---|---|---:|
| CONF_ACL | Annual Meeting of the Association for Computational Linguistics | 176 |
| CONF_EMNLP | Conference on Empirical Methods in Natural Language Processing | 148 |
| CONF_NAACL | Conference of the North American Chapter of the Association for Computational Linguistics | 77 |
| CONF_COLING | International Conference on Computational Linguistics | 64 |
| CONF_ICASSP | IEEE International Conference on Acoustics, Speech and Signal Processing | 37 |
| CONF_SIGIR | ACM SIGIR Conference on Research and Development in Information Retrieval | 37 |
| CONF_EACL | Conference of the European Chapter of the Association for Computational Linguistics | 35 |
| CONF_CIKM | ACM International Conference on Information and Knowledge Management | 33 |
| CONF_CONLL | Conference on Computational Natural Language Learning | 24 |
| CONF_KDD | ACM SIGKDD Conference on Knowledge Discovery and Data Mining | 20 |
| CONF_CVPR | IEEE/CVF Conference on Computer Vision and Pattern Recognition | 19 |
| CONF_ICML | International Conference on Machine Learning | 18 |
| CONF_CHI | ACM Conference on Human Factors in Computing Systems | 17 |
| CONF_COLING_ACL | Joint Conference of COLING and ACL | 14 |
| CONF_WWW | International World Wide Web Conference | 14 |
| CONF_ACL_IJCNLP | Joint Conference of ACL and IJCNLP | 13 |
| CONF_IJCAI | International Joint Conference on Artificial Intelligence | 12 |
| CONF_SIGDIAL | SIGDIAL Meeting on Discourse and Dialogue | 12 |
| CONF_LREC | International Conference on Language Resources and Evaluation | 11 |
| CONF_RANLP | International Conference on Recent Advances in Natural Language Processing | 11 |
| CONF_SIGMOD | ACM SIGMOD International Conference on Management of Data | 10 |
| CONF_ICCV | IEEE/CVF International Conference on Computer Vision | 9 |
| CONF_ICLR | International Conference on Learning Representations | 9 |
| CONF_ICPR | International Conference on Pattern Recognition | 8 |
| CONF_IJCNLP | International Joint Conference on Natural Language Processing | 8 |
| CONF_NEURIPS | Conference on Neural Information Processing Systems | 8 |
| CONF_ACM_MM | ACM International Conference on Multimedia | 7 |
| CONF_EMNLP_CONLL | Joint Conference of EMNLP and CoNLL | 6 |
| CONF_ICALP | International Colloquium on Automata, Languages and Programming | 5 |
| CONF_WSDM | ACM International Conference on Web Search and Data Mining | 5 |
| CONF_AAAI | AAAI Conference on Artificial Intelligence | 4 |
| CONF_ECML_PKDD | Joint European Conference on Machine Learning and Principles and Practice of Knowledge Discovery in Databases | 4 |
| CONF_CICLING | International Conference on Intelligent Text Processing and Computational Linguistics | 3 |
| CONF_ECCV | European Conference on Computer Vision | 2 |
| CONF_EMNLP_VLC | Joint SIGDAT Conference on Empirical Methods in Natural Language Processing and Very Large Corpora | 1 |
| CONF_PRIME | International Conference on Pattern Recognition, Informatics and Mobile Engineering | 1 |

Danh sách paper ID nằm trong `conference_papers.jsonl`; lấy title/abstract từ corpus chung bằng ID. Bảng `../venue_mapping.csv` chứa mọi venue, quy tắc và trạng thái để kiểm tra. Không có shortlist/quota, split, profile hoặc facet mới trong lần xử lý này.
