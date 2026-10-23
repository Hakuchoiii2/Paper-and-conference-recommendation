"""Write the source-reviewed findings alongside the offline diagnostic inventory."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE.parents[1]/'evaluation/base_v1_improvement_pilot50_20261022'
casebook = json.loads((OUT/'error_casebook_20261022.json').read_text(encoding='utf-8'))

# These judgments come from reading the supplied source, attempts and references.
# A score regression alone is not treated as proof of a semantic error.
notes = {
 'R1': {
 'P001963': ('draft: thiếu coverage + sai vai trò', 'Nguồn A1 nêu LDA, Girvan-Newman và inference mechanism; A3 nêu hai finding về cộng đồng/chủ đề. R1 bỏ LDA và hai finding, không giữ riêng artifact TTR-LDA-Community trong contribution; task đổi thành propose/evaluate model. Problem lấy background về structure/function, không phải một hạn chế được nêu. Các thiếu sót đã có trong draft, review không bổ sung.'),
 'P002471': ('draft: sai vai trò; review: đại từ; reference: gộp câu', 'R1 đưa kết quả null của nghiên cứu vào problem. Hai finding contribution có từ draft; review thêm it nhưng không phục hồi chủ ngữ cụ thể hay artifact web-based tutor. Gold gộp A1 và A2 thành một finding; không thể chép toàn bộ gold này từ một evidence_id. Cần tách lỗi vai trò rõ ràng khỏi phạt do gold/scorer.'),
 'P002297': ('draft: mất chủ thể; review: khớp nguồn nhưng xung đột reference', 'Problem chỉ còn challenging context for NLP, mất social dialogue và đối chiếu monologic resources. Review phục hồi đúng nguyên câu kết quả. Tuy nhiên gold sarcasm gộp 54/38 ở A4 với 62/52 ở A5; numeric guard chặn A5 vì không có số baseline trong cùng câu. Không nên gọi toàn bộ contribution FP là lỗi nghĩa.'),
 'P002380': ('draft: bỏ artifact', 'Nguồn A0 trình bày two language design methods. R1 thay artifact này bằng several useful extensions and generalizations of Pascal, trong khi vẫn giữ hai ví dụ cụ thể. Bỏ artifact độc lập và thêm mô tả bao trùm trùng vai trò; review giữ nguyên.'),
 'P001057': ('draft: nhãn method kém cụ thể; thiếu coverage chung', 'R1 giữ construct a novel vision model và extract linearly separable features thay cho tên compact novel vision model. Đây vừa là khác biệt cách đặt nhãn vừa là mất độ cụ thể. A2 nêu linear classifier nhưng cả baseline lẫn hai arm đều bỏ sót; không phải lỗi mới riêng R1.'),
 'P003002': ('draft: bỏ method', 'A3 nói rõ policy gradient ước lượng tham số của log-linear model for action selection. R1 chỉ giữ reinforcement learning và policy gradient, bỏ log-linear model; hai lượt review không thêm lại.'),
 'P001996': ('draft: sai vai trò problem', 'A1 đối chiếu prior work chỉ tập trung rumor volume với exposure. R1 chọn considering the size of the exposed population is a vital component... làm problem, tức một lập luận về cách tiếp cận thay vì hạn chế của prior work. Việc bỏ nhãn dataset Twitter case study là sửa đúng theo quy tắc named resource.'),
 'P002684': ('draft: bỏ artifact độc lập', 'A4 nêu giải pháp kết hợp joint n-gram features trong discriminative sequence model. R1 contribution chỉ còn finding cải thiện performance ở A6; không giữ giải pháp được giới thiệu. Review chỉ sửa our approach thành our results, không sửa coverage.'),
 'P002840': ('draft: finding quá chung', 'A2 nêu cụ thể negation tác động polarity/strength và modality tác động strength/certainty. R1 chỉ ghi distill effects/show specific effects, không giữ hai quan hệ kết quả; còn thêm áp dụng ngôn ngữ như contribution. Hai finding cụ thể cũng đã bị baseline bỏ sót; R1 thêm FP mà chưa khắc phục FN này.'),
 'P001484': ('review: anaphora; draft: bỏ artifact; scorer/reference', 'Review đổi problem thành nguyên văn This measure...intrinsically inadequate ở A2. Nội dung hợp nguồn trong ngữ cảnh A1, nhưng chủ thể đo cost bị thay bằng đại từ; gold diễn giải cả A1+A2 nên không match. R1 còn bỏ contribution three different approaches đã có ở final R0; đây là omission từ draft riêng R1.'),
 'P002848': ('draft: nhầm vai trò + bỏ method', 'Adaptive learning content and assessment exposition ở A1 bị đưa sang task và mất khỏi method. Novel phased learner model ở A2 không được thu hồi vào contribution dù là artifact giới thiệu rõ. R1 còn gộp/đổi task sang thủ tục; một phần điểm lệch do granularity reference, nhưng vai trò method/task là vấn đề thực.'),
 'P002877': ('draft: thiếu method/dataset', 'Nguồn A0 nêu multilingual encoder-decoder NMT architecture; A2 nêu WMT15. R1 bỏ cả hai so với final R0. English Yelp review classifier ở A1 cũng không được inventory thành resource phù hợp; omission này đã tồn tại ở baseline. Review không khôi phục.'),
 'P003809': ('draft: bỏ finding định lượng', 'Nguồn A5 nêu ClustalW cải thiện trên 6% trên hardest test cases, A6 nêu iteration mạnh hơn khi tích hợp trực tiếp vào progressive alignment. R1 bỏ finding định lượng đã có ở R0 và không thu hồi finding A6. Các câu tổng quát improves accuracy không thay thế được số và điều kiện.'),
 'P001589': ('draft: bỏ method/feature', 'A4 nói rõ dùng abstract form of Arabic words thay stem form. R1 không giữ feature này dù vẫn có các method ANOVA/LDA; review lặp lại và không phục hồi.'),
 'P000897': ('draft: bỏ artifact ở contribution', 'Nguồn A2 giới thiệu OntoUSP. R1 có tên này ở method nhưng contribution chỉ giữ finding recall +47%; artifact bị mất ở contribution dù chính prompt cho phép cùng tên ở hai vai trò. Draft đã thiếu, review giữ nguyên.'),
 'P001806': ('draft: bỏ method chính', 'A0 giới thiệu Temporal Attentive Relation Network (TARN) và A1 mô tả network sử dụng meta-learning. R1 giữ các thành phần nhưng bỏ tên TARN trong method. Parent/child cần xử lý theo quan hệ, không bỏ method chính chỉ vì các thành phần đã xuất hiện.'),
 'P003565': ('draft: suy diễn hạn chế', 'Nguồn nói MST parsing tăng efficiency/accuracy, nhưng không phát biểu existing approaches ... are inefficient. R1 tự tạo limitation từ finding tốt hơn, không chép được nguồn; hai review không sửa.'),
 'P002273': ('granularity reference + prior work', 'R1 tách ba đặc trưng count ở A5 thành các method riêng, trong khi reference gộp syntactic category/frequency thành một item. Các count này có nguồn, không thể mặc định mọi FP là hallucination. Finding a simple measure... ở A3 được mở đầu In a previous work; cả R0/R1/R2 đều vẫn nhận nó như contribution hiện tại.'),
 'P000781': ('draft: nhầm task/method', 'Meta-analysis of survey studies mô tả phương pháp, không nêu quan hệ nghiên cứu giữa perceived support và willingness to speak. R1 đặt nó vào task, trong khi task thực tế theo A0 vẫn không được thu hồi. Vấn đề coverage task đã có ở baseline; R1 thêm nhãn sai vai trò.'),
 },
 'R2': {
 'P002471': ('review: source-compliant nhưng mất chủ ngữ; reference gộp câu', 'R0 draft và final vốn đã tách hai finding, không phải R2 mới tách. R2 đổi nhãn có data space animation (không xuất hiện ở A2) thành it is no more effective... để khớp A2. Quan hệ so sánh vẫn có trong nguồn nhưng câu đứng riêng thiếu chủ ngữ; gold gộp A1+A2, khiến match bị mất. Artifact web-based tutor vẫn thiếu ở cả ba arm.'),
 'P001431': ('review: bỏ sót phục hồi, không phải xóa draft', 'Cached draft R0 method vốn là []. Review R0 thêm synthesis of the literature từ A0; review R2 vẫn để []. Vì vậy chênh lệch method là không tìm thêm method, không phải xóa nhãn draft hợp lệ. Bộ preserve method/contribution không thể bảo vệ một item chưa từng có.'),
 'P001484': ('review: anaphora; scorer/reference', 'R2 sửa problem thành This measure, assuming uniform costs...intrinsically inadequate, nguyên văn A2. Nó vẫn đúng trong ngữ cảnh, nhưng mất chủ thể cost-efficiency rõ ràng và không match gold tổng hợp A1+A2. Không đủ căn cứ gọi đây là một limitation sai; đây là ca kiểm tra ranh giới source-span và matching.'),
 'P001211': ('review: mất coverage; OCR + reference role', 'R2 bỏ phát biểu perform well only when tested on the same type of data... và đổi task thành thủ tục reproduce seven models. Gold đặt phát biểu generalization vào problem, dù A1 trình bày nó như finding của nghiên cứu: vai trò cần adjudication. Raw source có bri le/a acks; R2 phải giữ lỗi OCR để pass lexical. Source-quality lại ghi no_flag_detected. Không thể quy toàn bộ giảm điểm cho model.'),
 'P002297': ('review: xóa limitation thay vì sửa phrase', 'Draft ghi challenging context for NLP in social media dialogue, sai thứ tự nguồn. R2 xóa hẳn problem, dù A1 nêu social dialogue là challenging context so với monologic resources và cho phép chọn phrase đầy đủ theo source order. Hai contribution lỗi lexical vẫn lặp lại. Numeric guard với gold gộp hai câu là vấn đề riêng.'),
 'P001181': ('validator: sai phạm vi phủ định → review: đổi nghĩa; scorer: false positive', 'Policy 3.1 bắt nhầm not của mệnh đề Although...not improve in-domain accuracy sang finding surprisingly effective for domain adaptation. R2 lượt 3 xóa problem có nguồn và thay finding tích cực bằng prior negative finding, rồi pass validator. Scorer vẫn match finding tiêu cực với gold tích cực ở cosine 0.9082057522 vì cả hai chứa without; guard chỉ so sánh có/không có từ phủ định. Đây là lỗi ngữ nghĩa rõ và lỗi đo lường đã replay được.'),
 'P001996': ('review: xóa limitation; reference là paraphrase', 'Draft trộn prior rumor-volume ở A1 với subtle features ở A2 nên bị lỗi grounding. R2 xóa problem thay vì chọn trực tiếp prior work, which has focused on rumor volume ở A1 với đủ ngữ cảnh. Reference cũng diễn giải kết hợp hai câu, cần giữ riêng việc thiếu problem thật và chênh lệch wording. Bỏ generic Twitter case-study dataset là sửa đúng.'),
 'P002273': ('granularity reference; prior-work role cần xem', 'R2 giữ các count cụ thể ở A5 làm ba method, còn gold gộp; FP tăng không đồng nghĩa ba count này không có nguồn. Functional load hypothesis có ở background A2, cần phân biệt framework và procedure thực dùng. Finding A3 từ previous work vẫn được giữ như contribution hiện tại, lỗi chung chưa được repair xử lý.'),
 }}

def f1(c):
    d=2*c['tp']+c['fp']+c['fn']
    return 2*c['tp']/d if d else 1

for arm in notes:
    expected={r['paper_id'] for r in casebook[arm] if f1(r['counts_arm']) < f1(r['counts_R0'])-1e-12}
    assert set(notes[arm]) == expected, (arm,expected^set(notes[arm]))

lines = ['# Phân tích lỗi R1/R2 pilot50 — 22/10/2026', '',
 'Đã replay 388 attempts của R0/R1/R2 bằng đúng code đóng băng: assessments và applied outputs khớp audit. Kiểm tra cơ học toàn bộ 100 output R1/R2; đọc nguồn và chuỗi draft/review của toàn bộ 27 trường hợp arm-bài giảm micro F1, tương ứng 22 bài khác nhau, cùng các ca đối chứng và lỗi đo lường bên dưới. Đây là phân tích của AI trên nguồn đã cung cấp, chưa phải human adjudication.', '',
 '## Kết luận chính', '',
 'R1 làm thay đổi coverage và vai trò ngay từ draft: mất tên method/artifact, bỏ finding cụ thể, thêm problem từ task/background/result. R2 giúp sửa lexical, nhưng có thể xóa nội dung hoặc chuyển nhầm vai trò để được coi là hợp lệ. Một số chênh lệch F1 đến từ reference/scorer; F1 hiện tại không đủ để quyết định arm thắng.', '',
 '| Kiểm tra | R0 | R1 | R2 |', '|---|---:|---:|---:|',
 '| Draft lỗi → final hợp lệ | 4/37 | 6/34 | 19/37 |',
 '| Fallback | 33 | 28 | 18 |',
 '| Lỗi validator ở attempt được chọn (không tính thông báo fallback) | 100 | 77 | 52 |',
 '| Lỗi source-word/order trong số trên | 99 | 76 | 51 |',
 '| Fallback lặp nguyên selection và errors ở hai lượt cuối | 24 | 17 | 8 |',
 '| Attempts lỗi schema / tổng attempts | 0/134 | 1/129 | 2/125 |',
 '| Output tokens tối đa ở một call | 588 | 623 | 595 |', '',
 'Đơn vị lỗi validator là thông báo trên item, không phải số bài. Ở R0 còn một lỗi negation; R1 còn một lỗi negation; R2 còn một lỗi quantity. Không có parse failure; final được chọn đều đúng schema. Runtime cả ba arm giống nhau: Torch 2.11.0+cu128, Transformers 4.57.6, Tesla T4, matrix_efficient_no_gqa. Không thấy triệu chứng chạm cap 2048 output tokens.', '',
 '## 1. R1: lỗi phát sinh từ draft nhiều hơn là repair làm hỏng', '',
 '- 4 bài trước đó problem=[] và reference=[] nay có problem: P001389 (lấy task), P001963 (lấy background), P002471 (lấy finding null), P003565 (suy diễn hạn chế). Đây là sai vai trò hoặc thiếu căn cứ nguồn, không phải chỉ khác cách viết.',
 '- Theo matched gold của scorer, method mất 9 item đã match ở R0 và thêm 3 item, net -6 TP. Contribution mất 10 item và thêm 11, net +1 TP: điểm tổng tăng nhẹ che việc nhiều artifact/finding cũ biến mất.',
 '- Ví dụ rõ: P000897 mất OntoUSP trong contribution dù vẫn có ở method; P001806 mất TARN ở method; P003002 mất log-linear model; P001589 mất abstract form của Arabic words; P002877 mất NMT architecture và WMT15. P001963 là regression lớn nhất: micro F1 từng bài giảm 41,83 đpt.',
 '- Các omission trên đã nằm trong draft R1, review thường không inventory lại nguồn để thêm vào. 17/28 fallback có hai lượt cuối lặp nguyên selection/errors. Không có bằng chứng synthetic names ORBIT/TOOLBOX bị copy thành nhãn trong các case đã đọc; vấn đề chính là coverage/role, không nên kết luận prompt contamination trực tiếp.', '',
 '## 2. R2: valid không đồng nghĩa bảo toàn nội dung', '',
 '- 19 draft lỗi được sửa thành valid, nhưng 8/19 bài đồng thời xóa hết problem. Trong số này có các lần loại nhãn sai đúng đắn (như P000781: result đặt nhầm problem), và cũng có mất nội dung có nguồn (như P001181). Không thể xem mọi lần xóa là lỗi hay mọi lần pass là cải thiện.',
 '- Cả 5 problem TP bị mất theo scorer nằm ở P001181, P001211, P001484, P001996, P002297; không có problem TP mới bù lại. P001484 chủ yếu là anaphora/matching; P001211 có vấn đề vai trò reference và OCR. Phải xem từng ca thay vì gán cả 5 thành lỗi model giống nhau.',
 '- Review scope luôn có problem/dataset; cơ chế preserve_review_items chỉ bảo vệ method/contribution, và chỉ với item lexical-valid đã có ở draft. Vì vậy packet chỉ báo lỗi contribution cũng không ngăn model xóa problem. Ví dụ P001181 problem ban đầu không có validator error nhưng bị xóa khi repair contribution.',
 '- P001431 là missed recovery: draft R0 method=[]; review R0 tìm thêm synthesis of the literature, review R2 không tìm. Đính chính cách diễn đạt ngắn trước đó: R2 không xóa method đã có trong cached draft.', '',
 '## 3. P001181: chuỗi lỗi xác nhận được ở validator, repair và scorer', '',
 'Nguồn A1: “Although self-training without reranking has been found not to improve in-domain accuracy for parsers trained on the WSJ Penn Treebank, we show that it is surprisingly effective for parser domain adaptation.”', '',
 '1. Draft nêu finding hiện tại: `self-training without reranking is surprisingly effective for parser domain adaptation`. Đúng nội dung nguồn.',
 '2. Validator policy 3.1 dò span từ self-training đầu câu đến domain adaptation cuối câu, thấy not trong mệnh đề nhượng bộ, rồi báo shortening drops source negation. Probe giữ nguyên draft, đổi riêng assessor sang policy 3.2 thì lỗi này biến mất; không thay policy của thí nghiệm.',
 '3. R2 review 2 thêm but (không có trong source) nên vẫn lỗi. Review 3 bỏ problem và chỉ giữ mệnh đề prior work not improve in-domain accuracy làm contribution. Lỗi validator về 0 nhưng finding tích cực hiện tại bị mất.',
 '4. Scorer vẫn cho TP: silver tiêu cực vs gold `self-training without reranking is effective for parser domain adaptation`, cosine **0.9082057522**. Negation guard chỉ so sánh boolean có từ phủ định, nên without ở cả hai phía che việc một phía có thêm not. Replay pair_score xác nhận blocked_reason=None.',
 '5. Sensitivity riêng một cặp này: nếu đổi match sai đó từ TP thành FP+FN, R2 có TP/FP/FN = 214/145/188, Micro F1 **56,2418%**, thấp hơn R0 56,3636%. Đây chỉ là minh họa độ nhạy, KHÔNG phải điểm chấm lại chính thức. Một mismatch đã đủ đảo mức tăng 0,1410 đpt.', '',
 '## 4. Những ca không nên tự động coi là lỗi model', '',
 '- **P001484, cả R1/R2:** output problem giữ đúng A2 `This measure, assuming uniform costs ... intrinsically inadequate`. Gold diễn giải cả A1 (đo cost bằng số tokens) và A2. Output thiếu chủ thể tự đứng độc lập, nhưng đúng trong ngữ cảnh; scorer không match không đủ chứng minh nội dung sai.',
 '- **P002471:** positive finding ở A1, negative comparison có chủ ngữ it ở A2. Reference gộp hai câu thành một label, trong khi generator chỉ được chọn một evidence sentence. R0 đã tách hai item; R2 không phải bên mới tách. R2 chọn it để lexical-valid làm mất subject rõ ràng. Đây vừa là vấn đề anaphora vừa là lệch đơn vị nhãn/reference. Artifact web-based tutor bị bỏ là lỗi coverage riêng và rõ hơn.',
 '- **P002297:** gold sarcasm chứa cả 54/38 từ A4 và 62/52 từ A5. Label nguyên A5 chỉ có 62/52 nên numeric guard chặn; không thể thêm baseline vào A5 mà vẫn tuân thủ one-sentence source grounding. Điều này không phủ nhận lỗi R2 xóa problem hay R1 làm problem quá ngắn.',
 '- **P002273:** gold gộp syntactic category/frequency; arm tách các count có nguồn thành nhiều item. Granularity khác làm FP tăng. Đồng thời cả ba arm giữ finding mở đầu In a previous work làm contribution hiện tại: lỗi phân vai thực cần sửa.',
 '- **P002652, lỗi chung:** scorer match `new mixed integer programming models of the GMST problem` với gold về solution procedure giải đến 240 nodes ở cosine 0.879688078; label solution procedure có đủ 240 nodes lại thành extra. Pair này khác loại nội dung, cho thấy chỉ threshold embedding không bảo đảm matching đúng nghĩa.',
 '- **P003211, R2:** label chỉ nói identification of differences kèm channels/frequencies vẫn match gold có hướng Hardcore > Newbie ở cosine 0.883784889. Điểm tăng không chứng minh đã khôi phục đầy đủ hướng của finding.', '',
 '## 5. Lỗi nguồn và schema còn lại', '',
 '- P001211 có raw text `bri le`, `a acks`, `la er`; R2 giữ nguyên các dạng này để hợp lệ. source_quality vẫn no_flag_detected vì detector hiện tại không bắt mọi dạng OCR mất ký tự. P004047 có `poorl y`, `ma chine`, `transl ation`, `morpho logically` và được flag. Đây là lỗi input/contract, không thể chữa chỉ bằng tăng review calls.',
 '- R1 P003441 review 2 đổi key contribution thành con. R2 P000897 review 2 dùng key ` concept` có space; P001806 review 3 thêm trường evidence ngoài schema. Đều được phát hiện, không phải final JSON hỏng; đây là nguồn lãng phí call/budget và fallback.', '',
 '## 6. Thứ tự xử lý đề xuất', '',
 '1. Khóa các ca chẩn đoán P001181/P002471/P002297/P001484 thành bộ adjudication nhỏ. Làm rõ negation scope, coreference, một finding nhiều câu và đơn vị split/merge trước khi sửa prompt hoặc lấy F1 làm quyết định.',
 '2. Xử lý validator/scorer trong một phiên bản thí nghiệm riêng: không thay policy hoặc reference âm thầm trên kết quả đã đóng băng. Negation cần kiểm tra polarity/scope, không chỉ có một từ trong tập; matching cần kiểm tra subject/outcome/condition.',
 '3. R2: yêu cầu lý do theo nguồn cho việc bỏ problem và inventory lại missing method/artifact; đánh giá cả semantic preservation và recovery, không dùng giảm fallback làm mục tiêu duy nhất. Không bảo vệ cứng mọi problem lexical-valid, vì nhiều problem hiện tại sai vai trò.',
 '4. R1: thu hẹp thay đổi prompt sau khi xác nhận case lỗi; ưu tiên inventory method/artifact và phân biệt task/background/new finding với problem. Hiện không có bằng chứng để ghép ngay R4.',
 '5. Chuẩn hóa/adjudicate các lỗi OCR ở upstream theo chính sách riêng, có raw/provenance; không tự sửa source hoặc nhãn trong pilot đã đóng băng. Sau đó xác nhận trên cohort mới.', '',
 'Phạm vi công việc này: chẩn đoán và lưu evidence; chưa đổi prompt/pipeline/scorer/reference, chưa chạy inference hoặc R4.', '',
 '## 7. Toàn bộ các trường hợp giảm F1 đã đọc nguồn', '']

for arm in ('R1','R2'):
    lines += [f'### {arm}', '', '| Paper | Δ micro F1 từng bài (đpt) | Nhóm | Nhận xét theo nguồn/trace |', '|---|---:|---|---|']
    rows=sorted((r for r in casebook[arm] if r['paper_id'] in notes[arm]),key=lambda r:f1(r['counts_arm'])-f1(r['counts_R0']))
    for r in rows:
        kind,note=notes[arm][r['paper_id']]
        lines.append(f"| {r['paper_id']} | {100*(f1(r['counts_arm'])-f1(r['counts_R0'])):.2f} | {kind} | {note} |")
    lines.append('')
lines += ['## File bằng chứng', '',
 '- `error_casebook_20261022.json`: toàn bộ 150 case R0/R1/R2 với nguồn, options, draft, final, reference, attempts và so sánh scorer.',
 '- `error_diagnostics_20261022.json`: thống kê replay 388 attempts, lỗi selected, thay đổi problem, các item draft bị thay và raw/applied merge.',
 '- `error_review_annotations_20261022.json`: 27 nhận xét thủ công của AI cho các ca giảm điểm.',
 '- Scripts tái tạo: `data/exp_a/.kaggle/base_improvement/analyze_errors_20261022.py` và `write_error_review_20261022.py`.', '']
(OUT/'error_review_annotations_20261022.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'error_review_20261022.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Wrote error review; verified annotations cover all 19 R1 and 8 R2 paper-level score regressions.')
