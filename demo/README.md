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
└── backend/                # Server FastAPI phục vụ /api/v1/* và giao diện tĩnh
    ├── main.py             # 16 endpoints API + Single Page App fallback
    ├── schemas.py          # Pydantic schemas khớp 1:1 với Frontend
    ├── service.py          # Adapter nạp corpus papers.jsonl & tính điểm TF-IDF
    └── requirements.txt    # Danh sách thư viện Python
```

---

## 3. Hướng dẫn chạy trên máy cục bộ (Local)

Bạn có thể chạy thử theo một trong hai cách:

### Cách A: Chế độ Phát triển (Khuyên dùng khi sửa code giao diện)

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

## 4. Hướng dẫn chạy trên Kaggle Notebooks

Vì Kaggle không mở trực tiếp cổng mạng ra Internet, giải pháp là **chạy FastAPI serve cả web và tạo một đường hầm HTTPS tạm thời qua Cloudflare Tunnel (`pycloudflared`)**.

### Bước 1: Thiết lập Notebook trên Kaggle
1. Tạo một Notebook mới trên Kaggle.
2. Tại panel bên phải (**Notebook options**), gạt bật **`Internet On`** *(Bắt buộc)*. Accelerator có thể để `None` hoặc `GPU T4`.

### Bước 2: Chạy các Cell Code

* **Cell 1: Tải source code nhánh `feat/demo`**
  ```python
  !git clone https://github.com/Hakuchoiii2/Paper-and-conference-recommendation.git
  %cd Paper-and-conference-recommendation
  !git checkout feat/demo
  ```

* **Cell 2: Cài đặt thư viện Python & công cụ Tunnel**
  ```python
  !pip install -q fastapi uvicorn pydantic scikit-learn pycloudflared
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

## 5. Trạng thái hiện tại của phiên bản Demo

- **Frontend:** Đã hoàn chỉnh 100% về giao diện, luồng phân tích, đối chiếu facet, highlight bằng chứng và bảng so sánh extractor.
- **Backend Adapter:** Đã hoàn thiện toàn bộ hợp đồng API (`/api/v1/*`), nạp trực tiếp corpus từ `data/processed/papers.jsonl` và tính điểm xếp hạng theo TF-IDF cosine.
- **Mở rộng GPU sau này:** Khi kết nối pipeline LLM GPU thật (thực nghiệm A), bạn chỉ cần thay hàm trích xuất `_extract_heuristic_facets` trong `demo/backend/service.py` bằng hàm gọi checkpoint mô hình.
