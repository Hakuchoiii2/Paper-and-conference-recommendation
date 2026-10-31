"""Review frozen v4 labels; no enrichment, new papers, inferred DOI, or year changes.

Network mode only resolves identifiers ALREADY in raw, for sampled matched papers.
Default mode replays saved responses and explicit AI adjudications offline.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import csv
import hashlib
import html
import json
from pathlib import Path
import random
import re
import runpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE = ROOT / '4_catalog_mapping'
REVIEW = HERE / 'review'
OUT = HERE / 'output'
SEED = 20261031
LEGACY = ROOT / '3_mapping_reviewed/audit_mapping.py'
lib = runpy.run_path(str(LEGACY))
key = lib['key']
sha = lib['sha']
load = lib['load']
def write_csv(path, rows):
    if not rows:
        path.write_text('paper_id\n', encoding='utf-8-sig')
        return
    lib['write_csv'](path, rows)

# Independent reading of the publication names, with explicit canonical-ID crosswalk.
EXTRA = {
 'CONF_ACL_STARSEM': r'joint conference on lexical and computational semantics',
 'CONF_ACL_ANLP': r'conference on applied natural language processing',
 'CONF_ACL_FSMNLP': r'conference on finite state methods and natural language processing',
 'CONF_ACL_IWPT': r'conference on parsing technolog',
 'CONF_ICORE_13': r'computer[ -]supported cooperative work|cscw',
 'CONF_ICORE_18': r'object.oriented programming systems|oopsla',
 'CONF_ICORE_1658': r'pacific asia conference on language|pacific asia conference.*information.*computation',
 'CONF_ICORE_2268': r'learning analytics and knowledge',
 'CONF_ICORE_2355': r'learning @ scale|learning at scale',
 'CONF_ICORE_1123': r'machine learning and cybernetics',
 'CONF_ICORE_2311': r'advances in social networks analysis and mining',
 'CONF_ICORE_642': r'ieee.*conference on data mining',
 'CONF_ICORE_664': r'conference on multimedia and expo',
 'CONF_ICORE_792': r'intelligent robots and systems',
 'CONF_ICORE_1588': r'language descriptions.*tools.*applications',
}
old_reference = lib['reference_label']
CROSSWALK = {'CONF_CSCW':'CONF_ICORE_13','CONF_OOPSLA':'CONF_ICORE_18',
 'CONF_PACLIC':'CONF_ICORE_1658','CONF_ICMLC':'CONF_ICORE_1123',
 'CONF_ASONAM':'CONF_ICORE_2311','CONF_ICDM':'CONF_ICORE_642',
 'CONF_ICME':'CONF_ICORE_664','CONF_IROS':'CONF_ICORE_792'}


def reference_label(venue):
    text = re.sub(r'\s+', ' ', html.unescape(venue).casefold()).replace(' & ', ' and ')
    if 'special interest group on computational morphology' in text:
        return 'outside_main','workshop'
    # Mixed *SEM/SemEval volume titles do not establish each paper's track.
    if 'lexical and computational semantics' in text and ('workshop' in text or 'shared task' in text):
        return 'CONF_ACL_STARSEM', 'track_unclear'
    if re.search(r'\bworkshop\b|\bshared task\b|demonstration|student research|tutorial', text):
        return old_reference(venue)
    if 'european chapter of the acl' in text:
        return 'CONF_EACL','conference'
    if 'applied natural language processing conference' in text:
        return 'CONF_ACL_ANLP','conference'
    for cid, pattern in EXTRA.items():
        if re.search(pattern, text):
            if 'journal' in text or 'transactions' in text:
                return 'outside_main', 'journal'
            return cid, 'conference' if re.search(r'conference|proceedings|symposium', text) else 'track_unclear'
    cid, kind = old_reference(venue)
    return CROSSWALK.get(cid, cid), kind


lib['grade_paper'].__globals__['reference_label'] = reference_label
old_metadata=lib['metadata']


def metadata(response):
    result=old_metadata(response)
    if result and 'api.crossref.org' in response['url']:
        work=json.loads(response['text'])['message']
        subtitle=' '.join(work.get('subtitle') or [])
        if subtitle and not key(result['title']).endswith(key(subtitle)):
            result['title'] += ': '+subtitle
        # Some publishers put a complete personal name into Crossref's family field.
        result['authors'] += [a.rsplit(' ',1)[-1] for a in result['authors'] if ' ' in a]
    return result


lib['grade_paper'].__globals__['metadata']=metadata


def write_jsonl(path, records):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n' for r in records), encoding='utf-8')


def inputs():
    return [BASE/'venue_mapping.csv', *sorted((BASE/'output').glob('*')),
            ROOT.parent/'raw/csfcube/abstracts-csfcube-preds.jsonl',
            ROOT.parent/'processed/papers.jsonl', LEGACY,
            HERE/'review_mapping.py', REVIEW/'adjudications.json',
            HERE/'preprocess_cube.py', HERE/'audit_mapping.py', HERE/'README.md',
            BASE/'review/inherited/source_cache.jsonl',
            BASE/'review/inherited/alias_review.csv',
            BASE/'review/inherited/paper_evidence.jsonl']


def select(rows):
    groups = defaultdict(list)
    for r in rows:
        if r['mapping_status']=='matched':
            groups[r['conference_id']].append(r)
    rng = random.Random(SEED)
    selected = {}
    for cid in sorted(groups):
        if len(groups[cid])>=5:
            for r in rng.sample(sorted(groups[cid], key=lambda x:x['paper_id']), 5):
                selected[r['paper_id']] = 'random_per_conference'
    risk_ids = {'CONF_ACL_SIGMORPHON','CONF_ACL_FSMNLP','CONF_ACL_IWPT',
                'CONF_ICORE_1588','CONF_ACL_ANLP','CONF_ACL_STARSEM','CONF_ICLR'}
    for r in rows:
        if r['mapping_status']!='matched':
            continue
        risk = r['conference_id'] in risk_ids or any(re.search(
            r'workshop|companion|poster sessions|lake,|khandelwa',
            (e.get('venue_raw') or '')+' '+(e.get('journal_raw') or ''), re.I) for e in r['evidence'])
        if risk and r['paper_id'] not in selected:
            selected[r['paper_id']] = 'risk_only'
    return selected


def build(fetch=False):
    rows = load(BASE/'output/paper_conference_links.jsonl')
    papers = {r['paper_id']:r for r in load(ROOT.parent/'processed/papers.jsonl')}
    raw = {str(r['paper_id']):r for r in load(ROOT.parent/'raw/csfcube/abstracts-csfcube-preds.jsonl')}
    selected = select(rows)
    cache = {r['url']:r for r in load(BASE/'review/inherited/source_cache.jsonl')}
    local_cache = REVIEW/'source_cache.jsonl'
    if local_cache.exists():
        cache.update({r['url']:r for r in load(local_cache)})
    urls = {}
    for r in rows:
        if r['paper_id'] in selected:
            # Empty old_cache explicitly disables S2/DOI discovery from version 2.
            urls[r['paper_id']] = lib['paper_urls'](dict(r,title=papers[r['paper_id']]['title']),raw,[])
            urls[r['paper_id']] += lib['EXACT_PAPER_URLS'].get(r['paper_id'],[])
    adjudications = json.loads((REVIEW/'adjudications.json').read_text(encoding='utf-8'))
    required = set(u for group in urls.values() for u in group)
    required.update(u for a in adjudications['papers'] for u in a['source_urls'] if not u.endswith('.pdf'))
    if fetch:
        pending = sorted(u for u in required if u not in cache or 'getaddrinfo failed' in cache[u].get('error',''))
        with ThreadPoolExecutor(max_workers=4) as pool:
            fs = {pool.submit(lib['get'],u):u for u in pending}
            for i,f in enumerate(as_completed(fs),1):
                cache[fs[f]] = f.result()
                if i%20==0 or i==len(pending):
                    write_jsonl(local_cache,[cache[u] for u in sorted(cache)])
                    print(f'Source responses {i}/{len(pending)}',flush=True)
    outcomes = []
    for r in rows:
        if r['paper_id'] not in selected:
            continue
        out = lib['grade_paper'](dict(r,title=papers[r['paper_id']]['title']),urls[r['paper_id']],cache,raw)
        out['sample_kind'] = selected[r['paper_id']]
        out['raw_identifier_only'] = True
        outcomes.append(out)
    return rows, papers, outcomes, cache, adjudications


def derive(rows, outcomes, adjudications):
    result = copy.deepcopy(rows)
    by_id = {r['paper_id']:r for r in result}
    graded = {r['paper_id']:r for r in outcomes}
    decisions = {a['paper_id']:a for a in adjudications['papers']}
    changes=[]
    for r in result:
        if r['mapping_status']!='matched':
            continue  # Never enrich/promote unresolved or excluded records.
        pid=r['paper_id']
        outcome=graded.get(pid)
        r['mapping_review_v5'] = dict(status=outcome['status'] if outcome else 'not_paper_sampled',
            scope='paper_sample' if outcome else 'alias_only',human_verified=False)
        if pid not in decisions:
            continue
        a=decisions[pid]
        assert a['before_conference_id']==r['conference_id'], pid
        assert a['mapping_status'] in {'matched','excluded','unresolved'}
        if a['mapping_status']=='matched':
            assert a['conference_id']==r['conference_id'], 'No new conference mapping in this review'
        before=(r['mapping_status'],r['conference_id'],r['venue_type'])
        r['mapping_review_v5'].update(status=a['review_status'],scope='ai_source_adjudication',
            reason=a['reason'],source_urls=a['source_urls'])
        after=(a['mapping_status'],a['conference_id'],a['venue_type'])
        if before!=after:
            r['pre_v5_review']={k:r[k] for k in ['mapping_status','conference_id','venue_type','reason','verification_level']}
            r.update(mapping_status=after[0],conference_id=after[1],venue_type=after[2],
                     reason='v5_source_review_correction',verification_level='source_checked')
            changes.append(dict(paper_id=pid,before_status=before[0],before_conference_id=before[1],
                after_status=after[0],after_conference_id=after[1],reason=a['reason'],source_urls='; '.join(a['source_urls'])))
    # Preserve every raw/year field, evidence and existing text/ID association.
    for before,after in zip(rows,result):
        for k in ['paper_id','source_ids','year','year_source','year_status','year_candidates',
                  'publication_year','edition_year','evidence']:
            assert before.get(k)==after.get(k),(before['paper_id'],k)
    return result,changes


def artifacts(rows,papers,outcomes,cache,adjudications):
    result,changes=derive(rows,outcomes,adjudications)
    source_catalog={r['conference_id']:r for r in load(BASE/'output/conference_catalog.jsonl')}
    members=defaultdict(list)
    for r in result:
        if r['mapping_status']=='matched': members[r['conference_id']].append(r['paper_id'])
    groups=[dict(conference_id=c,paper_count=len(ids),paper_ids=sorted(ids)) for c,ids in sorted(members.items())]
    catalog=[]
    for cid in sorted(members):
        c=copy.deepcopy(source_catalog[cid])
        c['registry_sources']=[str(HERE/'venue_mapping.csv')]
        c['selection_reason']='Version-4 catalog, AI alias review and source-assisted paper sample; not human gold'
        catalog.append(c)
    aliases=list(csv.DictReader((BASE/'venue_mapping.csv').open(encoding='utf-8-sig')))
    inherited={r['venue_raw']:r for r in csv.DictReader((BASE/'review/inherited/alias_review.csv').open(encoding='utf-8-sig'))}
    overrides={a['venue_raw']:a for a in adjudications['aliases']}
    alias_audit=[]
    for a in aliases:
        if a['mapping_status']!='matched':continue
        ov=overrides.get(a['venue_raw'])
        sources=a.get('catalog_source_urls') or inherited.get(a['venue_raw'],{}).get('primary_sources','')
        record=dict(venue_raw=a['venue_raw'],before_conference_id=a['conference_id'],
            name_review='ai_name_consistent',evidence_scope='name_only_not_paper_track',
            source_urls=sources,human_verified=False,
            note='AI read-through of all 446 matched aliases; source-backed directory/inherited name evidence, not independent paper verification.')
        if ov:
            record.update(name_review=ov['review_status'],source_urls='; '.join(ov['source_urls']),note=ov['reason'])
            if ov.get('mapping_status'):
                a.update(mapping_status=ov['mapping_status'],conference_id=ov.get('conference_id') or '',
                    venue_type=ov['venue_type'],rule_id='v5_ai_source_review',note=ov['reason'])
        a['review_status']='ai_name_reviewed'
        alias_audit.append(record)
    stats=[dict(conference_id=g['conference_id'],acronym=source_catalog[g['conference_id']]['acronym'],
        conference_name=source_catalog[g['conference_id']]['canonical_name'],paper_count=g['paper_count']) for g in groups]
    stats.sort(key=lambda r:(-r['paper_count'],r['conference_id']))
    estimates=[]
    for c in catalog:
        c['aliases']=sorted(a['venue_raw'] for a in aliases if a['mapping_status']=='matched' and a['conference_id']==c['conference_id'])
    for g in groups:
        if g['paper_count']<5:continue
        a=[r for r in result if r['paper_id'] in g['paper_ids']]
        tr=sum(r['year'] is not None and r['year']<=2015 for r in a)
        te=sum(r['year'] is not None and 2016<=r['year']<=2019 for r in a)
        estimates.append(dict(conference_id=g['conference_id'],matched_count=len(a),train_estimate=tr,
            test_estimate=te,unassigned=len(a)-tr-te,eligible=tr>=3 and te>=1))
    return result,groups,catalog,aliases,alias_audit,stats,estimates,changes


def self_test():
    cases=[
      ('Proceedings of the ACL 2014 Workshop on Semantic Parsing',('outside_main','workshop')),
      ('Proceedings of the 11th Meeting of the ACL Special Interest Group on Computational Morphology and Phonology',('outside_main','workshop')),
      ('Proceedings of the 13th International Conference on Finite State Methods and Natural Language Processing',('CONF_ACL_FSMNLP','conference')),
      ('Proceedings of the 11th International Conference on Parsing Technologies',('CONF_ACL_IWPT','conference')),
      ('Proceedings of the Sixth International Conference on Learning Analytics &amp; Knowledge',('CONF_ICORE_2268','conference')),
      ('Proceedings of the 12th Conference of the European Chapter of the ACL',('CONF_EACL','conference')),
    ]
    for title,expected in cases:assert reference_label(title)==expected,(title,reference_label(title))
    return len(cases)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch',action='store_true',help='Fetch only missing raw-ID source responses for existing matched sample')
    parser.add_argument('--check',action='store_true',help='Read-only validation and deterministic offline replay')
    parser.add_argument('--self-test',action='store_true',help='Check workshop/edition/title interpretation regressions')
    args=parser.parse_args()
    tests=self_test()
    if args.self_test:
        print(json.dumps(dict(self_tests_passed=tests)))
        return
    assert not (args.fetch and args.check)
    if args.check:
        m=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
        for path,digest in m['input_hashes'].items():assert sha(Path(path))==digest,path
        for path,digest in m['output_hashes'].items():assert sha(HERE/path)==digest,path
    start_hashes={str(p):sha(p) for p in inputs()}
    rows,papers,outcomes,cache,adjudications=build(args.fetch)
    result,groups,catalog,aliases,alias_audit,stats,estimates,changes=artifacts(rows,papers,outcomes,cache,adjudications)
    data={'paper_conference_links.jsonl':result,'conference_papers.jsonl':groups,'conference_catalog.jsonl':catalog}
    assert len(result)==4182 and len({r['paper_id'] for r in result})==len(result)
    assert sum(g['paper_count'] for g in groups)==sum(r['mapping_status']=='matched' for r in result)
    assert not any(a['mapping_status']!='matched' and b['mapping_status']=='matched' for a,b in zip(rows,result))
    assert start_hashes=={str(p):sha(p) for p in inputs()},'Inputs changed'
    if args.check:
        for name,expected in data.items():assert load(OUT/name)==expected,name
        assert load(REVIEW/'paper_evidence.jsonl')==outcomes
        print(json.dumps(dict(check='passed',deterministic_replay=True,papers=len(result),raw_years_unchanged=True,baseline_unchanged=True)))
        return
    for name,records in data.items():write_jsonl(OUT/name,records)
    write_jsonl(REVIEW/'source_cache.jsonl',[cache[u] for u in sorted(cache)])
    write_jsonl(REVIEW/'paper_evidence.jsonl',outcomes)
    ai_decisions={a['paper_id']:a for a in adjudications['papers']}
    final_links={r['paper_id']:r for r in result}
    write_csv(REVIEW/'paper_sample_review.csv',[dict(
        **{k:v for k,v in r.items() if k!='observations'},
        final_review_status=ai_decisions.get(r['paper_id'],{}).get('review_status',r['status']),
        final_mapping_status=final_links[r['paper_id']]['mapping_status'],
        ai_note=ai_decisions.get(r['paper_id'],{}).get('reason','')) for r in outcomes])
    write_csv(REVIEW/'alias_review.csv',alias_audit)
    write_csv(HERE/'venue_mapping.csv',aliases)
    write_csv(REVIEW/'paper_review_overrides.csv',changes)
    write_csv(OUT/'comparison.csv',changes)
    write_csv(OUT/'conference_statistics.csv',stats)
    write_csv(REVIEW/'temporal_split_feasibility.csv',estimates)
    pending=[dict(paper_id=r['paper_id'],conference_id=r['baseline_conference_id'],
        status=r['status'],sample_kind=r['sample_kind'],reference_urls=r['reference_urls'])
        for r in outcomes if r['status']!='reference_agreement' and r['paper_id'] not in {a['paper_id'] for a in adjudications['papers']}]
    if pending:write_csv(REVIEW/'pending_review.csv',pending)
    counts=dict(Counter(r['mapping_status'] for r in result))
    sample_counts={kind:dict(Counter(r['status'] for r in outcomes if r['sample_kind']==kind)) for kind in ['random_per_conference','risk_only']}
    keep=[r for r in estimates if r['eligible']]
    report=['# Bản 5 — review mapping đã chốt của bản 4','',
        'AI review alias và đối chiếu mẫu bài bằng nguồn; không phải human gold, không phải kiểm chứng từng bài toàn corpus.',
        'Không enrichment: không tìm DOI mới, không dùng cache S2/tập 2, không truy arXiv, không thêm bài hoặc nâng unresolved/excluded thành matched. Chỉ dùng DOI/ACL ID có sẵn trong raw để xác minh mẫu matched; năm raw giữ nguyên.', '',
        f'- Alias đã đọc rà soát: {len(alias_audit)} (toàn bộ alias matched bản 4). Nguồn tên không chứng minh track từng bài.',
        f'- Mẫu mới: {sum(r["sample_kind"]=="random_per_conference" for r in outcomes)} bài ngẫu nhiên (5 bài × 41 hội nghị n ≥ 5), seed {SEED}; thêm {sum(r["sample_kind"]=="risk_only" for r in outcomes)} ca rủi ro. Mẫu phân tầng không dùng như ước lượng precision toàn corpus.',
        f'- Chỉnh nhãn có chứng cứ: {len(changes)} bài. Xem review/paper_review_overrides.csv và review/adjudications.json.',
        f'- AI phân xử bổ sung {len(adjudications["papers"])} bài; kết quả trong paper_sample_review.csv có cả trạng thái tự động và kết luận sau AI.',
        f'- Sau review: {counts}; {len(groups)} hội nghị/joint còn matched.',
        f'- Mẫu chưa chốt ở cấp bài: {len(pending)}; xem review/pending_review.csv. Giữ nhãn cũ nếu chưa có căn cứ sửa; không gọi các bài này source_verified.', '',
        '## Kết quả đối chiếu tự động trước AI phân xử','',json.dumps(sample_counts,ensure_ascii=False,indent=2),'',
        'reference_agreement = metadata phù hợp danh tính và cùng hội nghị, không phải precision được người chấm đo. identity_review/no_reference không tự chứng minh mapping sai. Kết luận AI bổ sung nằm riêng trong adjudications.json.', '',
        '## Các thay đổi chính','',
        'Sửa ANLP@EMNLP (Arabic NLP workshop, không phải Applied NLP conference); SIGMORPHON và LDTA; các bài workshop bị gộp vào ACL/EACL/EMNLP/IJCNLP/ICLR; xét đúng ấn bản workshop COLT 1992 và HLT 1993. FSMNLP 2017 và IWPT 2009 được giữ vì nguồn của đúng ấn bản ghi conference.',
        'Các record trộn title/tác giả, nhiều phiên bản công bố hoặc chưa rõ track companion chuyển unresolved theo từng bài. Không gán sang conference mới. Nguồn tên bare conference không chứng minh main track của mọi bài.', '',
        '## Khả thi chia theo năm raw — chỉ thống kê, chưa tạo train/test','',
        f'{len(estimates)} hội nghị có n ≥ 5; {sum(r["matched_count"] for r in estimates)} bài. Giữ thêm ≥ 3 train (≤ 2015), ≥ 1 test (2016–2019): {len(keep)} hội nghị, {sum(r["train_estimate"] for r in keep)} train và {sum(r["test_estimate"] for r in keep)} test dự kiến. Bài thiếu/mâu thuẫn năm không phân vào split.', '',
        '## Chạy lại','', 'python review_mapping.py  # offline, tái lập từ snapshot và kết luận đã lưu',
        'python review_mapping.py --check  # chỉ đọc, kiểm tra hash và dựng lại mapping',
        'python review_mapping.py --fetch  # chỉ lấy URL nguồn còn thiếu của mẫu matched', '',
        'Bản 4 giữ nguyên. Chưa chia train/test và chưa xây profile/mô hình. Các ca chưa xác minh và bài không nằm trong mẫu vẫn là giới hạn của review.']
    for path in [OUT/'report.md',REVIEW/'report.md']:
        path.write_text('\n'.join(report)+'\n',encoding='utf-8')
    outputs=[p for folder in [OUT,REVIEW] for p in folder.glob('*') if p.is_file() and p.name not in {'manifest.json','catalog_manifest.json','venue_directory.jsonl','venue_sources.jsonl'}]
    outputs.append(HERE/'venue_mapping.csv')
    m=dict(dataset_version='5_mapping_reviewed',mode='existing_mapping_review_only',human_verified=False,
        paper_enrichment=False,new_doi_discovery=False,arxiv_lookups=0,raw_years_unchanged=True,
        statuses=counts,conferences=len(groups),alias_sample=len(alias_audit),paper_sample=len(outcomes),
        self_tests_passed=tests,ai_paper_adjudications=len(adjudications['papers']),
        source_outcomes=sample_counts,corrections=len(changes),pending_sample=len(pending),
        input_hashes=start_hashes,output_hashes={str(p.relative_to(HERE)).replace('\\','/'):sha(p) for p in outputs})
    (OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in m.items() if k not in {'input_hashes','output_hashes'}},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
