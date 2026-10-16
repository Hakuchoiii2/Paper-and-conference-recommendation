# Exp E — Cập nhật profile theo thời gian (Modular Temporal Architecture)

[Chỉ mục script](../README.md) · [Generator E](../../data/exp_e/README.md) · [Profile C](../exp_c/README.md) · [Giao diện chung](../BASELINE_GUIDE.md)

## 1. E khác C/D ở đâu?

C kiểm tra profile tại một cutoff, D kiểm tra hướng phiên. E giữ profile builder/ranker C, thay **cách cân thời gian evidence** để đo thích ứng khi sở thích đổi.

E dùng users C rồi sinh stream/profile riêng. Không cần predictions/checkpoint model C hoặc kết quả D.

## 2. Cấu trúc Thư mục & Quy chuẩn Đặt tên (Unified Architecture)

Thư mục `scripts/exp_e` và `results/exp_e` được tổ chức theo kiến trúc **Modular Registry Pattern** để dễ dàng mở rộng và thử nghiệm các ý tưởng mới:

```text
scripts/exp_e/
├── README.md                      # Tài liệu hướng dẫn thực nghiệm E
├── base.py                        # Lớp cơ sở BaseTemporalModel & các hàm tính profile chung
├── registry.py                    # Registry (@register_temporal_model) & Presets
├── run_exp_e.py                   # Entrypoint chính (hỗ trợ --preset, --models, --list-models)
├── methods/                       # Các họ mô hình thời gian
│   ├── baselines.py               # Static, Recent
│   ├── decay_fixed.py             # Exponential Decay cố định (HL 14, 21, 30, 60)
│   ├── decay_adaptive.py          # Adaptive Decay theo độ lệch sở thích ngắn/dài hạn
│   ├── change_point.py            # Change-Point Shift Gate phát hiện điểm gãy sở thích
│   ├── dual_state.py              # Dual-State Hybrid kết hợp Short-term & Long-term profile
│   └── decay_power_law.py         # Power-Law (Hyperbolic) Decay
├── sweeps/                        # Kịch bản khảo sát độ nhạy tham số
│   ├── sweep_half_life.py         # Quét chu kỳ bán rã Half-Life (3 -> 180 ngày)
│   └── sweep_dual_state.py        # Quét trọng số Alpha của mô hình Dual-State
└── analysis/                      # Công cụ tổng hợp & đối sánh kết quả
    └── compare_models.py          # Xuất bảng Markdown so sánh toàn diện các mô hình
```

### Quy chuẩn đặt tên mô hình (`<family>__<method>__<param>`)

| Mã chuẩn hóa (Unified Key) | Alias (Canonical) | Ý nghĩa thuật toán |
|---|---|---|
| `popularity` | `popularity` | Tổng phản ứng dương toàn bộ users trước cutoff |
| `baseline__static__all` | `static` | Toàn bộ quá khứ, trọng số thời gian $w_t = 1$ |
| `baseline__recent__prev_period` | `recent` | Chỉ giữ kỳ ngay trước cutoff ($t \ge \text{recent\_start}$) |
| `decay__exp__hl30` | `decay` | Suy giảm hàm mũ $w_t = 2^{-\Delta t / T_{1/2}}$ ($T_{1/2} = 30$ ngày) |
| `decay__adaptive__divergence` | — | Tự động co giãn $T_{1/2} \in [10, 60]$ ngày theo độ tương đồng ngắn/dài hạn |
| `drift__shift_gate__cos0.55` | — | Phát hiện điểm dịch chuyển sở thích để giảm trọng số quá khứ cũ |
| `hybrid__dual_state__alpha0.65` | — | Tổ hợp tuyến tính hồ sơ ngắn hạn ($\alpha=0.65$) và dài hạn ($0.35$) |
| `decay__power_law__beta0.6` | — | Suy giảm hàm lũy thừa $w_t = (1 + \Delta t / \tau_0)^{-\beta}$ |

## 3. Dữ liệu và mốc đánh giá

300 users, bốn kỳ tháng, 15 events/kỳ/user; 150 stable, 150 drift. Group và true profiles được giấu trong `ground_truth`.

| Case | Cutoff | Lịch sử hợp lệ | Candidates |
|---|---|---|---|
| Kỳ 2 | Đầu tháng 2 | Kỳ 1 | 15 bài kỳ 2 |
| Kỳ 3 | Đầu tháng 3 | Kỳ 1–2 | 15 bài kỳ 3 |
| Kỳ 4 | Đầu tháng 4 | Kỳ 1–3 | 15 bài kỳ 4 |

900 cases = 300 users × 3 mốc. Tổng **18.000 phản ứng độc lập**.

## 4. Hướng dẫn Chạy Thực nghiệm (CLI)

```powershell
# 1. Liệt kê toàn bộ mô hình và preset đã đăng ký
python scripts/exp_e/run_exp_e.py --list-models

# 2. Kiểm tra hợp lệ dữ liệu (Dry-run)
python scripts/exp_e/run_exp_e.py --dry-run

# 3. Chạy chuẩn canonical (tương thích 100% với bộ test chung)
python scripts/exp_e/run_exp_e.py --preset canonical --output results/exp_e/baselines --overwrite

# 4. Chạy đối sánh toàn bộ Baselines + Các ý tưởng mới (Unified Benchmark)
python scripts/exp_e/run_exp_e.py --preset all --output results/exp_e/ideas/all_ideas_benchmark --overwrite

# 5. Chạy thử nghiệm một hoặc nhiều mô hình cụ thể
python scripts/exp_e/run_exp_e.py --models decay__adaptive__divergence hybrid__dual_state__alpha0.65 --output results/exp_e/ideas/custom_run --overwrite

# 6. Chạy khảo sát độ nhạy tham số (Sweeps) và xuất bảng tổng hợp
python scripts/exp_e/sweeps/sweep_half_life.py
python scripts/exp_e/sweeps/sweep_dual_state.py
python scripts/exp_e/analysis/compare_models.py
```

## 5. Cách thêm một ý tưởng mới

1. Tạo file mới trong `scripts/exp_e/methods/` (ví dụ `my_new_idea.py`).
2. Kế thừa `BaseTemporalModel` từ `exp_e.base` và gắn decorator `@register_temporal_model('<family>__<method>__<param>')`.
3. Import module mới vào `scripts/exp_e/methods/__init__.py`.
4. Chạy thử ngay bằng `--models <family>__<method>__<param>`.
