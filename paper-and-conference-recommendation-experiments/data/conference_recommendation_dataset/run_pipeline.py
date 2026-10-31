"""Run versioned conference datasets and replay source audits from local snapshots."""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
STATS_HEADING = '## Phân bố số bài theo hội nghị — tập 4'


def run(stage, arguments):
    script = HERE / stage / 'preprocess_cube.py'
    subprocess.run([sys.executable, str(script), *arguments], cwd=script.parent, check=True)


def compare_baseline():
    def load(stage):
        path = HERE / stage / 'output/paper_conference_links.jsonl'
        return {r['paper_id']: r for r in (json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip())}
    first, second = load('1_raw_mapping'), load('2_mapping_enriched')
    if set(first) != set(second) or any((r['mapping_status'], r['conference_id']) !=
        (second[pid]['baseline_status'], second[pid]['baseline_conference_id']) for pid, r in first.items()):
        raise ValueError('Stage-2 baseline reconstruction differs from the frozen stage-1 labels')
    print(json.dumps(dict(frozen_baseline_comparison='passed', papers=len(first))))


def conference_statistics(check=False):
    out = HERE / '4_catalog_mapping/output'

    def read(name):
        with (out / name).open(encoding='utf-8') as stream:
            return [json.loads(line) for line in stream if line.strip()]

    links = read('paper_conference_links.jsonl')
    catalog = read('conference_catalog.jsonl')
    groups = read('conference_papers.jsonl')
    if len({r['paper_id'] for r in links}) != len(links):
        raise ValueError('Duplicate paper IDs in stage-4 statistics')
    members = {}
    for row in links:
        if row['mapping_status'] == 'matched':
            if not row['conference_id']:
                raise ValueError('Matched paper has no conference ID')
            members.setdefault(row['conference_id'], set()).add(row['paper_id'])
    lookup = {r['conference_id']: r for r in catalog}
    if len(lookup) != len(catalog) or set(lookup) != set(members):
        raise ValueError('Stage-4 catalog does not match paper labels')
    if len({g['conference_id'] for g in groups}) != len(groups) or {g['conference_id'] for g in groups} != set(members):
        raise ValueError('Stage-4 conference groups are incomplete or duplicated')
    for group in groups:
        ids = group['paper_ids']
        if len(ids) != len(set(ids)) or group['paper_count'] != len(ids) or set(ids) != members[group['conference_id']]:
            raise ValueError('Stage-4 paper count/group membership differs from labels')

    rows = [dict(conference_id=cid, acronym=lookup[cid]['acronym'],
                 conference_name=lookup[cid]['canonical_name'], paper_count=len(ids))
            for cid, ids in members.items()]
    rows.sort(key=lambda r: (-r['paper_count'], r['conference_name'], r['conference_id']))
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=['conference_id', 'acronym', 'conference_name', 'paper_count'], lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    expected = stream.getvalue().encode('utf-8-sig')
    path = out / 'conference_statistics.csv'
    if check:
        if path.read_bytes() != expected:
            raise ValueError('Stage-4 conference_statistics.csv differs from current labels')
    else:
        path.write_bytes(expected)

    total = sum(r['paper_count'] for r in rows)
    counts = [r['paper_count'] for r in rows]
    lines = ['', STATS_HEADING, '',
        'Chỉ đếm paper_id duy nhất có mapping_status=matched; mỗi ID hội nghị/joint được tính là một nhóm.', '',
        f'Danh sách đầy đủ tên hội nghị và số bài, sắp giảm dần: [conference_statistics.csv]({path.as_posix()}).', '',
        f'Tập 4 có **{len(rows)} hội nghị/joint**, **{total:,} bài conference**; mỗi hội nghị có **{min(counts) if counts else 0}–{max(counts) if counts else 0} bài**.', '',
        '| Số bài/hội nghị | Số hội nghị/joint | Tổng số bài |', '|---|---:|---:|']
    bins = [('1–4', 1, 4), ('5–9', 5, 9), ('10–19', 10, 19),
            ('20–49', 20, 49), ('50–99', 50, 99), ('Từ 100', 100, None)]
    for label, low, high in bins:
        selected = [n for n in counts if n >= low and (high is None or n <= high)]
        lines.append(f'| {label} | {len(selected)} | {sum(selected):,} |')
    lines += [f'| **Tổng** | **{len(rows)}** | **{total:,}** |', '',
        f'Có **{sum(n >= 10 for n in counts)} hội nghị từ 10 bài trở lên**, tương ứng **{sum(n for n in counts if n >= 10):,} bài**; đây là thống kê mô tả, chưa áp ngưỡng chọn hội nghị thực nghiệm.', '',
        'Chạy riêng phần thống kê và cập nhật báo cáo: `python run_pipeline.py --stats-only`.', '']
    print(json.dumps(dict(conference_statistics='passed' if check else 'updated', conferences=len(rows), papers=total)))
    return lines


def version5_statistics():
    """Summarize frozen stage-5 outputs without changing review/split artifacts."""
    stage = HERE / '5_mapping_reviewed'
    with (stage / 'output/conference_statistics.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    counts = [int(row['paper_count']) for row in rows]
    links = [json.loads(line) for line in (stage / 'output/paper_conference_links.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    actual = Counter(row['conference_id'] for row in links if row['mapping_status'] == 'matched')
    if len(rows) != len(actual) or {row['conference_id']: int(row['paper_count']) for row in rows} != dict(actual):
        raise ValueError('Stage-5 statistics differ from current labels')
    candidates = [n for n in counts if n >= 5]
    lines = ['## Phân bố số bài theo hội nghị — tập 5', '',
        f'Chỉ đếm bài `matched`, mỗi `paper_id` một lần và mỗi ID hội nghị/joint một nhóm: **{len(rows)} hội nghị/joint, {sum(counts):,} bài**, từ **{min(counts)}–{max(counts)} bài/nhóm**. Chi tiết từng hội nghị: [conference_statistics.csv](5_mapping_reviewed/output/conference_statistics.csv).', '',
        '| Số bài/hội nghị | Số hội nghị/joint | Tổng số bài |', '|---|---:|---:|']
    for label, low, high in [('1–4', 1, 4), ('5–9', 5, 9), ('10–19', 10, 19), ('20–49', 20, 49), ('50–99', 50, 99), ('Từ 100', 100, None)]:
        selected = [n for n in counts if n >= low and (high is None or n <= high)]
        lines.append(f'| {label} | {len(selected)} | {sum(selected):,} |')
    lines += [f'| **Tổng** | **{len(rows)}** | **{sum(counts):,}** |', '',
        f'Ngưỡng **n ≥ 5** cho **{len(candidates)} hội nghị, {sum(candidates):,} bài** ({sum(candidates)/sum(counts):.1%} số bài matched); đây là tập ứng viên trước khi lọc năm và kiểm tra tối thiểu train/test.', '']
    split = stage / 'splits/temporal_2015_2016_2019'
    if (split / 'manifest.json').exists():
        manifest = json.loads((split / 'manifest.json').read_text(encoding='utf-8'))
        config, totals = manifest['config'], manifest['counts']
        lines += ['### Chia train/test của tập 5', '',
            f'Chỉ dùng `matched` đã review, lấy năm từ `raw.metadata.year`: **train ≤ {config["train_year_max"]}**, **test {config["test_year_min"]}–{config["test_year_max"]}**. Hội nghị phải có tổng ≥ {config["min_matched_per_conference"]} bài matched và ít nhất **{config["min_train_per_conference"]} train + {config["min_test_per_conference"]} test**; không đủ thì loại cả hội nghị. Bỏ bài thiếu/mâu thuẫn năm hoặc ngoài khoảng năm; không chia ngẫu nhiên, không bổ sung năm từ web.', '',
            '| Phần dữ liệu | Số hội nghị | Số bài |', '|---|---:|---:|',
            f'| Train | {totals["selected_conferences"]} | {totals["train"]:,} |',
            f'| Test | {totals["selected_conferences"]} | {totals["test"]:,} |',
            f'| **Tổng, cùng tập hội nghị** | **{totals["selected_conferences"]}** | **{totals["selected_papers"]:,}** |', '',
            f'Còn {totals["reviewed_matched"]-totals["selected_papers"]:,} bài matched không vào split. Chi tiết số train/test từng hội nghị: [conference_split_statistics.csv](5_mapping_reviewed/splits/temporal_2015_2016_2019/conference_split_statistics.csv). Dữ liệu nằm trong `5_mapping_reviewed/splits/temporal_2015_2016_2019/`; chỉ dùng train xây profile K-Medoids, test để đánh giá. Chưa tạo dev.', '']
    return lines


def dataset_report(check=False):
    def read(path):
        with path.open(encoding='utf-8') as stream:
            return [json.loads(line) for line in stream if line.strip()]

    stages = ['1_raw_mapping', '2_mapping_enriched', '3_mapping_reviewed']
    if (HERE/'4_catalog_mapping/review/catalog_manifest.json').exists():
        stages.append('4_catalog_mapping')
    if (HERE/'5_mapping_reviewed/output/manifest.json').exists():
        stages.append('5_mapping_reviewed')
    raw = read(HERE.parent / 'raw/csfcube/abstracts-csfcube-preds.jsonl')
    parse_year = runpy.run_path(str(HERE / stages[0] / 'preprocess_cube.py'))['parse_raw_year']
    raw_known = sum(parse_year((r.get('metadata') or {}).get('year')) is not None for r in raw)
    raw_missing = sum((r.get('metadata') or {}).get('year') is None or str(r['metadata']['year']).strip() == '' for r in raw)
    links = {stage: read(HERE / stage / 'output/paper_conference_links.jsonl') for stage in stages}
    lines = ['# Tổng hợp dataset cho Conference Recommendation', '',
        'Phạm vi: chỉ CSFCube, dùng title + abstract để gợi ý hội nghị. Bản 5 đã review mapping và chia train/test theo năm raw; chưa tạo dev, bổ sung rank hoặc xây profile hội nghị.' if '5_mapping_reviewed' in stages else 'Phạm vi: chỉ CSFCube, dùng title + abstract để gợi ý hội nghị. Chưa bổ sung rank, chia train/dev/test hoặc xây profile hội nghị.', '',
        '## Cách tạo các phiên bản', '',
        'Dùng phần CSFCube đã tiền xử lý chung: làm sạch văn bản, gộp trùng và giữ ID. Nối từng bài về các bản ghi raw bằng source ID; giữ nguyên văn bản và thông tin nguồn.', '',
        '1. **1_raw_mapping:** đọc venue có sẵn, chuẩn hóa/mapping tên hội nghị; tách journal/workshop/ấn phẩm phụ và các bài chưa rõ.',
        '2. **2_mapping_enriched:** mở rộng alias, nối metadata theo DOI hoặc CorpusId → DOI; đối chiếu title và tác giả khi có, rồi xét lại venue. Trường hợp mâu thuẫn hoặc không đủ căn cứ được giữ chưa rõ.',
        '3. **3_mapping_reviewed:** kế thừa bản 1, đối chiếu 223 alias và mẫu 169 bài với nguồn; sửa hai quy tắc tên và ba trường hợp cụ thể. Chưa hợp nhất enrichment của bản 2.',
        *(['4. **4_catalog_mapping:** kế thừa bản 3, mở rộng tên venue raw bằng danh mục ICORE, ACL Anthology và tên journal Crossref khớp đầy đủ; không tìm thêm bài hoặc lần ngược arXiv.'] if '4_catalog_mapping' in stages else []),
        *(['5. **5_mapping_reviewed:** review toàn bộ 1.144 bài matched và 446 alias matched của bản 4: đọc venue/journal raw, đối chiếu danh tính bài và venue/track với nguồn; AI xét các trường hợp cần phân xử. Sửa 26 ID joint, chuyển 36 bài ngoài đích và 18 bài chưa đủ căn cứ; giữ 1.090 matched. Không mở rộng tập mapping, không đổi năm/văn bản raw. Chi tiết: [phương pháp review bản 5](5_mapping_reviewed/METHOD_REVIEW_V5.md).'] if '5_mapping_reviewed' in stages else []), '',
        '## Thống kê', '',
        '| Tập dữ liệu | Tổng bản ghi/bài | Conference | Ngoài đích | Chưa rõ | Hội nghị/joint | Có năm raw chốt được |',
        '|---|---:|---:|---:|---:|---:|---:|',
        f'| Raw CSFCube | {len(raw):,} | — | — | — | — | {raw_known:,} |']
    for stage, rows in links.items():
        counts = Counter(r['mapping_status'] for r in rows)
        conferences = len({r['conference_id'] for r in rows if r['mapping_status'] == 'matched'})
        known = sum(r['year'] is not None for r in rows)
        lines.append(f"| {stage} | {len(rows):,} | {counts['matched']:,} | {counts['excluded']:,} | {counts['unresolved']:,} | {conferences} | {known:,} |")
    years = Counter(r['year_status'] for r in links[stages[0]])
    coverage = '; '.join(f"bản {i}: {sum(r['mapping_status']=='matched' and r['year'] is not None for r in links[s])}/{sum(r['mapping_status']=='matched' for r in links[s])}" for i, s in enumerate(stages, 1))
    lines += ['',
        'Raw đếm bản ghi nguồn; các bản xử lý đếm bài sau gộp trùng (25 bản ghi dư). Dấu — nghĩa là chưa áp quy tắc phân loại trên raw, không phải số lượng bằng 0.', '',
        f"Năm được nối trực tiếp từ `metadata.year` của mọi alias raw thành `year` (số nguyên 1000–2100). Raw có {raw_missing} bản ghi thiếu năm và {len(raw)-raw_known-raw_missing} giá trị không hợp lệ. Sau gộp, mỗi bản có {years['available']:,} bài chốt được năm, {years['missing']} bài thiếu và {years['conflicting']} bài có các năm nguồn mâu thuẫn; hai nhóm cuối để `year=null`. Các năm khác nhau được giữ trong `year_candidates` và thông tin nguồn trong `evidence`.", '',
        f'Bài conference chốt được năm: {coverage}.', '',
        '`year` là năm từ dataset gốc, không mặc định là năm tổ chức hội nghị. `publication_year` là trường riêng cho năm được metadata xuất bản ủng hộ; bước nối raw không ghi đè trường này. Nhãn hội nghị không thay đổi khi nối năm.', '',
        '## Lưu ý khi chọn cách dựng dataset', '',
        '- **Cách 2 — enrichment:** có thể dùng khi nối đúng bài/phiên bản, xác minh venue/track và đánh giá riêng nhãn bổ sung; chưa nên dùng nguyên bản 2 làm nhãn chuẩn vì rule cũ chưa hợp nhất các sửa mới và chưa có kiểm định độc lập. Luồng hiện tại là DOI gốc hoặc CorpusId → DOI → Crossref, chưa tra trực tiếp arXiv ID.',
        '- DOI của preprint arXiv không chứng minh đã xuất bản ở conference; phải phân biệt với DOI bản xuất bản và giữ chứng cứ nguồn. Xem [hướng dẫn DOI arXiv](https://info.arxiv.org/help/doi.html).',
        '- **Bản 5 — tập thực nghiệm:** đã rà soát toàn bộ matched của bản 4, giữ chứng cứ và tách các ca chưa chắc chắn; đủ dùng tiếp cho thực nghiệm và mô tả phương pháp trong bài báo. Đây là nhãn đối chiếu nguồn kết hợp AI review, chưa phải gold do người chấm độc lập xác nhận; chưa đo precision/recall nhãn. Profile chỉ dùng train.' if '5_mapping_reviewed' in stages else '- **Cách 3 — kiểm tra mapping:** đủ làm baseline thử nghiệm ban đầu, chưa đủ tuyên bố toàn bộ nhãn đã đúng; phần tên mở rộng ở bản 4 cũng cần đánh giá. Để chốt tập thực nghiệm cần chọn hội nghị đủ dữ liệu, kiểm tra mẫu độc lập, xử lý trùng/phiên bản và chốt split; profile chỉ dùng train.',
        '- Không cần ép giải quyết hết unresolved: có thể chốt một tập con đủ căn cứ và báo rõ phần loại/thiếu. Chi tiết điều kiện dùng enrichment và kiểm định ở [restriction.md]('+ (HERE/'restriction.md').as_posix()+').', '',
        '## Tái lập', '',
        'Giữ bộ raw, corpus chung, bảng mapping và hồ sơ metadata/đối chiếu nguồn đi kèm. Chạy tại thư mục chứa báo cáo; mặc định không truy cập mạng và không dùng kết quả của các thư mục thử nghiệm cũ:', '',
        '```powershell', 'python 1_raw_mapping/preprocess_cube.py', 'python run_pipeline.py --audit',
        'python run_pipeline.py --check --check-isolated',
        *(['python 5_mapping_reviewed/review_mapping.py --check', 'python 5_mapping_reviewed/split_temporal.py --check'] if '5_mapping_reviewed' in stages else []),
        '```', '',
        'Báo cáo tạo lại từ output thực tế; các lệnh kiểm tra bản 5 xác nhận hồ sơ review, hash và split tái lập được. Kết quả kiểm tra kỹ thuật không thay thế đánh giá độ chính xác nhãn độc lập.' if '5_mapping_reviewed' in stages else 'Báo cáo này được lệnh chung tạo lại từ output thực tế. Có kiểm tra nguồn/ID, năm, tổng đếm, nhãn, hash và khả năng tái lập. Bản 3 dùng làm baseline đã sửa theo nguồn; chưa phải nhãn được người chấm độc lập xác nhận toàn bộ, chưa đo precision/recall nhãn.', '']
    if '4_catalog_mapping' in stages:
        if lines and lines[-1] == '':
            lines.pop()
        lines += conference_statistics(check=check)
    if '5_mapping_reviewed' in stages:
        lines += version5_statistics()
    expected = '\n'.join(lines)
    path = HERE / 'Report_dataset.md'
    if check:
        if path.read_text(encoding='utf-8') != expected:
            raise ValueError('Report_dataset.md differs from current datasets')
    else:
        path.write_text(expected, encoding='utf-8', newline='\n')
    print(json.dumps(dict(dataset_report='passed' if check else 'updated')))


def check_isolated(stage_name='2_mapping_enriched'):
    stage = HERE / stage_name
    fresh = Path(tempfile.mkdtemp(prefix='.rebuild-', dir=stage)).resolve()
    baseline = HERE / '1_raw_mapping'
    frozen = {str(p.relative_to(baseline)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in baseline.rglob('*') if p.is_file()}
    forbidden = [HERE.parents[2] / 'Extra_DOING', baseline, stage / 'output']
    if stage_name=='4_catalog_mapping':
        forbidden += [HERE/'2_mapping_enriched',HERE/'3_mapping_reviewed']
    active = [True]

    def audit(event, arguments):
        if not active[0]:
            return
        if event in {'socket.connect', 'socket.getaddrinfo'}:
            raise AssertionError('Isolated rebuild attempted network access')
        if event == 'open' and isinstance(arguments[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(arguments[0])).resolve()
            if any(path.is_relative_to(folder) for folder in forbidden):
                raise AssertionError('Isolated rebuild accessed legacy code or prior outputs: ' + str(path))

    sys.addaudithook(audit)
    previous_argv = sys.argv[:]
    try:
        sys.argv = [str(stage / 'preprocess_cube.py'), '--output-dir', str(fresh)]
        runpy.run_path(str(stage / 'preprocess_cube.py'), run_name='__main__')
        active[0] = False
        expected = json.loads((stage / 'output/manifest.json').read_text(encoding='utf-8'))
        actual = json.loads((fresh / 'manifest.json').read_text(encoding='utf-8'))
        if expected['input_hashes'] != actual['input_hashes'] or expected['output_hashes'] != actual['output_hashes']:
            raise ValueError('Fresh rebuild differs from existing inputs or outputs')
        after = {str(p.relative_to(baseline)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in baseline.rglob('*') if p.is_file()}
        if frozen != after:
            raise ValueError('Frozen baseline files changed during isolated rebuild')
        print(json.dumps(dict(stage=stage_name,isolated_rebuild='passed', network_and_old_outputs_blocked=True,
                              output_hashes_identical=True, frozen_baseline_unchanged=True)))
    finally:
        active[0] = False
        sys.argv = previous_argv
        # Only remove the exact temporary directory created by this check, inside stage 2.
        if not fresh.is_relative_to(stage.resolve()) or not fresh.name.startswith('.rebuild-'):
            raise ValueError('Refusing cleanup outside the isolated rebuild directory')
        shutil.rmtree(fresh)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify all generated versions without changing files')
    parser.add_argument('--check-isolated', action='store_true', help='Also rebuild in a temporary directory while blocking network and old outputs')
    parser.add_argument('--stats-only', action='store_true', help='Update the dataset report and available conference/split statistics without rebuilding datasets')
    parser.add_argument('--audit-raw', action='store_true', help='Replay the source audit offline and rebuild the reviewed version')
    parser.add_argument('--audit', action='store_true', help='Replay both raw and enrichment sample audits offline, then rebuild the reviewed version')
    parser.add_argument('--import-cache', type=Path, help='One-time bootstrap from old original API caches')
    parser.add_argument('--prepare-mapping', action='store_true')
    parser.add_argument('--fetch-missing', action='store_true', help='Explicit opt-in network refresh of exact DOI metadata')
    parser.add_argument('--limit', type=int, default=50)
    args = parser.parse_args()
    checking = args.check or args.check_isolated
    if args.stats_only:
        if args.import_cache or args.prepare_mapping or args.fetch_missing or args.audit_raw or args.audit or args.check_isolated:
            parser.error('--stats-only cannot be combined with pipeline rebuild or isolated-check options')
        if not (HERE/'4_catalog_mapping/output/manifest.json').exists():
            parser.error('Stage-4 outputs are required for --stats-only')
        dataset_report(check=args.check)
        return
    if checking and (args.import_cache or args.prepare_mapping or args.fetch_missing or args.audit_raw or args.audit):
        parser.error('--check cannot be combined with input-changing options')
    base_manifest = HERE / '1_raw_mapping/output/manifest.json'
    if checking or base_manifest.exists():
        run('1_raw_mapping', ['--check'])
    else:
        run('1_raw_mapping', [])
        run('1_raw_mapping', ['--check'])
    extra = []
    if args.import_cache:
        extra += ['--import-cache', str(args.import_cache.resolve())]
    if args.prepare_mapping:
        extra.append('--prepare-mapping')
    if args.fetch_missing:
        extra += ['--fetch-missing', '--limit', str(args.limit)]
    if not checking:
        run('2_mapping_enriched', extra)
    run('2_mapping_enriched', ['--check'])
    compare_baseline()
    audit_script=HERE/'3_mapping_reviewed/audit_mapping.py'
    audit_manifest=HERE/'3_mapping_reviewed/review/manifest.json'
    if args.audit:
        subprocess.run([sys.executable,str(audit_script),'--enriched'],cwd=audit_script.parent,check=True)
    if args.audit_raw or args.audit:
        subprocess.run([sys.executable,str(audit_script)],cwd=audit_script.parent,check=True)
    if audit_manifest.exists():
        subprocess.run([sys.executable,str(audit_script),'--check'],cwd=audit_script.parent,check=True)
        if not checking:run('3_mapping_reviewed',[])
        run('3_mapping_reviewed',['--check'])
    if (HERE/'2_mapping_enriched/review/manifest.json').exists():
        subprocess.run([sys.executable,str(audit_script),'--enriched','--check'],cwd=audit_script.parent,check=True)
    directory_script=HERE/'4_catalog_mapping/audit_mapping.py'
    if (directory_script.parent/'review/catalog_manifest.json').exists():
        subprocess.run([sys.executable,str(directory_script),'--check'],cwd=directory_script.parent,check=True)
        if not checking:run('4_catalog_mapping',['--prepare-mapping'])
        run('4_catalog_mapping',['--check'])
    dataset_report(check=checking)
    if args.check_isolated:
        check_isolated()
        if (HERE/'4_catalog_mapping/review/catalog_manifest.json').exists():
            check_isolated('4_catalog_mapping')


if __name__ == '__main__':
    main()
