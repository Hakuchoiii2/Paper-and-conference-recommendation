"""Conference protocol regressions; synthetic data only, no model downloads."""
import copy
import csv
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.conference_recommendation.experiment_protocol import (
    Experiment, PairMatrices, get_stratified_folds, WEIGHT_PRESETS,
    FLAT_5_FACET_PRESETS, aggregate_folds, numeric_list, main,
)
from scripts.conference_recommendation.data_loader import load_dataset, FACET_KEYS
from scripts.conference_recommendation.feature_loader import FacetFeatureStore, CustomCallableBackend
from scripts.conference_recommendation.reranker import GatedFacetKNNReranker
from scripts.conference_recommendation.baselines import FlatFacetKNNReranker, WholeTextKNNReranker
from scripts.conference_recommendation.report_experiments import write_report


def fixture():
    def paper(pid, topic, split):
        return dict(paper_id=pid, title=topic + " science", abstract="shared " + topic,
                    conference_id="v_" + topic, split=split,
                    facets={f: [topic + " " + f] for f in FACET_KEYS})
    train = [paper(f"tr_{topic}_{i}", topic, "train") for topic in ("alpha", "beta") for i in range(6)]
    test = [paper(f"te_{topic}_{i}", topic, "test") for topic in ("alpha", "beta") for i in range(2)]
    # Missing and zero facets must be handled identically in every scoring path.
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
        # Whole-text IDF must not depend on facet text either.
        changed_train = copy.deepcopy(train)
        changed_train[0]["facets"]["task"] = ["alpha " * 20]
        third = FacetFeatureStore(changed_train, test)
        self.assertEqual(first.get_vectors(train[0]["paper_id"])["whole_text"],
                         third.get_vectors(train[0]["paper_id"])["whole_text"])

    def test_matrix_runtime_parity_sparse_and_numpy_dense(self):
        train, test, venues = fixture()
        def encode(texts):
            return [np.array([text.count("alpha"), text.count("beta"), 1. if text.strip() else 0.]) for text in texts]
        for backend in ("tfidf", CustomCallableBackend(encode)):
            store = FacetFeatureStore(train, test, backend=backend)
            pairs = PairMatrices(store, train, test, venues)
            configs = [
                dict(method="whole_text", k=3),
                dict(method="flat_5_facet", k=3, weights=FLAT_5_FACET_PRESETS["flat_problem_heavy"]),
                dict(method="gated", k=3, tau=.25, kappa=5., weights=WEIGHT_PRESETS["method_heavy"]),
            ]
            for config in configs:
                method = config["method"]
                kwargs = {k: v for k, v in config.items() if k != "method"}
                cls = {"whole_text": WholeTextKNNReranker, "flat_5_facet": FlatFacetKNNReranker, "gated": GatedFacetKNNReranker}[method]
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
        model = GatedFacetKNNReranker(store, train, tau=.25, kappa=5.)
        self.assertEqual(model.compute_context_gate(None, {"x": 1}), .5)
        self.assertEqual(model.compute_context_gate(np.zeros(3), np.ones(3)), .5)
        from scripts.conference_recommendation.ranking import rank_neighbors
        a = rank_neighbors(["z", "a"], ["v_beta", "v_alpha"], [1., 1.], venues, 1)
        b = rank_neighbors(["a", "z"], ["v_alpha", "v_beta"], [1., 1.], venues[::-1], 1)
        self.assertEqual(a, b)
        self.assertEqual(a[0][0], "v_alpha")

    def test_fold_balance_stratification_and_input_order(self):
        train, _, _ = fixture()
        first = get_stratified_folds(train, 3)
        reverse = list(reversed(train))
        second = get_stratified_folds(reverse, 3)
        self.assertEqual([[train[i]["paper_id"] for i in f] for f in first],
                         [[reverse[i]["paper_id"] for i in f] for f in second])
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
        from scripts.conference_recommendation.experiment_protocol import METRICS
        summary = aggregate_folds([{m: v for m in METRICS} for v in (0., .5, 1.)])
        self.assertEqual(summary["hit@3"], .5)
        self.assertEqual(summary["hit@3_std"], .5)
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
        return self.exp.tune([1, 3], [.25], [5.])

    def test_end_to_end_artifacts_csv_counts_report_and_frozen_benchmark(self):
        tuning = self.tune()
        self.assertEqual(len(tuning["methods"]["gated"]["cv_all"]), 20)
        self.assertEqual(len(tuning["methods"]["flat_5_facet"]["cv_all"]), 20)
        with (self.output / "grid_search_all_tfidf.csv").open(encoding="utf-8-sig", newline="") as h:
            grid = list(csv.DictReader(h))
        with (self.output / "grid_search_folds_tfidf.csv").open(encoding="utf-8-sig", newline="") as h:
            folds = list(csv.DictReader(h))
        self.assertEqual(len(grid), 42)
        self.assertEqual(len(folds), 126)
        self.assertEqual(sum(int(r["selected"]) for r in grid), 3)
        self.assertTrue(all(r["tuning_id"] == tuning["tuning_id"] for r in grid))
        self.assertEqual(float(grid[0]["cv_hit@3"]), tuning["methods"]["whole_text"]["best"]["cv"]["hit@3"])
        test_result = self.exp.evaluate_test()
        self.assertEqual(len(test_result["rows"]), 6)
        self.assertAlmostEqual(test_result["random_theoretical"]["mrr"], .75)
        analysis = self.exp.analyze()
        self.assertEqual(len(analysis["facet_ablation_table2"]), 10)
        best = tuning["methods"]["gated"]["best"]["config"]
        for record, facet in zip(analysis["facet_ablation_table2"][6:], FACET_KEYS[1:]):
            w = record["config"]["weights"]
            self.assertEqual(w[facet], 0)
            self.assertAlmostEqual(sum(w.values()), 1)
            for a in FACET_KEYS[1:]:
                for b in FACET_KEYS[1:]:
                    if a != facet and b != facet and best["weights"][b] > 0:
                        self.assertAlmostEqual(w[a] / w[b], best["weights"][a] / best["weights"][b])
        self.assertEqual(analysis["sensitivity_split"], "train_cv_only")
        self.assertFalse(any("test" in row for rows in analysis["sensitivity"].values() for row in rows))
        altered = copy.deepcopy(self.test)
        altered[0]["facets"]["method"] = ["beta"]
        benchmark = self.exp.benchmark({"Qwen-8B": self.test, "Other": altered})
        qwen = benchmark["rows"][0]["metrics"]
        selected = next(r["metrics"] for r in test_result["rows"] if r["method"] == "gated" and r["variant"] == "best")
        self.assertEqual(qwen, selected)
        self.assertEqual(benchmark["rows"][0]["frozen_train_digest"], benchmark["rows"][1]["frozen_train_digest"])
        report = write_report(self.output, self.output / "report.md")
        text = report.read_text(encoding="utf-8")
        for title in ("Bảng 1", "Bảng 2", "Bảng 3", "Bảng 4"):
            self.assertIn(title, text)
        self.assertNotIn("45.36%", text)
        self.assertTrue((self.output / "report_tables/table1.csv").exists())
        self.assertIn("Hình 3 — Biểu đồ đường bổ sung", text)
        self.assertIn("| Tham số thay đổi |", text)  # Keep the numeric sensitivity table.
        self.assertIn("Phụ lục A", text)
        self.assertIn("Vì sao Bảng 4 dùng Gated thay vì Whole-Text?", text)
        self.assertIn("đối chứng bất biến theo extractor", text)
        self.assertIn("Phụ lục B — Code và dữ liệu tạo Hình 3", text)
        self.assertTrue((self.output / "figures/sensitivity_cv_hit3.png").exists())
        self.assertTrue((self.output / "figures/sensitivity_cv_hit3.svg").exists())
        with (self.output / "figures/sensitivity_cv_hit3.csv").open(encoding="utf-8-sig", newline="") as handle:
            chart_rows = list(csv.DictReader(handle))
        self.assertEqual(len(chart_rows), sum(len(rows) for rows in analysis["sensitivity"].values()))
        self.assertEqual(sum(int(row["frozen_choice"]) for row in chart_rows), 3)
        self.assertTrue(all(row["tuning_id"] == tuning["tuning_id"] for row in chart_rows))
        self.assertNotIn("1.440", text)  # Custom grids must not inherit fixed sample-report counts.
        with self.assertRaises(FileExistsError):
            self.exp.evaluate_test()

    def test_tuning_does_not_access_final_or_test_scoring(self):
        from unittest.mock import patch
        with patch.object(self.exp, "build_final", side_effect=AssertionError("Test accessed while tuning")):
            tuning = self.tune()
        for method in tuning["methods"].values():
            self.assertEqual(len(method["best"]["cv"]["fold_metrics"]), 3)
        # Every fold reference excludes its validation IDs.
        for pairs in self.exp.cv_pairs:
            self.assertFalse({p["paper_id"] for p in pairs.train} & {p["paper_id"] for p in pairs.queries})

    def test_dense_cv_reuses_one_encoder_and_excludes_self_neighbors(self):
        from unittest.mock import patch
        def encode(texts):
            return [np.array([float("alpha" in t), float("beta" in t), float(bool(t))]) for t in texts]
        encoder = CustomCallableBackend(encode)
        with patch("scripts.conference_recommendation.feature_loader.SentenceTransformerBackend", return_value=encoder) as constructor:
            exp = Experiment(self.train, self.test, self.venues, backend="specter", n_splits=3, output_dir=self.output)
            for pairs in exp.build_cv():
                self.assertFalse({p['paper_id'] for p in pairs.train} & {p['paper_id'] for p in pairs.queries})
                self.assertEqual(pairs.sim['problem'].shape, (4, 8))
            final = exp.build_final()
            self.assertEqual(final.sim['whole_text'].shape, (4, 12))
            self.assertIs(exp.encoder, encoder)
            self.assertEqual(constructor.call_count, 1)

    def test_provenance_mismatch_tampering_and_stale_report_rejected(self):
        self.tune()
        self.exp.evaluate_test()
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
        for name, rows in [("train.jsonl", self.train), ("test.jsonl", self.test),
                           ("conference_catalog.jsonl", [{"conference_id": v} for v in self.venues])]:
            (split / name).write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        (split / "label_map.json").write_text(json.dumps(dict.fromkeys(self.venues, 0)), encoding="utf-8")
        base = self.output / "base.jsonl"
        base.write_text("\n".join(json.dumps({"paper_id": p["paper_id"], **p["facets"]}) for p in self.train + self.test), encoding="utf-8")
        other = self.output / "other.jsonl"
        other.write_text("\n".join(json.dumps({"paper_id": p["paper_id"], **{f: ["different"] for f in FACET_KEYS}}) for p in self.test), encoding="utf-8")
        train, test, _, _ = load_dataset(split, base, ROOT, test_facets_path=other, require_coverage=True)
        self.assertEqual(train[0]["facets"], self.train[0]["facets"])
        self.assertEqual(test[0]["facets"]["task"], ["different"])
        other.write_text("", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Missing facets"):
            load_dataset(split, base, ROOT, test_facets_path=other, require_coverage=True)
        # Exercise the actual CLI across every stage, using local fixtures only.
        manifest = self.output / "manifest.json"
        manifest.write_text(json.dumps({"Qwen-8B": str(base)}), encoding="utf-8")
        main(argv=["--stage", "all", "--embedding-backend", "tfidf", "--split-dir", str(split),
                   "--facets-path", str(base), "--extractor-manifest", str(manifest), "--n-splits", "3",
                   "--k-list", "1,3", "--tau-list", ".25", "--kappa-list", "5",
                   "--output-dir", str(self.output / "cli"), "--report-path", str(self.output / "cli.md")])
        self.assertTrue((self.output / "cli.md").exists())

    def test_missing_outputs_generate_honest_template(self):
        report = write_report(self.output, self.output / "template.md")
        text = report.read_text(encoding="utf-8")
        self.assertIn("Chưa chạy", text)
        self.assertNotIn("± 0.00%", text)


if __name__ == "__main__":
    unittest.main()
