# Pilot50 v3.7 — lấy thêm ý nhưng tăng nhãn dư

Kernel **version9 / prompt3.7 đã COMPLETE**, đủ50 bài. Cùng reference AI v1,
evaluator, encoder và ngưỡng0,85: **micro-F1 53,8462% → 54,2741%** (+0,4279
điểm phần trăm), nhưng **macro-F1 56,8339% → 56,2050%** (−0,6289 điểm).
Method/task tăng, contribution/problem/dataset giảm. Chưa có cải thiện đồng
đều và chưa đủ căn cứ mở rộng chạy toàn corpus.

## Kiểm tra run và điều kiện so sánh

- Hai **Tesla T4** thực tế,25 bài/GPU; inference/merge **2.868,53 giây** (~47,8
  phút), so với2.218,96 giây (~37 phút) ở3.6.
- **50/50 ID**, không missing/failed; **130 generations**, **21 validation pass /
  29 fallback**. V3.6 là127 generations,27 pass/23 fallback.
- Source kernel tải lại khớp bản push;13 file source/input khớp hash bản gửi.
  Hai JSONL chuẩn khớp manifest/bản tải; replay merged50, hai shard25 và50 audit
  files đều qua. Không có lỗi runtime merge hoặc lỗi audit mới.
- Corpus/reference/evaluator/selection và output cũ khớp snapshot trước push.
  Manifest ba lượt3.5/3.6/3.7 xác nhận cùng reference/cohort/evaluator/matcher/
  encoder file hashes/ngưỡng. Đã cộng lại counts từ per-paper và kiểm công thức.
- Chỉ kiểm/chấm output mới; không sửa generator, prompt, reference, evaluator
  hay push kernel khác trong lượt này.

## Điểm mới

| Facet | F1 v3.6 | F1 v3.7 | TP / FP / FN v3.7 | Δ TP / FP / FN |
|---|---:|---:|---:|---:|
| Problem | 41,51% | **38,46%** | 10 / 11 / 21 | −1 / 0 / +1 |
| Task | 56,12% | **59,42%** | 41 / 13 / 43 | +2 / −3 / −2 |
| Method | 58,30% | **59,84%** | 73 / 27 / 71 | +8 / +13 / −8 |
| Dataset | 80,00% | **75,86%** | 11 / 2 / 5 | −1 / 0 / +1 |
| Contribution | 48,25% | **47,45%** | 65 / 82 / 62 | +3 / +14 / −3 |
| Micro | 53,85% | **54,27%** | 200 / 135 / 202 | +11 / +24 / −11 |

Micro precision **63,00% → 59,70%**, recall **47,01% → 49,75%**. Tổng nhãn
dự đoán **300 → 335**. Method tăng79 →100 nhãn, contribution130 →147; phần
tăng TP bị bù đáng kể bởi FP. Không diễn giải Δ TP/Δ số nhãn như precision
của riêng nhãn bổ sung vì một số nhãn cũ cũng thay đổi và được ghép lại.

Theo F1 từng bài: **13 tăng,15 giảm,21 bằng**,1 không xác định do hai phía cùng
rỗng. Bài duy nhất ghép đủ năm facet vẫn là P003491, nguồn boilerplate không
phải nghiên cứu; không coi là một bài nghiên cứu hoàn hảo.

Contribution và method hiện chiếm **242/337 FP+FN (~71,81%)**. Các counts là
bất đồng matcher/reference, không phải337 lỗi ngữ nghĩa đã adjudicate.

## Mục tiêu sửa: cái gì đã có tác dụng

- **P002586:** draft method rỗng, review2 sinh semi-supervised training và
  speaker adaptation; applied/selected giữ được cả hai. Lỗi khóa bỏ hai method
  của3.6 đã hết ở run thật. Bottleneck features vẫn thiếu.
- **P001963:** phục hồi LDA, Girvan-Newman và inference mechanism, +3 TP method.
- **P003579:** phục hồi softmax classifier; **P003565:** phục hồi Eisner algorithm;
  **P004047:** có lại unsupervised morphology learning. P003565 vẫn thiếu
  online large-margin learning.
- Method rỗng dù reference có method giảm **7 →4 bài**. P000781 có meta-analysis,
  P003809 có iteration, nhưng nhãn còn quá chung so với method cụ thể nên chưa
  được matcher tính thêm TP ở hai ca này. Bốn bài còn rỗng: P001431/P002273/
  P003187/P003614.
- P001806 đã ghi finding competitive zero-shot, vốn thiếu trước đó. Matcher
  vẫn chỉ ghép được một nhãn với reference gộp few-shot/zero-shot; việc phục
  hồi nội dung này không làm tăng TP contribution. Nhãn mới còn thiếu chủ thể
  độc lập khi đọc riêng.
- P002015 tách finding về morphology/syntax features, contribution +1 TP;
  P002684 có mô tả tích hợp joint n-gram features vào discriminative model,
  contribution +1 TP. P003211 +1 TP contribution chủ yếu do cách diễn đạt/ghép
  finding, không phải chứng minh có thêm một finding hoàn toàn mới.
- Whether ở P003673 và các dataset BioNLP/BioCreative, Inria, Prague, Europarl
  vẫn giữ được. Không tái phát lỗi merge hoặc audit.

## Những lỗi quan trọng chưa sửa được

**Qualifier P002586 vẫn thiếu trong generation mới.** Cả draft/review của3.7
đều không ghi Tamil hoặc điều kiện nhiều test data hơn training data trong
contribution. Test trước push đã chứng minh code nhận được bản sửa khi raw
review có nó, nhưng run thật này không sinh bản sửa ấy. Không còn là trường
hợp code khóa bỏ qualifier vừa sinh. Matcher vẫn nhận nhãn thiếu điều kiện là
TP; semantic correctness không thể suy ra chỉ từ TP.

**Artifact vẫn yếu.** JTV(P001389), TARN(P001806), novel vision model(P001057),
POS tagging tool(P001409), reinforcement learning approach(P003002) chưa được
ghi như artifact mới ở contribution. MCMM(P003308) xuất hiện trong câu finding
nhưng vẫn không có contribution nói mô hình được đề xuất. Polya process ở
P001948 có trong draft finding nhưng không thành nhãn artifact được giới thiệu
ở output chọn cuối; TTR-LDA-Community cũng chỉ nằm trong finding/method.
Scripts được phát hành ở P003809 tiếp tục thiếu.

**Finding âm và dataset còn hồi quy.** P004047 vẫn bỏ negative BLEU trong cả3
raw attempts, chỉ giữ benefit finding. P002877 mất WMT15 đã có ở3.6; cả3 raw
dataset đều rỗng, không phải filter xóa. Yelp vẫn thiếu. P003579 vẫn gộp
NLPCC2014/Reuters; Dota/UCI vẫn là hai false acceptance theo policy named dataset.

**Contribution thêm procedure thay vì đóng góp.** P001389 thêm câu tiến hành
experiments và qualitative/quantitative evaluations, nhưng vẫn không có JTV.
P001589 đưa sử dụng abstract word forms/ANOVA evaluation vào contribution;
cần phân biệt thao tác dùng với artifact/finding mới được tác giả tuyên bố.
Không gọi mọi extra là hallucination: nhiều câu có nguồn nhưng sai vai trò hoặc
khác độ chi tiết với reference.

**Nhãn method quá ngắn hoặc bị đổi thành thành phần rời.** P001996 mất
mixed-methods framework/case study và chỉ giữ volume/exposure/content production.
P001806 giữ attention mechanisms/deep-distance measure nhưng mất temporal
alignment/video-segment relation đã có ở3.6. Prompt ưu tiên tên ngắn vẫn cần
giữ setting/quan hệ thiết yếu; không thể dùng số từ làm tiêu chí đúng nghĩa.

**Nguồn bị cắt còn bị model điền tiếp.** P003614 sinh phần kết a certain mental
state trong khi abstract dừng ở hearer will come to. Validator đã gắn lỗi
source words/evidence và output được giữ với fallback, không có validation pass
giả; detector nguồn vẫn ghi no_flag_detected. Không coi đây là source-supported
finding chỉ vì có một phần câu trùng nguồn.

## Nguyên nhân của nhãn dư: không phải code preservation tự cộng trong run này

Đã so raw/applied **mọi attempt**: không có thay đổi method/contribution do
`preserve_review_items` trong run3.7 này. Selected output chỉ có hai khác biệt
task ngoài scope (P001057 đổi evidence ID, P001181 đổi cách viết trong raw).
Vì vậy tăng21 method labels/17 contribution labels đến từ candidate model sinh
ra; chưa có căn cứ quy FP tăng cho việc Python giữ item cũ. Prompt/routing/
coverage feedback thay đổi cùng lượt, chưa có ablation tách riêng tác động.

Fallback có hai raw response liền nhau giống hệt tăng **9/23 →13/29**; applied
selection/errors không đổi trước review cuối tăng11 →14. Nhiều ca vẫn sửa chữ
hoặc lặp thay vì phục hồi ý; tăng thêm retry chưa có bằng chứng sẽ giải quyết.

## Hướng tiếp theo

Giữ bản3.7 như một mốc có recall cao hơn, không tuyên bố thay thế toàn diện3.6.
Ưu tiên contribution: tách rõ kiểm tra artifact được giới thiệu, finding dương/
âm và procedure; kiểm tra qualifier trước khi chấp nhận review. Rà các cặp
matcher/reference khác granularity trong phép đánh giá riêng, giữ ngưỡng hiện
tại để so extraction. Chưa tự chỉnh matcher hoặc sinh thêm nhãn để khớp gold.

Điểm là **embedding agreement với reference AI trên cohort phát triển50 bài**,
chưa phải human semantic F1. Đã đọc nguồn/attempts có chủ đích ở các ca sửa và
hồi quy, chưa adjudicate độc lập mọi matched/extra/missing của toàn cohort.

## Bằng chứng và tái lập

- [Report evaluator](../../../data/exp_a/evaluation/pilot50_v3_7_ai_v1/report.md),
  summary/manifest/per_paper cùng thư mục.
- [Counts, delta, retry và raw/applied diagnostics](../../../data/exp_a/evaluation/pilot50_v3_7_ai_v1/error_analysis.json).
- [50 ca có nguồn, nhãn v3.6/v3.7 và delta](../../../data/exp_a/evaluation/pilot50_v3_7_ai_v1/review_cases.jsonl).
- [Xác minh source/input/hash/replay hoàn tất](../../../data/exp_a/.kaggle/review/pilot50_v3_7_completion_verification.json).
- Raw/applied đầy đủ: `data/exp_a/generated_v3_7_pilot50/annotation_metadata.jsonl`.
- Kiểm download: `tmp/pilot37_verify.py`; phân tích: `tmp/pilot37_review.py`.

```powershell
.\.venv-qwen\Scripts\python.exe -X utf8 -B scripts/exp_a/evaluate_exp_a.py --source data/exp_a/generated_v3_7_pilot50 --gold data/exp_a/pilot50/ai_reference_v1/review_annotations.jsonl --expected-count 50 --threshold 0.85 --output data/exp_a/evaluation/pilot50_v3_7_ai_v1
.\.venv-qwen\Scripts\python.exe -X utf8 -B tmp/pilot37_review.py
.\.venv-qwen\Scripts\python.exe -X utf8 -B tmp/pilot37_verify.py
```
