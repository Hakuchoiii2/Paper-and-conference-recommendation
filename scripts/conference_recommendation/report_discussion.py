"""Conservative, data-derived discussion for the experiment report."""


def test_row(bundle, method, variant="best"):
    return next(r for r in bundle["test"]["rows"] if r["method"] == method and r["variant"] == variant)


def discussion_table1(artifacts):
    sections = ["### Nhận xét Bảng 1",
                "Best tuned nghĩa là thắng trên Train CV trong grid đã công bố, không phải cấu hình đạt Test cao nhất. Tăng điểm CV sau lựa chọn không bảo đảm tăng điểm Test."]
    for backend, bundle in artifacts.items():
        if not bundle.get("test"):
            continue
        whole = test_row(bundle, "whole_text")["metrics"]
        flat = test_row(bundle, "flat_5_facet")["metrics"]
        gated = test_row(bundle, "gated")["metrics"]
        default = test_row(bundle, "gated", "default")["metrics"]
        sections.append(f"- **{backend}:** Gated Test Hit@3 {100*default['hit@3']:.2f}% → {100*gated['hit@3']:.2f}% sau tuning "
                        f"({100*(gated['hit@3']-default['hit@3']):+.2f} điểm phần trăm). "
                        f"Best tuned Whole-Text / Flat / Gated lần lượt là **{100*whole['hit@3']:.2f}% / {100*flat['hit@3']:.2f}% / {100*gated['hit@3']:.2f}%**. "
                        f"Gated so với Whole-Text: {100*(gated['hit@3']-whole['hit@3']):+.2f} pp; so với Flat: {100*(gated['hit@3']-flat['hit@3']):+.2f} pp.")
    sections.append("Cần đánh giá đồng thời Hit@1/3/5 và MRR; hòa Hit@3 không có nghĩa hai hệ thống cho cùng thứ hạng hoặc cùng danh sách bài đúng. "
                    "Chưa có kiểm định trên dự đoán ghép cặp thì không gọi chênh lệch nhỏ là có ý nghĩa thống kê. "
                    "Khả năng xem riêng điểm từng facet là lợi ích về truy vết, chưa phải bằng chứng đã đánh giá chất lượng giải thích với người dùng. "
                    "Không nên gọi Whole-Text cosine là hoàn toàn không thể giải thích, hoặc dùng khả năng truy vết để thay thế bằng chứng về độ chính xác.")
    return sections


def discussion_table2(artifacts):
    sections = ["### Nhận xét Bảng 2",
                "Sáu dòng preset là so sánh cách phân bổ trọng số. Chỉ bốn dòng leave-one-out và phép tắt gate giữ các thành phần khác cố định mới được dùng để bàn về tác động của từng thành phần."]
    for backend, bundle in artifacts.items():
        analysis = bundle.get("analysis")
        if not analysis or not bundle.get("test"):
            continue
        base = test_row(bundle, "gated")["metrics"]["hit@3"]
        ablations = [row for row in analysis["facet_ablation_table2"] if row["name"].startswith("ablation_no_") and "test" in row]
        details = "; ".join(f"bỏ {row['name'].removeprefix('ablation_no_')}: {100*(row['test']['metrics']['hit@3']-base):+.2f} pp" for row in ablations)
        gate_off = analysis["problem_gate_ablation"]["test"]["metrics"]["hit@3"]
        sections.append(f"- **{backend}:** {details}. Tắt Problem gate: {100*base:.2f}% → {100*gate_off:.2f}% "
                        f"({100*(gate_off-base):+.2f} pp so với đầy đủ).")
    sections.append("Bỏ một facet hoặc tắt gate có thể làm Test tăng điểm. Vì vậy kết quả không chứng minh mọi facet hoặc gate luôn hữu ích. "
                    "Mọi giải thích như ‘lọc bài khác bài toán’ hoặc ‘dataset gắn với hội nghị’ mới là giả thuyết cơ chế; muốn xác nhận cần phân tích lỗi/láng giềng cụ thể. "
                    "Không chọn lại weights hoặc gate từ bảng Test này; các phương án khác chỉ là phân tích hậu nghiệm trên cùng holdout.")
    return sections


def discussion_sensitivity(artifacts):
    sections = ["### Nhận xét Bảng 3 và biểu đồ",
                "Mỗi đường là một lát cắt qua cấu hình Gated đã đóng băng của backend tương ứng; không phải cùng một cấu hình chung cho ba backend."]
    for backend, bundle in artifacts.items():
        analysis = bundle.get("analysis")
        if not analysis:
            continue
        best = analysis["best_operating_point"]
        tuning = bundle["tuning"]
        summaries = []
        for parameter, rows in analysis["sensitivity"].items():
            values = [r["value"] for r in rows]
            means = [r["cv"]["hit@3"] for r in rows]
            chosen = next(r for r in rows if r["value"] == best[parameter])
            edge = " ở biên dưới" if best[parameter] == min(values) else " ở biên trên" if best[parameter] == max(values) else " bên trong dải khảo sát"
            summaries.append(f"{parameter}*={best[parameter]:g}{edge}; biên độ mean Hit@3 trong lát cắt {100*(max(means)-min(means)):.2f} pp")
        sections.append(f"- **{backend}:** " + "; ".join(summaries) + ".")
        kpoints = analysis["sensitivity"]["k"]
        if best["k"] == max(tuning["search_space"]["k"]):
            sections.append(f"  k*={best['k']} chạm biên trên của grid tìm kiếm: hiện chưa xác nhận đã bão hòa. "
                            "Nếu khảo sát thêm k>30, cần chọn lại bằng Train CV và coi đó là thí nghiệm mới; không sửa cấu hình dựa trên Test.")
        if best["tau"] == min(tuning["search_space"]["tau"]):
            sections.append("  Tau* nằm ở biên dưới của grid: chưa loại trừ điểm tốt hơn ở ngưỡng thấp hơn.")
    sections.append("Độ lệch chuẩn giữa 5 fold mô tả biến thiên theo cách chia dữ liệu; vùng tô không phải khoảng tin cậy hay kiểm định ý nghĩa. "
                    "Không kết luận ‘tăng liên tục’, ‘độ dốc chuẩn mực’ hoặc ‘hình chuông’ khi đường số liệu có dao động. "
                    "Một đỉnh trên mean không chứng minh cơ chế nhân quả, cũng không khẳng định cấu hình đó tốt nhất ở mọi fold. "
                    "Trục tung của từng ô có thể khác nhau; phải đọc biên độ số, không chỉ so độ dốc bằng mắt.")
    return sections


def table4_rationale():
    return [
        "### Vì sao Bảng 4 dùng Gated thay vì Whole-Text?",
        "**Bảng 1 đánh giá độ chính xác giữa các phương pháp; Bảng 4 đánh giá ảnh hưởng của bộ trích xuất trong kiến trúc facet đang nghiên cứu.** "
        "Câu hỏi của Bảng 4 là: khi kho Train, embedding và thuật toán đối sánh đã cố định, việc thay LLM trích xuất facets của bản thảo làm thay đổi gợi ý như thế nào? "
        "Do đó Gated được giữ làm đối tượng khảo sát của thí nghiệm này, không được chọn vì thắng Whole-Text trên Test.",
        "**Whole-Text là một đối chứng bất biến theo extractor trong thiết kế hiện tại.** Nó chỉ dùng Title + Abstract gốc; "
        "thay Qwen-8B bằng Qwen-14B, Llama hoặc Gemma để trích facets không thay đổi đầu vào Whole-Text. "
        "TF-IDF của Whole-Text cũng được fit riêng theo trường trên Train, nên không nhận thông tin từ các facets thay thế. "
        "Với cùng encoder và cấu hình k đã đóng băng, chạy lại Whole-Text cho cả 5 LLM sẽ lặp cùng một đối chứng, "
        "không đo được tác động của chất lượng trích xuất. Điểm Whole-Text tuned ở Bảng 1 vì vậy vẫn là mốc so sánh độ chính xác cho Bảng 4.",
        "**Cấu hình được đóng băng là cấu hình tốt nhất bên trong họ Gated theo Train CV của từng backend.** "
        "Giữ nguyên k*, tau*, kappa*, weights* và kho facets Train Qwen-8B giúp chỉ thay một thành phần: facets Test do LLM tạo ra. "
        "Nếu tune lại riêng cho từng LLM thì chênh lệch sẽ trộn tác động của extractor với tác động của chọn siêu tham số. "
        "Bảng 4 không phải phép chọn lại phương pháp thắng cuộc, và không dùng điểm Test để thay cấu hình.",
        "**Lý do tiếp tục nghiên cứu kiến trúc facet dù độ chính xác hiện thấp hơn** là khả năng kiểm tra riêng tương đồng Problem, Task, Method, Dataset và Contribution, "
        "bóc tách ảnh hưởng bằng ablation, và thay extractor mà vẫn giữ lớp đối sánh. "
        "Đây là những thuộc tính cấu trúc hữu ích cho phân tích lỗi và phát triển hệ thống theo khía cạnh; "
        "kết quả hiện tại chưa đo được mức hữu ích của giải thích với người dùng, chưa chứng minh lợi ích đó bù đắp phần giảm độ chính xác hoặc chi phí LLM.",
        "**Phạm vi kết luận:** việc chọn Gated ở Bảng 4 phù hợp với câu hỏi nghiên cứu về extractor; "
        "điều này không đồng nghĩa nên ưu tiên Gated khi triển khai chỉ để tối đa Hit@3. "
        "Nếu mục tiêu duy nhất là độ chính xác, phải chọn theo tiêu chí validation đã công bố và thừa nhận kết quả mạnh của Whole-Text. "
        "Để xác định thay extractor có lợi riêng cho gate hay cho biểu diễn facets nói chung, cần bổ sung Flat 5-Facet dưới cùng 5 LLM ở một thí nghiệm tiếp theo; "
        "Bảng 4 hiện chỉ đo sự thay đổi của Gated.",
    ]


def discussion_table4(artifacts):
    sections = ["### Nhận xét Bảng 4",
                "Đây là so sánh chuyển bộ trích xuất ở Test với kho Train Qwen-8B cố định, không phải huấn luyện lại toàn bộ hệ thống theo từng LLM."]
    for backend, bundle in artifacts.items():
        benchmark = bundle.get("benchmark")
        if not benchmark:
            continue
        rows = benchmark["rows"]
        base = next((r for r in rows if r["extractor"] == "Qwen-8B"), None)
        low, high = min(r["metrics"]["hit@3"] for r in rows), max(r["metrics"]["hit@3"] for r in rows)
        sections.append(f"- **{backend}:** Hit@3 trên các LLM đã đo nằm trong {100*low:.2f}%–{100*high:.2f}%. "
                        "Đây là độ phân tán quan sát trên một Test cố định; không tự suy ra tính chịu lỗi trước nhiễu hoặc khả năng tổng quát hóa ngoài tập dữ liệu.")
        if base:
            for row in rows:
                if row["extractor"] != "Qwen-14B":
                    continue
                sections.append(f"  Qwen-8B → Qwen-14B: Hit@3 {100*base['metrics']['hit@3']:.2f}% → {100*row['metrics']['hit@3']:.2f}%; "
                                f"Hit@1 {100*base['metrics']['hit@1']:.2f}% → {100*row['metrics']['hit@1']:.2f}%; "
                                f"MRR {base['metrics']['mrr']:.4f} → {row['metrics']['mrr']:.4f}.")
    sections.append("LLM lớn hơn có thể tăng Hit@3 nhưng giảm Hit@1/MRR hoặc Macro-Hit@3. "
                    "Kết quả không xác lập upper bound, không bảo đảm nâng cấp LLM luôn tăng hiệu năng và không chứng minh Whole-Text đã chạm trần. "
                    "Phải so với baseline tuned của Bảng 1, thay vì chỉ baseline mặc định. Chọn LLM thắng trên Test rồi báo lại như lựa chọn độc lập sẽ gây thiên lệch lựa chọn.")
    return sections


def limitations(artifacts):
    sections = ["## Kết luận và giới hạn bằng chứng",
                "Các kết luận ở đây là mô tả kết quả đã đo; không xem ±std CV là bằng chứng về ý nghĩa thống kê trên Test."]
    if all(bundle.get("test") for bundle in artifacts.values()):
        rows = [(backend, row) for backend, b in artifacts.items() for row in b["test"]["rows"] if row["variant"] == "best"]
        highest = max(rows, key=lambda item: item[1]["metrics"]["hit@3"])
        backend, row = highest
        sections.append(f"Trong các cấu hình Best tuned ở Bảng 1, Test Hit@3 cao nhất quan sát là **{100*row['metrics']['hit@3']:.2f}%** "
                        f"({row['method']}, {backend}); đây là thống kê mô tả, không chọn lại backend bằng Test. "
                        "Không có cơ sở để kết luận Gated vượt trội toàn diện so với các baseline đã tune.")
    sections += [
        "- **Mức phân giải Test:** với 168 bài, một bài tương ứng khoảng 0,595 điểm phần trăm Hit@K. Chênh lệch 0,60–1,19 pp chỉ tương ứng 1–2 bài về tổng số đúng; cần xem cả cặp dự đoán bất đồng. Không suy ra ý nghĩa thống kê chỉ từ phần trăm làm tròn.",
        "- **Độ bất định:** nên bổ sung khoảng tin cậy bootstrap ghép cặp trên từng paper và/hoặc kiểm định McNemar cho Hit@3 nếu cần tuyên bố hơn/kém. Nếu kiểm tra nhiều cặp, phải công bố phạm vi kiểm định và xử lý đa so sánh. Chưa thực hiện kiểm định thì không gắn nhãn significant.",
        "- **Mất cân bằng nhãn:** Test có 30 ứng viên nhưng không nhất thiết có mẫu cho cả 30 hội nghị. Cần báo cáo số lớp hoạt động, phân bố số bài và Macro-Hit@3/Macro-MRR của baseline, không chỉ của Gated. Chênh lệch micro–macro gợi ý hiệu năng chưa đồng đều giữa hội nghị, không tự chứng minh nguyên nhân.",
        "- **Khả năng tái lập:** công bố checkpoint embedding, phiên bản thư viện, split theo thời gian, seed, tập preset và quy tắc missing-facet/tie-break. TF-IDF Whole-Text dùng Title + Abstract, không gọi đó là full paper. Chưa có revision checkpoint và số đo thời gian/chi phí extraction thì cần nêu thiếu thông tin này, không suy ra hiệu quả chi phí.",
        "- **Giới hạn thiết kế:** 5-fold CV được dùng để chọn siêu tham số nên điểm CV thắng cuộc có thể lạc quan; chưa có nested CV. Không yêu cầu nested CV để dùng holdout cuối, nhưng phải giữ Test khỏi các quyết định mới. Mở rộng grid vì chạm biên phải được ghi thành vòng thí nghiệm mới.",
    ]
    return sections


def appendix_macro(artifacts, table, number):
    sections = ["## Phụ lục A — Hiệu năng macro của các cấu hình Best tuned",
                "Bổ sung Macro-Hit@3 và Macro-MRR cho cả baseline để tránh chỉ so micro trên dữ liệu mất cân bằng. Macro là trung bình theo hội nghị có mẫu Test, không chia đều cho các hội nghị không có mẫu."]
    rows = []
    labels = {"whole_text": "Whole-Text", "flat_5_facet": "Flat 5-Facet", "gated": "Gated 5-Facet"}
    for backend, bundle in artifacts.items():
        if not bundle.get("test"):
            continue
        first = bundle["test"]["rows"][0]
        counts = {venue: data["test_count"] for venue, data in first["per_venue"].items()}
        largest = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:3]
        sections.append(f"- **{backend}:** {len(counts)}/{len(bundle['tuning']['metadata']['candidates'])} hội nghị có mẫu Test; "
                        f"các lớp lớn nhất: {', '.join(f'{v}={n}' for v,n in largest)}.")
        for method in labels:
            metrics = test_row(bundle, method)["metrics"]
            rows.append([backend, labels[method], number(metrics, "hit@3"), number(metrics, "macro_hit@3"), number(metrics, "macro_mrr")])
    sections.append(table(["Backend", "Method (best)", "Micro-Hit@3", "Macro-Hit@3", "Macro-MRR"], rows))
    return sections
