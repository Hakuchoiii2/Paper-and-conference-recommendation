"""Single-GPU QLoRA with assistant-only loss and checksum-checked explicit resume."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path


BASE_MODEL = 'Qwen/Qwen3-8B'
BASE_REVISION = 'b968826d9c46dd6066d109eabc6255188de91218'
PINNED_REQUIREMENTS = ('transformers==4.57.6', 'peft==0.18.1', 'accelerate==1.15.0', 'bitsandbytes==0.50.2')
RESUME_FILES = ('adapter_config.json', 'adapter_model.safetensors', 'trainer_state.json',
                'optimizer.pt', 'scheduler.pt', 'rng_state.pth')
DEFAULTS = dict(model=BASE_MODEL, revision=BASE_REVISION, max_seq_length=4096, epochs=3,
                seed=42, gradient_accumulation_steps=8, learning_rate=2e-4,
                warmup_ratio=0.03, weight_decay=0.0, max_grad_norm=0.3, logging_steps=5)


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def file_hashes(directory, exclude=()):
    directory = Path(directory)
    return {str(path.relative_to(directory)).replace('\\', '/'): sha256(path)
            for path in sorted(directory.rglob('*')) if path.is_file() and path.name not in exclude}


def verify_hashes(directory, files):
    directory = Path(directory).resolve()
    if not isinstance(files, dict) or not files:
        raise ValueError('Missing file checksums')
    for name, expected in files.items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or not path.is_file() or sha256(path) != expected:
            raise ValueError(f'File checksum differs or file is missing: {name}')


def read_examples(path):
    rows, seen = [], set()
    with Path(path).open(encoding='utf-8') as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            paper_id = row.get('paper_id')
            if not isinstance(paper_id, str) or not paper_id:
                raise ValueError(f'{path}:{line_number}: missing paper_id')
            if paper_id in seen:
                raise ValueError(f'Duplicate paper_id in {path}: {paper_id}')
            if not isinstance(row.get('provenance'), dict) or not row['provenance']:
                raise ValueError(f'{paper_id}: missing label provenance')
            rows.append(row)
            seen.add(paper_id)
    if not rows:
        raise ValueError(f'Empty training/development file: {path}')
    return rows


def validate_split_ids(train_rows, dev_rows):
    overlap = {row['paper_id'] for row in train_rows} & {row['paper_id'] for row in dev_rows}
    if overlap:
        raise ValueError(f'Train/dev paper_id overlap: {sorted(overlap)}')


def encode_example(tokenizer, row, max_seq_length):
    """Keep the exact inference prefix; supervise the final JSON and its EOS only."""
    paper_id, messages = row['paper_id'], row.get('messages')
    if not isinstance(messages, list) or [message.get('role') for message in messages] != ['system', 'user', 'assistant']:
        raise ValueError(f'{paper_id}: expected exactly system/user/assistant messages')
    if any(not isinstance(message.get('content'), str) or not message['content'] for message in messages):
        raise ValueError(f'{paper_id}: message content must be a nonempty string')
    try:
        answer = json.loads(messages[-1]['content'])
    except json.JSONDecodeError as error:
        raise ValueError(f'{paper_id}: assistant completion must be a JSON object') from error
    if not isinstance(answer, dict):
        raise ValueError(f'{paper_id}: assistant completion must be a JSON object')
    prefix = tokenizer.apply_chat_template(messages[:-1], tokenize=False,
        add_generation_prompt=True, enable_thinking=False)
    complete = tokenizer.apply_chat_template(messages, tokenize=False,
        add_generation_prompt=False, enable_thinking=False)
    if not complete.startswith(prefix):
        raise ValueError(f'{paper_id}: chat template changes the inference prefix')
    prompt_ids = tokenizer(prefix, add_special_tokens=False)['input_ids']
    completion_ids = tokenizer(complete[len(prefix):], add_special_tokens=False)['input_ids']
    eos = tokenizer.eos_token_id
    if eos is None or eos not in completion_ids:
        raise ValueError(f'{paper_id}: chat template does not terminate the answer with EOS')
    end = completion_ids.index(eos)
    if end == 0 or tokenizer.decode(completion_ids[end + 1:]).strip():
        raise ValueError(f'{paper_id}: unexpected content after the assistant EOS')
    completion_ids = completion_ids[:end + 1]
    input_ids = prompt_ids + completion_ids
    if len(input_ids) > max_seq_length:
        raise ValueError(f'{paper_id}: {len(input_ids)} tokens exceeds max_seq_length={max_seq_length}; truncation forbidden')
    return dict(input_ids=input_ids, attention_mask=[1] * len(input_ids),
                labels=[-100] * len(prompt_ids) + completion_ids)


class CompletionCollator:
    def __init__(self, pad_token_id):
        if pad_token_id is None:
            raise ValueError('A padding token ID is required')
        self.pad_token_id = pad_token_id

    def __call__(self, rows):
        import torch
        length = max(len(row['input_ids']) for row in rows)
        return {key: torch.tensor([row[key] + [padding] * (length - len(row[key])) for row in rows],
                                  dtype=torch.long)
                for key, padding in (('input_ids', self.pad_token_id), ('attention_mask', 0), ('labels', -100))}


def check_run_directory(state_dir, signature, adapter_dir, resume=None, reuse_completed=False):
    """Refuse ambiguous restarts, incompatible runs, and modified cached artifacts."""
    state_dir, adapter_dir = Path(state_dir).resolve(), Path(adapter_dir).resolve()
    manifest_path = state_dir / 'run_manifest.json'
    if not manifest_path.is_file():
        if state_dir.exists() and any(state_dir.iterdir()):
            raise ValueError('Refusing an unmarked nonempty training state directory')
        if resume is not None:
            raise ValueError('Cannot resume without a matching run manifest')
    else:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('signature') != signature:
            raise ValueError('Training signature differs; use a new output/state directory')
        if manifest.get('status') == 'complete':
            if not reuse_completed or resume is not None:
                raise ValueError('Run is complete; set reuse_completed=true to verify and reuse it')
            verify_hashes(adapter_dir, manifest.get('files'))
            return json.loads((adapter_dir / 'training_metadata.json').read_text(encoding='utf-8'))
        if resume is None:
            raise ValueError('Incomplete run exists; select an explicit resume_from_checkpoint or a new state directory')
        checkpoint = Path(resume).resolve()
        if checkpoint.parent != state_dir or not checkpoint.name.startswith('checkpoint-'):
            raise ValueError('Resume checkpoint must belong to this training state directory')
        for name in RESUME_FILES:
            if not (checkpoint / name).is_file():
                raise ValueError(f'Incomplete resume checkpoint: missing {name}')
        checkpoint_manifest = json.loads((checkpoint / 'checkpoint_manifest.json').read_text(encoding='utf-8'))
        if checkpoint_manifest.get('signature') != signature:
            raise ValueError('Checkpoint signature differs')
        verify_hashes(checkpoint, checkpoint_manifest.get('files'))
    if adapter_dir.exists() and any(adapter_dir.iterdir()):
        raise ValueError('Refusing to overwrite a nonempty adapter output directory')
    return None


def prepare_adapter(model, settings, quantized=True):
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    model.config.use_cache = False
    if quantized:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True,
            gradient_checkpointing_kwargs={'use_reentrant': False})
    else:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    config = LoraConfig(task_type='CAUSAL_LM', target_modules='all-linear', r=16,
        lora_alpha=32, lora_dropout=0.05, bias='none', revision=settings.get('revision', BASE_REVISION))
    return get_peft_model(model, config)


def install_attention(root):
    path = Path(root) / 'data/exp_a/.kaggle/matrix/matrix.py'
    spec = importlib.util.spec_from_file_location('finetuning_matrix_attention', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.install_attention()


def completion_loss(model, inputs, *, return_outputs=False, num_items_in_batch=None):
    """Exact masked causal loss without allocating vocabulary logits for prompt tokens."""
    import torch
    batch=dict(inputs)
    labels=batch.pop('labels')
    shifted=labels[:,1:]
    positions=torch.nonzero((shifted!=-100).any(dim=0),as_tuple=False).flatten()
    if not positions.numel():
        raise ValueError('Batch has no supervised completion tokens')
    outputs=model(**batch,logits_to_keep=positions,use_cache=False)
    targets=shifted.index_select(1,positions)
    loss=torch.nn.functional.cross_entropy(outputs.logits.float().reshape(-1,outputs.logits.shape[-1]),
        targets.reshape(-1),ignore_index=-100,reduction='sum' if num_items_in_batch is not None else 'mean')
    if num_items_in_batch is not None:
        loss=loss/num_items_in_batch
    return (loss,outputs) if return_outputs else loss


def make_completion_trainer(**kwargs):
    from transformers import Trainer
    class CompletionTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            return completion_loss(model,inputs,return_outputs=return_outputs,num_items_in_batch=num_items_in_batch)
    runner=CompletionTrainer(**kwargs)
    # Trainer supplies the total supervised-token count across accumulated batches.
    runner.model_accepts_loss_kwargs=True
    return runner


def train(root, settings):
    """Read only train/dev JSONL. Save the lowest-dev-loss PEFT adapter, never merged weights."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from transformers import TrainerCallback, TrainingArguments, set_seed
    root = Path(root).resolve()
    config = {key: settings.get(key, value) for key, value in DEFAULTS.items()}
    if config['model'] != BASE_MODEL and 'revision' not in settings:
        raise ValueError('A model override requires an explicit checkpoint revision')
    for key in ('max_seq_length', 'gradient_accumulation_steps', 'logging_steps'):
        if not isinstance(config[key], int) or config[key] <= 0:
            raise ValueError(f'{key} must be a positive integer')
    if config['epochs'] <= 0 or config['learning_rate'] <= 0:
        raise ValueError('epochs and learning_rate must be positive')
    for key in ('prompt_sha256', 'schema_sha256'):
        value = settings.get(key, '')
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError(f'{key} must be a SHA-256 hex digest')
    runtime = {name: importlib.metadata.version(name) for name in ('torch', 'transformers', 'peft', 'accelerate', 'bitsandbytes')}
    if runtime['transformers'] != '4.57.6' or runtime['peft'] != '0.18.1':
        raise ValueError('This trainer requires transformers==4.57.6 and peft==0.18.1')
    train_path, dev_path = root / settings['train_file'], root / settings['dev_file']
    adapter_dir = root / settings.get('output_dir', 'adapters/qwen3-8b-facets-qlora-v1')
    state_dir = root / settings.get('checkpoint_dir', 'train_state')
    resume = root / settings['resume_from_checkpoint'] if settings.get('resume_from_checkpoint') else None
    train_rows, dev_rows = read_examples(train_path), read_examples(dev_path)
    validate_split_ids(train_rows, dev_rows)
    options = dict(revision=config['revision'], cache_dir=settings.get('cache_dir'),
                   local_files_only=settings.get('offline', False), token=False, trust_remote_code=False)
    tokenizer = AutoTokenizer.from_pretrained(config['model'], **options)
    tokenizer.padding_side = 'right'
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    signature = dict(contract_version=1, config=config, train_sha256=sha256(train_path), dev_sha256=sha256(dev_path),
        prompt_sha256=settings['prompt_sha256'], schema_sha256=settings['schema_sha256'],
        split_manifest_sha256=sha256(root / settings['split_manifest_file']) if settings.get('split_manifest_file') else None,
        chat_template_sha256=hashlib.sha256(tokenizer.chat_template.encode('utf-8')).hexdigest(),
        trainer_sha256=sha256(__file__), runtime=runtime, loss='assistant_completion_and_eos_selected_logits', enable_thinking=False,
        quantization='nf4_double_fp16', lora=dict(r=16, alpha=32, dropout=0.05, target_modules='all-linear'))
    completed = check_run_directory(state_dir, signature, adapter_dir, resume, settings.get('reuse_completed', False))
    if completed is not None:
        return completed
    encoded_train = [encode_example(tokenizer, row, config['max_seq_length']) for row in train_rows]
    encoded_dev = [encode_example(tokenizer, row, config['max_seq_length']) for row in dev_rows]
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or int(os.environ.get('WORLD_SIZE', '1')) != 1:
        raise ValueError('Run training in a fresh single-GPU process with CUDA_VISIBLE_DEVICES=0; distributed training is disabled')
    set_seed(config['seed'])
    attention = install_attention(root) if config['model'] == BASE_MODEL else 'sdpa'
    write_json(state_dir / 'run_manifest.json', dict(signature=signature, status='running'))
    model = AutoModelForCausalLM.from_pretrained(config['model'], **options, use_safetensors=True,
        torch_dtype=torch.float16, device_map={'': 0}, attn_implementation=attention,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16))
    actual_revision = getattr(model.config, '_commit_hash', None)
    if actual_revision != config['revision']:
        raise ValueError(f'Loaded checkpoint revision differs: {actual_revision} != {config["revision"]}')
    model = prepare_adapter(model, config)

    class SaveIntegrity(TrainerCallback):
        def on_save(self, args, state, control, **kwargs):
            checkpoint = Path(args.output_dir) / f'checkpoint-{state.global_step}'
            write_json(checkpoint / 'checkpoint_manifest.json', dict(signature=signature,
                files=file_hashes(checkpoint, exclude={'checkpoint_manifest.json'})))

    arguments = TrainingArguments(output_dir=str(state_dir), num_train_epochs=config['epochs'],
        per_device_train_batch_size=1, per_device_eval_batch_size=1,
        gradient_accumulation_steps=config['gradient_accumulation_steps'], learning_rate=config['learning_rate'],
        warmup_ratio=config['warmup_ratio'], weight_decay=config['weight_decay'], max_grad_norm=config['max_grad_norm'],
        optim='paged_adamw_8bit', lr_scheduler_type='cosine', fp16=True, bf16=False, tf32=False,
        gradient_checkpointing=True, gradient_checkpointing_kwargs={'use_reentrant': False},
        eval_strategy='epoch', save_strategy='epoch', load_best_model_at_end=True,
        metric_for_best_model='eval_loss', greater_is_better=False, save_total_limit=2,
        prediction_loss_only=True, logging_steps=config['logging_steps'], seed=config['seed'], data_seed=config['seed'],
        dataloader_num_workers=0, group_by_length=True, report_to=[], push_to_hub=False, save_safetensors=True)
    runner = make_completion_trainer(model=model, args=arguments, train_dataset=encoded_train, eval_dataset=encoded_dev,
        data_collator=CompletionCollator(tokenizer.pad_token_id), processing_class=tokenizer, callbacks=[SaveIntegrity()])
    result = runner.train(resume_from_checkpoint=str(resume) if resume else None)
    if runner.state.best_model_checkpoint is None or runner.state.best_metric is None:
        raise RuntimeError('Training finished without a development-loss-selected checkpoint')
    runner.model.save_pretrained(adapter_dir, safe_serialization=True)
    tokenizer.save_pretrained(adapter_dir)
    metadata = dict(status='complete', base_model=config['model'], base_revision=actual_revision, signature=signature,
        label_source='ai_generated_reference', checkpoint_selection='lowest_dev_loss',
        best_checkpoint=Path(runner.state.best_model_checkpoint).name, best_dev_loss=float(runner.state.best_metric),
        global_steps=runner.state.global_step, training_metrics=result.metrics,
        train_paper_ids=[row['paper_id'] for row in train_rows], dev_paper_ids=[row['paper_id'] for row in dev_rows],
        counts=dict(train=len(train_rows), dev=len(dev_rows)),
        tokens={name: dict(max_input=max(len(row['input_ids']) for row in rows),
            total_input=sum(len(row['input_ids']) for row in rows),
            total_supervised=sum(sum(token != -100 for token in row['labels']) for row in rows))
            for name, rows in (('train', encoded_train), ('dev', encoded_dev))},
        runtime=dict(**runtime, gpu=torch.cuda.get_device_name(0), attention_implementation=attention),
        files=file_hashes(adapter_dir))
    write_json(adapter_dir / 'training_metadata.json', metadata)
    write_json(state_dir / 'run_manifest.json', dict(signature=signature, status='complete', files=file_hashes(adapter_dir)))
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--settings', type=Path, required=True)
    args = parser.parse_args()
    train(args.root, json.loads(args.settings.read_text(encoding='utf-8')))
