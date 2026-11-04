"""Bounded v2 inference; v1 source, weights and sealed bundles stay unchanged."""
import json
import math
import re
import time
import unicodedata

FACETS = ('problem', 'task', 'method', 'dataset', 'contribution')


def json_prefix(text):
    text = text.lstrip()
    try:
        value, end = json.JSONDecoder().raw_decode(text)
        return text[:end] if isinstance(value, dict) else None
    except ValueError:
        return None


def duplicate_concept(text):
    """Read complete items in unfinished arrays, without matching JSON inside strings."""
    decoder = json.JSONDecoder()
    def space(index):
        while index < len(text) and text[index].isspace():
            index += 1
        return index
    try:
        index = space(0)
        if text[index] != '{':
            return None
        index += 1
        while True:
            key, index = decoder.raw_decode(text, space(index))
            index = space(index)
            if not isinstance(key, str) or text[index] != ':':
                return None
            index = space(index + 1)
            if key in FACETS and text[index] == '[':
                seen = set()
                index = space(index + 1)
                while text[index] != ']':
                    item, index = decoder.raw_decode(text, index)
                    if isinstance(item, dict) and isinstance(item.get('concept'), str):
                        concept = ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', item['concept']).casefold()))
                        if concept and concept in seen:
                            return dict(facet=key, concept=item['concept'])
                        seen.add(concept)
                    index = space(index)
                    if text[index] == ',':
                        index = space(index + 1)
                    elif text[index] != ']':
                        return None
                index += 1
            else:
                _, index = decoder.raw_decode(text, index)
            index = space(index)
            if text[index] != ',':
                return None
            index = space(index + 1)
    except (ValueError, IndexError, TypeError):
        return None


class GenerationGuard:
    def __init__(self, tokenizer, input_length, seconds):
        self.tokenizer, self.input_length = tokenizer, input_length
        self.seconds, self.started = seconds, time.monotonic()
        self.reason, self.duplicate = None, None

    def __call__(self, input_ids, scores, **kwargs):
        if time.monotonic() - self.started >= self.seconds:
            self.reason = 'time_budget'
            return True
        text = self.tokenizer.decode(input_ids[0, self.input_length:], skip_special_tokens=True)
        if json_prefix(text) is not None:
            self.reason = 'json_complete'
            return True
        self.duplicate = duplicate_concept(text)
        if self.duplicate:
            self.reason = 'duplicate_concept'
            return True
        return False


def build_generator(model, tokenizer, config):
    """Return the existing (messages, seed) -> (text, statistics) interface."""
    config = {'max_new_tokens': 1024, 'seconds_per_call': 90, 'do_sample': True,
              'temperature': 0.7, 'top_p': 0.8, 'top_k': 20, **config}
    for key in ('max_new_tokens', 'top_k'):
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError(key + ' must be a positive integer')
    for key in ('seconds_per_call', 'temperature', 'top_p'):
        if (type(config[key]) not in (int, float) or not math.isfinite(config[key])
                or config[key] <= 0):
            raise ValueError(key + ' must be finite and positive')
    if config['top_p'] > 1 or type(config['do_sample']) is not bool:
        raise ValueError('Invalid sampling settings')

    def generate(messages, seed):
        import torch
        from transformers import StoppingCriteriaList
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        text = tokenizer.apply_chat_template(messages, tokenize=False,
            add_generation_prompt=True, enable_thinking=False)
        encoded = tokenizer(text, return_tensors='pt').to(model.device)
        length = encoded['input_ids'].shape[-1]
        if length + config['max_new_tokens'] > model.config.max_position_embeddings:
            raise ValueError('Source exceeds model context; truncation is forbidden')
        sampling = {k: config[k] for k in ('temperature', 'top_p', 'top_k')} if config['do_sample'] else {}
        started = time.monotonic()
        guard = GenerationGuard(tokenizer, length, config['seconds_per_call'])
        with torch.inference_mode():
            output = model.generate(**encoded, max_new_tokens=config['max_new_tokens'],
                do_sample=config['do_sample'], **sampling, use_cache=True,
                pad_token_id=tokenizer.eos_token_id,
                stopping_criteria=StoppingCriteriaList([guard]))[0, length:]
        raw = tokenizer.decode(output, skip_special_tokens=True).strip()
        prefix = json_prefix(raw)
        reason = guard.reason or ('token_limit' if len(output) == config['max_new_tokens'] else 'eos')
        return prefix if prefix is not None else raw, dict(
            usage=dict(input_tokens=length, output_tokens=len(output)),
            generation_seconds=round(time.monotonic() - started, 6), stop_reason=reason,
            reached_token_limit=reason == 'token_limit',
            bounded_stop=reason in ('time_budget', 'duplicate_concept', 'token_limit'),
            duplicate=guard.duplicate, raw_output_untrimmed=raw,
            discarded_suffix_chars=len(raw) - len(prefix) if prefix is not None else 0)
    return generate


def load_model(config, shared):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    if torch.cuda.device_count() != 1:
        raise ValueError('Each inference worker must see exactly one GPU')
    options = dict(revision=config['revision'], cache_dir=config.get('cache_dir', '/tmp/exp_a_huggingface'),
                   local_files_only=config.get('offline', False), token=False, trust_remote_code=False)
    tokenizer = AutoTokenizer.from_pretrained(config['model'], **options)
    attention = shared.install_attention()
    model = AutoModelForCausalLM.from_pretrained(config['model'], **options, use_safetensors=True,
        torch_dtype=torch.float16, device_map={'': 0}, attn_implementation=attention,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16)).eval()
    if model.config._commit_hash != config['revision']:
        raise ValueError('Loaded model revision differs')
    if config.get('adapter_path'):
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, config['adapter_path'], is_trainable=False).eval()
    runtime = dict(model=config['model'], revision=config['revision'], torch=torch.__version__,
        transformers=transformers.__version__, gpu=torch.cuda.get_device_name(0),
        adapter_enabled=bool(config.get('adapter_path')), quantization='nf4_double_fp16',
        attention=attention, enable_thinking=False, use_cache=True)
    return model, tokenizer, runtime
