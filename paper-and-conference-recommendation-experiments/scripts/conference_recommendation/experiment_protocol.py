"""Leakage-free CV, frozen evaluation and auditable IEEE experiment artifacts.

All model selection uses 5-fold stratified Train CV only (seed=42) and is locked
with SHA-256 tuning_id before evaluating the clean 168-paper Test split.
Strictly forbids validated_silver.jsonl in the Conference Recommendation branch.
"""
import argparse
import copy
import csv
import hashlib
import importlib.metadata
import itertools
import json
import math
import random
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .data_loader import FACET_KEYS, get_repo_root, load_dataset
from .feature_loader import (
    FacetFeatureStore,
    TfidfEmbeddingBackend,
    cosine_similarity,
    format_dense_facet_text,
)
from .metrics import VENUE_DISCIPLINE_MAP, classify_venue_tier, evaluate_predictions_detailed
from .ranking import (
    LOCKED_EXP_B_WEIGHTS,
    aggregate_venue_scores,
    compute_active_weight_mass,
    compute_adaptive_fusion_scores,
    compute_facet_first_venue_scores,
    observed,
    rank_neighbors,
    rank_venues_from_score_matrix,
    rerank_coarse_to_fine_batch,
    validate_weights,
)
from .significance import (
    holm_bonferroni,
    mann_whitney_u_test,
    mcnemar_exact_test,
    paired_bootstrap_ci,
    paired_permutation_test,
    rank_correlation_matrix,
    tier_contingency_test,
    win_tie_loss,
)

PROTOCOL = "conference-cv-v2"
DEFAULT_SPLIT = "data/conference_recommendation_dataset/5_mapping_reviewed/splits/temporal_2015_2016_2019_clean"
DEFAULT_FACETS = "data/exp_a/generated/facets_silver.jsonl"
DEFAULT_OUTPUT = "results/conference_recommendation_v2"
SOLUTION_FACETS = FACET_KEYS[1:]
METRICS = ("hit@1", "hit@3", "hit@5", "mrr", "macro_hit@3", "macro_mrr")
METHODS = ("whole_text", "flat_5_facet", "gated")
BACKENDS = ("tfidf", "bert", "specter2", "bge-base", "specter", "bge-small")
AGGREGATIONS = ("sum_knn", "temp_softmax", "prior_norm", "per_venue_top_m")

# Official Exp A Gold Test (60 papers) metrics for the 5 Raw LLMs
# Source: data/exp_a/final/results/llm_experiment_metrics.csv & experiment_summary.json
EXP_A_RAW_METRICS = {
    "Gemma-9B": {
        "precision": 0.674463938,
        "recall": 0.689243028,
        "micro_f1": 0.681773399,
        "macro_f1": 0.703858901,
        "problem_f1": 0.642424242,
        "task_f1": 0.754285714,
        "method_f1": 0.717514124,
        "dataset_f1": 0.845070423,
        "contribution_f1": 0.560000000,
        "exp_a_wall_seconds": 20145.936555,
    },
    "Qwen-8B": {
        "precision": 0.631672598,
        "recall": 0.707171315,
        "micro_f1": 0.667293233,
        "macro_f1": 0.676692372,
        "problem_f1": 0.615384615,
        "task_f1": 0.680000000,
        "method_f1": 0.740112994,
        "dataset_f1": 0.789473684,
        "contribution_f1": 0.558490566,
        "exp_a_wall_seconds": 17510.969629,
    },
    "Llama-8B": {
        "precision": 0.635135135,
        "recall": 0.655378486,
        "micro_f1": 0.645098039,
        "macro_f1": 0.652787970,
        "problem_f1": 0.480000000,
        "task_f1": 0.655555556,
        "method_f1": 0.735694823,
        "dataset_f1": 0.845070423,
        "contribution_f1": 0.547619048,
        "exp_a_wall_seconds": 13466.271561,
    },
    "Qwen-14B": {
        "precision": 0.612132353,
        "recall": 0.663346614,
        "micro_f1": 0.636711281,
        "macro_f1": 0.656238066,
        "problem_f1": 0.562874251,
        "task_f1": 0.637681159,
        "method_f1": 0.731428571,
        "dataset_f1": 0.857142857,
        "contribution_f1": 0.492063492,
        "exp_a_wall_seconds": 20830.097781,
    },
    "Qwen-4B": {
        "precision": 0.593220339,
        "recall": 0.627490040,
        "micro_f1": 0.609874153,
        "macro_f1": 0.629264836,
        "problem_f1": 0.542168675,
        "task_f1": 0.620000000,
        "method_f1": 0.674351585,
        "dataset_f1": 0.800000000,
        "contribution_f1": 0.509803922,
        "exp_a_wall_seconds": 11833.214614,
    },
}

WEIGHT_PRESETS = {
    "default": dict(zip(SOLUTION_FACETS, (.3, .3, .2, .2))),
    "equal": dict.fromkeys(SOLUTION_FACETS, .25),
    "method_heavy": dict(zip(SOLUTION_FACETS, (.2, .5, .15, .15))),
    "task_heavy": dict(zip(SOLUTION_FACETS, (.5, .2, .15, .15))),
    "method_task_focus": dict(zip(SOLUTION_FACETS, (.4, .4, .1, .1))),
    "dataset_focus": dict(zip(SOLUTION_FACETS, (.2, .2, .4, .2))),
}
for _facet in SOLUTION_FACETS:
    _weights = dict(WEIGHT_PRESETS["default"])
    _weights[_facet] = 0.0
    WEIGHT_PRESETS["ablation_no_" + ("contrib" if _facet == "contribution" else _facet)] = validate_weights(_weights, SOLUTION_FACETS)

# 5-Facet weights aligned with Exp B (Weighted A & Weighted B) plus search presets
FLAT_5_FACET_PRESETS = {
    "flat_equal": dict.fromkeys(FACET_KEYS, 0.2),
    "exp_b_weighted_a": dict(zip(FACET_KEYS, (0.40, 0.20, 0.20, 0.10, 0.10))),
    "exp_b_weighted_b": dict(zip(FACET_KEYS, (0.30, 0.25, 0.25, 0.10, 0.10))),
}
for _facet in ("problem", "task", "method", "dataset"):
    FLAT_5_FACET_PRESETS[f"flat_{_facet}_heavy"] = {f: 0.4 if f == _facet else 0.15 for f in FACET_KEYS}
FLAT_5_FACET_PRESETS["flat_method_task_focus"] = dict(zip(FACET_KEYS, (0.2, 0.3, 0.3, 0.1, 0.1)))
for _facet in ("problem", "task", "method", "dataset"):
    FLAT_5_FACET_PRESETS[f"flat_ablation_no_{_facet}"] = {f: 0.0 if f == _facet else 0.25 for f in FACET_KEYS}


def assert_not_validated_silver(path_like):
    """Non-negotiable rule: never load validated_silver.jsonl in Conference Recommendation."""
    if path_like is None:
        return
    text = str(path_like).replace("\\", "/").lower()
    if "validated_silver.jsonl" in text:
        raise ValueError(
            "FORBIDDEN INPUT: validated_silver.jsonl must NOT be used in the Conference "
            "Recommendation branch. Use raw LLM outputs (e.g., data/exp_a/generated/facets_silver.jsonl)."
        )


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def save_json(path, payload, overwrite=False):
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; use --overwrite to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def get_stratified_folds(papers, n_splits=5, seed=42):
    if n_splits < 2:
        raise ValueError("n_splits must be >= 2")
    by_conf = defaultdict(list)
    for idx, paper in enumerate(papers):
        by_conf[paper["conference_id"]].append(idx)
    if len(papers) < n_splits:
        raise ValueError("Need at least n_splits training papers")
    rng = random.Random(seed)
    folds = [[] for _ in range(n_splits)]
    offset = 0
    for venue in sorted(by_conf):
        indices = sorted(by_conf[venue], key=lambda i: papers[i]["paper_id"])
        rng.shuffle(indices)
        for i, idx in enumerate(indices):
            folds[(offset + i) % n_splits].append(idx)
        offset = (offset + len(indices)) % n_splits
    return [sorted(fold, key=lambda i: papers[i]["paper_id"]) for fold in folds]


def aggregate_folds(summaries):
    result = {"fold_metrics": summaries}
    for metric in METRICS:
        values = [row[metric] for row in summaries]
        result[metric] = float(np.mean(values))
        result[metric + "_std"] = float(np.std(values, ddof=1))
    return result


def compute_query_facet_stats(papers):
    """Compute per-facet coverage (%) and average word count across query papers."""
    n = len(papers)
    if n == 0:
        return {"avg_facet_coverage_pct": 0.0, "avg_facet_words": 0.0, "per_facet_coverage_pct": {}}
    per_facet = {}
    total_present = 0
    word_counts = []
    for f in FACET_KEYS:
        present = sum(
            1 for p in papers if format_dense_facet_text(p.get("facets", {}).get(f, "")) != ""
        )
        per_facet[f] = round(100.0 * present / n, 2)
        total_present += present
    for p in papers:
        w = sum(
            len(format_dense_facet_text(p.get("facets", {}).get(f, "")).split())
            for f in FACET_KEYS
        )
        word_counts.append(w)
    return {
        "avg_facet_coverage_pct": round(100.0 * total_present / (len(FACET_KEYS) * n), 2),
        "avg_facet_words": round(float(np.mean(word_counts)), 2),
        "per_facet_coverage_pct": per_facet,
    }


class PairMatrices:
    """Query x reference similarities, with explicit missingness per field."""

    def __init__(self, store, train, queries, candidates):
        self.train, self.queries = train, queries
        self.candidates = sorted(candidates)
        self.train_venue_counts = dict(Counter(p["conference_id"] for p in train))
        self.sim, self.obs = {}, {}
        self.mask_q, self.mask_r = {}, {}
        self.vecs_q, self.vecs_r = {}, {}
        self.embedding_dim = 0
        for field in ("whole_text",) + FACET_KEYS:
            left = [store.get_vectors(p["paper_id"]).get(field) for p in queries]
            right = [store.get_vectors(p["paper_id"]).get(field) for p in train]
            mask_l = np.array([observed(v) for v in left], dtype=bool)
            mask_r = np.array([observed(v) for v in right], dtype=bool)
            self.mask_q[field] = mask_l
            self.mask_r[field] = mask_r
            self.vecs_q[field] = left
            self.vecs_r[field] = right
            self.obs[field] = mask_l[:, None] & mask_r[None, :]
            matrix = np.zeros((len(left), len(right)), dtype=np.float64)
            sample = next((v for v in left + right if observed(v)), None)
            if sample is not None and not isinstance(sample, dict):
                self.embedding_dim = max(self.embedding_dim, len(sample))

                def stack(values):
                    arr = np.array(
                        [v if observed(v) else np.zeros(len(sample)) for v in values],
                        dtype=float,
                    )
                    norms = np.linalg.norm(arr, axis=1, keepdims=True)
                    return np.divide(arr, norms, out=np.zeros_like(arr), where=norms != 0)

                matrix = np.clip(stack(left) @ stack(right).T, -1, 1)
            else:
                for i, lv in enumerate(left):
                    for j, rv in enumerate(right):
                        if self.obs[field][i, j]:
                            matrix[i, j] = cosine_similarity(lv, rv)
            self.sim[field] = matrix

    def subset(self, train_indices, query_indices):
        result = object.__new__(PairMatrices)
        result.train = [self.train[i] for i in train_indices]
        result.queries = [self.queries[i] for i in query_indices]
        result.candidates = self.candidates
        result.train_venue_counts = dict(Counter(p["conference_id"] for p in result.train))
        result.embedding_dim = self.embedding_dim
        ix = np.ix_(query_indices, train_indices)
        result.sim = {f: m[ix] for f, m in self.sim.items()}
        result.obs = {f: m[ix] for f, m in self.obs.items()}
        result.mask_q = {f: m[query_indices] for f, m in self.mask_q.items()}
        result.mask_r = {f: m[train_indices] for f, m in self.mask_r.items()}
        result.vecs_q = {f: [v[i] for i in query_indices] for f, v in self.vecs_q.items()}
        result.vecs_r = {f: [v[i] for i in train_indices] for f, v in self.vecs_r.items()}
        return result

    def scores_with_validity(self, config):
        """Return (similarity_matrix, valid_mask_or_None) aligned with Exp B contract."""
        method = config["method"]
        if method in ("whole_text", "fulltext"):
            return self.sim["whole_text"], None
        facets = SOLUTION_FACETS if method == "gated" else FACET_KEYS
        weights = validate_weights(config["weights"], facets)
        numerator = np.zeros_like(self.sim["problem"])
        denominator = np.zeros_like(numerator)
        for f, weight in weights.items():
            numerator += weight * self.sim[f] * self.obs[f]
            denominator += weight * self.obs[f]

        missing_policy = config.get("missing_policy", "renormalize")
        if missing_policy == "zero_impute":
            # Fixed denominator = sum(w) = 1.0; missing facets contribute 0.0
            result = numerator
            valid_mask = None
        elif missing_policy == "renormalize":
            valid_mask = denominator > 0
            if method == "gated":
                result = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=valid_mask)
                valid_mask = None
            else:
                result = np.divide(
                    numerator, denominator, out=np.full_like(numerator, -np.inf), where=valid_mask
                )
        else:
            raise ValueError(f"Unsupported missing_policy: {missing_policy}")

        if method == "gated" and config.get("gate_enabled", True):
            z = config["kappa"] * (self.sim["problem"] - config["tau"])
            gate = 1 / (1 + np.exp(-np.clip(z, -20, 20)))
            gate[z >= 20] = 1.0
            gate[z <= -20] = 0.0
            gate[~self.obs["problem"]] = 0.5
            result *= gate
        return result, valid_mask

    def scores(self, config):
        mat, _ = self.scores_with_validity(config)
        return np.where(np.isfinite(mat), mat, 0.0)

    def _precompute_row_orders(self, scores, valid_mask=None):
        """Pre-sort reference indices per query row by (-score, paper_id) once per similarity matrix."""
        pids = [p["paper_id"] for p in self.train]
        venues = [p["conference_id"] for p in self.train]
        orders = []
        for idx, row in enumerate(scores):
            vm = None if valid_mask is None else valid_mask[idx]
            valid_rows = []
            if vm is None:
                for j, (pid, venue, sim) in enumerate(zip(pids, venues, row)):
                    val = float(sim)
                    if math.isfinite(val):
                        valid_rows.append((pid, venue, val))
            else:
                for pid, venue, sim, ok in zip(pids, venues, row, vm):
                    if ok:
                        val = float(sim)
                        if math.isfinite(val):
                            valid_rows.append((pid, venue, val))
            valid_rows.sort(key=lambda r: (-r[2], r[0]))
            orders.append(valid_rows)
        return orders

    def evaluate_scores_presorted(self, pre_orders, k_or_config):
        """Fast evaluation reusing pre-sorted per-query neighbor lists (100% bit-exact)."""
        cfg = {"aggregation": "sum_knn", "k": k_or_config} if isinstance(k_or_config, int) else k_or_config
        agg = cfg.get("aggregation", "sum_knn")
        cands = sorted(self.candidates)
        predictions = {}
        if agg == "sum_knn":
            k = int(cfg["k"])
            for p, valid_rows in zip(self.queries, pre_orders):
                scores_v = {v: 0.0 for v in cands}
                for _, venue, sc in valid_rows[:k]:
                    if venue in scores_v:
                        scores_v[venue] += sc
                predictions[p["paper_id"]] = sorted(scores_v.items(), key=lambda r: (-r[1], r[0]))
        elif agg == "temp_softmax":
            k = int(cfg["k"])
            tau = float(cfg.get("agg_tau", 0.05))
            for p, valid_rows in zip(self.queries, pre_orders):
                scores_v = {v: 0.0 for v in cands}
                nb = valid_rows[:k]
                if nb:
                    max_sim = max(r[2] for r in nb)
                    exps = [math.exp((r[2] - max_sim) / tau) for r in nb]
                    tot = sum(exps)
                    if tot > 0.0:
                        for (_, venue, _), w in zip(nb, exps):
                            if venue in scores_v:
                                scores_v[venue] += w / tot
                predictions[p["paper_id"]] = sorted(scores_v.items(), key=lambda r: (-r[1], r[0]))
        elif agg == "prior_norm":
            k = int(cfg["k"])
            tau = float(cfg.get("agg_tau", 0.05))
            alpha = float(cfg.get("alpha", 0.5))
            v_counts = self.train_venue_counts
            for p, valid_rows in zip(self.queries, pre_orders):
                scores_v = {v: 0.0 for v in cands}
                nb = valid_rows[:k]
                if nb:
                    max_sim = max(r[2] for r in nb)
                    for _, venue, sim in nb:
                        if venue in scores_v:
                            scores_v[venue] += math.exp((sim - max_sim) / tau)
                    for venue in scores_v:
                        nv = v_counts.get(venue, 0)
                        if nv > 0 and scores_v[venue] > 0.0:
                            scores_v[venue] /= (float(nv) ** alpha)
                predictions[p["paper_id"]] = sorted(scores_v.items(), key=lambda r: (-r[1], r[0]))
        else:
            pids = [p["paper_id"] for p in self.train]
            venues = [p["conference_id"] for p in self.train]
            for p, valid_rows in zip(self.queries, pre_orders):
                # Fallback to aggregate_venue_scores for per_venue_top_m
                r_pids = [r[0] for r in valid_rows]
                r_vens = [r[1] for r in valid_rows]
                r_sims = [r[2] for r in valid_rows]
                predictions[p["paper_id"]] = aggregate_venue_scores(pids if not valid_rows else r_pids, venues if not valid_rows else r_vens, r_sims, self.candidates, cfg)

        truth = {p["paper_id"]: p["conference_id"] for p in self.queries}
        detailed = evaluate_predictions_detailed(
            predictions, truth, self.candidates, train_venue_counts=self.train_venue_counts
        )
        return {**detailed, "predictions": predictions}

    def evaluate_scores(self, scores, k_or_config, valid_mask=None):
        pids = [p["paper_id"] for p in self.train]
        venues = [p["conference_id"] for p in self.train]
        cfg = {"aggregation": "sum_knn", "k": k_or_config} if isinstance(k_or_config, int) else k_or_config
        predictions = {}
        for idx, (p, row) in enumerate(zip(self.queries, scores)):
            vm = None if valid_mask is None else valid_mask[idx]
            predictions[p["paper_id"]] = aggregate_venue_scores(
                pids, venues, row, self.candidates, cfg, valid_mask=vm
            )
        truth = {p["paper_id"]: p["conference_id"] for p in self.queries}
        detailed = evaluate_predictions_detailed(
            predictions, truth, self.candidates, train_venue_counts=self.train_venue_counts
        )
        return {**detailed, "predictions": predictions}

    def evaluate(self, config):
        t0 = time.perf_counter()
        mat, valid_mask = self.scores_with_validity(config)
        res = self.evaluate_scores(mat, config, valid_mask=valid_mask)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        n_q = max(1, len(self.queries))
        res["retrieval_ms_per_query"] = round(elapsed_ms / n_q, 4)
        return res

    def facet_query_masks(self):
        return {f: self.mask_q[f] for f in FACET_KEYS}

    def facet_ref_masks(self):
        return {f: self.mask_r[f] for f in FACET_KEYS}

    def paper_first_activation_stats(self, valid_mask=None):
        n_q = len(self.queries)
        n_r = len(self.train)
        stats = {
            "n_queries": int(n_q),
            "n_ref": int(n_r),
            "valid_pair_rate": (
                float(np.mean(valid_mask))
                if (valid_mask is not None and (n_q * n_r) > 0)
                else 1.0
            ),
            "valid_query_rate": (
                float(np.mean(np.any(valid_mask, axis=1)))
                if (valid_mask is not None and n_q > 0 and n_r > 0)
                else 1.0
            ),
            "per_facet_pair_activation_rate": {},
            "per_facet_query_activation_rate": {},
        }
        for f in FACET_KEYS:
            pair_rate = float(np.mean(self.obs[f])) if (n_q * n_r) > 0 else 0.0
            q_rate = float(np.mean(self.mask_q[f])) if n_q > 0 else 0.0
            stats[f"{f}_activation_rate"] = pair_rate
            stats[f"{f}_query_activation_rate"] = q_rate
            stats["per_facet_pair_activation_rate"][f] = pair_rate
            stats["per_facet_query_activation_rate"][f] = q_rate
        return stats

    def paper_first_venue_matrix(self, config):
        mat, valid_mask = self.scores_with_validity(config)
        ev = self.evaluate_scores(mat, config, valid_mask=valid_mask)
        preds = ev["predictions"]
        n_q = len(self.queries)
        n_v = len(self.candidates)
        venue_to_col = {v: idx for idx, v in enumerate(self.candidates)}
        scores_mat = np.full((n_q, n_v), -np.inf, dtype=np.float64)
        for q_idx, p in enumerate(self.queries):
            for venue, sc in preds[p["paper_id"]]:
                scores_mat[q_idx, venue_to_col[venue]] = float(sc)
        act_stats = self.paper_first_activation_stats(valid_mask=valid_mask)
        return scores_mat, ev, act_stats

    def facet_first_venue_matrix(self, mode="top_m", top_m=3, weights=None):
        ref_venues = [p["conference_id"] for p in self.train]
        ref_pids = [p["paper_id"] for p in self.train]
        return compute_facet_first_venue_scores(
            ref_venues=ref_venues,
            candidate_venues=self.candidates,
            weights=weights or LOCKED_EXP_B_WEIGHTS,
            mode=mode,
            top_m=int(top_m),
            facet_sims={f: self.sim[f] for f in FACET_KEYS},
            query_masks={f: self.mask_q[f] for f in FACET_KEYS},
            ref_masks={f: self.mask_r[f] for f in FACET_KEYS},
            query_embeddings={f: self.vecs_q[f] for f in FACET_KEYS},
            ref_embeddings={f: self.vecs_r[f] for f in FACET_KEYS},
            ref_pids=ref_pids,
            facets=FACET_KEYS,
        )

    def evaluate_venue_predictions(self, predictions, query_subset_pids=None):
        if query_subset_pids is not None:
            subset_set = set(query_subset_pids)
            sub_preds = {pid: ranked for pid, ranked in predictions.items() if pid in subset_set}
            truth = {
                p["paper_id"]: p["conference_id"]
                for p in self.queries
                if p["paper_id"] in subset_set
            }
        else:
            sub_preds = predictions
            truth = {p["paper_id"]: p["conference_id"] for p in self.queries}
        detailed = evaluate_predictions_detailed(
            sub_preds, truth, self.candidates, train_venue_counts=self.train_venue_counts
        )
        return {**detailed, "predictions": sub_preds}

    def evaluate_facet_first(self, mode="top_m", top_m=3, weights=None):
        t0 = time.perf_counter()
        scores_mat, valid_mask, act_stats = self.facet_first_venue_matrix(
            mode=mode, top_m=top_m, weights=weights
        )
        q_pids = [p["paper_id"] for p in self.queries]
        preds = rank_venues_from_score_matrix(
            scores_mat, q_pids, self.candidates, valid_mask=valid_mask
        )
        ev = self.evaluate_venue_predictions(preds)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        ev["retrieval_ms_per_query"] = round(elapsed_ms / max(1, len(q_pids)), 4)
        ev["scores_matrix"] = scores_mat
        ev["valid_mask"] = valid_mask
        ev["activation_stats"] = act_stats
        return ev


class Experiment:
    def __init__(
        self,
        train,
        test,
        candidates,
        backend="tfidf",
        backend_config=None,
        n_splits=5,
        seed=42,
        output_dir=None,
    ):
        self.train = sorted(train, key=lambda p: p["paper_id"])
        self.test = sorted(test, key=lambda p: p["paper_id"])
        self.candidates = sorted(candidates)
        self.backend, self.backend_config = backend, dict(backend_config or {})
        self.seed = seed
        self.folds = get_stratified_folds(self.train, n_splits, seed)
        if not self.test or not self.candidates:
            raise ValueError("Test set and candidate catalog must be nonempty")
        if set(p["paper_id"] for p in train) & set(p["paper_id"] for p in test):
            raise ValueError("Train/test overlap")
        if len({p["paper_id"] for p in train}) != len(train) or len({p["paper_id"] for p in test}) != len(test):
            raise ValueError("Duplicate paper IDs")
        if any(p["conference_id"] not in self.candidates for p in train + test):
            raise ValueError("Label outside candidate catalog")
        self.output = Path(output_dir or get_repo_root() / DEFAULT_OUTPUT)
        self.cv_pairs = None
        self.final_pairs = None
        self.encoder = None

    @property
    def metadata(self):
        versions = {}
        for name in ("numpy", "scipy", "torch", "sentence-transformers"):
            try:
                versions[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                pass
        source_files = (
            "experiment_protocol.py",
            "feature_loader.py",
            "ranking.py",
            "metrics.py",
            "significance.py",
            "data_loader.py",
        )
        source_digest = digest(
            {
                name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                for name in source_files
            }
        )
        default_models = {
            "tfidf": None,
            "bert": "google-bert/bert-base-uncased",
            "specter2": "allenai/specter2_base",
            "bge-base": "BAAI/bge-base-en-v1.5",
            "specter": "sentence-transformers/allenai-specter",
            "bge-small": "BAAI/bge-small-en-v1.5",
        }
        model_name = self.backend_config.get("model_name", default_models.get(self.backend))
        counts = defaultdict(int)
        for paper in self.train:
            counts[paper["conference_id"]] += 1
        return {
            "protocol": PROTOCOL,
            "source_digest": source_digest,
            "backend": self.backend,
            "backend_config": self.backend_config,
            "embedding_model": model_name,
            "train_digest": digest(self.train),
            "test_digest": digest(self.test),
            "candidates": self.candidates,
            "n_train": len(self.train),
            "n_test": len(self.test),
            "n_splits": len(self.folds),
            "seed": self.seed,
            "std_ddof": 1,
            "tfidf_fit": "reference_only_per_field; OOV ignored",
            "tie_break": "neighbor score desc, paper_id asc; venue score desc, venue_id asc",
            "fold_paper_ids": [[self.train[i]["paper_id"] for i in f] for f in self.folds],
            "rare_train_venues": {v: n for v, n in sorted(counts.items()) if n < len(self.folds)},
            "versions": versions,
        }

    def path(self, stage):
        return self.output / f"{stage}_{self.backend.replace('-', '_')}.json"

    def _effective_backend_config(self):
        cfg = dict(self.backend_config)
        if self.backend != "tfidf" and "cache_dir" not in cfg:
            cfg["cache_dir"] = str(self.output / ".embedding_cache")
        return cfg

    def build_cv(self):
        if self.cv_pairs is not None:
            return self.cv_pairs
        self.cv_pairs = []
        dense_pairs = None
        if self.backend != "tfidf":
            store = FacetFeatureStore(
                self.train, [], backend=self.backend, backend_config=self._effective_backend_config()
            )
            self.encoder = store.backend
            dense_pairs = PairMatrices(store, self.train, self.train, self.candidates)
        for val in self.folds:
            val_set = set(val)
            ref = [i for i in range(len(self.train)) if i not in val_set]
            if dense_pairs is not None:
                pair = dense_pairs.subset(ref, val)
            else:
                train = [self.train[i] for i in ref]
                queries = [self.train[i] for i in val]
                store = FacetFeatureStore(train, queries, backend="tfidf")
                pair = PairMatrices(store, train, queries, self.candidates)
            self.cv_pairs.append(pair)
        return self.cv_pairs

    def build_final(self, queries=None):
        if queries is None and self.final_pairs is not None:
            return self.final_pairs
        queries_arg = self.test if queries is None else queries
        store = FacetFeatureStore(
            self.train,
            queries_arg,
            backend=self.encoder if self.encoder is not None else self.backend,
            backend_config=self._effective_backend_config(),
        )
        if self.backend != "tfidf":
            self.encoder = store.backend
        result = PairMatrices(store, self.train, queries_arg, self.candidates)
        if queries is None:
            self.final_pairs = result
        return result

    def cv(self, config):
        return aggregate_folds([pair.evaluate(config)["metrics"] for pair in self.build_cv()])

    @staticmethod
    def _sort_records(records, metric="hit@3"):
        records.sort(
            key=lambda row: (
                -row["cv"][metric],
                -row["cv"]["mrr"],
                -row["cv"]["macro_hit@3"],
                row["config"].get(
                    "k",
                    row["config"].get(
                        "m",
                        row["config"].get(
                            "top_m",
                            row["config"].get("beta", row["config"].get("top_c", 0)),
                        ),
                    ),
                ),
                digest(row["config"]),
            )
        )
        return records

    def _eval_cv_configs(self, pairs, configs, metric="hit@3"):
        records = []
        cache_key, cached_orders = None, None
        for config in configs:
            pair_key_dict = {
                k: v
                for k, v in config.items()
                if k not in ("k", "aggregation", "agg_tau", "alpha", "m")
            }
            key = digest(pair_key_dict)
            if key != cache_key:
                cached_orders = []
                for pair in pairs:
                    mat, vm = pair.scores_with_validity(config)
                    cached_orders.append(pair._precompute_row_orders(mat, valid_mask=vm))
                cache_key = key
            fold_metrics = [
                pair.evaluate_scores_presorted(orders, config)["metrics"]
                for pair, orders in zip(pairs, cached_orders)
            ]
            records.append({"config": copy.deepcopy(config), "cv": aggregate_folds(fold_metrics)})
        return self._sort_records(records, metric)

    def tune(
        self,
        ks,
        taus,
        kappas,
        metric="hit@3",
        overwrite=False,
        agg_taus=(0.02, 0.05, 0.10, 0.20),
        alphas=(0.5, 1.0),
        ms=(1, 2, 3),
    ):
        tag = self.backend.replace("-", "_")
        targets = [
            self.path("tuning"),
            self.output / f"grid_search_all_{tag}.csv",
            self.output / f"grid_search_folds_{tag}.csv",
        ]
        if not overwrite and any(path.exists() for path in targets):
            raise FileExistsError(f"Tuning JSON/CSV already exists in {self.output}; use --overwrite")
        pairs = self.build_cv()

        # 1. Core methods (Sum-kNN) — preserves full backward compatibility with v2 protocol
        grids = {
            "whole_text": [{"method": "whole_text", "aggregation": "sum_knn", "k": k} for k in ks],
            "flat_5_facet": [
                {"method": "flat_5_facet", "aggregation": "sum_knn", "k": k, "preset": name, "weights": weights}
                for (name, weights), k in itertools.product(FLAT_5_FACET_PRESETS.items(), ks)
            ],
            "gated": [
                {
                    "method": "gated",
                    "aggregation": "sum_knn",
                    "k": k,
                    "tau": tau,
                    "kappa": kappa,
                    "preset": name,
                    "weights": weights,
                }
                for (name, weights), tau, kappa, k in itertools.product(WEIGHT_PRESETS.items(), taus, kappas, ks)
            ],
        }
        defaults = {
            "whole_text": {"method": "whole_text", "aggregation": "sum_knn", "k": 10},
            "flat_5_facet": {
                "method": "flat_5_facet",
                "aggregation": "sum_knn",
                "k": 10,
                "preset": "flat_equal",
                "weights": FLAT_5_FACET_PRESETS["flat_equal"],
            },
            "gated": {
                "method": "gated",
                "aggregation": "sum_knn",
                "k": 10,
                "tau": 0.45,
                "kappa": 10.0,
                "preset": "default",
                "weights": WEIGHT_PRESETS["default"],
            },
        }
        methods = {}
        for method, configs in grids.items():
            print(f"[{self.backend}] CV {method}: {len(configs)} configurations", flush=True)
            records = self._eval_cv_configs(pairs, configs, metric)
            default = {"config": defaults[method], "cv": self.cv(defaults[method])}
            methods[method] = {"best": records[0], "default": default, "cv_all": records}

        # 2. IEEE Exp B-aligned methods x 4 venue aggregations (sum_knn, temp_softmax, prior_norm, per_venue_top_m)
        ieee_method_specs = {
            "fulltext": [{"method": "whole_text"}],
            "equal_weight_facet": [
                {"method": "flat_5_facet", "preset": "flat_equal", "weights": FLAT_5_FACET_PRESETS["flat_equal"]}
            ],
            "weighted_facet_a": [
                {
                    "method": "flat_5_facet",
                    "preset": "exp_b_weighted_a",
                    "weights": FLAT_5_FACET_PRESETS["exp_b_weighted_a"],
                }
            ],
            "weighted_facet_b": [
                {
                    "method": "flat_5_facet",
                    "preset": "exp_b_weighted_b",
                    "weights": FLAT_5_FACET_PRESETS["exp_b_weighted_b"],
                }
            ],
            "weighted_facet_cv": [
                {"method": "flat_5_facet", "preset": name, "weights": weights}
                for name, weights in FLAT_5_FACET_PRESETS.items()
            ],
        }
        ieee_methods = {}
        for m_name, base_list in ieee_method_specs.items():
            ieee_methods[m_name] = {}
            for agg in AGGREGATIONS:
                agg_configs = []
                for base in base_list:
                    if agg == "sum_knn":
                        for k in ks:
                            agg_configs.append({**base, "aggregation": "sum_knn", "k": k})
                    elif agg == "temp_softmax":
                        for k, at in itertools.product(ks, agg_taus):
                            agg_configs.append({**base, "aggregation": "temp_softmax", "k": k, "agg_tau": at})
                    elif agg == "prior_norm":
                        for k, at, alpha in itertools.product(ks, agg_taus, alphas):
                            agg_configs.append(
                                {**base, "aggregation": "prior_norm", "k": k, "agg_tau": at, "alpha": alpha}
                            )
                    elif agg == "per_venue_top_m":
                        for m_val in ms:
                            agg_configs.append({**base, "aggregation": "per_venue_top_m", "m": m_val})
                recs = self._eval_cv_configs(pairs, agg_configs, metric)
                ieee_methods[m_name][agg] = {"best": recs[0], "n_configs": len(recs)}

        payload = {
            "metadata": self.metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "selection_metric": metric,
            "selection_rule": f"max {metric}, max MRR, max macro-Hit@3, min k/m, config SHA256 asc",
            "search_space": {
                "k": ks,
                "tau": taus,
                "kappa": kappas,
                "agg_tau": list(agg_taus),
                "alpha": list(alphas),
                "m": list(ms),
                "gated_presets": WEIGHT_PRESETS,
                "flat_presets": FLAT_5_FACET_PRESETS,
            },
            "methods": methods,
            "ieee_methods": ieee_methods,
        }
        payload["tuning_id"] = digest(payload)
        save_json(self.path("tuning"), payload, overwrite)
        self.export_grid_csv(payload)
        return payload

    def export_grid_csv(self, tuning):
        tag = self.backend.replace("-", "_")
        common = ["backend", "tuning_id", "method", "rank_within_method", "selected", "k", "tau", "kappa", "preset"]
        weight_fields = ["weight_" + f for f in FACET_KEYS]
        metric_fields = [column for metric in METRICS for column in ("cv_" + metric, "cv_" + metric + "_std")]
        fold_fields = [f"fold_{i + 1}_{metric}" for i in range(len(self.folds)) for metric in METRICS]
        rows, folds = [], []
        for method in METHODS:
            for rank, record in enumerate(tuning["methods"][method]["cv_all"], 1):
                config, cv = record["config"], record["cv"]
                row = {
                    "backend": self.backend,
                    "tuning_id": tuning["tuning_id"],
                    "method": method,
                    "rank_within_method": rank,
                    "selected": int(rank == 1),
                    **{key: config.get(key, "") for key in ("k", "tau", "kappa", "preset")},
                    **{"weight_" + f: config.get("weights", {}).get(f, "") for f in FACET_KEYS},
                    **{"cv_" + m: cv[m] for m in METRICS},
                    **{"cv_" + m + "_std": cv[m + "_std"] for m in METRICS},
                }
                for i, fold in enumerate(cv["fold_metrics"]):
                    row.update({f"fold_{i + 1}_{m}": fold[m] for m in METRICS})
                    folds.append(
                        {
                            **{k: row[k] for k in common + weight_fields},
                            "fold": i + 1,
                            "validation_size": fold["total_test_papers"],
                            **{m: fold[m] for m in METRICS},
                        }
                    )
                rows.append(row)
        for name, fields, data in [
            (f"grid_search_all_{tag}.csv", common + weight_fields + metric_fields + fold_fields, rows),
            (f"grid_search_folds_{tag}.csv", common + weight_fields + ["fold", "validation_size", *METRICS], folds),
        ]:
            path = self.output / name
            temporary = path.with_suffix(".csv.tmp")
            with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(data)
            temporary.replace(path)
            print(f"Full grid CSV ({len(data)} rows): {path}", flush=True)

    def load_tuning(self):
        path = self.path("tuning")
        if not path.exists():
            raise FileNotFoundError(f"Run --stage tune first: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        saved = payload.get("metadata", {})
        current = self.metadata
        for key in current:
            if saved.get(key) != current[key]:
                raise ValueError(f"Tuning provenance mismatch: {key}; run tuning again")
        unsigned = {k: v for k, v in payload.items() if k != "tuning_id"}
        if payload.get("tuning_id") != digest(unsigned):
            raise ValueError("Tuning artifact checksum mismatch")
        return payload

    def envelope(self, tuning):
        return {"metadata": self.metadata, "tuning_id": tuning["tuning_id"]}

    def evaluate_test(self, overwrite=False, n_resamples=10000):
        tuning = self.load_tuning()
        if self.path("test").exists() and not overwrite:
            raise FileExistsError(f"{self.path('test')} exists; use --overwrite")
        pairs = self.build_final()
        truth = {p["paper_id"]: p["conference_id"] for p in self.test}

        # 1. Legacy rows (whole_text, flat_5_facet, gated x default/best)
        rows = []
        for method in METHODS:
            for variant in ("default", "best"):
                config = tuning["methods"][method][variant]["config"]
                rows.append({"method": method, "variant": variant, "config": config, **pairs.evaluate(config)})

        # 2. IEEE Exp B-aligned rows x aggregations + paired statistical tests vs Full-text
        ieee_rows = []
        fulltext_by_agg = {}
        ieee_methods = tuning.get("ieee_methods", {})
        for agg in AGGREGATIONS:
            if "fulltext" in ieee_methods and agg in ieee_methods["fulltext"]:
                ft_cfg = ieee_methods["fulltext"][agg]["best"]["config"]
                ft_eval = pairs.evaluate(ft_cfg)
                fulltext_by_agg[agg] = ft_eval

        p_values_hit3 = {}
        p_values_mrr = {}
        for m_name, agg_dict in ieee_methods.items():
            for agg, rec in agg_dict.items():
                cfg = rec["best"]["config"]
                ev = pairs.evaluate(cfg)
                row_key = f"{m_name}__{agg}"
                boot = paired_bootstrap_ci(
                    ev["predictions"],
                    fulltext_by_agg[agg]["predictions"] if (m_name != "fulltext" and agg in fulltext_by_agg) else None,
                    truth,
                    self.candidates,
                    n_boot=min(n_resamples, 10000),
                    seed=self.seed,
                )
                sig = {}
                if m_name != "fulltext" and agg in fulltext_by_agg:
                    ft_ev = fulltext_by_agg[agg]
                    sig = {
                        "vs_baseline": f"fulltext__{agg}",
                        "mcnemar_hit@1": mcnemar_exact_test(ev["per_query"]["hit@1"], ft_ev["per_query"]["hit@1"]),
                        "mcnemar_hit@3": mcnemar_exact_test(ev["per_query"]["hit@3"], ft_ev["per_query"]["hit@3"]),
                        "mcnemar_hit@5": mcnemar_exact_test(ev["per_query"]["hit@5"], ft_ev["per_query"]["hit@5"]),
                        "permutation_mrr": paired_permutation_test(
                            ev["per_query"]["rr"], ft_ev["per_query"]["rr"], n_resamples=n_resamples, seed=self.seed
                        ),
                        "win_tie_loss": win_tie_loss(ev["per_query"]["true_rank"], ft_ev["per_query"]["true_rank"]),
                    }
                    p_values_hit3[row_key] = sig["mcnemar_hit@3"]["p_value"]
                    p_values_mrr[row_key] = sig["permutation_mrr"]["p_value"]

                dim = pairs.embedding_dim or 768
                storage_kb = (dim * 4 / 1024.0) if m_name == "fulltext" else ((5 * dim * 4 + 5) / 1024.0)
                ieee_rows.append(
                    {
                        "row_key": row_key,
                        "ieee_method": m_name,
                        "aggregation": agg,
                        "config": cfg,
                        "cv": rec["best"]["cv"],
                        "storage_kb_per_paper": round(storage_kb, 3),
                        "bootstrap_ci": boot,
                        "significance_vs_fulltext": sig,
                        **ev,
                    }
                )

        holm_hit3 = holm_bonferroni(p_values_hit3, alpha=0.05)
        holm_mrr = holm_bonferroni(p_values_mrr, alpha=0.05)
        for row in ieee_rows:
            rk = row["row_key"]
            if rk in holm_hit3:
                row["significance_vs_fulltext"]["holm_hit@3"] = holm_hit3[rk]
                row["significance_vs_fulltext"]["holm_mrr"] = holm_mrr[rk]

        n = len(self.candidates)
        random_expectation = {f"hit@{k}": min(k, n) / n for k in (1, 3, 5)}
        random_expectation["mrr"] = sum(1 / r for r in range(1, n + 1)) / n
        payload = {
            **self.envelope(tuning),
            "rows": rows,
            "ieee_rows": ieee_rows,
            "random_theoretical": random_expectation,
        }
        save_json(self.path("test"), payload, overwrite)
        return payload

    def _select_primary_weighted_config(self, tuning):
        """Choose the locked primary Weighted Facet operating point (w_exp_b) from Train CV."""
        ieee = tuning.get("ieee_methods", {})
        if "weighted_facet_a" in ieee:
            candidates = [rec["best"] for rec in ieee["weighted_facet_a"].values()]
            self._sort_records(candidates, tuning.get("selection_metric", "hit@3"))
            return candidates[0]["config"]
        if "weighted_facet_cv" in ieee:
            candidates = [rec["best"] for rec in ieee["weighted_facet_cv"].values()]
            self._sort_records(candidates, tuning.get("selection_metric", "hit@3"))
            return candidates[0]["config"]
        return tuning["methods"]["flat_5_facet"]["best"]["config"]

    def analyze(self, overwrite=False):
        tuning = self.load_tuning()
        if self.path("analysis").exists() and not overwrite:
            raise FileExistsError(f"{self.path('analysis')} exists; use --overwrite")
        final = self.build_final()

        # 1. IEEE Table 2: 5-Facet Leave-One-Out Ablation & Temporal Drift + Exp C3 Zero-Imputation
        primary_weighted = self._select_primary_weighted_config(tuning)
        base_cv = self.cv(primary_weighted)
        base_test = final.evaluate(primary_weighted)
        ieee_ablation = [
            {
                "name": "full_5_facets",
                "label": "Full 5 Facets (Baseline)",
                "config": primary_weighted,
                "cv": base_cv,
                "test": base_test,
                "delta_cv_hit@3": 0.0,
                "delta_test_hit@3": 0.0,
                "delta_test_mrr": 0.0,
            }
        ]
        for facet in FACET_KEYS:
            weights = dict(primary_weighted["weights"])
            weights[facet] = 0.0
            if sum(weights.values()) <= 0:
                ieee_ablation.append({"name": f"wo_{facet}", "label": f"w/o {facet.title()}", "status": "undefined"})
                continue
            renorm_w = validate_weights(weights, FACET_KEYS)
            cfg = {**primary_weighted, "weights": renorm_w, "preset": f"wo_{facet}"}
            cv_res = self.cv(cfg)
            test_res = final.evaluate(cfg)
            ieee_ablation.append(
                {
                    "name": f"wo_{facet}",
                    "label": f"w/o {facet.title()}",
                    "config": cfg,
                    "cv": cv_res,
                    "test": test_res,
                    "delta_cv_hit@3": float(cv_res["hit@3"] - base_cv["hit@3"]),
                    "delta_test_hit@3": float(test_res["metrics"]["hit@3"] - base_test["metrics"]["hit@3"]),
                    "delta_test_mrr": float(test_res["metrics"]["mrr"] - base_test["metrics"]["mrr"]),
                }
            )

        # Exp C3 (Missing-Facet Handling Ablation): Zero-Imputation Policy
        zero_cfg = {**primary_weighted, "missing_policy": "zero_impute", "preset": "zero_imputation"}
        zero_cv = self.cv(zero_cfg)
        zero_test = final.evaluate(zero_cfg)
        # Subset diagnostics on Test papers missing 'dataset'
        missing_ds_pids = {
            p["paper_id"]
            for p in self.test
            if format_dense_facet_text(p.get("facets", {}).get("dataset", "")) == ""
        }
        missing_ds_subset = {}
        if missing_ds_pids:
            truth_sub = {p["paper_id"]: p["conference_id"] for p in self.test if p["paper_id"] in missing_ds_pids}
            renorm_sub = evaluate_predictions_detailed(
                {pid: base_test["predictions"][pid] for pid in missing_ds_pids},
                truth_sub,
                self.candidates,
            )["metrics"]
            zero_sub = evaluate_predictions_detailed(
                {pid: zero_test["predictions"][pid] for pid in missing_ds_pids},
                truth_sub,
                self.candidates,
            )["metrics"]
            missing_ds_subset = {
                "missing_dataset_test_count": len(missing_ds_pids),
                "renormalize": renorm_sub,
                "zero_impute": zero_sub,
            }

        ieee_ablation.append(
            {
                "name": "zero_imputation_exp_c3",
                "label": "Zero-Imputation Policy (Exp C3)",
                "config": zero_cfg,
                "cv": zero_cv,
                "test": zero_test,
                "delta_cv_hit@3": float(zero_cv["hit@3"] - base_cv["hit@3"]),
                "delta_test_hit@3": float(zero_test["metrics"]["hit@3"] - base_test["metrics"]["hit@3"]),
                "delta_test_mrr": float(zero_test["metrics"]["mrr"] - base_test["metrics"]["mrr"]),
                "missing_dataset_subset": missing_ds_subset,
            }
        )

        # 2. Legacy Gated ablation + sensitivity (preserved for v2 backward compatibility & unit tests)
        best = tuning["methods"]["gated"]["best"]["config"]
        presets = []
        for name, weights in list(WEIGHT_PRESETS.items())[:6]:
            presets.append((name, weights))
        for facet in SOLUTION_FACETS:
            weights = dict(best["weights"])
            weights[facet] = 0.0
            name = "ablation_no_" + ("contrib" if facet == "contribution" else facet)
            if sum(weights.values()) == 0:
                presets.append((name, None))
            else:
                presets.append((name, validate_weights(weights, SOLUTION_FACETS)))
        ablations = []
        for name, weights in presets:
            if weights is None:
                ablations.append({"name": name, "status": "undefined: removed the only nonzero facet"})
                continue
            config = {**best, "weights": weights, "preset": name}
            ablations.append({"name": name, "config": config, "cv": self.cv(config), "test": final.evaluate(config)})
        gate_config = {**best, "gate_enabled": False}
        gate_ablation = {"config": gate_config, "cv": self.cv(gate_config), "test": final.evaluate(gate_config)}
        tau_grid = (
            [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
            if self.backend == "tfidf"
            else [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
        )
        sweeps = {"k": [5, 10, 15, 20, 25, 30], "tau": tau_grid, "kappa": [2.0, 5.0, 10.0, 15.0, 20.0, 30.0]}
        sensitivity = {}
        for parameter, values in sweeps.items():
            sensitivity[parameter] = [
                {"value": value, "config": {**best, parameter: value}, "cv": self.cv({**best, parameter: value})}
                for value in sorted(set(values + [best[parameter]]))
            ]

        # Sensitivity across k for the 3 Exp B Sum-kNN methods
        k_sensitivity_exp_b = {}
        for m_key, cfg_base in [
            ("fulltext", {"method": "whole_text", "aggregation": "sum_knn"}),
            (
                "equal_weight_facet",
                {
                    "method": "flat_5_facet",
                    "aggregation": "sum_knn",
                    "preset": "flat_equal",
                    "weights": FLAT_5_FACET_PRESETS["flat_equal"],
                },
            ),
            (
                "weighted_facet_a",
                {
                    "method": "flat_5_facet",
                    "aggregation": "sum_knn",
                    "preset": "exp_b_weighted_a",
                    "weights": FLAT_5_FACET_PRESETS["exp_b_weighted_a"],
                },
            ),
        ]:
            k_sensitivity_exp_b[m_key] = [
                {"k": kv, "cv": self.cv({**cfg_base, "k": kv})} for kv in [5, 10, 15, 20, 25, 30]
            ]

        payload = {
            **self.envelope(tuning),
            "best_operating_point": best,
            "primary_weighted_operating_point": primary_weighted,
            "ieee_ablation_temporal_drift": ieee_ablation,
            "k_sensitivity_exp_b": k_sensitivity_exp_b,
            "facet_ablation_table2": ablations,
            "problem_gate_ablation": gate_ablation,
            "sensitivity": sensitivity,
            "sensitivity_split": "train_cv_only",
            "note": "Prespecified diagnostics; do not select a new config from held-out ablations.",
        }
        save_json(self.path("analysis"), payload, overwrite)
        return payload

    def benchmark(self, extractor_queries, overwrite=False, n_resamples=10000):
        tuning = self.load_tuning()
        if self.path("benchmark").exists() and not overwrite:
            raise FileExistsError(f"{self.path('benchmark')} exists; use --overwrite")
        best_gated = tuning["methods"]["gated"]["best"]["config"]
        ieee = tuning.get("ieee_methods", {})

        # Locked operating points for Cross-LLM substitution: Equal-weight & Weighted Facet
        def _best_agg(m_key, fallback):
            if m_key in ieee:
                recs = [v["best"] for v in ieee[m_key].values()]
                self._sort_records(recs, tuning.get("selection_metric", "hit@3"))
                return recs[0]["config"]
            return fallback

        locked_configs = {
            "equal_weight_facet": _best_agg(
                "equal_weight_facet",
                {
                    "method": "flat_5_facet",
                    "aggregation": "sum_knn",
                    "k": tuning["methods"]["flat_5_facet"]["best"]["config"]["k"],
                    "preset": "flat_equal",
                    "weights": FLAT_5_FACET_PRESETS["flat_equal"],
                },
            ),
            "weighted_facet_a": _best_agg(
                "weighted_facet_a",
                {
                    "method": "flat_5_facet",
                    "aggregation": "sum_knn",
                    "k": tuning["methods"]["flat_5_facet"]["best"]["config"]["k"],
                    "preset": "exp_b_weighted_a",
                    "weights": FLAT_5_FACET_PRESETS["exp_b_weighted_a"],
                },
            ),
            "weighted_facet_cv": self._select_primary_weighted_config(tuning),
        }

        base_ids = {p["paper_id"] for p in self.test}
        rows = []
        ieee_benchmark_rows = {k: [] for k in locked_configs}
        extractor_stats = {}

        for name, queries in extractor_queries.items():
            if {p["paper_id"] for p in queries} != base_ids or len(queries) != len(base_ids):
                raise ValueError(f"Extractor {name}: test IDs differ from frozen split")
            sorted_queries = sorted(queries, key=lambda p: p["paper_id"])
            for paper, base in zip(sorted_queries, self.test):
                if {k: v for k, v in paper.items() if k != "facets"} != {k: v for k, v in base.items() if k != "facets"}:
                    raise ValueError(f"Extractor {name}: changed text or labels")

            t_enc = time.perf_counter()
            pairs = self.build_final(sorted_queries)
            encode_ms_per_paper = round((time.perf_counter() - t_enc) * 1000.0 / max(1, len(sorted_queries)), 3)
            q_stats = compute_query_facet_stats(sorted_queries)
            exp_a_info = EXP_A_RAW_METRICS.get(name, {})
            # Estimate per-paper Exp A extraction latency from wall_seconds / 180 calls (60 papers x 3 V-recall turns)
            est_llm_ms = (
                round(exp_a_info["exp_a_wall_seconds"] * 1000.0 / 60.0, 1)
                if "exp_a_wall_seconds" in exp_a_info
                else None
            )
            dim = pairs.embedding_dim or 768
            storage_kb = round((5 * dim * 4 + 5) / 1024.0, 3)

            extractor_stats[name] = {
                **q_stats,
                "exp_a": exp_a_info,
                "encode_ms_per_paper": encode_ms_per_paper,
                "exp_a_est_ms_per_paper": est_llm_ms,
                "storage_kb_per_paper": storage_kb,
            }

            # Legacy gated row
            rows.append(
                {
                    "extractor": name,
                    "config": best_gated,
                    "query_digest": digest(queries),
                    "frozen_train_digest": digest(self.train),
                    **pairs.evaluate(best_gated),
                }
            )

            # IEEE Exp B-aligned rows (Equal-weight, Weighted A, Weighted CV)
            for m_key, cfg in locked_configs.items():
                ev = pairs.evaluate(cfg)
                ieee_benchmark_rows[m_key].append(
                    {
                        "extractor": name,
                        "ieee_method": m_key,
                        "config": cfg,
                        "query_digest": digest(queries),
                        "frozen_train_digest": digest(self.train),
                        "facet_stats": q_stats,
                        "exp_a": exp_a_info,
                        "encode_ms_per_paper": encode_ms_per_paper,
                        "exp_a_est_ms_per_paper": est_llm_ms,
                        "storage_kb_per_paper": storage_kb,
                        **ev,
                    }
                )

        # Pairwise significance & Win/Tie/Loss vs Qwen-8B (Raw) + Spearman/Kendall correlations
        rank_correlations = {}
        for m_key, m_rows in ieee_benchmark_rows.items():
            ref_row = next((r for r in m_rows if r["extractor"] == "Qwen-8B"), None)
            if ref_row is not None:
                for r in m_rows:
                    if r["extractor"] == "Qwen-8B":
                        r["vs_qwen8b"] = {"win": 0, "tie": len(self.test), "loss": 0}
                    else:
                        r["vs_qwen8b"] = {
                            **win_tie_loss(r["per_query"]["true_rank"], ref_row["per_query"]["true_rank"]),
                            "mcnemar_hit@3": mcnemar_exact_test(
                                r["per_query"]["hit@3"], ref_row["per_query"]["hit@3"]
                            ),
                            "permutation_mrr": paired_permutation_test(
                                r["per_query"]["rr"],
                                ref_row["per_query"]["rr"],
                                n_resamples=n_resamples,
                                seed=self.seed,
                            ),
                        }

            # Build correlation vectors across available Raw LLMs
            exp_a_vec_map = {}
            down_vec_map = {}
            for r in m_rows:
                ext = r["extractor"]
                if ext in EXP_A_RAW_METRICS:
                    exp_a_vec_map[ext] = {
                        **{k: v for k, v in EXP_A_RAW_METRICS[ext].items() if k != "exp_a_wall_seconds"},
                        "test_facet_coverage_pct": r["facet_stats"]["avg_facet_coverage_pct"],
                        "avg_facet_words": r["facet_stats"]["avg_facet_words"],
                    }
                    down_vec_map[ext] = {
                        k: r["metrics"][k] for k in ("hit@1", "hit@3", "hit@5", "mrr", "macro_hit@3", "macro_mrr")
                    }
            rank_correlations[m_key] = rank_correlation_matrix(exp_a_vec_map, down_vec_map)

        payload = {
            **self.envelope(tuning),
            "scenario": "Fixed-Index (Qwen-8B Raw, 602 Train), Query-Side Extractor Substitution (5 Raw LLMs, 168 Clean Test)",
            "rows": rows,
            "ieee_benchmark": ieee_benchmark_rows,
            "extractor_stats": extractor_stats,
            "rank_correlations": rank_correlations,
        }
        save_json(self.path("benchmark"), payload, overwrite)
        return payload

    def _get_or_tune_paper_first_baselines(
        self,
        cv_pairs,
        ks=(5, 10, 15, 20, 25, 30),
        agg_taus=(0.02, 0.05, 0.10, 0.20),
        alphas=(0.5, 1.0),
        ms=(1, 2, 3),
        metric="hit@3",
    ):
        """Read Paper-First CV winners from tuning_{backend}.json if available, else evaluate on cv_pairs."""
        tuning_path = self.path("tuning")
        if tuning_path.exists():
            try:
                saved = json.loads(tuning_path.read_text(encoding="utf-8"))
                saved_meta = saved.get("metadata", {})
                if (
                    saved_meta.get("train_digest") == self.metadata["train_digest"]
                    and saved_meta.get("candidates") == self.metadata["candidates"]
                    and "ieee_methods" in saved
                ):
                    ieee = saved["ieee_methods"]
                    if all(k in ieee for k in ("fulltext", "equal_weight_facet", "weighted_facet_a")):
                        return ieee
            except Exception:
                pass

        specs = {
            "fulltext": [{"method": "whole_text"}],
            "equal_weight_facet": [
                {"method": "flat_5_facet", "preset": "flat_equal", "weights": FLAT_5_FACET_PRESETS["flat_equal"]}
            ],
            "weighted_facet_a": [
                {
                    "method": "flat_5_facet",
                    "preset": "exp_b_weighted_a",
                    "weights": dict(LOCKED_EXP_B_WEIGHTS),
                }
            ],
        }
        ieee_methods = {}
        for m_name, base_list in specs.items():
            ieee_methods[m_name] = {}
            for agg in AGGREGATIONS:
                agg_configs = []
                for base in base_list:
                    if agg == "sum_knn":
                        for k in ks:
                            agg_configs.append({**base, "aggregation": "sum_knn", "k": int(k)})
                    elif agg == "temp_softmax":
                        for k, at in itertools.product(ks, agg_taus):
                            agg_configs.append(
                                {**base, "aggregation": "temp_softmax", "k": int(k), "agg_tau": float(at)}
                            )
                    elif agg == "prior_norm":
                        for k, at, alpha in itertools.product(ks, agg_taus, alphas):
                            agg_configs.append(
                                {
                                    **base,
                                    "aggregation": "prior_norm",
                                    "k": int(k),
                                    "agg_tau": float(at),
                                    "alpha": float(alpha),
                                }
                            )
                    elif agg == "per_venue_top_m":
                        for m_val in ms:
                            agg_configs.append({**base, "aggregation": "per_venue_top_m", "m": int(m_val)})
                recs = self._eval_cv_configs(cv_pairs, agg_configs, metric)
                ieee_methods[m_name][agg] = {"best": recs[0], "n_configs": len(recs)}
        return ieee_methods

    def tune_exp_d(
        self,
        ks=(5, 10, 15, 20, 25, 30),
        top_ms=(1, 2, 3),
        betas=(0.1, 0.2, 0.3, 0.5, 0.7),
        top_cs=(5, 10),
        metric="hit@3",
        overwrite=False,
    ):
        """5-Fold Stratified Train CV tuning for Facet-First (top_m), Adaptive Fusion (beta), and Coarse-to-Fine (top_c).

        Strictly locks Exp B weights w_exp_b = (0.40, 0.20, 0.20, 0.10, 0.10). Never tunes 5D facet weights.
        """
        target = self.path("tuning_d")
        if target.exists() and not overwrite:
            raise FileExistsError(f"{target} already exists; use --overwrite")

        cv_pairs = self.build_cv()
        ieee_paper_first = self._get_or_tune_paper_first_baselines(
            cv_pairs, ks=ks, ms=top_ms, metric=metric
        )

        # 1. Select CV-locked Full-text winner across all aggregations
        ft_candidates = [copy.deepcopy(rec["best"]) for rec in ieee_paper_first["fulltext"].values()]
        self._sort_records(ft_candidates, metric)
        fulltext_winner = ft_candidates[0]

        # 2. Mechanism 1: Facet-First Venue Aggregation on 5-Fold Train CV (Equal-weight & locked w_exp_b)
        weight_schemes = {
            "equal_weight_facet": dict(FLAT_5_FACET_PRESETS["flat_equal"]),
            "weighted_facet_a": dict(LOCKED_EXP_B_WEIGHTS),
        }
        facet_first_cv = {}
        for scheme_name, weights in weight_schemes.items():
            top_m_records = []
            for m_val in top_ms:
                cfg = {
                    "mechanism": "facet_first",
                    "mode": "top_m",
                    "top_m": int(m_val),
                    "preset": scheme_name,
                    "weights": dict(weights),
                }
                fold_metrics = [
                    pair.evaluate_facet_first(mode="top_m", top_m=int(m_val), weights=weights)["metrics"]
                    for pair in cv_pairs
                ]
                top_m_records.append({"config": cfg, "cv": aggregate_folds(fold_metrics)})
            self._sort_records(top_m_records, metric)

            centroid_cfg = {
                "mechanism": "facet_first",
                "mode": "centroid",
                "preset": scheme_name,
                "weights": dict(weights),
            }
            centroid_folds = [
                pair.evaluate_facet_first(mode="centroid", weights=weights)["metrics"]
                for pair in cv_pairs
            ]
            centroid_record = {"config": centroid_cfg, "cv": aggregate_folds(centroid_folds)}

            all_ff = copy.deepcopy(top_m_records + [centroid_record])
            self._sort_records(all_ff, metric)
            facet_first_cv[scheme_name] = {
                "top_m_best": top_m_records[0],
                "top_m_all": top_m_records,
                "centroid": centroid_record,
                "best": all_ff[0],
            }

        facet_first_winner = facet_first_cv["weighted_facet_a"]["best"]
        ff_win_cfg = facet_first_winner["config"]

        # Precompute per-fold base matrices for Full-text winner and Facet-First winner (under locked w_exp_b)
        fold_full_mats = []
        fold_full_preds = []
        fold_facet_mats = []
        fold_facet_vms = []
        fold_q_masks = []
        for pair in cv_pairs:
            f_mat, f_ev, _ = pair.paper_first_venue_matrix(fulltext_winner["config"])
            fold_full_mats.append(f_mat)
            fold_full_preds.append(f_ev["predictions"])

            ff_mat, ff_vm, _ = pair.facet_first_venue_matrix(
                mode=ff_win_cfg["mode"],
                top_m=ff_win_cfg.get("top_m", 3),
                weights=LOCKED_EXP_B_WEIGHTS,
            )
            fold_facet_mats.append(ff_mat)
            fold_facet_vms.append(ff_vm)
            fold_q_masks.append(pair.facet_query_masks())

        # 3. Mechanism 2: Coverage-Aware Adaptive Fusion on 5-Fold Train CV (beta in {0.1, 0.2, 0.3, 0.5, 0.7})
        adaptive_records = []
        for beta_val in betas:
            b_float = float(beta_val)
            cfg = {
                "mechanism": "adaptive_fusion",
                "beta": b_float,
                "base_fulltext": fulltext_winner["config"],
                "base_facet_first": ff_win_cfg,
                "weights": dict(LOCKED_EXP_B_WEIGHTS),
            }
            fold_metrics = []
            for pair, f_mat, ff_mat, ff_vm, q_masks in zip(
                cv_pairs, fold_full_mats, fold_facet_mats, fold_facet_vms, fold_q_masks
            ):
                fused_mat, _ = compute_adaptive_fusion_scores(
                    f_mat,
                    ff_mat,
                    q_masks,
                    beta=b_float,
                    facet_valid_mask=ff_vm,
                    weights=LOCKED_EXP_B_WEIGHTS,
                )
                q_pids = [p["paper_id"] for p in pair.queries]
                preds = rank_venues_from_score_matrix(fused_mat, q_pids, pair.candidates)
                fold_metrics.append(pair.evaluate_venue_predictions(preds)["metrics"])
            adaptive_records.append({"config": cfg, "cv": aggregate_folds(fold_metrics)})
        self._sort_records(adaptive_records, metric)
        adaptive_winner = adaptive_records[0]
        best_beta = float(adaptive_winner["config"]["beta"])

        # Precompute per-fold adaptive fusion matrices at best_beta for Stage-2 Coarse-to-Fine CV
        fold_adaptive_mats = []
        for f_mat, ff_mat, ff_vm, q_masks in zip(
            fold_full_mats, fold_facet_mats, fold_facet_vms, fold_q_masks
        ):
            fused_mat, _ = compute_adaptive_fusion_scores(
                f_mat,
                ff_mat,
                q_masks,
                beta=best_beta,
                facet_valid_mask=ff_vm,
                weights=LOCKED_EXP_B_WEIGHTS,
            )
            fold_adaptive_mats.append(fused_mat)

        # 4. Mechanism 3: Coarse-to-Fine Facet Reranking on 5-Fold Train CV (top_c in {5, 10})
        c2f_cv = {}
        for stage2_name in ("facet_first", "adaptive_fusion"):
            c_records = []
            for c_val in top_cs:
                c_int = int(c_val)
                cfg = {
                    "mechanism": "coarse_to_fine",
                    "top_c": c_int,
                    "stage2": stage2_name,
                    "stage1_fulltext": fulltext_winner["config"],
                    "stage2_config": ff_win_cfg if stage2_name == "facet_first" else adaptive_winner["config"],
                    "weights": dict(LOCKED_EXP_B_WEIGHTS),
                }
                fold_metrics = []
                for idx, pair in enumerate(cv_pairs):
                    q_pids = [p["paper_id"] for p in pair.queries]
                    s1_preds = fold_full_preds[idx]
                    if stage2_name == "facet_first":
                        s2_mat = fold_facet_mats[idx]
                        s2_vm = fold_facet_vms[idx]
                    else:
                        s2_mat = fold_adaptive_mats[idx]
                        s2_vm = None
                    c2f_preds = rerank_coarse_to_fine_batch(
                        s1_preds,
                        q_pids,
                        s2_mat,
                        pair.candidates,
                        top_c=c_int,
                        stage2_valid_mask=s2_vm,
                    )
                    fold_metrics.append(pair.evaluate_venue_predictions(c2f_preds)["metrics"])
                c_records.append({"config": cfg, "cv": aggregate_folds(fold_metrics)})
            by_c = {int(r["config"]["top_c"]): copy.deepcopy(r) for r in c_records}
            self._sort_records(c_records, metric)
            c2f_cv[stage2_name] = {
                "best": c_records[0],
                "all": c_records,
                "by_top_c": {str(k): v for k, v in by_c.items()},
            }

        payload = {
            "metadata": self.metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "selection_metric": metric,
            "selection_rule": f"max {metric}, max MRR, max macro-Hit@3, min top_m/beta/top_c, config SHA256 asc",
            "locked_exp_b_weights": dict(LOCKED_EXP_B_WEIGHTS),
            "search_space": {
                "top_m": [int(m) for m in top_ms],
                "beta": [float(b) for b in betas],
                "top_c": [int(c) for c in top_cs],
            },
            "paper_first_baselines": ieee_paper_first,
            "fulltext_winner": fulltext_winner,
            "facet_first": facet_first_cv,
            "facet_first_winner": facet_first_winner,
            "adaptive_fusion": {
                "best": adaptive_winner,
                "all": adaptive_records,
            },
            "coarse_to_fine": c2f_cv,
        }
        payload["tuning_id"] = digest(payload)
        save_json(target, payload, overwrite)
        return payload

    def load_tuning_d(self):
        path = self.path("tuning_d")
        if not path.exists():
            raise FileNotFoundError(f"Run --stage exp_d (or tune_exp_d) first: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        saved = payload.get("metadata", {})
        current = self.metadata
        for key in current:
            if saved.get(key) != current[key]:
                raise ValueError(f"Exp D tuning provenance mismatch: {key}; run tune_exp_d again")
        unsigned = {k: v for k, v in payload.items() if k != "tuning_id"}
        if payload.get("tuning_id") != digest(unsigned):
            raise ValueError("Exp D tuning artifact checksum mismatch")
        return payload

    def run_exp_d(
        self,
        extractor_queries=None,
        overwrite=False,
        n_resamples=10000,
        ks=(5, 10, 15, 20, 25, 30),
        top_ms=(1, 2, 3),
        betas=(0.1, 0.2, 0.3, 0.5, 0.7),
        top_cs=(5, 10),
        metric="hit@3",
    ):
        """Execute all 4 diagnostic experiments (Exp D1-D4) on the 168 clean Test papers."""
        target = self.path("exp_d")
        if target.exists() and not overwrite:
            raise FileExistsError(f"{target} already exists; use --overwrite")

        if not self.path("tuning_d").exists() or overwrite:
            tuning_d = self.tune_exp_d(
                ks=ks, top_ms=top_ms, betas=betas, top_cs=top_cs, metric=metric, overwrite=overwrite
            )
        else:
            tuning_d = self.load_tuning_d()

        if extractor_queries is None:
            extractor_queries = {"Qwen-8B": self.test}

        base_ids = {p["paper_id"] for p in self.test}
        for name, queries in extractor_queries.items():
            if {p["paper_id"] for p in queries} != base_ids or len(queries) != len(base_ids):
                raise ValueError(f"Extractor {name}: test IDs differ from frozen split")

        final = self.build_final()
        q_pids = [p["paper_id"] for p in self.test]
        truth = {p["paper_id"]: p["conference_id"] for p in self.test}
        n_boot = min(int(n_resamples), 10000)

        pf_cv = tuning_d["paper_first_baselines"]
        ff_cv = tuning_d["facet_first"]
        ft_win_rec = tuning_d["fulltext_winner"]
        ff_win_rec = tuning_d["facet_first_winner"]
        af_win_rec = tuning_d["adaptive_fusion"]["best"]
        best_beta = float(af_win_rec["config"]["beta"])

        # Evaluate Full-text winner on Test
        ft_scores_mat, ft_win_ev, ft_act_stats = final.paper_first_venue_matrix(ft_win_rec["config"])

        def _compare_eval(ev_a, ev_b, label_b, compute_boot=True):
            sig = {
                "vs_baseline": label_b,
                "mcnemar_hit@1": mcnemar_exact_test(ev_a["per_query"]["hit@1"], ev_b["per_query"]["hit@1"]),
                "mcnemar_hit@3": mcnemar_exact_test(ev_a["per_query"]["hit@3"], ev_b["per_query"]["hit@3"]),
                "mcnemar_hit@5": mcnemar_exact_test(ev_a["per_query"]["hit@5"], ev_b["per_query"]["hit@5"]),
                "permutation_mrr": paired_permutation_test(
                    ev_a["per_query"]["rr"], ev_b["per_query"]["rr"], n_resamples=n_resamples, seed=self.seed
                ),
                "win_tie_loss": win_tie_loss(ev_a["per_query"]["true_rank"], ev_b["per_query"]["true_rank"]),
                "delta_hit@1": float(ev_a["metrics"]["hit@1"] - ev_b["metrics"]["hit@1"]),
                "delta_hit@3": float(ev_a["metrics"]["hit@3"] - ev_b["metrics"]["hit@3"]),
                "delta_mrr": float(ev_a["metrics"]["mrr"] - ev_b["metrics"]["mrr"]),
            }
            if compute_boot:
                sig["bootstrap_ci"] = paired_bootstrap_ci(
                    ev_a["predictions"],
                    ev_b["predictions"],
                    truth,
                    self.candidates,
                    n_boot=n_boot,
                    seed=self.seed,
                )
            return sig

        # ======================================================================
        # EXP D1: Paper-First vs Facet-First + 5 Raw LLMs
        # ======================================================================
        d1_rows = []

        # Full-text reference rows
        for ft_agg_key, ft_label in [
            ("best", f"Full-text ({ft_win_rec['config']['aggregation']} Winner)"),
            ("sum_knn", "Full-text (Sum-kNN)"),
            ("per_venue_top_m", "Full-text (Per-Venue Top-m)"),
        ]:
            rec = ft_win_rec if ft_agg_key == "best" else pf_cv["fulltext"][ft_agg_key]["best"]
            _, ev, act = final.paper_first_venue_matrix(rec["config"])
            boot = paired_bootstrap_ci(
                ev["predictions"], None, truth, self.candidates, n_boot=n_boot, seed=self.seed
            )
            d1_rows.append(
                {
                    "row_key": f"fulltext__{ft_agg_key}",
                    "weight_scheme": "fulltext",
                    "paradigm": "Full-text",
                    "aggregation": rec["config"]["aggregation"],
                    "label": ft_label,
                    "config": rec["config"],
                    "cv": rec["cv"],
                    "metrics": ev["metrics"],
                    "tier_metrics": ev["tier_metrics"],
                    "per_query": ev["per_query"],
                    "activation_stats": act,
                    "bootstrap_ci": boot,
                }
            )

        # Paper-First vs Facet-First under Equal-weight and locked w_exp_b
        pf_sum_evals = {}
        for scheme_key, scheme_label, weights in [
            ("equal_weight_facet", "Equal-weight (0.2 x 5)", FLAT_5_FACET_PRESETS["flat_equal"]),
            ("weighted_facet_a", "Locked w_ExpB (0.4/0.2/0.2/0.1/0.1)", LOCKED_EXP_B_WEIGHTS),
        ]:
            # Paper-First: Sum-kNN
            pf_sum_rec = pf_cv[scheme_key]["sum_knn"]["best"]
            _, pf_sum_ev, pf_sum_act = final.paper_first_venue_matrix(pf_sum_rec["config"])
            pf_sum_evals[scheme_key] = pf_sum_ev
            d1_rows.append(
                {
                    "row_key": f"{scheme_key}__paper_first_sum_knn",
                    "weight_scheme": scheme_key,
                    "weight_label": scheme_label,
                    "paradigm": "Paper-First",
                    "aggregation": "sum_knn",
                    "label": f"Paper-First: Sum-kNN ({scheme_label})",
                    "config": pf_sum_rec["config"],
                    "cv": pf_sum_rec["cv"],
                    "metrics": pf_sum_ev["metrics"],
                    "tier_metrics": pf_sum_ev["tier_metrics"],
                    "per_query": pf_sum_ev["per_query"],
                    "activation_stats": pf_sum_act,
                    "vs_fulltext": _compare_eval(pf_sum_ev, ft_win_ev, "fulltext_winner"),
                }
            )

            # Paper-First: Per-Venue Top-m
            pf_topm_rec = pf_cv[scheme_key]["per_venue_top_m"]["best"]
            _, pf_topm_ev, pf_topm_act = final.paper_first_venue_matrix(pf_topm_rec["config"])
            d1_rows.append(
                {
                    "row_key": f"{scheme_key}__paper_first_per_venue_top_m",
                    "weight_scheme": scheme_key,
                    "weight_label": scheme_label,
                    "paradigm": "Paper-First",
                    "aggregation": "per_venue_top_m",
                    "label": f"Paper-First: Per-Venue Top-m ({scheme_label})",
                    "config": pf_topm_rec["config"],
                    "cv": pf_topm_rec["cv"],
                    "metrics": pf_topm_ev["metrics"],
                    "tier_metrics": pf_topm_ev["tier_metrics"],
                    "per_query": pf_topm_ev["per_query"],
                    "activation_stats": pf_topm_act,
                    "vs_fulltext": _compare_eval(pf_topm_ev, ft_win_ev, "fulltext_winner"),
                    "vs_paper_first_sum_knn": _compare_eval(
                        pf_topm_ev, pf_sum_ev, f"{scheme_key}__paper_first_sum_knn", compute_boot=False
                    ),
                }
            )

            # Facet-First: Per-Facet Venue Top-m
            ff_topm_rec = ff_cv[scheme_key]["top_m_best"]
            ff_topm_ev = final.evaluate_facet_first(
                mode="top_m", top_m=ff_topm_rec["config"]["top_m"], weights=weights
            )
            d1_rows.append(
                {
                    "row_key": f"{scheme_key}__facet_first_top_m",
                    "weight_scheme": scheme_key,
                    "weight_label": scheme_label,
                    "paradigm": "Facet-First",
                    "aggregation": "per_facet_top_m",
                    "label": f"Facet-First: Per-Facet Venue Top-m ({scheme_label})",
                    "config": ff_topm_rec["config"],
                    "cv": ff_topm_rec["cv"],
                    "metrics": ff_topm_ev["metrics"],
                    "tier_metrics": ff_topm_ev["tier_metrics"],
                    "per_query": ff_topm_ev["per_query"],
                    "activation_stats": ff_topm_ev["activation_stats"],
                    "vs_fulltext": _compare_eval(ff_topm_ev, ft_win_ev, "fulltext_winner"),
                    "vs_paper_first_sum_knn": _compare_eval(
                        ff_topm_ev, pf_sum_ev, f"{scheme_key}__paper_first_sum_knn", compute_boot=False
                    ),
                }
            )

            # Facet-First: Per-Facet Venue Centroid
            ff_cent_rec = ff_cv[scheme_key]["centroid"]
            ff_cent_ev = final.evaluate_facet_first(mode="centroid", weights=weights)
            d1_rows.append(
                {
                    "row_key": f"{scheme_key}__facet_first_centroid",
                    "weight_scheme": scheme_key,
                    "weight_label": scheme_label,
                    "paradigm": "Facet-First",
                    "aggregation": "per_facet_centroid",
                    "label": f"Facet-First: Per-Facet Venue Centroid ({scheme_label})",
                    "config": ff_cent_rec["config"],
                    "cv": ff_cent_rec["cv"],
                    "metrics": ff_cent_ev["metrics"],
                    "tier_metrics": ff_cent_ev["tier_metrics"],
                    "per_query": ff_cent_ev["per_query"],
                    "activation_stats": ff_cent_ev["activation_stats"],
                    "vs_fulltext": _compare_eval(ff_cent_ev, ft_win_ev, "fulltext_winner"),
                    "vs_paper_first_sum_knn": _compare_eval(
                        ff_cent_ev, pf_sum_ev, f"{scheme_key}__paper_first_sum_knn", compute_boot=False
                    ),
                }
            )

        # Cross-LLM Evaluation for Exp D1 & Exp D2 across the 5 Raw LLMs
        ff_win_cfg = ff_win_rec["config"]
        ff_topm_locked_m = int(ff_cv["weighted_facet_a"]["top_m_best"]["config"]["top_m"])
        pf_w_sum_cfg = pf_cv["weighted_facet_a"]["sum_knn"]["best"]["config"]

        d1_llm_rows_by_mode = {
            "facet_first_winner": [],
            "facet_first_top_m": [],
            "facet_first_centroid": [],
            "paper_first_sum_knn": [],
        }
        d2_by_llm = {}

        for ext_name, queries in extractor_queries.items():
            sorted_queries = sorted(queries, key=lambda p: p["paper_id"])
            pairs_ext = final if (ext_name == "Qwen-8B" and queries is self.test) else self.build_final(sorted_queries)
            q_stats = compute_query_facet_stats(sorted_queries)
            q_masks_ext = pairs_ext.facet_query_masks()
            g_q_ext = compute_active_weight_mass(q_masks_ext, weights=LOCKED_EXP_B_WEIGHTS)
            exp_a_info = EXP_A_RAW_METRICS.get(ext_name, {})

            # Evaluate Paper-First Sum-kNN (w_exp_b) on this LLM
            _, pf_ext_ev, pf_ext_act = pairs_ext.paper_first_venue_matrix(pf_w_sum_cfg)
            # Evaluate Facet-First Top-m (w_exp_b) on this LLM
            ff_topm_ext_ev = pairs_ext.evaluate_facet_first(
                mode="top_m", top_m=ff_topm_locked_m, weights=LOCKED_EXP_B_WEIGHTS
            )
            # Evaluate Facet-First Centroid (w_exp_b) on this LLM
            ff_cent_ext_ev = pairs_ext.evaluate_facet_first(
                mode="centroid", weights=LOCKED_EXP_B_WEIGHTS
            )
            # CV-locked Facet-First winner on this LLM
            ff_win_ext_ev = (
                ff_topm_ext_ev if ff_win_cfg["mode"] == "top_m" else ff_cent_ext_ev
            )

            # Evaluate Adaptive Fusion (CV-locked beta*) on this LLM
            af_scores_ext, _ = compute_adaptive_fusion_scores(
                ft_scores_mat,
                ff_win_ext_ev["scores_matrix"],
                q_masks_ext,
                beta=best_beta,
                facet_valid_mask=ff_win_ext_ev["valid_mask"],
                weights=LOCKED_EXP_B_WEIGHTS,
            )
            af_preds_ext = rank_venues_from_score_matrix(af_scores_ext, q_pids, self.candidates)
            af_ext_ev = pairs_ext.evaluate_venue_predictions(af_preds_ext)

            for mode_key, ev_obj, cfg_obj, act_obj in [
                ("facet_first_winner", ff_win_ext_ev, ff_win_cfg, ff_win_ext_ev["activation_stats"]),
                (
                    "facet_first_top_m",
                    ff_topm_ext_ev,
                    ff_cv["weighted_facet_a"]["top_m_best"]["config"],
                    ff_topm_ext_ev["activation_stats"],
                ),
                (
                    "facet_first_centroid",
                    ff_cent_ext_ev,
                    ff_cv["weighted_facet_a"]["centroid"]["config"],
                    ff_cent_ext_ev["activation_stats"],
                ),
                ("paper_first_sum_knn", pf_ext_ev, pf_w_sum_cfg, pf_ext_act),
            ]:
                vs_pf = (
                    {"win": 0, "tie": len(self.test), "loss": 0}
                    if mode_key == "paper_first_sum_knn"
                    else _compare_eval(ev_obj, pf_ext_ev, f"{ext_name}__paper_first_sum_knn", compute_boot=False)
                )
                d1_llm_rows_by_mode[mode_key].append(
                    {
                        "extractor": ext_name,
                        "mode_key": mode_key,
                        "config": cfg_obj,
                        "exp_a": exp_a_info,
                        "facet_stats": q_stats,
                        "avg_active_weight_mass_g": float(np.mean(g_q_ext)),
                        "problem_activation_rate": act_obj["problem_activation_rate"],
                        "dataset_activation_rate": act_obj["dataset_activation_rate"],
                        "problem_query_activation_rate": act_obj["problem_query_activation_rate"],
                        "dataset_query_activation_rate": act_obj["dataset_query_activation_rate"],
                        "activation_stats": act_obj,
                        "metrics": ev_obj["metrics"],
                        "tier_metrics": ev_obj["tier_metrics"],
                        "per_query": ev_obj["per_query"],
                        "vs_paper_first_same_llm": vs_pf,
                        "vs_fulltext": _compare_eval(ev_obj, ft_win_ev, "fulltext_winner", compute_boot=False),
                    }
                )

            # ==================================================================
            # EXP D2: Query Coverage Stratification for this LLM
            # High-Cov: mask_problem(q) == 1 and g(q) >= 0.80
            # Low-Cov: not (mask_problem(q) == 1 and g(q) >= 0.80)
            # ==================================================================
            high_cov_pids = []
            low_cov_pids = []
            high_g_vals = []
            low_g_vals = []
            for idx, p in enumerate(sorted_queries):
                has_prob = bool(q_masks_ext["problem"][idx])
                g_val = float(g_q_ext[idx])
                if has_prob and g_val >= 0.80 - 1e-9:
                    high_cov_pids.append(p["paper_id"])
                    high_g_vals.append(g_val)
                else:
                    low_cov_pids.append(p["paper_id"])
                    low_g_vals.append(g_val)

            strata_results = {}
            for stratum_key, stratum_pids, g_list in [
                ("all", q_pids, list(g_q_ext)),
                ("high_cov", high_cov_pids, high_g_vals),
                ("low_cov", low_cov_pids, low_g_vals),
            ]:
                if not stratum_pids:
                    strata_results[stratum_key] = {
                        "n": 0,
                        "paper_ids": [],
                        "mean_g_q": 0.0,
                        "methods": {},
                    }
                    continue
                ft_sub = pairs_ext.evaluate_venue_predictions(
                    ft_win_ev["predictions"], query_subset_pids=stratum_pids
                )
                pf_sub = pairs_ext.evaluate_venue_predictions(
                    pf_ext_ev["predictions"], query_subset_pids=stratum_pids
                )
                ff_sub = pairs_ext.evaluate_venue_predictions(
                    ff_win_ext_ev["predictions"], query_subset_pids=stratum_pids
                )
                ff_topm_sub = pairs_ext.evaluate_venue_predictions(
                    ff_topm_ext_ev["predictions"], query_subset_pids=stratum_pids
                )
                ff_cent_sub = pairs_ext.evaluate_venue_predictions(
                    ff_cent_ext_ev["predictions"], query_subset_pids=stratum_pids
                )
                af_sub = pairs_ext.evaluate_venue_predictions(
                    af_preds_ext, query_subset_pids=stratum_pids
                )

                methods_sub = {
                    "fulltext": {
                        "metrics": ft_sub["metrics"],
                        "tier_metrics": ft_sub["tier_metrics"],
                    },
                    "paper_first_sum_knn": {
                        "metrics": pf_sub["metrics"],
                        "tier_metrics": pf_sub["tier_metrics"],
                        "vs_fulltext": _compare_eval(pf_sub, ft_sub, "fulltext", compute_boot=False),
                    },
                    "facet_first": {
                        "metrics": ff_sub["metrics"],
                        "tier_metrics": ff_sub["tier_metrics"],
                        "vs_fulltext": _compare_eval(ff_sub, ft_sub, "fulltext", compute_boot=False),
                        "vs_paper_first": _compare_eval(ff_sub, pf_sub, "paper_first_sum_knn", compute_boot=False),
                    },
                    "facet_first_top_m": {
                        "metrics": ff_topm_sub["metrics"],
                        "tier_metrics": ff_topm_sub["tier_metrics"],
                        "vs_fulltext": _compare_eval(ff_topm_sub, ft_sub, "fulltext", compute_boot=False),
                    },
                    "facet_first_centroid": {
                        "metrics": ff_cent_sub["metrics"],
                        "tier_metrics": ff_cent_sub["tier_metrics"],
                        "vs_fulltext": _compare_eval(ff_cent_sub, ft_sub, "fulltext", compute_boot=False),
                    },
                    "adaptive_fusion": {
                        "metrics": af_sub["metrics"],
                        "tier_metrics": af_sub["tier_metrics"],
                        "vs_fulltext": _compare_eval(af_sub, ft_sub, "fulltext", compute_boot=False),
                    },
                }
                strata_results[stratum_key] = {
                    "n": len(stratum_pids),
                    "paper_ids": stratum_pids,
                    "mean_g_q": float(np.mean(g_list)) if g_list else 0.0,
                    "methods": methods_sub,
                }

            d2_by_llm[ext_name] = {
                "extractor": ext_name,
                "n_total": len(sorted_queries),
                "n_high_cov": len(high_cov_pids),
                "n_low_cov": len(low_cov_pids),
                "high_cov_share_pct": round(100.0 * len(high_cov_pids) / max(1, len(sorted_queries)), 2),
                "low_cov_share_pct": round(100.0 * len(low_cov_pids) / max(1, len(sorted_queries)), 2),
                "strata": strata_results,
            }

        # Pairwise vs Qwen-8B and exact Spearman/Kendall permutation correlations (n=5, 120 permutations) in Exp D1
        d1_rank_correlations = {}
        for mode_key, m_rows in d1_llm_rows_by_mode.items():
            ref_row = next((r for r in m_rows if r["extractor"] == "Qwen-8B"), None)
            if ref_row is not None:
                for r in m_rows:
                    if r["extractor"] == "Qwen-8B":
                        r["vs_qwen8b"] = {"win": 0, "tie": len(self.test), "loss": 0}
                    else:
                        r["vs_qwen8b"] = {
                            **win_tie_loss(r["per_query"]["true_rank"], ref_row["per_query"]["true_rank"]),
                            "mcnemar_hit@3": mcnemar_exact_test(
                                r["per_query"]["hit@3"], ref_row["per_query"]["hit@3"]
                            ),
                            "permutation_mrr": paired_permutation_test(
                                r["per_query"]["rr"],
                                ref_row["per_query"]["rr"],
                                n_resamples=n_resamples,
                                seed=self.seed,
                            ),
                        }
            exp_a_vec_map = {}
            down_vec_map = {}
            for r in m_rows:
                ext = r["extractor"]
                if ext in EXP_A_RAW_METRICS:
                    exp_a_vec_map[ext] = {
                        **{k: v for k, v in EXP_A_RAW_METRICS[ext].items() if k != "exp_a_wall_seconds"},
                        "test_facet_coverage_pct": r["facet_stats"]["avg_facet_coverage_pct"],
                        "avg_facet_words": r["facet_stats"]["avg_facet_words"],
                        "problem_activation_rate": r["problem_activation_rate"],
                        "dataset_activation_rate": r["dataset_activation_rate"],
                        "avg_active_weight_mass_g": r["avg_active_weight_mass_g"],
                    }
                    down_vec_map[ext] = {
                        k: r["metrics"][k]
                        for k in ("hit@1", "hit@3", "hit@5", "mrr", "macro_hit@3", "macro_mrr", "discipline_hit@1")
                        if k in r["metrics"]
                    }
            d1_rank_correlations[mode_key] = rank_correlation_matrix(exp_a_vec_map, down_vec_map)

        # ======================================================================
        # EXP D3: Complementary Signal & Intra-Discipline Disambiguation
        # ======================================================================
        q_masks_base = final.facet_query_masks()
        ff_win_base_ev = final.evaluate_facet_first(
            mode=ff_win_cfg["mode"],
            top_m=ff_win_cfg.get("top_m", 3),
            weights=LOCKED_EXP_B_WEIGHTS,
        )
        af_scores_base, g_q_base = compute_adaptive_fusion_scores(
            ft_scores_mat,
            ff_win_base_ev["scores_matrix"],
            q_masks_base,
            beta=best_beta,
            facet_valid_mask=ff_win_base_ev["valid_mask"],
            weights=LOCKED_EXP_B_WEIGHTS,
        )
        af_preds_base = rank_venues_from_score_matrix(af_scores_base, q_pids, self.candidates)
        af_base_ev = final.evaluate_venue_predictions(af_preds_base)

        # Coarse-to-Fine predictions for C in {5, 10} x Stage-2 in {facet_first, adaptive_fusion}
        c2f_evals = {}
        for stage2_name, s2_mat, s2_vm in [
            ("facet_first", ff_win_base_ev["scores_matrix"], ff_win_base_ev["valid_mask"]),
            ("adaptive_fusion", af_scores_base, None),
        ]:
            for c_val in top_cs:
                c_int = int(c_val)
                key = f"c2f_{stage2_name}_c{c_int}"
                preds_c = rerank_coarse_to_fine_batch(
                    ft_win_ev["predictions"],
                    q_pids,
                    s2_mat,
                    self.candidates,
                    top_c=c_int,
                    stage2_valid_mask=s2_vm,
                )
                c2f_evals[key] = final.evaluate_venue_predictions(preds_c)

        d3_method_specs = [
            ("fulltext", f"Full-text Baseline ({ft_win_rec['config']['aggregation']})", ft_win_rec["config"], ft_win_rec["cv"], ft_win_ev),
            ("facet_first", f"Facet-First ({ff_win_cfg['mode']})", ff_win_cfg, ff_win_rec["cv"], ff_win_base_ev),
            ("adaptive_fusion", f"Coverage-Aware Adaptive Fusion (beta={best_beta})", af_win_rec["config"], af_win_rec["cv"], af_base_ev),
        ]
        for stage2_name, stage2_label in [("facet_first", "Facet-First"), ("adaptive_fusion", "Adaptive Fusion")]:
            for c_val in top_cs:
                c_int = int(c_val)
                key = f"c2f_{stage2_name}_c{c_int}"
                c_rec = tuning_d["coarse_to_fine"][stage2_name]["by_top_c"][str(c_int)]
                d3_method_specs.append(
                    (
                        key,
                        f"Coarse-to-Fine Reranking (C={c_int}, Stage-2: {stage2_label})",
                        c_rec["config"],
                        c_rec["cv"],
                        c2f_evals[key],
                    )
                )

        d3_rows = []
        d3_p_hit1 = {}
        d3_p_hit3 = {}
        d3_p_mrr = {}
        for m_key, m_label, cfg_obj, cv_obj, ev_obj in d3_method_specs:
            if m_key == "fulltext":
                boot = paired_bootstrap_ci(
                    ev_obj["predictions"], None, truth, self.candidates, n_boot=n_boot, seed=self.seed
                )
                sig = {}
            else:
                sig = _compare_eval(ev_obj, ft_win_ev, "fulltext", compute_boot=True)
                boot = sig.pop("bootstrap_ci")
                d3_p_hit1[m_key] = sig["mcnemar_hit@1"]["p_value"]
                d3_p_hit3[m_key] = sig["mcnemar_hit@3"]["p_value"]
                d3_p_mrr[m_key] = sig["permutation_mrr"]["p_value"]
            d3_rows.append(
                {
                    "method_key": m_key,
                    "label": m_label,
                    "config": cfg_obj,
                    "cv": cv_obj,
                    "metrics": ev_obj["metrics"],
                    "tier_metrics": ev_obj["tier_metrics"],
                    "per_query": ev_obj["per_query"],
                    "bootstrap_ci": boot,
                    "significance_vs_fulltext": sig,
                }
            )

        holm_d3_hit1 = holm_bonferroni(d3_p_hit1, alpha=0.05)
        holm_d3_hit3 = holm_bonferroni(d3_p_hit3, alpha=0.05)
        holm_d3_mrr = holm_bonferroni(d3_p_mrr, alpha=0.05)
        for row in d3_rows:
            mk = row["method_key"]
            if mk in holm_d3_hit3:
                row["significance_vs_fulltext"]["holm_hit@1"] = holm_d3_hit1[mk]
                row["significance_vs_fulltext"]["holm_hit@3"] = holm_d3_hit3[mk]
                row["significance_vs_fulltext"]["holm_mrr"] = holm_d3_mrr[mk]

        # Intra-Discipline Ambiguous Subset: Full-text's Top-3 predicted venues all belong to the exact same discipline
        intra_ambiguous_pids = []
        cross_disc_top3_pids = []
        intra_discipline_breakdown = defaultdict(int)
        for pid in q_pids:
            top3_v = [v for v, _ in ft_win_ev["predictions"][pid][:3]]
            top3_d = [VENUE_DISCIPLINE_MAP.get(v) for v in top3_v]
            if len(top3_v) >= 3 and all(d is not None for d in top3_d) and len(set(top3_d)) == 1:
                intra_ambiguous_pids.append(pid)
                intra_discipline_breakdown[str(top3_d[0])] += 1
            else:
                cross_disc_top3_pids.append(pid)

        def _eval_d3_subset(subset_pids):
            if not subset_pids:
                return {"n": 0, "paper_ids": [], "rows": []}
            ft_sub = final.evaluate_venue_predictions(
                ft_win_ev["predictions"], query_subset_pids=subset_pids
            )
            sub_rows = []
            for m_key, m_label, cfg_obj, _, ev_obj in d3_method_specs:
                ev_sub = final.evaluate_venue_predictions(
                    ev_obj["predictions"], query_subset_pids=subset_pids
                )
                sig_sub = (
                    {}
                    if m_key == "fulltext"
                    else _compare_eval(ev_sub, ft_sub, "fulltext", compute_boot=False)
                )
                sub_rows.append(
                    {
                        "method_key": m_key,
                        "label": m_label,
                        "n": len(subset_pids),
                        "metrics": ev_sub["metrics"],
                        "tier_metrics": ev_sub["tier_metrics"],
                        "significance_vs_fulltext": sig_sub,
                    }
                )
            return {
                "n": len(subset_pids),
                "paper_ids": subset_pids,
                "rows": sub_rows,
            }

        intra_subset_eval = _eval_d3_subset(intra_ambiguous_pids)
        intra_subset_eval["discipline_distribution"] = dict(intra_discipline_breakdown)
        cross_subset_eval = _eval_d3_subset(cross_disc_top3_pids)

        # ======================================================================
        # EXP D4: Win/Loss Case Stratification
        # ======================================================================
        # Precompute 4 diagnostic features for each of the 168 Test queries
        query_features = []
        whole_sim = final.sim["whole_text"]
        k_nov = min(10, whole_sim.shape[1]) if whole_sim.ndim == 2 else 0
        for idx, p in enumerate(self.test):
            pid = p["paper_id"]
            abs_words = len(str(p.get("abstract", "")).split())
            g_val = float(g_q_base[idx])
            active_cnt = int(sum(bool(q_masks_base[f][idx]) for f in FACET_KEYS))
            true_v = p["conference_id"]
            v_tier = classify_venue_tier(final.train_venue_counts.get(true_v, 0))
            if k_nov > 0:
                top_sims = np.sort(whole_sim[idx])[-k_nov:]
                novelty = float(1.0 - np.mean(top_sims))
            else:
                novelty = 1.0
            query_features.append(
                {
                    "paper_id": pid,
                    "true_venue": true_v,
                    "venue_tier": v_tier,
                    "abstract_word_count": float(abs_words),
                    "active_weight_mass": g_val,
                    "active_facet_count": float(active_cnt),
                    "lexical_novelty_proxy": novelty,
                    "has_problem": bool(q_masks_base["problem"][idx]),
                    "has_dataset": bool(q_masks_base["dataset"][idx]),
                }
            )

        def _stratify_win_loss(ev_new, comparison_label):
            ranks_full = ft_win_ev["per_query"]["true_rank"]
            ranks_new = ev_new["per_query"]["true_rank"]
            groups = {"win": [], "tie": [], "loss": []}
            for idx, (rf, rn) in enumerate(zip(ranks_full, ranks_new)):
                rec = {
                    **query_features[idx],
                    "rank_full": int(rf),
                    "rank_new": int(rn),
                    "rank_improvement": int(rf - rn),
                }
                if rn < rf:
                    groups["win"].append(rec)
                elif rn == rf:
                    groups["tie"].append(rec)
                else:
                    groups["loss"].append(rec)

            cont_keys = (
                "abstract_word_count",
                "active_weight_mass",
                "active_facet_count",
                "lexical_novelty_proxy",
            )
            group_summaries = {}
            for g_name, items in groups.items():
                tier_cnts = Counter(it["venue_tier"] for it in items)
                n_g = len(items)
                feat_summary = {}
                for ck in cont_keys:
                    vals = [it[ck] for it in items]
                    feat_summary[ck] = {
                        "mean": float(np.mean(vals)) if vals else 0.0,
                        "median": float(np.median(vals)) if vals else 0.0,
                        "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
                    }
                group_summaries[g_name] = {
                    "n": int(n_g),
                    "share_pct": round(100.0 * n_g / max(1, len(self.test)), 2),
                    "continuous_features": feat_summary,
                    "venue_tier_dist": {
                        "counts": {t: int(tier_cnts.get(t, 0)) for t in ("head", "mid", "tail")},
                        "pcts": {
                            t: round(100.0 * int(tier_cnts.get(t, 0)) / n_g, 2) if n_g > 0 else 0.0
                            for t in ("head", "mid", "tail")
                        },
                    },
                }

            mw_tests = {}
            for ck in cont_keys:
                w_vals = [it[ck] for it in groups["win"]]
                l_vals = [it[ck] for it in groups["loss"]]
                mw_tests[ck] = mann_whitney_u_test(w_vals, l_vals)

            tier_test = tier_contingency_test(
                group_summaries["win"]["venue_tier_dist"]["counts"],
                group_summaries["loss"]["venue_tier_dist"]["counts"],
            )

            top_wins = sorted(
                groups["win"], key=lambda r: (-r["rank_improvement"], r["rank_new"], r["paper_id"])
            )[:10]
            top_losses = sorted(
                groups["loss"], key=lambda r: (r["rank_improvement"], -r["rank_new"], r["paper_id"])
            )[:10]

            return {
                "label": comparison_label,
                "n_total": len(self.test),
                "n_win": len(groups["win"]),
                "n_tie": len(groups["tie"]),
                "n_loss": len(groups["loss"]),
                "groups": group_summaries,
                "mann_whitney_win_vs_loss": mw_tests,
                "venue_tier_test_win_vs_loss": tier_test,
                "top_win_examples": top_wins,
                "top_loss_examples": top_losses,
            }

        c2f_af_c5_ev = c2f_evals.get(f"c2f_adaptive_fusion_c{int(top_cs[0])}", af_base_ev)
        c2f_ff_c5_ev = c2f_evals.get(f"c2f_facet_first_c{int(top_cs[0])}", ff_win_base_ev)
        d4_comparisons = {
            "facet_first_vs_fulltext": _stratify_win_loss(
                ff_win_base_ev, "Facet-First vs Full-text"
            ),
            "adaptive_fusion_vs_fulltext": _stratify_win_loss(
                af_base_ev, "Coverage-Aware Adaptive Fusion vs Full-text"
            ),
            "c2f_adaptive_c5_vs_fulltext": _stratify_win_loss(
                c2f_af_c5_ev, f"Coarse-to-Fine (C={int(top_cs[0])}, Adaptive Fusion) vs Full-text"
            ),
            "c2f_facet_c5_vs_fulltext": _stratify_win_loss(
                c2f_ff_c5_ev, f"Coarse-to-Fine (C={int(top_cs[0])}, Facet-First) vs Full-text"
            ),
        }

        payload = {
            "metadata": self.metadata,
            "tuning_id": tuning_d["tuning_id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "locked_exp_b_weights": dict(LOCKED_EXP_B_WEIGHTS),
            "selected_configs": {
                "fulltext_winner": ft_win_rec["config"],
                "facet_first_winner": ff_win_rec["config"],
                "adaptive_fusion_winner": af_win_rec["config"],
                "coarse_to_fine_facet_first_winner": tuning_d["coarse_to_fine"]["facet_first"]["best"]["config"],
                "coarse_to_fine_adaptive_fusion_winner": tuning_d["coarse_to_fine"]["adaptive_fusion"]["best"]["config"],
            },
            "exp_d1": {
                "paradigm_rows": d1_rows,
                "cross_llm_by_mode": d1_llm_rows_by_mode,
                "rank_correlations": d1_rank_correlations,
            },
            "exp_d2": {
                "criterion": "High-Cov: mask_problem(q) == 1 and g(q) >= 0.80; Low-Cov: complement",
                "by_extractor": d2_by_llm,
            },
            "exp_d3": {
                "all_test_rows": d3_rows,
                "intra_discipline_ambiguous_subset": intra_subset_eval,
                "cross_discipline_top3_subset": cross_subset_eval,
            },
            "exp_d4": {
                "comparisons": d4_comparisons,
            },
        }
        save_json(target, payload, overwrite)
        return payload


def numeric_list(text, kind=float):
    try:
        values = sorted(set(kind(x.strip()) for x in text.split(",") if x.strip()))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Expected comma-separated numbers") from exc
    if not values or any(not math.isfinite(v) for v in values):
        raise argparse.ArgumentTypeError("Grid must be nonempty and finite")
    return values


def parser(default_stage="tune"):
    result = argparse.ArgumentParser(description="Leakage-free IEEE conference experiments and 4-table report")
    result.add_argument(
        "--stage",
        choices=["tune", "test", "analyze", "benchmark", "exp_d", "report", "all"],
        default=default_stage,
    )
    result.add_argument("--embedding-backend", choices=[*BACKENDS, "all"], default="tfidf")
    result.add_argument("--split-dir", default=DEFAULT_SPLIT)
    result.add_argument("--facets-path", default=DEFAULT_FACETS, help="Reference Qwen-8B Raw facets (never validated_silver.jsonl)")
    result.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    result.add_argument("--report-path", default="../output/report_gated_facet_gridsearch_experiments.md")
    result.add_argument("--n-splits", type=int, default=5)
    result.add_argument("--seed", type=int, default=42)
    result.add_argument("--k-list", default="5,10,15,20,25,30")
    result.add_argument("--tau-list", default=None)
    result.add_argument("--kappa-list", default="5,10,20")
    result.add_argument("--metric", choices=METRICS, default="hit@3")
    result.add_argument("--embedding-model", default=None)
    result.add_argument("--device", default=None)
    result.add_argument("--batch-size", type=int, default=16)
    result.add_argument("--extractor-manifest", default=None, help="JSON object: extractor name -> test facets file")
    result.add_argument("--overwrite", action="store_true", help="Explicitly replace existing v2 artifacts")
    return result


def main(default_stage="tune", argv=None):
    args = parser(default_stage).parse_args(argv)
    assert_not_validated_silver(args.facets_path)
    root = get_repo_root()

    def resolve(value):
        path = Path(value)
        return path if path.is_absolute() else root / path

    output = resolve(args.output_dir)
    if args.stage == "report":
        from .report_experiments import write_exp_d_report, write_report
        write_report(output, resolve(args.report_path), args.overwrite)
        write_exp_d_report(output, overwrite=args.overwrite)
        return
    ks = numeric_list(args.k_list, int)
    kappas = numeric_list(args.kappa_list)
    if min(ks) <= 0 or min(kappas) <= 0 or args.batch_size <= 0:
        raise ValueError("k, kappa and batch size must be positive")
    train, test, catalog, _ = load_dataset(args.split_dir, args.facets_path, root, require_coverage=True)
    extractors = None
    if args.stage in ("benchmark", "exp_d", "all"):
        manifest = {
            "Qwen-8B": args.facets_path,
            **{
                name: f"data/conference_recommendation_dataset/generated_facets/{folder}/facets_silver.jsonl"
                for name, folder in [
                    ("Gemma-9B", "Gemma9B"),
                    ("Qwen-14B", "Qwen14B"),
                    ("Llama-8B", "Llama8B"),
                    ("Qwen-4B", "Qwen4B"),
                ]
            },
        }
        if args.extractor_manifest:
            manifest = json.loads(resolve(args.extractor_manifest).read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or not manifest:
            raise ValueError("Extractor manifest must be a nonempty JSON object")
        extractors = {}
        for name, path in manifest.items():
            assert_not_validated_silver(path)
            frozen_train, queries, _, _ = load_dataset(
                args.split_dir, args.facets_path, root, test_facets_path=path, require_coverage=True
            )
            if digest(frozen_train) != digest(train):
                raise ValueError(f"Extractor {name} changed reference train")
            extractors[name] = queries
    backends = ("bert", "specter2") if args.embedding_backend == "all" else [args.embedding_backend]
    if args.embedding_model and len(backends) > 1:
        raise ValueError("--embedding-model requires a single backend")
    for backend in backends:
        config = {"batch_size": args.batch_size}
        if args.embedding_model:
            config["model_name"] = args.embedding_model
        if args.device:
            config["device"] = args.device
        experiment = Experiment(train, test, catalog, backend, config, args.n_splits, args.seed, output)
        taus = (
            numeric_list(args.tau_list)
            if args.tau_list
            else (
                [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
                if backend == "tfidf"
                else [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
            )
        )
        if any(t < -1 or t > 1 for t in taus):
            raise ValueError("tau must lie in cosine range [-1, 1]")
        if args.stage in ("tune", "all"):
            experiment.tune(ks, taus, kappas, args.metric, args.overwrite)
        if args.stage in ("test", "all"):
            experiment.evaluate_test(args.overwrite)
        if args.stage in ("analyze", "all"):
            experiment.analyze(args.overwrite)
        if args.stage in ("benchmark", "all"):
            experiment.benchmark(extractors, args.overwrite)
        if args.stage in ("exp_d", "all"):
            n_res = 200 if len(test) < 20 else 10000
            experiment.run_exp_d(
                extractors,
                overwrite=args.overwrite,
                n_resamples=n_res,
                ks=ks,
                metric=args.metric,
            )
    if args.stage in ("exp_d", "all"):
        from .report_experiments import write_exp_d_report
        write_exp_d_report(output, overwrite=True if args.overwrite else False)
    if args.stage == "all":
        from .report_experiments import write_report
        write_report(output, resolve(args.report_path), args.overwrite)
