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
from .metrics import evaluate_predictions_detailed
from .ranking import aggregate_venue_scores, observed, rank_neighbors, validate_weights
from .significance import (
    holm_bonferroni,
    mcnemar_exact_test,
    paired_bootstrap_ci,
    paired_permutation_test,
    rank_correlation_matrix,
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
        self.embedding_dim = 0
        for field in ("whole_text",) + FACET_KEYS:
            left = [store.get_vectors(p["paper_id"]).get(field) for p in queries]
            right = [store.get_vectors(p["paper_id"]).get(field) for p in train]
            mask_l = np.array([observed(v) for v in left], dtype=bool)
            mask_r = np.array([observed(v) for v in right], dtype=bool)
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
                row["config"].get("k", row["config"].get("m", 0)),
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
        """Choose the locked primary Weighted Facet operating point from Train CV."""
        ieee = tuning.get("ieee_methods", {})
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
    result.add_argument("--stage", choices=["tune", "test", "analyze", "benchmark", "report", "all"], default=default_stage)
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
        from .report_experiments import write_report
        write_report(output, resolve(args.report_path), args.overwrite)
        return
    ks = numeric_list(args.k_list, int)
    kappas = numeric_list(args.kappa_list)
    if min(ks) <= 0 or min(kappas) <= 0 or args.batch_size <= 0:
        raise ValueError("k, kappa and batch size must be positive")
    train, test, catalog, _ = load_dataset(args.split_dir, args.facets_path, root, require_coverage=True)
    extractors = None
    if args.stage in ("benchmark", "all"):
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
    if args.stage == "all":
        from .report_experiments import write_report
        write_report(output, resolve(args.report_path), args.overwrite)
