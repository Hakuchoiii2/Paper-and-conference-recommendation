"""Package the approved paired experiment without changing the production pilot bundle."""
import hashlib
import inspect
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
import matrix

KERNEL = 'htnkhi/exp-a-qwen-facet-matrix'
DATASET = 'htnkhi/exp-a-qwen-facet-matrix-inputs'


def recover_4b(papers, baseline, config, files):
    source = HERE.parent/'review/matrix_v1_failure/exp_a_matrix'
    if not source.is_dir():
        return []
    policy = dict(prompts=[matrix.METHOD,matrix.CONTRIBUTION,matrix.COMMON],
        functions=[inspect.getsource(matrix.parse_items).strip(),inspect.getsource(matrix.split_paper).strip()])
    matrix.base.require(matrix.digest(policy) == 'a24ceb50769b79d5dff899bcd82bd48f370ba00f1aeb7a8ec3520242cb904e36',
                        'Recovered source-first policy changed; rerun 4B instead of reusing v1')
    old = json.loads((source/'matrix_settings.json').read_text(encoding='utf-8'))
    signature = '87e5e295c93bdd5008d6b10ce0d0ad6fb6d0626fae3e9c89131cef3934409cf9'
    unsigned = dict(old)
    unsigned.pop('generation_signature')
    matrix.base.require(matrix.digest(unsigned) == signature, 'Recovered settings signature is invalid')
    matrix.base.require(old['generation_signature'] == signature and old['generation'] == config,
                        'Recovered matrix v1 configuration differs')
    for name in ('model_inputs/papers.jsonl','model_inputs/baseline_records.jsonl',
                 config['prompt'],config['guideline'],'data/exp_a/extraction_v3.py','data/exp_a/build_exp_a.py'):
        matrix.base.require(old['files'][name] == hashlib.sha256(files[name]).hexdigest(),
                            f'Recovered 4B input differs: {name}')
    originals = {r['paper_id']:r['facets'] for r in baseline}
    recovered = []
    for paper in papers:
        pid = paper['paper_id']
        record = matrix.load_record(source/f'results/4b_source_first/records/{pid}.json',signature)
        matrix.base.require(record['paper_id'] == pid and record['runtime']['model'] == config['model']
            and record['runtime']['model_revision'] == config['revision'], 'Recovered 4B model/ID differs')
        attempts = iter([a for f in matrix.TARGETS for a in record['audit'][f]['attempts']])
        def replay(messages,seed):
            attempt = next(attempts)
            matrix.base.require(seed == attempt['seed'], 'Recovered seed differs')
            return attempt['raw_output'], {k:attempt[k] for k in ('usage','generation_seconds','reached_token_limit')}
        checked = matrix.split_paper(paper,originals[pid],replay,seed=config['seed'])
        matrix.base.require(all(checked[k] == record[k] for k in ('facets','audit','usage','generation_seconds','fallback_used')),
                            f'Recovered 4B raw/applied replay differs: {pid}')
        record['reused_from'] = dict(kernel='htnkhi/exp-a-qwen-facet-matrix',version=1,signature=signature)
        recovered.append(record)
    return recovered


def build(destination=None):
    destination = Path(destination or HERE/'build_matrix')
    config = json.loads((ROOT/'data/exp_a/config_v3_pilot50.json').read_text(encoding='utf-8'))
    ids = set(config['paper_ids'])
    papers = [p for p in matrix.base.read_jsonl(ROOT/config['corpus']) if p['paper_id'] in ids]
    references = matrix.base.read_jsonl(ROOT/'data/exp_a/pilot50/ai_reference_v1/review_annotations.jsonl')
    source = ROOT/'data/exp_a/generated_v3_7_pilot50'
    manifest = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['files'].items():
        matrix.base.require(matrix.base.sha256(source/name) == expected, f'Cached baseline checksum differs: {name}')
    facets = matrix.base.read_jsonl(source/'facets_silver.jsonl')
    notes = {r['paper_id']:r for r in matrix.base.read_jsonl(source/'annotation_metadata.jsonl')}
    matrix.base.require(len(papers) == len(facets) == len(references) == len(ids) == 50
        and ids == {r['paper_id'] for r in facets} == set(notes) == {r['paper_id'] for r in references}, 'Source/reference/baseline IDs differ')
    matrix.base.require(all(r['reviewer_type'] == 'ai' and r['review_status'] == 'reviewed' for r in references), 'Unexpected reference provenance')
    frozen_sources = matrix.base.read_jsonl(ROOT/'data/exp_a/pilot50/ai_reference_v1/source_papers.jsonl')
    frozen = {p['paper_id']:p for p in frozen_sources}
    matrix.base.require(all(all(p[k] == frozen[p['paper_id']][k] for k in ('title','abstract')) for p in papers), 'Source differs from frozen reference inputs')
    records = [dict(paper_id=r['paper_id'], facets=r, audit=notes[r['paper_id']],
        usage=notes[r['paper_id']]['usage'], generation_seconds=notes[r['paper_id']]['generation_seconds'],
        fallback_used=notes[r['paper_id']]['fallback_used']) for r in facets]
    score = json.loads((ROOT/'data/exp_a/evaluation/pilot50_v3_7_ai_v1/summary.json').read_text(encoding='utf-8'))
    evaluation_manifest = json.loads((ROOT/'data/exp_a/evaluation/pilot50_v3_7_ai_v1/manifest.json').read_text(encoding='utf-8'))
    matrix.base.require(evaluation_manifest['source_manifest_sha256'] == matrix.base.sha256(source/'manifest.json')
        and evaluation_manifest['gold_sha256'] == matrix.base.sha256(ROOT/'data/exp_a/pilot50/ai_reference_v1/review_annotations.jsonl')
        and evaluation_manifest['evaluator_sha256'] == matrix.base.sha256(Path(matrix.evaluator.__file__)),
        'Baseline evaluation provenance differs; recheck before building')
    expected_counts = {k:score['micro'][k] for k in ('tp','fp','fn')}
    def json_bytes(value):
        return (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    def jsonl_bytes(rows):
        return ''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows).encode('utf-8')
    files = {name:(ROOT/name).read_bytes() for name in (
        'data/exp_a/.kaggle/matrix/matrix.py','data/exp_a/build_exp_a.py','data/exp_a/extraction_v3.py',
        'scripts/exp_a/evaluate_exp_a.py','scripts/experiment_io.py','scripts/build_corpus.py',
        'scripts/download_sources.py','scripts/validate_all.py',config['prompt'],config['guideline'])}
    files['model_inputs/papers.jsonl'] = jsonl_bytes(sorted(papers,key=lambda p:p['paper_id']))
    files['model_inputs/baseline_records.jsonl'] = jsonl_bytes(records)
    recovered = recover_4b(papers,records,config,files)
    if recovered:
        files['model_inputs/completed_4b_source_first.jsonl'] = jsonl_bytes(recovered)
    files['evaluation_only/review_annotations.jsonl'] = jsonl_bytes(references)
    files['evaluation_only/reference_manifest.json'] = (ROOT/'data/exp_a/pilot50/ai_reference_v1/manifest.json').read_bytes()
    download_manifest = matrix.evaluator.MODEL_DIRECTORY+'/download_manifest.json'
    files[download_manifest] = (ROOT/download_manifest).read_bytes()
    embedding_manifest = json.loads(files[download_manifest])
    for name,info in embedding_manifest['files'].items():
        if name == 'model.safetensors':
            continue
        relative = matrix.evaluator.MODEL_DIRECTORY+'/'+name
        data = (ROOT/relative).read_bytes()
        matrix.base.require(hashlib.sha256(data).hexdigest() == info['sha256'], f'Embedding file changed: {name}')
        files[relative] = data
    settings = dict(experiment_version='facet_matrix_v2', paper_ids=sorted(ids),
        resumed_4b_source_first_count=len(recovered),
        target_facets=['method','contribution'], reference_kind='ai', sample_kind='reused_development_pilot50',
        generation=config, models={
            '4b':dict(model=config['model'],revision=config['revision']),
            '8b':dict(model='Qwen/Qwen3-8B',revision='b968826d9c46dd6066d109eabc6255188de91218')},
        decoding=dict(do_sample=False,enable_thinking=False,quantization='nf4_double',max_new_tokens=2048,
                      attention_implementation={'4b':'sdpa','8b':'matrix_efficient_no_gqa'}),
        baseline_expected_counts=expected_counts, baseline_manifest_sha256=matrix.base.sha256(source/'manifest.json'),
        limitations=['AI reference; no human adjudication','Repeated development cohort, no fresh held-out claims',
            'Models differ in post-training as well as size','Split arms replace only method/contribution and have extra generation cost'],
        files={name:hashlib.sha256(data).hexdigest() for name,data in files.items()})
    settings['generation_signature'] = matrix.digest(settings)
    files['matrix_settings.json'] = json_bytes(settings)
    dataset = destination/'input-dataset'
    dataset.mkdir(parents=True, exist_ok=True)
    archive_path = dataset/'matrix_bundle.zip.bin'
    with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(files.items()):
            info = zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info,data)
    matrix.base.write_json(dataset/'dataset-metadata.json', dict(id=DATASET,title='Exp A Qwen Facet Matrix Inputs',licenses=[dict(name='other')]))
    sha = matrix.base.sha256(archive_path)
    kernel = destination/'kernel'
    kernel.mkdir(parents=True,exist_ok=True)
    code = (HERE/'kernel_matrix.template.py').read_text(encoding='utf-8').replace('__BUNDLE_SHA256__',sha)
    compile(code,'run_matrix.py','exec')
    (kernel/'run_matrix.py').write_text(code,encoding='utf-8')
    matrix.base.write_json(kernel/'kernel-metadata.json', dict(id=KERNEL,title='Exp A Qwen Facet Matrix',
        code_file='run_matrix.py',language='python',kernel_type='script',is_private=True,
        enable_gpu=True,enable_internet=True,machine_shape='NvidiaTeslaT4',
        dataset_sources=[DATASET],competition_sources=[],kernel_sources=[],model_sources=[]))
    result = dict(kernel=KERNEL,dataset=DATASET,bundle_sha256=sha,baseline_expected_counts=expected_counts,
        resumed_4b_source_first_count=len(recovered),
        generation_signature=settings['generation_signature'],sample_size=50,bundle_files=settings['files'],
        arms=list(matrix.ARMS),baseline_origin='completed private pilot kernel version 9')
    matrix.base.write_json(destination/'build_manifest.json',result)
    return result


if __name__ == '__main__':
    result = build()
    print(json.dumps({k:v for k,v in result.items() if k != 'bundle_files'},ensure_ascii=False,indent=2))
