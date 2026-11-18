# DS300 FacetRec — Demo Web App (Frontend + FastAPI Backend)

Ứng dụng demo hỗ trợ **trích xuất năm facet khoa học có dẫn chứng** (`problem`, `task`, `method`, `dataset`, `contribution`), **gợi ý bài báo liên quan**, **gợi ý hội nghị phù hợp** và **so sánh các LLM extractor** từ Title & Abstract của manuscript.

## Cấu trúc thư mục

```text
demo/
├── frontend/               # React + TypeScript + Vite + Tailwind CSS
│   ├── src/
│   │   ├── components/     # Layout, SystemDrawer, FacetBadge, HighlightedText
│   │   ├── constants/      # Cấu hình nhãn & màu 5 facet
│   │   ├── context/        # SystemContext (quản lý mode mock/http & nạp model)
│   │   ├── mocks/          # Bộ dữ liệu mẫu (fixtures) bám sát corpus CSFCube
│   │   ├── pages/          # 5 trang theo đặc tả (Input, Result, Paper, Conference, Compare)
│   │   ├── services/api/   # Lớp ApiClient với 2 adapter: mockClient & httpClient
│   │   └── types/          # TypeScript interfaces cho toàn bộ API contract
│   └── dist/               # Bản build tĩnh (sau khi chạy npm run build)
└── backend/                # FastAPI phục vụ /api/v1/* và static frontend
    ├── main.py             # 16 endpoints /api/v1/* + SPA fallback an toàn
    ├── schemas.py          # Pydantic schemas khớp 1:1 với frontend
    ├── service.py          # Adapter đọc corpus papers.jsonl & tính TF-IDF ranking
    └── requirements.txt
```

## Trạng thái hiện tại (Thật vs Mock/Adapter)

- **Frontend (5 trang + Bảng phụ Hệ thống):** Hoàn thiện đầy đủ luồng nghiệp vụ, chạy độc lập với `MockApiClient` mà không cần GPU hay Python backend.
- **Backend FastAPI:** Hiện thực đủ 16 endpoint `/api/v1/*` và nạp trực tiếp corpus `data/processed/papers.jsonl` để tính điểm TF-IDF cosine cho bài báo.
- **Phần cần nối tiếp khi chạy trên GPU Kaggle:** Thay thế hàm `_extract_heuristic_facets` trong `backend/service.py` bằng hàm gọi model thực tế (`Qwen3`, `Llama3.1`, `Gemma2`) từ `scripts/exp_a` và bộ hồ sơ hội nghị từ `data/conference_recommendation_dataset`.

## Hướng dẫn chạy

### 1. Chạy Frontend ở chế độ Mock (không cần Backend/GPU)
```bash
cd demo/frontend
npm install
npm run dev
```
Mở trình duyệt tại `http://localhost:5173`. Mặc định ứng dụng chạy ở **Chế độ mẫu (Mock)**. Bạn có thể chuyển sang chế độ HTTP bất kỳ lúc nào trong bảng phụ **Hệ thống**.

### 2. Chạy Backend FastAPI + Frontend (Local / Kaggle)
```bash
# 1. Build frontend thành tệp tĩnh
cd demo/frontend
npm run build

# 2. Cài đặt và chạy FastAPI
cd ../backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
Khi đã build `frontend/dist`, truy cập `http://localhost:8000` (hoặc URL tunnel trên Kaggle) sẽ mở trực tiếp giao diện React và gọi API tại `/api/v1/*` trên cùng một origin.
