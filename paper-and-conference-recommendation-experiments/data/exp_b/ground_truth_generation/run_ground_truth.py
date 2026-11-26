"""Build the EXP-B initial candidate pool and the shared query split."""

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import random

import numpy as np

ROOT = Path(__file__).resolve().parent
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
FACETS = ("problem", "task", "method", "dataset", "contribution")
CORE = FACETS[:3]
SEED = 42


def write_rows(path, rows):
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def write_report(path, report):
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_papers(path):
    loaded = []
    invalid = []
    with path.open(encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, 1):
            try:
                row = json.loads(line)
                paper_id = row["paper_id"]
                facets = row["facets"]
                if not isinstance(paper_id, str) or not paper_id.strip():
                    raise ValueError("Missing paper ID")
                if not isinstance(facets, dict) or any(
                    not isinstance(facets.get(facet), str) for facet in FACETS
                ):
                    raise ValueError("Expected five string facets")
                if any(not isinstance(row.get(key, ""), str) for key in ("title", "abstract")):
                    raise ValueError("Invalid title or abstract type")
                loaded.append((line_number, {
                    "paper_id": paper_id.strip(),
                    "title": row.get("title", "").strip(),
                    "abstract": row.get("abstract", "").strip(),
                    "facets": {facet: " ".join(facets[facet].split()) for facet in FACETS},
                }))
            except (ValueError, KeyError, TypeError) as error:
                invalid.append({"line": line_number, "reason": str(error)})
    ids = Counter(row["paper_id"] for _, row in loaded)
    papers = []
    for line_number, row in loaded:
        if ids[row["paper_id"]] == 1:
            papers.append(row)
        else:
            invalid.append({"line": line_number, "paper_id": row["paper_id"], "reason": "Duplicate ID"})
    return sorted(papers, key=lambda row: row["paper_id"]), invalid


def encode_facets(corpus, directory, revision):
    from sentence_transformers import SentenceTransformer

    metadata = {
        "model": MODEL,
        "model_revision": revision,
        "sentence_transformers_version": importlib.metadata.version("sentence-transformers"),
        "normalization": "L2",
        "paper_ids": [row["paper_id"] for row in corpus],
        "content_sha256": {},
    }
    model = None
    matrices = {}
    for facet in FACETS:
        texts = [row["facets"][facet] for row in corpus]
        metadata["content_sha256"][facet] = [hashlib.sha256(t.encode()).hexdigest() for t in texts]
        key = hashlib.sha256(json.dumps([MODEL, revision, metadata["sentence_transformers_version"],
                                         facet, metadata["content_sha256"][facet]]).encode()).hexdigest()
        folder = directory / facet
        folder.mkdir(exist_ok=True)
        path = folder / f"{key}.npy"
        if path.exists():
            matrices[facet] = np.load(path, allow_pickle=False)
            continue
        if model is None:
            import torch
            torch.set_num_threads(min(6, torch.get_num_threads()))
            model = SentenceTransformer(MODEL, revision=revision, local_files_only=True)
        present = [i for i, value in enumerate(texts) if value]
        vectors = np.zeros((len(corpus), model.get_sentence_embedding_dimension()), dtype=np.float32)
        if present:
            unique = list(dict.fromkeys(texts[i] for i in present))
            print(f"Encoding {facet}: {len(unique)} unique texts", flush=True)
            encoded = model.encode(unique, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
            positions = {value: index for index, value in enumerate(unique)}
            vectors[present] = encoded[[positions[texts[i]] for i in present]]
        np.save(path, vectors)
        matrices[facet] = vectors
    metadata["embedding_dimension"] = next(iter(matrices.values())).shape[1]
    write_report(directory / "embedding_metadata.json", metadata)
    return matrices


def select_queries(eligible, similarity):
    rng = random.Random(SEED)
    order = list(range(len(eligible)))
    rng.shuffle(order)
    strata = defaultdict(list)
    for index in order:
        strata[sum(bool(eligible[index]["facets"][facet]) for facet in FACETS)].append(index)
    targets = [count for count in sorted(strata) if strata[count]]
    selected = []
    max_similarity = np.full(len(eligible), -1.0)
    used_titles = set()
    used_problems = set()
    while len(selected) < 50:
        target = targets[len(selected) % len(targets)]
        available = [
            i for i in order if max_similarity[i] < 0.75
            and eligible[i]["title"].casefold() not in used_titles
            and eligible[i]["facets"]["problem"].casefold() not in used_problems
        ]
        if not available:
            raise ValueError("Fewer than 50 diverse queries at the 0.75 threshold")
        preferred = [i for i in available if i in strata[target]]
        index = min(preferred or available, key=lambda i: max_similarity[i])
        selected.append(index)
        if eligible[index]["title"]:
            used_titles.add(eligible[index]["title"].casefold())
        used_problems.add(eligible[index]["facets"]["problem"].casefold())
        max_similarity = np.maximum(max_similarity, similarity[index])
        max_similarity[index] = 1
    return selected


def group_candidates(scored, query_facets, rng):
    ordered = sorted(scored, key=lambda row: (-row["overall_similarity"], row["candidate_id"]))
    priority = [row for row in ordered if len(row["shared_facets"]) >= 2]
    fallback = [row for row in ordered if len(row["shared_facets"]) == 1]
    overall = (priority + fallback)[:60]
    used = {row["candidate_id"] for row in overall}
    per_facet = {
        facet: iter(sorted((row for row in scored if facet in row["facet_similarities"]),
                           key=lambda row: (-row["facet_similarities"][facet], row["candidate_id"])))
        for facet in query_facets
    }
    focused = []
    while len(focused) < 20:
        previous = len(focused)
        for facet, candidates in per_facet.items():
            for row in candidates:
                if row["candidate_id"] not in used:
                    focused.append(dict(row, retrieval_facet=facet))
                    used.add(row["candidate_id"])
                    break
            if len(focused) == 20:
                break
        if len(focused) == previous:
            raise ValueError("Insufficient facet candidates")
    remaining = [row for row in reversed(ordered) if row["candidate_id"] not in used]
    middle = [
        dict(row, similarity_percentile=100 * index / max(1, len(remaining) - 1))
        for index, row in enumerate(remaining)
        if 0.60 <= index / max(1, len(remaining) - 1) <= 0.80
    ]
    medium = sorted(rng.sample(middle, 20), key=lambda row: (-row["overall_similarity"], row["candidate_id"]))
    for group, rows, method, expected in (
        ("A", overall, "top60_overall", 60),
        ("B", focused, "top20_facet", 20),
        ("C", medium, "top20_medium", 20),
    ):
        if len(rows) != expected:
            raise ValueError(f"Incorrect number of candidates in group {group}")
        for rank, row in enumerate(rows, 1):
            yield dict(row, candidate_group=group, rank_in_group=rank, retrieval_method=method)


def score_candidates(query_index, corpus, matrices, present):
    query = corpus[query_index]
    scores = {facet: np.clip(matrix @ matrix[query_index], -1, 1)
              for facet, matrix in matrices.items() if query["facets"][facet]}
    rows = []
    for index, candidate in enumerate(corpus):
        if index == query_index:
            continue
        shared = {facet: float(values[index]) for facet, values in scores.items()
                  if present[facet][index]}
        if shared:
            rows.append({
                "query_id": query["paper_id"],
                "candidate_id": candidate["paper_id"],
                "shared_facets": list(shared),
                "facet_similarities": shared,
                "overall_similarity": sum(shared.values()) / len(shared),
            })
    return rows


def main():
    from huggingface_hub import snapshot_download

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT.parent / "data_preparation/output/validated_silver.jsonl")
    parser.add_argument("--destination", type=Path, default=ROOT)
    args = parser.parse_args()
    output = args.destination / "output"
    intermediate = args.destination / "intermediate"
    reports = args.destination / "evaluation"
    review = args.destination / "human_review"
    judgments_path = review / "human_judgments.jsonl"
    if judgments_path.exists() and judgments_path.stat().st_size:
        raise ValueError("Judgments already exist. Build to a fresh --destination to preserve the judged split.")
    for directory in (output, intermediate, reports, review):
        directory.mkdir(parents=True, exist_ok=True)
    papers, invalid = load_papers(args.input)
    corpus = [row for row in papers if any(row["facets"].values())]
    excluded = [{"paper_id": row["paper_id"], "reason": "No facet content"}
                for row in papers if not any(row["facets"].values())]
    eligible = [row for row in corpus if all(row["facets"][facet] for facet in CORE)
                and sum(map(bool, row["facets"].values())) >= 4]
    missing_metadata = {key: sum(not row[key] for row in papers) for key in ("title", "abstract")}
    write_report(reports / "data_validation_report.json", {
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "valid_structure": len(papers), "invalid_records": len(invalid),
        "empty_metadata": missing_metadata,
        "metadata_policy": "Missing title/abstract allowed for facet-only mode; no other dataset read.",
        "blank_facets": {facet: sum(not row["facets"][facet] for row in papers) for facet in FACETS},
    })
    write_report(reports / "candidate_corpus_report.json", {
        "eligible": len(corpus), "invalid_records": len(invalid), "no_facet_content": len(excluded),
        "nonempty_facet_counts": dict(Counter(sum(map(bool, row["facets"].values())) for row in corpus)),
    })
    write_rows(intermediate / "validated_silver_loaded.jsonl", papers)
    write_rows(intermediate / "eligible_papers.jsonl", papers)
    write_rows(intermediate / "invalid_records.jsonl", invalid)
    write_rows(intermediate / "candidate_excluded.jsonl", invalid + excluded)
    write_rows(intermediate / "eligible_queries.jsonl", eligible)
    write_rows(intermediate / "candidate_corpus.jsonl", corpus)
    print(f"{len(eligible)} eligible queries and {len(corpus)} eligible candidates", flush=True)
    if len(eligible) < 50 or len(corpus) < 101:
        raise ValueError("Insufficient eligible papers")
    embedding_dir = intermediate / "facet_embeddings"
    embedding_dir.mkdir(exist_ok=True)
    revision = Path(snapshot_download(MODEL, local_files_only=True)).name
    matrices = encode_facets(corpus, embedding_dir, revision)
    indices = {row["paper_id"]: index for index, row in enumerate(corpus)}
    positions = [indices[row["paper_id"]] for row in eligible]
    similarity = np.zeros((len(eligible), len(eligible)), dtype=np.float32)
    query_dir = intermediate / "query_embeddings"
    query_dir.mkdir(exist_ok=True)
    for facet, weight in zip(CORE, (0.4, 0.3, 0.3)):
        vectors = matrices[facet][positions]
        np.save(query_dir / f"{facet}.npy", vectors)
        similarity += weight * (vectors @ vectors.T)
    np.clip(similarity, -1, 1, out=similarity)
    np.save(intermediate / "query_similarity_matrix.npy", similarity)
    write_rows(intermediate / "query_similarity_pairs.jsonl", (
        {"query_id": eligible[i]["paper_id"], "other_query_id": eligible[j]["paper_id"],
         "concept_similarity": float(similarity[i, j])}
        for i, j in zip(*np.where(np.triu(similarity >= 0.75, k=1)))
    ))
    selected = select_queries(eligible, similarity)
    split_order = selected.copy()
    random.Random(SEED).shuffle(split_order)
    split = {"dev": [eligible[i]["paper_id"] for i in split_order[:15]],
             "test": [eligible[i]["paper_id"] for i in split_order[15:]], "random_seed": SEED}
    query_split = {paper_id: name for name in ("dev", "test") for paper_id in split[name]}
    queries = [dict(eligible[i], split=query_split[eligible[i]["paper_id"]]) for i in selected]
    selected_scores = similarity[np.ix_(selected, selected)]
    max_selected = float(np.max(selected_scores[np.triu_indices(50, 1)]))
    write_report(reports / "query_selection_report.json", {
        "eligible_queries": len(eligible), "selected_queries": len(queries), "dev": 15, "test": 35,
        "max_selected_concept_similarity": max_selected, "threshold_exclusive": 0.75,
        "stratification": "Alternating by 4 vs 5 populated facets with greedy minimum maximum similarity",
        "selected_facet_counts": dict(Counter(sum(map(bool, row["facets"].values())) for row in queries)),
    })
    write_rows(output / "selected_queries.jsonl", queries)
    write_report(output / "query_split.json", split)
    write_rows(output / "ranking_input.jsonl", corpus)

    pairs = []
    present = {facet: [bool(row["facets"][facet]) for row in corpus] for facet in FACETS}
    with (intermediate / "facet_similarity_results.jsonl").open("w", encoding="utf-8") as similarity_file:
        for query in queries:
            query_id = query["paper_id"]
            scored = score_candidates(indices[query_id], corpus, matrices, present)
            overall_order = sorted(scored, key=lambda row: (-row["overall_similarity"], row["candidate_id"]))
            for rank, row in enumerate(overall_order, 1):
                row["overall_rank"] = rank
                similarity_file.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            query_facets = [facet for facet in FACETS if query["facets"][facet]]
            pairs.extend(dict(row, split=query["split"], model=MODEL)
                         for row in group_candidates(scored, query_facets, random.Random(f"{SEED}:{query_id}")))
    pair_ids = {(row["query_id"], row["candidate_id"]) for row in pairs}
    if len(pairs) != 5000 or len(pair_ids) != 5000:
        raise ValueError("Expected precisely 5,000 distinct query-candidate pairs")
    write_rows(output / "ground_truth_candidates.jsonl", pairs)
    by_query = defaultdict(list)
    for row in pairs:
        candidates = by_query[row["query_id"]]
        candidates.append({
            "candidate_id": row["candidate_id"],
            "rank": len(candidates) + 1,
            "score": row["overall_similarity"],
        })
    write_rows(output / "pooling_input.jsonl", (
        {"query_id": query_id, "source": "ground_truth_generation", "candidates": candidates}
        for query_id, candidates in by_query.items()
    ))
    for group, name in (("A", "top60_overall"), ("B", "top20_facet"), ("C", "top20_medium")):
        write_rows(intermediate / f"{name}.jsonl", (row for row in pairs if row["candidate_group"] == group))
    write_report(reports / "candidate_generation_report.json", {
        "query_count": len(queries), "pairs": len(pairs), "eligible_corpus": len(corpus),
        "group_counts": dict(Counter(row["candidate_group"] for row in pairs)),
        "medium_percentile_reference": "Remaining eligible candidates after groups A and B",
        "model": MODEL, "revision": revision,
    })

    review_rows = defaultdict(list)
    for row in pairs:
        qid, cid = row["query_id"], row["candidate_id"]
        review_rows[qid].append({
            "pair_id": f"{qid}:{cid}", "query_id": qid, "candidate_id": cid, "split": row["split"],
            "query": corpus[indices[qid]], "candidate": corpus[indices[cid]],
        })
    query_reviews = output / "review_by_query"
    query_reviews.mkdir(exist_ok=True)
    for query_id, rows in review_rows.items():
        rows.sort(key=lambda row: row["candidate_id"])
        write_rows(query_reviews / f"{query_id}.jsonl", rows)
    write_rows(output / "human_review_queue.jsonl", (row for rows in review_rows.values() for row in rows))
    for name in ("human_judgments.jsonl", "initial_human_qrels.jsonl"):
        (review / name).touch(exist_ok=True)
    write_report(review / "review_progress.json", {"pairs": len(pairs), "graded": 0, "pending": len(pairs)})
    write_report(reports / "ground_truth_quality_report.json", {
        "queries": len(queries), "candidate_pairs": len(pairs), "judged_pairs": 0,
        "max_selected_concept_similarity": max_selected, "missing_metadata": missing_metadata,
        "facet_status_filter_used": False,
        "limitation": "Some nonempty facets may still be pending review. Final qrels require human judgments and pooling.",
    })
    print(f"Saved {len(queries)} queries and {len(pairs)} candidate pairs to {output}", flush=True)


if __name__ == "__main__":
    main()
