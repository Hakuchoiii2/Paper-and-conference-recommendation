# Bản 4: mở rộng mapping tên từ danh mục venue

Kế thừa bản 3; chỉ mở rộng tên venue có sẵn trong raw bằng danh mục ICORE, ACL Anthology và tên journal khớp đầy đủ trong Crossref. Không tìm bài theo title/arXiv, không bổ sung bài ngoài CSFCube, không gọi LLM.

| Trạng thái | Bản 3 | Bản 4 |
|---|---:|---:|
| matched | 882 | 1144 |
| excluded | 810 | 1083 |
| unresolved | 2490 | 1955 |

Tổng 4182 bài canonical; 171 hội nghị/joint IDs. Thêm 262 bài conference và phân loại thêm 273 bài ngoài đích từ nhóm unresolved.

Còn chưa rõ: 1364 bài thiếu venue/chỉ preprint, 588 bài còn tên venue chưa chốt và 3 bài mâu thuẫn nguồn/alias; nhóm thiếu venue không được tự lấp bằng tên hội nghị.

Danh mục có 2698 venue; 2 phản hồi nguồn lỗi/không dùng được được giữ rõ. Mỗi tên mới có URL, ID nguồn và phương pháp khớp trong venue_mapping.csv; từng bài giữ catalog_evidence.

## Vì sao chưa so trực tiếp với bảng 3.455 bài

Bảng người dùng đưa gộp hội nghị/tạp chí và đếm trên 4.207 bản ghi raw; ở đây tách conference với loại ngoài đích trên bài sau gộp trùng. Chưa có code/cách kiểm chứng của bảng đó nên chưa xác nhận được 3.455 nhãn. Có DOI/ACL ID hoặc venue không rỗng chưa chứng minh bài thuộc main conference; thiếu DOI cũng không chứng minh preprint chưa từng xuất bản.

Raw hiện có 3343 bản ghi có DOI hoặc ACL ID, 3957 có venue và 202 thiếu cả venue/DOI/ACL ID. Xem raw_inventory.json để phân biệt đơn vị đếm.

Tên conference trần vẫn chưa xác minh track từng bài. Workshop/companion không được gộp theo conference chủ nhà; trùng tên, đổi loại theo thời gian hoặc thiếu thông tin tiếp tục unresolved. Chưa có kiểm định độc lập toàn bộ nhãn/precision/recall.

## Chạy lại

```powershell
python audit_mapping.py
python preprocess_cube.py --prepare-mapping
python preprocess_cube.py --check
```

Bước lấy danh mục công khai khi cần: python audit_mapping.py --download-sources. Mặc định dựng lại từ hồ sơ nguồn đi kèm, không gọi mạng.

## Hội nghị và số bài

| ID | Hội nghị | Số bài |
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
| CONF_SIGDIAL | SIGDIAL Meeting on Discourse and Dialogue | 13 |
| CONF_IJCAI | International Joint Conference on Artificial Intelligence | 12 |
| CONF_LREC | International Conference on Language Resources and Evaluation | 12 |
| CONF_RANLP | International Conference on Recent Advances in Natural Language Processing | 11 |
| CONF_SIGMOD | ACM SIGMOD International Conference on Management of Data | 10 |
| CONF_ICCV | IEEE/CVF International Conference on Computer Vision | 9 |
| CONF_ICLR | International Conference on Learning Representations | 9 |
| CONF_ICORE_13 | ACM Conference on Computer Supported Cooperative Work | 9 |
| CONF_ACL_STARSEM | Joint Conference on Lexical and Computational Semantics | 8 |
| CONF_ICPR | International Conference on Pattern Recognition | 8 |
| CONF_IJCNLP | International Joint Conference on Natural Language Processing | 8 |
| CONF_NEURIPS | Conference on Neural Information Processing Systems | 8 |
| CONF_ACM_MM | ACM International Conference on Multimedia | 7 |
| CONF_ICORE_2268 | International Conference on Learning Analytics and Knowledge | 7 |
| CONF_ICORE_2355 | ACM Conference on Learning @ Scale | 7 |
| CONF_EMNLP_CONLL | Joint Conference of EMNLP and CoNLL | 6 |
| CONF_ICORE_1658 | Pacific Asia Conference on Language, Information and Computation | 6 |
| CONF_ICORE_2311 | IEEE/ACM International Conference on Advances in Social Networks Analysis and Mining | 6 |
| CONF_ICORE_642 | IEEE International Conference on Data Mining | 6 |
| CONF_ICORE_664 | IEEE International Conference on Multimedia and Expo | 6 |
| CONF_ICORE_792 | IEEE/RSJ International Conference on Intelligent Robots and Systems | 6 |
| CONF_ICALP | International Colloquium on Automata, Languages and Programming | 5 |
| CONF_ICORE_1123 | International Conference on Machine Learning and Cybernetics | 5 |
| CONF_ICORE_18 | ACM Conference on Object Oriented Programming Systems Languages and Applications | 5 |
| CONF_WSDM | ACM International Conference on Web Search and Data Mining | 5 |
| CONF_AAAI | AAAI Conference on Artificial Intelligence | 4 |
| CONF_ACL_ANLP | Applied Natural Language Processing Conference | 4 |
| CONF_ACL_SIGMORPHON | Meeting of the ACL Special Interest Group on Computational Morphology and Phonology | 4 |
| CONF_ECML_PKDD | Joint European Conference on Machine Learning and Principles and Practice of Knowledge Discovery in Databases | 4 |
| CONF_ICORE_1122 | International Conference on Machine Learning and Applications | 4 |
| CONF_ICORE_1209 | International Conference on Software Engineering | 4 |
| CONF_ICORE_55 | ACM Special Interest Group on Computer Science Education Conference | 4 |
| CONF_ICORE_556 | Genetic and Evolutionary Computations | 4 |
| CONF_ICORE_654 | IEEE International Conference on Image Processing | 4 |
| CONF_ICORE_66 | ACM Symposium on User Interface Software and Technology | 4 |
| CONF_ICORE_794 | IEEE/WIC/ACM International Conference on Web Intelligence (previously joint with Intelligent Agent Technology WI-IAT) | 4 |
| CONF_CICLING | International Conference on Intelligent Text Processing and Computational Linguistics | 3 |
| CONF_ICORE_1101 | International Conference on Intelligent User Interfaces | 3 |
| CONF_ICORE_1727 | SIAM International Conference on Data Mining | 3 |
| CONF_ICORE_2047 | IEEE International Conference on Document Analysis and Recognition | 3 |
| CONF_ICORE_2051 | IEEE International Conference on Robotics and Automation | 3 |
| CONF_ICORE_2061 | IEEE Congress on Evolutionary Computation | 3 |
| CONF_ICORE_2237 | IEEE International Conference on Data Science and Advanced Analytics | 3 |
| CONF_ICORE_348 | Conference of the Association for Machine Translation in the Americas | 3 |
| CONF_ACL_HLT | Human Language Technology Conference | 2 |
| CONF_ACL_ROCLING | Conference on Computational Linguistics and Speech Processing | 2 |
| CONF_ECCV | European Conference on Computer Vision | 2 |
| CONF_ICORE_1038 | International Conference on Fuzzy Systems and Knowledge Discovery | 2 |
| CONF_ICORE_1144 | International Conference on Multimodal Interaction (was International Conference on Multimodal Interfaces) | 2 |
| CONF_ICORE_12 | ACM Conference on Computer and Communications Security | 2 |
| CONF_ICORE_124 | Conference on Learning Theory | 2 |
| CONF_ICORE_1251 | International Conference on Tools with Artificial Intelligence | 2 |
| CONF_ICORE_1269 | International Conference on Web Engineering | 2 |
| CONF_ICORE_1327 | International Natural Language Generation Conference | 2 |
| CONF_ICORE_1408 | The International Symposium on Research in Attacks, Intrusions and Defenses (was International Symposium on Recent Advances in Intrusion Detection) | 2 |
| CONF_ICORE_1551 | Internet Measurement Conference | 2 |
| CONF_ICORE_1825 | ACM International Joint Conference on Pervasive and Ubiquitous Computing (PERVASIVE and UbiComp combined from 2013) | 2 |
| CONF_ICORE_2021 | Extended Semantic Web Conference (was European Semantic Web Conference) | 2 |
| CONF_ICORE_2169 | International Conference on Web and Social Media | 2 |
| CONF_ICORE_2310 | ACM/IEEE International Conference on Human-Robot Interaction | 2 |
| CONF_ICORE_486 | European Conference on Machine Learning (Joined with PKDD from 2008) | 2 |
| CONF_ICORE_488 | European Conference on Object-Oriented Programming | 2 |
| CONF_ICORE_575 | Hawaii International Conference on System Sciences | 2 |
| CONF_ICORE_685 | IEEE International Joint Conference on Neural Networks | 2 |
| CONF_ICORE_688 | IEEE International Parallel and Distributed Processing Symposium (was IPPS and SPDP) | 2 |
| CONF_ICORE_724 | IEEE Pacific Visualization Symposium (was APVIS) | 2 |
| CONF_ICORE_750 | IEEE Symposium on Security and Privacy | 2 |
| CONF_ICORE_80 | ACM/SIAM Symposium on Discrete Algorithms | 2 |
| CONF_ICORE_986 | International Conference on Data Engineering | 2 |
| CONF_ACL_CLICIT | The Italian Conference on Computational Linguistics | 1 |
| CONF_ACL_FSMNLP | International Conference on Finite State Methods for Natural Language Processing | 1 |
| CONF_ACL_IWPT | International Conference on Parsing Technologies | 1 |
| CONF_ACL_NODALIDA | Nordic Conference of Computational Linguistics | 1 |
| CONF_EMNLP_VLC | Joint SIGDAT Conference on Empirical Methods in Natural Language Processing and Very Large Corpora | 1 |
| CONF_ICORE_1037 | International Conference on Functional Programming | 1 |
| CONF_ICORE_1048 | International Conference on High Performance Computing | 1 |
| CONF_ICORE_1054 | International Conference on Human-Computer Interaction with Mobile Devices and Services | 1 |
| CONF_ICORE_1056 | International Conference on Hybrid Intelligent Systems | 1 |
| CONF_ICORE_1072 | International Conference on Information Fusion | 1 |
| CONF_ICORE_1084 | International Conference on Information Technology Interfaces | 1 |
| CONF_ICORE_1113 | International Conference on Knowledge-Based and Intelligent Information and Engineering Systems | 1 |
| CONF_ICORE_1167 | International Conference on Parallel Processing | 1 |
| CONF_ICORE_1181 | IEEE International Conference on Program Comprehension (previously IWPC, changed in 2006) | 1 |
| CONF_ICORE_120 | Annual Meeting of the Cognitive Science Society | 1 |
| CONF_ICORE_1238 | International Conference on the Foundations of Digital Games | 1 |
| CONF_ICORE_1239 | International Conference on the Principles of Knowledge Representation and Reasoning | 1 |
| CONF_ICORE_1244 | International Conference on Model Driven Engineering Languages and Systems (Previously UML, changed in 2005) | 1 |
| CONF_ICORE_1271 | International Conference on Web Information Systems Engineering | 1 |
| CONF_ICORE_1369 | International Symposium on Computer and Information Sciences | 1 |
| CONF_ICORE_1370 | International Symposium on Computer Architecture and High Performance Computing | 1 |
| CONF_ICORE_147 | Architectural Support for Programming Languages and Operating Systems | 1 |
| CONF_ICORE_15 | ACM Conference on Embedded Networked Sensor Systems | 1 |
| CONF_ICORE_150 | Artificial Intelligence in Medicine | 1 |
| CONF_ICORE_1582 | Knowledge capture | 1 |
| CONF_ICORE_1588 | Language Descriptions, Tools and Applications | 1 |
| CONF_ICORE_1598 | Logics in Artificial Intelligence, European Conference | 1 |
| CONF_ICORE_1661 | Pacific Rim International Conference on Artificial Intelligence | 1 |
| CONF_ICORE_1666 | Pacific Symposium on Biocomputing | 1 |
| CONF_ICORE_175 | Asia-Pacific Bioinformatics Conference | 1 |
| CONF_ICORE_1790 | Symposium on Parallelism in Algorithms and Architectures | 1 |
| CONF_ICORE_1865 | Winter Simulation Conference | 1 |
| CONF_ICORE_1954 | Australasian Document Computing Symposium | 1 |
| CONF_ICORE_2003 | ACM Symposium on Document Engineering | 1 |
| CONF_ICORE_2074 | IEEE International Conference on Computer Communications | 1 |
| CONF_ICORE_2085 | ACM Conference on Digital Libraries | 1 |
| CONF_ICORE_2187 | Iberian Conference on Information Systems and Technologies | 1 |
| CONF_ICORE_22 | ACM International Conference on Advances in Geographic Information Systems | 1 |
| CONF_ICORE_2210 | Semantics - International Conference on Semantic Systems | 1 |
| CONF_ICORE_2221 | International Joint Conference on Computational Intelligence | 1 |
| CONF_ICORE_2261 | International Conference on Computer Supported Education | 1 |
| CONF_ICORE_2280 | IEEE International Conference on Software Analysis, Evolution and Reengineering | 1 |
| CONF_ICORE_2286 | International Conference on Control, Decision and Information Technologies | 1 |
| CONF_ICORE_2335 | ACM SIGIR Conference on Human Information Interaction And Retrieval | 1 |
| CONF_ICORE_2344 | International Conference on Evolutionary Multi-Criterion Optimization | 1 |
| CONF_ICORE_2350 | IEEE International Symposium on Computer-Based Medical Systems | 1 |
| CONF_ICORE_30 | ACM International Conference on Supercomputing | 1 |
| CONF_ICORE_326 | Computability in Europe: Logic and Theory of Algorithms | 1 |
| CONF_ICORE_352 | Conference of the European Association for Machine Translation | 1 |
| CONF_ICORE_404 | Cultural Attitudes towards Technology and Communications | 1 |
| CONF_ICORE_407 | Current Trends in Theory and Practice of Computer Science | 1 |
| CONF_ICORE_425 | Developments in Language Theory | 1 |
| CONF_ICORE_439 | Dynamic Languages Symposium | 1 |
| CONF_ICORE_465 | Euromicro International Conference on Parallel, Distributed and Network Based Processing | 1 |
| CONF_ICORE_473 | European Conference on Artificial Intelligence | 1 |
| CONF_ICORE_506 | European Signal Processing Conference | 1 |
| CONF_ICORE_511 | European Symposium on Algorithms | 1 |
| CONF_ICORE_514 | European Symposium on Programming | 1 |
| CONF_ICORE_57 | ACM Special Interest Group on Supporting Group Work (was SIGGRoup) | 1 |
| CONF_ICORE_61 | Asia Conference on Information, Computer and Communications Security | 1 |
| CONF_ICORE_616 | IEEE Consumer Communications and Networking Conference | 1 |
| CONF_ICORE_63 | ACM Symposium on Principles of Distributed Computing | 1 |
| CONF_ICORE_637 | IEEE International Conference on Computer and Information Technology | 1 |
| CONF_ICORE_656 | IEEE International Conference on Information and Automation | 1 |
| CONF_ICORE_666 | IEEE International Conference on Neural Networks | 1 |
| CONF_ICORE_678 | IEEE International Conference on Web Services | 1 |
| CONF_ICORE_690 | IEEE International Requirements Engineering Conference | 1 |
| CONF_ICORE_699 | IEEE International Symposium on Information Theory | 1 |
| CONF_ICORE_718 | IEEE International Working Conference on Source Code Analysis and Manipulation | 1 |
| CONF_ICORE_728 | IEEE Symposium on 3D User Interfaces | 1 |
| CONF_ICORE_744 | IEEE Symposium on Computers and Communications | 1 |
| CONF_ICORE_745 | IEEE Symposium on Foundations of Computer Science | 1 |
| CONF_ICORE_751 | IEEE Symposium on Visual Analytics Science and Technology | 1 |
| CONF_ICORE_782 | IEEE/ACIS International Conference on Computer and Information Science | 1 |
| CONF_ICORE_790 | International Conference on Trust, Security and Privacy in Computing and Communications | 1 |
| CONF_ICORE_803 | IFIP International Conference on Theoretical Computer Science | 1 |
| CONF_ICORE_819 | Inductive Logic Programming | 1 |
| CONF_ICORE_82 | ACM-SIGACT Symposium on Principles of Programming Languages | 1 |
| CONF_ICORE_847 | Intelligent Systems in Molecular Biology | 1 |
| CONF_ICORE_92 | IEEE International Conference on Advanced Video and Signal Based Surveillance | 1 |
| CONF_ICORE_922 | International Joint Conference on Autonomous Agents and Multiagent Systems (previously the International Conference on Multiagent Systems, ICMAS, changed in 2000) | 1 |
| CONF_ICORE_936 | International Conference on Compiler Construction | 1 |
| CONF_ICORE_957 | SIGGRAPH Asia | 1 |
| CONF_ICORE_996 | International Conference on Digital Government Research | 1 |
| CONF_ICORE_997 | International Conference on Digital Society | 1 |
| CONF_PRIME | International Conference on Pattern Recognition, Informatics and Mobile Engineering | 1 |
