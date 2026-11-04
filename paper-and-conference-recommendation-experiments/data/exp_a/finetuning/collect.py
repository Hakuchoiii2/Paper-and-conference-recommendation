"""Verify Kaggle outputs, recompute the paired scores, stage a reusable adapter."""
import argparse
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
import experiment
shared=experiment.shared

OUTPUT_PATTERN=(r'^exp_a_qlora/(adapters/.*|results/.*|qlora_settings\.json|data_manifest\.json|'
    r'instruction\.txt|model_inputs/test_papers\.jsonl|evaluation_only/test_references\.jsonl)$'
    r'|^experiment_summary\.json$')


def verify_download(root, expected):
    root=Path(root)
    settings=json.loads((root/'qlora_settings.json').read_text(encoding='utf-8'))
    shared.base.require(settings==expected, 'Downloaded experiment settings differ from the launched bundle')
    for name in ('data_manifest.json','instruction.txt','model_inputs/test_papers.jsonl','evaluation_only/test_references.jsonl'):
        shared.base.require(shared.base.sha256(root/name)==settings['files'][name], 'Downloaded input changed: '+name)
    data=json.loads((root/'data_manifest.json').read_text(encoding='utf-8'))
    shared.base.require(data['counts']==dict(train=467,dev=100,test=100), 'Unexpected split sizes')
    adapter=experiment.verify_adapter(root/experiment.ADAPTER,settings)
    training=json.loads((root/experiment.ADAPTER/'training_metadata.json').read_text(encoding='utf-8'))
    shared.base.require(training['status']=='complete' and training['global_steps']>0, 'Training did not finish')
    shared.base.require(training['base_model']==settings['model']['model']
        and training['base_revision']==settings['model']['revision'], 'Training used a different base checkpoint')
    shared.base.require(training['counts']==dict(train=467,dev=100), 'Training counts differ')
    for split in ('train','dev'):
        shared.base.require(training[split+'_paper_ids']==data['split_ids'][split], 'Training split IDs differ')
        shared.base.require(training['signature'][split+'_sha256']==settings['files']['model_inputs/'+split+'.jsonl'],
            'Training source hash differs')
    signature=training['signature']
    shared.base.require(signature['trainer_sha256']==settings['files']['data/exp_a/finetuning/train.py']
        and signature['split_manifest_sha256']==settings['files']['data_manifest.json']
        and signature['prompt_sha256']==settings['training']['prompt_sha256']
        and signature['schema_sha256']==settings['training']['schema_sha256'], 'Training provenance differs')
    summary=json.loads((root/'results/experiment_summary.json').read_text(encoding='utf-8'))
    shared.base.require(summary['status']=='complete' and summary['settings']==settings, 'Paired evaluation incomplete')
    papers=shared.base.read_jsonl(root/'model_inputs/test_papers.jsonl')
    references=shared.base.read_jsonl(root/'evaluation_only/test_references.jsonl')
    shared.base.require([p['paper_id'] for p in papers]==settings['test_ids']==data['split_ids']['test']
        and [r['paper_id'] for r in references]==settings['test_ids'] and len(papers)==100, 'Test cohort differs')
    for arm in experiment.ARMS:
        for paper in papers:
            record=shared.load_record(root/f'results/{arm}/records/{paper["paper_id"]}.json',settings['experiment_signature'])
            shared.base.require(record['paper_id']==paper['paper_id'] and record['arm']==arm, 'Prediction identity differs')
            if arm=='qlora':
                shared.base.require(record['adapter_manifest_sha256']==shared.base.sha256(root/experiment.ADAPTER/'adapter_manifest.json'),
                    'Prediction used another adapter')
    return adapter


def collect(root, build=None, destination=None):
    root=Path(root)
    build=Path(build or HERE/'build')
    destination=Path(destination or HERE/'adapter-dataset')
    expected=json.loads((build/'build_manifest.json').read_text(encoding='utf-8'))['settings']
    adapter=verify_download(root,expected)
    cloud=json.loads((root/'results/experiment_summary.json').read_text(encoding='utf-8'))
    # Reuse the locally verified pinned embedding model, with the unchanged scorer.
    previous=experiment.embedding_vectors
    experiment.embedding_vectors=lambda unused,labels: shared.evaluator.encode_labels(ROOT,labels)
    try:
        table=experiment.evaluate(root,expected)
    finally:
        experiment.embedding_vectors=previous
    for actual,remote in zip(table,cloud['table']):
        shared.base.require(actual['arm']==remote['arm'] and all(actual[k]==remote[k] for k in ('tp','fp','fn')),
            'Local/cloud matching counts differ; inspect before publishing')
    destination.mkdir(parents=True,exist_ok=True)
    shared.base.require(not any(destination.iterdir()), 'Adapter publication directory must be empty')
    source=root/experiment.ADAPTER
    for name in [*adapter['files'],'adapter_manifest.json']:
        shutil.copy2(source/name,destination/name)
    shared.base.write_json(destination/'dataset-metadata.json',dict(id=expected['adapter_dataset'],
        title='Qwen3 8B Scientific Facets QLoRA v1',licenses=[dict(name='other')]))
    (destination/'USAGE.md').write_text(
        '# Scientific facet QLoRA adapter v1\n\n'
        'Base: `Qwen/Qwen3-8B`, revision `'+expected['model']['revision']+'`.\n\n'
        'Adapter weights only. Load the pinned base with the experiment NF4 configuration, then '
        'set `adapter_path` to this dataset directory in the shared matrix loader. '
        'Use Transformers4.57.6 and PEFT0.18.1. Do not merge into an unrelated base revision.\n\n'
        '467 train /100 dev /100 test; pilot50 excluded. GPT/Codex AI reference labels; '
        'human review pending. Lowest development loss selects the saved adapter. '
        'See training_metadata.json and adapter_manifest.json for provenance and checksums.\n',encoding='utf-8')
    experiment.verify_adapter(destination,expected)
    result=dict(status='verified_and_staged',adapter_dataset=expected['adapter_dataset'],
        adapter_directory=str(destination),experiment_signature=expected['experiment_signature'],table=table,
        adapter_manifest_sha256=shared.base.sha256(destination/'adapter_manifest.json'))
    shared.base.write_json(build/'collection_manifest.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True,help='Downloaded exp_a_qlora directory')
    parser.add_argument('--build',type=Path)
    parser.add_argument('--destination',type=Path)
    args=parser.parse_args()
    print(json.dumps(collect(args.root,args.build,args.destination),ensure_ascii=False,indent=2))
