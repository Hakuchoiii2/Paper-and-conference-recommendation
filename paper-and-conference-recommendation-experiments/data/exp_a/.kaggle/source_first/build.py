"""Code-only private Kaggle build; reuse the verified frozen pilot dataset."""
import base64
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'base_improvement'
PINNED=HERE.parent/'r2a/release_20261024_v1'
RELEASE=HERE/'release_20261025_v1'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    if (RELEASE/'launch_report.json').exists():raise ValueError('Launched release is immutable; choose a new version')
    settings=read(PINNED/'settings.json')
    files={'runner.py':HERE/'runner.py','units.py':HERE/'units.py','r2a_runner.py':PINNED/'preflight_project/runner.py',
           'repair.py':PINNED/'preflight_project/repair.py','legacy.py':PINNED/'preflight_project/legacy.py'}
    for new,old in [('r2a_runner.py','runner.py'),('repair.py','repair.py'),('legacy.py','legacy.py')]:
        assert sha(files[new])==settings['code_sha256'][old],'Pinned V code changed'
    assets={n:p.read_bytes() for n,p in files.items()}
    for n,b in assets.items():compile(b,n,'exec')
    settings.update(version='exp_a_v_source_first_pilot50_v1',arms=['R2a-V','Source-first'],kernel='htnkhi/exp-a-v-source-first-pilot50',
        code_sha256={n:hashlib.sha256(b).hexdigest() for n,b in assets.items()},
        definitions={'R2a-V':'Exact previous scoped-validator V; cached raw draft plus up to 2 original reviews',
                     'Source-first':'Verbatim source inventory/roles/context -> original schema -> optional validator repair'},
        max_logical_calls=3,max_new_tokens_per_call=2048,new_call_caps={'R2a-V':2,'Source-first':3},
        training_performed=False,adapters_enabled=False,reference_to_generator=False,
        inventory_error_policy='one inventory retry then extraction; no more than 3 total calls',
        annotation_schema_unchanged=True,scorer_unchanged=True,
        comparison_limitations='Same development cohort and common max logical calls/tokens; V inherits draft cost, actual input/output tokens and latency may differ; no semantic quality certification.')
    settings.pop('signature',None);settings['signature']=hashlib.sha256(json.dumps(settings,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    write(RELEASE/'settings.json',settings)
    boot=load('source_original_bootstrap',OLD/'bootstrap.template.py')
    snapshot=OLD/'frozen_inputs_20261022';preflight=RELEASE/'preflight_project'
    if not preflight.exists():boot.extract_original(snapshot/'matrix_bundle.zip.bin',preflight,settings)
    for n,b in assets.items():(preflight/n).write_bytes(b)
    write(preflight/'improvement_settings.json',settings)
    dest=preflight/'results/R0/records';dest.mkdir(parents=True,exist_ok=True)
    for pid,h in settings['r0_record_sha256'].items():
        src=snapshot/f'8b_original/records/{pid}.json';assert sha(src)==h;shutil.copyfile(src,dest/src.name)
    runner=load('source_preflight_runner',preflight/'runner.py')
    shared,papers,original=runner.verify(preflight,settings)
    assert original['generation']['max_attempts']==3 and original['generation']['max_new_tokens']==2048
    instruction='\n\n'.join((preflight/original['generation'][k]).read_text(encoding='utf-8') for k in ('guideline','prompt'))
    assert hashlib.sha256(instruction.encode()).hexdigest()==settings['instruction_sha256']
    # Exercise new packaged inventory path against every real source without invoking a model.
    for paper in papers:
        eid,opt=next(iter(shared.base.evidence_options(paper).items()))
        plan=dict(paper_id=paper['paper_id'],units=[dict(evidence_id=eid,span=opt['evidence'],roles=['task'],origin='uncertain',context_ids=[])])
        runner.units.validate_inventory(plan,paper,shared)
    source=(HERE/'bootstrap.template.py').read_text(encoding='utf-8')
    b64=lambda b:base64.b64encode(b).decode('ascii')
    source=source.replace('__SETTINGS_B64__',b64(json.dumps(settings,ensure_ascii=False).encode()))
    source=source.replace('__ASSETS_B64__',b64(json.dumps({n:b64(b) for n,b in assets.items()}).encode()))
    source=source.replace('__EXTRACT_ORIGINAL__',inspect.getsource(boot.extract_original))
    compile(source,'run_experiment.py','exec')
    kernel=RELEASE/'kernel';kernel.mkdir(parents=True,exist_ok=True)
    (kernel/'run_experiment.py').write_text(source,encoding='utf-8')
    metadata=read(PINNED/'kernel/kernel-metadata.json')
    metadata.update(id=settings['kernel'],title='Exp A V vs Source First Pilot50')
    write(kernel/'kernel-metadata.json',metadata)
    report=dict(status='passed',papers=len(papers),verified_frozen_records=50,verified_inventory_source_packets=50,
        signature=settings['signature'],code_sha256=settings['code_sha256'],bootstrap_sha256=sha(kernel/'run_experiment.py'),
        private=metadata['is_private'],dataset_sources=metadata['dataset_sources'],training_performed=False,
        model=settings['model'],logical_call_cap=3,new_call_caps=settings['new_call_caps'],reference_to_generator=False)
    write(RELEASE/'preflight.json',report);print(json.dumps(report,indent=2))

if __name__=='__main__':main()
