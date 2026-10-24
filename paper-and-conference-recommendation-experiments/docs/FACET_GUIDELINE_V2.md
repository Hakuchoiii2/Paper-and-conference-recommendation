# HƯỚNG DẪN GÁN NHÃN 5 FACETS (PHIÊN BẢN 2.0 - ROLE-AWARE)
## QUY CHUẨN XÁC ĐỊNH BẰNG CHỨNG HỌC THUẬT CHO BÀI BÁO KHOA HỌC

> **Chủ nhiệm:** Nhóm Nghiên cứu DS300 (Kiên, Khải, Phi và các thành viên)  
> **Phiên bản:** 2.0 (Role-Aware & Evidence-Grounded)  
> **Phạm vi áp dụng:** Toàn bộ quá trình trích xuất LLM (Exp A) và Gán nhãn Chuẩn vàng (Human Gold Set 600 bài).

---

## 1. NGUYÊN TẮC CỐT LÕI (CORE PRINCIPLES)

1. **Ràng buộc Dẫn chứng Nguyên văn (Verbatim Grounding Constraint):**
   * Chỉ trích xuất các khái niệm (concepts) xuất hiện **trực tiếp trong Tiêu đề (T0) hoặc Abstract (A0, A1, ...)** của bài báo.
   * Concept phải là cụm từ ngắn gọn, súc tích (từ **2 đến 6 từ**), xuất hiện nguyên văn trong câu bằng chứng.
   * Tuyệt đối không tự suy diễn hoặc dùng kiến thức bên ngoài văn bản.
2. **Quy tắc Thiếu Dữ liệu (Open-World / Null Value Rule):**
   * Nếu bài báo không đề cập đến một khía cạnh nào đó, bắt buộc để danh sách rỗng `[]`.
   * Tuyệt đối không cố điền thông tin để lấp đầy schema. Việc một bài báo để trống trường `dataset` là hoàn toàn bình thường trong văn phong khoa học.
3. **Phân định Vai trò Phương pháp (Role-Aware Method Principle):**
   * Tách bạch 100% giữa phương pháp do bài báo **đề xuất** (`proposed`) và phương pháp **đem ra so sánh** (`baseline`).

---

## 2. MA TRẬN PHÂN ĐỊNH 5 KHÍA CẠNH (FACET DISAMBIGUATION MATRIX)

| Facet | Bản chất & Câu hỏi Định hướng | Dấu hiệu Nhận diện Ngôn ngữ | Tiêu chí Bao hàm (Include) | Tiêu chí Loại trừ (Exclude) |
|---|---|---|---|---|
| **`problem`** | *Vấn đề/Hạn chế gì đang cản trở khoa học?* | *lack of, difficulty in, limitation of, sparse, bottleneck, challenge* | Thách thức vĩ mô, khoảng trống nghiên cứu, bẫy kỹ thuật của các mô hình cũ. | Không nhầm với `task` (nhiệm vụ thao tác) hoặc `dataset`. |
| **`task`** | *Hệ thống/Thuật toán làm thao tác kỹ thuật gì?* | *prediction, classification, ranking, recommendation, detection, extraction* | Nhiệm vụ toán học hoặc thao tác nghiệp vụ cụ thể có chuẩn đánh giá (input $\to$ output). | Không ghi chung chung là "nghiên cứu AI", không nhầm với `problem`. |
| **`method`** | *Kỹ thuật / Giải thuật nào được vận dụng?* | *we propose, our framework, based on, algorithm, neural network* | **`proposed`**: Kỹ thuật do bài báo đề xuất.<br>**`baseline`**: Mô hình đối chứng cũ đem ra so sánh. | Không trích xuất các kỹ thuật phụ trợ tầm thường (như "stochastic gradient descent"). |
| **`dataset`** | *Dữ liệu thực nghiệm có tên riêng là gì?* | *evaluated on, tested on, benchmark, dataset, corpus, collection* | **BẮT BUỘC là Danh từ Riêng có viết hoa hoặc viết tắt chuẩn** (ví dụ: *AMiner, DBLP, ImageNet, MovieLens-1M*). | **CẤM trích xuất cụm chung chung:** *"three real-world datasets"*, *"benchmark data"*, *"forum posts"* $\to$ Phải để `[]`. |
| **`contribution`** | *Tác giả khẳng định đóng góp mới mẻ gì?* | *experiments show, our findings, first framework, achieve state-of-the-art* | Tuyên bố đóng góp mới, phát hiện lý thuyết, kiến trúc mới hoặc bộ dữ liệu mới do nhóm công bố. | Không chép lại tên phương pháp đơn thuần; phải nêu rõ giá trị tạo ra. |

---

## 3. VÍ DỤ MINH HỌA PHÂN XỬ RANH GIỚI (CANONICAL EXAMPLES)

### Ví dụ 1: Bài báo về Xử lý Ngôn ngữ Tự nhiên
```text
T0: Deep contextualized word representations
A0: We introduce a new type of deep contextualized word representation that models both complex characteristics of word use, and how these uses vary across linguistic contexts.
A1: Our word vectors are functions of the internal states of a deep bidirectional language model (biLM), which is pre-trained on a large text corpus.
A2: We show that these representations can be easily added to existing models and significantly improve the state of the art across six challenging NLP problems, including question answering, textual entailment and sentiment analysis.
```

* **Gán nhãn chuẩn hóa:**
  ```json
  {
    "problem": ["complex characteristics of word use", "vary across linguistic contexts"],
    "task": ["question answering", "textual entailment", "sentiment analysis"],
    "method": {
      "proposed": ["deep contextualized word representation", "bidirectional language model"],
      "baseline": []
    },
    "dataset": [],
    "contribution": ["improve the state of the art", "functions of the internal states"]
  }
  ```
  *(Giải thích: Ở câu A1, "large text corpus" chỉ là mô tả chung chung, không có danh xưng riêng nên `dataset` là `[]`).*

---

### Ví dụ 2: Bài báo về Hệ thống Khuyến nghị (Tránh Bẫy Liệt kê Baseline)
```text
T0: Adaptive Collaborative Filtering for Recommendation
A0: Collaborative filtering methods often suffer from severe data sparsity and the cold-start problem.
A1: Unlike traditional matrix factorization and LightGCN which ignore high-order temporal dynamics, we propose a Fast-Slow Gated Network.
A2: Extensive experiments on the MovieLens-1M and Amazon-Book datasets demonstrate our method outperforms existing baselines by 12% in NDCG@10.
```

* **Gán nhãn chuẩn hóa:**
  ```json
  {
    "problem": ["data sparsity", "cold-start problem"],
    "task": ["collaborative filtering", "recommendation"],
    "method": {
      "proposed": ["Fast-Slow Gated Network"],
      "baseline": ["matrix factorization", "LightGCN"]
    },
    "dataset": ["MovieLens-1M", "Amazon-Book"],
    "contribution": ["outperforms existing baselines by 12% in NDCG@10"]
  }
  ```
  *(Giải thích: `matrix factorization` và `LightGCN` là baseline cũ bị bài báo chỉ trích/vượt qua, bắt buộc phải nằm ở mục `baseline`, không được gán vào `proposed`).*

---

## 4. QUY TRÌNH KIỂM SOÁT BẤT ĐỒNG (DISAGREEMENT ADJUDICATION)

1. **Khi 2 người gán nhãn lệch nhau giữa `problem` và `task`:**
   * Quy tắc: Nếu cụm từ nói về **sự thiếu thốn / hạn chế / thách thức** $\to$ `problem`. Nếu cụm từ nói về **hành động xử lý thông tin** $\to$ `task`.
2. **Khi lệch nhau giữa `method` và `contribution`:**
   * Quy tắc: Tên gọi của cơ chế / thuật toán $\to$ `method`. Câu khẳng định tính ưu việt hoặc kết quả đạt được $\to$ `contribution`.
3. **Khi một người ghi `dataset` còn người kia để trống `[]`:**
   * Quy tắc: Kiểm tra xem từ đó có phải tên riêng (Proper Noun) được cộng đồng thừa nhận hay không. Nếu chỉ là tên miêu tả tính chất dữ liệu $\to$ Chốt là `[]`.
