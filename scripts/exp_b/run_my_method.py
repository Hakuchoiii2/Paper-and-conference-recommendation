"""Exp B: Mô hình Semantic Embedding (Pretrained Transformer) so sánh với Baseline TF-IDF."""
import sys
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

# Thêm đường dẫn scripts vào hệ thống
PROJECT_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_SCRIPTS))

from baseline_common import ranked
from exp_b.run_exp_b import predict as baseline_predict
from experiment_io import FACETS
from experiment_runner import main

# Tải mô hình Pretrained SentenceTransformer (nhỏ gọn ~80MB, chạy nhanh trên CPU)
print("--> Đang khởi tạo mô hình ngôn ngữ 'all-MiniLM-L6-v2'...")
ENCODER = SentenceTransformer('all-MiniLM-L6-v2')


def predict(papers, facets, cases, history, options):
    # 1. Chạy 4 baseline cũ để lấy kết quả đối chứng: random, text_tfidf, equal_facets, weighted_facets
    predictions = baseline_predict(papers, facets, cases, history, options)

    # 2. Thu thập danh sách các bài báo xuất hiện trong tập kiểm thử (bài mốc + bài ứng viên)
    all_paper_ids = set()
    for case in cases:
        all_paper_ids.add(case['query_paper_id'])
        all_paper_ids.update(case['candidate_ids'])
    paper_list = sorted(all_paper_ids)
    paper_idx = {pid: idx for idx, pid in enumerate(paper_list)}

    print(f"--> Đang vector hóa ngữ nghĩa (Semantic Embedding) cho {len(paper_list)} bài báo...")

    # 3. Mã hóa toàn văn (Title + Abstract)
    whole_texts = [
        papers[pid]['title'] + '. ' + papers[pid]['abstract']
        for pid in paper_list
    ]
    # normalize_embeddings=True để chuẩn hóa L2, tích vô hướng (dot product) chính là Cosine Similarity
    whole_vectors = ENCODER.encode(whole_texts, normalize_embeddings=True, show_progress_bar=False)

    # 4. Mã hóa từng khía cạnh riêng biệt (Facet Embeddings)
    facet_vectors = {}
    for f in FACETS:
        f_texts = [
            ' '.join(sorted(facets[pid][f])) if (pid in facets and facets[pid][f]) else ''
            for pid in paper_list
        ]
        facet_vectors[f] = ENCODER.encode(f_texts, normalize_embeddings=True, show_progress_bar=False)

    weights = options.get('fixed_weights', {
        'problem': 0.4, 'task': 0.2, 'method': 0.2, 'dataset': 0.1, 'contribution': 0.1
    })

    # 5. Tính điểm tương đồng và xếp hạng cho từng query case
    for case in cases:
        q_pid = case['query_paper_id']
        q_idx = paper_idx[q_pid]
        cand_ids = case['candidate_ids']

        text_embed_scores = {}
        equal_embed_scores = {}
        weighted_embed_scores = {}

        for cand_pid in cand_ids:
            c_idx = paper_idx[cand_pid]

            # A. Điểm Cosine toàn văn ngữ nghĩa
            cos_whole = float(np.dot(whole_vectors[q_idx], whole_vectors[c_idx]))
            text_embed_scores[cand_pid] = cos_whole

            # B. Điểm Cosine từng Facet ngữ nghĩa
            facet_sims = {}
            for f in FACETS:
                q_has = bool(facets.get(q_pid, {}).get(f))
                c_has = bool(facets.get(cand_pid, {}).get(f))

                # Chỉ tính độ tương đồng nếu cả hai bài đều có thông tin ở khía cạnh này
                if q_has and c_has:
                    facet_sims[f] = float(np.dot(facet_vectors[f][q_idx], facet_vectors[f][c_idx]))
                else:
                    facet_sims[f] = 0.0

            # C. Chia đều trọng số 5 facet
            equal_embed_scores[cand_pid] = sum(facet_sims.values()) / len(FACETS)

            # D. Nhân với bộ trọng số 5 facet
            weighted_embed_scores[cand_pid] = sum(weights[f] * facet_sims[f] for f in FACETS)

        # 6. Đưa 3 mô hình ngữ nghĩa mới vào bảng xếp hạng
        predictions.append(ranked(case, 'text_embedding', text_embed_scores))
        predictions.append(ranked(case, 'equal_facet_embedding', equal_embed_scores))
        predictions.append(ranked(case, 'weighted_facet_embedding', weighted_embed_scores))

    return predictions


if __name__ == '__main__':
    main('b', predict)