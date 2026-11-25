"""Build a separate immutable compact/patch experiment from the prior gold400 release."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PRIOR=HERE.parent/'v_recall_gold400/release_20261026_v1'
RELEASE=HERE/'release_20261027_v1'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    if (RELEASE/'launch_report.json').exists() or (RELEASE/'dataset_upload_report.json').exists():
        raise ValueError('Uploaded release is immutable; use a new version')
    old=read(PRIOR/'settings.json');pre=PRIOR/'preflight_project';files={}
    for name,checksum in old['files'].items():
        if name in ('runner.py','recall.py'):continue
        assert sha(pre/name)==checksum,'Changed prior frozen file: '+name
        files[name]=(pre/name).read_bytes()
    prompt='data/exp_a/prompts/extraction_compact_v1.md'
    files[prompt]=(HERE/'compact_prompt.md').read_bytes()
    files['runner.py']=(HERE/'runner.py').read_bytes()
    baseline=HERE.parent/'v_recall_gold400/downloads/checked_20261027/exp_a_v_recall_gold400/results/experiment_summary.json'
    observed=read(baseline)
    assert observed['status']=='complete' and observed['paper_count']==400 and observed['excluded_papers']==0
    assert observed['gold_sha256']==old['gold_sha256'] and observed['source_sha256']==old['source_sha256'] and observed['threshold']==.85
    assert observed['settings']['scorer_sha256']==old['scorer_sha256']
    files['baseline/experiment_summary.json']=baseline.read_bytes()
    generation=dict(old['generation'],prompt=prompt,output_dir='results/Compact-patch')
    instruction=b'\n\n'.join(files[generation[k]] for k in ('guideline','prompt'))
    settings=dict(version='compact_indexed_patch_gold400_v1',kernel='htnkhi/exp-a-compact-patch-human-gold400',dataset=old['dataset'],
        paper_count=400,paper_ids=old['paper_ids'],model=old['model'],generation=generation,max_logical_calls=3,max_new_tokens_per_call=2048,
        files={n:hashlib.sha256(raw).hexdigest() for n,raw in files.items()},gold_sha256=old['gold_sha256'],source_sha256=old['source_sha256'],
        instruction_sha256=hashlib.sha256(instruction).hexdigest(),scorer_sha256=old['scorer_sha256'],scorer_threshold=.85,
        worker_shards=2,reference_kind='human_gold',human_review_status='accepted',reference_to_generator=False,training_performed=False,adapters_enabled=False,
        comparison_note='Exploratory development on already inspected gold400; compact source draft then at most two indexed repairs. No broad coverage. Compare frozen prior observed stages; actual cost differs.')
    settings['signature']=hashlib.sha256(json.dumps(settings,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    write(RELEASE/'settings.json',settings)
    work=RELEASE/'preflight_project'
    for name,raw in files.items():
        path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    write(work/'settings.json',settings)
    runner=load('compact_packaged_preflight',work/'runner.py')
    shared,papers,_,_=runner.verify(work,settings,evaluation=True)
    assert len(papers)==400 and len(runner.shard(papers,0))==len(runner.shard(papers,1))==200
    gold=shared.base.read_jsonl(work/'evaluation_only/human_gold.jsonl')
    assert len(gold)==400 and {r['paper_id'] for r in gold}==set(settings['paper_ids'])
    assert all(r.get('human_review_status')=='accepted' and r.get('reviewer_type')=='human' and r.get('review_status')=='reviewed' for r in gold)
    dataset=RELEASE/'input-dataset';dataset.mkdir(parents=True,exist_ok=True);bundle=dataset/'gold400_bundle.zip.bin'
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in sorted(list(files)+['settings.json']):
            info=zipfile.ZipInfo(name,date_time=(2026,10,27,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;archive.writestr(info,(work/name).read_bytes())
    (dataset/'README.md').write_text('LOCAL OFFLINE PREFLIGHT ONLY. Do not upload this bundle. Cloud launch reuses the already uploaded private prior gold400 dataset and uploads only code/prompt/aggregate metrics, not paper source or reference labels.\n',encoding='utf-8')
    # Only changed code/prompt and aggregate baseline metadata enter the new kernel source.
    overlay={n:base64.b64encode(raw).decode() for n,raw in files.items() if n not in old['files'] or hashlib.sha256(raw).hexdigest()!=old['files'][n]}
    assert set(overlay)=={'runner.py',prompt,'baseline/experiment_summary.json'},'Unexpected cloud overlay payload'
    boot=(HERE/'bootstrap.template.py').read_text(encoding='utf-8').replace('__SETTINGS_B64__',base64.b64encode(json.dumps(settings,ensure_ascii=False).encode()).decode()).replace('__BUNDLE_SHA256__',sha(PRIOR/'input-dataset/gold400_bundle.zip.bin')).replace('__INPUT_SETTINGS_B64__',base64.b64encode(json.dumps(old,ensure_ascii=False).encode()).decode()).replace('__OVERLAY_B64__',base64.b64encode(json.dumps(overlay).encode()).decode())
    compile(boot,'run_experiment.py','exec')
    kernel=RELEASE/'kernel';kernel.mkdir(parents=True,exist_ok=True);(kernel/'run_experiment.py').write_text(boot,encoding='utf-8')
    metadata=read(PRIOR/'kernel/kernel-metadata.json')
    metadata.update(id=settings['kernel'],title='Exp A Compact Patch Human Gold400',is_private=True,dataset_sources=[settings['dataset']])
    write(kernel/'kernel-metadata.json',metadata)
    report=dict(status='passed',papers=400,gold_concepts=sum(len(v) for r in gold for v in r['facets'].values()),gold_sha256=settings['gold_sha256'],source_sha256=settings['source_sha256'],signature=settings['signature'],
        bundle_sha256=sha(bundle),bundle_bytes=bundle.stat().st_size,kernel_sha256=sha(kernel/'run_experiment.py'),private=True,workers=2,shard_sizes=[200,200],
        scorer_unchanged=True,helpers_unchanged=True,max_logical_calls=3,max_output_tokens_per_call=2048,reference_to_generator=False,training_performed=False,
        reused_private_dataset=settings['dataset'],cloud_input_bundle_sha256=sha(PRIOR/'input-dataset/gold400_bundle.zip.bin'),cloud_overlay_files=sorted(overlay),source_or_gold_uploaded=False)
    write(RELEASE/'preflight.json',report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
