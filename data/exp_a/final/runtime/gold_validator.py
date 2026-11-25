"""Source-only gate compatible with reviewed paraphrases; lexical checks are warnings.

This module never reads reference labels. Passing the gate establishes structure,
source attribution and a few explicit consistency checks, not semantic entailment.
"""
from contextlib import contextmanager
from decimal import Decimal
import re
import unicodedata

VERSION = 'source_attributed_paraphrase_v1'
STOPWORDS = set('a an the of to for from in on at by with as and or that this these those '
                'we our us it its they their he she is are was were be been being '
                'do does did have has had can could may might will would shall should '
                'also then than'.split())
NEGATIONS = {'not', 'no', 'never', 'cannot', 'without', 'neither', 'nor'}
NUMBER = re.compile(r'(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?(?:(?!\w)|(?=x\b))')


def concept_key(value):
    """Retain meaningful name suffixes: bAbI+ != bAbI and C++ != C#."""
    text = unicodedata.normalize('NFKC', value).casefold()
    return ' '.join(re.findall(r'\w+(?:[+#]+)?|[+#]+', text))


def numbers(text):
    return {Decimal(m.group().replace(',', '')).normalize() for m in NUMBER.finditer(text)}


def negative(text):
    text = re.sub(r'\bnot\s+(?:only|just)\b', '', text, flags=re.I)
    return frozenset(re.findall(r'\w+', text.casefold())) & NEGATIONS


def content_words(shared, text):
    words = re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold())
    return {min(shared.base.word_forms(w), key=lambda x: (len(x), x))
            for w in words if w not in STOPWORDS | NEGATIONS}


def explicit_polarity_reversal(shared, concept, evidence):
    """Reject only a direct same-claim reversal; ambiguous scope stays a warning."""
    claim = content_words(shared, concept)
    if len(claim) < 3:
        return False
    clauses = re.split(r';|\b(?:but|whereas|however|although)\b', evidence, flags=re.I)
    aligned = [clause for clause in clauses if content_words(shared, clause) == claim]
    target = negative(concept)
    def reversed_claim(clause):
        source = negative(clause)
        # Disjoint negative forms (e.g. no/without) can be faithful paraphrases.
        return bool(source) != bool(target) or bool(source & target) and source != target
    return bool(aligned) and all(reversed_claim(clause) for clause in aligned)


def generic_resource(concept):
    generic = re.match(r'(?i)^(?:(?:a|an|the)\s+)?(?:dataset|corpus|collection|set)\s+(?:of|on|with|containing)\b', concept)
    if not generic:
        return False
    # A capitalized resource name such as Corpus of Linguistic Acceptability is valid.
    return not any(any(c.isupper() for c in token) for token in concept.split()[1:])


def validate_response(shared, value, paper):
    labels = shared.base.validate_response(value, paper, allow_quality_errors=True)
    entire_source = paper['title'] + '\n' + paper['abstract']
    source_numbers = numbers(entire_source)
    for facet in shared.FACETS:
        seen = set()
        for item in value[facet]:
            concept, evidence, source = (item[k] for k in ('concept', 'evidence', 'source'))
            shared.base.require(source in ('title', 'abstract') and evidence and evidence in paper[source],
                                'evidence must be an exact source sentence')
            key = concept_key(concept)
            shared.base.require(key not in seen, 'duplicate concept')
            seen.add(key)
            shared.base.require(not numbers(concept) - source_numbers, 'quantity absent from supplied title/abstract')
            shared.base.require(not explicit_polarity_reversal(shared, concept, evidence), 'explicit source-claim polarity reversal')
            if facet == 'dataset':
                shared.base.require(not generic_resource(concept), 'dataset requires an explicit named resource, not a collection description')
    return labels


def warnings(shared, value, paper, original_validate):
    result = []
    for facet in shared.FACETS:
        for index, item in enumerate(value[facet]):
            if item.get('source') not in ('title', 'abstract') or not item.get('evidence'):
                continue
            one = dict(paper_id=paper['paper_id'], **{f: [] for f in shared.FACETS})
            one[facet] = [item]
            try:
                original_validate(one, paper, policy='3.1')
            except ValueError as error:
                result.append(dict(facet=facet, index=index, kind='lexical_or_scope_review', message=str(error),
                                   concept=item['concept'], evidence=item['evidence']))
            if numbers(item['concept']) - numbers(item['evidence']):
                result.append(dict(facet=facet, index=index, kind='context_quantity_review',
                                   message='Quantity requires context outside the primary evidence sentence'))
    return result


@contextmanager
def scope(shared):
    """Integrate at the existing v3 assessment seam, including dataset postprocessing."""
    original_validate = shared.v3.validate_response
    original_assess = shared.v3.assess_generation
    original_normalize = shared.base.normalize
    shared.base.normalize = concept_key
    shared.v3.validate_response = lambda value, paper, policy='3.1': validate_response(shared, value, paper)

    def assess(raw, paper, policy, **kwargs):
        value, selection, audit = original_assess(raw, paper, policy, **kwargs)
        lexical_questions = [e for e in audit['validation_errors'] if 'preserve whether from the source research question' in e]
        audit['validation_errors'] = [e for e in audit['validation_errors'] if e not in lexical_questions]
        notes = warnings(shared, value, paper, original_validate)
        notes.extend(dict(kind='question_scope_review', message=e) for e in lexical_questions)
        total = sum(len(items) for f, items in selection.items() if f in shared.FACETS and isinstance(items, list)) if isinstance(selection, dict) else 0
        invalid = {match.groups() for error in audit['validation_errors']
                   if (match := re.match(r'^(problem|task|method|dataset|contribution)\[(\d+)\]:', error))}
        audit['score'] = round(10 * audit['schema_valid'] + (90 * max(0, total-len(invalid)) / total if total else 0), 4)
        audit.update(validator_policy=VERSION, semantic_entailment_verified=False,
                     score_kind='structural_source_consistency_not_semantic_confidence', validation_warnings=notes)
        return value, selection, audit

    shared.v3.assess_generation = assess
    try:
        yield
    finally:
        shared.base.normalize = original_normalize
        shared.v3.validate_response = original_validate
        shared.v3.assess_generation = original_assess
