"""Create/check a deterministic temporal split of reviewed v5 matched labels only."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1]
DEST = HERE/'splits/temporal_2015_2016_2019'
CONFIG = dict(dataset_version='5_mapping_reviewed',split_name='temporal_2015_2016_2019',
    required_mapping_status='matched',require_review_usable_for_split=True,
    min_matched_per_conference=5,min_train_per_conference=3,min_test_per_conference=1,
    total_threshold_basis='all_reviewed_matched_before_year_filter',
    year_field='paper_conference_links.year',year_origin='csfcube_raw.metadata.year',
    train_year_max=2015,test_year_min=2016,test_year_max=2019,
    missing_or_conflicting_year='exclude',outside_test_upper_bound='exclude',
    failed_conference='exclude_entire_conference_from_both_splits',
    sort_order=['conference_id','year','paper_id'],random_sampling=False,
    same_year_tie_breaker='paper_id',input_text_fields=['title','abstract'],
    target='conference_id',numeric_target='label_index',numeric_label_order='conference_id ascending',
    profile_data='train_only',test_usage='evaluation_only',dev_split_created=False)


def encode_json(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')


def encode_jsonl(rows):
    return ''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows).encode('utf-8')


def encode_csv(rows):
    assert rows,'A report must not be silently empty'
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8-sig')


def load(path):
    with path.open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    paths=[HERE/'output/paper_conference_links.jsonl',HERE/'output/conference_catalog.jsonl',
        HERE/'output/manifest.json',DATA/'processed/papers.jsonl',
        HERE/'METHOD_REVIEW_V5.md',Path(__file__).resolve()]
    return {str(p.resolve()):sha(p) for p in paths}


def normalize(text):
    # Same conservative normalization for both splits; do not modify exported text.
    return re.sub(r'\W+',' ',unicodedata.normalize('NFKC',text).casefold()).strip()


def partition_year(row):
    year=row.get('year')
    if row.get('year_status')!='available' or type(year) is not int:
        return None
    if year<=CONFIG['train_year_max']:return 'train'
    if CONFIG['test_year_min']<=year<=CONFIG['test_year_max']:return 'test'
    return None


def build():
    links=load(HERE/'output/paper_conference_links.jsonl')
    catalog_rows=load(HERE/'output/conference_catalog.jsonl')
    corpus_rows=load(DATA/'processed/papers.jsonl')
    assert len({r['paper_id'] for r in links})==len(links),'Duplicate mapping IDs'
    assert len({r['paper_id'] for r in corpus_rows})==len(corpus_rows),'Duplicate corpus IDs'
    corpus={r['paper_id']:r for r in corpus_rows}
    catalog={r['conference_id']:r for r in catalog_rows}
    assert len(catalog)==len(catalog_rows),'Duplicate catalog IDs'
    matched=[r for r in links if r['mapping_status']=='matched']
    assert all(r.get('mapping_review_v5',{}).get('usable_for_split') is True for r in matched)
    groups=defaultdict(list)
    for r in matched:
        assert r['conference_id'] in catalog
        assert r['paper_id'] in corpus
        assert corpus[r['paper_id']]['source']=='csfcube'
        groups[r['conference_id']].append(r)
    stats=[]
    for cid,rows in sorted(groups.items()):
        counts=Counter(partition_year(r) for r in rows)
        reasons=[]
        if len(rows)<CONFIG['min_matched_per_conference']:reasons.append('conference_below_min_total')
        if counts['train']<CONFIG['min_train_per_conference']:reasons.append('conference_below_min_train')
        if counts['test']<CONFIG['min_test_per_conference']:reasons.append('conference_below_min_test')
        stats.append(dict(conference_id=cid,acronym=catalog[cid]['acronym'],
            conference_name=catalog[cid]['canonical_name'],matched_count=len(rows),
            eligible_year_train_count=counts['train'],eligible_year_test_count=counts['test'],
            unavailable_or_out_of_window=counts[None],selected=not reasons,
            train_count=counts['train'] if not reasons else 0,
            test_count=counts['test'] if not reasons else 0,exclusion_reasons=';'.join(reasons)))
    selected={r['conference_id'] for r in stats if r['selected']}
    assert selected,'No conference satisfies the configured split'
    labels=[dict(label_index=i,conference_id=cid,conference_name=catalog[cid]['canonical_name'],
        acronym=catalog[cid]['acronym']) for i,cid in enumerate(sorted(selected))]
    label_index={r['conference_id']:r['label_index'] for r in labels}
    by_conf={r['conference_id']:r for r in stats}
    splits={'train':[],'test':[]}
    excluded=[]
    for r in links:
        cid=r['conference_id']
        if r['mapping_status']!='matched':
            reason='mapping_'+r['mapping_status']
        elif r.get('year_status')!='available' or type(r.get('year')) is not int:
            reason='year_'+r.get('year_status','missing')
        elif partition_year(r) is None:
            reason='year_outside_configured_window'
        elif cid not in selected:
            reason=by_conf[cid]['exclusion_reasons']
        else:
            split=partition_year(r)
            paper=corpus[r['paper_id']]
            assert all(isinstance(paper.get(k),str) and paper[k].strip() for k in ['title','abstract'])
            splits[split].append(dict(paper_id=r['paper_id'],source=r['source'],
                source_ids=r['source_ids'],title=paper['title'],abstract=paper['abstract'],
                year=r['year'],year_source=r['year_source'],year_status=r['year_status'],
                conference_id=cid,conference_name=catalog[cid]['canonical_name'],
                label_index=label_index[cid],mapping_status='matched',
                mapping_review_status=r['mapping_review_v5']['status'],split=split))
            continue
        excluded.append(dict(paper_id=r['paper_id'],mapping_status=r['mapping_status'],
            conference_id=cid,year=r.get('year'),year_status=r.get('year_status'),reason=reason))
    for rows in splits.values():rows.sort(key=lambda r:(r['conference_id'],r['year'],r['paper_id']))
    check_partition(links,splits,excluded,selected,corpus,by_conf)
    selected_catalog=[dict(catalog[cid],label_index=label_index[cid],
        train_paper_count=by_conf[cid]['train_count'],test_paper_count=by_conf[cid]['test_count']) for cid in sorted(selected)]
    reason_counts=dict(sorted(Counter(r['reason'] for r in excluded).items()))
    counts=dict(canonical_papers=len(links),reviewed_matched=len(matched),
        matched_conferences=len(groups),conferences_with_at_least_5_matched=sum(len(r)>=5 for r in groups.values()),
        selected_conferences=len(selected),train=len(splits['train']),test=len(splits['test']),
        selected_papers=sum(map(len,splits.values())),excluded_from_split=len(excluded),
        exclusion_reasons=reason_counts)
    readme=make_readme(counts)
    files={'train.jsonl':encode_jsonl(splits['train']),'test.jsonl':encode_jsonl(splits['test']),
        'conference_catalog.jsonl':encode_jsonl(selected_catalog),'label_map.json':encode_json(labels),
        'conference_split_statistics.csv':encode_csv(stats),'excluded_from_split.csv':encode_csv(excluded),
        'split_config.json':encode_json(CONFIG),'README.md':readme.encode('utf-8')}
    return files,counts


def check_partition(links,splits,excluded,selected,corpus,stats):
    train,test=splits['train'],splits['test']
    ids=lambda rows:{r['paper_id'] for r in rows}
    assert len(ids(train))==len(train) and len(ids(test))==len(test)
    assert ids(train).isdisjoint(ids(test)),'Paper leakage'
    assert ids(train).isdisjoint(ids(excluded)) and ids(test).isdisjoint(ids(excluded))
    assert ids(train)|ids(test)|ids(excluded)==ids(links),'Incomplete accounting'
    assert len(train)+len(test)+len(excluded)==len(links)
    train_sources={s for r in train for s in r['source_ids']}
    test_sources={s for r in test for s in r['source_ids']}
    assert train_sources.isdisjoint(test_sources),'Raw-source alias leakage'
    for field in ['title','abstract']:
        a={normalize(r[field]) for r in train}
        b={normalize(r[field]) for r in test}
        assert a.isdisjoint(b),'Content leakage: '+field
    assert all(r['year']<=2015 and r['split']=='train' for r in train)
    assert all(2016<=r['year']<=2019 and r['split']=='test' for r in test)
    assert {r['conference_id'] for r in train}=={r['conference_id'] for r in test}==selected
    for cid in selected:
        tr=[r for r in train if r['conference_id']==cid]
        te=[r for r in test if r['conference_id']==cid]
        assert len(tr)>=3 and len(te)>=1 and stats[cid]['matched_count']>=5
        assert max(r['year'] for r in tr)<min(r['year'] for r in te)
    for r in train+test:
        assert r['mapping_status']=='matched' and r['year_status']=='available'
        assert r['title']==corpus[r['paper_id']]['title'] and r['abstract']==corpus[r['paper_id']]['abstract']


def make_readme(counts):
    return f'''# Tập train/test hội nghị — chia theo năm raw của bản 5

Đầu vào là mapping đã review toàn bộ nhóm matched của bản 4, được chốt tại bản 5. Phương pháp và giới hạn: ../../METHOD_REVIEW_V5.md. Nhãn có chứng cứ nguồn và AI review; không phải human gold hoặc bảo đảm độ chính xác tuyệt đối.

## Số lượng

| Phần | Số lượng |
|---|---:|
| Bài matched của bản 5 | {counts['reviewed_matched']} |
| Hội nghị matched | {counts['matched_conferences']} |
| Hội nghị ứng viên có n ≥ 5 matched | {counts['conferences_with_at_least_5_matched']} |
| Hội nghị đáp ứng đủ điều kiện chia | {counts['selected_conferences']} |
| Train | {counts['train']} |
| Test | {counts['test']} |
| Tổng bài được chọn | {counts['selected_papers']} |
| Bài không vào split trên toàn corpus | {counts['excluded_from_split']} |

## Quy tắc

Chỉ dùng mapping_status=matched và mapping_review_v5.usable_for_split=true. Đếm n trên toàn bộ matched của mỗi conference_id, giữ ứng viên n ≥ 5. Sau đó chia bằng year raw trong mapping: train ≤ 2015; test 2016–2019. Giữ hội nghị có ít nhất 3 train và 1 test; nếu không đạt thì cả hội nghị không vào hai tập. Thiếu/mâu thuẫn năm hoặc ngoài cửa sổ để ngoài split. Không suy năm, không chia ngẫu nhiên, không ép tỷ lệ và không bớt bài ở hội nghị lớn.

Trong mỗi hội nghị, bài được sắp theo năm tăng dần, cùng năm dùng paper_id để có thứ tự tái lập. Chỉ train được dùng xây profile K-Medoids. Test là bài mới để đánh giá và không được đưa vào xây profile, chọn medoid hoặc điều chỉnh mô hình theo kết quả test.

## Sử dụng

- train.jsonl, test.jsonl: đầy đủ title, abstract, year raw và nhãn; không phải chỉ danh sách ID.
- Dùng title/abstract làm nội dung đầu vào, conference_id làm ground truth. Các trường conference_name, label_index và mapping_review_status là thông tin nhãn/provenance, không đưa chúng vào nội dung văn bản đầu vào.
- label_index từ 0 tới {counts['selected_conferences']-1}, theo conference_id tăng dần. label_map.json ánh xạ chỉ số về ID/tên hội nghị, dùng thống nhất cho train và test.
- conference_catalog.jsonl: đúng tập hội nghị ứng viên recommendation của split này. Không dùng toàn bộ catalog 163 hội nghị nếu đang đánh giá theo thiết kế tập đóng này.
- conference_split_statistics.csv: thống kê mọi hội nghị matched, kể cả hội nghị không được chọn, và lý do.
- excluded_from_split.csv: mọi bài không được chọn, gồm excluded/unresolved của mapping, năm không hợp lệ và hội nghị thiếu bài.
- split_config.json và manifest.json: quy tắc, hash đầu vào/đầu ra, số lượng và kiểm tra.

Đã kiểm tra: không trùng paper_id, raw source_id, title chuẩn hóa hoặc abstract chuẩn hóa giữa train/test; mọi hội nghị có đủ 3 train/1 test; max năm train < min năm test; văn bản giữ nguyên corpus chung; toàn bộ {counts['canonical_papers']} bài được hạch toán đúng một lần vào train/test/danh sách loại. Không tạo dev hoặc chạy mô hình.

## Tái lập

Từ thư mục 5_mapping_reviewed, chạy `python -B split_temporal.py`; kiểm tra chỉ đọc bằng `python -B split_temporal.py --check`. Chương trình kiểm tra mapping bản 5 trước khi dựng tập, không gọi mạng. Nếu mapping/corpus/phương pháp thay đổi thì check phát hiện hash thay đổi; cần chủ động dựng lại split theo phiên bản đầu vào mới.
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Validate frozen inputs/outputs and rebuild in memory without writes')
    args=parser.parse_args()
    subprocess.run([sys.executable,'-B',str(HERE/'review_mapping.py'),'--check'],check=True,cwd=HERE)
    before=source_hashes()
    if args.check:
        manifest=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
        assert manifest['input_hashes']==before,'Split input changed'
        assert manifest['config']==CONFIG,'Split configuration changed'
        for name,digest in manifest['output_hashes'].items():assert sha(DEST/name)==digest,name
    files,counts=build()
    assert before==source_hashes(),'Inputs changed while splitting'
    checks=dict(review_integrity=True,only_reviewed_matched=True,raw_years_preserved=True,
        no_paper_overlap=True,no_source_alias_overlap=True,no_normalized_title_overlap=True,
        no_normalized_abstract_overlap=True,text_unchanged=True,minimums_per_conference=True,
        temporal_order=True,all_records_accounted_for=True,deterministic_rebuild=True)
    if args.check:
        assert manifest['counts']==counts
        assert manifest['checks']==checks
        for name,data in files.items():assert (DEST/name).read_bytes()==data,'Rebuild differs: '+name
        print(json.dumps(dict(split_check='passed',**counts),ensure_ascii=True))
        return
    DEST.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():(DEST/name).write_bytes(data)
    manifest=dict(schema_version='1.0',generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dataset_version='5_mapping_reviewed',config=CONFIG,input_hashes=before,
        output_hashes={name:sha(DEST/name) for name in files},counts=counts,checks=checks,
        network_requests=0,human_gold=False,review_method='../../METHOD_REVIEW_V5.md')
    (DEST/'manifest.json').write_bytes(encode_json(manifest))
    print(json.dumps(dict(split_created=str(DEST),**counts),ensure_ascii=True))


if __name__=='__main__':main()
