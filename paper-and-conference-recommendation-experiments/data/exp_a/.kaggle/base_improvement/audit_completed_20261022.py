"""Read-only checks of downloaded pilot artifacts; writes a local audit report."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE / 'completed_20261022_v2/base_v1_r1_r2'
SCORES = BASE / 'summary_20261022_v2/base_v1_r1_r2/results'
OUT = BASE.parents[1] / 'evaluation/base_v1_improvement_pilot50_20261022'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

checks = []
def check(value, name):
    if not value:
        raise AssertionError(name)
    checks.append(name)

summary = read(SCORES / 'experiment_summary.json')
settings = summary['settings']
release = read(BASE / 'release_20261022_v2/settings.json')
check(settings == release, 'Cloud settings equal verified v2 release')
check(digest({k:v for k,v in settings.items() if k != 'signature'}) == settings['signature'], 'Settings signature')
check(hashlib.sha256((ROOT/'improvement.py').read_bytes()).hexdigest() == settings['runner_sha256'], 'Cloud runner hash')
check(summary['status'] == 'complete' and summary['paper_count'] == 50, 'Completed summary, 50 papers')
check(not summary['R4_performed'] and not summary['training_performed'], 'No R4 or training')
ids = set(settings['paper_ids'])
records, evaluations, derived, comparisons = {}, {}, {}, {}
for arm in ('R0','R1','R2'):
    paths = list((ROOT/f'results/{arm}/records').glob('*.json'))
    check(len(paths) == 50 and {p.stem for p in paths} == ids, arm+' exact cohort')
    records[arm] = {}
    for path in paths:
        envelope = read(path)
        r = envelope['record']; pid = r['paper_id']; audit = r['audit']
        check(envelope['signature'] == settings['baseline_signature' if arm == 'R0' else 'signature'], arm+'/'+pid+' signature')
        check(envelope['record_sha256'] == digest(r), arm+'/'+pid+' checksum')
        check(pid == path.stem and audit['model'] == settings['model']['model'] and audit['model_revision'] == settings['model']['revision'], arm+'/'+pid+' identity and model')
        check(audit['quantization'] == 'nf4_double' and audit['enable_thinking'] is False, arm+'/'+pid+' NF4 and thinking off')
        params = audit['request_parameters']
        check(params['max_attempts'] == 3 and params['max_new_tokens'] == 2048 and params['do_sample'] is False, arm+'/'+pid+' generation config')
        check(1 <= audit['attempts_used'] <= 3 and audit['attempts_used'] == len(audit['attempt_scores']), arm+'/'+pid+' call budget')
        if arm == 'R0':
            check(hashlib.sha256(path.read_bytes()).hexdigest() == settings['r0_record_sha256'][pid], arm+'/'+pid+' immutable baseline')
        else:
            trace = r['call_trace']
            check(r['arm'] == arm and len(trace) == audit['attempts_used'], arm+'/'+pid+' call trace')
            check(r['new_cost']['calls'] == sum(not t['inherited'] for t in trace), arm+'/'+pid+' new cost')
            check(r['baseline_record_sha256'] == settings['r0_record_sha256'][pid], arm+'/'+pid+' baseline linkage')
            if arm == 'R2':
                first = audit['attempt_scores'][0]
                original = records['R0'][pid]['audit']['attempt_scores'][0]
                check(all(first[k] == original[k] for k in ('raw_output','seed','stage','attempt','usage','generation_seconds')), arm+'/'+pid+' exact inherited draft')
                check(trace[0]['inherited'] and all(not t['inherited'] and t['repair_packet'] is not None for t in trace[1:]) and r['new_cost']['calls'] <= 2, arm+'/'+pid+' targeted repair budget')
            else:
                check(all(not t['inherited'] and t['repair_packet'] is None for t in trace), arm+'/'+pid+' fresh calls')
        records[arm][pid] = r
    rows = list(records[arm].values())
    metrics = dict(calls=sum(r['audit']['attempts_used'] for r in rows), fallback=sum(r['fallback_used'] for r in rows), invalid_drafts=sum(bool(r['audit']['attempt_scores'][0]['validation_errors']) for r in rows))
    if arm != 'R0':
        metrics.update(new_calls=sum(r['new_cost']['calls'] for r in rows), invalid_to_valid=sum(r['repair_transitions']['invalid_to_valid'] for r in rows), valid_to_invalid=sum(r['repair_transitions']['valid_to_invalid'] for r in rows))
    published = next(r for r in summary['arms'] if r['arm'] == arm)
    check(all(metrics[k] == published[k] for k in metrics), arm+' recomputed operational metrics')
    derived[arm] = metrics
    evaluation = read(SCORES/arm/'evaluation.json')
    evaluations[arm] = evaluation
    check(len(evaluation['details']) == 50 and {d['paper_id'] for d in evaluation['details']} == ids, arm+' evaluation cohort')
    for key in ('tp','fp','fn'):
        count = sum(c[key] for d in evaluation['details'] for c in d['comparison'].values())
        check(count == evaluation['micro'][key] == published[key], arm+' recomputed '+key)
    m = evaluation['micro']
    check(abs(2*m['tp']/(2*m['tp']+m['fp']+m['fn'])-m['f1']) < 1e-12, arm+' F1 arithmetic')
    for d in evaluation['details']:
        for facet,c in d['comparison'].items():
            check(c['tp']+c['fp'] == len(records[arm][d['paper_id']]['facets'][facet]), arm+'/'+d['paper_id']+'/'+facet+' scored prediction count')

def paper_f1(d):
    t = {k:sum(c[k] for c in d['comparison'].values()) for k in ('tp','fp','fn')}
    denom = 2*t['tp']+t['fp']+t['fn']
    return 2*t['tp']/denom if denom else 1.0

baseline = {d['paper_id']:d for d in evaluations['R0']['details']}
for arm in ('R1','R2'):
    diffs = [(paper_f1(d)-paper_f1(baseline[d['paper_id']]),d['paper_id']) for d in evaluations[arm]['details']]
    comparisons[arm] = dict(improved=sum(d>1e-12 for d,_ in diffs),worse=sum(d < -1e-12 for d,_ in diffs),tied=sum(abs(d)<=1e-12 for d,_ in diffs),worst=sorted(diffs)[:5],best=sorted(diffs,reverse=True)[:5])
    comparisons[arm]['draft_valid_semantic_regressions'] = [pid for delta,pid in diffs if delta < -1e-12 and not records[arm][pid]['audit']['attempt_scores'][0]['validation_errors']]

report = dict(status='passed',check_count=len(checks),checks=checks,derived=derived,comparisons=comparisons,summary=summary,limitations=['Reused development cohort with frozen AI reference; human review pending.', 'Verified downloaded records and score arithmetic; embeddings were not rerun locally.', 'Validator validity does not establish semantic correctness.'])
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'completion_audit_20261022.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines = ['# Kiểm tra kết quả pilot50 R1/R2 — 22/10/2026', '',
    'Kaggle kernel `htnkhi/exp-a-base-v1-r1-r2-pilot50` được kiểm tra trực tiếp ở trạng thái COMPLETE. Kết quả khớp settings của release v2.', '',
    f'Đạt {len(checks)} kiểm tra trên 150 record: đủ cohort, checksum/signature, R0 bất biến, model/revision/NF4, thinking off, greedy, cap 3 × 2048, R2 kế thừa đúng raw draft và tối đa 2 calls mới. Đối chiếu counts từng bài với evaluation và công thức F1; không chạy lại embeddings tại máy local.', '',
    '| Arm | Micro F1 (%) | Δ R0 (đpt) | Macro F1 (%) | TP/FP/FN | Fallback | Calls mới / tổng |',
    '|---|---:|---:|---:|---|---:|---:|']
base_f1 = summary['arms'][0]['f1']
for r in summary['arms']:
    lines.append(f"| {r['arm']} | {100*r['f1']:.4f} | {100*(r['f1']-base_f1):+.4f} | {100*r['macro_f1']:.4f} | {r['tp']}/{r['fp']}/{r['fn']} | {r['fallback']} | {r['new_calls']} / {r['calls']} |")
lines += ['', 'R0 là kết quả lịch sử nên calls mới bằng 0; R2 có 75 calls mới + 50 draft kế thừa. Không so sánh 75 calls của R2 với 134 calls lịch sử như chi phí end-to-end.', '',
    '| Facet F1 (%) | R0 | R1 | R2 |', '|---|---:|---:|---:|']
for facet in ('problem','task','method','dataset','contribution'):
    lines.append('| '+facet+' | '+' | '.join(f"{100*evaluations[a]['by_facet'][facet]['f1']:.2f}" for a in ('R0','R1','R2'))+' |')
lines += ['', '- R1: Micro F1 giảm 1,32 đpt; method giảm 2,93 đpt, problem giảm 9,00 đpt. Ví dụ bổ sung hiện chưa đem lại cải thiện tổng thể.',
    '- R2: Micro F1 chỉ tăng 0,14 đpt, Macro F1 giảm 0,89 đpt. FP giảm 151 → 144, nhưng TP cũng giảm 217 → 215 và FN tăng 185 → 187. Chưa có bằng chứng cải thiện chất lượng tổng thể đáng tin cậy.',
    '- R2 sửa 19/37 draft lỗi thành hợp lệ theo validator; R0 kết thúc còn 33 fallback, R2 còn 18. Không có draft hợp lệ chuyển thành không hợp lệ theo validator; điều này không chứng minh không có suy giảm ngữ nghĩa.',
    '- Cả hai arm đều làm giảm mạnh problem F1; R2 tăng nhẹ method/contribution/dataset. Cần xem các item bị xóa, thay đổi biên phrase hoặc tách finding để đánh đổi source-validity lấy coverage.', '']
for a,c in comparisons.items():
    lines.append(f"- {a} so với final R0 theo micro F1 từng bài: {c['improved']} tăng, {c['worse']} giảm, {c['tied']} bằng. Các bài giảm mạnh để review: {', '.join(pid for _,pid in c['worst'][:3])}.")
lines += ['', 'Cập nhật sau review nguồn/trace: P002471 vốn đã có hai item từ R0; R2 đổi chủ ngữ cụ thể thành đại từ it để khớp evidence A2, làm contribution TP từ 1 xuống 0 theo scorer. P001431 là không phục hồi method `a synthesis of the literature` mà review R0 đã bổ sung, không phải xóa method có sẵn trong cached draft. Xem `error_review_20261022.md` để tách lỗi model, validator và reference/scorer.', '',
    'Đề xuất: giữ R0 làm mốc, chưa ghép R4. Review các trường hợp R2 sửa validator nhưng giảm F1, đặc biệt problem và finding dài; chỉ điều chỉnh sau khi kiểm tra nguồn. Đây là pilot phát triển đã dùng lại và reference AI, human review còn pending; cần cohort mới để xác nhận generalization.', '',
    'Nguồn: `completion_audit_20261022.json`, các file evaluation/experiment_summary tải từ Kaggle trong `data/exp_a/.kaggle/base_improvement/summary_20261022_v2/` và 150 record trong `completed_20261022_v2/`.']
(OUT/'completion_review_20261022.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ('status','check_count','derived','comparisons')},ensure_ascii=False,indent=2))
