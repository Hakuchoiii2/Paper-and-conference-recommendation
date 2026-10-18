"""Report the fixed contrast experiment, including pool ceilings and scope limitations."""
import collections
from pathlib import Path

from run_improve_trial import read,rows,write,digest,verify
from run_evidence_suite import bootstrap

PROJECT=Path(__file__).resolve().parents[2];DATA=PROJECT/'data/exp_d'


def main():
    root=DATA/'results/contrast_proposal_20261016_v1';analysis=root/'analysis'
    if analysis.exists():raise ValueError('Analysis exists; preserve prior report')
    manifest=read(root/'manifest.json');verify(root,manifest['files'])
    for name,h in manifest['input_hashes'].items():
        if digest(Path(name))!=h:raise ValueError('Input changed: '+name)
    cases=rows(root/'generated/sessions.jsonl');truth={r['case_id']:r for r in rows(root/'ground_truth/session_intents.jsonl')}
    by_id={c['case_id']:c for c in cases};pair_metadata=rows(root/'ground_truth/paired_designs.jsonl')
    focus=read(root/'focus_metrics.json');shuffled=read(root/'shuffle_summary.json')
    absolute=[];focus_summary=[];lookups={}
    for seed in (42,43,44):
        for noise in (.2,.5):
            name=f'seed_{seed}_noise_{noise:g}';result=root/name/'results'
            summary=read(result/'report.json')['summary']
            overall={r['model']:r for r in summary if r['group']=='overall'}
            lookups[name]={(r['case_id'],r['model']):r for r in rows(result/'details.jsonl')}
            for model in ('direction_behavior','direction_search','strict_behavior_similar','strict_behavior_predicted',
                          'proposal_behavior_predicted','proposal_behavior_similar','proposal_behavior_flipped',
                          'proposal_search_predicted','proposal_search_similar'):
                r=overall[model];absolute.append(dict(condition=name,model=model,ndcg10=r['ndcg@10'],
                    compliance1=r['intent_compliance@1'],compliance5=r['intent_compliance@5']))
            f=next(r for r in focus if r['condition']==name and r['model']=='direction_behavior' and r['group']=='overall')
            sf=[r for r in shuffled if r['condition']==name]
            noobs=read(root/'no_observations/focus_metrics.json')
            noobs=next(r for r in noobs if r['model']=='direction_behavior' and r['group']=='overall')
            focus_summary.append(dict(condition=name,accuracy=f['focus_accuracy'],coverage=f['focus_coverage'],
                no_observation_accuracy=noobs['focus_accuracy'],
                shuffled_accuracy=sum(r['accuracy'] for r in sf)/len(sf),shuffled_coverage=sum(r['coverage'] for r in sf)/len(sf)))
    paired=[]
    for noise in (.2,.5):
        ls=[lookups[f'seed_{seed}_noise_{noise:g}'] for seed in (42,43,44)]
        for family in ('strict','proposal'):
            for channel in ('behavior','search'):
                for ref in ('similar','flipped'):
                    a=f'{family}_{channel}_predicted';b=f'{family}_{channel}_{ref}'
                    for group in ('overall','intent_similar','intent_different','clear','ambiguous','none'):
                        selected=[c for c in cases if group=='overall' or group in ls[0][c['case_id'],a]['groups']]
                        for metric in ('ndcg@10','intent_compliance@1','intent_compliance@5'):
                            ds=[sum(l[c['case_id'],a]['metrics'][metric]-l[c['case_id'],b]['metrics'][metric] for l in ls)/3 for c in selected]
                            by_anchor=collections.defaultdict(list)
                            for c,delta in zip(selected,ds):by_anchor[c['query_paper_id']].append(delta)
                            leave_out=[]
                            for anchor in by_anchor:
                                kept=[v for k,vs in by_anchor.items() if k!=anchor for v in vs]
                                if kept:leave_out.append(sum(kept)/len(kept))
                            paired.append(dict(noise=noise,model=a,reference=b,group=group,metric=metric,
                                **bootstrap(ds,selected),leave_one_anchor_out_range=[min(leave_out),max(leave_out)] if leave_out else None))
    analysis.mkdir()
    write(analysis/'absolute_metrics.json',absolute);write(analysis/'focus_summary.json',focus_summary)
    write(analysis/'seed_averaged_comparisons.json',paired)
    lines=['# D: kết quả benchmark cặp intent và proposal','',
        '**Kết luận:** có bằng chứng cho cả suy hướng và tác dụng direction lên ranking trong benchmark cơ chế mới; kết luận có điều kiện trên corpus nhỏ và simulator, chưa phải hiệu quả người thật hay generalization trên anchors mới.','',
        '## 1. Vì sao cần phép thử mới?','',
        'Bộ canonical cũ có 750/750 phiên different không có candidate grade 1, nên chưa tách rõ context khỏi direction. Bộ mới giữ nguyên corpus/facet thật nhưng tạo các phiên mô phỏng mới có cả ứng viên đúng và sai hướng trong cùng context. Không sửa dữ liệu/nhãn/kết quả cũ.','',
        'Thiết kế đã ghi trước khi tính metrics: tất cả 15 tổ hợp khả thi/8 anchors, 2 directions × 3 query modes = 90 phiên. Mỗi pool gồm 1 same-focus cùng context, 1 different-focus cùng context và 18 ngoài context; có 1 grade 2 và 1 grade 1 ở mọi phiên. Cặp similar/different giữ nguyên user, cutoff, anchor, context, candidates; chỉ intent và query/phản ứng tương ứng khác nhau.','',
        'Không thể tạo thiết kế ban đầu 1 same/9 different trong corpus; kết quả thiếu hụt được giữ ở audit. Không tạo paper/facet giả để ép quota. Các focus có dữ liệu: task, method, dataset, contribution; không có problem.','',
        'Source target 1.500 phiên còn shortfall 1.410: bundle là diagnostic riêng, không tự nhận canonical complete. Synthetic chỉ dành cho observation, 4 cặp/phiên, 3 seed × 2 noise. `check_d` hiện hành kiểm tra cả bộ không observation và sáu overlay.','',
        '## 2. Luận điểm 1: evidence giúp suy facet và hướng','',
        '| Cấu hình | Accuracy behavior | Coverage behavior | Accuracy không observation | Accuracy xáo (10 lần) |',
        '|---|---:|---:|---:|---:|']
    for r in focus_summary:lines.append(f"| {r['condition']} | {r['accuracy']:.4f} | {r['coverage']:.4f} | {r['no_observation_accuracy']:.4f} | {r['shuffled_accuracy']:.4f} |")
    lines += ['', 'Unknown được tính là chưa đúng. Xáo giữ timestamps, IDs và số lượng action trong phiên; phản ứng gắn đúng bài là điều tạo tín hiệu dưới simulator. Query rõ hỗ trợ search; ambiguous/none giữ thiếu evidence đúng thiết kế. Không suy ra hành vi người thật từ kết quả này.','',
        '## 3. Luận điểm 2: tác dụng riêng của direction','',
        'Đối chứng giữ nguyên proposal scorer, focus dự đoán, C weights, context/missingness gate và secondary score không phụ thuộc direction. Chỉ đổi focus direction giữa predicted / always-similar / flipped. Bảng seed 42, noise 0,2:','',
        '| Model | nDCG@10 | Compliance@1 (chẩn đoán thêm) | Compliance@5 |',
        '|---|---:|---:|---:|']
    for r in absolute:
        if r['condition']=='seed_42_noise_0.2':lines.append(f"| {r['model']} | {r['ndcg10']:.4f} | {r['compliance1']:.4f} | {r['compliance5']:.4f} |")
    lines += ['', 'Primary chốt trước chạy là nDCG@10; compliance@1 chỉ bổ sung để quan sát việc đưa bài đúng lên đầu. Compliance@5 có trần 0,2 vì chỉ một bài grade 2; khi bài đó đã nằm trong top 5, đổi vị trí từ thứ 2 lên thứ 1 không làm chỉ số này tăng. @10 có trần 0,1. Không sửa metric/nhãn để làm tăng điểm.','',
        'Delta predicted − always-similar, trung bình ba seed trước khi bootstrap theo 8 anchors:','',
        '| Noise | Nhánh / nhóm | Metric | Delta | CI 95% theo anchor | Leave-one-anchor-out min–max |',
        '|---|---|---|---:|---|---|']
    for r in paired:
        if r['reference'].endswith('_similar') and r['model'] in ('proposal_behavior_predicted','strict_behavior_predicted') and r['group'] in ('overall','intent_different') and r['metric']=='ndcg@10':
            lines.append(f"| {r['noise']} | {r['model']} / {r['group']} | {r['metric']} | {r['mean']:+.6f} | {r['ci95']} | {r['leave_one_anchor_out_range']} |")
    lines += ['', 'CI và leave-one-out chỉ mô tả độ ổn định trong cohort 8 anchors này; không đại diện cho toàn bộ khoa học hoặc người dùng. Strict scorer vẫn là đối chứng quan trọng: hướng đúng không tự bảo đảm tổng score mềm/gate gốc chuyển nó thành cải thiện. Không dùng mức tăng giữa hai scorer để quy hết cho direction.','',
        '## 4. Proposal đề xuất','',
        '**Evidence-guided facet reranking:** suy focus/hướng bằng evidence trước cutoff; thiếu hoặc xung đột thì fallback; khi đủ evidence, giữ context, active context/focus, ưu tiên ứng viên thỏa hướng, dùng profile C làm tie-break không phụ thuộc direction. Chi tiết tại docs/proposal.md.','',
        'Proposal là phương pháp quy tắc có thể giải thích, chưa phải thuật toán mới đã được xác nhận với semantic/human relevance. Việc đạt điểm cao khi dự đoán đúng là kỳ vọng vì ranking ưu tiên trực tiếp điều kiện của nhãn overlap. Giá trị thực nghiệm là đo estimator/noise/fallback và tách direction khỏi context bằng các đối chứng công bằng.','',
        '## 5. Luận điểm có thể đưa vào báo cáo','',
        '> Trong benchmark mô phỏng cặp intent đối lập, phản ứng đầu phiên cho phép suy facet và hướng similar/different tốt hơn khi không có hoặc xáo phản ứng; với cùng ranker đề xuất và candidate pool có bài cạnh tranh hai hướng, directions dự đoán cải thiện nDCG@10 so với luôn-similar, cho thấy tác dụng của intent lên thứ tự khuyến nghị trong điều kiện được kiểm soát.','',
        'Kèm giới hạn bắt buộc: 8 anchors đã xuất hiện ở dữ liệu trước, episodes mới nhưng không phải corpus/anchor untouched; 4/5 focus; label/evidence mô phỏng và ưu tiên overlap; không chứng minh hiệu quả người dùng thật, semantic relevance độc lập hoặc novelty so với toàn bộ nghiên cứu trước.','',
        '## 6. Việc tiếp theo và tái lập','',
        '- Giữ cả kết quả null của canonical cũ và kết quả cơ chế mới; không thay số giữa hai benchmark để tuyên bố tăng thuật toán.',
        '- Mở rộng corpus thật và tạo phần giữ riêng trước nghiên cứu tiếp, đặc biệt thêm problem-focus và nhiều ứng viên đối lập cùng context; review semantic relevance độc lập.',
        '- Không tune trọng số/ngưỡng trên bundle này. Nếu thêm supervised ranker, cần split và ngân sách nhãn train riêng.',
        '- Code mới: scripts/exp_d/run_contrast_proposal.py, proposal_ranker.py; generator data/exp_d/build_contrast_sessions.py. Không sửa baseline, A/C, source corpus, validator hoặc config chung.',
        '', '```powershell','python -B -m unittest discover -s scripts/exp_d -p test_contrast_proposal.py',
        'python -B scripts/exp_d/run_contrast_proposal.py','python -B scripts/exp_d/summarize_contrast_proposal.py','```',
        '', 'Các lệnh không ghi đè output. Output chính ở data/exp_d/results/contrast_proposal_20261016_v1/. Manifest suite và analysis theo dõi input/code/output riêng.']
    report='\n'.join(lines)+'\n'
    (root/'report.md').write_text(report,encoding='utf-8')
    (DATA/'docs/contrast_report.md').write_text(report,encoding='utf-8')
    write(analysis/'manifest.json',dict(suite_manifest_sha256=digest(root/'manifest.json'),code_sha256=digest(Path(__file__)),
        files={str(p.relative_to(root)):digest(p) for p in list(analysis.iterdir())+[root/'report.md'] if p.is_file()}))
    print('CONTRAST REPORT COMPLETE: '+str(root/'report.md'))


if __name__=='__main__':main()
