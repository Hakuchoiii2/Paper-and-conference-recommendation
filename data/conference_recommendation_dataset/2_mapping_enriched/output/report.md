# Kết quả mở rộng mapping CSFCube

Chạy lại từ raw + corpus/ID chung + bảng mapping + cache metadata cục bộ. Không đọc output hoặc nhãn cũ của Extra_DOING; không gọi LLM.

| Trạng thái | Bản 1: raw mapping | Mở rộng tên raw | Bản 2: thêm metadata định danh |
|---|---:|---:|---:|
| matched | 884 | 1040 | 1150 |
| excluded | 809 | 809 | 985 |
| unresolved | 2489 | 2333 | 2047 |

Tổng: **4182 bài CSFCube**. Conference/joint IDs cuối: **74**.

- Bài mới vào conference: **420**; bài rời conference: **154**; bài còn conference nhưng đổi ID: **17**.
- Không cộng nhãn cũ vào nhãn mới. Metadata có thể sửa raw conference thành workshop/journal hoặc giữ chưa rõ.
- DOI gốc được tra đúng định danh; DOI từ Semantic Scholar chỉ dùng khi nối đúng CorpusId/title và Crossref đối chiếu được tác giả.
- Chỉ title chuẩn hóa trùng hoàn toàn mới nhận metadata. Thiếu tác giả được ghi rõ, không gọi là đã kiểm tra tác giả đạt.
- Trong nhóm conference: **823 bài** có metadata được nhận; **327 bài** còn dựa trên raw mapping. **254 bài** có đối chiếu tác giả đạt theo quy tắc tự động.
- Nhiều DOI/bản công bố có loại hoặc conference khác nhau giữ unresolved; không chọn nhãn thuận lợi để tăng số bài.

## Nguồn và giới hạn

Cache chứa 4685 phản hồi bài/metadata từ API theo định danh (có thể nhiều snapshot cho một DOI). Cache là đầu vào có hash, không phải bảng nhãn được nhập sẵn.
Mặc định chạy offline. Cache ban đầu được tái sử dụng từ các evidence_cache cũ; có lưu URL/thời điểm/hash nguồn. Không sử dụng tìm title hoặc lần ngược arXiv. Các lựa chọn tên/alias vẫn là quy tắc cục bộ, chưa được người chấm xác nhận toàn bộ. Chưa đo precision/recall nhãn; chưa có human gold.

## Số bài theo hội nghị

| ID | Hội nghị | Số bài |
|---|---|---:|
| CONF_EMNLP | Conference on Empirical Methods in Natural Language Processing | 190 |
| CONF_ACL | Annual Meeting of the Association for Computational Linguistics | 179 |
| CONF_NAACL | Conference of the North American Chapter of the Association for Computational Linguistics | 111 |
| CONF_COLING | International Conference on Computational Linguistics | 53 |
| CONF_ICASSP | IEEE International Conference on Acoustics, Speech and Signal Processing | 49 |
| CONF_EACL | Conference of the European Chapter of the Association for Computational Linguistics | 38 |
| CONF_SIGIR | ACM SIGIR Conference on Research and Development in Information Retrieval | 35 |
| CONF_CVPR | IEEE/CVF Conference on Computer Vision and Pattern Recognition | 34 |
| CONF_ACL_IJCNLP | Joint Conference of ACL and IJCNLP | 33 |
| CONF_CONLL | Conference on Computational Natural Language Learning | 29 |
| CONF_CIKM | ACM International Conference on Information and Knowledge Management | 27 |
| CONF_IJCAI | International Joint Conference on Artificial Intelligence | 19 |
| CONF_INTERSPEECH | Interspeech | 17 |
| CONF_AAAI | AAAI Conference on Artificial Intelligence | 15 |
| CONF_ICCV | IEEE/CVF International Conference on Computer Vision | 15 |
| CONF_RANLP | International Conference on Recent Advances in Natural Language Processing | 14 |
| CONF_WWW | International World Wide Web Conference | 13 |
| CONF_ICML | International Conference on Machine Learning | 12 |
| CONF_CHI | ACM Conference on Human Factors in Computing Systems | 10 |
| CONF_CIG | IEEE Conference on Computational Intelligence and Games | 10 |
| CONF_ICLR | International Conference on Learning Representations | 10 |
| CONF_ICPR | International Conference on Pattern Recognition | 10 |
| CONF_KDD | ACM SIGKDD Conference on Knowledge Discovery and Data Mining | 10 |
| CONF_LREC | International Conference on Language Resources and Evaluation | 10 |
| CONF_ASONAM | International Conference on Advances in Social Networks Analysis and Mining | 8 |
| CONF_IJCNLP | International Joint Conference on Natural Language Processing | 8 |
| CONF_IJCNN | International Joint Conference on Neural Networks | 8 |
| CONF_NEURIPS | Conference on Neural Information Processing Systems | 8 |
| CONF_SIGDIAL | SIGDIAL Meeting on Discourse and Dialogue | 8 |
| CONF_WMT | Conference on Machine Translation | 8 |
| CONF_BIGDATA | IEEE International Conference on Big Data | 7 |
| CONF_ICME | IEEE International Conference on Multimedia and Expo | 7 |
| CONF_IROS | IEEE/RSJ International Conference on Intelligent Robots and Systems | 7 |
| CONF_SIGMOD | ACM SIGMOD International Conference on Management of Data | 7 |
| CONF_EMNLP_CONLL | Joint Conference of EMNLP and CoNLL | 6 |
| CONF_ICMLA | International Conference on Machine Learning and Applications | 6 |
| CONF_ICRA | IEEE International Conference on Robotics and Automation | 6 |
| CONF_ICSE | International Conference on Software Engineering | 6 |
| CONF_PACLIC | Pacific Asia Conference on Language, Information and Computation | 6 |
| CONF_SDM | SIAM International Conference on Data Mining | 6 |
| CONF_ACM_MM | ACM International Conference on Multimedia | 5 |
| CONF_ICDM | IEEE International Conference on Data Mining | 5 |
| CONF_SMC | IEEE International Conference on Systems, Man and Cybernetics | 5 |
| CONF_WI | IEEE/WIC/ACM International Conference on Web Intelligence | 5 |
| CONF_ECML_PKDD | Joint European Conference on Machine Learning and Principles and Practice of Knowledge Discovery in Databases | 4 |
| CONF_FOCS | IEEE Symposium on Foundations of Computer Science | 4 |
| CONF_HT | ACM Conference on Hypertext and Social Media | 4 |
| CONF_ICDAR | International Conference on Document Analysis and Recognition | 4 |
| CONF_ICFHR | International Conference on Frontiers in Handwriting Recognition | 4 |
| CONF_ICIP | IEEE International Conference on Image Processing | 4 |
| CONF_ICSC | IEEE International Conference on Semantic Computing | 4 |
| CONF_SODA | ACM-SIAM Symposium on Discrete Algorithms | 4 |
| CONF_WSDM | ACM International Conference on Web Search and Data Mining | 4 |
| CONF_COMPSAC | International Computer Software and Applications Conference | 3 |
| CONF_CSCW | ACM Conference on Computer-Supported Cooperative Work | 3 |
| CONF_GECCO | Genetic and Evolutionary Computation Conference | 3 |
| CONF_ICMLC | International Conference on Machine Learning and Cybernetics | 3 |
| CONF_ICTAI | IEEE International Conference on Tools with Artificial Intelligence | 3 |
| CONF_ICWSM | International AAAI Conference on Web and Social Media | 3 |
| CONF_AMTA | Conference of the Association for Machine Translation in the Americas | 2 |
| CONF_CCS | ACM Conference on Computer and Communications Security | 2 |
| CONF_ICDE | IEEE International Conference on Data Engineering | 2 |
| CONF_SAC | ACM Symposium on Applied Computing | 2 |
| CONF_STOC | ACM Symposium on Theory of Computing | 2 |
| CONF_WACV | IEEE Winter Conference on Applications of Computer Vision | 2 |
| CONF_AIIDE | AAAI Conference on Artificial Intelligence and Interactive Digital Entertainment | 1 |
| CONF_AISTATS | International Conference on Artificial Intelligence and Statistics | 1 |
| CONF_ECCV | European Conference on Computer Vision | 1 |
| CONF_ECML | European Conference on Machine Learning | 1 |
| CONF_ECOOP | European Conference on Object-Oriented Programming | 1 |
| CONF_ICALP | International Colloquium on Automata, Languages and Programming | 1 |
| CONF_MICCAI | International Conference on Medical Image Computing and Computer-Assisted Intervention | 1 |
| CONF_UIST | ACM Symposium on User Interface Software and Technology | 1 |
| CONF_WEBSCI | ACM Web Science Conference | 1 |

Xem `comparison.csv` để đối chiếu từng bài; `paper_conference_links.jsonl` để xem raw và metadata hỗ trợ/bị loại. Chưa áp quota, chưa chọn shortlist, chưa chia tập hoặc xây profile.
