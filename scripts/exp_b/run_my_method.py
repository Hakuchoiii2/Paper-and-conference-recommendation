"""Exp B: Scorer chuẩn hóa theo Mục 6.3 của Paper mới (Hỗ trợ Missing Facet & Fallback)."""
import sys
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

PROJECT_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_SCRIPTS))

from baseline_common import ranked
from exp_b.run_exp_b import predict as baseline_predict
from experiment_io import FACETS
from experiment_runner import main

print("--> Đang khởi tạo mô hình ngôn ngữ 'all-MiniLM-L6-v2'...")
ENCODER = SentenceTransformer('all-MiniLM-L6-v2')


def predict(papers, facets, cases, history, options):
    # 1. Chạy lấy kết quả baseline cũ đối chứng
    predictions = baseline_predict(papers, facets, cases, history, options)

    # 2. Gom danh sách các bài báo trong tập test
    all_paper_ids = set()
    for case in cases:
        all_paper_ids.add(case['query_paper_id'])
        all_paper_ids.update(case['candidate_ids'])
    paper_list = sorted(all_paper_ids)
    paper_idx = {pid: idx for idx, pid in enumerate(paper_list)}

    print(f"--> Đang vector hóa {len(paper_list)} bài báo...")

    # 3. Mã hóa toàn văn (Title + Abstract)
    whole_texts = [
        papers[pid]['title'] + '. ' + papers[pid]['abstract']
        for pid in paper_list
    ]
    whole_vectors = ENCODER.encode(whole_texts, normalize_embeddings=True, show_progress_bar=False)

    # 4. Mã hóa từng Facet riêng biệt
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

    # 5. Chấm điểm theo công thức chuẩn hóa Mục 6.3
    for case in cases:
        q_pid = case['query_paper_id']
        q_idx = paper_idx[q_pid]
        cand_ids = case['candidate_ids']

        text_embed_scores = {}
        equal_embed_scores = {}
        weighted_embed_scores = {}

        for cand_pid in cand_ids:
            c_idx = paper_idx[cand_pid]

            # A. Cosine toàn văn
            cos_whole = float(np.dot(whole_vectors[q_idx], whole_vectors[c_idx]))
            text_embed_scores[cand_pid] = cos_whole

            # B. Cosine từng Facet & Mặt nạ m_f(q, d)
            facet_sims = {}
            active_facets = []
            for f in FACETS:
                q_has = bool(facets.get(q_pid, {}).get(f))
                c_has = bool(facets.get(cand_pid, {}).get(f))

                if q_has and c_has:
                    facet_sims[f] = float(np.dot(facet_vectors[f][q_idx], facet_vectors[f][c_idx]))
                    active_facets.append(f)
                else:
                    facet_sims[f] = 0.0

            # C. Chuẩn hóa mẫu số theo Mục 6.3: S_w(q, d) = sum(w_f * s_f) / sum(w_f)
            if active_facets:
                # Equal: chia đều các facet có mặt
                equal_embed_scores[cand_pid] = sum(facet_sims[f] for f in active_facets) / len(active_facets)

                # Weighted: chia cho tổng trọng số của các facet có mặt
                weighted_sum = sum(weights[f] * facet_sims[f] for f in active_facets)
                total_active_weight = sum(weights[f] for f in active_facets)
                weighted_embed_scores[cand_pid] = weighted_sum / total_active_weight
            else:
                # Fallback toàn văn nếu cả 5 facet đều không so sánh được (Mục 6.3)
                equal_embed_scores[cand_pid] = cos_whole
                weighted_embed_scores[cand_pid] = cos_whole

        # 6. Đưa vào danh sách dự đoán
        predictions.append(ranked(case, 'text_embedding', text_embed_scores))
        predictions.append(ranked(case, 'equal_facet_embedding', equal_embed_scores))
        predictions.append(ranked(case, 'weighted_facet_embedding', weighted_embed_scores))

    return predictions


if __name__ == '__main__':
    main('b', predict)