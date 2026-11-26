# DS300 FacetRec — Demo Web App

Ứng dụng web hỗ trợ **trích xuất năm facet khoa học có dẫn chứng**, **gợi ý bài báo liên quan**, **gợi ý hội nghị phù hợp** và **so sánh các LLM extractor** từ Title & Abstract của manuscript.

---

## 1. Giới thiệu tổng quan

Trong nghiên cứu khoa học, việc tìm kiếm tài liệu và chọn hội nghị xuất bản thường gặp khó khăn do các phương pháp tìm kiếm truyền thống gộp chung toàn bộ abstract, làm lu mờ các khía cạnh quan trọng.

Hệ thống **DS300 FacetRec** giải quyết vấn đề trên bằng cách phân tách nội dung manuscript thành **5 facet cốt lõi kèm bằng chứng trích dẫn nguyên văn**:
- **Problem:** Vấn đề nghiên cứu cần giải quyết.
- **Task:** Nhiệm vụ cụ thể của bài báo.
- **Method:** Phương pháp hoặc mô hình đề xuất.
- **Dataset:** Dữ liệu, ngữ liệu hoặc benchmark sử dụng.
- **Contribution:** Đóng góp chính được công bố.

Dựa trên 5 facet này, hệ thống sẽ:
1. Xếp hạng **Bài báo liên quan** trong corpus và giải thích mức độ trùng khớp theo từng facet.
2. Xếp hạng **Hội nghị phù hợp** dựa trên hồ sơ bài báo lịch sử và minh họa bằng các bài đại diện.
3. Cung cấp trang **So sánh Extractor** để đối chiếu đầu ra giữa các LLM (Qwen, Llama, Gemma,...).

---

## 2. Cấu trúc thư mục

```text
demo/
├── frontend/               # Ứng dụng React + TypeScript + Vite + Tailwind CSS
│   ├── src/
│   │   ├── components/     # Layout, SystemDrawer, FacetBadge, HighlightedText
│   │   ├── constants/      # Nhãn & mã màu 5 facet
│   │   ├── context/        # Quản lý kết nối API & nạp model
│   │   ├── pages/          # 5 trang nghiệp vụ theo đặc tả:
│   │   │   ├── InputPage.tsx              # Trang 1: Nhập Title & Abstract
│   │   │   ├── AnalysisResultPage.tsx     # Trang 2: Kết quả 5 facet & 2 tab gợi ý
│   │   │   ├── PaperDetailPage.tsx        # Trang 3: Chi tiết bài báo & đối chiếu facet
│   │   │   ├── ConferenceDetailPage.tsx   # Trang 4: Chi tiết hội nghị & bài lịch sử
│   │   │   └── ComparePage.tsx            # Trang 5: So sánh tuần tự các Extractor
│   │   ├── services/api/   # HttpApiClient kết nối trực tiếp /api/v1/*
│   │   └── types/          # TypeScript interfaces chuẩn API contract
│   └── dist/               # Bản build tĩnh sau khi chạy build
├── backend/                # Server FastAPI phục vụ /api/v1/* và giao diện tĩnh
│   ├── main.py             # 16 endpoints API + Single Page App fallback
│   ├── schemas.py          # Pydantic schemas khớp 1:1 với Frontend
│   ├── service.py          # Service nạp _local/demo_artifacts/ & chạy các phương pháp Ranking
│   └── requirements.txt    # Danh sách thư viện Python
└── script/
    └── build_demo_artifacts.py  # Script tái tạo bộ dữ liệu demo & embedding 6 trường
```

---

## 3. Hướng dẫn chạy & tái lập trên máy cục bộ (Local)

Hệ thống được thiết kế để **tái lập hoàn toàn từ dữ liệu gốc trong repo** và hỗ trợ 2 mức sử dụng:
* **Không cần copy `_local/adapter/` (Chạy ngay trên mọi máy):** Đầy đủ chế độ **Mẫu có sẵn** (168 bài Test sạch × đủ 5/5 LLM thật ở cả `InputPage` & `ComparePage`), chế độ **Toàn văn (Full-Text)** cho bản thảo mới bất kỳ, và đủ 3 phương pháp Ranking cho Bài báo & Hội nghị (`TF-IDF` + `BGE-small`).
* **Máy có GPU + tự bổ sung `_local/adapter/`:** Dùng thêm khi muốn chạy **Live LLM thật trên GPU** cho bản thảo mới nhập tay ở chế độ `Trực tiếp`.

### Bước chuẩn bị 1: Cấu hình môi trường (`demo/.env`)
Trong thư mục `demo/` đã có sẵn file [`.env.example`](.env.example). Sao chép thành `.env`:
```powershell
cd demo
copy .env.example .env
```
*(Nếu không tạo `.env`, backend và script build vẫn dùng các đường dẫn mặc định tương đối từ `demo/`).*

### Bước chuẩn bị 2: Cài thư viện Python & Tái tạo bộ dữ liệu Demo (`_local/demo_artifacts/`) — **Bắt buộc lần đầu**
Vì thư mục `_local/` nằm trong `.gitignore` (không push lên GitHub), khi clone repo sang máy mới hãy cài thư viện và chạy **1 lệnh duy nhất** từ thư mục gốc của repo:
```powershell
pip install -r demo\backend\requirements.txt
# (Tùy chọn) Chỉ cài thêm nếu máy có GPU NVIDIA và muốn bật ENABLE_REAL_LLM=true:
# pip install -r demo\backend\requirements-llm.txt

python demo\script\build_demo_artifacts.py
```
Script sẽ tự động đọc dữ liệu gốc từ `paper-and-conference-recommendation-experiments/data/` và sinh ra `_local/demo_artifacts/` gồm:
- `paper_corpus.jsonl`: 4,210 bài báo kèm 5 facets thật từ Exp A (kho ứng viên cho Khuyến nghị Bài báo).
- `conference_train_pool.jsonl` & `conference_catalog.json`: 602 bài Train (1982–2015) & 30 hội nghị kèm 30 link trang nguồn chính thống (tách biệt hoàn toàn với Test, 0% data leak).
- `demo_examples.json`: 168 bài Test sạch (2016–2019) kèm đủ **5 / 5 đầu ra LLM thật** (`Qwen3-4B`, `Qwen3-8B`, `Qwen3-14B`, `Llama3.1-8B`, `Gemma2-9B`).
- `*_bge_small_*.npz`: Vector `BGE-small` cho cả 6 trường (`whole_text` + 5 facets). *(Nếu máy mới chưa có `_local/models/bge-small-en-v1.5`, script sẽ tự tải `BAAI/bge-small-en-v1.5` ~130MB từ Hugging Face).*

> **Lưu ý về `_local/adapter/` và `ENABLE_REAL_LLM`:**
> - **Máy không có GPU / chưa copy `_local/adapter/`**: Đặt `ENABLE_REAL_LLM=false` trong `demo/.env` — vẫn chạy đầy đủ **100% tính năng** ở chế độ `Mẫu có sẵn` (168 bài Test × 5 LLM thật ở cả `InputPage` & `ComparePage`), chế độ `Toàn văn (Full-Text)` và toàn bộ các phương pháp Ranking (`TF-IDF` + `BGE-small`).
> - **Máy có GPU NVIDIA (≥ 4GB VRAM) + đã copy `_local/adapter/`**: Giữ `ENABLE_REAL_LLM=true` và `LOAD_IN_4BIT=true` trong `demo/.env` để chạy trích xuất `Qwen3-4B + LoRA` thật trực tiếp trên GPU (tự động đẩy `BGE-small` sang CPU trên GPU ≤ 6.5GB VRAM để tránh tràn VRAM).

---

### Cách A: Chế độ Phát triển (Khuyên dùng khi xem và thử nghiệm)

Mở **2 cửa sổ Terminal**:

* **Terminal 1 — Chạy Backend FastAPI:**
  ```powershell
  cd demo\backend
  pip install -r requirements.txt
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
  ```
  *(Backend sẽ chạy tại `http://localhost:8000`)*

* **Terminal 2 — Chạy Frontend Vite:**
  ```powershell
  cd demo\frontend
  npm install
  npm run dev
  ```
  *(Truy cập giao diện tại **`http://localhost:5173`**. Vite đã được cấu hình tự động proxy các request `/api/v1` sang cổng `8000`).*

---

### Cách B: Chế độ Đóng gói 1 Cổng duy nhất (Giống môi trường Kaggle)

Cách này build frontend thành các file tĩnh và để FastAPI phục vụ cả web lẫn API tại một địa chỉ duy nhất:

```powershell
# 1. Build frontend thành static files
cd demo\frontend
npm install
npm run build

# 2. Khởi chạy FastAPI
cd ..\backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
Truy cập ứng dụng tại: **`http://localhost:8000`**.

---

## 4. Tùy chỉnh và Chuyển đổi Mô hình Extractor

Hệ thống hỗ trợ nạp linh hoạt 5 mô hình Extractor:
1. **Qwen3-4B-Instruct** (Yêu cầu tối thiểu ~4GB VRAM GPU, hỗ trợ chạy 4-bit)
2. **Qwen3-8B-Instruct** (Yêu cầu tối thiểu 8GB VRAM)
3. **Qwen3-14B-Instruct** (Yêu cầu tối thiểu 16GB VRAM)
4. **Llama-3.1-8B-Instruct** (Yêu cầu tối thiểu 8GB VRAM)
5. **Gemma-2-9B-IT** (Yêu cầu tối thiểu 9GB VRAM)

### Khi máy người khác đã tải sẵn mô hình ở thư mục khác:
Mở file `demo/.env`, trỏ đường dẫn tới checkpoint mô hình hoặc thư mục cache trên máy:
```env
# Trỏ trực tiếp đến snapshot checkpoint hoặc tên trên Hugging Face
BASE_MODEL_QWEN4B=D:/my_models/Qwen3-4B
BASE_MODEL_QWEN8B=D:/my_models/Qwen3-8B
ADAPTER_ROOT=D:/my_adapters
```
Khi mở giao diện web, người dùng chỉ cần mở panel **"Hệ thống & Model Runtime"** ở góc trên bên phải, bấm vào model mong muốn và chọn **"Nạp model"**. Hệ thống sẽ tự động dọn dẹp bộ nhớ GPU và nạp mô hình mới lên!

---

## 5. Hướng dẫn chạy trên Kaggle Notebooks

Vì Kaggle không mở trực tiếp cổng mạng ra Internet, giải pháp là **chạy FastAPI serve cả web và tạo một đường hầm HTTPS tạm thời qua Cloudflare Tunnel (`pycloudflared`)**.

### Bước 1: Thiết lập Notebook trên Kaggle
1. Tạo một Notebook mới trên Kaggle.
2. Tại panel bên phải (**Notebook options**), gạt bật **`Internet On`** *(Bắt buộc)*. Accelerator có thể để `None` hoặc `GPU T4`.

### Bước 2: Chạy các Cell Code

* **Cell 1: Tải source code nhánh `feat/demo_v2`**
  ```python
  !git clone https://github.com/Hakuchoiii2/Paper-and-conference-recommendation.git
  %cd Paper-and-conference-recommendation
  !git checkout feat/demo_v2
  ```

* **Cell 2: Cài đặt thư viện Python, sinh dữ liệu Demo & công cụ Tunnel**
  ```python
  !pip install -q fastapi uvicorn pydantic sentence-transformers pycloudflared
  !python demo/script/build_demo_artifacts.py
  ```

* **Cell 3: Build giao diện Frontend tĩnh**
  ```python
  %cd demo/frontend
  !npm install -q
  !npm run build
  %cd ../..
  ```

* **Cell 4: Khởi chạy Server và nhận link truy cập**
  ```python
  import subprocess
  import time
  from pycloudflared import try_cloudflare

  # 1. Chạy FastAPI ngầm trên cổng 8000
  %cd demo/backend
  process = subprocess.Popen(
      ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
  )
  time.sleep(3)  # Đợi server sẵn sàng

  # 2. Tạo đường dẫn Cloudflare Tunnel công khai
  tunnel = try_cloudflare(port=8000)
  print("\n" + "=" * 65)
  print(f"🎉 LINK TRUY CẬP DEMO (CLICK VÀO ĐỂ DÙNG):\n👉 {tunnel.tunnel}")
  print("=" * 65 + "\n")
  ```

> Khi mở đường link `https://xxxx.trycloudflare.com`, trình duyệt sẽ tải toàn bộ giao diện và tương tác bình thường với backend FastAPI đang chạy trên phiên Kaggle mà không bị lỗi CORS.

---

## 6. Trạng thái hiện tại của phiên bản Demo

- **Frontend:** Đã hoàn chỉnh giao diện nhập liệu (tìm kiếm 168 bài Test, chọn Encoder & 2 bộ chọn Phương pháp Ranking cho Bài báo / Hội nghị), xem kết quả & giải thích chi tiết, so sánh 5 LLM Extractor thật, lịch sử phân tích và cấu hình Runtime.
- **Backend & Artifacts:** Đã chuẩn hóa 3 kho dữ liệu sạch không data leak (`_local/demo_artifacts/`) và cài đặt đầy đủ các phương pháp Ranking (`Whole-Text`, `Equal 5-Facet`, `Weighted 5-Facet` cho Bài báo; `Whole-Text k-NN`, `Flat 5-Facet k-NN`, `Gated 5-Facet k-NN` cho Hội nghị) trên cả `TF-IDF` lẫn `BGE-small`.
- **Live GPU LLM (`model_runner.py`):** Đã nối trực tiếp `Qwen3-4B-Instruct` 4-bit NF4 + LoRA adapter (`enable_thinking=False`, prompt `extraction_gold_v1.md`, bộ parse JSON 3 tầng chống lỗi cắt ngang) chạy ổn định trên GPU 4GB VRAM (`RTX 3050 Ti`).
