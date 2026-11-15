# Pilot40 — sổ đối chiếu cuối sau rà AI độc lập

40 bài / 200 facet. Hai bản trích source-first riêng được giữ nguyên/hash trước khi mở nhãn đối chiếu. Nhãn cuối là 345 AI references tạm thời; human review pending.
Không quy đổi khác biệt câu chữ, tách/gộp hoặc evidence thành accuracy/F1. Policy v2.2 được làm rõ sau pilot; cần mẫu mới trước mở rộng.

## P000349 — Towards Open Intent Discovery for Conversational Text

train / existing_ai_reference

### problem

- Cũ: predefined set of known categories [A1]
- Cuối: Existing research for intent discovery model it as a classification task with a predefined set of known categories [A1]
- Lý do: Giữ cả chủ thể intent discovery và giới hạn vào predefined categories; tên category đơn lẻ chưa mô tả hạn chế.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: open intent discovery [A2]; tagging the intent [A4]
- Cuối: open intent discovery [T0]
- Lý do: Open intent discovery là mục tiêu; tagging intent là bước của cách giải hai giai đoạn, không phải mục tiêu độc lập. Giữ tên task theo title.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: bidirectional LSTM [A5]; CRF [A5]; Self-attention [A6]; adversarial training [A7]
- Cuối: bidirectional LSTM [A5]; CRF [A5]; Self-attention [A6]; adversarial training [A7]; two-stage approach to this task - predicting whether an utterance contains an intent, and then tagging the intent in the input utterance [A4]
- Lý do: Giữ nguyên nhãn cũ sau khi kiểm tra vai trò, dẫn chứng và các ý có thể thiếu trong nguồn. Rà độc lập: The independent pass included the explicit two-stage predict-intent/tag-intent procedure. The provisional components are valid; decide whether this pipeline is an independently useful procedure or a redundant parent label. This is granularity/coverage, not an unsupported claim.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: two-stage approach [A4]; dataset of 25k real-life utterances [A8]
- Cuối: open intent discovery [A2]; two-stage approach [A4]; dataset of 25k real-life utterances that have been labelled via crowd sourcing [A8]; Our experiments across different domains and real-world datasets show the effectiveness of our approach, with less than 100 annotated examples needed per unique domain to recognize diverse intents [A4,A9]; The approach outperforms state-of-the-art baselines by 5-15% F1 score points [A4,A10]
- Lý do: Giữ hai artifact cũ; thêm định nghĩa task mới và hai finding A9/A10. Finding giữ ngưỡng dưới 100 ví dụ mỗi domain và 5–15% F1 so với baseline. Rà độc lập: The two findings use our/the approach, which is the two-stage discovery pipeline in A4. Add A4 to each finding's evidence so the reported threshold and F1 comparison have an explicit approach antecedent.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P000905 — Identifying Appropriate Support for Propositions in Online User Comments

train / existing_ai_reference

### problem

- Cũ: arguments lacking proper substantiation and reasoning [A0]
- Cuối: online user comments, which often consist of arguments lacking proper substantiation and reasoning [A0]
- Lý do: Nêu rõ phạm vi online user comments của các lập luận thiếu substantiation/reasoning.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: classifying each proposition [A1]; analyze the adequacy of supporting information [A0]
- Cuối: automatically classifying each proposition as UNVERIFIABLE, VERIFIABLE NONEXPERIENTIAL, or VERIFIABLE EXPERIENTIAL2 [A1]
- Lý do: Gộp mục tiêu khái quát adequacy vào thao tác phân lớp với các lớp nguồn nêu. Không tạo thêm task cha trùng.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: Support Vector Machine [A3]; n-grams [A3]; verifiability and experientiality [A3]
- Cuối: SVM [A3]; n-grams [A3]; additional features capturing the verifiability and experientiality [A3]
- Lý do: SVM là acronym được A3 định nghĩa, không phải phương pháp mới khác Support Vector Machine. Feature ghi rõ vai trò capturing verifiability/experientiality.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: goldstandard dataset of 9,476 sentences and clauses [A3]; framework for automatically classifying each proposition [A1]
- Cuối: framework for automatically classifying each proposition as UNVERIFIABLE, VERIFIABLE NONEXPERIENTIAL, or VERIFIABLE EXPERIENTIAL2 [A1]; goldstandard dataset of 9,476 sentences and clauses from 1,047 comments submitted to an eRulemaking platform [A3]; Support Vector Machine (SVM) classifiers trained with n-grams and additional features capturing the verifiability and experientiality exhibit statistically significant improvement over the unigram baseline, achieving a macro-averaged F1 of 68.99% [A3]
- Lý do: Giữ framework và corpus mới với phạm vi/loại nhãn; thêm finding SVM vượt unigram baseline với macro F1 68.99%, giữ đúng tổ hợp feature.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P001479 — Path-tree: An efficient reachability indexing scheme for large directed graphs

train / existing_ai_reference

### problem

- Cũ: increasingly large number of vertices [A2]; best tradeoff among the labeling size, the query answering time, and the construction time [A2]
- Cuối: how to handle increasingly large number of vertices in real-world graphs [A2]; how to find the best tradeoff among the labeling size, the query answering time, and the construction time [A2]
- Lý do: Giữ hai vấn đề độc lập: xử lý graph rất lớn và cân bằng label size/query time/construction time. Mỗi nhãn giữ động từ hỏi, không chỉ số lượng vertex.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: Reachability query [A0]; dynamic index maintenance [A7]
- Cuối: reachability indexing for large directed graphs [T0]; dynamic index maintenance [A7]
- Lý do: Dùng mục tiêu reachability indexing theo title và giữ dynamic index maintenance độc lập. Rà độc lập: The title's large directed graph setting distinguishes the primary indexing objective; generic reachability indexing loses the scale and graph-direction scope.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: path-tree [A3]; chain-tree [A5]; compression scheme [A6]; incremental update algorithm [A7]
- Cuối: path-tree [A3]; chain-tree [A5]; compression scheme which groups vertices with similar labels together [A6]; incremental update algorithm [A7]
- Lý do: Giữ bốn phương pháp; compression scheme nói rõ nhóm vertex có label tương tự, không thêm kỹ thuật khác.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: path-tree [A3]; chain-tree [A5]; compression scheme [A6]; incremental update algorithm [A7]
- Cuối: path-tree [A3]; chain-tree [A5]; compression scheme which groups vertices with similar labels together to further reduce the labeling size [A6]; efficient incremental update algorithm for dynamic index maintenance [A7]; path-tree can be generalized to chain-tree which theoretically can has smaller labeling cost [A5]
- Lý do: Giữ bốn artifact; mô tả compression/update đủ nghĩa và thêm finding chain-tree có thể có labeling cost nhỏ hơn về lý thuyết, giữ can/theoretically.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P002108 — Characterizing the structural diversity of complex networks across domains

train / existing_ai_reference

### problem

- Cũ: no comprehensive study of network structure [A2]
- Cuối: there is no comprehensive study of network structure across a diverse set of domains in order to explain the structural diversity we observe in the real-world networks [A2]
- Lý do: Giữ phạm vi diverse domains và mục đích giải thích structural diversity của thiếu comprehensive study.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: Characterizing the structural diversity of complex networks [T0]
- Cuối: Characterizing the structural diversity of complex networks across domains [T0]
- Lý do: Khôi phục across domains, điều kiện phân biệt của nghiên cứu.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: partitions of network categories tend to have similar underlying functions [A6]
- Cuối: Our results indicate that there are some partitions of network categories in which networks are hard to distinguish based purely on network structure [A5]; partitions of network categories in which networks are hard to distinguish based purely on network structure tend to have similar underlying functions, constraints and/or generative mechanisms of networks even though networks in the same partition have different origins [A5,A6]; This suggests that the origin of a network, whether it's biological, technological or social, may not necessarily be a decisive factor of the formation of similar network structure [A5,A6,A7]
- Lý do: Khôi phục finding khó phân biệt các nhóm chỉ từ cấu trúc và caveat tend to/even though/may not necessarily của quan hệ cấu trúc với chức năng/nguồn gốc. Rà độc lập: A7 explicitly frames the origin conclusion as 'This suggests'; retain that hedge in addition to may/not/necessarily. A6 'these partitions' needs A5 to identify the hard-to-distinguish partitions. A7's inference is about the result in A6.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P002263 — Beyond Prediction: First Steps Toward Automatic Intervention in MOOC Student Stopout

train / existing_ai_reference

### problem

- Cũ: High attrition rates [A0]; generalizability to new courses [A2]
- Cuối: High attrition rates in massive open online courses (MOOCs) [A0]
- Lý do: High attrition là hạn chế rõ; generalizability chỉ được nêu như yếu tố thiết kế cần khảo sát, chưa có mệnh đề hạn chế độc lập.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: automatic detection of student "stopout" [A0]; dynamic survey intervention [A2]
- Cuối: automatic detection of student "stopout" [A0]; dynamic survey intervention [A2]; exploring important elements of classifier design such as generalizability to new courses [A2]
- Lý do: Giữ nguyên nhãn cũ sau khi kiểm tra vai trò, dẫn chứng và các ý có thể thiếu trong nguồn. Rà độc lập: A2 explicitly enumerates studying classifier-design elements such as generalizability to new courses as a current research objective. It is not a routine training/evaluation step, and is distinct from stopout detection and the intervention task.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: stopout classifier [A1]; control theory [A2]
- Cuối: novel framework inspired by control theory [A2]; dynamic survey intervention [A2]; automatic stopout classifier [A3]
- Lý do: A1 nói khả năng chung của stopout classifiers. Dùng classifier ở A3 gắn kết quả hiện tại, framework control theory và dynamic survey thực sự đã làm ở A2.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: framework inspired by control theory [A2]; higher response rates [A3]
- Cuối: novel framework inspired by control theory [A2]; Our results suggest that surveying students based on an automatic stopout classifier achieves higher response rates compared to traditional post-course surveys, and may boost students' propensity to "come back" into the course [A3]
- Lý do: Không giữ higher response rates đơn lẻ: khôi phục surveying dựa classifier, đối chứng post-course surveys, results suggest và may boost return propensity.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P003166 — CASME database: A dataset of spontaneous micro-expressions collected from neutralized faces

train / existing_ai_reference

### task

- Cũ: micro-expression detection and recognition [A3]
- Cuối: create a database of spontaneous micro-expressions which were elicited from neutralized faces [A4]
- Lý do: Mục tiêu bài hiện tại là tạo database micro-expressions từ neutralized faces; detection/recognition ở A3 là động cơ/lĩnh vực nền.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: Action units [A8]; participants' self-report [A9]; procedure in lab situations [A5]
- Cuối: procedure in lab situations to elicit spontaneous micro-expressions [A5]; Action units (AUs) were marked to give an objective and accurate description of the facial movements [A8]; Emotions were labeled based on psychological studies and participants' self-report to enhance the validity [A9]; first, peak and last frames were tagged [A7]
- Lý do: Giữ thủ tục elicitation và annotation. Action units/self-report phải gắn hành động đánh dấu/gán emotion, không chỉ tên input/người cung cấp. Rà độc lập: The elicitation, AU marking and emotion labeling are covered, but the independent temporal annotation procedure in A7 is absent.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: database of spontaneous micro-expressions [A4]; 195 micro-expressions [A6]
- Cuối: CASME [T0]; effective procedure in lab situations to elicit spontaneous micro-expressions [A5]
- Lý do: CASME là artifact database được giới thiệu, đối chiếu tên title với A4. 195 micro-expressions là quy mô mẫu, không phải finding độc lập; gộp với artifact thay vì tạo contribution riêng. Rà độc lập: A5 explicitly says the authors designed an effective elicitation procedure. It is a developed operational procedure distinct from the resulting CASME database, so the current contribution facet omits a source-supported artifact.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P003168 — Domain adaptation for semantic role labeling in the biomedical domain.

train / existing_ai_reference

### problem

- Cũ: manually annotated training instances, which are rare and expensive [A2]
- Cuối: state-of-the-art SRL relies on manually annotated training instances, which are rare and expensive to prepare [A2]
- Lý do: Giữ rõ SRL phụ thuộc instance gán nhãn thủ công hiếm và tốn chi phí.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: semantic role labeling [A0]; domain adaptation [A3]
- Cuối: SRL for the biomedical domain [A3]; evaluate the performance of three recently proposed domain adaptation algorithms for SRL [A4]
- Lý do: SRL trong biomedical domain và đánh giá ba adaptation algorithms là mục tiêu nghiên cứu; domain adaptation là cách làm, không phải task chung chung.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: domain adaptation algorithms [A4]
- Cuối: domain adaptation [A3]; BioKIT [A7]
- Lý do: Domain adaptation thực sự áp dụng ở A3; BioKIT là hệ thống hiện tại thực hiện SRL ở A7, có thể đồng thời thuộc contribution.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### dataset

- Cũ: BioProp [A10]
- Cuối: []
- Lý do: BioProp chỉ được nêu availability ở A10. Chưa có câu chứng minh dùng/giới thiệu trong nghiên cứu; tạm [] và giữ pending, không khẳng định reference cũ sai thực tế.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: BioKIT [A7]; 97% of the performance with as little as 60 annotated target domain abstracts [A6]
- Cuối: BioKIT [A7]; by using domain adaptation, the cost of developing an SRL system for the biomedical domain can be reduced significantly [A5]
- Lý do: Giữ BioKIT; finding 97% cần cả Using domain adaptation và hệ thống/60 abstracts. Thêm finding giảm chi phí, không đổi can thành khẳng định tuyệt đối. Rà độc lập: A6 reports 97% 'of the performance' without stating the comparator/denominator anywhere in the supplied title/abstract. Exact copying preserves the source's gap rather than establishing a fully interpretable quantitative comparison. Suspend this item from asserted labels and keep its exact quote pending a versioned source-completeness decision; do not fill the denominator from external full text.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P003611 — Recognizing Insufficiently Supported Arguments in Argumentative Essays

train / existing_ai_reference

### problem

- Cũ: no empirical studies on its applicability [A2]
- Cuối: Although this criterion, known as sufficiency, is widely adopted in argumentation theory, there are no empirical studies on its applicability to real arguments [A2]
- Lý do: Khôi phục chủ thể sufficiency criterion và real arguments; no empirical studies on its applicability thiếu antecedent.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: identifying insufficiently supported arguments [A4]; assessing the quality of natural language arguments [A0]
- Cuối: automatically identifying insufficiently supported arguments [A4]
- Lý do: Giữ thao tác identify insufficiently supported arguments; đánh giá chất lượng natural-language arguments là mục tiêu cha cùng việc này.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: novel annotated corpus [A3]; human annotators substantially agree on the sufficiency criterion [A3]
- Cuối: novel annotated corpus [A3]; annotation guideline [A5]; human annotators substantially agree on the sufficiency criterion [A3]; we experiment with feature-rich SVMs and convolutional neural networks and achieve 84% accuracy for automatically identifying insufficiently supported arguments [A4]
- Lý do: Giữ corpus và đồng thuận sufficiency; thêm annotation guideline được phát hành và finding accuracy 84% với SVM/CNN ở A4.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P003628 — Active learning-based information structure analysis of full scientific articles and two applications for biomedical literature review.

train / existing_ai_reference

### problem

- Cũ: substantial labeled data that are expensive to develop [A1]; high linguistic and informational complexity [A3]
- Cuối: most existing approaches rely on supervised machine learning (ML) and substantial labeled data that are expensive to develop and apply to different sub-fields of biomedicine [A1]; minimal supervision is sufficient for fairly accurate information structure analysis of biomedical abstracts; however, is it realistic for full articles given their high linguistic and informational complexity? [A2,A3]
- Lý do: Giữ chi phí dữ liệu/supervised approaches. A2+A3 cho phép giữ nguyên câu hỏi chuyển minimal supervision từ abstracts sang full articles mà không bỏ antecedent hoặc biến câu hỏi thành sự thật.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: information structure analysis [A2]; question answering [A5]; summarization [A5]
- Cuối: information structure analysis of full scientific articles [T0]; question answering [A5]; summarization [A5]
- Lý do: Giữ bối cảnh full scientific articles trong task chính; QA và summarization là hai ứng dụng được thực hiện.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: active learning [A4]; Support Vector Machines [A4]; Argumentative Zoning [A4]
- Cuối: active learning [A4]; SVM [A4]; AZ [A4]
- Lý do: SVM và AZ đều được định nghĩa trực tiếp tại A4. Mỗi tên đầy đủ/acronym chỉ một phương pháp, không nhân đôi.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: novel corpus of 50 biomedical articles [A4]; two novel applications [A5]; biomedical researchers find relevant information significantly faster [A7]
- Cuối: novel corpus of 50 biomedical articles annotated according to the Argumentative Zoning (AZ) scheme [A4]; two novel applications that use AZ to support real-life literature review in biomedicine via question answering and summarization [A5]; active learning with SVM trained on 500 labeled sentences (6% of the corpus) performs surprisingly well with the accuracy of 82%, just 2% lower than fully supervised learning [A6]; In our question answering task, biomedical researchers find relevant information significantly faster from AZ-annotated than unannotated articles [A7]; In the summarization task, sentences extracted from particular zones are significantly more similar to gold standard summaries than those extracted from particular sections of full articles [A8]; our AZ classifier [A10]
- Lý do: Giữ corpus và hai ứng dụng với chức năng; khôi phục finding 500 sentences/6%/82%/kém 2% supervised và finding zone-based summaries so với sections. Finding QA giữ AZ-annotated vs unannotated. Rà độc lập: A10 releases an AZ classifier distinct from the annotated corpus and two applications. A7/A8 findings should keep their explicit QA/summarization experimental scopes.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P004028 — What Your Face Vlogs About: Expressions of Emotion and Big-Five Traits Impressions in YouTube

train / existing_ai_reference

### task

- Cũ: automatic personality impression prediction [A5]
- Cuối: study of the connections between automatically extracted facial expressions of emotion and impressions of Big-Five personality traits in YouTube vlogs [A2]; automatic personality impression prediction [A5]
- Lý do: Bổ sung mục tiêu nghiên cứu quan hệ facial expressions và Big-Five impressions ở A2, đồng thời giữ prediction đã thực hiện.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: Computer Expression Recognition Toolbox [A3]; behavioral cues [A4]; correlation analysis [A5]
- Cuối: CERT [A3]; four sets of behavioral cues that characterize face statistics and dynamics in a compact way [A4]; correlation analysis [A5]
- Lý do: CERT là alias được A3 định nghĩa. Behavioral cues giữ số bốn nhóm và face statistics/dynamics để phân biệt; correlation analysis giữ nguyên.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: four sets of behavioral cues [A4]; significantly predict Extraversion impressions [A6]
- Cuối: four sets of behavioral cues that characterize face statistics and dynamics in a compact way [A4]; Using a dataset of 281 vloggers, the study shows that while multiple facial expression cues have significant correlation with several of the Big-Five traits, they are only able to significantly predict Extraversion impressions with moderate values of R2 [A6]
- Lý do: Không giữ significantly predict Extraversion đơn lẻ. Khôi phục while correlation for several traits, only predict Extraversion, moderate R2 và bối cảnh 281 vloggers.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P000271 — Morpheme Boundaries within Words: Report on a Computer Test

train / additional_ai_reference

### problem

- Cũ: we need a test for determining what are the morphemes of a language, or at least a test that would tentatively segment a phonemic sequence (as a sentence) into morphemes, leaving it for a distributional criterion to decide which of these tentative segments are to be accepted as morphemes [A5]
- Cuối: we need a test for determining what are the morphemes of a language [A5]
- Lý do: Câu A5 cũ gồm cả mục tiêu/phương án phân đoạn và tiêu chuẩn hậu xử lý. Giữ nhu cầu test xác định morphemes làm problem, không ép toàn bộ câu vào một nhãn.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: Morpheme Boundaries within Words [T0]
- Cuối: tentatively segment a phonemic sequence (as a sentence) into morphemes [A5]
- Lý do: Nguồn A5 cho thao tác segment phonemic sequence into morphemes; cụ thể hơn chủ đề Morpheme Boundaries trong title.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P000501 — Cache-Oblivious Peeling of Random Hypergraphs

train / additional_ai_reference

### contribution

- Cũ: Cache-Oblivious Peeling of Random Hypergraphs [T0]; algorithm requires $O(\mathrm{sort}(n))$ I/Os and $O(n \log n)$ time to peel a random hypergraph with $n$ edges [A3]; our algorithm builds a MPHF of $7.6$ billion keys in less than $21$ hours on a single machine [A4]; resulting data structure is both more space-efficient and faster than that obtained with the current state-of-the-art MPHF construction for large-scale key sets [A5]
- Cuối: Cache-Oblivious Peeling of Random Hypergraphs [T0]; algorithm requires $O(\mathrm{sort}(n))$ I/Os and $O(n \log n)$ time to peel a random hypergraph with $n$ edges [A3]; our algorithm builds a MPHF of $7.6$ billion keys in less than $21$ hours on a single machine [A4]; resulting data structure is both more space-efficient and faster than that obtained with the current state-of-the-art MPHF construction for large-scale key sets [A4,A5]
- Lý do: Nhãn artifact theo title và ba finding/complexity cũ đều có căn cứ, giữ nguyên. Không mặc định bản blind tốt hơn reference cũ. Rà độc lập: A5's resulting data structure is the MPHF built in A4. Add A4 to ground the comparison's subject; the comparative wording itself is valid.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P001002 — Semantic Composition and Decomposition: From Recognition to Generation

train / additional_ai_reference

### method

- Cũ: distributional approach to semantics [A2]; context vector [A2]; fast unsupervised learning algorithm [A9]; slower supervised learning algorithm [A9]
- Cuối: distributional approach to semantics [A2]; fast unsupervised learning algorithm [A9]; slower supervised learning algorithm [A9]
- Lý do: Context vector là cách biểu diễn của chính distributional approach, chưa phải một kỹ thuật độc lập thêm. Giữ approach và hai thuật toán unsupervised/supervised.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P001234 — GeoTextTagger: High-Precision Location Tagging of Textual Documents using a Natural Language Processing Approach

train / additional_ai_reference

### method

- Cũ: GeoTextTagger [T0]; part-of-speech tagger [A2]; named entity recognizer [A2]; distance-based scores [A4]; repeatedly selecting the location and block with the best score [A4]; Spark framework for data analytics [A10]
- Cuối: GeoTextTagger [T0]; part-of-speech tagger [A2]; named entity recognizer [A2]; assigning distance-based scores to each location and repeatedly selecting the location and block with the best score [A4]; Spark framework for data analytics [A10]
- Lý do: Giữ GeoTextTagger, POS tagger, NER và Spark. Distance scoring/repeated best-score selection là một thủ tục chọn location, gộp thành nhãn có đủ hành động và đối tượng.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P001353 — Effective deep learning-based multi-modal retrieval

train / additional_ai_reference

### method

- Cũ: stacked auto-encoders [A5]; deep convolutional neural network [A5]; neural language model [A5]; mini-batches [A7]; adjust the mapping functions continuously for each batch [A7]
- Cuối: stacked auto-encoders [A5]; deep convolutional neural network [A5]; neural language model [A5]; mini-batches [A7]; general learning objective that effectively captures both intramodal and intermodal semantic relationships of data from heterogeneous sources [A4,A5]
- Lý do: Giữ ba kỹ thuật neural độc lập. Mini-batch và cập nhật mapping mỗi batch là một thủ tục training, giữ mini-batches, bỏ nhãn bước phụ trùng. Không loại batching chỉ vì không phải tên mô hình. Rà độc lập: The general learning objective capturing intra/intermodal semantic relationships is developed and operationally used to realize both algorithms in A4/A5. It can be retained as a method in addition to its contribution role; omission may instead be a deliberate granularity choice.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: general learning objective that effectively captures both intramodal and intermodal semantic relationships of data from heterogeneous sources [A4]; unsupervised approach that uses stacked auto-encoders and requires minimum prior knowledge on the training data [A5]; supervised approach using deep convolutional neural network and neural language model [A5]; training algorithms are memory efficient with respect to the data volume [A6]; proposed methods achieve significant improvement in search accuracy over the state-of-the-art solutions [A8]
- Cuối: general learning objective that effectively captures both intramodal and intermodal semantic relationships of data from heterogeneous sources [A4]; unsupervised approach that uses stacked auto-encoders and requires minimum prior knowledge on the training data [A5]; supervised approach using deep convolutional neural network and neural language model [A5]; Our training algorithms are memory efficient with respect to the data volume [A6]; Experimental results on three real datasets demonstrate that our proposed methods achieve significant improvement in search accuracy over the state-of-the-art solutions [A8]
- Lý do: Giữ ba artifact/proposal. Hai finding viết đủ chủ thể và giới hạn kết luận vào thử nghiệm trên ba dataset; đây chủ yếu là làm rõ cách trình bày, không tự coi nhãn cũ là sai thực tế.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P002666 — On minimum spanning tree-like metric spaces

train / additional_ai_reference

### contribution

- Cũ: if a spanning tree representation, $T$, of $M$ exists, then it is isomorphic to the unique minimum spanning tree in the weighted complete graph associated with $M$ [A2]; fourth-point condition that is necessary and sufficient to ensure the existence of $T$ whenever each distance in $M$ is unique [A2]; a finite median graph, in which each geodesic distance is distinct, is simply a tree [A3]; Provided that the tie-breaking assumption holds, the fourth-point condition serves as a criterion for measuring the goodness-of-fit of the minimum spanning tree to $M$, i.e., the spanning tree-likeness of $M$ [A4]; These quantities can be measured in $O(n^4)$ and $O(n^3)$ time, respectively [A6]
- Cuối: fourth-point condition that is necessary and sufficient to ensure the existence of $T$ whenever each distance in $M$ is unique [A2]; if a spanning tree representation, $T$, of $M$ exists, then it is isomorphic to the unique minimum spanning tree in the weighted complete graph associated with $M$ [A2]; a finite median graph, in which each geodesic distance is distinct, is simply a tree [A3]; Provided that the tie-breaking assumption holds, the fourth-point condition serves as a criterion for measuring the goodness-of-fit of the minimum spanning tree to $M$, i.e., the spanning tree-likeness of $M$ [A4]; Provided that the tie-breaking assumption holds, spanning tree-likeness of $M$, spanning path-likeness of $M$ can be measured in $O(n^4)$ and $O(n^3)$ time, respectively [A4,A5,A6]
- Lý do: Bốn theorem/artifact cũ được giữ về nghĩa. A6 These quantities cần A4+A5 để gắn spanning tree/path-likeness với O(n^4)/O(n^3), giữ respectively và điều kiện tie-breaking. Không suy ra hai độ phức tạp có thể hoán đổi.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P002811 — The EcoLexicon Semantic Sketch Grammar: from Knowledge Patterns to Word Sketches

train / additional_ai_reference

### task

- Cũ: extract KRCs codifying generic-specific, part-whole, location, cause and function relations [A4]; evaluation with refinement purposes [A6]
- Cuối: extract KRCs codifying generic-specific, part-whole, location, cause and function relations [A4]; precision and recall evaluation of the 64 English sketch grammar rules created so far for hyponymy, meronymy and causality [A7]
- Lý do: Evaluation with refinement purposes cần đối tượng và thước đo: precision/recall của 64 English rules về hyponymy/meronymy/causality.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: KP-based EcoLexicon Semantic SketchGrammar (ESSG) [A2]; Sketch Engine [A2]; word sketches [A5]; shallow precision and recall evaluation [A7]; random sample of concordances extracted from each word sketch type [A8]; random sample of concordances where known term pairs are found [A9]
- Cuối: ESSG [A2]; Sketch Engine [A2]; random sample of concordances extracted from each word sketch type [A8]; random sample of concordances where known term pairs are found [A9]
- Lý do: ESSG là tên được định nghĩa ở A2. Word sketches là representation đầu ra, không thêm kỹ thuật độc lập. Shallow precision/recall là mục đích đo đã thể hiện trong task; giữ hai thủ tục random sampling làm method.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: KP-based EcoLexicon Semantic SketchGrammar (ESSG) [A2]; reusing the ESSG in any English corpus uploaded by the user enables Sketch Engine to extract KRCs codifying generic-specific, part-whole, location, cause and function relations, because most of the KPs are domain-independent [A4]; noise of false positives helped to further specify the rules, whereas the silence of false negatives allows us to find useful new patterns [A11]
- Cuối: ESSG [A2]; reusing the ESSG in any English corpus uploaded by the user enables Sketch Engine to extract KRCs codifying generic-specific, part-whole, location, cause and function relations, because most of the KPs are domain-independent [A4]; noise of false positives helped to further specify the rules, whereas the silence of false negatives allows us to find useful new patterns [A11]
- Lý do: Giữ cùng artifact ESSG, khả năng reuse trên English corpus và finding false positives/negatives giúp refinement. Chỉ chuẩn hóa tên artifact; không tự coi các finding cũ là thiếu căn cứ.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P003056 — Put It Back: Entity Typing with Language Model Enhancement

train / additional_ai_reference

### method

- Cũ: entity typing with language model enhancement [A2]; language model to measure the compatibility between context sentences and labels [A3]
- Cuối: entity typing with language model enhancement [A2]
- Lý do: Language model đo compatibility chính là cách thực hiện entity typing with language model enhancement, gộp thành một kỹ thuật thay vì model cha và mô tả thành phần trùng.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: entity typing with language model enhancement [A2]; our method is capable of enhancing the entity typing model with information from the language model, and significantly outperforms the stateof-the-art baseline [A4]; Code and data [A5]
- Cuối: entity typing with language model enhancement [A2]; Experiments on benchmark datasets demonstrate that our method is capable of enhancing the entity typing model with information from the language model, and significantly outperforms the stateof-the-art baseline [A4]; Code [A5]; data [A5]
- Lý do: Giữ artifact và Code and data được bài cung cấp; finding giữ phạm vi experiments on benchmark datasets. Không suy ra acronym LME hay tên dataset từ URL hỏng. Rà độc lập: Code and data are two released artifacts in A5. Splitting them follows the independent-artifact unit rule, but preserves the same factual content; the broken URL must remain irrelevant to naming.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P003918 — Modeling Narrative Discourse

train / additional_ai_reference

### task

- Cũ: formal modeling of narrative discourse [A0]; find similarities and analogies between encoded stories [A8]
- Cuối: formal modeling of narrative discourse [A0]; find similarities and analogies between encoded stories based on the proposed relations [A8]
- Lý do: Task similarity/analogy giữ đối tượng encoded stories và cơ sở proposed relations; giữ task formal modeling narrative discourse.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: isolating and analyzing these networks [A3]; discourse relations that are specific to narrative [A4]; theory-of-mind interpretation [A5]; agentive characters [A5]; goals [A5]; plans [A5]; beliefs [A5]; time [A5]; software system [A6]
- Cuối: first approach considers the conversational networks to be found in literary fiction as a key aspect of discourse coherence; by isolating and analyzing these networks [A3]; new set of discourse relations that are specific to narrative [A4]
- Lý do: Giữ hai approach: conversational-network analysis và narrative discourse relations. Agentive characters/goals/plans/beliefs/time là khía cạnh của representation, không năm thuật toán; generic software implementation không thêm method độc lập.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: approach considers the conversational networks to be found in literary fiction as a key aspect of discourse coherence [A3]; new set of discourse relations that are specific to narrative [A4]; discourse relations are expressive, formal, robust, and through the use of a software system, amenable to corpus collection projects through the use of trained annotators [A6]; collection of over 100 encodings, covering a set of fables as well as longer texts including literary fiction and epic poetry [A7]; evaluation of this technique shows that human raters prefer such a measure of similarity to a more traditional one based on the semantic distances between story propositions [A8]
- Cuối: approach considers the conversational networks to be found in literary fiction as a key aspect of discourse coherence [A3]; new set of discourse relations that are specific to narrative [A4]; collection of over 100 encodings, covering a set of fables as well as longer texts including literary fiction and epic poetry [A7]; discourse relations that are specific to narrative are expressive, formal, robust, and through the use of a software system, amenable to corpus collection projects through the use of trained annotators [A4,A6]; We are able to inferentially find similarities and analogies between encoded stories based on the proposed relations, and an evaluation of this technique shows that human raters prefer such a measure of similarity to a more traditional one based on the semantic distances between story propositions [A8]
- Lý do: Phục hồi contribution conversational-network approach hợp lệ mà blind bỏ sót. Giữ corpus encoding, tính chất discourse relations và finding human raters prefer; không đổi preference thành khách quan tốt hơn. Rà độc lập: A6 'these discourse relations' refers to the new narrative-specific relations introduced in A4; include that sentence so the finding's subject is evidenced.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P004191 — Prediction of guide strand of microRNAs from its sequence and secondary structure

train / additional_ai_reference

### method

- Cũ: support vector machine (SVM) models [A3]; five fold cross validation [A4]; mono-, di-, and tri-nucleotide composition [A5]; split nucleotide composition [A6]; binary pattern [A7]; secondary structure features [A8]; hybrid models [A9]; various siRNA-designing methods [A11]
- Cuối: SVM [A3]; mono-, di-, and tri-nucleotide composition [A5]; split nucleotide composition [A6]; binary pattern [A7]; integrating the secondary structure features with binary pattern [A8]; hybrid models [A9]; five fold cross validation [A4]
- Lý do: SVM được định nghĩa trong A3; giữ các feature family thực sự thử, cross-validation và hybrid. Various siRNA-designing methods ở A11 chỉ làm baseline so sánh, loại khỏi method của mô hình mới; secondary structure + binary pattern là phương án kết hợp.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: support vector machine (SVM) models developed for predicting the guide strands of miRNAs [A3]; web server [A15]; models were developed using mono-, di-, and tri-nucleotide composition of miRNA strands and achieved the highest accuracies of 0.588, 0.638 and 0.596 respectively [A5]; models were developed using split nucleotide composition and achieved maximum accuracies of 0.553, 0.641 and 0.602 for mono-, di-, and tri-nucleotide respectively [A6]; models were developed using binary pattern and achieved the highest accuracy of 0.708 [A7]; when integrating the secondary structure features with binary pattern, an accuracy of 0.719 was seen [A8]; hybrid models were developed by combining various features and achieved maximum accuracy of 0.799 with sensitivity 0.781 and specificity 0.818 [A9]; performance of this model was tested on an independent dataset that achieved an accuracy of 0.80 [A10]; guide and passenger strand of miRNA precursors can be distinguished using their nucleotide sequence and secondary structure [A13]
- Cuối: support vector machine (SVM) models developed for predicting the guide strands of miRNAs [A3]; web server [A15]; models were developed using mono-, di-, and tri-nucleotide composition of miRNA strands and achieved the highest accuracies of 0.588, 0.638 and 0.596 respectively [A5]; models were developed using split nucleotide composition and achieved maximum accuracies of 0.553, 0.641 and 0.602 for mono-, di-, and tri-nucleotide respectively [A6]; models were developed using binary pattern and achieved the highest accuracy of 0.708 [A7]; when integrating the secondary structure features with binary pattern, an accuracy of 0.719 was seen [A8]; hybrid models were developed by combining various features and achieved maximum accuracy of 0.799 with sensitivity 0.781 and specificity 0.818 [A9]; guide and passenger strand of miRNA precursors can be distinguished using their nucleotide sequence and secondary structure [A13]; hybrid model tested on an independent dataset achieved an accuracy of 0.80 [A9,A10]
- Lý do: Giữ artifact SVM models cho guide-miRNA, server và mọi kết quả composition/binary/hybrid/secondary structure. Ghép A9+A10 để thay this model bằng hybrid model trong accuracy 0.80 trên independent set; liên kết đại từ là quyết định ngữ nghĩa cần reviewer kiểm tra, không do schema chứng minh.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P000779 — Totalitarian Language: Orwell's Newspeak and Its Nazi and Communist Antecedents

dev / existing_ai_reference

### task

- Cũ: examines the manipulation of language [A0]; evaluates the extent to which thought control succeeded [A7]
- Cuối: examines the manipulation of language by Nazi and Communist regimes [A0]; evaluates the extent to which thought control succeeded under the Nazi and Soviet regimes [A7]
- Lý do: Giữ hai mục tiêu nhưng nêu rõ Nazi/Communist và Nazi/Soviet regimes, không diễn đạt thành đánh giá mọi chế độ/toàn bộ ngôn ngữ.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: analysis of the speeches and writings [A4]
- Cuối: analysis of the speeches and writings of actual dictators, particularly in Nazi Germany and the Soviet Union [A4]
- Lý do: Textual analysis giữ speeches/writings của actual dictators và phạm vi Nazi Germany/Soviet Union.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: language of actual totalitarian regimes was not nearly so successful [A5]; counterlanguages [A6]
- Cuối: Young's analysis of the speeches and writings of actual dictators, particularly in Nazi Germany and the Soviet Union, reveals a similar propagandistic structure in the use, or misuse, of language, the purpose of which was to enslave and control the populace [A4]; Young's analysis of the effects of these languages on the subjects of totalitarian dictatorships reveals that although Orwell's Newspeak was a potent instrument of control over the thought and behaviour of the citizens, the language of actual totalitarian regimes was not nearly so successful [A5]; When official rhetoric and reality did not agree, the skepticism and cynicism of the people gave rise to the phenomenon of counterlanguages that attempted to reinscribe the reality of life under dictorial rule [A6]
- Lý do: Khôi phục propagandistic structure finding; mức thành công phải giữ đối chiếu Orwell Newspeak với actual regimes và phủ định not nearly. Counterlanguages giữ điều kiện rhetoric khác reality và phản ứng skepticism/cynicism.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P001080 — Detecting changes in student behavior from clickstream data

dev / existing_ai_reference

### problem

- Cũ: noisy and complex nature of this data [A1]
- Cuối: given the noisy and complex nature of this data, an on-going challenge involves devising statistical techniques that capture clear and meaningful aspects of students' click patterns [A1]
- Lý do: Noise/complexity phải gắn thách thức xây kỹ thuật thống kê rút rõ click patterns, không chỉ hai tính từ.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: Detecting changes in student behavior [T0]
- Cuối: Detecting changes in student behavior from clickstream data [T0]
- Lý do: Giữ nguồn clickstream data trong task phát hiện thay đổi hành vi.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: detect when students change their previewing and reviewing behavior [A3]
- Cuối: statistical change detection techniques using clickstream data from two large university courses, one face-to-face and one online, can be used to detect when students change their previewing and reviewing behavior, and how these changes can be related to other aspects of students' activity and performance [A2,A3]
- Lý do: Finding giữ hai course, một face-to-face/một online, preview/review behavior và quan hệ activity/performance. Không tuyên bố hiệu quả trên mọi course. Rà độc lập: A3 'this methodology' is statistical change detection introduced in A2. Keep A2 with A3 rather than a sentence-local unidentified methodology.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P001150 — From Isolation to Radicalization: Anti-Muslim Hostility and Support for ISIS in the West

dev / existing_ai_reference

### problem

- Cũ: What explains online radicalization and support for ISIS [A0]
- Cuối: What explains online radicalization and support for ISIS in Europe [A0]
- Lý do: Giữ Europe trong câu hỏi nghiên cứu theo A0.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: predicts support for ISIS on Twitter [A5]
- Cuối: test whether the intensity of anti-Muslim hostility at the local (neighborhood/municipality) level predicts support for ISIS on Twitter [A5]
- Lý do: Giữ cấu trúc test whether và bối cảnh local/neighborhood/municipality, predictor anti-Muslim hostility, outcome support for ISIS on Twitter. Không biến kiểm tra liên hệ thành chứng minh nhân quả.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: matched online radicalization indicators with offline data [A5]; analysis of high-frequency data [A7]
- Cuối: matched online radicalization indicators with offline data on vote share for far-right, anti-Muslim political parties [A5]; analysis of high-frequency data surrounding events that stir anti-Muslim hostility [A7]
- Lý do: Nêu rõ offline vote share cho far-right/anti-Muslim parties và high-frequency events làm đối tượng hai phân tích.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: local-level support for far-right parties is a significant and substantively meaningful predictor of online radicalization [A6]
- Cuối: Results show that local-level support for far-right parties is a significant and substantively meaningful predictor of online radicalization, including posting tweets sympathizing with ISIS, describing life in ISIS-controlled territories, discussing foreign fighters, and expressing anti-West sentiment [A6]; Results show that local-level support for far-right parties is a significant and substantively meaningful predictor of online radicalization. An analysis of high-frequency data surrounding events that stir anti-Muslim hostility, such as terrorist attacks and anti-Muslim protests in Europe, shows the same pattern [A6,A7]
- Lý do: Giữ predictor, không đổi thành cause; các dạng online radicalization trong A6 làm rõ outcome, phạm vi local-level được giữ. Rà độc lập: A7 reports corroboration of the observed pattern using high-frequency event data, a distinct reported finding beyond the A6 local-level predictor result. Preserve the observational claim and antecedent; do not turn it into causation.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P001394 — Towards Web Spam Filtering Using a Classifier Based on the Minimum Description Length Principle

dev / existing_ai_reference

### problem

- Cũ: curse of dimensionality [A2]; very high computational cost [A2]; overfitting [A3]
- Cuối: Despite different machine learning approaches have been used to detect web spam, many of them suffer with the curse of dimensionality or require a very high computational cost impeding their employment in real scenarios [A2]; there is still a big effort to develop more advanced methods that at the same time are able to prevent overfitting and fast to learn [A3]
- Lý do: Gắn curse of dimensionality/cost với machine-learning spam detectors và thực tế triển khai; thêm unresolved requirement prevent overfitting/learn fast thay vì nhãn overfitting rời.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: minimum description length principle [A4]; ensemble of predictions [A8]; content-based, link-based, and transformed link-based features [A6]
- Cuối: MDLClass [A4]; combines the predictions obtained by the classifiers using content-based, link-based, and transformed link-based features [A6]
- Lý do: MDLClass là tên classifier hiện tại. MDL principle là nền tảng cùng classifier, không thêm một method cha trùng. Ensemble và các feature types mô tả một thủ tục kết hợp ở A6; giữ nguyên nhóm feature có source suffix chung, chưa coi từng tính từ rời là method.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: MDLClass [A4]; new approach to detect web spam [A6]
- Cuối: MDLClass [A4]; new approach to detect web spam that combines the predictions obtained by the classifiers using content-based, link-based, and transformed link-based features [A6]; The results indicate that the proposed MDLClass and ensemble of predictions using different types of features are promising in the task of web spam filtering [A8]; MDLClass is very efficient, lightweight, multi-class, and fast [A4,A5]
- Lý do: Giữ MDLClass và new ensemble approach với cơ chế, thêm finding promising trong web-spam filtering đúng mức khẳng định của A8. Rà độc lập: A5 explicitly reports the proposed classifier as efficient, lightweight, multi-class and fast. A4 identifies it as MDLClass. This is a source-reported qualitative property, not an independently verified benchmark; optionally retain it rather than replacing it by the weaker and different 'promising' finding.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P001790 — Music Playlist Continuation by Learning from Hand-Curated Examples and Song Features: Alleviating the Cold-Start Problem for Rare and Out-of-Set Songs

dev / existing_ai_reference

### problem

- Cũ: scarcity of thoroughly curated playlists [A4]; bias towards popular songs [A4]; Cold-Start Problem [T0]
- Cuối: the scarcity of thoroughly curated playlists and the bias towards popular songs result in the vast majority of songs occurring in very few playlists and thus being poorly recommended [A4]
- Lý do: Scarcity/bias tạo cùng cold-start mechanism: ít playlist/song dẫn đến poor recommendation; giữ một mệnh đề thay vì ba tên cha/con trùng.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: music playlist generation [A0]; Music Playlist Continuation [T0]
- Cuối: Music Playlist Continuation [T0]
- Lý do: Playlist generation là mô tả cha, continuation là nhiệm vụ cụ thể của paper; giữ continuation một lần.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: song-to-playlist classifier [A5]; song features [A5]
- Cuối: song-to-playlist classifier [A5]; song features derived from audio, social tags and independent listening logs [A5]
- Lý do: Giữ classifier và feature group với ba nguồn audio/social tags/independent listening logs.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: song-to-playlist classifier [A5]; more robust performance when recommending rare and out-of-set songs [A6]
- Cuối: song-to-playlist classifier [A5]; Experiments on two datasets of hand-curated playlists show competitive performance compared to collaborative filtering when sufficient training data is available and more robust performance when recommending rare and out-of-set songs [A6]; song-to-playlist classifier: both approaches achieve a recall@100 of roughly 35% for songs occurring in 5 or more training playists, whereas the proposed model achieves a recall@100 of roughly 15% for songs occurring in 4 or less training playlists, compared to the 3% achieved by collaborative filtering [A5,A7]
- Lý do: Finding robust phải giữ so sánh CF và điều kiện đủ training data/rare/out-of-set. Thêm recall@100 với roughly, ngưỡng 5+ vs 4-or-less, và đúng cặp 35%/15%/3%. Rà độc lập: A7 identifies collaborative filtering and a proposed model, but the subject of 'both approaches' requires A5's song-to-playlist classifier. Add A5; retain the two frequency regimes and approximately 35/15/3 recall values.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P002501 — A Multiword Expression Data Set: Annotating Non-Compositionality and Conventionalization for English Noun Compounds

dev / existing_ai_reference

### problem

- Cũ: Scarcity of multiword expression data sets [A0]; lack of availability of true negative instances [A3]
- Cuối: Scarcity of multiword expression data sets raises a fundamental challenge to evaluating the systems that deal with these linguistic structures [A0]; quality of the annotations, and lack of availability of true negative instances [A3]
- Lý do: Giữ thách thức evaluation từ scarcity; thêm annotation quality và true negatives như vấn đề khác, không nhân đôi scarcity/small sample.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: Annotating Non-Compositionality and Conventionalization [T0]
- Cuối: Annotating Non-Compositionality and Conventionalization for English Noun Compounds [T0]
- Lý do: Nêu đối tượng English Noun Compounds bên cạnh hai chiều non-compositionality/conventionalization.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: annotated by experts [A1]; common statistical measures [A1]
- Cuối: annotated by experts [A1]; validated by common statistical measures [A1]
- Lý do: Annotated by experts là thủ tục annotation, không chỉ người. Common statistical measures giữ hành động validation để rõ vai trò.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: 1048 noun-noun compounds [A2]; large data set annotated by experts [A1]
- Cuối: set of 1048 noun-noun compounds annotated as non-compositional, compositional, conventionalized and not conventionalized [A2]
- Lý do: Hai nhãn cũ cùng nói một dataset. Gộp thành artifact set 1048 noun-noun compounds cùng bốn trạng thái annotation; 1048 compounds đơn lẻ chưa mô tả artifact.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P002633 — Is reflexivity the key to minimising problems of interpretation in phenomenological research?

dev / existing_ai_reference

### problem

- Cũ: problems of interpretation [T0]; avoid assumptions [A3]
- Cuối: problems of interpretation in phenomenological research [T0]
- Lý do: Title nêu rõ problems of interpretation trong phenomenological research. Giữ bối cảnh đó; avoid assumptions là mục tiêu/khuyến nghị của reflexivity, không một hạn chế thứ hai độc lập.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: discuss and demonstrate the use of reflexivity [A0]
- Cuối: discuss and demonstrate the use of reflexivity in interpretive phenomenological analysis [A0]
- Lý do: Giữ use of reflexivity trong interpretive phenomenological analysis, không mở rộng sang mọi loại research.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: reflexivity [A0]; interpretive phenomenological analysis [A0]; reflexive diary [A11]
- Cuối: reflexivity [A0,A7,A10]; reviewed pertinent literature and personal examples of reflexivity in research practice [A7]
- Lý do: Reflexive diary ở A11 là lựa chọn khuyến nghị Nurse researchers may choose, chưa là thủ tục đã thực hiện. IPA là đối tượng thảo luận, không mặc định method đã triển khai. Thêm literature/personal-example review thực sự ở A7. Rà độc lập: A0 alone is an aim; A7/A10 document personal/practical examples actually presented. Include all three and keep advice-only reflexive diary excluded.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: practical examples are offered for using reflexivity [A10]; more rigorous approach [A9]
- Cuối: practical examples are offered for using reflexivity [A10]; Reflexivity is an active process that may, at times, be difficult and probing, but which is crucial to becoming self-aware and thus able to see any influences that could affect data collection or analysis [A8]
- Lý do: Giữ practical examples mà blind bỏ sót; thay more rigorous approach không rõ chủ thể bằng kết luận đầy đủ về reflexivity, giữ may be difficult/probing và ảnh hưởng tới data collection/analysis.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P002993 — Semi-Supervised Multi-Task Word Embeddings

dev / existing_ai_reference

### problem

- Cũ: do not use the available manual labeled datasets [A2]
- Cuối: More recently, unsupervised learning has been used to find a lower-dimensional representation, similar in size to that of the word embeddings within the ensemble. However, these methods do not use the available manual labeled datasets that are often used solely for the purpose of evaluation [A1,A2]
- Lý do: Khôi phục chủ thể methods và available manual labeled datasets thường chỉ được dùng evaluation. Rà độc lập: Replacing 'these methods' by bare 'methods' leaves a generic class of methods. The antecedent is recent unsupervised lower-dimensional ensemble representation learning in A1, not methods generally.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: Siamese Network [A4]; cosine loss [A7]; Brier's loss [A7]; reconstruct an ensemble of pretrained word embeddings [A3]
- Cuối: reconstructing word meta-embeddings [A4]; Siamese Network [A4]; cosine loss for reconstruction [A7]; Brier's loss for word similarity [A7]
- Lý do: Giữ Siamese Network, reconstruction và hai loss; loss cần gắn reconstruction vs word similarity để không hoán đổi chức năng.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: Semi-Supervised Multi-Task Word Embeddings [T0]; performance is improved for all word similarity datasets when compared to unsupervised learning methods with a mean increase of 11.33 in the Spearman Correlation coefficient [A6]
- Cuối: Semi-Supervised Multi-Task Word Embeddings [T0]; performance is improved for all word similarity datasets when compared to unsupervised learning methods with a mean increase of 11.33 in the Spearman Correlation coefficient [A6]; 4 of 6 of word similarity datasets from our approach show best performance when using of a cosine loss for reconstruction and Brier's loss for word similarity [A7]
- Lý do: Giữ tên artifact theo title và finding mean Spearman +11.33; thêm finding 4/6 datasets tốt nhất với đúng tổ hợp cosine/Brier loss.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P003459 — Author Profiling for Hate Speech Detection

dev / existing_ai_reference

### problem

- Cũ: oblivious to user and community information [A2]
- Cuối: The current state-of-the-art approaches to hate speech detection are oblivious to user and community information and rely entirely on textual (i.e., lexical and semantic) cues [A2]
- Lý do: Giữ chủ thể state-of-the-art hate-speech approaches và hạn chế chỉ dựa text, không chỉ oblivious với user/community.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: hate speech detection [A2]
- Cuối: hate speech detection [A4]
- Lý do: A2 là mô tả hệ thống nền; A4 trực tiếp chứng minh paper thực hiện hate-speech detection. Concept không đổi, đổi evidence cho đúng vai trò.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: community-based profiling features [A3]; qualitative analysis [A5]
- Cuối: community-based profiling features of Twitter users [A3]; qualitative analysis of model characteristics [A5]
- Lý do: Giữ Twitter user community profiling features và qualitative analysis of model characteristics; nhãn cũ quá rộng nhưng không thêm kỹ thuật từ ngoài.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: community-based profiling features [A3]
- Cuối: community-based profiling features of Twitter users [A3]; Experimenting with a dataset of 16k tweets, we show that our methods significantly outperform the current state of the art in hate speech detection [A4]; code [A6]; pre-trained models [A6]
- Lý do: Giữ artifact feature approach; thêm finding trên 16k tweets vượt current state of art và các artifact code/pre-trained models được release ở A6. Không gọi mọi resource đã dùng là resource mới.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P004198 — Correlation and variable importance in random forests

dev / existing_ai_reference

### problem

- Cũ: highly correlated predictors [A1]
- Cuối: In high-dimensional regression or classification frameworks, variable selection is a difficult task, that becomes even more challenging in the presence of highly correlated predictors [A1]
- Lý do: Highly correlated predictors chỉ là setting; thêm variable selection khó hơn trong high-dimensional regression/classification.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: variable selection [A0]
- Cuối: variable selection with the random forests algorithm in presence of correlated predictors [A0]
- Lý do: Giữ variable selection bằng random forests với correlated predictors, điều kiện chính của paper.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: random forests [A0]; Recursive Feature Elimination [A4]; permutation importance [A2]
- Cuối: random forests algorithm [A0]; permutation importance measure [A2]; RFE [A4]; simulation experiments [A6]
- Lý do: RFE được A4 định nghĩa nên dùng acronym một lần; giữ random forests/permutation importance và thêm simulation experiments thực sự mô tả ở A6.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### dataset

- Cũ: Landsat Satellite [A7]; UCI Machine Learning Repository [A7]
- Cuối: Landsat Satellite data [A7]
- Lý do: Landsat Satellite data là dataset cụ thể; UCI Machine Learning Repository là nơi lấy cùng dataset, không một dataset thứ hai.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: theoretical study of the permutation importance measure [A2]; efficiency of the RFE algorithm for selecting a small number of variables together with a good prediction error [A6]
- Cuối: theoretical study of the permutation importance measure for an additive regression model [A2]; various simulation experiments illustrate the efficiency of the RFE algorithm for selecting a small number of variables together with a good prediction error [A6]
- Lý do: Theoretical study giữ additive regression model; finding RFE giữ simulated evidence và đồng thời small number variables/good prediction error.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P000841 — Presupposition Trigger-A Comparative Analysis of Broadcast News Discourse

dev / additional_ai_reference

### task

- Cũ: PressTV and CNN as varieties of Persian and American English respectively, in terms of presupposition triggers [A4]
- Cuối: pinpointing the oral discourse structure of two English news channels: PressTV and CNN as varieties of Persian and American English respectively, in terms of presupposition triggers [A3,A4]
- Lý do: A3 bị tách tại i.e. và A4 chỉ còn tên kênh/variety. Dẫn cả A3+A4 để giữ thao tác pinpoint oral discourse structure, hai channels và tiêu chí presupposition triggers; không biến PressTV/CNN thành task hoặc dataset.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: analyzed in terms of presupposition triggers [A5]; existential [A5]; factive [A5]; lexical [A5]; non-factive [A5]; structural [A5]; counter-factual [A5]; adverbial [A5]; relative [A5]
- Cuối: transcripts (20 selected from PressTV and another 20 from CNN) were analyzed in terms of presupposition triggers, namely existential, factive, lexical, non-factive, structural, counter-factual, adverbial, and relative [A5]
- Lý do: Existential/factive/.../relative là tám loại trigger được phân tích, không tám phương pháp. Giữ một thủ tục transcript analysis với đầy đủ phạm vi/loại trigger.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: most frequently used presupposition trigger in both varieties of oral discourse was Existential [A6]
- Cuối: PressTV and CNN as varieties of Persian and American English respectively: Analysis of the transcripts revealed that the most frequently used presupposition trigger in both varieties of oral discourse was Existential [A4,A6]
- Lý do: Khôi phục Analysis of the transcripts revealed để giữ trạng thái finding và chủ thể đo; most frequent Existential áp dụng cả hai oral-discourse varieties. Rà độc lập: A6's 'both varieties' are Persian and American English in PressTV and CNN as specified in A4. Add A4 to identify the comparison's scope without changing the finding.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P000990 — Building a Treebank for French

dev / additional_ai_reference

### contribution

- Cũ: treebank project for French [A0]; newspaper corpus of 1 Million words with part of speech, inflection, compounds, lemmas and constituency [A1]
- Cuối: treebank project for French: a newspaper corpus of 1 Million words with part of speech, inflection, compounds, lemmas and constituency [A0,A1]
- Lý do: Treebank project và newspaper corpus đã annotation là cùng artifact. Giữ mô tả corpus 1 Million words và các lớp annotation, không nhân đôi chỉ vì hai câu gọi tên khác nhau. Rà độc lập: One artifact is correct; the independent draft makes the French treebank identity and completed annotation explicit. The provisional corpus descriptor is supported but can carry the language scope with A0 rather than relying on the task facet.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P001860 — Compositional Approaches for Representing Relations Between Words: A Comparative Study

dev / additional_ai_reference

### problem

- Cũ: it suffers from data sparseness, information scalability and linguistic creativity as the model is unable to handle previously unseen word pairs in a corpus [A2]
- Cuối: A popular approach to represent the relations between a pair of words is to extract the patterns in which the words co-occur with from a corpus, and assign each word-pair a vector of pattern frequencies. Despite the simplicity of this approach, it suffers from data sparseness, information scalability and linguistic creativity as the model is unable to handle previously unseen word pairs in a corpus [A1,A2]
- Lý do: Giữ nguyên nhãn cũ sau khi kiểm tra vai trò, dẫn chứng và các ý có thể thiếu trong nguồn. Rà độc lập: The limitations in A2 apply to the cooccurrence-pattern frequency-vector approach in A1. Keeping 'it' with A2 alone leaves the failing approach unidentified; do not attribute these limitations to the compositional methods studied.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: compare different operations for creating relation representations from word-level representations [A4]; measuring the relational similarities [A5]; knowledge base completion [A6]
- Cuối: compare different operations for creating relation representations from word-level representations [A4]; knowledge base completion [A6]
- Lý do: Measuring relational similarities là cách đánh giá comparative operations, không một task độc lập bên cạnh comparative study/knowledge-base completion.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: compositional approach for representing relations between words [A3]
- Cuối: compositional methods [A5]; measuring the relational similarities [A5]
- Lý do: Giữ compositional methods thực sự được investigate ở A5 và phép đo relational similarity. Không thêm word analogy datasets vì không có tên riêng.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P002110 — Likelihood-based semi-supervised model selection with applications to speech processing

dev / additional_ai_reference

### problem

- Cũ: labeled development data are typically costly and difficult to obtain [A1]
- Cuối: In the context of speech processing systems and other large-scale practical applications, however, such labeled development data are typically costly and difficult to obtain [A0,A1]
- Lý do: Giữ chi phí/độ khó của labeled development data, chỉ đổi đại từ dẫn; ý chính nhãn cũ hợp lệ. Rà độc lập: A1 locates the development-data difficulty in speech processing and other large-scale practical applications; the clipped label drops that context and retains an unresolved 'such'. A0 explains the ground-truth labeled development data.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### task

- Cũ: semi-supervised likelihood-based model selection [A2]; select between candidate word pronunciations using unlabeled speech data that only potentially contain instances of the words under test [A4]
- Cuối: likelihood-based model selection [A2]; select between candidate word pronunciations using unlabeled speech data that only potentially contain instances of the words under test [A4]
- Lý do: Likelihood-based model selection là task, semi-supervised là cách thực hiện. Khôi phục nguyên task ASR cũ gồm unlabeled speech data only potentially contain words under test; blind đã bỏ sót điều kiện quan trọng này.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### method

- Cũ: trained classifiers representing each model to automatically generate putative labels [A2]; robust statistics [A3]; minimax-optimal censored likelihood ratio tests [A3]; automatic speech recognition system [A4]
- Cuối: trained classifiers representing each model to automatically generate putative labels [A2]; minimax-optimal censored likelihood ratio tests [A3]; automatic speech recognition system [A4]
- Lý do: Giữ trained classifiers sinh putative labels, censored likelihood tests và ASR. Robust statistics là nền lý thuyết của cùng likelihood tests, không một method độc lập chưa cụ thể.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

### contribution

- Cũ: alternative semi-supervised framework for likelihood-based model selection [A2]; minimax-optimal censored likelihood ratio tests that recover the nonparametric sign test as a limiting case [A3]; Results provide supporting evidence for the utility of this approach [A5]
- Cuối: semi-supervised framework for likelihood-based model selection that leverages unlabeled data by using trained classifiers representing each model to automatically generate putative labels [A2]; minimax-optimal censored likelihood ratio tests that recover the nonparametric sign test as a limiting case [A3]; semi-supervised framework for likelihood-based model selection. This approach is then validated experimentally using a state-of-the-art automatic speech recognition system to select between candidate word pronunciations using unlabeled speech data that only potentially contain instances of the words under test. Results provide supporting evidence for the utility of this approach [A2,A4,A5]
- Lý do: Framework giữ cơ chế dùng unlabeled data và trained classifiers. Giữ theorem tests/sign-test và supporting evidence; ứng dụng tương lai ở A5 là suggest/may, không thêm thành finding đã được kiểm chứng. Rà độc lập: A5's generic supporting-evidence statement refers to the A2 framework tested in the specific speech/pronunciation setting of A4. The standalone utility claim loses that evidential scope. The future-use suggestion is not an established finding and need not be added.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P003587 — Estimating Markov model structures

dev / additional_ai_reference

### contribution

- Cũ: combination of these techniques yields tagging accuracies that are at least equivalent to those of standard approaches [A8]
- Cuối: model merging; model splitting: the combination of these techniques yields tagging accuracies that are at least equivalent to those of standard approaches [A5,A6,A8]
- Lý do: Giữ nguyên finding cũ: combination of techniques yields at least equivalent tagging accuracies. Model merging/splitting được investigate, chưa có câu khẳng định mới nên không thêm artifact theo lượt blind ban đầu. Rà độc lập: A8's combined techniques are model merging and model splitting from A5/A6, not either technique alone. Include both names and their evidence; keep 'at least equivalent' rather than stronger superiority.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P003754 — MST-based Visual Parsing of Online Handwritten Mathematical Expressions

dev / additional_ai_reference

### method

- Cũ: Maximum Spanning Tree (MST) based parser [A0]; Edmonds' algorithm [A0]; directed Line-of-Sight graph [A0]; grouping input strokes [A1]; symbols are labeled [A1]; symbol pair spatial relationships are labeled [A1]
- Cuối: Maximum Spanning Tree (MST) based parser [A0]; Edmonds' algorithm [A0]; directed Line-of-Sight graph [A0]; grouping input strokes [A1]; symbols and symbol pair spatial relationships are labeled [A1]
- Lý do: Giữ parser, Edmonds algorithm, line-of-sight graph và grouping strokes. Hai nhãn symbols/spatial relationships labeled là cùng bước gán nhãn ở A1; gộp thành một thủ tục, không xóa biểu diễn graph hợp lệ mà blind bỏ sót.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P003775 — Should We Translate The Documents Or The Queries In Cross-Language Information Retrieval?

dev / additional_ai_reference

### method

- Cũ: identical statistical translation models [A1]; document translation [A2]; query translation-based information retrieval [A2]; hybrid systems [A2]
- Cuối: training identical statistical translation models for both translation directions using the same training data [A1]; document translation [A2]; query translation-based information retrieval [A2]; hybrid systems [A2]
- Lý do: Identical statistical translation models phải gắn training cả hai hướng bằng cùng data để xử lý confound đã nêu. Giữ doc/query translation và hybrid; đây là comparative objective nên các hệ thống được khảo sát thực sự đủ vai trò method.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P003879 — Active learning in multimedia annotation and retrieval: A survey

dev / additional_ai_reference

Giữ nguyên năm facet sau đối chiếu nguồn và rà AI độc lập.

## P004130 — Klout Topics for Modeling Interests and Expertise of Users Across Social Networks

dev / additional_ai_reference

### contribution

- Cũ: Klout Topics [A0]; model the interests of over 780M social media users on Klout.com [A3]; open the ontology for external use [A4]
- Cuối: Klout Topics [A0]; Klout Topics is used to model the interests of over 780M social media users on Klout.com [A0,A3]
- Lý do: Giữ Klout Topics như artifact một lần; open ontology for external use là release của cùng artifact, không artifact thứ hai. A0+A3 cho phép finding Klout Topics is used to model interests over 780M users có chủ thể rõ, không biến con số thành dataset riêng.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.

## P004190 — BLAST+: architecture and applications

dev / additional_ai_reference

### method

- Cũ: BLAST+ [T0]; Long query sequences are broken into chunks for processing [A4]; retrieve only the relevant parts of the sequence [A5]; modular software library [A7]
- Cuối: BLAST+ [T0]; Long query sequences are broken into chunks for processing [A4]; retrieve only the relevant parts of the sequence [A5]; retrieve masking information for database sequences from the BLAST databases [A6]; modular software library [A7]
- Lý do: Giữ tên BLAST+ và các thủ tục chunking/relevant subsequence/library. Thêm masking-information retrieval thực sự có ở A6. BLAST+ không bị thay bằng tên BLAST nền chỉ vì source gọi rewritten BLAST software.
- Trạng thái: AI reviewer độc lập đã chấp nhận bản sửa; human review pending.
