"""Explicit, single-process Qwen3-14B placement; never replicate the model."""
import json
import os


def device_map():
    return {'model.embed_tokens': 0, 'model.rotary_emb': 0,
            **{f'model.layers.{i}': 0 if i < 20 else 1 for i in range(40)},
            'model.norm': 1, 'lm_head': 1}


def require_two_gpus():
    import torch
    if torch.cuda.device_count() != 2 or int(os.environ.get('WORLD_SIZE', '1')) != 1:
        raise ValueError('Qwen14B requires one process with CUDA_VISIBLE_DEVICES=0,1; DDP is disabled')


def memory(stage):
    import torch
    report = []
    for gpu in range(torch.cuda.device_count()):
        torch.cuda.synchronize(gpu)
        report.append(dict(gpu=gpu, name=torch.cuda.get_device_name(gpu),
            allocated_gib=torch.cuda.memory_allocated(gpu)/2**30,
            reserved_gib=torch.cuda.memory_reserved(gpu)/2**30,
            peak_allocated_gib=torch.cuda.max_memory_allocated(gpu)/2**30))
    print('GPU_MEMORY '+json.dumps(dict(stage=stage, devices=report)), flush=True)
    return report


def load_base(config, options, attention):
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, BitsAndBytesConfig
    require_two_gpus()
    if config['model'] != 'Qwen/Qwen3-14B':
        raise ValueError('This device map is only for Qwen/Qwen3-14B')
    architecture = AutoConfig.from_pretrained(config['model'], **options)
    if (architecture.num_hidden_layers, architecture.hidden_size, architecture.tie_word_embeddings) != (40, 5120, False):
        raise ValueError('Qwen14B architecture differs from the tested placement')
    model = AutoModelForCausalLM.from_pretrained(config['model'], **options, use_safetensors=True,
        torch_dtype=torch.float16, device_map=device_map(), attn_implementation=attention,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16))
    if model.config._commit_hash != config['revision']:
        raise ValueError('Loaded Qwen14B revision differs')
    memory('base_loaded_on_two_gpus')
    return model


def check_adapter_placement(model):
    """Require trainable LoRA weights on both cards and a frozen base."""
    devices = set()
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            if 'lora_' not in name:
                raise ValueError('Unexpected trainable base parameter: '+name)
            devices.add(parameter.device.index)
    if devices != {0, 1}:
        raise ValueError('Trainable LoRA parameters must occupy both GPUs')
    memory('fp32_preparation_and_lora_ready')


def completion_loss(model, inputs, *, return_outputs=False, num_items_in_batch=None):
    """Same completion-only objective, with indices/targets valid across devices."""
    import torch
    batch = dict(inputs)
    shifted = batch.pop('labels')[:, 1:]
    positions = torch.nonzero((shifted != -100).any(dim=0), as_tuple=False).flatten()
    if not positions.numel():
        raise ValueError('Batch has no supervised completion tokens')
    # A scalar suffix length survives dispatch hooks without cross-device index tensors.
    start = positions[0].item()
    outputs = model(**batch, logits_to_keep=shifted.shape[1]+1-start, use_cache=False)
    targets = shifted[:, start:].to(outputs.logits.device)
    logits = outputs.logits[:, :-1, :]
    loss = torch.nn.functional.cross_entropy(logits.float().reshape(-1, logits.shape[-1]),
        targets.reshape(-1), ignore_index=-100, reduction='sum' if num_items_in_batch is not None else 'mean')
    if num_items_in_batch is not None:
        loss = loss/torch.as_tensor(num_items_in_batch, device=loss.device)
    return (loss, outputs) if return_outputs else loss


def smoke_examples(encoded, accumulation):
    """Exercise both the longest context and the largest supervised-logit allocation."""
    longest = max(encoded, key=lambda row: len(row['input_ids']))
    completion = max(encoded, key=lambda row: sum(label != -100 for label in row['labels']))
    return [longest if i % 2 == 0 else completion for i in range(accumulation)]
