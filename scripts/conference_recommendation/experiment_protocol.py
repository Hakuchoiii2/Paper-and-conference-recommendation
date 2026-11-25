"""Leakage-free CV, frozen evaluation and auditable experiment artifacts.

All model selection uses train CV only. Held-out analyses never update tuning.
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
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .data_loader import FACET_KEYS, get_repo_root, load_dataset
from .feature_loader import FacetFeatureStore, cosine_similarity, TfidfEmbeddingBackend
from .metrics import evaluate_predictions
from .ranking import observed, validate_weights, rank_neighbors

PROTOCOL = "conference-cv-v2"
DEFAULT_SPLIT = "data/conference_recommendation_dataset/5_mapping_reviewed/splits/temporal_2015_2016_2019_clean"
DEFAULT_FACETS = "data/exp_a/generated/facets_silver.jsonl"
DEFAULT_OUTPUT = "results/conference_recommendation_v2"
SOLUTION_FACETS = FACET_KEYS[1:]
METRICS = ("hit@1", "hit@3", "hit@5", "mrr", "macro_hit@3", "macro_mrr")
METHODS = ("whole_text", "flat_5_facet", "gated")
BACKENDS = ("tfidf", "specter", "bge-small")
WEIGHT_PRESETS = {
    "default": dict(zip(SOLUTION_FACETS, (.3, .3, .2, .2))),
    "equal": dict.fromkeys(SOLUTION_FACETS, .25),
    "method_heavy": dict(zip(SOLUTION_FACETS, (.2, .5, .15, .15))),
    "task_heavy": dict(zip(SOLUTION_FACETS, (.5, .2, .15, .15))),
    "method_task_focus": dict(zip(SOLUTION_FACETS, (.4, .4, .1, .1))),
    "dataset_focus": dict(zip(SOLUTION_FACETS, (.2, .2, .4, .2))),
}
# Search presets keep historical names, but each removal preserves the other ratios.
for _facet in SOLUTION_FACETS:
    _weights = dict(WEIGHT_PRESETS["default"])
    _weights[_facet] = 0.0
    WEIGHT_PRESETS["ablation_no_" + ("contrib" if _facet == "contribution" else _facet)] = validate_weights(_weights, SOLUTION_FACETS)

FLAT_5_FACET_PRESETS = {"flat_equal": dict.fromkeys(FACET_KEYS, .2)}
for _facet in ("problem", "task", "method", "dataset"):
    FLAT_5_FACET_PRESETS[f"flat_{_facet}_heavy"] = {f: .4 if f == _facet else .15 for f in FACET_KEYS}
FLAT_5_FACET_PRESETS["flat_method_task_focus"] = dict(zip(FACET_KEYS, (.2, .3, .3, .1, .1)))
for _facet in ("problem", "task", "method", "dataset"):
    FLAT_5_FACET_PRESETS[f"flat_ablation_no_{_facet}"] = {f: 0.0 if f == _facet else .25 for f in FACET_KEYS}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def save_json(path, payload, overwrite=False):
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; use --overwrite to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
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
    # Offset successive classes so remainder samples do not all enter fold zero.
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


class PairMatrices:
    """Query x reference similarities, with explicit missingness per field."""
    def __init__(self, store, train, queries, candidates):
        self.train, self.queries = train, queries
        self.candidates = sorted(candidates)
        self.sim, self.obs = {}, {}
        for field in ("whole_text",) + FACET_KEYS:
            left = [store.get_vectors(p["paper_id"]).get(field) for p in queries]
            right = [store.get_vectors(p["paper_id"]).get(field) for p in train]
            mask_l = np.array([observed(v) for v in left], dtype=bool)
            mask_r = np.array([observed(v) for v in right], dtype=bool)
            self.obs[field] = mask_l[:, None] & mask_r[None, :]
            matrix = np.zeros((len(left), len(right)), dtype=np.float64)
            sample = next((v for v in left + right if observed(v)), None)
            if sample is not None and not isinstance(sample, dict):
                # Dense vectors are fixed encodings; normalization also covers custom backends.
                def stack(values):
                    arr = np.array([v if observed(v) else np.zeros(len(sample)) for v in values], dtype=float)
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
        ix = np.ix_(query_indices, train_indices)
        result.sim = {f: m[ix] for f, m in self.sim.items()}
        result.obs = {f: m[ix] for f, m in self.obs.items()}
        return result

    def scores(self, config):
        method = config["method"]
        if method == "whole_text":
            return self.sim["whole_text"]
        facets = FACET_KEYS if method == "flat_5_facet" else SOLUTION_FACETS
        weights = validate_weights(config["weights"], facets)
        numerator = np.zeros_like(self.sim["problem"])
        denominator = np.zeros_like(numerator)
        for f, weight in weights.items():
            numerator += weight * self.sim[f] * self.obs[f]
            denominator += weight * self.obs[f]
        result = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)
        if method == "gated" and config.get("gate_enabled", True):
            z = config["kappa"] * (self.sim["problem"] - config["tau"])
            gate = 1 / (1 + np.exp(-np.clip(z, -20, 20)))
            gate[z >= 20] = 1.0
            gate[z <= -20] = 0.0
            gate[~self.obs["problem"]] = .5
            result *= gate
        return result

    def evaluate_scores(self, scores, k):
        pids = [p["paper_id"] for p in self.train]
        venues = [p["conference_id"] for p in self.train]
        predictions = {p["paper_id"]: rank_neighbors(pids, venues, row, self.candidates, k)
                       for p, row in zip(self.queries, scores)}
        truth = {p["paper_id"]: p["conference_id"] for p in self.queries}
        summary, per_venue = evaluate_predictions(predictions, truth, self.candidates)
        return {"metrics": summary, "per_venue": per_venue, "predictions": predictions}

    def evaluate(self, config):
        return self.evaluate_scores(self.scores(config), config["k"])


class Experiment:
    def __init__(self, train, test, candidates, backend="tfidf", backend_config=None,
                 n_splits=5, seed=42, output_dir=None):
        self.train = sorted(train, key=lambda p: p["paper_id"])
        self.test = sorted(test, key=lambda p: p["paper_id"])
        self.candidates = sorted(candidates)
        self.backend, self.backend_config = backend, backend_config or {}
        self.seed = seed
        self.folds = get_stratified_folds(self.train, n_splits, seed)
        if not self.test or not self.candidates:
            raise ValueError("Test set and candidate catalog must be nonempty")
        if set(p["paper_id"] for p in train) & set(p["paper_id"] for p in test):
            raise ValueError("Train/test overlap")
        if len({p['paper_id'] for p in train}) != len(train) or len({p['paper_id'] for p in test}) != len(test):
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
        for name in ("numpy", "torch", "sentence-transformers"):
            try:
                versions[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                pass
        source_files = ("experiment_protocol.py", "feature_loader.py", "ranking.py", "metrics.py", "data_loader.py")
        source_digest = digest({name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                for name in source_files})
        model_name = self.backend_config.get("model_name", {
            "tfidf": None, "specter": "sentence-transformers/allenai-specter",
            "bge-small": "BAAI/bge-small-en-v1.5"}.get(self.backend))
        counts = defaultdict(int)
        for paper in self.train:
            counts[paper["conference_id"]] += 1
        return {"protocol": PROTOCOL, "source_digest": source_digest, "backend": self.backend,
                "backend_config": self.backend_config, "embedding_model": model_name,
                "train_digest": digest(self.train), "test_digest": digest(self.test),
                "candidates": self.candidates, "n_train": len(self.train), "n_test": len(self.test),
                "n_splits": len(self.folds), "seed": self.seed, "std_ddof": 1,
                "tfidf_fit": "reference_only_per_field; OOV ignored",
                "tie_break": "neighbor score desc, paper_id asc; venue score desc, venue_id asc",
                "fold_paper_ids": [[self.train[i]["paper_id"] for i in f] for f in self.folds],
                "rare_train_venues": {v: n for v, n in sorted(counts.items()) if n < len(self.folds)},
                "versions": versions}

    def path(self, stage):
        return self.output / f"{stage}_{self.backend.replace('-', '_')}.json"

    def build_cv(self):
        if self.cv_pairs is not None:
            return self.cv_pairs
        self.cv_pairs = []
        dense_pairs = None
        if self.backend != "tfidf":
            store = FacetFeatureStore(self.train, [], backend=self.backend, backend_config=self.backend_config)
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
        store = FacetFeatureStore(self.train, queries_arg,
                                  backend=self.encoder if self.encoder is not None else self.backend,
                                  backend_config=self.backend_config)
        if self.backend != "tfidf":
            self.encoder = store.backend
        result = PairMatrices(store, self.train, queries_arg, self.candidates)
        if queries is None:
            self.final_pairs = result
        return result

    def cv(self, config):
        return aggregate_folds([pair.evaluate(config)["metrics"] for pair in self.build_cv()])

    def tune(self, ks, taus, kappas, metric="hit@3", overwrite=False):
        tag = self.backend.replace("-", "_")
        targets = [self.path("tuning"), self.output / f"grid_search_all_{tag}.csv", self.output / f"grid_search_folds_{tag}.csv"]
        if not overwrite and any(path.exists() for path in targets):
            raise FileExistsError(f"Tuning JSON/CSV already exists in {self.output}; use --overwrite")
        pairs = self.build_cv()
        grids = {
            "whole_text": [{"method": "whole_text", "k": k} for k in ks],
            "flat_5_facet": [{"method": "flat_5_facet", "k": k, "preset": name, "weights": weights}
                             for (name, weights), k in itertools.product(FLAT_5_FACET_PRESETS.items(), ks)],
            "gated": [{"method": "gated", "k": k, "tau": tau, "kappa": kappa, "preset": name, "weights": weights}
                      for (name, weights), tau, kappa, k in itertools.product(WEIGHT_PRESETS.items(), taus, kappas, ks)],
        }
        defaults = {
            "whole_text": {"method": "whole_text", "k": 10},
            "flat_5_facet": {"method": "flat_5_facet", "k": 10, "preset": "flat_equal", "weights": FLAT_5_FACET_PRESETS["flat_equal"]},
            "gated": {"method": "gated", "k": 10, "tau": .45, "kappa": 10., "preset": "default", "weights": WEIGHT_PRESETS["default"]},
        }
        methods = {}
        for method, configs in grids.items():
            print(f"[{self.backend}] CV {method}: {len(configs)} configurations", flush=True)
            records = []
            # Neighbor order is independent of k: compute a similarity matrix once per other parameter tuple.
            cache_key, cached = None, None
            for config in configs:
                key = digest({k: v for k, v in config.items() if k != "k"})
                if key != cache_key:
                    cached = [pair.scores(config) for pair in pairs]
                    cache_key = key
                metrics = aggregate_folds([pair.evaluate_scores(scores, config["k"])["metrics"] for pair, scores in zip(pairs, cached)])
                records.append({"config": copy.deepcopy(config), "cv": metrics})
                if len(records) % 100 == 0:
                    print(f"[{self.backend}] {method}: {len(records)}/{len(configs)}", flush=True)
            # Stable, declared tie-breaking, independent of traversal/input order.
            records.sort(key=lambda row: (-row["cv"][metric], -row["cv"]["mrr"],
                                          -row["cv"]["macro_hit@3"], row["config"]["k"], digest(row["config"])))
            default = {"config": defaults[method], "cv": self.cv(defaults[method])}
            methods[method] = {"best": records[0], "default": default, "cv_all": records}
        payload = {"metadata": self.metadata, "created_at": datetime.now(timezone.utc).isoformat(),
                   "selection_metric": metric,
                   "selection_rule": f"max {metric}, max MRR, max macro-Hit@3, min k, config SHA256 asc",
                   "search_space": {"k": ks, "tau": taus, "kappa": kappas,
                                    "gated_presets": WEIGHT_PRESETS, "flat_presets": FLAT_5_FACET_PRESETS},
                   "methods": methods}
        payload["tuning_id"] = digest(payload)
        save_json(self.path("tuning"), payload, overwrite)
        self.export_grid_csv(payload)
        return payload

    def export_grid_csv(self, tuning):
        """One numeric row per grid configuration, plus a long table of all folds."""
        tag = self.backend.replace("-", "_")
        common = ["backend", "tuning_id", "method", "rank_within_method", "selected", "k", "tau", "kappa", "preset"]
        weight_fields = ["weight_" + f for f in FACET_KEYS]
        metric_fields = [column for metric in METRICS for column in ("cv_" + metric, "cv_" + metric + "_std")]
        fold_fields = [f"fold_{i + 1}_{metric}" for i in range(len(self.folds)) for metric in METRICS]
        rows, folds = [], []
        for method in METHODS:
            for rank, record in enumerate(tuning["methods"][method]["cv_all"], 1):
                config, cv = record["config"], record["cv"]
                row = {"backend": self.backend, "tuning_id": tuning["tuning_id"], "method": method,
                       "rank_within_method": rank, "selected": int(rank == 1),
                       **{key: config.get(key, "") for key in ("k", "tau", "kappa", "preset")},
                       **{"weight_" + f: config.get("weights", {}).get(f, "") for f in FACET_KEYS},
                       **{"cv_" + m: cv[m] for m in METRICS},
                       **{"cv_" + m + "_std": cv[m + "_std"] for m in METRICS}}
                for i, fold in enumerate(cv["fold_metrics"]):
                    row.update({f"fold_{i + 1}_{m}": fold[m] for m in METRICS})
                    folds.append({**{k: row[k] for k in common + weight_fields}, "fold": i + 1,
                                  "validation_size": fold["total_test_papers"], **{m: fold[m] for m in METRICS}})
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

    def evaluate_test(self, overwrite=False):
        tuning = self.load_tuning()
        if self.path("test").exists() and not overwrite:
            raise FileExistsError(f"{self.path('test')} exists; use --overwrite")
        pairs = self.build_final()
        rows = []
        for method in METHODS:
            for variant in ("default", "best"):
                config = tuning["methods"][method][variant]["config"]
                rows.append({"method": method, "variant": variant, "config": config, **pairs.evaluate(config)})
        # Exact expectation is reported as theoretical, never as a measured CV mean +/- std.
        n = len(self.candidates)
        random_expectation = {f"hit@{k}": min(k, n) / n for k in (1, 3, 5)}
        random_expectation["mrr"] = sum(1 / r for r in range(1, n + 1)) / n
        payload = {**self.envelope(tuning), "rows": rows, "random_theoretical": random_expectation}
        save_json(self.path("test"), payload, overwrite)
        return payload

    def analyze(self, overwrite=False):
        tuning = self.load_tuning()
        if self.path("analysis").exists() and not overwrite:
            raise FileExistsError(f"{self.path('analysis')} exists; use --overwrite")
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
        final = self.build_final()
        ablations = []
        for name, weights in presets:
            if weights is None:
                ablations.append({"name": name, "status": "undefined: removed the only nonzero facet"})
                continue
            config = {**best, "weights": weights, "preset": name}
            ablations.append({"name": name, "config": config, "cv": self.cv(config),
                              "test": final.evaluate(config)})
        gate_config = {**best, "gate_enabled": False}
        gate_ablation = {"config": gate_config, "cv": self.cv(gate_config), "test": final.evaluate(gate_config)}
        tau_grid = ([.15, .20, .25, .30, .35, .40, .45, .50] if self.backend == "tfidf"
                    else [.35, .40, .45, .50, .55, .60, .65, .70])
        sweeps = {"k": [5, 10, 15, 20, 25, 30], "tau": tau_grid, "kappa": [2., 5., 10., 15., 20., 30.]}
        sensitivity = {}
        for parameter, values in sweeps.items():
            sensitivity[parameter] = [{"value": value, "config": {**best, parameter: value},
                                       "cv": self.cv({**best, parameter: value})}
                                      for value in sorted(set(values + [best[parameter]]))]
        payload = {**self.envelope(tuning), "best_operating_point": best,
                   "facet_ablation_table2": ablations, "problem_gate_ablation": gate_ablation,
                   "sensitivity": sensitivity, "sensitivity_split": "train_cv_only",
                   "note": "Prespecified diagnostics; do not select a new config from held-out ablations."}
        save_json(self.path("analysis"), payload, overwrite)
        return payload

    def benchmark(self, extractor_queries, overwrite=False):
        tuning = self.load_tuning()
        if self.path("benchmark").exists() and not overwrite:
            raise FileExistsError(f"{self.path('benchmark')} exists; use --overwrite")
        best = tuning["methods"]["gated"]["best"]["config"]
        base_ids = {p["paper_id"] for p in self.test}
        rows = []
        for name, queries in extractor_queries.items():
            if {p["paper_id"] for p in queries} != base_ids or len(queries) != len(base_ids):
                raise ValueError(f"Extractor {name}: test IDs differ from frozen split")
            for paper, base in zip(sorted(queries, key=lambda p: p["paper_id"]), self.test):
                if {k: v for k, v in paper.items() if k != "facets"} != {k: v for k, v in base.items() if k != "facets"}:
                    raise ValueError(f"Extractor {name}: changed text or labels")
            pairs = self.build_final(sorted(queries, key=lambda p: p["paper_id"]))
            rows.append({"extractor": name, "config": best, "query_digest": digest(queries),
                         "frozen_train_digest": digest(self.train), **pairs.evaluate(best)})
        payload = {**self.envelope(tuning), "rows": rows}
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
    result = argparse.ArgumentParser(description="Leakage-free conference experiments and four-table Markdown report")
    result.add_argument("--stage", choices=["tune", "test", "analyze", "benchmark", "report", "all"], default=default_stage)
    result.add_argument("--embedding-backend", choices=[*BACKENDS, "all"], default="tfidf")
    result.add_argument("--split-dir", default=DEFAULT_SPLIT)
    result.add_argument("--facets-path", default=DEFAULT_FACETS, help="Reference Qwen-8B facets, covering train and test")
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
    result.add_argument("--batch-size", type=int, default=64)
    result.add_argument("--extractor-manifest", default=None, help="JSON object: extractor name -> test facets file")
    result.add_argument("--overwrite", action="store_true", help="Explicitly replace existing v2 artifacts")
    return result


def main(default_stage="tune", argv=None):
    args = parser(default_stage).parse_args(argv)
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
        manifest = ({"Qwen-8B": args.facets_path,
                     **{name: f"data/conference_recommendation_dataset/generated_facets/{folder}/facets_silver.jsonl"
                        for name, folder in [("Qwen-14B", "Qwen14B"), ("Qwen-4B", "Qwen4B"),
                                             ("Llama-8B", "Llama8B"), ("Gemma-9B", "Gemma9B")]}})
        if args.extractor_manifest:
            manifest = json.loads(resolve(args.extractor_manifest).read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or not manifest:
            raise ValueError("Extractor manifest must be a nonempty JSON object")
        extractors = {}
        for name, path in manifest.items():
            frozen_train, queries, _, _ = load_dataset(args.split_dir, args.facets_path, root,
                                                      test_facets_path=path, require_coverage=True)
            if digest(frozen_train) != digest(train):
                raise ValueError(f"Extractor {name} changed reference train")
            extractors[name] = queries
    backends = BACKENDS if args.embedding_backend == "all" else [args.embedding_backend]
    if args.embedding_model and len(backends) > 1:
        raise ValueError("--embedding-model requires a single backend")
    for backend in backends:
        config = {"batch_size": args.batch_size}
        if args.embedding_model:
            config["model_name"] = args.embedding_model
        if args.device:
            config["device"] = args.device
        experiment = Experiment(train, test, catalog, backend, config, args.n_splits, args.seed, output)
        taus = numeric_list(args.tau_list) if args.tau_list else ([.15, .20, .25, .30, .35, .40, .45, .50] if backend == "tfidf" else [.35, .40, .45, .50, .55, .60, .65, .70])
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
