"""
Script: generate_facets.py
Vị trí: data/conference_recommendation_dataset/generate_facets.py

Nhiệm vụ:
  Trích xuất 5 khía cạnh khoa học (problem, task, method, dataset, contribution)
  cho các bài báo của nhánh Khuyến nghị Hội nghị (đặc biệt là 186 bài test),
  sử dụng các mô hình LLM và Adapter PEFT QLoRA đã huấn luyện từ Exp A.

Các mô hình được hỗ trợ:
  - Qwen8B   : Qwen/Qwen3-8B
  - Gemma9B  : google/gemma-2-9b-it
  - Llama8B  : meta-llama/Llama-3.1-8B-Instruct
  - Qwen4B   : Qwen/Qwen3-4B
  - Qwen14B  : Qwen/Qwen3-14B

Cách sử dụng:
  # 1. Kiểm tra cấu hình và đường dẫn mà không nạp model GPU:
  python data/conference_recommendation_dataset/generate_facets.py --check --model Qwen8B

  # 2. Chạy thử nghiệm trích xuất trên 5 bài test đầu tiên:
  python data/conference_recommendation_dataset/generate_facets.py --model Qwen8B --limit 5

  # 3. Chạy trích xuất toàn bộ 186 bài test của nhánh Hội nghị:
  python data/conference_recommendation_dataset/generate_facets.py --model Qwen8B

  # 4. Chạy với mô hình Gemma-9B hoặc Llama-8B:
  python data/conference_recommendation_dataset/generate_facets.py --model Gemma9B
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from typing import Dict, List, Optional

sys.dont_write_bytecode = True

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Xác định thư mục gốc của repo
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FACET_KEYS = ("problem", "task", "method", "dataset", "contribution")

# Danh mục cấu hình mặc định cho các mô hình
MODEL_CONFIGS = {
    "Qwen8B": {
        "base_model": "Qwen/Qwen3-8B",
        "revision": "b968826d9c46dd6066d109eabc6255188de91218",
        "adapter_dirs": [
            "data/exp_a/final/adapter/Qwen8B",
            "data/exp_a/final/results/Qwen8B/adapter",
        ],
        "selected_checkpoint": "checkpoint-105",
    },
    "Gemma9B": {
        "base_model": "google/gemma-2-9b-it",
        "revision": None,
        "adapter_dirs": [
            "data/exp_a/final/adapter/Gemma9B",
            "data/exp_a/final/results/Gemma9B/adapter",
        ],
        "selected_checkpoint": "checkpoint-105",
    },
    "Llama8B": {
        "base_model": "meta-llama/Llama-3.1-8B-Instruct",
        "revision": "0e9e39f249a16976918f6564b8830bc894c89659",
        "adapter_dirs": [
            "data/exp_a/final/adapter/Llama8B",
            "data/exp_a/final/results/Llama8B/adapter",
        ],
        "selected_checkpoint": "checkpoint-105",
    },
    "Qwen4B": {
        "base_model": "Qwen/Qwen3-4B",
        "revision": None,
        "adapter_dirs": [
            "data/exp_a/final/adapter/Qwen4B",
            "data/exp_a/final/results/Qwen4B/adapter",
        ],
        "selected_checkpoint": "checkpoint-105",
    },
    "Qwen14B": {
        "base_model": "Qwen/Qwen3-14B",
        "revision": None,
        "adapter_dirs": [
            "data/exp_a/final/adapter/Qwen14B",
            "data/exp_a/final/results/Qwen14B/adapter",
        ],
        "selected_checkpoint": "checkpoint-70",
    },
}


def read_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> List[Dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def find_adapter_dir(model_key: str, repo: Path = REPO_ROOT) -> Optional[Path]:
    """Tìm thư mục adapter khả dụng của model."""
    candidates = MODEL_CONFIGS.get(model_key, {}).get("adapter_dirs", [])
    for rel_path in candidates:
        full_p = repo / rel_path
        if full_p.exists() and (full_p / "adapter_config.json").exists():
            return full_p
    return None


def read_input_papers(path: Path) -> List[Dict]:
    """Đọc dữ liệu bài báo đầu vào và kiểm tra hợp lệ."""
    rows = read_jsonl(path)
    papers, seen = [], set()
    for r in rows:
        pid = r.get("paper_id")
        if not pid or pid in seen:
            continue
        title = r.get("title", "").strip()
        abstract = r.get("abstract", "").strip()
        if not title or not abstract:
            continue
        seen.add(pid)
        papers.append({
            "paper_id": pid,
            "title": title,
            "abstract": abstract,
            "year": r.get("year"),
            "conference_id": r.get("conference_id"),
        })
    return papers


def load_exp_a_runtime(repo: Path = REPO_ROOT):
    """Nạp module chính thức từ runtime đóng băng của Exp A (Read-only)."""
    runtime_dir = repo / "data/exp_a/final/runtime"
    policy_path = runtime_dir / "gold_policy.py"
    if not policy_path.exists():
        raise FileNotFoundError(f"Không tìm thấy runtime policy tại: {policy_path}")

    spec = importlib.util.spec_from_file_location("gold_policy", policy_path)
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
    shared = policy.load_shared(runtime_dir)
    return policy, shared


def export_facets(shared, output_dir: Path, papers: List[Dict], records: List[Dict], model_key: str):
    """Xuất kết quả 5 facets ra file facets_silver.jsonl chuẩn."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "facets_silver.jsonl"
    
    rows = []
    for r in records:
        f_dict = r.get("facets", {})
        rows.append({
            "paper_id": r["paper_id"],
            "problem": f_dict.get("problem", []),
            "task": f_dict.get("task", []),
            "method": f_dict.get("method", []),
            "dataset": f_dict.get("dataset", []),
            "contribution": f_dict.get("contribution", []),
        })

    shared.base.write_jsonl(out_file, rows)

    # Xuất metadata tóm tắt
    summary = {
        "model_key": model_key,
        "base_model": MODEL_CONFIGS[model_key]["base_model"],
        "checkpoint": MODEL_CONFIGS[model_key]["selected_checkpoint"],
        "paper_count": len(rows),
        "facet_coverage": {
            f: sum(bool(r.get(f)) for r in rows) for f in FACET_KEYS
        },
        "output_file": str(out_file),
    }
    shared.base.write_json(output_dir / "summary.json", summary)
    return out_file


def run_facet_generation(
    input_path: Path,
    output_dir: Path,
    model_key: str = "Qwen8B",
    device: str = "auto",
    limit: Optional[int] = None,
    repo: Path = REPO_ROOT,
):
    """Thực thi pipeline trích xuất 5 facets cho danh sách bài báo."""
    adapter_path = find_adapter_dir(model_key, repo)
    if not adapter_path:
        raise FileNotFoundError(f"Không tìm thấy adapter cho mô hình {model_key} trong data/exp_a/final/adapter/")

    weights_file = adapter_path / "adapter_model.safetensors"
    if not weights_file.exists():
        print(f"[!] Cảnh báo: File trọng số {weights_file} chưa có trong {adapter_path}.")
        print("[!] Vui lòng đảm bảo đã tải và giải nén adapter từ Google Drive.")
        return

    m_cfg = MODEL_CONFIGS[model_key]
    print(f"[*] Bắt đầu trích xuất 5 Facets bằng mô hình: {model_key} ({m_cfg['base_model']})")
    print(f"[*] Thư mục Adapter: {adapter_path}")
    print(f"[*] Tệp đầu vào:     {input_path}")
    print(f"[*] Thư mục đầu ra:  {output_dir}")

    papers = read_input_papers(input_path)
    if limit is not None and limit > 0:
        papers = papers[:limit]
    print(f"[*] Số lượng bài báo cần trích xuất: {len(papers)} bài.")

    # Tự động nhận diện thiết bị chạy (CUDA hoặc CPU)
    use_cuda = False
    if device == "auto":
        try:
            import torch
            use_cuda = torch.cuda.is_available()
        except ImportError:
            use_cuda = False
    elif device.lower() == "cuda":
        use_cuda = True

    print(f"[*] Thiết bị suy luận: {'CUDA (GPU)' if use_cuda else 'CPU'}")

    # Đọc prompt & guideline từ bản đóng băng Exp A (Read-only)
    prompts_dir = repo / "data/exp_a/final/prompts"
    guideline_text = (prompts_dir / "guideline_gold_v1.md").read_text(encoding="utf-8")
    prompt_text = (prompts_dir / "extraction_gold_v1.md").read_text(encoding="utf-8")
    instruction = f"{guideline_text}\n\n{prompt_text}"

    # Nạp pipeline và runtime
    policy, shared = load_exp_a_runtime(repo)
    adapter_hash = sha256_file(weights_file)

    gen_config = {
        "model": m_cfg["base_model"],
        "revision": m_cfg["revision"],
        "adapter_path": str(adapter_path),
        "device": "cuda" if use_cuda else "cpu",
        "load_in_4bit": use_cuda,  # Chỉ bật 4-bit nếu có CUDA
        "do_sample": False,
        "temperature": 0.7,
        "max_new_tokens": 2048,
        "extraction_protocol": "two_pass_v3",
        "validator_policy": "source_attributed_paraphrase_v1",
        "threshold": 0.85,
    }

    records_dir = output_dir / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    records = []

    # Khởi tạo generator model
    print("[*] Đang khởi tạo mô hình và nạp trọng số Adapter...")
    decoder, runtime = shared.load_generator(gen_config)
    runtime.update(adapter_enabled=True, adapter_sha256=adapter_hash)

    print("[*] Đang thực thi V-recall 3-pass extraction...")
    for idx, paper in enumerate(papers, 1):
        pid = paper["paper_id"]
        cached_file = records_dir / f"{pid}.json"
        if cached_file.exists():
            with open(cached_file, "r", encoding="utf-8") as f:
                rec = json.load(f)
            print(f"[{idx}/{len(papers)}] {pid} (Đã có sẵn trong cache)")
        else:
            rec = policy.annotate_fresh(
                shared,
                paper,
                instruction,
                gen_config,
                runtime,
                decoder,
                output_dir,
                signature=f"conf_rec_{model_key}",
            )
            rec.update(paper_id=pid, model_key=model_key, adapter_enabled=True)
            with open(cached_file, "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=2)
            print(f"[{idx}/{len(papers)}] {pid} (Trích xuất xong, fallback={rec.get('fallback_used')})")

        records.append(rec)

    out_file = export_facets(shared, output_dir, papers, records, model_key)
    print(f"\n[+] HOÀN THÀNH! Đã xuất 5 facets của {len(records)} bài báo tại:")
    print(f"    👉 {out_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Trích xuất 5 Facets cho bài báo nhánh Khuyến nghị Hội nghị bằng Adapter Exp A."
    )
    parser.add_argument(
        "--model",
        choices=list(MODEL_CONFIGS.keys()),
        default="Qwen8B",
        help="Mô hình LLM cần sử dụng (mặc định: 'Qwen8B').",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Tệp JSONL chứa bài báo (mặc định: 186 bài test của nhánh Hội nghị).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Thư mục xuất file facets_silver.jsonl.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Giới hạn số lượng bài báo cần trích xuất (dùng cho dry-run / test nhanh).",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cuda", "cpu"],
        default="auto",
        help="Thiết bị thực thi (mặc định: 'auto').",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Kiểm tra cấu hình, adapter và tệp đầu vào mà không nạp model GPU.",
    )
    args = parser.parse_args()

    repo = REPO_ROOT
    default_input = (
        repo
        / "data/conference_recommendation_dataset/5_mapping_reviewed/splits/temporal_2015_2016_2019/test.jsonl"
    )
    input_path = args.input or default_input
    if not input_path.is_absolute():
        input_path = repo / input_path

    model_key = args.model
    default_output = (
        repo
        / f"data/conference_recommendation_dataset/generated_facets/{model_key}"
    )
    output_dir = args.output or default_output
    if not output_dir.is_absolute():
        output_dir = repo / output_dir

    if args.check:
        print("=" * 70)
        print("          KIỂM TRA CẤU HÌNH & TÍNH KHẢ THI (PREFLIGHT CHECK)")
        print("=" * 70)
        print(f"[*] Mô hình chọn:       {model_key} ({MODEL_CONFIGS[model_key]['base_model']})")
        print(f"[*] Checkpoint chọn:     {MODEL_CONFIGS[model_key]['selected_checkpoint']}")
        print(f"[*] Tệp đầu vào:         {input_path} (Tồn tại: {input_path.exists()})")
        if input_path.exists():
            papers = read_input_papers(input_path)
            print(f"    -> Đã đọc được {len(papers)} bài báo hợp lệ.")
        adapter_path = find_adapter_dir(model_key, repo)
        print(f"[*] Thư mục Adapter:     {adapter_path} (Tồn tại: {bool(adapter_path)})")
        if adapter_path:
            weights = adapter_path / "adapter_model.safetensors"
            print(f"    -> Trọng số safetensors: {weights.exists()} ({weights.stat().st_size:,} bytes)" if weights.exists() else "    -> Chưa có adapter_model.safetensors")
        print(f"[*] Thư mục đầu ra dự kiến: {output_dir}")
        print("=" * 70)
        return

    run_facet_generation(
        input_path=input_path,
        output_dir=output_dir,
        model_key=model_key,
        device=args.device,
        limit=args.limit,
        repo=repo,
    )


if __name__ == "__main__":
    main()
