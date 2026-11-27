"""Conference protocol regressions & IEEE standard unit tests (17 tests, CPU-only)."""
import copy
import csv
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.conference_recommendation.baselines import FlatFacetKNNReranker, WholeTextKNNReranker
from scripts.conference_recommendation.data_loader import FACET_KEYS, load_dataset
from scripts.conference_recommendation.experiment_protocol import (
    DEFAULT_FACETS,
    EXP_A_RAW_METRICS,
    FLAT_5_FACET_PRESETS,
    METRICS,
    WEIGHT_PRESETS,
    Experiment,
    PairMatrices,
    aggregate_folds,
    assert_not_validated_silver,
    get_stratified_folds,
    main,
    numeric_list,
)
from scripts.conference_recommendation.feature_loader import (
    CustomCallableBackend,
    FacetFeatureStore,
    format_dense_facet_text,
    format_dense_whole_text,
)
from scripts.conference_recommendation.metrics import (
    VENUE_DISCIPLINE_MAP,
    classify_venue_tier,
    evaluate_predictions_detailed,
)
from scripts.conference_recommendation.ranking import (
    LOCKED_EXP_B_WEIGHTS,
    compute_active_weight_mass,
    compute_adaptive_fusion_scores,
    compute_facet_first_venue_scores,
    rank_neighbors,
    rank_venues_from_score_row,
    rank_venues_per_venue_top_m,
    rank_venues_prior_norm,
    rank_venues_temp_softmax,
    rerank_coarse_to_fine,
)
from scripts.conference_recommendation.report_experiments import write_exp_d_report, write_report
from scripts.conference_recommendation.reranker import GatedFacetKNNReranker
from scripts.conference_recommendation.significance import (
    holm_bonferroni,
    mann_whitney_u_test,
    mcnemar_exact_test,
    paired_bootstrap_ci,
    paired_permutation_test,
    rank_correlation_matrix,
    tier_contingency_test,
    win_tie_loss,
)


def fixture():
    def paper(pid, topic, split):
        return dict(
            paper_id=pid,
            title=topic + " science",
            abstract="shared " + topic,
            conference_id="v_" + topic,
            split=split,
            facets={f: [topic + " " + f] for f in FACET_KEYS},
        )

    train = [paper(f"tr_{topic}_{i}", topic, "train") for topic in ("alpha", "beta") for i in range(6)]
    test = [paper(f"te_{topic}_{i}", topic, "test") for topic in ("alpha", "beta") for i in range(2)]
    train[0]["facets"]["problem"] = []
    train[2]["facets"]["dataset"] = []
    test[0]["facets"]["problem"] = []
    return train, test, ["v_alpha", "v_beta"]


class FeatureAndRankingTests(unittest.TestCase):
    def test_tfidf_queries_cannot_change_reference_vectors_or_idf(self):
        train, test, _ = fixture()
        first = FacetFeatureStore(train, test)
        altered = copy.deepcopy(test)
        for p in altered:
            p["title"] = "unseen_token " * 50
            p["facets"] = {f: ["never_in_training"] for f in FACET_KEYS}
        second = FacetFeatureStore(train, altered)
        for p in train:
            self.assertEqual(first.get_vectors(p["paper_id"]), second.get_vectors(p["paper_id"]))
        self.assertNotIn("unseen_token", second.field_backends["whole_text"].idf_dict)
        self.assertEqual(second.get_vectors(altered[0]["paper_id"])["problem"], {})
        changed_train = copy.deepcopy(train)
        changed_train[0]["facets"]["task"] = ["alpha " * 20]
        third = FacetFeatureStore(changed_train, test)
        self.assertEqual(
            first.get_vectors(train[0]["paper_id"])["whole_text"],
            third.get_vectors(train[0]["paper_id"])["whole_text"],
        )

    def test_matrix_runtime_parity_sparse_and_numpy_dense(self):
        train, test, venues = fixture()

        def encode(texts):
            return [np.array([text.count("alpha"), text.count("beta"), 1.0 if text.strip() else 0.0]) for text in texts]

        for backend in ("tfidf", CustomCallableBackend(encode)):
            store = FacetFeatureStore(train, test, backend=backend)
            pairs = PairMatrices(store, train, test, venues)
            configs = [
                dict(method="whole_text", k=3),
                dict(method="flat_5_facet", k=3, weights=FLAT_5_FACET_PRESETS["exp_b_weighted_a"]),
                dict(method="gated", k=3, tau=0.25, kappa=5.0, weights=WEIGHT_PRESETS["method_heavy"]),
            ]
            for config in configs:
                method = config["method"]
                kwargs = {k: v for k, v in config.items() if k != "method"}
                cls = {
                    "whole_text": WholeTextKNNReranker,
                    "flat_5_facet": FlatFacetKNNReranker,
                    "gated": GatedFacetKNNReranker,
                }[method]
                model = cls(store, train, **kwargs)
                predictions = pairs.evaluate(config)["predictions"]
                for paper in test:
                    actual = model.predict(paper["paper_id"], list(reversed(venues)))
                    expected = predictions[paper["paper_id"]]
                    self.assertEqual([v for v, _ in actual], [v for v, _ in expected])
                    np.testing.assert_allclose([s for _, s in actual], [s for _, s in expected], atol=1e-12)

    def test_missing_problem_gate_is_neutral_and_ties_stable(self):
        train, test, venues = fixture()
        store = FacetFeatureStore(train, test)
        model = GatedFacetKNNReranker(store, train, tau=0.25, kappa=5.0)
        self.assertEqual(model.compute_context_gate(None, {"x": 1}), 0.5)
        self.assertEqual(model.compute_context_gate(np.zeros(3), np.ones(3)), 0.5)
        a = rank_neighbors(["z", "a"], ["v_beta", "v_alpha"], [1.0, 1.0], venues, 1)
        b = rank_neighbors(["a", "z"], ["v_alpha", "v_beta"], [1.0, 1.0], venues[::-1], 1)
        self.assertEqual(a, b)
        self.assertEqual(a[0][0], "v_alpha")

    def test_fold_balance_stratification_and_input_order(self):
        train, _, _ = fixture()
        first = get_stratified_folds(train, 3)
        reverse = list(reversed(train))
        second = get_stratified_folds(reverse, 3)
        self.assertEqual(
            [[train[i]["paper_id"] for i in f] for f in first],
            [[reverse[i]["paper_id"] for i in f] for f in second],
        )
        for fold in first:
            self.assertEqual(len(fold), 4)
            self.assertEqual(len({train[i]["conference_id"] for i in fold}), 2)
        with self.assertRaises(ValueError):
            get_stratified_folds(train[:2], 5)
        rare = train[:3] + train[6:]
        folds = get_stratified_folds(rare, 5)
        self.assertEqual(sorted(i for fold in folds for i in fold), list(range(len(rare))))
        self.assertLessEqual(max(map(len, folds)) - min(map(len, folds)), 1)

    def test_sample_standard_deviation_and_weight_validation(self):
        summary = aggregate_folds([{m: v for m in METRICS} for v in (0.0, 0.5, 1.0)])
        self.assertEqual(summary["hit@3"], 0.5)
        self.assertEqual(summary["hit@3_std"], 0.5)
        train, test, _ = fixture()
        with self.assertRaises(ValueError):
            FlatFacetKNNReranker(FacetFeatureStore(train, test), train, weights={"task": 1})
        self.assertEqual(numeric_list("3,1,3", int), [1, 3])


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        self.train, self.test, self.venues = fixture()
        self.exp = Experiment(self.train, self.test, self.venues, n_splits=3, output_dir=self.output)

    def tearDown(self):
        self.temp.cleanup()

    def tune(self):
        return self.exp.tune([1, 3], [0.25], [5.0], agg_taus=(0.05,), alphas=(0.5,), ms=(1, 2))

    def test_end_to_end_artifacts_csv_counts_report_and_frozen_benchmark(self):
        tuning = self.tune()
        self.assertEqual(len(tuning["methods"]["gated"]["cv_all"]), 20)
        self.assertEqual(len(tuning["methods"]["flat_5_facet"]["cv_all"]), len(FLAT_5_FACET_PRESETS) * 2)
        with (self.output / "grid_search_all_tfidf.csv").open(encoding="utf-8-sig", newline="") as h:
            grid = list(csv.DictReader(h))
        with (self.output / "grid_search_folds_tfidf.csv").open(encoding="utf-8-sig", newline="") as h:
            folds = list(csv.DictReader(h))
        expected_grid = 2 + len(FLAT_5_FACET_PRESETS) * 2 + 20
        self.assertEqual(len(grid), expected_grid)
        self.assertEqual(len(folds), expected_grid * 3)
        self.assertEqual(sum(int(r["selected"]) for r in grid), 3)
        self.assertTrue(all(r["tuning_id"] == tuning["tuning_id"] for r in grid))
        test_result = self.exp.evaluate_test(n_resamples=200)
        self.assertEqual(len(test_result["rows"]), 6)
        self.assertTrue(len(test_result["ieee_rows"]) > 0)
        self.assertAlmostEqual(test_result["random_theoretical"]["mrr"], 0.75)
        analysis = self.exp.analyze()
        self.assertEqual(len(analysis["facet_ablation_table2"]), 10)
        self.assertEqual(len(analysis["ieee_ablation_temporal_drift"]), 7)  # Full + 5 facets + Zero-Imputation
        self.assertEqual(analysis["sensitivity_split"], "train_cv_only")
        altered = copy.deepcopy(self.test)
        altered[0]["facets"]["method"] = ["beta"]
        benchmark = self.exp.benchmark({"Qwen-8B": self.test, "Gemma-9B": altered}, n_resamples=200)
        qwen = benchmark["rows"][0]["metrics"]
        selected = next(r["metrics"] for r in test_result["rows"] if r["method"] == "gated" and r["variant"] == "best")
        self.assertEqual(qwen, selected)
        self.assertEqual(benchmark["rows"][0]["frozen_train_digest"], benchmark["rows"][1]["frozen_train_digest"])
        self.assertIn("equal_weight_facet", benchmark["ieee_benchmark"])
        self.assertIn("weighted_facet_a", benchmark["ieee_benchmark"])
        report = write_report(self.output, self.output / "report.md")
        text = report.read_text(encoding="utf-8")
        for title in ("Bảng 1", "Bảng 2", "Bảng 3", "Bảng 4", "Bộ 4 Bảng Kết quả Chuẩn Hội nghị IEEE"):
            self.assertIn(title, text)
        self.assertTrue((self.output / "report_tables/ieee_table1_main_results.csv").exists())
        self.assertTrue((self.output / "report_tables/ieee_table1_main_results.tex").exists())
        with self.assertRaises(FileExistsError):
            self.exp.evaluate_test()

    def test_tuning_does_not_access_final_or_test_scoring(self):
        with patch.object(self.exp, "build_final", side_effect=AssertionError("Test accessed while tuning")):
            tuning = self.tune()
        for method in tuning["methods"].values():
            self.assertEqual(len(method["best"]["cv"]["fold_metrics"]), 3)
        for pairs in self.exp.cv_pairs:
            self.assertFalse({p["paper_id"] for p in pairs.train} & {p["paper_id"] for p in pairs.queries})

    def test_dense_cv_reuses_one_encoder_and_excludes_self_neighbors(self):
        def encode(texts):
            return [np.array([float("alpha" in t), float("beta" in t), float(bool(t))]) for t in texts]

        encoder = CustomCallableBackend(encode)
        with patch("scripts.conference_recommendation.feature_loader.SentenceTransformerBackend", return_value=encoder) as constructor:
            exp = Experiment(self.train, self.test, self.venues, backend="bert", n_splits=3, output_dir=self.output)
            for pairs in exp.build_cv():
                self.assertFalse({p["paper_id"] for p in pairs.train} & {p["paper_id"] for p in pairs.queries})
                self.assertEqual(pairs.sim["problem"].shape, (4, 8))
            final = exp.build_final()
            self.assertEqual(final.sim["whole_text"].shape, (4, 12))
            self.assertIs(exp.encoder, encoder)
            self.assertEqual(constructor.call_count, 1)

    def test_provenance_mismatch_tampering_and_stale_report_rejected(self):
        self.tune()
        self.exp.evaluate_test(n_resamples=100)
        old = copy.deepcopy(self.exp.test)
        self.exp.test[0]["title"] = "changed"
        with self.assertRaisesRegex(ValueError, "test_digest"):
            self.exp.load_tuning()
        self.exp.test = old
        path = self.exp.path("test")
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["tuning_id"] = "stale"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Stale/mixed"):
            write_report(self.output, self.output / "report.md")
        path = self.exp.path("tuning")
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["methods"]["gated"]["best"]["config"]["k"] = 99
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.exp.load_tuning()

    def test_benchmark_missing_or_modified_papers_rejected(self):
        self.tune()
        with self.assertRaisesRegex(ValueError, "test IDs"):
            self.exp.benchmark({"Incomplete": self.test[:-1]})
        changed = copy.deepcopy(self.test)
        changed[0]["conference_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "text or labels"):
            self.exp.benchmark({"Changed": changed})

    def test_loader_overlay_is_strict_and_freezes_train(self):
        split = self.output / "split"
        split.mkdir()
        for name, rows in [
            ("train.jsonl", self.train),
            ("test.jsonl", self.test),
            ("conference_catalog.jsonl", [{"conference_id": v} for v in self.venues]),
        ]:
            (split / name).write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        (split / "label_map.json").write_text(json.dumps(dict.fromkeys(self.venues, 0)), encoding="utf-8")
        base = self.output / "base.jsonl"
        base.write_text(
            "\n".join(json.dumps({"paper_id": p["paper_id"], **p["facets"]}) for p in self.train + self.test),
            encoding="utf-8",
        )
        other = self.output / "other.jsonl"
        other.write_text(
            "\n".join(json.dumps({"paper_id": p["paper_id"], **{f: ["different"] for f in FACET_KEYS}}) for p in self.test),
            encoding="utf-8",
        )
        train, test, _, _ = load_dataset(split, base, ROOT, test_facets_path=other, require_coverage=True)
        self.assertEqual(train[0]["facets"], self.train[0]["facets"])
        self.assertEqual(test[0]["facets"]["task"], ["different"])
        other.write_text("", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Missing facets"):
            load_dataset(split, base, ROOT, test_facets_path=other, require_coverage=True)
        manifest = self.output / "manifest.json"
        manifest.write_text(json.dumps({"Qwen-8B": str(base)}), encoding="utf-8")
        main(
            argv=[
                "--stage", "all", "--embedding-backend", "tfidf",
                "--split-dir", str(split), "--facets-path", str(base),
                "--extractor-manifest", str(manifest), "--n-splits", "3",
                "--k-list", "1,3", "--tau-list", ".25", "--kappa-list", "5",
                "--output-dir", str(self.output / "cli"), "--report-path", str(self.output / "cli.md"),
            ]
        )
        self.assertTrue((self.output / "cli.md").exists())

    def test_missing_outputs_generate_honest_template(self):
        report = write_report(self.output, self.output / "template.md")
        text = report.read_text(encoding="utf-8")
        self.assertIn("Chưa chạy", text)
        self.assertNotIn("± 0.00%", text)


class IEEEStandardTests(unittest.TestCase):
    """5 new unit tests verifying IEEE venue aggregations, significance, Exp B parity, raw text & diagnostics."""

    def test_venue_aggregation_scale_invariance_and_tie_breaks(self):
        # Tail venue has 3 papers with high similarity (0.90, 0.88, 0.86);
        # Head venue has 3 papers (0.85, 0.84, 0.83) + 57 extra lower papers (0.70).
        tail_pids = [f"tail_{i}" for i in range(3)]
        tail_sims = [0.90, 0.88, 0.86]
        head_base_pids = [f"head_{i}" for i in range(3)]
        head_base_sims = [0.85, 0.84, 0.83]
        head_extra_pids = [f"head_extra_{i}" for i in range(57)]
        head_extra_sims = [0.70] * 57

        # 1. Per-Venue Top-m must be 100% invariant to duplicating lower-ranked Head papers
        r_small = rank_venues_per_venue_top_m(
            tail_pids + head_base_pids,
            ["v_tail"] * 3 + ["v_head"] * 3,
            tail_sims + head_base_sims,
            ["v_head", "v_tail"],
            m=3,
        )
        r_large = rank_venues_per_venue_top_m(
            tail_pids + head_base_pids + head_extra_pids,
            ["v_tail"] * 3 + ["v_head"] * 60,
            tail_sims + head_base_sims + head_extra_sims,
            ["v_head", "v_tail"],
            m=3,
        )
        self.assertEqual(r_small, r_large)
        self.assertEqual(r_large[0][0], "v_tail")
        self.assertAlmostEqual(r_large[0][1], (0.90 + 0.88 + 0.86) / 3.0)

        # 2. Temp-Softmax must sum to 1.0 over active venues and remain numerically stable with small tau
        r_temp = rank_venues_temp_softmax(
            tail_pids + head_base_pids,
            ["v_tail"] * 3 + ["v_head"] * 3,
            tail_sims + head_base_sims,
            ["v_head", "v_tail"],
            k=6,
            tau=0.02,
        )
        self.assertAlmostEqual(sum(s for _, s in r_temp), 1.0, places=10)
        self.assertEqual(r_temp[0][0], "v_tail")

        # 3. Prior-Norm must penalize high-frequency head venue relative to tail venue
        # Top-6 contains 3 tail papers (0.80) and 3 head papers (0.80); 57 extra head papers are at 0.70.
        r_prior = rank_venues_prior_norm(
            tail_pids + head_base_pids + head_extra_pids,
            ["v_tail"] * 3 + ["v_head"] * 60,
            [0.80] * 3 + [0.80] * 3 + [0.70] * 57,
            ["v_head", "v_tail"],
            k=6,
            tau=0.1,
            alpha=1.0,
        )
        self.assertEqual(r_prior[0][0], "v_tail")
        self.assertAlmostEqual(r_prior[0][1] / r_prior[1][1], 20.0, places=6)

    def test_significance_mcnemar_permutation_bootstrap_and_holm(self):
        # Exact analytical McNemar test: n_10=8, n_01=1 => p = 2 * (C(9,0) + C(9,1)) / 2^9 = 20 / 512 = 0.0390625
        hits_a = [1] * 8 + [0] * 1 + [1] * 5 + [0] * 6
        hits_b = [0] * 8 + [1] * 1 + [1] * 5 + [0] * 6
        mc = mcnemar_exact_test(hits_a, hits_b)
        self.assertEqual(mc["n_10"], 8)
        self.assertEqual(mc["n_01"], 1)
        self.assertAlmostEqual(mc["p_value"], 20.0 / 512.0, places=12)
        self.assertTrue(mc["significant_005"])

        # Permutation test determinism (seed=42)
        scores_a = [1.0, 0.5, 1.0, 0.5, 1.0, 1.0, 0.5, 1.0]
        scores_b = [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]
        p1 = paired_permutation_test(scores_a, scores_b, n_resamples=2000, seed=42)
        p2 = paired_permutation_test(scores_a, scores_b, n_resamples=2000, seed=42)
        self.assertEqual(p1["p_value"], p2["p_value"])
        self.assertLess(p1["p_value"], 0.05)

        # Paired Bootstrap CI
        preds_a = {f"p{i}": [("v1", 0.9), ("v2", 0.1)] for i in range(10)}
        preds_b = {f"p{i}": [("v2", 0.9), ("v1", 0.1)] for i in range(10)}
        truth = {f"p{i}": ("v1" if i < 5 else "v2") for i in range(10)}
        boot = paired_bootstrap_ci(preds_a, preds_b, truth, ["v1", "v2"], n_boot=500, seed=42)
        self.assertIn("ci_low", boot["macro_hit@3"])
        self.assertIn("delta_macro_hit@3", boot)

        # Holm-Bonferroni monotonicity
        hb = holm_bonferroni({"c1": 0.01, "c2": 0.04, "c3": 0.03}, alpha=0.05)
        self.assertAlmostEqual(hb["c1"]["adjusted_p"], 0.03)
        self.assertAlmostEqual(hb["c3"]["adjusted_p"], 0.06)
        self.assertAlmostEqual(hb["c2"]["adjusted_p"], 0.06)
        self.assertTrue(hb["c1"]["reject_null"])
        self.assertFalse(hb["c3"]["reject_null"])

        # Win/Tie/Loss sums to N
        wtl = win_tie_loss([1, 2, 3, 4], [2, 2, 1, 5])
        self.assertEqual(wtl, {"win": 2, "tie": 1, "loss": 1})
        self.assertEqual(sum(wtl.values()), 4)

    def test_exp_b_pairwise_scoring_and_missing_policy_parity(self):
        # Verify exact numerical parity with data/exp_b/ranking/scripts/05_weighted_ranking.py
        # Paper q has problem, task, method (missing dataset & contribution)
        # Paper c1 has problem, task, method -> denominator = 0.4 + 0.2 + 0.2 = 0.8
        # Paper c2 has ONLY dataset -> V(q, c2) = empty -> denominator = 0.0 (excluded under renormalize!)
        q = dict(
            paper_id="Q1", title="T", abstract="A", conference_id="v1", split="test",
            facets={"problem": ["p"], "task": ["t"], "method": ["m"], "dataset": [], "contribution": []},
        )
        c1 = dict(
            paper_id="C1", title="T", abstract="A", conference_id="v1", split="train",
            facets={"problem": ["p"], "task": ["t"], "method": ["m"], "dataset": ["d"], "contribution": ["c"]},
        )
        c2 = dict(
            paper_id="C2", title="T", abstract="A", conference_id="v2", split="train",
            facets={"problem": [], "task": [], "method": [], "dataset": ["d"], "contribution": []},
        )
        vec_map = {
            "p": np.array([1.0, 0.0, 0.0]),
            "t": np.array([0.8, 0.6, 0.0]),
            "m": np.array([0.0, 1.0, 0.0]),
            "d": np.array([0.0, 0.0, 1.0]),
            "c": np.array([1.0, 0.0, 0.0]),
        }

        def encode(texts):
            return [vec_map.get(t, np.array([1.0, 0.0, 0.0]) if t.strip() else None) for t in texts]

        store = FacetFeatureStore([c1, c2], [q], backend=CustomCallableBackend(encode))
        pairs = PairMatrices(store, [c1, c2], [q], ["v1", "v2"])
        w_a = FLAT_5_FACET_PRESETS["exp_b_weighted_a"]

        # 1. Dynamic Denominator Renormalization (Exp B standard)
        mat_renorm, valid_mask = pairs.scores_with_validity(
            {"method": "flat_5_facet", "weights": w_a, "missing_policy": "renormalize"}
        )
        self.assertTrue(bool(valid_mask[0, 0]))
        self.assertFalse(bool(valid_mask[0, 1]))  # c2 excluded because denominator == 0
        self.assertAlmostEqual(float(mat_renorm[0, 0]), 1.0, places=6)

        # 2. Zero-Imputation Policy (Exp C3): numerator = 0.8 * 1.0, denominator fixed at 1.0 => 0.8
        mat_zero, valid_zero = pairs.scores_with_validity(
            {"method": "flat_5_facet", "weights": w_a, "missing_policy": "zero_impute"}
        )
        self.assertIsNone(valid_zero)
        self.assertAlmostEqual(float(mat_zero[0, 0]), 0.8, places=6)
        self.assertAlmostEqual(float(mat_zero[0, 1]), 0.0, places=6)

    def test_dense_text_preservation_and_no_validated_silver(self):
        # Verify dense backends preserve natural punctuation, casing, and "; " concept delimiter
        self.assertEqual(format_dense_whole_text("A k-NN Study", "Uses L1-norm & BERT."), "A k-NN Study. Uses L1-norm & BERT.")
        self.assertEqual(format_dense_facet_text(["BiLSTM-CRF", "k-NN"]), "BiLSTM-CRF; k-NN")
        paper = dict(
            paper_id="P1", title="A k-NN Study", abstract="Uses L1-norm & BERT.",
            conference_id="v1", split="train",
            facets={"problem": ["Cold-Start"], "task": ["k-NN", "L1"], "method": [], "dataset": [], "contribution": []},
        )
        captured = []

        def spy_encode(texts):
            captured.extend(texts)
            return [np.array([1.0, 0.0]) if t.strip() else None for t in texts]

        store = FacetFeatureStore([paper], [], backend=CustomCallableBackend(spy_encode))
        self.assertEqual(store.text_store["P1"]["whole_text"], "A k-NN Study. Uses L1-norm & BERT.")
        self.assertEqual(store.text_store["P1"]["task"], "k-NN; L1")

        # Verify validated_silver.jsonl is never the default and is strictly rejected
        self.assertNotIn("validated_silver.jsonl", DEFAULT_FACETS.lower())
        with self.assertRaises(ValueError):
            assert_not_validated_silver("data/exp_b/data_preparation/output/validated_silver.jsonl")

    def test_diagnostic_tiers_disciplines_and_rank_correlations(self):
        # Verify VENUE_DISCIPLINE_MAP covers 100% (30/30) of conference_catalog.jsonl if present
        catalog_path = ROOT / "data/conference_recommendation_dataset/5_mapping_reviewed/splits/temporal_2015_2016_2019_clean/conference_catalog.jsonl"
        if catalog_path.exists():
            catalog_ids = [json.loads(l)["conference_id"] for l in catalog_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            self.assertEqual(len(catalog_ids), 30)
            for cid in catalog_ids:
                self.assertIn(cid, VENUE_DISCIPLINE_MAP)

        # Verify tier classification & discipline_hit@1 + cross_discipline_error_rate == 1.0
        self.assertEqual(classify_venue_tier(25), "head")
        self.assertEqual(classify_venue_tier(10), "mid")
        self.assertEqual(classify_venue_tier(3), "tail")

        preds = {
            "P1": [("CONF_EMNLP", 0.9), ("CONF_ACL", 0.8), ("CONF_CVPR", 0.1)],  # intra-disc NLP
            "P2": [("CONF_CVPR", 0.9), ("CONF_ACL", 0.8), ("CONF_EMNLP", 0.1)],  # cross-disc NLP->CV
        }
        truth = {"P1": "CONF_ACL", "P2": "CONF_ACL"}
        detailed = evaluate_predictions_detailed(
            preds, truth, ["CONF_ACL", "CONF_EMNLP", "CONF_CVPR"],
            train_venue_counts={"CONF_ACL": 122, "CONF_EMNLP": 106, "CONF_CVPR": 14},
        )
        m = detailed["metrics"]
        self.assertAlmostEqual(m["discipline_hit@1"] + m["cross_discipline_error_rate"], 1.0)
        self.assertAlmostEqual(m["discipline_hit@1"], 0.5)
        self.assertEqual(detailed["tier_metrics"]["head"]["test_count"], 2)

        # Verify Spearman & Kendall rank correlations across 5 Raw LLMs
        dummy_down = {
            "Gemma-9B": {"hit@3": 0.75},
            "Qwen-8B": {"hit@3": 0.70},
            "Llama-8B": {"hit@3": 0.65},
            "Qwen-14B": {"hit@3": 0.66},
            "Qwen-4B": {"hit@3": 0.60},
        }
        corr = rank_correlation_matrix(EXP_A_RAW_METRICS, dummy_down)
        self.assertAlmostEqual(corr["macro_f1"]["hit@3"]["spearman_rho"], 1.0, places=6)
        self.assertAlmostEqual(corr["macro_f1"]["hit@3"]["kendall_tau"], 1.0, places=6)
        self.assertAlmostEqual(corr["macro_f1"]["hit@3"]["spearman_p"], 2.0 / 120.0, places=6)


class ExpDDiagnosticTests(unittest.TestCase):
    """6 unit tests verifying the 3 venue aggregation mechanisms and Exp D1-D4 diagnostics."""

    def test_mechanism1_facet_first_compositional_matching_and_renormalization(self):
        # Venue v_comp has two disjoint single-facet papers:
        #   R1 has ONLY problem ("p_match"), R2 has ONLY method ("m_match").
        # Venue v_single has one paper R3 with both problem ("p_weak") and method ("m_weak").
        # Venue v_empty has R4 with ONLY contribution ("c_only"), while Query Q1 lacks contribution.
        # Query Q1 has problem ("p_match"), method ("m_match"), and dataset ("d_query"),
        # where NO reference paper in v_comp has dataset (|P_{v_comp, dataset}| == 0).
        q1 = dict(
            paper_id="Q1",
            title="T",
            abstract="A",
            conference_id="v_comp",
            split="test",
            facets={"problem": ["p_match"], "task": [], "method": ["m_match"], "dataset": ["d_query"], "contribution": []},
        )
        r1 = dict(
            paper_id="R1",
            title="T",
            abstract="A",
            conference_id="v_comp",
            split="train",
            facets={"problem": ["p_match"], "task": [], "method": [], "dataset": [], "contribution": []},
        )
        r2 = dict(
            paper_id="R2",
            title="T",
            abstract="A",
            conference_id="v_comp",
            split="train",
            facets={"problem": [], "task": [], "method": ["m_match"], "dataset": [], "contribution": []},
        )
        r3 = dict(
            paper_id="R3",
            title="T",
            abstract="A",
            conference_id="v_single",
            split="train",
            facets={"problem": ["p_weak"], "task": [], "method": ["m_weak"], "dataset": [], "contribution": []},
        )
        r4 = dict(
            paper_id="R4",
            title="T",
            abstract="A",
            conference_id="v_empty",
            split="train",
            facets={"problem": [], "task": [], "method": [], "dataset": [], "contribution": ["c_only"]},
        )

        vec_map = {
            "p_match": np.array([1.0, 0.0, 0.0]),
            "m_match": np.array([0.0, 1.0, 0.0]),
            "d_query": np.array([0.0, 0.0, 1.0]),
            "p_weak": np.array([0.6, 0.8, 0.0]),
            "m_weak": np.array([0.8, 0.6, 0.0]),
            "c_only": np.array([0.0, 0.0, 1.0]),
        }

        def encode(texts):
            return [vec_map.get(t, np.array([1.0, 0.0, 0.0]) if t.strip() else None) for t in texts]

        candidates = ["v_comp", "v_empty", "v_single"]
        store = FacetFeatureStore([r1, r2, r3, r4], [q1], backend=CustomCallableBackend(encode))
        pairs = PairMatrices(store, [r1, r2, r3, r4], [q1], candidates)

        # In Paper-First (Per-Venue Top-1), R1 only matches problem (sim=1.0) and R2 only matches method (sim=1.0),
        # never combining both facets in a single venue prototype; in Facet-First, v_comp pools R1 for problem
        # and R2 for method with dynamic denominator w_problem + w_method = 0.40 + 0.20 = 0.60 (excluding dataset).
        for mode in ("top_m", "centroid"):
            scores_mat, valid_mask, act_stats = pairs.facet_first_venue_matrix(
                mode=mode, top_m=2, weights=LOCKED_EXP_B_WEIGHTS
            )
            self.assertEqual(scores_mat.shape, (1, 3))
            # v_comp (col 0) and v_single (col 2) are valid; v_empty (col 1) has V_venue = empty -> False, -inf
            self.assertTrue(bool(valid_mask[0, 0]))
            self.assertFalse(bool(valid_mask[0, 1]))
            self.assertTrue(bool(valid_mask[0, 2]))
            self.assertTrue(math.isinf(scores_mat[0, 1]) and scores_mat[0, 1] < 0)

            # v_comp compositional score: (0.40 * 1.0 + 0.20 * 1.0) / (0.40 + 0.20) = 1.0
            self.assertAlmostEqual(float(scores_mat[0, 0]), 1.0, places=5)
            # v_single score: (0.40 * 0.6 + 0.20 * 0.6) / (0.40 + 0.20) = 0.6
            self.assertAlmostEqual(float(scores_mat[0, 2]), 0.6, places=5)
            # Activation rates: problem active in 2/3 venues (v_comp, v_single), dataset active in 0/3 venues
            self.assertAlmostEqual(act_stats["problem_activation_rate"], 2.0 / 3.0, places=6)
            self.assertAlmostEqual(act_stats["dataset_activation_rate"], 0.0, places=6)
            self.assertAlmostEqual(act_stats["problem_query_activation_rate"], 1.0, places=6)
            self.assertAlmostEqual(act_stats["dataset_query_activation_rate"], 1.0, places=6)

    def test_mechanism1_per_facet_venue_centroid_zero_cv_leakage(self):
        train, test, venues = fixture()

        def encode(texts):
            out = []
            for t in texts:
                if not t or not t.strip():
                    out.append(None)
                else:
                    out.append(
                        np.array(
                            [
                                float(t.count("alpha") + 0.1 * len(t)),
                                float(t.count("beta") + 0.2 * ("problem" in t)),
                                float(1.0 + t.count("poison")),
                            ],
                            dtype=np.float64,
                        )
                    )
            return out

        exp = Experiment(
            train,
            test,
            venues,
            backend=CustomCallableBackend(encode),
            n_splits=3,
            seed=42,
        )
        cv_pairs = exp.build_cv()

        for fold_idx, pair in enumerate(cv_pairs):
            val_ids = {p["paper_id"] for p in pair.queries}
            ref_ids = {p["paper_id"] for p in pair.train}
            self.assertTrue(val_ids.isdisjoint(ref_ids))

            base_scores, base_vm, _ = pair.facet_first_venue_matrix(
                mode="centroid", weights=LOCKED_EXP_B_WEIGHTS
            )

            # Corrupt every other validation paper in the training corpus and rebuild fold pair for query 0
            poisoned_train = copy.deepcopy(train)
            target_q_pid = pair.queries[0]["paper_id"]
            for p in poisoned_train:
                if p["paper_id"] in val_ids and p["paper_id"] != target_q_pid:
                    p["facets"] = {f: ["poison " * 50] for f in FACET_KEYS}

            val_indices = exp.folds[fold_idx]
            ref_indices = [i for i in range(len(train)) if i not in set(val_indices)]
            store_poison = FacetFeatureStore(
                [poisoned_train[i] for i in ref_indices],
                [poisoned_train[i] for i in val_indices],
                backend=CustomCallableBackend(encode),
            )
            pair_poison = PairMatrices(
                store_poison,
                [poisoned_train[i] for i in ref_indices],
                [poisoned_train[i] for i in val_indices],
                venues,
            )
            poison_scores, poison_vm, _ = pair_poison.facet_first_venue_matrix(
                mode="centroid", weights=LOCKED_EXP_B_WEIGHTS
            )
            # Query 0's centroid scores against reference pool P_{v, f} must be 100% invariant to other validation papers
            np.testing.assert_allclose(base_scores[0], poison_scores[0], atol=1e-12)
            np.testing.assert_array_equal(base_vm[0], poison_vm[0])

    def test_mechanism2_adaptive_fusion_zero_coverage_fallback_and_zero_variance(self):
        # 3 queries x 4 venues:
        # Query 0: g(q) == 0 (all 5 facets missing, facet_scores = -inf, facet_valid_mask = False)
        # Query 1: g(q) == 1.0, but facet_scores has zero variance across valid venues ([0.5, 0.5, 0.5, 0.5])
        # Query 2: g(q) == 0.6, partial validity (venue 3 invalid -> filled with min(valid_z) - 1.0)
        candidates = ["v1", "v2", "v3", "v4"]
        full_scores = np.array(
            [
                [0.20, 0.80, 0.50, 0.10],
                [0.90, 0.40, 0.60, 0.30],
                [0.30, 0.40, 0.50, 0.60],
            ],
            dtype=np.float64,
        )
        facet_scores = np.array(
            [
                [-np.inf, -np.inf, -np.inf, -np.inf],
                [0.50, 0.50, 0.50, 0.50],
                [0.90, 0.60, 0.30, -np.inf],
            ],
            dtype=np.float64,
        )
        facet_valid_mask = np.array(
            [
                [False, False, False, False],
                [True, True, True, True],
                [True, True, True, False],
            ],
            dtype=bool,
        )
        query_masks = {
            "problem": [False, True, True],
            "task": [False, True, True],
            "method": [False, True, False],
            "dataset": [False, True, False],
            "contribution": [False, True, False],
        }

        for beta in (0.1, 0.3, 0.7):
            fused, g_q = compute_adaptive_fusion_scores(
                full_scores,
                facet_scores,
                query_masks,
                beta=beta,
                facet_valid_mask=facet_valid_mask,
                weights=LOCKED_EXP_B_WEIGHTS,
            )
            self.assertTrue(np.all(np.isfinite(fused)))
            self.assertAlmostEqual(float(g_q[0]), 0.0, places=12)
            self.assertAlmostEqual(float(g_q[1]), 1.0, places=12)
            self.assertAlmostEqual(float(g_q[2]), 0.6, places=12)

            # Query 0 (g(q) == 0) and Query 1 (zero variance facet scores) must preserve exact Full-text venue order
            for q_idx in (0, 1):
                ft_order = [v for v, _ in rank_venues_from_score_row(full_scores[q_idx], candidates)]
                af_order = [v for v, _ in rank_venues_from_score_row(fused[q_idx], candidates)]
                self.assertEqual(af_order, ft_order)

    def test_mechanism3_coarse_to_fine_preserves_tail_ranks_and_tie_breaks(self):
        # 30 candidate venues sorted by Stage-1 score descending
        venues_30 = [f"CONF_{i:02d}" for i in range(1, 31)]
        stage1_ranked = [(v, round(1.0 - 0.02 * idx, 4)) for idx, v in enumerate(venues_30)]

        # Stage-2 scores reverse the top-10, put a tie between CONF_03 and CONF_02, and mark CONF_01 invalid
        stage2_scores = {v: float(idx) for idx, v in enumerate(venues_30)}
        stage2_scores["CONF_02"] = 50.0
        stage2_scores["CONF_03"] = 50.0  # tie with CONF_02 -> CONF_02 must win by conference_id asc
        stage2_valid = {v: True for v in venues_30}
        stage2_valid["CONF_01"] = False  # invalid -> treated as -np.inf, placed at rank top_c

        for top_c in (5, 10):
            reranked = rerank_coarse_to_fine(
                stage1_ranked,
                stage2_scores,
                top_c=top_c,
                stage2_valid_mask=stage2_valid,
            )
            self.assertEqual(len(reranked), 30)
            # Tail ranks > top_c (indices top_c..29) must be 100% untouched in venue ID and score
            self.assertEqual(reranked[top_c:], stage1_ranked[top_c:])
            # Within top_c, CONF_02 and CONF_03 tied at 50.0 must be 1st and 2nd in alphabetical order
            self.assertEqual(reranked[0][0], "CONF_02")
            self.assertEqual(reranked[1][0], "CONF_03")
            # Invalid CONF_01 must drop to the last slot of the top_c window (index top_c - 1) with score -inf
            self.assertEqual(reranked[top_c - 1][0], "CONF_01")
            self.assertTrue(math.isinf(reranked[top_c - 1][1]) and reranked[top_c - 1][1] < 0)

    def test_exp_d2_coverage_stratification_mutual_exclusivity_and_completeness_168(self):
        # Build a 168-query Test split across 4 coverage patterns:
        # 1) problem=1, all facets present -> g(q)=1.00 >= 0.80 -> High-Cov
        # 2) problem=1, task=1, method=1 -> g(q)=0.80 >= 0.80 -> High-Cov
        # 3) problem=1, task=1 only -> g(q)=0.60 < 0.80 -> Low-Cov
        # 4) problem=0, task=1, method=1, dataset=1, contrib=1 -> g(q)=0.60, problem=0 -> Low-Cov
        venues = ["CONF_ACL", "CONF_CVPR", "CONF_KDD"]
        train = []
        for idx in range(15):
            v = venues[idx % 3]
            train.append(
                dict(
                    paper_id=f"tr_{idx:03d}",
                    title=f"{v} title {idx}",
                    abstract=f"abstract text for {v} paper {idx}",
                    conference_id=v,
                    split="train",
                    facets={f: [f"{v}_{f}"] for f in FACET_KEYS},
                )
            )
        test = []
        for idx in range(168):
            v = venues[idx % 3]
            mod = idx % 4
            if mod == 0:
                facets = {f: [f"{v}_{f}"] for f in FACET_KEYS}
            elif mod == 1:
                facets = {"problem": [f"{v}_problem"], "task": [f"{v}_task"], "method": [f"{v}_method"], "dataset": [], "contribution": []}
            elif mod == 2:
                facets = {"problem": [f"{v}_problem"], "task": [f"{v}_task"], "method": [], "dataset": [], "contribution": []}
            else:
                facets = {"problem": [], "task": [f"{v}_task"], "method": [f"{v}_method"], "dataset": [f"{v}_dataset"], "contribution": [f"{v}_contribution"]}
            test.append(
                dict(
                    paper_id=f"te_{idx:03d}",
                    title=f"{v} test {idx}",
                    abstract="word " * (20 + (idx % 30)) + f" {v}",
                    conference_id=v,
                    split="test",
                    facets=facets,
                )
            )

        with tempfile.TemporaryDirectory() as tmp:
            exp = Experiment(train, test, venues, backend="tfidf", n_splits=3, output_dir=Path(tmp))
            d_payload = exp.run_exp_d({"Qwen-8B": test}, overwrite=True, n_resamples=100, ks=(3, 5))
            d2_qwen = d_payload["exp_d2"]["by_extractor"]["Qwen-8B"]
            n_high = d2_qwen["n_high_cov"]
            n_low = d2_qwen["n_low_cov"]
            self.assertEqual(n_high + n_low, 168)
            self.assertEqual(n_high, 84)  # mod 0 and mod 1 (2/4 of 168)
            self.assertEqual(n_low, 84)   # mod 2 and mod 3 (2/4 of 168)
            high_ids = set(d2_qwen["strata"]["high_cov"]["paper_ids"])
            low_ids = set(d2_qwen["strata"]["low_cov"]["paper_ids"])
            self.assertTrue(high_ids.isdisjoint(low_ids))
            self.assertEqual(len(high_ids | low_ids), 168)

    def test_exp_d4_win_tie_loss_sum_168_and_mann_whitney_u_validity(self):
        venues = ["CONF_ACL", "CONF_EMNLP", "CONF_CVPR", "CONF_KDD"]
        # Train counts: CONF_ACL=20 (head), CONF_EMNLP=8 (mid), CONF_CVPR=3 (tail), CONF_KDD=3 (tail)
        train_specs = [("CONF_ACL", 20), ("CONF_EMNLP", 8), ("CONF_CVPR", 3), ("CONF_KDD", 3)]
        train = []
        for v, count in train_specs:
            for i in range(count):
                train.append(
                    dict(
                        paper_id=f"tr_{v}_{i:02d}",
                        title=f"{v} study {i}",
                        abstract=f"shared research in {v} topic {i}",
                        conference_id=v,
                        split="train",
                        facets={f: [f"{v}_{f}"] for f in FACET_KEYS},
                    )
                )

        test = []
        for idx in range(168):
            v = venues[idx % 4]
            # Vary abstract word count, facet coverage, and lexical content so Win, Tie, and Loss all occur
            if idx % 3 == 0:
                # Facets match true venue v while abstract mentions a distractor venue
                distractor = venues[(idx + 1) % 4]
                abstract_text = (f"{distractor} " * (10 + idx % 15)).strip()
                facets = {f: [f"{v}_{f}"] for f in FACET_KEYS}
            elif idx % 3 == 1:
                # Abstract slightly favors true venue v over distractor, while all 5 facets strongly match distractor
                distractor = venues[(idx + 1) % 4]
                abstract_text = f"{v} {v} " + (f"{distractor} " * 2).strip() + (" filler" * (10 + idx % 15))
                facets = {f: [f"{distractor}_{f}"] for f in FACET_KEYS}
            else:
                # Both match true venue v -> Tie
                abstract_text = (f"{v} " * 12).strip()
                facets = {f: [f"{v}_{f}"] for f in FACET_KEYS}
            test.append(
                dict(
                    paper_id=f"te_{idx:03d}",
                    title=f"Paper {idx}",
                    abstract=abstract_text,
                    conference_id=v,
                    split="test",
                    facets=facets,
                )
            )

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            exp = Experiment(train, test, venues, backend="tfidf", n_splits=3, output_dir=out_dir)
            d_payload = exp.run_exp_d({"Qwen-8B": test}, overwrite=True, n_resamples=100, ks=(3, 5))
            for comp_key in ("facet_first_vs_fulltext", "adaptive_fusion_vs_fulltext"):
                comp = d_payload["exp_d4"]["comparisons"][comp_key]
                self.assertEqual(comp["n_win"] + comp["n_tie"] + comp["n_loss"], 168)
                self.assertGreater(comp["n_win"], 0)
                self.assertGreater(comp["n_loss"], 0)
                for feat_key in (
                    "abstract_word_count",
                    "active_weight_mass",
                    "active_facet_count",
                    "lexical_novelty_proxy",
                ):
                    mw = comp["mann_whitney_win_vs_loss"][feat_key]
                    self.assertTrue(math.isfinite(mw["u_stat"]) and mw["u_stat"] >= 0.0)
                    self.assertTrue(0.0 <= mw["p_value"] <= 1.0)
                tt = comp["venue_tier_test_win_vs_loss"]
                self.assertTrue(0.0 <= tt["chi2_p_value"] <= 1.0)
                self.assertTrue(0.0 <= tt["fisher_head_vs_nonhead_p_value"] <= 1.0)

            rep_path = write_exp_d_report(out_dir, overwrite=True)
            self.assertIsNotNone(rep_path)
            self.assertTrue(rep_path.exists())
            self.assertTrue((out_dir / "report_tables/exp_d1_paradigm_comparison.csv").exists())
            self.assertTrue((out_dir / "report_tables/exp_d2_coverage_stratification.csv").exists())
            self.assertTrue((out_dir / "report_tables/exp_d3_complementary_all_test.csv").exists())
            self.assertTrue((out_dir / "report_tables/exp_d4_win_loss_stratification.csv").exists())


if __name__ == "__main__":
    unittest.main()
