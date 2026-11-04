"""Package only the frozen training/development/test split and required runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'data/exp_a/.kaggle/matrix'))
import matrix

MODEL=dict(model='Qwen/Qwen3-8B',revision='b968826d9c46dd6066d109eabc6255188de91218')
KERNEL='htnkhi/exp-a-qwen-qlora'
DATASET='htnkhi/exp-a-qwen-qlora-inputs'
ADAPTER_DATASET='htnkhi/exp-a-qwen3-8b-facets-qlora-v1'


def build(data=None,destination=None):
    data=Path(data or HERE/'data')
    destination=Path(destination or HERE/'build')
    manifest=json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    matrix.base.require(manifest['counts']==dict(train=467,dev=100,test=100), 'Expected 667 papers split 467/100/100')
    matrix.base.require(manifest['token_limits']['verified'], 'Pinned-tokenizer preflight is required')
    matrix.base.require(all(v==0 for v in manifest['leakage'].values()), 'Dataset leakage detected')
    for name in ('train.jsonl','dev.jsonl','test_papers.jsonl','test_references.jsonl','instruction.txt'):
        matrix.base.require(matrix.base.sha256(data/name)==manifest['output_sha256'][name], 'Prepared data changed: '+name)
    mapping={'train.jsonl':'model_inputs/train.jsonl','dev.jsonl':'model_inputs/dev.jsonl',
        'test_papers.jsonl':'model_inputs/test_papers.jsonl','test_references.jsonl':'evaluation_only/test_references.jsonl',
        'instruction.txt':'instruction.txt','manifest.json':'data_manifest.json'}
    files={target:(data/name).read_bytes() for name,target in mapping.items()}
    for name in ('data/exp_a/finetuning/train.py','data/exp_a/finetuning/experiment.py',
        'data/exp_a/.kaggle/matrix/matrix.py','data/exp_a/build_exp_a.py','data/exp_a/extraction_v3.py',
        'scripts/exp_a/evaluate_exp_a.py','scripts/experiment_io.py','scripts/build_corpus.py',
        'scripts/download_sources.py','scripts/validate_all.py'):
        files[name]=(ROOT/name).read_bytes()
    relative=matrix.evaluator.MODEL_DIRECTORY
    download=json.loads((ROOT/relative/'download_manifest.json').read_text(encoding='utf-8'))
    files[relative+'/download_manifest.json']=(ROOT/relative/'download_manifest.json').read_bytes()
    for name,info in download['files'].items():
        if name!='model.safetensors':
            payload=(ROOT/relative/name).read_bytes()
            matrix.base.require(hashlib.sha256(payload).hexdigest()==info['sha256'], 'Embedding metadata changed')
            files[relative+'/'+name]=payload
    generation=json.loads((ROOT/'data/exp_a/config_v3_pilot50.json').read_text(encoding='utf-8'))
    generation.update(MODEL,paper_ids=manifest['split_ids']['test'])
    training=dict(MODEL,train_file='model_inputs/train.jsonl',dev_file='model_inputs/dev.jsonl',
        output_dir='adapters/qwen3-8b-facets-qlora-v1',split_manifest_file='data_manifest.json',
        prompt_sha256=manifest['prompt_sha256'],schema_sha256=manifest['schema_sha256'],
        max_seq_length=4096,epochs=3,gradient_accumulation_steps=8,learning_rate=2e-4,seed=42,
        cache_dir='/tmp/exp_a_huggingface')
    settings=dict(experiment_version='qlora_v1',model=MODEL,training=training,generation=generation,
        test_ids=manifest['split_ids']['test'],data_signature=matrix.digest(manifest),
        adapter_dataset=ADAPTER_DATASET,reference_kind='ai',
        limitations=['GPT/Codex AI labels, human review pending',
            'Test papers excluded from this QLoRA train/dev and all pilot50; existing-reference papers have prior project history',
            'One QLoRA training seed; semantic evaluator threshold0.85 unchanged'],
        files={name:hashlib.sha256(payload).hexdigest() for name,payload in files.items()})
    settings['experiment_signature']=matrix.digest(settings)
    files['qlora_settings.json']=(json.dumps(settings,ensure_ascii=False,indent=2)+'\n').encode()
    dataset,kernel=destination/'input-dataset',destination/'kernel'
    dataset.mkdir(parents=True,exist_ok=True)
    kernel.mkdir(parents=True,exist_ok=True)
    bundle=dataset/'qlora_bundle.zip.bin'
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,payload in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            archive.writestr(info,payload)
    matrix.base.write_json(dataset/'dataset-metadata.json',dict(id=DATASET,title='Exp A Qwen QLoRA Inputs',licenses=[dict(name='other')]))
    code=(HERE/'kernel.template.py').read_text(encoding='utf-8').replace('__BUNDLE_SHA256__',matrix.base.sha256(bundle))
    compile(code,'run_qlora.py','exec')
    (kernel/'run_qlora.py').write_text(code,encoding='utf-8')
    matrix.base.write_json(kernel/'kernel-metadata.json',dict(id=KERNEL,title='Exp A Qwen QLoRA',
        code_file='run_qlora.py',language='python',kernel_type='script',is_private=True,enable_gpu=True,
        enable_internet=True,machine_shape='NvidiaTeslaT4',dataset_sources=[DATASET],
        competition_sources=[],kernel_sources=[],model_sources=[]))
    result=dict(kernel=KERNEL,dataset=DATASET,adapter_dataset=ADAPTER_DATASET,counts=manifest['counts'],
        bundle_sha256=matrix.base.sha256(bundle),experiment_signature=settings['experiment_signature'],settings=settings)
    matrix.base.write_json(destination/'build_manifest.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path)
    parser.add_argument('--destination',type=Path)
    args=parser.parse_args()
    print(json.dumps({k:v for k,v in build(args.data,args.destination).items() if k!='settings'},indent=2))
