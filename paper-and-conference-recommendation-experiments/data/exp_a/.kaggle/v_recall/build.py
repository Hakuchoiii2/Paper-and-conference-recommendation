"""Build a separate code-only recall experiment over the same private frozen inputs."""
import base64
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent
PINNED=HERE.parent/'r2a/release_20261024_v1'
OLD=HERE.parent/'base_improvement'
RELEASE=HERE/'release_20261026_v1'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    if (RELEASE/'launch_report.json').exists():raise ValueError('Launched release is immutable')
    settings=read(PINNED/'settings.json')
    files={'runner.py':HERE/'runner.py','recall.py':HERE/'recall.py','r2a_runner.py':PINNED/'preflight_project/runner.py',
        'repair.py':PINNED/'preflight_project/repair.py','legacy.py':PINNED/'preflight_project/legacy.py'}
    for new,old in [('r2a_runner.py','runner.py'),('repair.py','repair.py'),('legacy.py','legacy.py')]:
        assert sha(files[new])==settings['code_sha256'][old],'Pinned V code changed'
    assets={n:path.read_bytes() for n,path in files.items()}
    for n,b in assets.items():compile(b,n,'exec')
    settings.update(version='exp_a_v_recall_pilot50_v1',arms=['R2a-V','V-recall'],kernel='htnkhi/exp-a-v-recall-pilot50',
        code_sha256={n:hashlib.sha256(b).hexdigest() for n,b in assets.items()},
        definitions={'R2a-V':'Unchanged V; cached draft and up to two original reviews',
            'V-recall':'Exact cached draft and first V review; replace final review with task/method additions only'},
        max_logical_calls=3,max_new_tokens_per_call=2048,new_call_caps={'R2a-V':2,'V-recall':2},
        coverage_facets=['task','method'],coverage_application='add_only_individual_scoped_validation',
        training_performed=False,adapters_enabled=False,reference_to_generator=False,
        annotation_schema_unchanged=True,scorer_unchanged=True,
        comparison_limitations='Reused development cohort and AI reference; human review pending. Actual costs differ.')
    settings.pop('signature',None);settings['signature']=hashlib.sha256(json.dumps(settings,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    write(RELEASE/'settings.json',settings)
    boot=load('recall_original_bootstrap',OLD/'bootstrap.template.py')
    snapshot=OLD/'frozen_inputs_20261022';preflight=RELEASE/'preflight_project'
    if not preflight.exists():boot.extract_original(snapshot/'matrix_bundle.zip.bin',preflight,settings)
    for n,b in assets.items():(preflight/n).write_bytes(b)
    write(preflight/'improvement_settings.json',settings)
    dest=preflight/'results/R0/records';dest.mkdir(parents=True,exist_ok=True)
    for pid,h in settings['r0_record_sha256'].items():
        src=snapshot/f'8b_original/records/{pid}.json';assert sha(src)==h;shutil.copyfile(src,dest/src.name)
    runner=load('recall_preflight_runner',preflight/'runner.py');shared,papers,original=runner.verify(preflight,settings)
    assert original['generation']['max_attempts']==3 and original['generation']['max_new_tokens']==2048
    instruction='\n\n'.join((preflight/original['generation'][k]).read_text(encoding='utf-8') for k in ('guideline','prompt'))
    assert hashlib.sha256(instruction.encode()).hexdigest()==settings['instruction_sha256']
    b64=lambda b:base64.b64encode(b).decode('ascii')
    source=(HERE/'bootstrap.template.py').read_text(encoding='utf-8').replace('__SETTINGS_B64__',b64(json.dumps(settings,ensure_ascii=False).encode()))
    source=source.replace('__ASSETS_B64__',b64(json.dumps({n:b64(b) for n,b in assets.items()}).encode())).replace('__EXTRACT_ORIGINAL__',inspect.getsource(boot.extract_original))
    compile(source,'run_experiment.py','exec')
    kernel=RELEASE/'kernel';kernel.mkdir(parents=True,exist_ok=True);(kernel/'run_experiment.py').write_text(source,encoding='utf-8')
    metadata=read(PINNED/'kernel/kernel-metadata.json');metadata.update(id=settings['kernel'],title='Exp A V Recall Pilot50')
    write(kernel/'kernel-metadata.json',metadata)
    report=dict(status='passed',papers=len(papers),verified_frozen_records=50,signature=settings['signature'],
        code_sha256=settings['code_sha256'],bootstrap_sha256=sha(kernel/'run_experiment.py'),private=metadata['is_private'],
        dataset_sources=metadata['dataset_sources'],model=settings['model'],training_performed=False,
        max_logical_calls=3,new_call_caps=settings['new_call_caps'],reference_to_generator=False)
    write(RELEASE/'preflight.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
