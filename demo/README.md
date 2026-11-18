# DS300 FacetRec — Demo Web App (Frontend + Backend Adapter)

Ứng dụng web hỗ trợ **trích xuất năm facet khoa học có dẫn chứng** (`problem`, `task`, `method`, `dataset`, `contribution`), **gợi ý bài báo liên quan**, **gợi ý hội nghị phù hợp** và **so sánh các LLM extractor** từ Title & Abstract của manuscript.

## Cấu trúc thư mục

```text
demo/
├── frontend/               # React + TypeScript + Vite + Tailwind CSS
│   ├── src/
│   │   ├── components/     # Layout, SystemDrawer, FacetBadge, HighlightedText
│   │   ├── constants/      # Cấu hình nhãn & màu 5 facet
│   │   ├── context/        # SystemContext (kết nối Backend API & nạp model)
│   │   ├── pages/          # 5 trang theo đặc tả (Input, Result, Paper, Conference, Compare)
│   │   ├── services/api/   # HttpApiClient gọi /api/v1/*
│   │   └── types/          # TypeScript interfaces cho toàn bộ API contract
│   └── dist/               # Bản build tĩnh (sau khi chạy npm run build)
└── backend/                # Khung FastAPI phục vụ /api/v1/* và static frontend
```

## Hướng dẫn chạy Frontend (Phát triển Local)

```bash
cd demo/frontend
npm install
npm run dev
```

Mở trình duyệt tại `http://localhost:5173`.
Mặc định Vite proxy `/api/v1` sang `http://localhost:8000` (hoặc bạn có thể cấu hình địa chỉ backend tùy chỉnh trong bảng phụ **Hệ thống**).

## Build bản tĩnh để phục vụ cùng Backend (Kaggle / Production)

```bash
cd demo/frontend
npm run build
```

Bản build tĩnh nằm trong `demo/frontend/dist/`. Khi backend FastAPI mount thư mục này và phục vụ `/api/v1/*` trên cùng origin, frontend sẽ tự động gọi đường dẫn tương đối `/api/v1`.
