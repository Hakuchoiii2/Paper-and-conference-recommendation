from __future__ import annotations

import gc
import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv
    _demo_env = Path(__file__).resolve().parent.parent / ".env"
    if _demo_env.exists():
        load_dotenv(_demo_env)
    else:
        load_dotenv()
except ImportError:
    pass

from schemas import EvidenceSpan, FacetConcept, FacetKey, FacetOutput

logger = logging.getLogger("demo.model_runner")

FACETS: List[FacetKey] = ["problem", "task", "method", "dataset", "contribution"]


@dataclass
class ModelSpec:
    model_key: str
    display_name: str
    family: str
    parameter_size: str
    base_model_name: str
    adapter_rel_path: str
    min_vram_gb: int
    local_supported: bool
    notes: str


MODEL_REGISTRY: Dict[str, ModelSpec] = {
    "Qwen3-4B": ModelSpec(
        model_key="Qwen3-4B",
        display_name="Qwen3-4B-Instruct",
        family="Qwen3",
        parameter_size="4B",
        base_model_name=os.getenv("BASE_MODEL_QWEN4B", "Qwen/Qwen3-4B"),
        adapter_rel_path="Qwen4B",
        min_vram_gb=4,
        local_supported=True,
        notes="Chạy mượt trên GPU RTX 3050 Laptop 4GB VRAM với 4-bit quantization.",
    ),
    "Qwen3-8B": ModelSpec(
        model_key="Qwen3-8B",
        display_name="Qwen3-8B-Instruct",
        family="Qwen3",
        parameter_size="8B",
        base_model_name=os.getenv("BASE_MODEL_QWEN8B", "Qwen/Qwen3-8B"),
        adapter_rel_path="Qwen8B",
        min_vram_gb=8,
        local_supported=False,
        notes="Yêu cầu tối thiểu 8GB VRAM; khuyến nghị chạy trên Kaggle GPU T4 hoặc dùng kết quả tính trước.",
    ),
    "Qwen3-14B": ModelSpec(
        model_key="Qwen3-14B",
        display_name="Qwen3-14B-Instruct",
        family="Qwen3",
        parameter_size="14B",
        base_model_name=os.getenv("BASE_MODEL_QWEN14B", "Qwen/Qwen3-14B"),
        adapter_rel_path="Qwen14B",
        min_vram_gb=16,
        local_supported=False,
        notes="Yêu cầu 16GB VRAM (Kaggle Dual-T4); không hỗ trợ chạy trực tiếp trên GPU 4GB.",
    ),
    "Llama3.1-8B": ModelSpec(
        model_key="Llama3.1-8B",
        display_name="Llama-3.1-8B-Instruct",
        family="Llama 3.1",
        parameter_size="8B",
        base_model_name=os.getenv("BASE_MODEL_LLAMA8B", "meta-llama/Meta-Llama-3.1-8B-Instruct"),
        adapter_rel_path="Llama8B",
        min_vram_gb=8,
        local_supported=False,
        notes="Yêu cầu tối thiểu 8GB VRAM và HF_TOKEN có quyền truy cập Meta-Llama.",
    ),
    "Gemma2-9B": ModelSpec(
        model_key="Gemma2-9B",
        display_name="Gemma-2-9B-IT",
        family="Gemma 2",
        parameter_size="9B",
        base_model_name=os.getenv("BASE_MODEL_GEMMA9B", "google/gemma-2-9b-it"),
        adapter_rel_path="Gemma9B",
        min_vram_gb=9,
        local_supported=False,
        notes="Yêu cầu tối thiểu 9GB VRAM; khuyến nghị chạy trên Kaggle GPU.",
    ),
}


def python_idx_to_utf16_offset(text: str, py_idx: int) -> int:
    return len(text[:py_idx].encode("utf-16-le")) // 2


def make_evidence_span(text: str, quote: str, source_field: str) -> EvidenceSpan:
    idx = text.find(quote)
    if idx == -1:
        return EvidenceSpan(
            quote=quote,
            source_field=source_field,  # type: ignore[arg-type]
            start_offset=None,
            end_offset=None,
            verified=False,
        )
    start_u16 = python_idx_to_utf16_offset(text, idx)
    end_u16 = python_idx_to_utf16_offset(text, idx + len(quote))
    return EvidenceSpan(
        quote=quote,
        source_field=source_field,  # type: ignore[arg-type]
        start_offset=start_u16,
        end_offset=end_u16,
        verified=True,
    )


class ModelRunnerManager:
    """Quản lý nạp và chạy inference cho các LLM Extractor (Local & Kaggle)."""

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self.repo_root = repo_root or self._detect_repo_root()
        self.enable_real_llm = os.getenv("ENABLE_REAL_LLM", "false").lower() in ("true", "1", "yes")
        self.device = os.getenv("DEVICE", "cuda")
        self.load_in_4bit = os.getenv("LOAD_IN_4BIT", "true").lower() in ("true", "1", "yes")
        self.adapter_root = self._resolve_adapter_root()

        self.loaded_model_key: Optional[str] = None
        self.model = None
        self.tokenizer = None

        # Multi-GPU LRU Resident Pool: model_key -> (peft_model, tokenizer, gpu_id)
        # Front = Least Recently Used (LRU), Back = Most Recently Used (MRU)
        self._model_pool: "OrderedDict[str, Tuple[Any, Any, int]]" = OrderedDict()
        self._pool_meta_lock = threading.Lock()
        # Per-GPU lock: đảm bảo tại 1 thời điểm trên 1 GPU chỉ có tối đa 1 tác vụ (nạp HOẶC suy luận).
        # Khi 1 GPU đang nạp model, tuyệt đối cấm nạp thêm hoặc chạy suy luận trên chính GPU đó.
        self._gpu_locks: Dict[int, threading.Lock] = {}
        self._loading_gpus: Dict[int, str] = {}
        self._inferencing_gpus: Dict[int, str] = {}
        self._gpu_map: Dict[str, int] = {
            "Qwen3-4B": 0,
            "Qwen3-8B": 0,
            "Llama3.1-8B": 1,
            "Gemma2-9B": 1,
            "Qwen3-14B": 1,
        }
        for _pair in os.getenv("KAGGLE_GPU_MAP", "").split(","):
            if ":" in _pair:
                _k, _v = _pair.split(":", 1)
                try:
                    self._gpu_map[_k.strip()] = int(_v.strip())
                except ValueError:
                    pass

        logger.info(
            f"ModelRunnerManager initialized. enable_real_llm={self.enable_real_llm}, "
            f"device={self.device}, adapter_root={self.adapter_root}"
        )

    def _get_gpu_lock(self, gpu_id: int) -> threading.Lock:
        with self._pool_meta_lock:
            lock = self._gpu_locks.get(gpu_id)
            if lock is None:
                lock = threading.Lock()
                self._gpu_locks[gpu_id] = lock
            return lock

    def get_model_gpu(self, model_key: str) -> int:
        """Trả về gpu_id mà model này đang thường trú hoặc sẽ được gán lên."""
        with self._pool_meta_lock:
            if model_key in self._model_pool:
                return self._model_pool[model_key][2]
        if self.device != "cuda":
            return 0
        try:
            import torch
            if torch.cuda.is_available():
                num_gpus = torch.cuda.device_count()
                if num_gpus <= 1:
                    return 0
                return min(self._gpu_map.get(model_key, 0), num_gpus - 1)
        except Exception:
            pass
        return 0

    def get_loading_model_on_gpu(self, gpu_id: int) -> Optional[str]:
        with self._pool_meta_lock:
            return self._loading_gpus.get(gpu_id)

    def get_gpu_busy_reason(self, gpu_id: int) -> Optional[str]:
        """Nếu GPU đang bận nạp hoặc suy luận, trả về mô tả lý do; ngược lại trả về None."""
        with self._pool_meta_lock:
            if gpu_id in self._loading_gpus:
                return f"đang nạp model {self._loading_gpus[gpu_id]}"
            if gpu_id in self._inferencing_gpus:
                return f"đang suy luận bằng {self._inferencing_gpus[gpu_id]}"
        return None

    def get_resident_models(self) -> Dict[str, int]:
        """Trả về dict {model_key: gpu_id} của các model đang thường trú trong VRAM."""
        with self._pool_meta_lock:
            return {k: gid for k, (_, _, gid) in self._model_pool.items()}

    def _detect_repo_root(self) -> Path:
        here = Path(__file__).resolve()
        for p in [here.parent, *here.parents]:
            if (p / "paper-and-conference-recommendation-experiments").exists():
                return p
            if (p / "_local" / "adapter").exists():
                return p
        return here.parent.parent

    def _resolve_adapter_root(self) -> Path:
        env_root = os.getenv("ADAPTER_ROOT")
        if env_root:
            p = Path(env_root)
            if not p.is_absolute():
                demo_dir = Path(__file__).resolve().parent.parent
                backend_dir = Path(__file__).resolve().parent
                for base in [demo_dir, backend_dir, self.repo_root]:
                    cand = (base / p).resolve()
                    if cand.exists():
                        return cand
            elif p.exists():
                return p
        # Default fallback
        cand = self.repo_root / "_local" / "adapter"
        if cand.exists():
            return cand
        return Path(__file__).parent / ".." / ".." / "_local" / "adapter"

    def get_adapter_path(self, model_key: str) -> Optional[Path]:
        spec = MODEL_REGISTRY.get(model_key)
        if not spec:
            return None
        cand = self.adapter_root / spec.adapter_rel_path
        if cand.exists():
            return cand
        return None

    def is_local_runnable(self, model_key: str) -> Tuple[bool, str]:
        spec = MODEL_REGISTRY.get(model_key)
        if not spec:
            return False, f"Model {model_key} không có trong danh mục hỗ trợ."

        adapter_path = self.get_adapter_path(model_key)
        if not adapter_path:
            return (
                False,
                f"Chưa tìm thấy LoRA adapter tại {self.adapter_root / spec.adapter_rel_path} "
                "(chế độ Mẫu có sẵn vẫn hỗ trợ đầy đủ 168 bài Test).",
            )

        if not self.enable_real_llm:
            return True, f"Chế độ CPU heuristic sẵn sàng (Adapter: {adapter_path.name})."

        # Kiểm tra tổng VRAM thực tế trên tất cả GPU CUDA (hỗ trợ cả single-GPU lẫn Kaggle Dual-T4)
        total_vram_gb = 0.0
        gpu_count = 0
        has_cuda = False
        try:
            import torch
            if torch.cuda.is_available():
                has_cuda = True
                gpu_count = torch.cuda.device_count()
                total_vram_gb = sum(
                    torch.cuda.get_device_properties(i).total_memory for i in range(gpu_count)
                ) / (1024**3)
        except Exception:
            pass

        if has_cuda and total_vram_gb >= (spec.min_vram_gb - 0.5):
            gpu_label = f"{gpu_count}x GPU, tổng {total_vram_gb:.1f}GB VRAM" if gpu_count > 1 else f"GPU {total_vram_gb:.1f}GB VRAM"
            return True, f"Sẵn sàng trên {gpu_label} (Adapter: {adapter_path.name})."

        if has_cuda:
            return (
                False,
                f"GPU hiện có {total_vram_gb:.1f}GB VRAM, cần tối thiểu {spec.min_vram_gb}GB để chạy "
                f"{spec.display_name} trực tiếp (chế độ Mẫu có sẵn vẫn hỗ trợ đầy đủ 168 bài Test).",
            )

        if spec.local_supported:
            return True, spec.notes

        return (
            False,
            f"Không phát hiện GPU CUDA đủ {spec.min_vram_gb}GB VRAM cho {spec.display_name} "
            "(chế độ Mẫu có sẵn vẫn hỗ trợ đầy đủ 168 bài Test).",
        )

    def _resolve_base_model_name(self, spec: ModelSpec) -> str:
        name = spec.base_model_name
        cand = Path(name)
        if not cand.is_absolute():
            demo_dir = Path(__file__).resolve().parent.parent
            backend_dir = Path(__file__).resolve().parent
            for base in [demo_dir, backend_dir, self.repo_root]:
                target = (base / cand).resolve()
                if target.exists():
                    return str(target)
        elif cand.exists():
            return str(cand)

        if spec.model_key == "Qwen3-4B":
            local_snap = (
                self.repo_root
                / "models"
                / "huggingface"
                / "models--Qwen--Qwen3-4B-Instruct-2507"
                / "snapshots"
                / "cdbee75f17c01a7cc42f958dc650907174af0554"
            )
            if local_snap.exists():
                return str(local_snap)
        return name

    def _release_model_vram(self, model_obj: Any, tokenizer_obj: Any, gpu_id: int) -> None:
        """Giải phóng triệt để VRAM của model 4-bit / PEFT + accelerate hooks trên đúng gpu_id."""
        if model_obj is not None:
            try:
                from accelerate.hooks import remove_hook_from_module
                remove_hook_from_module(model_obj, recurse=True)
            except Exception:
                pass
            try:
                for mod in model_obj.modules():
                    for attr in ("_hf_hook", "_old_forward"):
                        if hasattr(mod, attr):
                            try:
                                delattr(mod, attr)
                            except Exception:
                                pass
                    if hasattr(mod, "_parameters") and isinstance(mod._parameters, dict):
                        for k in list(mod._parameters.keys()):
                            mod._parameters[k] = None
                    if hasattr(mod, "_buffers") and isinstance(mod._buffers, dict):
                        for k in list(mod._buffers.keys()):
                            mod._buffers[k] = None
            except Exception:
                pass
        del model_obj, tokenizer_obj
        gc.collect()
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                with torch.cuda.device(gpu_id):
                    torch.cuda.synchronize(gpu_id)
                    torch.cuda.empty_cache()
                    if hasattr(torch.cuda, "ipc_collect"):
                        torch.cuda.ipc_collect()
        except Exception:
            pass

    def _evict_gpu_if_needed(self, gpu_id: int, need_gb: float) -> None:
        """Giải phóng dần model ít dùng nhất (LRU) trên đúng gpu_id nếu VRAM trống không đủ."""
        import torch
        if not torch.cuda.is_available():
            return
        # Xả cache block PyTorch chưa dùng trước khi đo mem_get_info để tránh đuổi oan model đang thường trú
        with torch.cuda.device(gpu_id):
            torch.cuda.empty_cache()
        while True:
            free_bytes, _ = torch.cuda.mem_get_info(gpu_id)
            free_gb = free_bytes / (1024**3)
            if free_gb >= need_gb:
                return
            with self._pool_meta_lock:
                # OrderedDict: phần tử đầu tiên khớp gpu_id chính là model lâu chưa dùng nhất (LRU)
                victims = [k for k, (_, _, gid) in self._model_pool.items() if gid == gpu_id]
                if not victims:
                    return
                victim_key = victims[0]
                m_old, t_old, _ = self._model_pool.pop(victim_key)
                if self.loaded_model_key == victim_key:
                    self.model = None
                    self.tokenizer = None
                    self.loaded_model_key = None

            logger.info(
                f"[GPU {gpu_id}] Trống {free_gb:.1f}GB < cần ~{need_gb:.1f}GB -> giải phóng LRU: {victim_key}"
            )
            print(
                f"[GPU {gpu_id}] Trống {free_gb:.1f}GB < cần ~{need_gb:.1f}GB -> giải phóng LRU: {victim_key}",
                flush=True,
            )
            self._release_model_vram(m_old, t_old, gpu_id)
            del m_old, t_old
            after_bytes, _ = torch.cuda.mem_get_info(gpu_id)
            after_gb = after_bytes / (1024**3)
            print(
                f"[GPU {gpu_id}] Sau khi giải phóng {victim_key}: trống {after_gb:.1f}GB",
                flush=True,
            )

    def unload_current_model(self) -> None:
        m_old = None
        t_old = None
        gid = 0
        with self._pool_meta_lock:
            if self.loaded_model_key and self.loaded_model_key in self._model_pool:
                m_old, t_old, gid = self._model_pool.pop(self.loaded_model_key)
            if self.model is not None:
                if m_old is None:
                    m_old = self.model
                self.model = None
            if self.tokenizer is not None:
                if t_old is None:
                    t_old = self.tokenizer
                self.tokenizer = None
            self.loaded_model_key = None
        self._release_model_vram(m_old, t_old, gid)

    def load_model(self, model_key: str) -> None:
        """Nạp model và adapter vào bộ nhớ (hỗ trợ Multi-GPU LRU Resident Pool + khóa từng GPU)."""
        spec = MODEL_REGISTRY.get(model_key)
        if not spec:
            raise ValueError(f"Model không xác định: {model_key}")

        # Kiểm tra nếu chỉ chạy ở chế độ giả lập (fast test UI)
        if not self.enable_real_llm:
            logger.info(f"[Mock Mode] Kích hoạt giả lập thành công cho model {model_key}.")
            self.loaded_model_key = model_key
            return

        # Kiểm tra phần cứng local
        can_run, reason = self.is_local_runnable(model_key)
        if not can_run and self.device == "cuda":
            raise ValueError(
                f"Không thể nạp {model_key} trên máy cục bộ: {reason}"
            )

        adapter_path = self.get_adapter_path(model_key)
        if not adapter_path:
            raise FileNotFoundError(
                f"Không tìm thấy thư mục adapter cho {model_key} tại {self.adapter_root / spec.adapter_rel_path}"
            )

        gpu_id = self.get_model_gpu(model_key)
        gpu_lock = self._get_gpu_lock(gpu_id)
        if not gpu_lock.acquire(blocking=False):
            busy_reason = self.get_gpu_busy_reason(gpu_id) or "đang bận tác vụ khác"
            raise RuntimeError(
                f"GPU {gpu_id} hiện {busy_reason}. Không thể nạp hoặc chuyển sang {model_key} trên GPU {gpu_id} lúc này — vui lòng đợi hoàn tất."
            )

        base_model = None
        peft_model = None
        tok = None
        try:
            # 1. Pool HIT -> chuyển đổi 0 giây và cập nhật MRU (an toàn vì đang giữ gpu_lock)
            with self._pool_meta_lock:
                if model_key in self._model_pool:
                    self._model_pool.move_to_end(model_key)
                    m_cached, t_cached, gid = self._model_pool[model_key]
                    self.model = m_cached
                    self.tokenizer = t_cached
                    self.loaded_model_key = model_key
                    print(
                        f"⚡ [Pool HIT] Chuyển nhanh sang {model_key} trên GPU {gid} trong 0.0s (đã nạp sẵn trong VRAM)!",
                        flush=True,
                    )
                    return
                self._loading_gpus[gpu_id] = model_key

            import inspect
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            from peft import LoraConfig, PeftModel

            num_gpus = torch.cuda.device_count() if (self.device == "cuda" and torch.cuda.is_available()) else 0
            if num_gpus > 0:
                est_vram = {
                    "Qwen3-4B": 3.4,
                    "Qwen3-8B": 5.8,
                    "Llama3.1-8B": 5.8,
                    "Gemma2-9B": 6.4,
                    "Qwen3-14B": 10.5,
                }.get(model_key, 6.5)
                self._evict_gpu_if_needed(gpu_id, est_vram)

            logger.info(f"Bắt đầu nạp LLM thật cho {model_key} -> GPU {gpu_id} từ {adapter_path}...")
            print(f"🚀 [START LOAD] {model_key} -> GPU {gpu_id} (adapter: {adapter_path})", flush=True)

            # Cấu hình lượng tử hóa 4-bit tiết kiệm VRAM
            bnb_config = None
            if self.load_in_4bit and self.device == "cuda":
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )

            hf_token = os.getenv("HF_TOKEN") or None
            resolved_base_model = self._resolve_base_model_name(spec)
            is_local_base = Path(resolved_base_model).exists()

            print(f"   [1/3] Đang nạp tokenizer ({resolved_base_model})...", flush=True)
            try:
                tok = AutoTokenizer.from_pretrained(
                    str(adapter_path),
                    trust_remote_code=True,
                    token=hf_token,
                )
            except Exception:
                tok = AutoTokenizer.from_pretrained(
                    resolved_base_model,
                    trust_remote_code=True,
                    token=None if is_local_base else hf_token,
                    local_files_only=is_local_base,
                )

            print(f"   [2/3] Đang nạp base model 4-bit: {resolved_base_model} lên GPU {gpu_id}...", flush=True)
            target_device_map = {"": gpu_id} if self.device == "cuda" else None
            base_model = AutoModelForCausalLM.from_pretrained(
                resolved_base_model,
                quantization_config=bnb_config,
                device_map=target_device_map,
                dtype=torch.float16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
                token=None if is_local_base else hf_token,
                local_files_only=is_local_base,
            )

            print(f"   [3/3] Đang gắn LoRA adapter: {adapter_path}...", flush=True)
            peft_config = None
            cfg_file = adapter_path / "adapter_config.json"
            if cfg_file.exists():
                raw_cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                valid_params = set(inspect.signature(LoraConfig.__init__).parameters.keys()) - {"self"}
                filtered_cfg = {k: v for k, v in raw_cfg.items() if k in valid_params}
                peft_config = LoraConfig(**filtered_cfg)
            peft_model = PeftModel.from_pretrained(base_model, str(adapter_path), config=peft_config)
            peft_model.eval()

            with self._pool_meta_lock:
                self._model_pool[model_key] = (peft_model, tok, gpu_id)
                self._model_pool.move_to_end(model_key)
                self.model = peft_model
                self.tokenizer = tok
                self.loaded_model_key = model_key
                loaded_list = [f"{k}@GPU{g}" for k, (_, _, g) in self._model_pool.items()]
            logger.info(f"Nạp model {model_key} thành công! Pool: {', '.join(loaded_list)}")
            print(
                f"✅ [READY] Đã nạp xong {model_key} lên GPU {gpu_id}! Đang thường trú: {', '.join(loaded_list)}",
                flush=True,
            )

        except ImportError as exc:
            logger.warning(f"Chưa cài đặt đủ thư viện deep learning ({exc}). Chuyển sang fallback heuristic.")
            self.loaded_model_key = model_key
        except Exception as exc:
            err_msg = str(exc)
            logger.error(f"Lỗi khi nạp model {model_key}: {err_msg}")
            print(f"❌ [LOAD FAILED] {model_key} trên GPU {gpu_id}: {err_msg}", flush=True)
            # Dọn sạch VRAM bị chiếm dở nếu OOM hoặc lỗi giữa chừng
            self._release_model_vram(peft_model if peft_model is not None else base_model, tok, gpu_id)
            peft_model = None
            base_model = None
            tok = None
            # Không chain traceback gốc (`from None`) để Python không giữ sống frame chứa tensor CUDA
            raise RuntimeError(f"Lỗi nạp mô hình {model_key}: {err_msg}") from None
        finally:
            with self._pool_meta_lock:
                self._loading_gpus.pop(gpu_id, None)
            gpu_lock.release()

    def extract_facets(self, title: str, abstract: str, model_key: str) -> Dict[FacetKey, FacetOutput]:
        """Thực hiện trích xuất 5 facet từ Title & Abstract (khóa theo GPU để không đụng độ khi nạp)."""
        # 1. Tách câu chuẩn hóa
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", abstract) if s.strip()]
        sentence_map: Dict[str, str] = {"T0": title}
        for i, s in enumerate(sentences):
            sentence_map[f"A{i}"] = s

        # 2. Nếu tắt real LLM trong .env (chế độ test UI không GPU), dùng heuristic
        if not self.enable_real_llm:
            return self._heuristic_fallback(title, abstract, sentences)

        # 3. Quy tắc bắt buộc: không được suy luận trên GPU đang nạp model, và không tự ý nạp lại trong lúc suy luận
        gpu_id = self.get_model_gpu(model_key)
        loading_mk = self.get_loading_model_on_gpu(gpu_id)
        if loading_mk:
            raise RuntimeError(
                f"GPU {gpu_id} đang nạp model {loading_mk}. Không được phép suy luận trên GPU {gpu_id} trong lúc đang nạp model — vui lòng đợi nạp xong."
            )

        gpu_lock = self._get_gpu_lock(gpu_id)
        if not gpu_lock.acquire(blocking=False):
            busy_reason = self.get_gpu_busy_reason(gpu_id) or "đang bận tác vụ khác"
            raise RuntimeError(
                f"GPU {gpu_id} hiện {busy_reason}. Vui lòng đợi tác vụ trên GPU {gpu_id} hoàn tất rồi thử lại."
            )

        try:
            with self._pool_meta_lock:
                entry = self._model_pool.get(model_key)
                if entry is None:
                    raise RuntimeError(
                        f"Model {model_key} chưa được nạp trong VRAM trên GPU {gpu_id}. Vui lòng mở ngăn 'Hệ thống' để nạp model trước khi phân tích."
                    )
                self._model_pool.move_to_end(model_key)
                model_obj, tok_obj, _ = entry
                self._inferencing_gpus[gpu_id] = model_key

            # 4. Chạy inference thật qua LLM trên GPU
            return self._run_llm_inference(model_obj, tok_obj, title, abstract, sentences, sentence_map)
        finally:
            with self._pool_meta_lock:
                self._inferencing_gpus.pop(gpu_id, None)
            gpu_lock.release()

    def _run_llm_inference(
        self,
        model_obj: Any,
        tokenizer_obj: Any,
        title: str,
        abstract: str,
        sentences: List[str],
        sentence_map: Dict[str, str],
    ) -> Dict[FacetKey, FacetOutput]:
        import torch

        # Soạn prompt input theo đúng định dạng train QLoRA (extraction_gold_v1.md)
        doc_lines = [f"T0: {title}"]
        for i, s in enumerate(sentences):
            doc_lines.append(f"A{i}: {s}")
        paper_text = "\n".join(doc_lines)

        system_prompt = self._load_system_prompt()
        user_content = (
            "paper_id: LIVE_QUERY\n"
            f"{paper_text}\n\n"
            "Return JSON only."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            text_input = tokenizer_obj.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except Exception:
            try:
                text_input = tokenizer_obj.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            except Exception:
                # Gemma-2-IT không hỗ trợ role "system" riêng -> gộp system prompt vào đầu user message
                merged_messages = [{"role": "user", "content": f"{system_prompt}\n\n{user_content}"}]
                text_input = tokenizer_obj.apply_chat_template(
                    merged_messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
        input_device = next(model_obj.parameters()).device
        model_inputs = tokenizer_obj([text_input], return_tensors="pt").to(input_device)

        try:
            with torch.inference_mode():
                generated_ids = model_obj.generate(
                    **model_inputs,
                    max_new_tokens=768,
                    do_sample=False,
                    use_cache=True,
                    pad_token_id=tokenizer_obj.eos_token_id,
                )

            generated_ids = [
                output_ids[len(input_ids):]
                for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            response_text = tokenizer_obj.batch_decode(generated_ids, skip_special_tokens=True)[0]
        finally:
            del model_inputs
            if torch.cuda.is_available():
                with torch.cuda.device(input_device):
                    torch.cuda.empty_cache()

        # Trích xuất JSON từ chuỗi kết quả
        return self._parse_llm_json(response_text, title, abstract, sentence_map)

    def _load_system_prompt(self) -> str:
        candidates = [
            self.repo_root
            / "paper-and-conference-recommendation-experiments"
            / "data"
            / "exp_a"
            / "final"
            / "prompts"
            / "extraction_gold_v1.md",
            self.repo_root / "data" / "exp_a" / "final" / "prompts" / "extraction_gold_v1.md",
        ]
        for p in candidates:
            if p.exists():
                return p.read_text(encoding="utf-8").strip()
        return (
            "Extract concepts from the supplied title and abstract only. "
            "Return JSON with paper_id, problem, task, method, dataset, contribution; "
            "each facet is a list of objects with exactly concept and evidence_id. "
            "T0 is the title and A0... are abstract sentences. Unsupported facets must be []. Return JSON only."
        )

    def _extract_json_object(self, raw_output: str) -> Dict[str, Any]:
        # 1. Remove <think>...</think> blocks if present
        cleaned = re.sub(r"<think>.*?</think>", "", raw_output, flags=re.DOTALL).strip()
        # 2. Strip markdown code fences
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        start = cleaned.find("{")
        if start == -1:
            raise ValueError(f"Không tìm thấy JSON hợp lệ trong phản hồi của model: {cleaned[:200]}")

        candidate = cleaned[start:]
        decoder = json.JSONDecoder()

        # Layer 1: Strict JSON decode
        try:
            obj, _ = decoder.raw_decode(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

        # Layer 2: Repair common 4B LLM JSON glitches (trailing commas, missing evidence_id key, truncation)
        repaired = re.sub(r",\s*([}\]])", r"\1", candidate)
        repaired = re.sub(
            r',\s*"((?:T0|A\d+))"\s*\}',
            r', "evidence_id": "\1"}',
            repaired,
        )
        try:
            obj, _ = decoder.raw_decode(repaired)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

        # Layer 3: Resilient per-facet extractor (handles unescaped quotes inside concepts or mid-JSON truncation)
        recovered = self._recover_facets_from_malformed_json(repaired)
        if any(recovered.get(f) for f in FACETS):
            logger.warning("Recovered facets from slightly malformed LLM JSON output.")
            return recovered

        logger.error(f"Raw LLM output failed JSON parse: {raw_output[:800]}")
        raise ValueError("Model trả về JSON không thể khôi phục được. Vui lòng thử lại.")

    def _recover_facets_from_malformed_json(self, text: str) -> Dict[str, List[Dict[str, str]]]:
        """Extract facet items safely even if a concept contains unescaped quotes or output was truncated."""
        recovered: Dict[str, List[Dict[str, str]]] = {f: [] for f in FACETS}
        facet_pattern = re.compile(r'"(problem|task|method|dataset|contribution)"\s*:\s*\[', re.IGNORECASE)
        matches = list(facet_pattern.finditer(text))
        for idx, m in enumerate(matches):
            facet_name = m.group(1).lower()
            seg_start = m.end()
            seg_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            segment = text[seg_start:seg_end]

            # Match {"concept": "...", "evidence_id": "A0"} cleanly without leaking JSON fragments
            item_matches = re.findall(
                r'\{\s*"concept"\s*:\s*"([^"\n\r]+?)"\s*,\s*(?:"evidence_id"\s*:\s*)?"(T0|A\d+)"\s*\}',
                segment,
            )
            if item_matches:
                for concept, ev_id in item_matches:
                    c_clean = re.split(r'"\s*,\s*"?evidence', concept, maxsplit=1)[0].replace('\\"', '"').strip()
                    if c_clean:
                        recovered[facet_name].append({"concept": c_clean, "evidence_id": ev_id})
            else:
                # Fallback: match {"concept": "..."} without evidence_id
                c_only = re.findall(r'"concept"\s*:\s*"([^"\n\r]+)"', segment)
                for c in c_only:
                    c_clean = re.split(r'"\s*,\s*"?evidence', c, maxsplit=1)[0].strip()
                    if c_clean:
                        recovered[facet_name].append({"concept": c_clean, "evidence_id": ""})
        return recovered

    def _parse_llm_json(
        self,
        raw_output: str,
        title: str,
        abstract: str,
        sentence_map: Dict[str, str],
    ) -> Dict[FacetKey, FacetOutput]:
        parsed = self._extract_json_object(raw_output)
        result: Dict[FacetKey, FacetOutput] = {}

        for f in FACETS:
            items_raw = parsed.get(f, [])
            facet_concepts: List[FacetConcept] = []
            if isinstance(items_raw, list):
                for item in items_raw:
                    if isinstance(item, str):
                        concept = item.strip()
                        ev_id = ""
                    elif isinstance(item, dict):
                        concept = str(item.get("concept", "")).strip()
                        ev_id = str(item.get("evidence_id", "")).strip()
                    else:
                        continue
                    if not concept:
                        continue

                    # Tìm câu trích dẫn dựa trên evidence_id (T0, A0, A1...)
                    quote = sentence_map.get(ev_id, "")
                    source_field = "title" if ev_id == "T0" else "abstract"
                    evidence_span = make_evidence_span(
                        title if source_field == "title" else abstract,
                        quote,
                        source_field,
                    )
                    facet_concepts.append(
                        FacetConcept(
                            concept=concept,
                            evidences=[evidence_span] if quote else [],
                        )
                    )

            result[f] = FacetOutput(
                status="ok" if facet_concepts else "empty",
                items=facet_concepts,
            )

        return result

    def _heuristic_fallback(
        self,
        title: str,
        abstract: str,
        sentences: List[str],
    ) -> Dict[FacetKey, FacetOutput]:
        s0 = sentences[0] if sentences else abstract[:140]
        s1 = sentences[1] if len(sentences) > 1 else ""
        s_last = sentences[-1] if len(sentences) > 2 else ""

        return {
            "problem": FacetOutput(
                status="ok",
                items=[
                    FacetConcept(
                        concept=f"Problem addressed in {title[:60]}",
                        evidences=[make_evidence_span(abstract, s0, "abstract")],
                    )
                ],
            ),
            "task": FacetOutput(
                status="ok",
                items=[
                    FacetConcept(
                        concept=title,
                        evidences=[make_evidence_span(title, title, "title")],
                    )
                ],
            ),
            "method": FacetOutput(
                status="ok" if s1 else "empty",
                items=(
                    [
                        FacetConcept(
                            concept="Methodology described in abstract",
                            evidences=[make_evidence_span(abstract, s1, "abstract")],
                        )
                    ]
                    if s1
                    else []
                ),
            ),
            "dataset": FacetOutput(status="empty", items=[]),
            "contribution": FacetOutput(
                status="ok" if s_last else "empty",
                items=(
                    [
                        FacetConcept(
                            concept="Primary findings and contributions",
                            evidences=[make_evidence_span(abstract, s_last, "abstract")],
                        )
                    ]
                    if s_last
                    else []
                ),
            ),
        }
