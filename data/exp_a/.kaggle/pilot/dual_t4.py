"""Run two isolated model workers and reuse the verified A-part merger."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import build_exp_a as base


def worker_configs(config):
    count = len(config['paper_ids'])
    base.require(count >= 2 and config.get('paper_range') == [1, None],
                 'Dual-T4 requires at least two papers and the full pilot range')
    midpoint = (count + 1) // 2
    return [dict(config, paper_range=bounds, output_dir=config['output_dir'] + f'_parts/gpu_{gpu}')
            for gpu, bounds in enumerate(([1, midpoint], [midpoint + 1, count]))]


def run_workers(root, config, *, gpu_count):
    base.require(gpu_count >= 2, 'Dual-T4 requires two visible GPUs; refusing to silently run on one')
    root = Path(root).resolve()
    if (root / config['output_dir'] / 'manifest.json').exists():
        return base.check_outputs(root, config)
    from merge_exp_a import merge
    workers = worker_configs(config)
    processes = []
    try:
        for gpu, worker in enumerate(workers):
            config_path = root / f'data/exp_a/config_pilot_gpu_{gpu}.json'
            base.write_json(config_path, worker)
            env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), CUDA_DEVICE_ORDER='PCI_BUS_ID',
                       OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONDONTWRITEBYTECODE='1')
            command = [sys.executable, '-X', 'utf8', '-B', str(Path(__file__).resolve()),
                       '--root', str(root), '--worker-config', str(config_path)]
            print(json.dumps(dict(worker_gpu=gpu, paper_range=worker['paper_range'],
                                  output_dir=worker['output_dir'])), flush=True)
            processes.append(subprocess.Popen(command, env=env))
        for gpu, process in enumerate(processes):
            if process.wait() != 0:
                raise RuntimeError(f'GPU worker {gpu} failed; part checkpoints retained, merged output not published')
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait()
    return merge(root, [worker['output_dir'] for worker in workers], config['output_dir'])


def run_worker(root, config_path):
    import torch
    base.require(torch.cuda.device_count() == 1, 'A worker must see exactly one isolated GPU')
    print(json.dumps(dict(physical_gpu=os.environ['CUDA_VISIBLE_DEVICES'],
                          visible_gpu_count=torch.cuda.device_count(), gpu=torch.cuda.get_device_name(0))), flush=True)
    torch.set_num_threads(2)
    config = json.loads(Path(config_path).read_text(encoding='utf-8'))
    base.generate(Path(root), config)
    base.check_outputs(Path(root), config, allow_partial=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--worker-config', type=Path, required=True)
    args = parser.parse_args()
    run_worker(args.root, args.worker_config)
