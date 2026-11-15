"""Freeze the current V-recall bytes and accepted400 gold into a private Kaggle input."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import zipfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PINNED=HERE.parent/'v_recall/release_20261026_v1'
RELEASE=HERE/'release_20261026_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def rows(p):return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
    if (RELEASE/'launch_report.json').exists() or (RELEASE/'dataset_upload_report.json').exists():raise ValueError('Uploaded release is immutable; use a new version')
    old=read(PINNED/'settings.json');pre=PINNED/'preflight_project';gold_dir=ROOT/'data/exp_a/ground_truth/gold_review'
    gold=rows(gold_dir/'human_gold.jsonl');sources=rows(gold_dir/'review_papers.jsonl');source_by_id={r['paper_id']:r for r in sources}
    ids=sorted(r['paper_id'] for r in gold)
    assert len(gold)==len(set(ids))==len(source_by_id)==400 and set(ids)==set(source_by_id)
    assert all(r.get('human_review_status')=='accepted' and r.get('reviewer_type')=='human' and r.get('review_status')=='reviewed' for r in gold),'Unaccepted reference'
    assert not set(ids)&set(old['paper_ids']),'Do not mix cached pilot cohort into gold400'
    corpus={r['paper_id']:r for r in rows(ROOT/'data/processed/papers.jsonl')}
    assert all(all(source_by_id[pid][k]==corpus[pid][k] for k in ('title','abstract')) for pid in ids),'Gold source differs from corpus'
    assert sha(HERE.parent/'v_recall/recall.py')==old['code_sha256']['recall.py'],'Current recall differs from pinned current release'
    files={}
    for name,h in old['old_files'].items():
        if name.startswith(('evaluation_only/','model_inputs/')):continue
        assert sha(pre/name)==h,'Frozen scorer/runtime changed: '+name
        files[name]=(pre/name).read_bytes()
    for name in ['recall.py','r2a_runner.py','repair.py','legacy.py']:
        assert sha(pre/name)==old['code_sha256'][name]
        files[name]=(pre/name).read_bytes()
    files['runner.py']=(HERE/'runner.py').read_bytes()
    papers=[{k:source_by_id[pid][k] for k in ('paper_id','title','abstract')} for pid in ids]
    files['model_inputs/papers.jsonl']=''.join(json.dumps(p,ensure_ascii=False)+'\n' for p in papers).encode()
    files['evaluation_only/human_gold.jsonl']=(gold_dir/'human_gold.jsonl').read_bytes()
    files['evaluation_only/gold_manifest.json']=(gold_dir/'gpt_review_manifest.json').read_bytes()
    generation=read(pre/'matrix_settings.json')['generation']
    generation.update(**old['model'],paper_ids=ids,corpus='model_inputs/papers.jsonl',output_dir='results/V-recall',cache_dir='/tmp/exp_a_gold400_hf')
    config=dict(version='v_recall_accepted_human_gold400_v1',kernel='htnkhi/exp-a-v-recall-human-gold400',dataset='htnkhi/exp-a-v-recall-human-gold400-inputs',
        paper_count=400,paper_ids=ids,model=old['model'],generation=generation,max_logical_calls=3,max_new_tokens_per_call=2048,
        files={n:hashlib.sha256(b).hexdigest() for n,b in files.items()},
        recall_sha256=old['code_sha256']['recall.py'],gold_sha256=sha(gold_dir/'human_gold.jsonl'),source_sha256=hashlib.sha256(files['model_inputs/papers.jsonl']).hexdigest(),
        gold_source_origin_sha256=sha(gold_dir/'review_papers.jsonl'),instruction_sha256=old['instruction_sha256'],
        reference_kind='human_gold',human_review_status='accepted',reference_to_generator=False,training_performed=False,adapters_enabled=False,
        worker_shards=2,scorer_threshold=.85,scorer_sha256=hashlib.sha256(files['scripts/exp_a/evaluate_exp_a.py']).hexdigest(),
        comparison_note='Same current V-recall, fresh draft+review+coverage. All400 included. Prior development/selection and AI-assisted human acceptance retained; not a newly sampled heldout experiment.')
    config['signature']=hashlib.sha256(json.dumps(config,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    write(RELEASE/'settings.json',config)
    work=RELEASE/'preflight_project';work.mkdir(parents=True,exist_ok=True)
    for name,raw in files.items():
        path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    write(work/'settings.json',config)
    runner=load('gold400_packaged_preflight',work/'runner.py');shared,checked,_,_=runner.verify(work,config,evaluation=True)
    assert len(checked)==400 and len(runner.shard(checked,0))==len(runner.shard(checked,1))==200
    dataset=RELEASE/'input-dataset';dataset.mkdir(parents=True,exist_ok=True);bundle=dataset/'gold400_bundle.zip.bin'
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in sorted(list(files)+['settings.json']):
            raw=(work/name).read_bytes();info=zipfile.ZipInfo(name,date_time=(2026,10,26,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;archive.writestr(info,raw)
    metadata=read(HERE.parent/'base_improvement/frozen_inputs_20261022/dataset-metadata.json')
    metadata.update(id=config['dataset'],title='Exp A V Recall Human Gold400 Inputs')
    write(dataset/'dataset-metadata.json',metadata)
    (dataset/'README.md').write_text('Private frozen source-only generation inputs and evaluation-only accepted human gold400. Source corpus: CSFCube v1.1 and SciFact, with original provenance/licenses retained in the project data/raw. AI-assisted labels accepted by the user on 2026-10-26. Never pass reference labels to the model. No adapter or training data included.\n',encoding='utf-8')
    boot=(HERE/'bootstrap.template.py').read_text(encoding='utf-8').replace('__SETTINGS_B64__',base64.b64encode(json.dumps(config,ensure_ascii=False).encode()).decode()).replace('__BUNDLE_SHA256__',sha(bundle))
    compile(boot,'run_experiment.py','exec');kernel=RELEASE/'kernel';kernel.mkdir(parents=True,exist_ok=True);(kernel/'run_experiment.py').write_text(boot,encoding='utf-8')
    kernel_metadata=read(PINNED/'kernel/kernel-metadata.json');kernel_metadata.update(id=config['kernel'],title='Exp A V Recall Human Gold400',dataset_sources=[config['dataset']]);write(kernel/'kernel-metadata.json',kernel_metadata)
    report=dict(status='passed',papers=400,gold_concepts=sum(len(v) for r in gold for v in r['facets'].values()),gold_sha256=config['gold_sha256'],signature=config['signature'],bundle_sha256=sha(bundle),bundle_bytes=bundle.stat().st_size,kernel_sha256=sha(kernel/'run_experiment.py'),
        current_recall_unchanged=True,scorer_unchanged=True,private=True,workers=2,shard_sizes=[200,200],max_logical_calls=3,max_output_tokens_per_call=2048,reference_to_generator=False,training_performed=False)
    write(RELEASE/'preflight.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
