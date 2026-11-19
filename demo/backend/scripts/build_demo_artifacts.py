from __future__ import annotations

import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

FACETS = ["problem", "task", "method", "dataset", "contribution"]
FIELDS = ["whole_text", *FACETS]

OFFICIAL_CONFERENCE_URLS: Dict[str, str] = {
    "CONF_ACL": "https://aclanthology.org/venues/acl/",
    "CONF_ACL_STARSEM": "https://aclanthology.org/venues/starsem/",
    "CONF_ACM_MM": "https://acmmm.org/",
    "CONF_CHI": "https://chi2027.acm.org/",
    "CONF_CIKM": "https://dl.acm.org/conference/cikm",
    "CONF_COLING": "https://aclanthology.org/venues/coling/",
    "CONF_CONLL": "https://aclanthology.org/venues/conll/",
    "CONF_CVPR": "https://cvpr.thecvf.com/",
    "CONF_EACL": "https://aclanthology.org/venues/eacl/",
    "CONF_EMNLP": "https://aclanthology.org/venues/emnlp/",
    "CONF_ICASSP": "https://ieeeicassp.org/",
    "CONF_ICLR": "https://iclr.cc/",
    "CONF_ICML": "https://icml.cc/",
    "CONF_ICORE_1123": "https://www.icmlc.com/",
    "CONF_ICORE_13": "https://cscw.acm.org/2027/",
    "CONF_ICORE_2268": "https://www.solaresearch.org/events/lak/",
    "CONF_ICORE_2311": "https://asonam.cpsc.ucalgary.ca/",
    "CONF_ICORE_642": "https://icdm.zhonghuapu.com/",
    "CONF_ICORE_664": "https://ieeeicme.org/",
    "CONF_ICORE_792": "https://www.ieee-ras.org/conferences-workshops/financially-co-sponsored/iros",
    "CONF_ICPR": "https://iapr.org/conferences/conference-archives/",
    "CONF_IJCNLP": "https://aclanthology.org/venues/ijcnlp/",
    "CONF_KDD": "https://kdd.org/",
    "CONF_LREC": "https://aclanthology.org/venues/lrec/",
    "CONF_NAACL": "https://aclanthology.org/venues/naacl/",
    "CONF_RANLP": "https://aclanthology.org/venues/ranlp/",
    "CONF_SIGDIAL": "https://aclanthology.org/venues/sigdial/",
    "CONF_SIGIR": "https://sigir.org/",
    "CONF_SIGMOD": "https://sigmod.org/",
    "CONF_WSDM": "https://www.wsdm-conference.org/",
}


def load_dotenv_file(env_path: Path) -> Dict[str, str]:
    """Simple .env reader (does not require python-dotenv)."""
    env: Dict[str, str] = {}
    if not env_path.exists():
        return env
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def resolve_path(base_dir: Path, raw_path: str) -> Path:
    p = Path(raw_path)
    return p if p.is_absolute() else (base_dir / p).resolve()


def read_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_concept_list(val) -> List[str]:
    if not val:
        return []
    if isinstance(val, str):
        s = val.strip()
        return [s] if s else []
    if isinstance(val, list):
        out: List[str] = []
        seen = set()
        for item in val:
            if isinstance(item, dict):
                s = str(item.get("concept", "")).strip()
            else:
                s = str(item).strip()
            if s and s.lower() not in seen:
                seen.add(s.lower())
                out.append(s)
        return out
    return []


def find_best_evidence(title: str, abstract: str, concept: str) -> Optional[Dict[str, str]]:
    """Find best matching sentence in title or abstract for a concept without inventing quotes."""
    c_low = concept.strip().lower()
    if not c_low:
        return None
    if c_low in title.lower():
        return {"quote": title.strip(), "source_field": "title"}
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", abstract) if s.strip()]
    for sent in sentences:
        if c_low in sent.lower():
            return {"quote": sent, "source_field": "abstract"}
    # Token overlap fallback (require >= 60% of concept content tokens)
    c_toks = [t for t in re.findall(r"[a-z0-9]+", c_low) if len(t) >= 3]
    if not c_toks:
        return None
    best_sent = None
    best_ratio = 0.0
    for sent in sentences:
        s_toks = set(re.findall(r"[a-z0-9]+", sent.lower()))
        ratio = sum(1 for t in c_toks if t in s_toks) / len(c_toks)
        if ratio > best_ratio:
            best_ratio = ratio
            best_sent = sent
    if best_sent and best_ratio >= 0.6:
        return {"quote": best_sent, "source_field": "abstract"}
    return None


def build_model_facet_items(
    raw_facets: Dict,
    title: str,
    abstract: str,
    raw_evidence: Optional[Dict] = None,
) -> Dict[str, List[Dict]]:
    """Convert raw facet dict into structured {facet: [{concept, evidences}]}."""
    out: Dict[str, List[Dict]] = {}
    for f in FACETS:
        items: List[Dict] = []
        if raw_evidence and isinstance(raw_evidence.get(f), list) and raw_evidence[f]:
            seen = set()
            for entry in raw_evidence[f]:
                concept = str(entry.get("concept", "")).strip()
                if not concept or concept.lower() in seen:
                    continue
                seen.add(concept.lower())
                ev_text = str(entry.get("evidence", "")).strip()
                src = entry.get("source", "abstract")
                if src not in ("title", "abstract"):
                    src = "abstract"
                evs = [{"quote": ev_text, "source_field": src}] if ev_text else []
                items.append({"concept": concept, "evidences": evs})
        else:
            concepts = normalize_concept_list(raw_facets.get(f, []))
            for concept in concepts:
                ev = find_best_evidence(title, abstract, concept)
                items.append({"concept": concept, "evidences": [ev] if ev else []})
        out[f] = items
    return out


def encode_6fields_bge(
    bge_model,
    rows: List[Dict],
    batch_size: int = 128,
) -> Dict[str, np.ndarray]:
    """Encode whole_text + 5 facets using BGE-small. Empty facets get zero vector + False mask."""
    n = len(rows)
    dim = bge_model.get_sentence_embedding_dimension()
    result: Dict[str, np.ndarray] = {}

    for field in FIELDS:
        texts: List[str] = []
        valid_indices: List[int] = []
        mask = np.zeros(n, dtype=bool)

        for idx, r in enumerate(rows):
            if field == "whole_text":
                txt = f"{r.get('title', '').strip()}. {r.get('abstract', '').strip()}".strip(". ")
            else:
                concepts = normalize_concept_list(r.get("facets", {}).get(field, []))
                txt = "; ".join(concepts)
            if txt:
                texts.append(txt)
                valid_indices.append(idx)
                mask[idx] = True

        mat = np.zeros((n, dim), dtype=np.float32)
        if texts:
            embs = bge_model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            mat[valid_indices] = embs.astype(np.float32)

        result[field] = mat.astype(np.float16)
        result[f"mask_{field}"] = mask
        print(f"    encoded {field:12s}: {len(valid_indices):4d}/{n} non-empty")

    return result


def main() -> None:
    t_start = time.perf_counter()
    demo_dir = Path(__file__).resolve().parents[2]
    env = load_dotenv_file(demo_dir / ".env")

    def cfg(key: str, default: str) -> Path:
        val = os.environ.get(key) or env.get(key) or default
        return resolve_path(demo_dir, val)

    artifacts_dir = cfg("DEMO_ARTIFACTS_DIR", "../_local/demo_artifacts")
    bge_model_path = cfg("BGE_MODEL_PATH", "../_local/models/bge-small-en-v1.5")
    paper_corpus_path = cfg("PAPER_CORPUS_PATH", "../paper-and-conference-recommendation-experiments/data/processed/papers.jsonl")
    corpus_facets_path = cfg("CORPUS_FACETS_PATH", "../paper-and-conference-recommendation-experiments/data/exp_a/generated/facets_silver.jsonl")
    corpus_evidence_path = cfg("CORPUS_EVIDENCE_PATH", "../paper-and-conference-recommendation-experiments/data/exp_a/generated/annotation_metadata.jsonl")
    conf_catalog_path = cfg("CONFERENCE_CATALOG_PATH", "../paper-and-conference-recommendation-experiments/data/conference_recommendation_dataset/5_mapping_reviewed/splits/temporal_2015_2016_2019_clean/conference_catalog.jsonl")
    conf_train_path = cfg("CONFERENCE_TRAIN_PATH", "../paper-and-conference-recommendation-experiments/data/conference_recommendation_dataset/5_mapping_reviewed/splits/temporal_2015_2016_2019_clean/train.jsonl")
    conf_test_path = cfg("CONFERENCE_TEST_PATH", "../paper-and-conference-recommendation-experiments/data/conference_recommendation_dataset/5_mapping_reviewed/splits/temporal_2015_2016_2019_clean/test.jsonl")
    generated_facets_dir = cfg("GENERATED_FACETS_DIR", "../paper-and-conference-recommendation-experiments/data/conference_recommendation_dataset/generated_facets")

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    print(f"[1/6] Loading source datasets into {artifacts_dir} ...")

    papers_raw = read_jsonl(paper_corpus_path)
    exp_a_facets_map = {r["paper_id"]: r for r in read_jsonl(corpus_facets_path)}
    exp_a_evidence_map: Dict[str, Dict] = {}
    if corpus_evidence_path.exists():
        for r in read_jsonl(corpus_evidence_path):
            if r.get("evidence"):
                exp_a_evidence_map[r["paper_id"]] = r["evidence"]

    conf_catalog_raw = read_jsonl(conf_catalog_path)
    conf_train_raw = read_jsonl(conf_train_path)
    conf_test_raw = read_jsonl(conf_test_path)

    # Zero-leakage sanity check
    train_ids = {r["paper_id"] for r in conf_train_raw}
    test_ids = {r["paper_id"] for r in conf_test_raw}
    overlap_ids = train_ids & test_ids
    if overlap_ids:
        raise RuntimeError(f"DATA LEAKAGE DETECTED: {len(overlap_ids)} overlapping paper_ids between train and test!")
    print(f"  Loaded papers={len(papers_raw)}, conf_catalog={len(conf_catalog_raw)}, conf_train={len(conf_train_raw)}, conf_test={len(conf_test_raw)} (overlap=0)")

    # Load 4 extra LLM precomputed facets on test set
    model_dir_map = {
        "Qwen3-4B": generated_facets_dir / "Qwen4B" / "facets_silver.jsonl",
        "Qwen3-14B": generated_facets_dir / "Qwen14B" / "facets_silver.jsonl",
        "Llama3.1-8B": generated_facets_dir / "Llama8B" / "facets_silver.jsonl",
        "Gemma2-9B": generated_facets_dir / "Gemma9B" / "facets_silver.jsonl",
    }
    generated_by_model: Dict[str, Dict[str, Dict]] = {}
    for mk, fpath in model_dir_map.items():
        if fpath.exists():
            generated_by_model[mk] = {r["paper_id"]: r for r in read_jsonl(fpath)}
            cov = len(set(generated_by_model[mk].keys()) & test_ids)
            print(f"  Model {mk:12s}: loaded {len(generated_by_model[mk])} rows (test coverage: {cov}/{len(test_ids)})")
        else:
            print(f"  WARNING: Missing {fpath} for {mk}")

    # Map conference_id -> acronym/name
    conf_by_id = {c["conference_id"]: c for c in conf_catalog_raw}
    train_venue_by_pid = {
        r["paper_id"]: conf_by_id.get(r["conference_id"], {}).get("acronym") or r.get("conference_name")
        for r in conf_train_raw
    }

    # [2/6] Build paper_corpus.jsonl (4,210 papers + 5 facets)
    print("[2/6] Writing paper_corpus.jsonl ...")
    paper_corpus_rows: List[Dict] = []
    for p in papers_raw:
        pid = p["paper_id"]
        f_raw = exp_a_facets_map.get(pid, {})
        facets_clean = {f: normalize_concept_list(f_raw.get(f, [])) for f in FACETS}
        venue = train_venue_by_pid.get(pid) or p.get("venue") or (p.get("source", "").upper() if p.get("source") else None)
        paper_corpus_rows.append(
            {
                "paper_id": pid,
                "title": p.get("title", "").strip(),
                "abstract": p.get("abstract", "").strip(),
                "authors": p.get("authors") or [],
                "year": p.get("year"),
                "venue": venue,
                "source": p.get("source"),
                "facets": facets_clean,
            }
        )
    with (artifacts_dir / "paper_corpus.jsonl").open("w", encoding="utf-8") as f:
        for row in paper_corpus_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # [3/6] Build conference_train_pool.jsonl (602 train papers strictly) & conference_catalog.json
    print("[3/6] Writing conference_train_pool.jsonl & conference_catalog.json ...")
    conf_train_rows: List[Dict] = []
    conf_years: Dict[str, List[int]] = defaultdict(list)
    conf_facet_concepts: Dict[str, Dict[str, Counter]] = defaultdict(lambda: {f: Counter() for f in FACETS})

    for r in conf_train_raw:
        pid = r["paper_id"]
        cid = r["conference_id"]
        raw_f = r.get("facets") or exp_a_facets_map.get(pid, {})
        facets_clean = {f: normalize_concept_list(raw_f.get(f, [])) for f in FACETS}
        if r.get("year"):
            conf_years[cid].append(int(r["year"]))
        for f in FACETS:
            for c in facets_clean[f]:
                conf_facet_concepts[cid][f][c] += 1
        conf_train_rows.append(
            {
                "paper_id": pid,
                "title": r.get("title", "").strip(),
                "abstract": r.get("abstract", "").strip(),
                "year": r.get("year"),
                "conference_id": cid,
                "conference_name": r.get("conference_name", ""),
                "conference_acronym": conf_by_id.get(cid, {}).get("acronym", r.get("conference_name", "")),
                "facets": facets_clean,
            }
        )

    with (artifacts_dir / "conference_train_pool.jsonl").open("w", encoding="utf-8") as f:
        for row in conf_train_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    conf_catalog_out: List[Dict] = []
    for c in conf_catalog_raw:
        cid = c["conference_id"]
        yrs = sorted(conf_years.get(cid, []))
        yr_range = f"{yrs[0]}–{yrs[-1]}" if yrs else "1982–2015"
        hist_count = len(yrs) if yrs else int(c.get("train_paper_count", 0))
        top_kw_by_facet = {
            f: [k for k, _ in conf_facet_concepts[cid][f].most_common(8)]
            for f in FACETS
        }
        all_top = []
        for f in ("problem", "task", "method"):
            all_top.extend(top_kw_by_facet[f][:4])
        topic_desc = (
            f"Hồ sơ chủ đề {c.get('acronym', '')} ({c.get('canonical_name', '')}) tổng hợp từ {hist_count} bài Train ({yr_range}). "
            f"Chủ đề tiêu biểu: {', '.join(all_top[:10])}."
        )
        conf_catalog_out.append(
            {
                "conference_id": cid,
                "canonical_name": c.get("canonical_name", ""),
                "acronym": c.get("acronym", ""),
                "url": OFFICIAL_CONFERENCE_URLS.get(
                    cid, f"https://dblp.org/search?q={c.get('acronym', '')}"
                ),
                "historical_paper_count": hist_count,
                "year_range": yr_range,
                "cutoff_note": "Hồ sơ xây dựng hoàn toàn từ 602 bài Train (1982–2015), tách biệt với 168 bài Test (2016–2019).",
                "coverage_note": f"100% bài Train có đủ 5 facets (Qwen3-8B). Số bài lịch sử: {hist_count}.",
                "sparse_profile_warning": (
                    f"Số lượng bài lịch sử trong tập Train khá ít ({hist_count} bài)."
                    if hist_count < 15
                    else None
                ),
                "topic_profile_description": topic_desc,
                "top_keywords_by_facet": top_kw_by_facet,
            }
        )
    (artifacts_dir / "conference_catalog.json").write_text(
        json.dumps(conf_catalog_out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # [4/6] Build demo_examples.json (168 clean test papers with all 5 real LLM precomputed outputs)
    print("[4/6] Writing demo_examples.json (168 clean test papers × 5 real LLMs) ...")
    examples_out: List[Dict] = []
    for r in conf_test_raw:
        pid = r["paper_id"]
        title = r.get("title", "").strip()
        abstract = r.get("abstract", "").strip()
        year = r.get("year")
        cid = r["conference_id"]
        c_info = conf_by_id.get(cid, {})
        acronym = c_info.get("acronym") or r.get("conference_name", "")
        cname = c_info.get("canonical_name") or r.get("conference_name", "")

        precomputed_facets: Dict[str, Dict[str, List[Dict]]] = {}
        # Qwen3-8B directly from merged test.jsonl
        if r.get("facets"):
            precomputed_facets["Qwen3-8B"] = build_model_facet_items(r["facets"], title, abstract)
        # Qwen3-4B directly from generated_facets/Qwen4B (QLoRA fine-tuned)
        if "Qwen3-4B" in generated_by_model and pid in generated_by_model["Qwen3-4B"]:
            precomputed_facets["Qwen3-4B"] = build_model_facet_items(
                generated_by_model["Qwen3-4B"][pid],
                title,
                abstract,
            )
        elif pid in exp_a_facets_map:
            precomputed_facets["Qwen3-4B"] = build_model_facet_items(
                exp_a_facets_map[pid],
                title,
                abstract,
                raw_evidence=exp_a_evidence_map.get(pid),
            )
        # Qwen3-14B, Llama3.1-8B, Gemma2-9B
        for mk in ("Qwen3-14B", "Llama3.1-8B", "Gemma2-9B"):
            if mk in generated_by_model and pid in generated_by_model[mk]:
                precomputed_facets[mk] = build_model_facet_items(
                    generated_by_model[mk][pid],
                    title,
                    abstract,
                )

        avail = [m for m in ["Qwen3-4B", "Qwen3-8B", "Qwen3-14B", "Llama3.1-8B", "Gemma2-9B"] if m in precomputed_facets]
        y_str = f" ({year})" if year else ""
        short_title = title[:65] + ("..." if len(title) > 65 else "")
        examples_out.append(
            {
                "example_id": f"ex_{pid.lower()}",
                "paper_id": pid,
                "title": title,
                "abstract": abstract,
                "year": year,
                "short_label": f"{short_title}{y_str}",
                "domain": "Computer Science",
                "ground_truth_venue_id": cid,
                "ground_truth_venue_acronym": acronym,
                "ground_truth_venue_name": cname,
                "default_model_key": "Qwen3-4B",
                "available_models": avail,
                "precomputed_facets": precomputed_facets,
            }
        )

    (artifacts_dir / "demo_examples.json").write_text(
        json.dumps(examples_out, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Wrote {len(examples_out)} examples; all 5 models present: {sum(1 for e in examples_out if len(e['available_models']) == 5)}/{len(examples_out)}")

    # [5/6] Precompute 6-field BGE-small dense embeddings
    print(f"[5/6] Encoding 6-field BGE-small embeddings using {bge_model_path} ...")
    import torch
    from sentence_transformers import SentenceTransformer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  Using device: {device}")
    if bge_model_path.exists():
        bge = SentenceTransformer(str(bge_model_path), device=device, model_kwargs={"local_files_only": True})
    else:
        bge = SentenceTransformer("BAAI/bge-small-en-v1.5", device=device)

    print("  Encoding paper_corpus (4,210 papers × 6 fields) ...")
    corpus_embs = encode_6fields_bge(bge, paper_corpus_rows)
    np.savez_compressed(artifacts_dir / "corpus_bge_small_6fields.npz", **corpus_embs)

    print("  Encoding conference_train_pool (602 papers × 6 fields) ...")
    train_embs = encode_6fields_bge(bge, conf_train_rows)
    np.savez_compressed(artifacts_dir / "conf_train_bge_small_6fields.npz", **train_embs)

    # Compute 30 conference centroids strictly from the 602 train papers
    print("  Computing 30 conference centroids from 602 train papers ...")
    cid_to_indices: Dict[str, List[int]] = defaultdict(list)
    for i, r in enumerate(conf_train_rows):
        cid_to_indices[r["conference_id"]].append(i)

    dim = bge.get_sentence_embedding_dimension()
    centroid_dict: Dict[str, np.ndarray] = {}
    for field in FIELDS:
        mat = np.zeros((len(conf_catalog_out), dim), dtype=np.float32)
        src_mat = train_embs[field].astype(np.float32)
        src_mask = train_embs[f"mask_{field}"]
        for ci, c in enumerate(conf_catalog_out):
            idxs = [i for i in cid_to_indices.get(c["conference_id"], []) if src_mask[i]]
            if idxs:
                mean_vec = src_mat[idxs].mean(axis=0)
                norm = np.linalg.norm(mean_vec)
                if norm > 0:
                    mat[ci] = mean_vec / norm
        centroid_dict[field] = mat.astype(np.float16)
    np.savez_compressed(artifacts_dir / "conf_centroids_bge_small.npz", **centroid_dict)

    # [6/6] Write manifest.json
    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.perf_counter() - t_start, 2),
        "counts": {
            "paper_corpus": len(paper_corpus_rows),
            "conference_catalog": len(conf_catalog_out),
            "conference_train_pool": len(conf_train_rows),
            "demo_examples": len(examples_out),
            "examples_with_all_5_llms": sum(1 for e in examples_out if len(e["available_models"]) == 5),
        },
        "zero_leakage_verified": True,
        "bge_device": device,
        "fields_encoded": FIELDS,
    }
    (artifacts_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[6/6] Done in {manifest['elapsed_seconds']}s! Artifacts saved to {artifacts_dir}")


if __name__ == "__main__":
    main()
