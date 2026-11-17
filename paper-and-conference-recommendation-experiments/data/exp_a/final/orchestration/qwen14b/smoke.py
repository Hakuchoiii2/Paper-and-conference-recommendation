"""One disposable optimizer step, then verify the adapter in a fresh process."""
import json
from pathlib import Path


def gradient_callback():
    import torch
    from transformers import TrainerCallback
    from dual_gpu import memory

    class CheckGradients(TrainerCallback):
        def on_train_begin(self, args, state, control, model=None, **kwargs):
            self.before = {}
            self.parameters = {}
            self.checked = False
            for name, parameter in model.named_parameters():
                if parameter.requires_grad and 'lora_B' in name:
                    gpu = parameter.device.index
                    if gpu not in self.before:
                        self.parameters[gpu] = parameter
                        self.before[gpu] = parameter.detach().cpu().clone()
            if set(self.before) != {0, 1}:
                raise ValueError('Smoke test requires LoRA B weights on both GPUs')

        def on_pre_optimizer_step(self, args, state, control, model=None, **kwargs):
            nonzero = set()
            for name, parameter in model.named_parameters():
                if parameter.requires_grad:
                    gradient = parameter.grad
                    if gradient is None or not torch.isfinite(gradient).all().item():
                        raise ValueError('Missing/non-finite LoRA gradient: '+name)
                    if torch.count_nonzero(gradient).item():
                        nonzero.add(parameter.device.index)
            if nonzero != {0, 1}:
                raise ValueError('Smoke test needs nonzero gradients on both GPUs')
            self.checked = True
            memory('smoke_backward')

        def on_train_end(self, args, state, control, **kwargs):
            if not self.checked or state.global_step != 1:
                raise ValueError('Smoke test did not complete exactly one checked optimizer step')
            for gpu, parameter in self.parameters.items():
                if torch.equal(parameter.detach().cpu(), self.before[gpu]):
                    raise ValueError(f'LoRA weights did not update on GPU{gpu}')
            memory('smoke_optimizer_step_passed')

    return CheckGradients()


def save_probe(model, encoded, destination):
    import torch
    from dual_gpu import completion_loss
    model.eval()
    cases = []
    for row in (encoded[0], encoded[1]):
        inputs = {key: torch.tensor([value], device='cuda:0') for key, value in row.items()}
        with torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
            loss = completion_loss(model, inputs).item()
        if not torch.isfinite(torch.tensor(loss)).item():
            raise ValueError('Non-finite smoke evaluation loss')
        cases.append(dict(example=row, loss=loss))
    Path(destination).write_text(json.dumps(dict(cases=cases), indent=2)+'\n', encoding='utf-8')


def reload(root, settings, helper):
    import torch
    from peft import PeftModel, prepare_model_for_kbit_training
    from dual_gpu import load_base, memory, completion_loss
    adapter = root/'smoke_adapter'
    metadata = json.loads((adapter/'training_metadata.json').read_text(encoding='utf-8'))
    helper.verify_hashes(adapter, metadata['files'])
    config = settings['training']
    options = dict(revision=config['revision'], cache_dir=config.get('cache_dir'), token=False, trust_remote_code=False)
    model = load_base(config, options, helper.install_attention(root))
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=False)
    model = PeftModel.from_pretrained(model, str(adapter), is_trainable=False).eval()
    if any(parameter.requires_grad for parameter in model.parameters()):
        raise ValueError('Reloaded inference adapter must be frozen')
    from safetensors.torch import load_file
    from peft import get_peft_model_state_dict
    saved = load_file(str(adapter/'adapter_model.safetensors'))
    restored = get_peft_model_state_dict(model)
    if set(saved) != set(restored):
        raise ValueError('Reloaded adapter tensor names differ')
    for name, tensor in saved.items():
        if not torch.equal(tensor, restored[name].detach().cpu()):
            raise ValueError('Reloaded adapter weight differs: '+name)
    probe = json.loads((adapter/'probe.json').read_text(encoding='utf-8'))
    losses = []
    for case in probe['cases']:
        inputs = {key: torch.tensor([value], device='cuda:0') for key, value in case['example'].items()}
        with torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
            loss = completion_loss(model, inputs).item()
        if not torch.isfinite(torch.tensor(loss)).item() or abs(loss-case['loss']) > 1e-3:
            raise ValueError(f'Reloaded adapter loss differs: {loss} vs {case["loss"]}')
        losses.append(loss)
    report = dict(status='passed', settings_signature=settings['signature'],
                  gradient_devices=[0, 1], optimizer_steps=1, reloaded_tensors=len(saved), losses=losses,
                  memory=memory('smoke_reload_passed'))
    helper.write_json(root/'results/dual_gpu_smoke.json', report)
    print('DUAL_GPU_SMOKE_PASSED '+json.dumps(report), flush=True)


if __name__ == '__main__':
    import train
    root = Path(__file__).resolve().parent
    reload(root, json.loads((root/'settings.json').read_text(encoding='utf-8')), train)
