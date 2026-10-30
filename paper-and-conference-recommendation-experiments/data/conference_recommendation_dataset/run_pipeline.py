"""Run versioned conference datasets and replay source audits from local snapshots."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


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


def dataset_report(check=False):
    def read(path):
        with path.open(encoding='utf-8') as stream:
            return [json.loads(line) for line in stream if line.strip()]

    stages = ['1_raw_mapping', '2_mapping_enriched', '3_mapping_reviewed']
    if (HERE/'4_catalog_mapping/review/catalog_manifest.json').exists():
        stages.append('4_catalog_mapping')
    raw = read(HERE.parent / 'raw/csfcube/abstracts-csfcube-preds.jsonl')
    parse_year = runpy.run_path(str(HERE / stages[0] / 'preprocess_cube.py'))['parse_raw_year']
    raw_known = sum(parse_year((r.get('metadata') or {}).get('year')) is not None for r in raw)
    raw_missing = sum((r.get('metadata') or {}).get('year') is None or str(r['metadata']['year']).strip() == '' for r in raw)
    links = {stage: read(HERE / stage / 'output/paper_conference_links.jsonl') for stage in stages}
    lines = ['# Tổng hợp dataset cho Conference Recommendation', '',
        'Phạm vi: chỉ CSFCube, dùng title + abstract để gợi ý hội nghị. Chưa bổ sung rank, chia train/dev/test hoặc xây profile hội nghị.', '',
        '## Cách tạo các phiên bản', '',
        'Dùng phần CSFCube đã tiền xử lý chung: làm sạch văn bản, gộp trùng và giữ ID. Nối từng bài về các bản ghi raw bằng source ID; giữ nguyên văn bản và thông tin nguồn.', '',
        '1. **1_raw_mapping:** đọc venue có sẵn, chuẩn hóa/mapping tên hội nghị; tách journal/workshop/ấn phẩm phụ và các bài chưa rõ.',
        '2. **2_mapping_enriched:** mở rộng alias, nối metadata theo DOI hoặc CorpusId → DOI; đối chiếu title và tác giả khi có, rồi xét lại venue. Trường hợp mâu thuẫn hoặc không đủ căn cứ được giữ chưa rõ.',
        '3. **3_mapping_reviewed:** kế thừa bản 1, đối chiếu 223 alias và mẫu 169 bài với nguồn; sửa hai quy tắc tên và ba trường hợp cụ thể. Chưa hợp nhất enrichment của bản 2.',
        *(['4. **4_catalog_mapping:** kế thừa bản 3, mở rộng tên venue raw bằng danh mục ICORE, ACL Anthology và tên journal Crossref khớp đầy đủ; không tìm thêm bài hoặc lần ngược arXiv.'] if len(stages)>3 else []), '',
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
        '## Tái lập', '',
        'Giữ bộ raw, corpus chung, bảng mapping và hồ sơ metadata/đối chiếu nguồn đi kèm. Chạy tại thư mục chứa báo cáo; mặc định không truy cập mạng và không dùng kết quả của các thư mục thử nghiệm cũ:', '',
        '```powershell', 'python 1_raw_mapping/preprocess_cube.py', 'python run_pipeline.py --audit',
        'python run_pipeline.py --check --check-isolated', '```', '',
        'Báo cáo này được lệnh chung tạo lại từ output thực tế. Có kiểm tra nguồn/ID, năm, tổng đếm, nhãn, hash và khả năng tái lập. Bản 3 dùng làm baseline đã sửa theo nguồn; chưa phải nhãn được người chấm độc lập xác nhận toàn bộ, chưa đo precision/recall nhãn.', '']
    expected = '\n'.join(lines)
    path = HERE / 'Report_dataset.md'
    if check:
        if path.read_text(encoding='utf-8') != expected:
            raise ValueError('Report_dataset.md differs from current datasets')
    else:
        path.write_text(expected, encoding='utf-8')
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
    parser.add_argument('--audit-raw', action='store_true', help='Replay the source audit offline and rebuild the reviewed version')
    parser.add_argument('--audit', action='store_true', help='Replay both raw and enrichment sample audits offline, then rebuild the reviewed version')
    parser.add_argument('--import-cache', type=Path, help='One-time bootstrap from old original API caches')
    parser.add_argument('--prepare-mapping', action='store_true')
    parser.add_argument('--fetch-missing', action='store_true', help='Explicit opt-in network refresh of exact DOI metadata')
    parser.add_argument('--limit', type=int, default=50)
    args = parser.parse_args()
    checking = args.check or args.check_isolated
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
