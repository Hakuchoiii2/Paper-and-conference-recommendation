"""Use the accepted Qwen3 non-thinking encoder/decoder for both model sizes."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


encode_example = load('public_qwen_encoding', ROOT/'train.py').encode_example


def load_generator(config, install_attention):
    matrix = load('public_qwen_decoder', ROOT/'data/exp_a/.kaggle/matrix.py')
    return matrix.load_generator(config)
