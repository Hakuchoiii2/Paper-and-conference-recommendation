"""Summarize an immutable evidence suite, including null results and pool confounding."""
import collections
import argparse
from pathlib import Path
import sys

from run_improve_trial import read,rows,digest,verify,write
from run_evidence_suite import bootstrap

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh',action='store_true',help='Regenerate analysis files only; never the suite inputs/results')
    args=parser.parse_args()
    root=HERE/'results/evidence_20261016_v1'
    output=root/'analysis'
    if output.exists() and not args.refresh:raise ValueError('Analysis already exists; use --refresh for analysis only')
    manifest=read(root/'manifest.json')
    verify(root,manifest['files'])
    for name,value in manifest['input_hashes'].items():
        if digest(Path(name))!=value:raise ValueError('Input changed: '+name)
    source=HERE/'workspace_baseline_20261016_v1'
    cases=rows(source/'data/exp_d/generated/sessions.jsonl')
    truth={r['case_id']:r for r in rows(source/'data/exp_d/ground_truth/session_intents.jsonl')}
    grades=collections.defaultdict(collections.Counter)
    for r in rows(source/'data/exp_d/ground_truth/intent_labels.jsonl'):
        grades[r['case_id']][r['relevance']]+=1
    panel=rows(root/'expanded_overlay/generated/sessions.jsonl')
    panel_ids={c['case_id'] for c in panel}
    pool=[]
    for cohort,selected in [('canonical',cases),('expanded',panel)]:
        for direction in ('similar','different'):
            subset=[c for c in selected if truth[c['case_id']]['directions'][truth[c['case_id']]['focus_facet']]==direction]
            pool.append(dict(cohort=cohort,direction=direction,cases=len(subset),
                anchors=len({c['query_paper_id'] for c in subset}),
                mixed_grade1_grade2=sum(grades[c['case_id']][1]>0 and grades[c['case_id']][2]>0 for c in subset),
                grade1=sum(grades[c['case_id']][1] for c in subset)))
    # Average repeated noise draws at case level BEFORE cluster bootstrap over anchors.
    paired=[]
    for noise in (.2,.5):
        lookups=[]
        for seed in (42,43,44):
            path=root/f'expanded_overlay/seed_{seed}_noise_{noise:g}/results/details.jsonl'
            lookups.append({(r['case_id'],r['model']):r for r in rows(path)})
        for family in ('strict','m0'):
            for channel in ('behavior','search'):
                for control in ('similar','flipped'):
                    for group in ('overall','intent_similar','intent_different','anchor_audit'):
                        a=f'{family}_{channel}_predicted';b=f'{family}_{channel}_{control}'
                        subset=[c for c in panel if group=='overall' or group in lookups[0][c['case_id'],a]['groups']]
                        for metric in ('ndcg@10','intent_compliance@5'):
                            delta=[]
                            for c in subset:
                                values=[l[c['case_id'],a]['metrics'][metric]-l[c['case_id'],b]['metrics'][metric] for l in lookups]
                                delta.append(sum(values)/len(values))
                            paired.append(dict(noise=noise,model=a,reference=b,group=group,metric=metric,
                                               repeats_averaged=3,**bootstrap(delta,subset)))
    # Reuse original evaluator-owned oracle predictions for these identical canonical cases.
    sys.path[:0]=[str(source/'scripts'),str(source)]
    from experiment_runner import evaluate_predictions
    from baseline_common import aggregate
    oracle=[r for r in rows(HERE/'results/baseline_20261016_v1/predictions.jsonl')
            if r['model']=='oracle_intent' and r['case_id'] in panel_ids]
    assert all(r['privileged_information'] for r in oracle)
    judged={c['case_id']:{} for c in panel}
    for r in rows(root/'expanded_overlay/ground_truth/intent_labels.jsonl'):
        judged[r['case_id']][r['candidate_id']]=r['relevance']
    groups={cid:truth[cid]['query_mode'] for cid in panel_ids}
    oracle_details=evaluate_predictions(oracle,panel,judged,groups,[5,10],truth)
    output.mkdir(exist_ok=args.refresh)
    write(output/'oracle_reference.json',dict(privileged_information=True,source='original evaluator predictions, same sessions/pools',
                                             predictions=oracle,summary=aggregate(oracle_details)))
    write(output/'pool_audit.json',pool);write(output/'seed_averaged_comparisons.json',paired)
    evidence=read(root/'focus_evidence.json');design=read(root/'design.json')
    split=design['anchor_split'];split_counts=collections.Counter(split.values())
    focus_rows=[]
    for seed in (42,43,44):
        for noise in (.2,.5):
            condition=f'seed_{seed}_noise_{noise:g}'
            subset=[r for r in evidence if r['condition']==condition]
            aligned=next(r for r in subset if r['arm']=='aligned');none=next(r for r in subset if r['arm']=='no_observations')
            shuffled=[r for r in subset if r['arm']=='shuffled']
            focus_rows.append(dict(condition=condition,aligned=aligned,no_observations=none,
                shuffled_mean_accuracy=sum(r['accuracy'] for r in shuffled)/len(shuffled),
                shuffled_accuracy_range=[min(r['accuracy'] for r in shuffled),max(r['accuracy'] for r in shuffled)],
                shuffled_mean_coverage=sum(r['coverage'] for r in shuffled)/len(shuffled)))
    write(output/'focus_summary.json',focus_rows)
    canonical=[r for r in read(root/'paired_comparisons.json') if r['condition']=='canonical']
    def fmt(value):return 'N/A' if value is None else f'{value:.6f}'
    def ci(row):return '['+', '.join(fmt(v) for v in row['ci95'])+']' if row['ci95'] else 'N/A'
    lines=['# Kết quả bổ sung bằng chứng cho thực nghiệm D','',
        'Ngày chạy: 16/10/2026. Đọc lại README D và protocol 2.0 trước triển khai. Không sửa dataset canonical, nhãn, baseline, scorer/evaluator/validator hoặc simulator gốc.','',
        '## 1. Thiết kế và phạm vi kết luận','',
        '- Kết quả chính: giữ nguyên scorer, weights C, missingness và gate context của protocol; chỉ can thiệp hướng tại focus dự đoán: predicted / always-similar / flipped. Context luôn giữ similar, unknown giữ nguyên.',
        '- Kết quả phụ: cùng M0 priority trong ba nhánh, với điểm phá hòa lấy từ all-similar để direction dự đoán không lọt vào nhánh đối chứng qua secondary score. M0 là mở rộng policy, không phải scorer gốc của protocol.',
        '- Canonical: 1.500 phiên/57 anchors. Overlay mở rộng riêng: 171 phiên/57 anchors, chọn tối đa 3 phiên mỗi anchor bằng hash public case ID, không chọn theo điểm/nhãn; giữ nguyên candidates/query/intent/relevance/cutoff nguồn.',
        '- Overlay có 684 exposures/1.368 interactions mỗi cấu hình, 3 seeds × 2 noise. Synthetic chỉ dành cho observation; matching, thời gian và nhãn được check_d hiện hành kiểm tra. Không nhập chúng vào corpus/A silver.',
        '- Xáo action trong từng phiên, giữ nguyên IDs, exposures, timestamps và phân bố action; 10 lần xáo mỗi cấu hình. Đây là negative control, không gọi là phản ứng simulator gốc hợp lệ về utility.',
        f'- Chia anchor bằng hash: {dict(split_counts)}. Các phần không trùng anchor, nhưng canonical đã được xem trong các lượt trước, vì vậy đây là retrospective audit, chưa phải test hoàn toàn chưa chạm.',
        '- Không train/tune hoặc đổi threshold. CI 95% dùng 2.000 cluster bootstrap theo anchor; gộp seed bằng trung bình theo phiên trước khi bootstrap, không coi ba seed là ba cohort độc lập. Nhiều phép so mang tính thăm dò, không diễn giải CI riêng lẻ thành chứng minh tổng quát.','',
        '## 2. Bằng chứng phản ứng giúp suy hướng','',
        '| Cấu hình | Accuracy có phản ứng đúng liên kết | Accuracy không phản ứng | Accuracy xáo trung bình | Coverage xáo trung bình |',
        '|---|---:|---:|---:|---:|']
    for r in focus_rows:lines.append(f"| {r['condition']} | {r['aligned']['accuracy']:.4f} | {r['no_observations']['accuracy']:.4f} | {r['shuffled_mean_accuracy']:.4f} | {r['shuffled_mean_coverage']:.4f} |")
    lines += ['', 'Accuracy được tính trên focus thật khi đánh giá; unknown tính chưa đúng. Xáo làm thay đổi cả coverage nên không chỉ so accuracy trên những phiên đã quyết định. Việc xác định focus từ cấu trúc cặp được kiểm soát cũng là giả định của simulator.', '',
              '## 3. Tác dụng riêng của direction với scorer gốc','',
              'Delta = predicted − always-similar, cùng focus dự đoán và cùng scorer. Bảng overlay đã trung bình 3 seed ở mỗi noise.','',
              '| Bộ / noise | Nhánh | Metric | Delta | CI 95% theo anchor |', '|---|---|---|---:|---|']
    for r in canonical:
        if r['model'].startswith('strict_') and r['reference'].endswith('_similar') and r['group']=='overall':
            lines.append(f"| Canonical | {r['model']} | {r['metric']} | {fmt(r['mean'])} | {ci(r)} |")
    for r in paired:
        if r['model'].startswith('strict_') and r['reference'].endswith('_similar') and r['group']=='overall':
            lines.append(f"| Overlay noise {r['noise']} | {r['model']} | {r['metric']} | {fmt(r['mean'])} | {ci(r)} |")
    lines += ['', 'Xem summary.csv/report.md của từng cấu hình để đọc điểm tuyệt đối và nhóm focus, query mode, intent similar/different, anchor audit. Các so sánh với flipped có trong paired_comparisons.json và seed_averaged_comparisons.json.','',
              '## 4. Đối chứng M0 và giới hạn pool','',
              '| Bộ | Intent thật | Phiên | Phiên có cả grade 1 và 2 | Tổng candidate grade 1 |', '|---|---|---:|---:|---:|']
    for r in pool:lines.append(f"| {r['cohort']} | {r['direction']} | {r['cases']} | {r['mixed_grade1_grade2']} | {r['grade1']} |")
    lines += ['', 'Grade 1 là đúng context nhưng sai hướng focus. Khi các phiên different không có grade 1, ranker không phải lựa chọn giữa hai hướng trong cùng context; do đó khó kiểm chứng lợi ích riêng của different. Không sửa nhãn hoặc đổi pool trong lượt kiểm tra này.','',
              '| Bộ / noise | Nhánh M0 | Metric | Delta predicted − similar | CI 95% |', '|---|---|---|---:|---|']
    for r in paired:
        if r['model'].startswith('m0_') and r['reference'].endswith('_similar') and r['group']=='overall':
            lines.append(f"| Overlay noise {r['noise']} | {r['model']} | {r['metric']} | {fmt(r['mean'])} | {ci(r)} |")
    lines += ['', 'So predicted với flipped (trung bình 3 seed, nhóm overall):', '',
              '| Noise | Nhánh | Metric | Delta predicted − flipped | CI 95% |',
              '|---|---|---|---:|---|']
    for r in paired:
        if r['reference'].endswith('_flipped') and r['group']=='overall' and r['model'].endswith('behavior_predicted'):
            lines.append(f"| {r['noise']} | {r['model']} | {r['metric']} | {fmt(r['mean'])} | {ci(r)} |")
    lines += ['', 'Đảo hướng có thể làm giảm kết quả ở các phiên similar có candidates cạnh tranh, nhưng predicted thắng flipped chưa đủ chứng minh tốt hơn đối chứng luôn-similar; phải đọc cả hai phép so.', '',
              '## 5. Luận điểm được hỗ trợ và điều chưa chứng minh','',
        '**Luận điểm 1 — có bằng chứng:** trong simulator matched-pair hiện tại, phản ứng gắn đúng bài mang tín hiệu để suy similar/different; đối chứng không phản ứng và xáo action giúp phân biệt tín hiệu này khỏi việc chỉ có thêm log.', '',
        '**Luận điểm 2 — cần đọc theo độ lớn thực tế:** phép so strict ở mục 3 mới tách tác dụng hướng khỏi scorer/weights/gate. Không lấy mức tăng M0 so baseline cũ làm mức tăng riêng của direction. Chênh lệch nhỏ hoặc CI chứa 0 không đủ cho khẳng định mạnh.', '',
        '**Giới hạn quyết định:** pool hiện tại thiếu hoàn toàn grade 1 ở nhóm different. M0 có điểm cao trên nhãn overlap không tự chứng minh hiểu nhu cầu muốn khác; nếu predicted bằng always-similar thì phải báo đó là kết quả không phân biệt được tác dụng.', '',
        '**Chưa chứng minh:** hiệu quả với người thật, quan hệ nhân quả trên log thực, semantic relevance độc lập, tính mới thuật toán, hoặc generalization trên test chưa từng quan sát.', '',
        '## 6. Bước tiếp đúng protocol','',
        'Nếu mục tiêu bắt buộc chứng minh tác dụng different, thiết kế benchmark đối chứng riêng có cả bài cùng/khác focus trong cùng context, dùng corpus/facet thật và báo shortfall nếu không đủ; chốt intent trước sinh query/reaction/labels, giữ observation ngoài pool và tôn trọng cutoff. Không thay nhãn canonical cũ. Cần một phần dữ liệu/corpus được giữ riêng thật sự trước phát triển tiếp.', '',
        'Không cần tiếp tục tải model để khắc phục thiếu đối chứng trong candidate pool. Có thể hoàn thành báo cáo thực nghiệm mô phỏng bằng cả phát hiện tích cực lẫn giới hạn này.', '',
        '## 7. File và tái lập','',
        '- `data/exp_d/run_evidence_suite.py`: runner suite; output mặc định `data/exp_d/results/evidence_20261016_v1/`.',
        '- `data/exp_d/summarize_evidence.py`: tạo báo cáo phân tích sau khi suite hoàn tất.',
        '- `analysis/oracle_reference.json`: đối chứng đặc quyền từ evaluator cũ cho đúng 171 phiên/pools; oracle không dùng cho public scorer và không đổi theo observation.',
        '- Mỗi condition có predictions/details/report/summary/focus metrics, paired comparisons và case studies. Không có case giảm ở một nhóm thì không bịa case giảm.',
        '- `design.json` ghi quy tắc cố định trước khi đánh giá; `manifest.json` kiểm input/code/output; analysis có manifest riêng.',
        '', '```powershell','python -B -m unittest discover -s data/exp_d -p test_evidence_controls.py',
        'python -B data/exp_d/run_evidence_suite.py','python -B data/exp_d/summarize_evidence.py','```',
        '', 'Suite từ chối ghi đè output; nếu chạy lại cần --output tên mới và điều chỉnh đường dẫn input của summarizer tương ứng.']
    lines += ['', '## 8. Ví dụ phiên và cách đọc kết quả', '',
              'Các ví dụ chọn sau đánh giá để giải thích, không phải tiêu chí chọn dataset.', '',
              '| Bộ | Family / loại | Case | Focus / intent thật | Delta compliance@5 predicted − similar |',
              '|---|---|---|---|---:|']
    for name,path in [('canonical',root/'canonical'),('noise 0,2',root/'expanded_overlay/seed_42_noise_0.2/results'),
                      ('noise 0,5',root/'expanded_overlay/seed_42_noise_0.5/results')]:
        examples=read(path/'case_studies.json')
        for r in examples:
            if r['family']=='strict' or r['category']=='tie':
                t=r['truth'];focus=t['focus_facet']
                lines.append(f"| {name} | {r['family']} / {r['category']} | {r['case']['case_id']} | "
                             f"{focus} / {t['directions'][focus]} | {r['compliance_delta']:+.4f} |")
    lines += ['', 'Case tie có thể do thiếu evidence (mọi nhánh fallback), candidate pool không có bài phân biệt hướng, hoặc scorer/gate cho các thứ tự không đổi; xem predictions cùng case_id để xác định từng trường hợp, không mặc định mọi tie cùng nguyên nhân.',
              'Case gain/loss trong strict là chênh lệch khi chỉ đổi direction ở focus dự đoán. Grade 1 trong pool là điều kiện để tách được đúng/sai hướng trong cùng context; thiếu nó hạn chế khả năng diễn giải điểm cao của M0.']
    text='\n'.join(lines)+'\n'
    (output/'report.md').write_text(text,encoding='utf-8')
    (HERE/'docs/evidence_report.md').write_text(text,encoding='utf-8')
    write(output/'manifest.json',dict(suite_manifest_sha256=digest(root/'manifest.json'),
          summary_code_sha256=digest(Path(__file__)),
          files={p.name:digest(p) for p in sorted(output.iterdir()) if p.is_file() and p.name!='manifest.json'}))
    print('EVIDENCE ANALYSIS COMPLETE: '+str(output/'report.md'))


if __name__=='__main__':main()
