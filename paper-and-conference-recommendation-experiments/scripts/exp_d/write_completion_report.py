"""Build the seven-section Vietnamese report from checked D outputs; check links/math."""
import re
from pathlib import Path
from run_improve_trial import read

PROJECT=Path(__file__).resolve().parents[2]
DATA=PROJECT/'data/exp_d'
RUN=DATA/'results/completion_20261018_v1'
REVIEW=DATA/'results/completion_20261018_v1_review'
REPORT=DATA/'docs/Report_D.md'

NAMES={
    'fixed_similar':'Fixed Similar — baseline',
    'profile_similar':'Profile Similar — baseline',
    'direction_behavior':'Direction Behavior — baseline',
    'direction_search':'Direction Search — baseline',
    'proposal_behavior_predicted':'Evidence-guided — behavior (proposal)',
    'proposal_search_predicted':'Evidence-guided — search (proposal)',
    'linear_ranknet_behavior':'Linear RankNet — behavior (đối chiếu học)',
    'linear_ranknet_search':'Linear RankNet — search (đối chiếu học)',
    'oracle_intent':'Oracle Intent — đặc quyền',
}
ORDER=list(NAMES)


def num(x):return f'{x:.4f}'.replace('.',',')


def table(metrics,macro=False,noise=None):
    lookup={r['model']:r for r in metrics}
    header='| '+('Nhiễu | ' if noise else '')+'Phương pháp | '+('Direction Macro-F1 | ' if macro else '')+'nDCG@10 | Compliance@5 | Compliance@10 |'
    lines=[header,'|'+'---|'*(len(header.split('|'))-2)]
    for model in ORDER:
        if model not in lookup:continue
        row=lookup[model]
        values=([num(row['direction_macro_f1'])] if macro else [])+[num(row[k]) for k in ('ndcg@10','intent_compliance@5','intent_compliance@10')]
        lines.append('| '+(' | '.join([noise])+' | ' if noise else '')+NAMES[model]+' | '+' | '.join(values)+' |')
    return '\n'.join(lines)


def build():
    checked=read(REVIEW/'report_tables.json')
    full=table(checked['canonical_full'],macro=True)
    canonical=table(checked['canonical_canonical'])
    auxiliary=table(checked['auxiliary_noise_0.2'],noise='0,2')+'\n'+'\n'.join(table(checked['auxiliary_noise_0.5'],noise='0,5').splitlines()[2:])
    text=r'''# BÁO CÁO THỰC NGHIỆM D

**Suy ý định similar/different trong phiên và ứng dụng vào xếp hạng bài báo**

Cập nhật ngày 18/10/2026. Đã đánh giá proposal trên D gốc và một mô hình tuyến tính theo RankNet. Bài mốc/ứng viên là bài thật, các khía cạnh do A trích xuất tự động; ý định (intent), nhãn theo giao concept (overlap) và phản ứng là mô phỏng.

## 1. Bối cảnh và mục tiêu của exp D

Một phiên có **bài mốc (anchor)** là bài đang đọc, **context** là khía cạnh cần giữ tương tự và **focus** là khía cạnh cần suy hướng tìm giống hay khác bài mốc. Năm khía cạnh (facet) là problem, task, method, dataset, contribution. Ví dụ: giữ cùng nhiệm vụ (context = task) nhưng đổi phương pháp (focus = method, hướng different).

D kiểm tra: (1) query/phản ứng giúp suy hướng không; (2) dùng hướng đó giúp ranking không; (3) proposal không huấn luyện so với một đối chiếu học từ nhãn như thế nào. Context được cung cấp sẵn, mỗi phiên chỉ có một focus; chưa đánh giá tự chọn context hoặc nhiều focus đồng thời.

## 2. Thiết kế exp D

### 2.1. Hai bộ dữ liệu riêng

| Thành phần | D gốc (canonical) | Bộ phụ nhiều ứng viên v2 |
|---|---|---|
| Quy mô | 300 người dùng, 1.500 phiên, 57 bài mốc | 45 người dùng, 90 phiên, 8 bài mốc |
| Tập ứng viên và nhãn | 20 ứng viên/phiên; 30.000 nhãn | 20 ứng viên/phiên; 1.800 nhãn |
| Quan sát đầu phiên D | Không có cặp hiển thị/phản ứng | 4 cặp/phiên; 360 lượt hiển thị cặp, 720 phản ứng/cấu hình |
| Focus | Đủ 5 facet trong toàn bộ dữ liệu | 4 facet, chưa có problem |

Canonical giữ nguyên sessions, candidates, nhãn, query, cutoff và profile C của [snapshot baseline](../workspace_baseline_20261016_v1/data/exp_d/generated/manifest.json). Không bổ sung phản ứng vào bộ này.

**Lưu ý định danh:** `data/exp_d/generated`/`ground_truth` hiện tại cũng có 1.500 phiên nhưng sessions, query và nhãn khác snapshot baseline, dù tái sử dụng case IDs. Báo cáo chỉ dùng `workspace_baseline_20261016_v1` khớp hashes của `baseline_20261016_v1`; không dùng dữ liệu hiện tại để chấm predictions cũ. [Biên nhận đối chiếu](../results/completion_20261018_v1_identity/identity.json).

Bộ phụ có 15 thiết kế × 2 intent đối lập × 3 query mode. Cùng thiết kế giữ pool/profile/cutoff; có 1 same-focus, 1–5 different-focus trong context, còn lại ngoài context. Chín thiết kế chỉ có 1 different; hai có 2 và bốn có 5. Mẫu observation tổng hợp nằm ngoài candidates; sáu cấu hình seed 42/43/44 × noise 0,2/0,5 được giữ nguyên bytes từ lượt trước. Đây là **development diagnostic**, không phải thêm 90 quan sát độc lập hoặc tập test hoàn toàn mới.

### 2.2. Nhãn và kiểm tra dữ liệu

Intent được sinh trước query/phản ứng/nhãn. Context luôn similar; focus similar hoặc different; trọng số thật context/focus là 0,6/0,4 và chỉ evaluator/oracle được dùng. Query clear nêu hướng, ambiguous chỉ context, none không có query.

Grade 2: có giao concept ở context và thỏa hướng focus; grade 1: đúng context nhưng sai hướng; grade 0: ngoài context hoặc thiếu facet cần xét. Similar là có giao concept; different là không giao khi có đủ dữ liệu. Đây là **nhãn theo quy tắc**, chưa phải relevance do chuyên gia xác nhận.

Đã kiểm tra mã băm và nguồn dữ liệu, thời gian quan sát, mã định danh trùng, ghép cặp, việc tách bài quan sát khỏi ứng viên, và tính lại 31.800 nhãn độc lập với điểm mô hình. Với 45 cặp intent đối lập của bộ phụ, nhãn 1/2 hoán đổi và nhãn 0 giữ nguyên. Canonical được kiểm thêm khi đảo intent giả định, không sửa dữ liệu. Các kiểm tra xác nhận **tính nhất quán quy tắc**, chưa xác nhận relevance thực tế.

Nguồn: [protocol](../../../docs/EXPERIMENT_PROTOCOL.md), [README D](../README.md), [thiết kế v2](../results/multicandidate_proposal_20261017_v2_verified/design.json), [data audit](../results/completion_20261018_v1/data_audit.json), [kiểm tra nhãn phản thực](../results/completion_20261018_v1_diagnostics/canonical_pool_audit.json).

### 2.3. Split và ngân sách nhãn của mô hình học

Ba tập **train** (học tham số), **validation** (chọn cấu hình) và **test** (đánh giá sau khi chọn) được [chốt trước huấn luyện](../results/completion_20261018_v1/registration.json), theo nhóm bài mốc với tỷ lệ khoảng 60/20/20. Mọi phiên và biến thể cùng bài mốc luôn thuộc cùng tập, kể cả bài mốc dùng chung giữa hai bộ. Cách chia dựa trên hash ID, phân tầng theo việc thuộc bộ phụ để cả ba tập không rỗng; không dùng nhãn/điểm để chọn split.

| Bộ | Train: phiên / anchor | Validation: phiên / anchor | Held-out test: phiên / anchor |
|---|---:|---:|---:|
| Canonical | 1.014 / 34 | 245 / 11 | 241 / 12 |
| Bộ phụ | 72 / 5 | 6 / 1 | 12 / 2 |

Mỗi bộ và mỗi nguồn behavior/search huấn luyện riêng cùng một loại mô hình. Bộ phụ gộp sáu điều kiện quan sát **chỉ trên train**; seed là giá trị khởi tạo ngẫu nhiên, lặp seed không tạo thêm nhãn độc lập. Ngân sách thêm cho mỗi nguồn: canonical **20.280 nhãn train**; bộ phụ **1.440 nhãn train**, dùng lặp qua sáu điều kiện. Baseline/proposal không dùng nhãn train này.

Chọn hệ số phạt L2 trong {0,001; 0,01; 0,1} bằng nDCG@10 validation: cả hai nguồn chọn 0,1 ở canonical và 0,001 ở bộ phụ. Không huấn luyện lại với validation hoặc chỉnh theo test. Dữ liệu đã từng được xem khi phát triển: **held-out** chỉ nghĩa bài mốc ngoài train của lần fit này, chưa phải tập hoàn toàn mới. Validation/test canonical thiếu focus dataset; test bộ phụ chỉ có task, validation chỉ có contribution. Chi tiết tối ưu và ngân sách cặp ở [ghi chú tái lập](completion_reproducibility.md).

## 3. Các phương pháp và baselines

**Trọng số C** là mức quan tâm dài hạn của từng người dùng đối với năm khía cạnh, được ước lượng từ lịch sử tương tác và tìm kiếm của dữ liệu thực nghiệm C. Năm trọng số không âm, có tổng bằng 1; chúng không phải hướng similar/different của phiên D. Ví dụ minh họa: task có trọng số 0,4 nghĩa là nó chiếm 40% trọng số trước khi chuẩn hóa lại nếu phương pháp chỉ dùng một số facet.

**Cutoff** là mốc thời gian chốt dữ liệu đầu vào trước khi xếp hạng: chỉ lịch sử, truy vấn và phản ứng xảy ra **trước mốc này** được dùng. Ví dụ cutoff 10:30 thì phản ứng lúc 10:35 không được dùng để dự đoán. Đây không phải ngưỡng điểm hay giới hạn top K.

| Phương pháp | Vai trò và thông tin sử dụng |
|---|---|
| Fixed Similar | Baseline: trọng số đều, luôn similar |
| Profile Similar | Baseline: mức quan tâm dài hạn từ C, luôn similar |
| Direction Behavior | Baseline: trọng số C; suy hướng từ phản ứng đầu phiên D trước mốc chốt dữ liệu (cutoff) |
| Direction Search | Baseline: như Direction Behavior, thêm truy vấn trước cutoff |
| Evidence-guided facet reranking | **Một proposal**, không train; thay cách xếp hạng từ hướng baseline dự đoán; nguồn behavior/search báo riêng |
| Linear RankNet cho D | **Một mô hình đối chiếu học**, score tuyến tính với pairwise logistic loss; nguồn behavior/search báo riêng |
| Oracle Intent | Tham chiếu đặc quyền: hướng/trọng số thật, scorer gốc |

Trong báo cáo, **proposal** là ý tưởng được đề xuất để kiểm chứng, không mặc định là phương pháp có điểm cao nhất. Predicted/always-similar/flipped là các nhánh đối chứng của cùng proposal. Oracle dùng thông tin đặc quyền, không phải trần điểm của mọi hàm xếp hạng. Linear RankNet giữ nguyên bộ suy hướng của baseline, chỉ học xếp hạng.

**Unknown** nghĩa là chưa đủ bằng chứng để kết luận hướng. **Fallback** nghĩa là quay về nguyên thứ hạng baseline khi không đủ bằng chứng để áp dụng proposal. **Strict** trong phần đối chứng là hàm xếp hạng gốc của baseline, phân biệt với hàm ưu tiên intent của proposal.

## 4. Cách suy ý định và tính điểm xếp hạng

### 4.1. Profile và hướng dự đoán

Profile C chuẩn hóa độ lớn bằng chứng từ tương tác/truy vấn từng facet thành trọng số; các phép so dùng cùng profile của snapshot. Fixed Similar dùng trọng số đều theo định nghĩa. Focus, hướng, trọng số thật và nguồn gốc ẩn không đi vào đặc trưng/hàm xếp hạng. Nhãn relevance chỉ là target trên train; validation chọn cấu hình, test đánh giá.

Phản ứng đổi thành dislike = −1, view = 0, click = 1, save = 2, like = 3. Với n cặp so sánh hợp lệ, b ở phía same/diff là điểm phản ứng với bài giống/khác bài mốc tại facet đang xét:

$$
\delta_f=\frac{\sum_{j=1}^{n}(b_j^{\mathrm{diff}}-b_j^{\mathrm{same}})}{n+2}.
$$

Cần ít nhất 2 cặp và trị tuyệt đối delta ít nhất 0,25; dương cho different, âm cho similar; còn lại **unknown**. Context khởi tạo similar. Search dùng query rõ mới nhất: “alternatives to” hoặc “more papers using”; chỉ nhắc concept khác chưa đủ kết luận different. Confidence là điểm quy tắc, chưa được hiệu chuẩn.

### 4.2. Scorer gốc

Với S là cosine từng facet trong [0,1], w là trọng số C và F là tập facet đang dùng, hàm xếp hạng baseline/strict tính:

$$
T_f=\begin{cases}1-S_f,&\text{different},\\S_f,&\text{similar hoặc unknown},\end{cases}
\qquad \operatorname{Score}_{\mathrm{gốc}}=\frac{\sum_{f\in F}w_fT_f}{\sum_{f\in F}w_f}.
$$

Ignore bị bỏ qua. Context thiếu/cosine không dương hoặc candidate thiếu facet active nhận −1; facet thiếu ở anchor bị bỏ qua. Hết trọng số thì dùng cosine context. Unknown dùng similarity khi xếp hạng nhưng vẫn là unknown khi chấm hướng. Hòa điểm sắp theo ID. Proposal và mô hình học có hàm điểm riêng ở mục 7.

## 5. Metrics

**Chỉ số chính: nDCG@10**, đo thứ tự 10 bài đầu so với thứ tự tốt nhất theo nhãn; càng cao càng tốt. **Compliance@5/10** là tỷ lệ bài thỏa đầy đủ intent trong 5/10 bài đầu. Trong công thức, r là grade của bài ở vị trí i, G₂ là số bài grade 2 trong tập ứng viên; IDCG là DCG lớn nhất khi sắp theo grade giảm dần:

$$
\operatorname{DCG}@K=\sum_{i=1}^{K}\frac{2^{r_i}-1}{\log_2(i+1)},\qquad
\operatorname{nDCG}@K=\frac{\operatorname{DCG}@K}{\operatorname{IDCG}@K}.
$$

$$
\operatorname{Compliance}@K=\frac{1}{K}\sum_{i=1}^{K}\mathbf1[r_i=2],\qquad
\operatorname{Ceiling}@K=\frac{\min(G_2,K)}{K}.
$$

Trần Compliance@5/@10: canonical toàn bộ **0,60/0,45**, canonical held-out **0,6913/0,5635**; bộ phụ toàn bộ **0,32/0,16**, bộ phụ held-out **0,60/0,30**. Vì vậy, không so chênh lệch giữa các tập để quy riêng cho thuật toán. Các bài cùng grade không có thứ tự ưu tiên được đánh giá độc lập.

Tại focus thật, **Accuracy** là tỷ lệ phiên dự đoán đúng hướng, **Coverage** là tỷ lệ phiên có dự đoán similar/different thay vì unknown. **Macro-F1** trung bình F1 của hai hướng; unknown gây bỏ sót. Đây chưa phải đánh giá riêng việc chọn đúng tên focus. Direction Macro-F1 còn tính cả context đã cho sẵn; facet thật ignore bị bỏ qua:

$$
F1_c=\frac{2TP_c}{2TP_c+FP_c+FN_c},\quad
\operatorname{MacroF1}=\frac{F1_{\mathrm{similar}}+F1_{\mathrm{different}}}{2}.
$$

TP/FP/FN lần lượt là số dự đoán đúng, dự đoán nhầm và bỏ sót của lớp đang xét. Trung bình seed tại từng phiên trước **bootstrap 2.000 lần theo bài mốc**: lấy mẫu lại các nhóm bài mốc, giữ toàn bộ phiên của nhóm để ước lượng khoảng tin cậy (**CI 95%**). Macro-F1 gộp số đếm trong từng seed rồi trung bình. Canonical chỉ có một điều kiện. CI mô tả dữ liệu hiện tại; 2 bài mốc test bộ phụ chưa đủ để suy rộng. Phân tích nhóm/chỉ số phụ chưa điều chỉnh nhiều phép so.

## 6. Kết quả thực nghiệm và đánh giá

### 6.1. D gốc: proposal trên đủ 1.500 phiên / 57 anchor

**Cùng snapshot canonical đã cố định; không thêm phản ứng đầu phiên.**

@@FULL@@

Proposal behavior fallback **1.500/1.500 phiên**, bằng Profile Similar/Direction Behavior: **không tăng**. Proposal search fallback **1.000 phiên**; so Direction Search, tăng nDCG@10 **0,04094**, CI 95% [0,02140; 0,06862], Compliance@5/@10 tăng **0,03587/0,03413**. Có 195 phiên tăng nDCG, 1.305 hòa, không phiên giảm trong phép so này. Đây là thay đổi toàn ranker, không phải tăng độ chính xác suy hướng.

Focus Accuracy/Coverage/Macro-F1: behavior và proposal behavior **0/0/0**; search và proposal search **0,3333/0,3333/0,5000**. Fixed/Profile luôn similar đạt **0,5/1/0,3333**; oracle đạt 1 cả ba. Toàn bộ 750 phiên different thiếu grade 1, nên canonical yếu khi tách riêng tác dụng direction.

Nguồn: [full summary, delta và CI](../results/completion_20261018_v1/canonical/full_summary.json), [predictions/details](../results/completion_20261018_v1/canonical/full/), [baseline được tái kiểm](../results/baseline_20261016_v1/report.json).

### 6.2. Canonical held-out: cùng 241 phiên / 12 anchor cho mọi dòng

**Chỉ bảng này dùng mô hình học trên canonical.** Baseline, proposal và oracle được lọc đúng cùng test subset; không so trực tiếp với điểm toàn bộ 1.500 phiên ở mục 6.1.

@@CANONICAL@@

Linear RankNet tăng nDCG@10 so proposal tương ứng: behavior **+0,13154**, CI [0,05256; 0,25904]; search **+0,08870**, CI [0,03342; 0,18295]. Cả hai đạt trần Compliance của subset. Oracle scorer gốc có thể thấp hơn ranker học dù dùng intent thật; không mâu thuẫn với định nghĩa oracle.

Tuy vậy, behavior vẫn có Focus Accuracy/Coverage/F1 **0/0/0**; search là **0,3527/0,3527/0,5240**, giống baseline/proposal cùng nguồn. Fixed/Profile là **0,3859/1/0,2784**, oracle là 1. Điểm ranking cao khi không suy được hướng cho thấy có thể tận dụng quy tắc overlap/cấu trúc pool và tránh phạt facet không liên quan; **chưa chứng minh học được intent**. Ngân sách nhãn train cũng khác proposal. Held-out thiếu focus dataset, không đại diện đủ năm facet.

Nguồn: [held-out canonical](../results/completion_20261018_v1/canonical/heldout_summary.json), [model và validation](../results/completion_20261018_v1/canonical/models/), [nhóm và cấu trúc pool](../results/completion_20261018_v1_diagnostics/group_metrics.json).

### 6.3. Bộ phụ held-out: cùng 12 phiên / 2 anchor cho mọi dòng

Mỗi mức nhiễu trung bình ba seed trên cùng 12 phiên; mô hình fit từ 72 phiên train, không fit từ hai anchor này. **Test chỉ có focus task**; validation chỉ 6 phiên/1 anchor contribution. Không đổi split sau khi thấy hạn chế.

@@AUXILIARY@@

So proposal behavior, Linear RankNet **giảm** nDCG@10 **0,00524/0,00893** ở noise 0,2/0,5; CI lần lượt [−0,01047; 0] và [−0,02122; 0,00336]. Nhánh search **hòa** ở noise 0,2 và **giảm 0,00222** ở noise 0,5, CI [−0,01047; 0,00604]. Không có bằng chứng mô hình học vượt proposal trên primary này. Compliance@10 hòa; behavior noise 0,5 tăng nhẹ Compliance@5 **0,00556** dù nDCG giảm, không dùng chỉ số phụ để đổi kết luận.

Focus Accuracy/Coverage/Macro-F1 của baseline hướng, proposal và Linear RankNet cùng nguồn: noise 0,2 là **1/1/1**; noise 0,5 behavior **0,9167/0,9722/0,9259**, search **0,9444/1/0,9441**. Fixed/Profile **0,5/1/0,3333**, oracle 1. Ranking không tạo thêm độ chính xác hướng.

Nguồn: [held-out bộ phụ, focus và CI](../results/completion_20261018_v1/auxiliary/heldout_summary.json), [model/validation](../results/completion_20261018_v1/auxiliary/models/), [thành phần từng split](../results/completion_20261018_v1_review/subset_composition.json). Không tính/báo điểm mô hình học trên toàn bộ 90 phiên.

### 6.4. Đối chứng bộ phụ toàn bộ 90 phiên — development diagnostic

Phần này tái sử dụng output đã khớp hash và điều kiện, gồm cả anchor nay thuộc train. **Không phải bảng held-out và không so với điểm mô hình học ở mục 6.3.**

Với Direction Behavior, Focus Accuracy/Coverage/Macro-F1 khi không observation là **0/0/0**; có reaction đúng là **1/1/1** ở noise 0,2 và **0,9000/0,9407/0,9276** ở noise 0,5. Sau xáo action trong phiên, accuracy/coverage còn **0,3348/0,6770** và **0,3719/0,7696**; summary cũ không lưu F1 xáo. Query search vẫn cho focus accuracy 1/3 khi không observation. Proposal behavior không observation fallback, nDCG@10 **0,7757**, Compliance@5/@10 **0,2133/0,1267**.

Ba nhánh proposal giữ cùng focus dự đoán, C weights, ranker, gate/missingness và điểm phụ trung tính; chỉ đổi direction. Kết quả behavior trên **cùng 90 phiên**:

| Noise | Predicted nDCG@10 | Always-similar | Flipped | Delta predicted − similar | CI 95% theo anchor |
|---|---:|---:|---:|---:|---|
| 0,2 | 1,0000 | 0,9080 | 0,7985 | +0,0920 | [0,0847; 0,0981] |
| 0,5 | 0,9806 | 0,9018 | 0,8069 | +0,0788 | [0,0673; 0,0925] |

Compliance@5 tăng **0,02667/0,02222**, CI [0,00556; 0,05000]/[0,00370; 0,04167]; **Compliance@10 không tăng**. Strict scorer chỉ tăng nDCG **0,00946/0,00579**, CI [0; 0,03547]/[0; 0,02223] chạm 0. Nhóm intent similar noise 0,5 của proposal **giảm nDCG 0,01083**, 7/45 phiên giảm sau trung bình seed. Giữ các kết quả giảm/không tăng.

Nguồn: [absolute metrics và oracle của đủ 90 phiên](../results/multicandidate_proposal_20261017_v2_verified/analysis/absolute_metrics.json), [đối chứng direction/strict](../results/multicandidate_proposal_20261017_v2_verified/analysis/seed_averaged_comparisons.json), [no observation](../results/multicandidate_proposal_20261017_v2_verified/no_observations/report.json), [xáo phản ứng](../results/multicandidate_proposal_20261017_v2_verified/shuffle_summary.json). Xáo chỉ kiểm suy hướng, không được gọi là ranking sau xáo trên pool mới.

## 7. Phương pháp đề xuất và hướng cải tiến

### 7.1. Evidence-guided facet reranking

Giữ estimator baseline. Chọn facet ngoài context có hướng rõ và confidence dương lớn nhất duy nhất làm focus dự đoán. Thiếu focus, hòa confidence hoặc tổng C weights trên context/focus bằng 0 thì **fallback nguyên ranking baseline**, giữ unknown. Khi đủ evidence, chỉ active context và focus; chuẩn hóa hai trọng số C. Candidate thiếu facet active/không overlap context nhận −1.

Với ứng viên hợp lệ, q bằng 1 khi overlap focus khớp hướng dự đoán. Hai trọng số có dấu ngã được chuẩn hóa trên context và focus, tổng bằng 1; chỉ số c/f chỉ hai facet này. Điểm phụ B luôn dùng cosine similarity:

$$
B(p)=\tilde w_cS_c(p)+\tilde w_fS_f(p),\qquad
\operatorname{Score}_{\mathrm{proposal}}(p)=2q(p)+B(p).
$$

Điểm phụ thuộc [0,1], nên bài thỏa hướng đứng trước nhóm không thỏa. Hệ số 2 mã hóa ưu tiên nhóm, không fit bằng nhãn. Đây là **một proposal sử dụng hướng**, không phải estimator mới và chưa chứng minh relevance ngữ nghĩa độc lập. Xem [proposal.md](proposal.md) và [implementation](../../../scripts/exp_d/proposal_ranker.py).

### 7.2. Linear RankNet: đối chiếu từ bài báo

Đã đọc [Burges và cộng sự, “Learning to Rank using Gradient Descent”, 2005](https://www.microsoft.com/en-us/research/publication/learning-to-rank-using-gradient-descent/) và [PDF gốc](https://www.microsoft.com/en-us/research/wp-content/uploads/2005/08/icml_ranking.pdf). **Kế thừa** xác suất logistic từ chênh lệch score và cross-entropy cặp, mục 3, phương trình (1)–(3); bài cũng đánh giá mạng tuyến tính. Đây là **biến thể áp dụng cho D**, không tái lập toàn bộ kiến trúc/thực nghiệm gốc.

Score tuyến tính dùng vector đặc trưng z đã chuẩn hóa bằng mean/std **chỉ từ train**; theta là tham số học, P là xác suất bài i đứng trước bài j. Mỗi cặp khác grade trong cùng phiên lấy một lần, bài grade cao đứng trước; bỏ cặp hòa. Không có bias vì triệt tiêu khi lấy hiệu:

$$
s_i=\theta^\top z_i,\qquad P_{ij}=\frac{1}{1+\exp[-(s_i-s_j)]}.
$$

$$
\mathcal L(\theta)=\frac{1}{M}\sum_{u=1}^{M}\frac{1}{|\mathcal P_u|}
\sum_{(i,j)\in\mathcal P_u}\log\left(1+\exp[-(s_i-s_j)]\right)
+\frac{\lambda}{2}\|\theta\|_2^2,\qquad y_i>y_j.
$$

M là số lượt phiên/điều kiện train; mỗi lượt có tổng trọng số bằng nhau. Các lượt train hiện tại đều có cặp khác grade. Nhãn chỉ xác định thứ tự cặp trong train, không đi vào vector đặc trưng.

**Tự thiết kế cho D:** 90 đặc trưng gồm độ tương tự/giao concept từng facet, tình trạng thiếu dữ liệu, context, trọng số C, hướng/confidence dự đoán và các tích giữa chúng. ID chỉ dùng tra bản ghi; không dùng focus/hướng/trọng số thật, nhãn relevance hoặc nguồn gốc ẩn làm đặc trưng. Biểu diễn TF-IDF giữ từ corpus không nhãn của snapshot. Cách tạo đặc trưng, chuẩn hóa, phạt L2, cân bằng phiên, bỏ cặp hòa, chia tập và tối ưu là các lựa chọn cho D; [chi tiết tái lập](completion_reproducibility.md) phân biệt chúng với phần kế thừa bài gốc.

Đã kiểm 25 tests và tái dựng số liệu từ output; không chạy thêm mô hình trong lần chỉnh lời giải thích. Code, lệnh chạy, ngân sách cặp và biên nhận hash nằm trong [ghi chú tái lập](completion_reproducibility.md). Các bảng giữ nguyên số liệu đã xác minh.
'''
    return text.replace('@@FULL@@',full).replace('@@CANONICAL@@',canonical).replace('@@AUXILIARY@@',auxiliary)


def validate(text):
    headings=re.findall(r'^## (\d+)\.',text,re.M)
    assert headings==list('1234567'),headings
    assert all(line=='$$' or '$' not in line for line in text.splitlines()),'Inline math or broken delimiters'
    assert text.splitlines().count('$$')%2==0,'Unbalanced block math'
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if target.startswith(('https://','http://')):continue
        assert (REPORT.parent/target).resolve().exists(),target
    assert '@@' not in text


if __name__=='__main__':
    text=build();validate(text)
    REPORT.write_text(text,encoding='utf-8')
    print('Wrote Report_D.md: 7 sections, numeric tables from verified output; local links and block math pass')
