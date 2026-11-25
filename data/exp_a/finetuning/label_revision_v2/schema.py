"""Versioned multi-sentence annotation boundary; the v1 training schema is unchanged."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location('revision_v2_base', ROOT / 'data/exp_a/build_exp_a.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
FACETS = base.FACET_NAMES
ITEM = dict(type='object', additionalProperties=False, required=['concept', 'evidence_ids'], properties={
    'concept': dict(type='string', minLength=1, pattern=r'\S'),
    'evidence_ids': dict(type='array', minItems=1, uniqueItems=True,
                         items=dict(type='string', pattern=r'^(T0|A(?:0|[1-9][0-9]*))$'))})
SCHEMA = dict(type='object', additionalProperties=False, required=['paper_id', *FACETS], properties={
    'paper_id': dict(type='string', minLength=1),
    **{facet: dict(type='array', items=ITEM) for facet in FACETS}})


def ground_response(value, paper):
    """Check shape and source words, then retain every exact supporting sentence.

    Word presence/order is a grounding check, not proof of entailment or correct
    coreference. Cross-sentence meaning, qualifiers and facet roles need review.
    """
    for key in ('paper_id', 'title', 'abstract'):
        base.require(isinstance(paper.get(key), str) and paper[key].strip(), 'Invalid source ' + key)
    base.require(isinstance(value, dict) and value.get('paper_id') == paper['paper_id'], 'Wrong paper_id')
    base.require(set(value) == {'paper_id', *FACETS}, 'Wrong facet keys')
    options = base.evidence_options(paper)
    positions = {eid: i for i, eid in enumerate(options)}
    grounded = dict(paper_id=paper['paper_id'])
    for facet in FACETS:
        base.require(isinstance(value[facet], list), facet + ': expected list')
        grounded[facet], seen = [], set()
        for item in value[facet]:
            base.require(isinstance(item, dict) and set(item) == {'concept', 'evidence_ids'}, 'Wrong v2 item keys')
            concept, ids = item['concept'], item['evidence_ids']
            base.require(isinstance(concept, str) and bool(concept.strip()) and concept == concept.strip(), 'Empty/untrimmed concept')
            key = base.normalize(concept).casefold()
            base.require(key and key not in seen, 'Duplicate/empty concept')
            seen.add(key)
            base.require(isinstance(ids, list) and bool(ids) and all(isinstance(eid, str) for eid in ids), 'Expected nonempty evidence_ids')
            base.require(len(ids) == len(set(ids)) and all(eid in options for eid in ids), 'Unknown/duplicate evidence ID')
            base.require(ids == sorted(ids, key=positions.__getitem__), 'Evidence IDs must follow source order')
            evidence = [dict(evidence_id=eid, **options[eid]) for eid in ids]
            words = [base.word_forms(w) for w in base.normalize(' '.join(e['evidence'] for e in evidence)).split()]
            cursor = 0
            for token in base.normalize(concept).split():
                token_forms = base.word_forms(token)
                match = next((i for i in range(cursor, len(words)) if words[i] & token_forms), None)
                base.require(match is not None, 'Concept must use selected source words in source order')
                cursor = match + 1
            grounded[facet].append(dict(concept=concept, evidence=evidence))
    return grounded
