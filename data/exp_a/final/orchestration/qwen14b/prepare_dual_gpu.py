"""Build a Qwen14B-only release from the frozen v1, preserving data and policy."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RELEASE = HERE/'release_20261102_dual_gpu_v1'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Patch anchor differs: '+old[:120])
    return text.replace(old, new)


def build(destination=RELEASE):
    previous = HERE/'release_20261031_v1'
    code = (previous/'kernel/run_qwen14b.py').read_text(encoding='utf-8')
    tree = ast.parse(code)
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == 'RUNTIME_FILES' for target in node.targets))
    files = ast.literal_eval(assignment.value)
    trainer = files['train.py'].decode()
    trainer = replace_once(trainer, 'def completion_loss(model, inputs, *, return_outputs=False, num_items_in_batch=None):',
        'def legacy_completion_loss(model, inputs, *, return_outputs=False, num_items_in_batch=None):')
    # Bind the cross-device objective used by the existing completion-only Trainer.
    trainer = replace_once(trainer, 'def make_completion_trainer(**kwargs):',
        'def completion_loss(model, inputs, *, return_outputs=False, num_items_in_batch=None):\n'
        '    from dual_gpu import completion_loss as dual_loss\n'
        '    return dual_loss(model, inputs, return_outputs=return_outputs, num_items_in_batch=num_items_in_batch)\n\n\n'
        'def make_completion_trainer(**kwargs):')
    trainer = replace_once(trainer,
        '    import torch\n    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig',
        '    from dual_gpu import load_base, require_two_gpus, check_adapter_placement, smoke_examples\n'
        '    import torch\n    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig')
    trainer = replace_once(trainer, "    if config['model'] != BASE_MODEL and 'revision' not in settings:",
        "    config['smoke_test'] = bool(settings.get('smoke_test', False))\n    if config['model'] != BASE_MODEL and 'revision' not in settings:")
    trainer = replace_once(trainer, "trainer_sha256=sha256(__file__), runtime=runtime,", 
        "trainer_sha256=sha256(__file__), dual_gpu_sha256=sha256(root/'dual_gpu.py'), training_parallelism='explicit_two_gpu_single_process', runtime=runtime,")
    guard = "    if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or int(os.environ.get('WORLD_SIZE', '1')) != 1:\n        raise ValueError('Run training in a fresh single-GPU process with CUDA_VISIBLE_DEVICES=0; distributed training is disabled')"
    trainer = replace_once(trainer, guard,
        "    if config['smoke_test']:\n        encoded_train = smoke_examples(encoded_train, config['gradient_accumulation_steps'])\n        encoded_dev = smoke_examples(encoded_dev, 2)\n    require_two_gpus()")
    start = trainer.index('    model = AutoModelForCausalLM.from_pretrained(')
    end = trainer.index('    actual_revision = ', start)
    trainer = trainer[:start]+"    model = load_base(config, options, attention)\n"+trainer[end:]
    trainer = replace_once(trainer, '    model = prepare_adapter(model, config)',
        '    model = prepare_adapter(model, config)\n    check_adapter_placement(model)')
    trainer = replace_once(trainer, 'callbacks=[SaveIntegrity()])',
        'callbacks=[SaveIntegrity()]+([__import__("smoke").gradient_callback()] if config["smoke_test"] else []))\n    if not runner.is_model_parallel or runner.args.n_gpu != 1 or runner.args.train_batch_size != 1:\n        raise ValueError("Trainer must use model parallelism with microbatch1, without DataParallel")')
    trainer = replace_once(trainer, '    tokenizer.save_pretrained(adapter_dir)',
        '    tokenizer.save_pretrained(adapter_dir)\n    if config["smoke_test"]:\n        __import__("smoke").save_probe(runner.model, encoded_train, adapter_dir/"probe.json")')
    trainer = replace_once(trainer, "runtime=dict(**runtime, gpu=torch.cuda.get_device_name(0), attention_implementation=attention),",
        "runtime=dict(**runtime, gpu=[torch.cuda.get_device_name(i) for i in (0,1)], device_map=model.hf_device_map, training_parallelism='explicit_two_gpu_single_process', attention_implementation=attention),")
    # The old objective stays out of the release, so there is only one active loss implementation.
    start = trainer.index('def legacy_completion_loss(')
    end = trainer.index('def completion_loss(', start)
    trainer = trainer[:start]+trainer[end:]
    files['train.py'] = trainer.encode()
    for name in ('dual_gpu.py', 'smoke.py'):
        files[name] = (HERE/name).read_bytes()

    runtime = files['runtime.py'].decode()
    runtime = replace_once(runtime, "path.name not in ('train_state', 'provisional_adapter')",
        "path.name not in ('train_state', 'provisional_adapter', 'smoke_state', 'smoke_adapter')")
    runtime = replace_once(runtime, 'def train(root, settings, old, compat):',
        'def train(root, settings, old, compat, *, smoke=False):')
    runtime = replace_once(runtime, "    config = dict(settings['training'], reuse_completed=True)",
        "    config = dict(settings['training'], reuse_completed=True, smoke_test=smoke)\n    if smoke:\n        config.update(output_dir='smoke_adapter', checkpoint_dir='smoke_state', epochs=1, logging_steps=1, warmup_ratio=0.0)")
    runtime = replace_once(runtime, "    old.write(root/'results/training_summary.json', metadata)",
        "    old.write(root/('results/smoke_training_summary.json' if smoke else 'results/training_summary.json'), metadata)")
    runtime = replace_once(runtime, "    old.require(old.command(root, '--train').wait() == 0, 'Training failed; checkpoints retained')",
        "    old.require(old.command(root, '--smoke', gpu='0,1').wait() == 0, 'Dual-GPU smoke training failed; full run not started')\n"
        "    old.require(old.command(root, '--smoke-reload', gpu='0,1').wait() == 0, 'Smoke adapter reload failed; full run not started')\n"
        "    old.require(old.command(root, '--train', gpu='0,1').wait() == 0, 'Training failed; checkpoints retained')")
    runtime = replace_once(runtime, "    parser.add_argument('--train', action='store_true')",
        "    parser.add_argument('--train', action='store_true')\n    parser.add_argument('--smoke', action='store_true')\n    parser.add_argument('--smoke-reload', action='store_true')")
    runtime = replace_once(runtime, '    if args.train:',
        "    if args.smoke:\n        train(root, settings, old, compat, smoke=True)\n    elif args.smoke_reload:\n        helper = old.load('smoke_reload_trainer', root/'train.py')\n        __import__('smoke').reload(root, settings, helper)\n    elif args.train:")
    files['runtime.py'] = runtime.encode()
    config = json.loads(files['config.json'])
    config.update(version='exp_a_qwen14b_dual_gpu_20261102_v1', training_gpus=2,
                  training_parallelism='explicit_two_gpu_single_process', smoke_gate=True)
    files['config.json'] = (json.dumps(config, indent=2)+'\n').encode()
    # Replace only the embedded runtime assignment, keeping the validated bootstrap/input contract.
    lines = code.splitlines(keepends=True)
    code = ''.join(lines[:assignment.lineno-1])+'RUNTIME_FILES = '+repr(files)+'\n'+''.join(lines[assignment.end_lineno:])
    code = replace_once(code, "inputs = set(settings['files'])|{'compat.py', 'frozen_runtime.py'}",
        "inputs = set(settings['files'])|{'compat.py', 'frozen_runtime.py', 'dual_gpu.py', 'smoke.py'}")
    code = code.replace('/kaggle/working/exp_a_qwen14b', '/kaggle/working/exp_a_qwen14b_dual_gpu')
    code = replace_once(code, "    import torch\n", "    os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'expandable_segments:True')\n    import torch\n")
    compile(code, 'run_qwen14b.py', 'exec')
    for name, data in files.items():
        if name.endswith('.py'):
            compile(data, name, 'exec')
    destination = Path(destination)
    kernel = destination/'kernel'
    kernel.mkdir(parents=True, exist_ok=True)
    (kernel/'run_qwen14b.py').write_text(code, encoding='utf-8', newline='\n')
    metadata = json.loads((previous/'kernel/kernel-metadata.json').read_text(encoding='utf-8'))
    (kernel/'kernel-metadata.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    report = dict(parent_release=previous.name, kernel=metadata['id'],
        code_sha256=hashlib.sha256(code.encode()).hexdigest(),
        runtime_files={name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        input_bundle_sha256='6259ddb570c4c208d0aeb2e8a17d5ac984701f391f65f08964145bd6a710b510',
        training_gpus=2, training_processes=1, smoke_gate=True)
    (destination/'build_manifest.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return files, code


if __name__ == '__main__':
    build()
    print('Built '+str(RELEASE))
