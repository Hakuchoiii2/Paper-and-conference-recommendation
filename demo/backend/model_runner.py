from __future__ import annotations

import gc
import json
import logging
import os
import re
import time
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

        logger.info(
            f"ModelRunnerManager initialized. enable_real_llm={self.enable_real_llm}, "
            f"device={self.device}, adapter_root={self.adapter_root}"
        )

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
            return False, f"Chưa tìm thấy adapter tại {self.adapter_root / spec.adapter_rel_path}"

        # Kiểm tra VRAM thực tế nếu có GPU CUDA
        vram_gb = 4.0
        has_cuda = False
        try:
            import torch
            if torch.cuda.is_available():
                has_cuda = True
                props = torch.cuda.get_device_properties(0)
                vram_gb = props.total_memory / (1024**3)
        except Exception:
            pass

        if has_cuda and vram_gb >= (spec.min_vram_gb - 0.5):
            return True, f"GPU có {vram_gb:.1f}GB VRAM, đủ điều kiện chạy mô hình {spec.display_name}."

        if spec.local_supported:
            return True, spec.notes

        return (
            False,
            f"Model {spec.display_name} yêu cầu tối thiểu {spec.min_vram_gb}GB VRAM (GPU hiện có {vram_gb:.1f}GB). {spec.notes}",
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

    def unload_current_model(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        self.loaded_model_key = None
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def load_model(self, model_key: str) -> None:
        """Nạp model và adapter vào bộ nhớ."""
        if self.loaded_model_key == model_key and self.model is not None:
            logger.info(f"Model {model_key} đã sẵn sàng trong bộ nhớ.")
            return

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

        logger.info(f"Bắt đầu nạp LLM thật cho {model_key} từ {adapter_path}...")
        self.unload_current_model()

        try:
            import inspect
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            from peft import LoraConfig, PeftModel

            # Cấu hình lượng tử hóa 4-bit tiết kiệm VRAM
            bnb_config = None
            if self.load_in_4bit and self.device == "cuda":
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )

            logger.info(f"Loading tokenizer: {adapter_path} (or base {spec.base_model_name})...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(adapter_path),
                trust_remote_code=True,
            )

            resolved_base_model = self._resolve_base_model_name(spec)
            logger.info(f"Loading base model: {resolved_base_model}...")
            # Ghim toàn bộ lớp 4-bit lên GPU 0 để tránh accelerate tự đẩy bớt lớp sang CPU RAM
            target_device_map = {"": 0} if (self.device == "cuda" and self.load_in_4bit) else (
                "auto" if self.device == "cuda" else None
            )
            base_model = AutoModelForCausalLM.from_pretrained(
                resolved_base_model,
                quantization_config=bnb_config,
                device_map=target_device_map,
                dtype=torch.float16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
            )

            logger.info(f"Loading PEFT LoRA adapter: {adapter_path}...")
            peft_config = None
            cfg_file = adapter_path / "adapter_config.json"
            if cfg_file.exists():
                raw_cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                valid_params = set(inspect.signature(LoraConfig.__init__).parameters.keys()) - {"self"}
                filtered_cfg = {k: v for k, v in raw_cfg.items() if k in valid_params}
                peft_config = LoraConfig(**filtered_cfg)
            self.model = PeftModel.from_pretrained(base_model, str(adapter_path), config=peft_config)
            self.model.eval()
            self.loaded_model_key = model_key
            logger.info(f"Nạp model {model_key} thành công!")

        except ImportError as exc:
            logger.warning(f"Chưa cài đặt đủ thư viện deep learning ({exc}). Chuyển sang fallback heuristic.")
            self.loaded_model_key = model_key
        except Exception as exc:
            logger.error(f"Lỗi khi nạp model {model_key}: {exc}")
            self.unload_current_model()
            raise RuntimeError(f"Lỗi nạp mô hình {model_key}: {str(exc)}") from exc

    def extract_facets(self, title: str, abstract: str, model_key: str) -> Dict[FacetKey, FacetOutput]:
        """Thực hiện trích xuất 5 facet từ Title & Abstract."""
        # 1. Tách câu chuẩn hóa
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", abstract) if s.strip()]
        sentence_map: Dict[str, str] = {"T0": title}
        for i, s in enumerate(sentences):
            sentence_map[f"A{i}"] = s

        # 2. Nếu tắt real LLM trong .env (chế độ test UI không GPU), dùng heuristic
        if not self.enable_real_llm:
            return self._heuristic_fallback(title, abstract, sentences)

        # 3. Đảm bảo model đã nạp lên GPU trước khi chạy inference thật
        if self.model is None or self.tokenizer is None or self.loaded_model_key != model_key:
            self.load_model(model_key)

        # 4. Chạy inference thật qua LLM trên GPU
        return self._run_llm_inference(title, abstract, sentences, sentence_map)

    def _run_llm_inference(
        self,
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
            text_input = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            text_input = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        model_inputs = self.tokenizer([text_input], return_tensors="pt").to(self.device)

        try:
            with torch.inference_mode():
                generated_ids = self.model.generate(
                    **model_inputs,
                    max_new_tokens=768,
                    do_sample=False,
                    use_cache=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                )

            generated_ids = [
                output_ids[len(input_ids):]
                for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            response_text = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        finally:
            del model_inputs
            if torch.cuda.is_available():
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

            # Match {"concept": "...", "evidence_id": "A0"} even if concept has unescaped inner quotes
            item_matches = re.findall(
                r'\{\s*"concept"\s*:\s*"(.*?)"\s*,\s*(?:"evidence_id"\s*:\s*)?"(T0|A\d+)"\s*\}',
                segment,
                flags=re.DOTALL,
            )
            if item_matches:
                for concept, ev_id in item_matches:
                    c_clean = concept.replace('\\"', '"').strip()
                    if c_clean:
                        recovered[facet_name].append({"concept": c_clean, "evidence_id": ev_id})
            else:
                # Fallback: match {"concept": "..."} without evidence_id
                c_only = re.findall(r'"concept"\s*:\s*"([^"]+)"', segment)
                for c in c_only:
                    c_clean = c.strip()
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
