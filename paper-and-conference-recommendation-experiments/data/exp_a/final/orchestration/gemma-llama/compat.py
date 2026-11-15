"""Model-specific chat and decoding; the extraction/evaluation policy stays frozen."""
import json
import time


def format_messages(messages, model):
    result = [dict(message) for message in messages]
    if model.startswith('google/gemma-2-') and result and result[0]['role'] == 'system':
        if len(result) < 2 or result[1]['role'] != 'user':
            raise ValueError('Gemma system instruction requires a following user message')
        result[1]['content'] = result[0]['content'] + '\n\n' + result[1]['content']
        result = result[1:]
    return result


def stop_ids(tokenizer):
    ids = {tokenizer.eos_token_id}
    vocabulary = tokenizer.get_vocab()
    for token in ('<|eot_id|>', '<end_of_turn>'):
        if token in vocabulary:
            ids.add(vocabulary[token])
    return sorted(value for value in ids if value is not None)


def encode_example(tokenizer, row, max_seq_length):
    messages = row.get('messages', [])
    if [m.get('role') for m in messages] != ['system', 'user', 'assistant']:
        raise ValueError('Expected system/user/assistant training messages')
    if any(not isinstance(m.get('content'), str) or not m['content'] for m in messages):
        raise ValueError('Empty training message')
    if not isinstance(json.loads(messages[-1]['content']), dict):
        raise ValueError('Expected JSON object completion')
    messages = format_messages(messages, tokenizer.name_or_path)
    prefix = tokenizer.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True)
    complete = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    if not complete.startswith(prefix):
        raise ValueError('Chat template changes the inference prefix')
    prompt = tokenizer(prefix, add_special_tokens=False)['input_ids']
    answer = tokenizer(complete[len(prefix):], add_special_tokens=False)['input_ids']
    end_ids = set(stop_ids(tokenizer))
    ends = [i for i, value in enumerate(answer) if value in end_ids]
    if not ends or ends[0] == 0 or tokenizer.decode(answer[ends[0]+1:]).strip():
        raise ValueError('Missing assistant end-of-turn or unexpected trailing content')
    answer = answer[:ends[0]+1]
    tokens = prompt + answer
    if len(tokens) > max_seq_length:
        raise ValueError(f'{row["paper_id"]}: {len(tokens)} tokens; truncation forbidden')
    return dict(input_ids=tokens, attention_mask=[1]*len(tokens), labels=[-100]*len(prompt)+answer)


def attention_for(model, install_attention):
    # Gemma2's softcapping is part of its logits; generic SDPA omits it.
    return 'eager' if model.startswith('google/gemma-2-') else install_attention()


def load_generator(config, install_attention):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise ValueError('Each generation worker must see exactly one CUDA GPU')
    options = dict(revision=config['revision'], cache_dir='/tmp/exp_a_huggingface', token=True, trust_remote_code=False)
    tokenizer = AutoTokenizer.from_pretrained(config['model'], **options)
    attention = attention_for(config['model'], install_attention)
    model = AutoModelForCausalLM.from_pretrained(config['model'], **options, use_safetensors=True,
        torch_dtype=torch.float16, device_map={'': 0}, attn_implementation=attention,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16))
    revision = model.config._commit_hash
    if revision != config['revision']:
        raise ValueError('Loaded model revision differs')
    model = PeftModel.from_pretrained(model, config['adapter_path'], is_trainable=False).eval()
    ends = stop_ids(tokenizer)
    runtime = dict(model=config['model'], model_revision=revision, quantization='nf4_double',
        torch_version=torch.__version__, transformers_version=transformers.__version__,
        gpu_name=torch.cuda.get_device_name(0), attention_implementation=attention,
        chat_adapter='native_llama_or_folded_gemma2_v1', stop_token_ids=ends, enable_thinking=False)

    def generate(messages, seed):
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        text = tokenizer.apply_chat_template(format_messages(messages, config['model']),
                                             tokenize=False, add_generation_prompt=True)
        encoded = tokenizer(text, add_special_tokens=False, return_tensors='pt').to(model.device)
        length = encoded['input_ids'].shape[-1]
        if length + config['max_new_tokens'] > model.config.max_position_embeddings:
            raise ValueError('Source exceeds context; truncation forbidden')
        started = time.monotonic()
        with torch.inference_mode():
            output = model.generate(**encoded, max_new_tokens=config['max_new_tokens'], do_sample=False,
                eos_token_id=ends, pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id)[0, length:]
        return tokenizer.decode(output, skip_special_tokens=True).strip(), dict(
            usage=dict(input_tokens=length, output_tokens=len(output)),
            generation_seconds=time.monotonic()-started, reached_token_limit=len(output) == config['max_new_tokens'])
    return generate, runtime
