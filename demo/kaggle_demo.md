# Chiến lược & Ý tưởng Tối ưu Demo DS300 FacetRec trên Kaggle (GPU T4 x2)

Tài liệu này tổng hợp:
1. Kiểm chứng cơ chế nạp model cục bộ / từ Kaggle Dataset để **không bị lỗi**.
2. Cách đóng gói trọng số model thành **Kaggle Dataset** để import nhanh (giống cách gắn dataset `adapter` sẵn).
3. Phân tích bài toán VRAM trên **Kaggle GPU T4 x2 (15GB × 2 = 30GB VRAM + 30GB System RAM)** và các ý tưởng tận dụng tối đa 2 GPU.

---

## 1. Suy luận: Đặt model đúng vị trí thì có chạy không lỗi không?

**Có — sẽ chạy trơn tru và KHÔNG cần tải lại từ Internet**, miễn là thỏa mãn đủ **4 điều kiện** sau:

1. **Trỏ đúng thư mục Snapshot phẳng (có `config.json` nằm trực tiếp bên trong):**
   - Trong `model_runner.py`, hàm `_resolve_base_model_name()` đọc biến môi trường `BASE_MODEL_QWEN4B`, `BASE_MODEL_QWEN8B`, `BASE_MODEL_QWEN14B`, `BASE_MODEL_LLAMA8B`, `BASE_MODEL_GEMMA9B`.
   - Khi biến môi trường là một đường dẫn thư mục tồn tại trên đĩa (ví dụ `/kaggle/input/qwen3-4b-weights/`), `transformers` sẽ nạp thẳng từ đĩa và **bỏ qua hoàn toàn bước kiểm tra `HF_TOKEN`** (kể cả với `Llama-3.1-8B` và `Gemma-2-9B` vốn là gated model trên Hugging Face).
   - **Lưu ý bẫy hay gặp:** Nếu bạn upload cả thư mục cache Hugging Face (`hub/models--Qwen--Qwen3-4B/snapshots/<hash>/...`), bạn phải trỏ sâu vào tới đúng thư mục `<hash>` (nơi chứa `config.json` và `*.safetensors`), **không** trỏ vào thư mục `hub/` vì `/kaggle/input` là **read-only** — `huggingface_hub` sẽ báo lỗi quyền ghi khi cố tạo file `.lock` trong `/kaggle/input`.

2. **Đủ LoRA Adapter tương ứng trong `ADAPTER_ROOT`:**
   - Thư mục `ADAPTER_ROOT` cần có các thư mục con `Qwen4B`, `Qwen8B`, `Qwen14B`, `Llama8B`, `Gemma9B`, mỗi thư mục chứa `adapter_config.json` và `adapter_model.safetensors`.

3. **Đủ GPU VRAM thực tế:**
   - Backend hiện đã bỏ hard-code và tự kiểm tra tổng VRAM qua `ModelRunnerManager.is_local_runnable()`.
   - Máy local 4GB chỉ mở khóa `Qwen3-4B`; Kaggle T4 (15GB) mở khóa tới 8B–9B; Kaggle **T4 x2 (30GB)** tự động mở khóa **5/5 model**.

4. **Embedding model (`bert-base-uncased`):**
   - Code hiện dùng `BERT_MODEL_PATH` (không còn dùng BGE-small). Có thể gói luôn thư mục `bert-base-uncased` (~440MB) vào Dataset để khởi động offline 100%.

---

## 2. Ý tưởng lưu trọng số Model thành Kaggle Dataset (Không phải tải lại mỗi phiên)

Thay vì mỗi lần mở Kaggle phải đợi tải 15–35GB từ Hugging Face vào `/tmp/hf_cache` (tốn 5–10 phút và dễ đầy ổ `/tmp`), bạn tạo Dataset 1 lần duy nhất:

### Cấu trúc Dataset khuyến nghị (Snapshot phẳng — sạch & nhanh nhất)
Bạn có thể tạo 1 Dataset lớn (hoặc tách mỗi model 1 Dataset để dễ gắn/gỡ theo nhu cầu):

```text
/kaggle/input/ds300-base-models/
├── Qwen3-4B/                # chứa config.json, model-*.safetensors, tokenizer.json...
├── Qwen3-8B/                # chứa config.json, model-*.safetensors, tokenizer.json...
├── Qwen3-14B/               # chứa config.json, model-*.safetensors, tokenizer.json...
├── Llama-3.1-8B-Instruct/   # chứa config.json, model-*.safetensors, tokenizer.json...
├── Gemma-2-9B-IT/           # chứa config.json, model-*.safetensors, tokenizer.json...
└── bert-base-uncased/       # chứa modules.json, config.json, model.safetensors...
```

### Lợi ích
- **Khởi động cực nhanh:** Không tốn băng thông mạng, không cần `HF_TOKEN` cho Llama/Gemma khi demo.
- **Không tốn dung lượng `/tmp` (chỉ có ~19–57GB tùy phiên):** Toàn bộ trọng số nằm trên phân vùng `/kaggle/input` (read-only, không tính vào dung lượng `/tmp` hay `/kaggle/working`).
- **Tận dụng Kaggle Models có sẵn:** Với các model phổ biến (như `Qwen3`, `Llama-3.1`, `Gemma-2`), Kaggle Models đôi khi đã host sẵn — chỉ cần bấm **Add Input → Models** và trỏ `BASE_MODEL_OVERRIDES` trong `kaggle_run_demo.ipynb` vào đường dẫn `/kaggle/input/...` tương ứng.

---

## 3. Bài toán VRAM trên Kaggle T4 x2 (15GB × 2 = 30GB): Có load hết 5 model cùng lúc không?

### Bảng ước tính VRAM thực tế (lượng tử hóa 4-bit NF4 + LoRA + KV-Cache)

| Model | Tham số | VRAM 4-bit NF4 (Weights) | VRAM FP16 (Full/Half) | + KV-Cache khi sinh JSON (~1024 tok) |
|---|---|---|---|---|
| `Qwen3-4B` | 4B | ~3.0 GB | ~8.2 GB | +0.5 GB |
| `Qwen3-8B` | 8B | ~5.6 GB | ~16.2 GB | +0.8 GB |
| `Llama3.1-8B` | 8B | ~5.6 GB | ~16.2 GB | +0.8 GB |
| `Gemma2-9B` | 9B | ~6.4 GB | ~18.5 GB | +1.0 GB |
| `Qwen3-14B` | 14B | ~9.6 GB | ~28.5 GB | +1.2 GB |
| `BERT-base-uncased` | 110M | — | ~0.5 GB | ~0.1 GB |
| **Tổng 5 LLM (4-bit)** | — | **~30.2 GB** | **~87.6 GB** | **+1.5 GB (khi chạy)** |

### Kết luận & Phương án ĐÃ CHỐT (Đã tích hợp trực tiếp vào Backend, Frontend & Notebook)
- **Không nên load cả 5 model vào VRAM cùng lúc** trên T4 x2 (15GB × 2 = 30GB), vì tổng riêng weights 4-bit đã ~30.2GB, cộng thêm CUDA context (~0.5GB/GPU) và KV-Cache khi generate chắc chắn gây **OOM (Out of Memory)**.
- **Phương án đã chốt — 4 Model Thường Trú (Chuyển đổi 0 giây cho 4/5 model):**
  - **GPU 0 (15GB):** `Qwen3-4B` (~3.0GB) + `Qwen3-8B` (~5.6GB) + `BERT-base-uncased` (~0.5GB) ≈ **9.1 GB / 15 GB**.
  - **GPU 1 (15GB):** `Llama3.1-8B` (~5.6GB) + `Gemma2-9B` (~6.4GB) ≈ **12.0 GB / 15 GB**.
  - **Khi gọi `Qwen3-14B` (~9.6GB):** Backend tự động giải phóng model ít dùng nhất (**LRU**) trên **GPU 1** cho đến khi đủ VRAM trống rồi nạp `Qwen3-14B` — **GPU 0 (`Qwen3-4B` + `Qwen3-8B`) luôn giữ nguyên không bị ảnh hưởng**.
- **Hiển thị rõ ràng 3 trạng thái trong ngăn Hệ thống (`SystemDrawer`):**
  - 🟢 **`Đang dùng • GPU X`**: Model đang active hiện tại.
  - 🔵 **`Sẵn sàng (0s) • GPU X`**: Đã nạp sẵn trong VRAM, bấm nút **"Chuyển nhanh sang `<Model>` (0s)"** là đổi tức thì.
  - ⚪ **`Chưa nạp`**: Nằm ngoài VRAM, bấm nạp sẽ hiển thị thông báo rõ cơ chế tự giải phóng LRU trên GPU mục tiêu nếu cần.

*(Ghi chú: Nếu chưa có `HF_TOKEN` và chưa gắn Dataset cho Llama/Gemma, chỉ cần đổi `PRELOAD_MODELS = ["Qwen3-4B", "Qwen3-8B", "Qwen3-14B"]` ở Cell 1.)*

---

## 4. Các ý tưởng tận dụng tối đa GPU Kaggle T4 x2

### Ý tưởng 1: Multi-GPU Resident Pool + LRU Eviction (Chuyển đổi model 0 giây)
- Giữ sẵn 3–4 model phổ biến nhất trong `_model_pool` trên GPU 0 và GPU 1 (đã tích hợp sẵn trong `kaggle_run_demo.ipynb`).
- Khi người dùng chuyển qua lại giữa các model đang thường trú trên Web UI → **mất 0.0 giây** (chỉ đổi con trỏ `self.model`, không unload/reload).
- Khi người dùng bấm nạp model thứ 4 hoặc 5 chưa có trong pool → tự động giải phóng model ít dùng nhất (LRU) **trên đúng GPU đó** rồi nạp model mới, các model ở GPU còn lại vẫn giữ nguyên.

### Ý tưởng 2: Chế độ "Full FP16 Speed Boost" cho 1–2 model chủ lực (Tăng tốc độ sinh 2×–3×)
- **Bản chất phần cứng T4:** NVIDIA T4 có **Tensor Core FP16 rất nhanh**, trong khi `bitsandbytes` 4-bit NF4 phải giải nén (dequantize) từng lớp ngay lúc chạy nên tốc độ tokens/giây thường chậm hơn FP16 khoảng **2×–3×** (đặc biệt khi batch_size = 1).
- **Cách tận dụng T4 x2:**
  - **GPU 0 (15GB):** Nạp **`Qwen3-4B` ở chế độ FP16 thuần (`LOAD_IN_4BIT=false`, ~8.2GB VRAM)** → suy luận siêu nhanh (chỉ ~1.5–3 giây/bài báo thay vì 5–8 giây như 4-bit), dùng làm extractor mặc định cho luồng Tra cứu OpenAlex & Manuscript!
  - **GPU 1 (15GB):** Giữ **`Qwen3-14B` (4-bit, ~9.6GB)** hoặc **`Qwen3-8B` (4-bit, ~5.6GB)** để phục vụ khi người dùng cần đối chứng độ chính xác với model lớn.
- Có thể cấu hình theo từng model: `MODEL_PRECISION = {"Qwen3-4B": "fp16", "Qwen3-8B": "4bit", "Qwen3-14B": "4bit"}`.

### Ý tưởng 3: Chạy song song thật sự 2 GPU cho trang "So sánh extractor" (Giảm 50% thời gian)
- Hiện tại, tính năng **So sánh extractor** chạy tuần tự từng model một.
- Với T4 x2, khi người dùng so sánh 2 model nằm trên 2 GPU khác nhau (ví dụ `Qwen3-4B` ở GPU 0 vs `Qwen3-14B` hoặc `Llama3.1-8B` ở GPU 1):
  - Backend có thể dispatch 2 thread chạy **`model_a.generate()` trên GPU 0** và **`model_b.generate()` trên GPU 1 cùng lúc** (dùng `torch.cuda.device(gpu_id)`).
  - Thời gian so sánh 2 model giảm từ `T1 + T2` xuống chỉ còn `max(T1, T2)` (~giảm 40–50% thời gian chờ khi demo live!).

### Ý tưởng 4: Lưu bản Pre-quantized (AWQ / GPTQ / 4-bit) trong Kaggle Dataset
- Nếu lưu bản gốc FP16 của cả 5 model vào Kaggle Dataset, tổng dung lượng sẽ lên tới ~85GB.
- Nếu lượng tử hóa trước (ví dụ dùng bản `AWQ` / `GPTQ` hoặc lưu checkpoint 4-bit) rồi đẩy lên Dataset:
  - Dung lượng Dataset giảm từ ~85GB xuống chỉ còn **~25–30GB** (gọn trong 1–2 Dataset).
  - Tốc độ nạp từ đĩa lên GPU nhanh gấp **2–3×** vì không phải đọc trọng số FP16 rồi lượng tử hóa lại bằng `bitsandbytes` lúc khởi động.

### Ý tưởng 5: Tận dụng 30GB System RAM của Kaggle làm tầng đệm (CPU Warm Cache)
- Kaggle cung cấp ~30GB RAM hệ thống (CPU RAM).
- Khi phải đổi sang model thứ 4/5 không nằm trong GPU Pool:
  - Nếu trọng số đã được đọc qua 1 lần từ `/kaggle/input`, Linux Page Cache tự động giữ các file `.safetensors` trên RAM, nên lần swap sau chỉ mất ~6–10 giây thay vì 30–40 giây.
  - Có thể thêm bước đọc trước (warm-read) nhẹ hoặc giữ **state_dict / model thứ 4 trên CPU RAM** (offload từ GPU sang CPU thay vì `del` hoàn toàn), giúp chuyển qua lại GPU ↔ CPU nhanh hơn đọc lại từ đĩa. *(Lưu ý: chỉ offload tối đa 1–2 model 4-bit ~6GB để không tràn 30GB RAM.)*

### Ý tưởng 6: Tách `BERT-base-uncased` lên GPU để Ranking siêu nhanh (~50ms)
- Trên máy local 4GB VRAM, `service.py` cố tình đẩy `BERT-base-uncased` về CPU để nhường VRAM cho Qwen3-4B.
- Trên Kaggle T4 x2 (dư rất nhiều VRAM trên GPU 0), giữ `BERT-base-uncased` (~0.5GB) trực tiếp trên **GPU 0** giúp encode bài mới từ OpenAlex hoặc Manuscript gần như tức thì (~30–50ms thay vì ~300–500ms trên CPU).

---

## 5. Bảng chọn nhanh cấu hình theo kịch bản sử dụng

| Kịch bản | Cấu hình GPU 0 (15GB) | Cấu hình GPU 1 (15GB) | Ưu điểm nổi bật |
|---|---|---|---|
| **Demo bảo vệ đồ án (Nhanh + Ấn tượng)** | `Qwen3-4B` (**FP16**, ~8.2GB) + `BERT` (~0.5GB) | `Qwen3-14B` (4-bit, ~9.6GB) | Phản hồi mặc định siêu nhanh 2–3s; chuyển sang 14B mất 0s |
| **Demo đa dạng 3 model Qwen** *(Mặc định trong notebook)* | `Qwen3-4B` (4-bit) + `Qwen3-8B` (4-bit) + `BERT` | `Qwen3-14B` (4-bit) | 3 kích cỡ 4B/8B/14B luôn thường trú, đổi model 0s |
| **Demo so sánh 3 họ model (Qwen / Llama / Gemma)** | `Qwen3-4B` (4-bit) + `Qwen3-8B` (4-bit) + `BERT` | `Llama3.1-8B` (4-bit) + `Gemma2-9B` (4-bit) | Cả 4 model thường trú cùng lúc, so sánh 2 GPU song song |
| **Chạy offline 100% không cần tải lại** | Gắn Dataset `adapter` + Dataset `base-models` | Tự động trỏ `BASE_MODEL_*` vào `/kaggle/input/...` | Khởi động < 2 phút, không cần `HF_TOKEN`, không sợ lỗi mạng |
