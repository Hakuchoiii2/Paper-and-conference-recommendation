"""Build/preflight a code-only Kaggle release; never upload source/reference content."""
import base64
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'base_improvement'
RELEASE=HERE/'release_20261024_v1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def b64(raw):return base64.b64encode(raw).decode('ascii')


def main():
    settings=read(OLD/'release_20261022_v2/settings.json')
    historical=read(OLD/'summary_20261022_v2/base_v1_r1_r2/results/experiment_summary.json')
    assert historical['status']=='complete' and historical['settings']==settings
    assets={name:path.read_bytes() for name,path in dict(
        **{'runner.py':HERE/'runner.py','repair.py':HERE/'repair.py','legacy.py':OLD/'improvement.py'}).items()}
    settings.update(version='exp_a_r2a_pilot50_1',arms=['R2a-V','R2a-P','R2a-full'],
        kernel='htnkhi/exp-a-r2a-v-p-full-pilot50',
        code_sha256={name:hashlib.sha256(raw).hexdigest() for name,raw in assets.items()},
        historical_R2=next(r for r in historical['arms'] if r['arm']=='R2'),
        historical_summary_sha256=sha(OLD/'summary_20261022_v2/base_v1_r1_r2/results/experiment_summary.json'),
        definitions={'R2a-V':'scoped validator only; original R2 full-review repair',
            'R2a-P':'original validator; indexed repair of flagged items only',
            'R2a-full':'scoped validator plus indexed repair; no coverage intervention'},
        new_call_cap_per_paper=2,annotation_schema_unchanged=True,scorer_unchanged=True)
    settings.pop('signature',None)
    settings['signature']=hashlib.sha256(json.dumps(settings,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    write(RELEASE/'settings.json',settings)
    spec=importlib.util.spec_from_file_location('original_bootstrap',OLD/'bootstrap.template.py')
    boot=importlib.util.module_from_spec(spec);spec.loader.exec_module(boot)
    snapshot=OLD/'frozen_inputs_20261022'
    preflight=RELEASE/'preflight_project'
    if not preflight.exists():boot.extract_original(snapshot/'matrix_bundle.zip.bin',preflight,settings)
    for name,raw in assets.items():
        compile(raw,name,'exec');(preflight/name).write_bytes(raw)
    write(preflight/'improvement_settings.json',settings)
    dest=preflight/'results/R0/records';dest.mkdir(parents=True,exist_ok=True)
    for pid,h in settings['r0_record_sha256'].items():
        src=snapshot/f'8b_original/records/{pid}.json'
        assert sha(src)==h
        shutil.copyfile(src,dest/src.name)
    spec=importlib.util.spec_from_file_location('r2a_preflight',preflight/'runner.py')
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    shared,papers,original=runner.verify(preflight,settings)
    changed=[];draft_counts={False:0,True:0}
    for paper in papers:
        r0=shared.load_record(dest/(paper['paper_id']+'.json'),settings['baseline_signature'])
        draft=r0['audit']['attempt_scores'][0]
        a=runner.repair.assess(shared,draft['raw_output'],paper,scoped=False)[2]
        b=runner.repair.assess(shared,draft['raw_output'],paper,scoped=True)[2]
        assert a['validation_errors']==draft['validation_errors']
        draft_counts[False]+=bool(a['validation_errors']);draft_counts[True]+=bool(b['validation_errors'])
        if a!=b:changed.append(paper['paper_id'])
    source=(HERE/'bootstrap.template.py').read_text(encoding='utf-8')
    source=source.replace('__SETTINGS_B64__',b64(json.dumps(settings,ensure_ascii=False).encode()))
    source=source.replace('__ASSETS_B64__',b64(json.dumps({n:b64(r) for n,r in assets.items()}).encode()))
    source=source.replace('__EXTRACT_ORIGINAL__',inspect.getsource(boot.extract_original))
    compile(source,'run_experiment.py','exec')
    kernel=RELEASE/'kernel';kernel.mkdir(parents=True,exist_ok=True)
    (kernel/'run_experiment.py').write_text(source,encoding='utf-8')
    metadata=read(OLD/'release_20261022_v2/kernel/kernel-metadata.json')
    metadata.update(id=settings['kernel'],title='Exp A R2a V P Full Pilot50')
    write(kernel/'kernel-metadata.json',metadata)
    report=dict(status='passed',papers=50,original_invalid_drafts=draft_counts[False],
        scoped_invalid_drafts=draft_counts[True],validator_changed_papers=changed,
        source_bundle_sha256=sha(snapshot/'matrix_bundle.zip.bin'),record_hashes_verified=50,
        signature=settings['signature'],code_sha256=settings['code_sha256'],
        bootstrap_sha256=sha(kernel/'run_experiment.py'),private=metadata['is_private'],
        dataset_sources=metadata['dataset_sources'],reference_to_generator=False,
        logical_call_cap=3,new_call_cap=2,training_performed=False)
    write(RELEASE/'preflight.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
