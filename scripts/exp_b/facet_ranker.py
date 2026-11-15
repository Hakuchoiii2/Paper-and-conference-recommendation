"""Reusable all-MiniLM-L6-v2 downstream ranker for Exp B."""
import json
import math
from pathlib import Path
import sys

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from baseline_common import ranked
from experiment_io import FACETS

MODEL_NAME = 'all-MiniLM-L6-v2'
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FROZEN_CONFIG = ROOT / 'configs' / 'exp_b_frozen.json'


def load_frozen_weights(path=DEFAULT_FROZEN_CONFIG):
    config = json.loads(Path(path).read_text(encoding='utf-8'))
    weights = config['weights']
    validate_weights(weights)
    return weights


def validate_weights(weights):
    if set(weights) != set(FACETS):
        raise ValueError(f'Weights must contain exactly these facets: {", ".join(FACETS)}')
    if any(type(weights[facet]) not in (int, float) or not math.isfinite(weights[facet])
           or weights[facet] < 0 for facet in FACETS):
        raise ValueError('Facet weights must be finite non-negative numbers')
    if not math.isclose(sum(weights.values()), 1.0, rel_tol=0.0, abs_tol=1e-8):
        raise ValueError('Facet weights must sum to 1')


class FacetRanker:
    """Encode paper text and facets once, then score candidate sets consistently."""

    def __init__(self, encoder=None, model_name=MODEL_NAME):
        if encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:
                raise RuntimeError(
                    'Install sentence-transformers to use the all-MiniLM-L6-v2 ranker'
                ) from error
            encoder = SentenceTransformer(model_name)
        self.encoder = encoder
        self.model_name = model_name
        self.whole_vectors = {}
        self.facet_vectors = {facet: {} for facet in FACETS}
        self.facet_present = {facet: {} for facet in FACETS}

    def encode(self, papers, facets):
        keys, texts = [], []
        for paper_id in sorted(papers):
            paper = papers[paper_id]
            text = f"{paper.get('title', '')}. {paper.get('abstract', '')}".strip()
            keys.append((paper_id, 'whole'))
            texts.append(text)
            for facet in FACETS:
                concepts = facets.get(paper_id, {}).get(facet, ())
                facet_text = ' '.join(sorted(concepts))
                self.facet_present[facet][paper_id] = bool(concepts)
                if facet_text:
                    keys.append((paper_id, facet))
                    texts.append(facet_text)

        if not texts:
            raise ValueError('No paper or facet text is available for encoding')
        vectors = np.asarray(self.encoder.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        ), dtype=np.float64)
        if vectors.ndim != 2 or vectors.shape[0] != len(keys) or vectors.shape[1] == 0:
            raise ValueError('Encoder returned an unexpected embedding shape')
        if not np.isfinite(vectors).all():
            raise ValueError('Encoder returned non-finite embeddings')

        dimension = vectors.shape[1]
        zero = np.zeros(dimension, dtype=np.float64)
        for (paper_id, facet), vector in zip(keys, vectors):
            if facet == 'whole':
                self.whole_vectors[paper_id] = vector
            else:
                self.facet_vectors[facet][paper_id] = vector
        for facet in FACETS:
            for paper_id in papers:
                self.facet_vectors[facet].setdefault(paper_id, zero)

    def score_components(self, query_id, candidate_ids):
        whole = np.asarray([
            float(np.dot(self.whole_vectors[query_id], self.whole_vectors[candidate_id]))
            for candidate_id in candidate_ids
        ], dtype=np.float64)
        similarities = np.zeros((len(candidate_ids), len(FACETS)), dtype=np.float64)
        active = np.zeros_like(similarities, dtype=bool)
        for column, facet in enumerate(FACETS):
            query_has_facet = self.facet_present[facet].get(query_id, False)
            for row, candidate_id in enumerate(candidate_ids):
                if query_has_facet and self.facet_present[facet].get(candidate_id, False):
                    similarities[row, column] = np.dot(
                        self.facet_vectors[facet][query_id],
                        self.facet_vectors[facet][candidate_id],
                    )
                    active[row, column] = True
        return whole, similarities, active

    @staticmethod
    def weighted_scores(whole, similarities, active, weights):
        validate_weights(weights)
        whole = np.asarray(whole, dtype=np.float64)
        similarities = np.asarray(similarities, dtype=np.float64)
        active = np.asarray(active, dtype=bool)
        weight_vector = np.asarray([weights[facet] for facet in FACETS], dtype=np.float64)
        active_weights = active * weight_vector
        denominator = active_weights.sum(axis=1)
        numerator = (similarities * active_weights).sum(axis=1)
        return np.divide(numerator, denominator, out=whole.copy(), where=denominator > 0)

    def score_case(self, query_id, candidate_ids, weights):
        whole, similarities, active = self.score_components(query_id, candidate_ids)
        equal_weights = {facet: 1.0 / len(FACETS) for facet in FACETS}
        equal = self.weighted_scores(whole, similarities, active, equal_weights)
        weighted = self.weighted_scores(whole, similarities, active, weights)
        return {
            'text_embedding': dict(zip(candidate_ids, whole.tolist())),
            'equal_facet_embedding': dict(zip(candidate_ids, equal.tolist())),
            'weighted_facet_embedding': dict(zip(candidate_ids, weighted.tolist())),
        }


def evaluate_downstream_ranker(facet_data):
    """Return standard Exp B predictions for {'papers', 'facets', 'cases', 'weights'}."""
    required = {'papers', 'facets', 'cases'}
    missing = required - set(facet_data)
    if missing:
        raise ValueError(f'facet_data is missing: {", ".join(sorted(missing))}')
    weights = facet_data.get('weights')
    if weights is None:
        weights = load_frozen_weights()
    validate_weights(weights)

    ranker = FacetRanker(
        encoder=facet_data.get('encoder'),
        model_name=facet_data.get('model_name', MODEL_NAME),
    )
    ranker.encode(facet_data['papers'], facet_data['facets'])
    predictions = []
    for case in facet_data['cases']:
        case_scores = ranker.score_case(
            case['query_paper_id'], case['candidate_ids'], weights
        )
        predictions.extend(
            ranked(case, model, scores) for model, scores in case_scores.items()
        )
    return predictions