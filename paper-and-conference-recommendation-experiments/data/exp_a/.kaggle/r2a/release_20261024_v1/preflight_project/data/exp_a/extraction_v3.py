"""Source-grounded extract/review, scored retries, and explicitly audited fallbacks."""
import json
import re
import unicodedata

from functools import partial

import build_exp_a as base

PROTOCOL = 'two_pass_v3'
PROMPT_POLICIES = {'3.1': '3.1', '3.2': '3.2', '3.3': '3.1', '3.4': '3.1', '3.5': '3.1', '3.6': '3.1', '3.7': '3.1'}
NEGATIONS = {'not', 'no', 'never', 'without', 'cannot', 'neither', 'nor'}
NUMBER = r'\d+(?:[.,]\d+)*'
QUALIFIERS = {'although', 'but', 'however', 'only', 'unless', 'provided'}
NO_VALID_REVIEW = 'No valid self-review within the attempt budget; best available output requires review'
# shortcut: common language-only labels; other ambiguous resource names still need source review.
LANGUAGE_NAMES = {'arabic', 'assamese', 'bengali', 'danish', 'dutch', 'english', 'finnish', 'french',
                  'german', 'haitian', 'hindi', 'lao', 'russian', 'swedish', 'tamil', 'zulu'}
REVIEW = '''Read the original title and ALL abstract evidence_options again. Revise the draft:
1. TASK: keep the actual operational objective, not presenting/proposing a method,
   reporting a result, or a training/evaluation step when it is not the research objective.
2. METHOD: recover techniques actually used; exclude background methods and future suggestions.
3. DATASET: recover every explicitly named resource used, including names in the title.
   Do not replace names with sample counts, generic collections, or tasks. Keep [] if unnamed.
4. CONTRIBUTION: recover new artifacts AND supported findings. A new method/resource may
   occur in both its operational facet and contribution when both roles are explicit.
5. PROBLEM: keep the concrete addressed limitation/question, not background interest
   or a statement that a topic is popular. Use [] when no limitation is explicit.
Split distinct techniques/resources into separate labels; avoid parent/child duplicates.
Keep valid draft concepts. Preserve scope, negation, quantities, metrics and comparisons.
Use short concrete source phrases; a finding may need more words than an artifact name.
Do not fill unsupported facets. Do not infer missing facts or create a confidence score.
Select evidence_id first, then copy a phrase from that ONE sentence in source order.
Fix every listed facet/index error. Preserve valid labels and qualifications such
as 'although only partially successful'; a positive claim must not lose its caveat.
If source text has broken words, do not silently repair or invent source tokens;
choose an intact supported phrase or leave the unsupported item out.
Return the complete corrected JSON with the original paper_id and evidence IDs.'''
REVIEW_33 = '''\nFor this revision, preserve compact names while repairing coverage:
- METHOD: one independent technique, feature or procedure per label; no whole
  presenting/proposing sentence when its method names suffice.
- TASK: recover each actual objective and its distinguishing setting from the
  title/abstract; do not replace the objective with a procedure or a result.
- CONTRIBUTION: check introduced artifact names, positive findings AND negative/null
  findings separately. Keep each finding's own subject, metric, setting and caveat.
- PROBLEM: accept only an explicit addressed limitation/question; do not invent
  whether/how questions or turn a task name into a limitation.
Keep supported compact labels; add omissions rather than rewriting every list.
Split independent concepts, not one named technique into parent/child duplicates.\n'''
REVIEW_34 = REVIEW_33 + '''
Focus this review on coverage and the role of PROBLEM:
- An all-empty draft is not evidence that this is non-research text. Re-read T0
  and every abstract sentence for an actual objective, technique, or introduced
  artifact. Recover supported content; do not fill unsupported facets.
- For each PROBLEM label, identify the explicit limitation or unresolved research
  question that motivates this work. A task called a "problem" is still a TASK.
  A result found by this study belongs in CONTRIBUTION, even if it is negative.
  Remove wrong-role problem labels; keep supported ideas in their proper facet.
- Preserve the subject of a limitation. A bare "this", "it", or a task name does
  not state what is limited. Use a self-contained phrase from one source sentence.
Keep the other supported labels and their granularity. Do not rewrite all facets
or invent a limitation to avoid an empty PROBLEM list.
'''
REVIEW_35 = REVIEW_34 + '''
Before accepting PROBLEM=[], scan every original source sentence again:
- Look for a stated shortcoming of existing approaches, an inadequate assumption,
  a threat to validity, an unmet requirement, known computational difficulty,
  or an explicitly unresolved question that this work addresses.
- A motivating limitation can be stated in background as a declarative sentence.
  It need not contain a question mark or the words "we address". Check its link
  to this work's objective in the supplied text; unrelated background is not enough.
- Separate a known limitation motivating the work from a new result reported by
  this study. Keep the former in PROBLEM and the latter in CONTRIBUTION when the
  source explicitly supports both; one does not replace the other.
- If a draft problem is unsupported or copied from an instruction example, remove
  it, then search the actual paper for a supported limitation before choosing [].
Choose the actual evidence_id first. Copy a source phrase preserving the affected
subject, what is limited, and its conditions. Use a fuller span when abbreviation
loses the meaning. Do not turn a task/topic or a new negative result into a problem.
Keep PROBLEM=[] when no motivating limitation/question is explicit. Preserve the
other supported facet labels; return the complete JSON, without an explanation.
'''
REVIEW_36 = REVIEW_35 + '''
DATASET inventory: read T0 and every original abstract sentence, including the
results/findings. Recover explicitly named corpora, benchmarks and treebanks
used for training, testing or analysis even when mentioned only in a finding.
Keep each independent resource/version in a separate item. For a shared name
prefix followed by several years/versions, keep each supported prefix and suffix
in source order, citing the same sentence. Prefer the bare resource name if
adding descriptors would reverse source words. Do not merge independent names.
Sample counts, languages, a game being played, a computing platform, or generic
data from a repository without a named dataset do not establish a resource name.
Return the complete JSON. The review scope below controls which facets may change;
preserve all other lists exactly. Within scope, keep valid independent concepts
and repair/add omissions rather than replacing a list with a broad summary.
'''
REVIEW_37 = REVIEW_36 + '''
METHOD and CONTRIBUTION are also in scope, including empty lists. Work sentence
by sentence before editing: inventory the actual algorithms/models, feature
groups and procedures, then compare each independent idea with the draft.
For contribution, check introduced artifact names separately from findings;
do not let an artifact disappear because method already names it. Inspect
negative/null results separately from benefits. Use the source sentence IDs
highlighted below as candidates to inspect, not mandatory labels: skip prior
work, goals, unsupported novelty and data that has no operational method role.
Keep valid draft items while adding omissions. Expand a finding in the SAME
evidence sentence to restore its subject, language/population, conditions,
comparison or caveat; do not replace it with a weaker or shorter assertion.
Keep methods and artifact names compact. Do not duplicate an acronym and its
expanded name or merge independent techniques into a long summary.
'''
STAGNANT_REVIEW = '''
The last review left the applied concepts and validation errors unchanged.
Do not repeat that answer. Rebuild the scoped invalid items from the ORIGINAL
evidence_options: choose the correct evidence_id first, then an intact source
phrase with its original word order. Preserve whether, negation and conditions.
Recheck missing named resources in result sentences and split independent names.
Keep valid items; do not remove a supported concept just to silence a lexical error.
'''


def policy_for_prompt(version):
    base.require(version in PROMPT_POLICIES, 'Unknown extraction prompt version')
    return PROMPT_POLICIES[version]


def matching_span(concept, evidence):
    tokens = [base.word_forms(w) for w in base.normalize(concept).split()]
    words = base.normalize(evidence).split()
    forms = [base.word_forms(w) for w in words]
    spans = []
    for start, form in enumerate(forms):
        if not tokens or not form & tokens[0]:
            continue
        end = start
        try:
            for token in tokens[1:]:
                end = next(i for i in range(end + 1, len(forms)) if forms[i] & token)
        except StopIteration:
            continue
        spans.append((start, end))
    if not spans:
        missing = [word for word in base.normalize(concept).split()
                   if not any(base.word_forms(word) & form for form in forms)]
        split = next(((words[i], words[i+1], word) for word in missing for i in range(len(words)-1)
                      if word.isalpha() and len(word) >= 5 and words[i]+words[i+1] == word), None)
        hint = f'; possible split source word: {split[0]} {split[1]} -> {split[2]}; preserve raw evidence' if split else ''
        raise ValueError('concept must use source words in their original order; no invented synonyms' + hint)
    start, end = min(spans, key=lambda span: span[1] - span[0])
    raw = unicodedata.normalize('NFKC', evidence).casefold()
    offsets = list(re.finditer(r'\w+', raw))
    left, right = offsets[start].start(), offsets[end].end()
    for number in re.finditer(NUMBER, raw):
        if number.start() < right and number.end() > left:
            left, right = min(left, number.start()), max(right, number.end())
    raw_span = raw[left:right]
    return words[start:end+1], words[max(0, start-3):start], raw_span, raw[right:]


def validate_response(value, paper, *, policy='3.1'):
    labels = base.validate_response(value, paper, allow_quality_errors=True)
    for facet in base.FACET_NAMES:
        seen = set()
        for item in value[facet]:
            concept, evidence, source = (item[k] for k in ('concept', 'evidence', 'source'))
            base.require(source in ('title', 'abstract') and evidence and evidence in paper[source],
                         'evidence must be an exact source sentence')
            span, prefix, raw_span, suffix = matching_span(concept, evidence)
            concept_words = {w.strip('.,;:!?()') for w in base.normalize(concept).split()}
            span_words = {w.strip('.,;:!?()') for w in span}
            claim_span = raw_span
            if policy == '3.2' and evidence.casefold().lstrip().startswith('although '):
                # A background failure and the authors' contrasting finding have different polarity scopes.
                claim_span = re.split(r',\s*we\s+(?:show|find|demonstrate|report)\b', raw_span)[-1]
            negation_words = set(re.findall(r'\w+', claim_span)) if policy == '3.2' else span_words
            base.require((negation_words & NEGATIONS) <= concept_words, 'shortening drops source negation')
            if facet == 'contribution':
                nearby_negations = {w.strip('.,;:!?()') for w in prefix} & NEGATIONS
                base.require(nearby_negations <= concept_words, 'shortening drops nearby source negation')
                base.require(set(re.findall(NUMBER, raw_span))
                             <= set(re.findall(NUMBER, unicodedata.normalize('NFKC', concept))),
                             'shortening drops a quantity inside the finding')
                base.require((span_words & QUALIFIERS) <= concept_words,
                             'shortening drops a source qualification or caveat')
                # shortcut: nearby markers cannot prove complete semantic equivalence; retain source review.
                trailing = re.match(r'\s*[,;:-]?\s*(although|but|however|only|unless|provided)\b', suffix)
                base.require(not trailing, 'finding ends before a source qualification or caveat; include the limiting clause')
                if policy == '3.2':
                    condition = re.search(r'^\s*(?:(?:however|furthermore|nevertheless),\s*)?'
                                          r'((?:in the case of|when|if|unless|provided that|under|for)\b.*?),\s*'
                                          r'(?!(?:when|if|unless|under)\b)',
                                          evidence.casefold())
                    if condition:
                        linking = {'in', 'the', 'case', 'of', 'is', 'are', 'was', 'were', 'a', 'an', 'that'}
                        required = set(base.normalize(condition[1]).split()) - linking
                        forms = [base.word_forms(w) for w in concept_words]
                        base.require(all(any(base.word_forms(w) & f for f in forms) for w in required),
                                     'finding drops leading source condition: ' + condition[1])
            if policy == '3.2' and facet == 'problem' and re.search(r'\bwhether\b', evidence, re.I):
                base.require('whether' in concept_words, 'problem drops whether and turns a question into an assertion')
            if facet == 'dataset':
                base.require(not re.match(r'(?i)^(?:(?:a|an|the)\s+)?(?:dataset|corpus|collection|set)\s+(?:of|on|with|containing)\b', concept)
                             and not re.match(r'(?i)^\d[\d,.]*\s+(?:tweets|posts|articles|participants|samples|documents)\b', concept),
                             'dataset requires an explicit named resource, not a collection description')
                if policy == '3.2':
                    strong_name = bool(re.search(r'\b(?:[A-Z]{2,}[\w.-]*|[A-Za-z][\w.-]*\d[\w.-]*)\b', concept))
                    names = [w for w in re.findall(r'\b[A-Z][\w.-]*\b', evidence)
                             if w.casefold() in concept_words and w not in {'We', 'Our', 'The', 'This', 'An', 'A', 'In'}]
                    resource_context = re.search(r'\b(corpus|corpora|datasets?|benchmarks?|treebanks?|databases?|collections?|lexicons?|reviews?)\b', evidence, re.I)
                    generic = re.search(r'(?i)^(?:\d[\d,.]*\s+|annotated\b|synthetic\b|real world\b|linked knowledge\b)|^[\w-]+ test collection$', concept)
                    language = (re.search(r'\blanguages?\b', evidence, re.I)
                                and not re.search(r'\b(corpus|dataset|benchmark|treebank|database|collection|lexicon)\b', evidence, re.I))
                    named_explicitly = re.search(r'\b(?:dataset|corpus|benchmark|collection)\s+(?:named|called)\s+[\"\']?'
                                                 + re.escape(concept) + r'\b', evidence, re.I)
                    language_only = base.normalize(concept) in LANGUAGE_NAMES and not named_explicitly
                    base.require((strong_name or (names and resource_context)) and not (generic and not strong_name)
                                 and not (language and not strong_name) and not language_only,
                                 'dataset requires an explicit named resource; language names and generic collections are not resource names')
            key = base.normalize(concept).casefold()
            base.require(key not in seen, 'duplicate concept')
            seen.add(key)
    return labels


def ground_response(value, paper):
    base.require(isinstance(value, dict) and value.get('paper_id') == paper['paper_id'], 'wrong paper_id')
    base.require(set(value) == {'paper_id', *base.FACET_NAMES}, 'wrong facet keys')
    options = base.evidence_options(paper)
    grounded = dict(paper_id=paper['paper_id'])
    for facet in base.FACET_NAMES:
        base.require(isinstance(value[facet], list), f'{facet}: expected list')
        grounded[facet] = []
        for item in value[facet]:
            base.require(isinstance(item, dict) and set(item) == {'concept', 'evidence_id'}, 'wrong concept/evidence_id keys')
            base.require(isinstance(item['evidence_id'], str) and item['evidence_id'] in options, 'unknown evidence_id')
            grounded[facet].append(dict(concept=item['concept'], **options[item['evidence_id']]))
    validate_response(grounded, paper)
    return grounded


def source_quality(paper, attempts, *, policy='3.1'):
    issues = []
    text = paper['abstract'].casefold()
    if 'thank you for downloading' in text or 'our book servers' in text:
        issues.append('Abstract contains download/book-server boilerplate; inspect the original source')
    split_errors = [error for row in attempts for error in row['validation_errors']
                    if 'split source word' in error]
    if split_errors:
        issues.append('Possible split source words detected; raw source was preserved')
    truncated = policy == '3.2' and bool(re.search(r'\b(?:to|the|a|an|of|and|or|with|for|that|which)\s*$', text))
    encoding = policy == '3.2' and bool(re.search(r'[\u0080-\u009f\ufffd]', text))
    if truncated:
        issues.append('Possible truncated abstract ending in a linking word; inspect the original source')
    if encoding:
        issues.append('Possible text encoding corruption; raw source was preserved')
    status = ('suspected_non_research' if 'thank you for downloading' in text or 'our book servers' in text
              else 'suspected_text_corruption' if split_errors or encoding
              else 'suspected_incomplete_source' if truncated else 'no_flag_detected')
    return dict(status=status, issues=issues)


def assess_generation(raw, paper, policy, *, prompt_version=None, dataset_resource_filter=False):
    base.require(policy in ('3.1', '3.2'), 'Unknown extraction policy')
    value, selection, assessment = base.assess_generation(
        raw, paper, validator=partial(validate_response, policy=policy), score_version=policy)
    if prompt_version in ('3.4', '3.5', '3.6', '3.7') and assessment['schema_valid']:
        visible = filter_named_datasets(value, paper)[0] if dataset_resource_filter else value
        if (not any(visible[facet] for facet in base.FACET_NAMES)
                and source_quality(paper, [], policy=policy)['status'] != 'suspected_non_research'):
            # shortcut: flags empty extraction for review; does not prove which facets the source supports.
            assessment['validation_errors'].append(
                'coverage: all facets are empty; re-read the title and abstract for supported objectives, '
                'techniques and artifacts. Keep unsupported facets empty; unresolved empty output requires review.')
    if prompt_version in ('3.6', '3.7') and assessment['schema_valid']:
        for index, item in enumerate(value['problem']):
            # shortcut: guards explicit research-question frames, not every implicit uncertainty.
            question = re.search(r'\b(?:investigat\w*|examin\w*|explor\w*|determin\w*|test\w*|ask\w*)\s+whether\b',
                                 item['evidence'], re.I)
            if question and not re.search(r'\bwhether\b', item['concept'], re.I):
                assessment['validation_errors'].append(
                    f'problem[{index}]: preserve whether from the source research question; do not turn it into an assertion')
    if policy == '3.2':
        # shortcut: this catches explicit experimental negation, not every semantic omission.
        for evidence_id, source in base.evidence_options(paper).items():
            text = source['evidence'].casefold()
            negative = re.search(r'\b(?:not(?! only\b| just\b)|no|never|cannot)\b', text)
            if source['source'] != 'abstract' or not negative:
                continue
            prefix = text[:negative.start()]
            authored = (re.search(r'\b(?:our experiments|in our experiments|our results|we (?:find|found|observe|observed|report|show))\b', prefix)
                        or re.search(r'\bwe\s+(?:(?:did|do|could|can)\s+)?$', prefix))
            result_claim = re.match(r'(?:not|no|never|cannot)\s+(?:(?:completely|significantly|consistently|further|statistically)\s+)*'
                                    r'(?:obtain\w*|achiev\w*|improv\w*|outperform\w*|increas\w*|decreas\w*|reduc\w*|mitigat\w*|observ\w*|benefit\w*|difference\w*)\b',
                                    text[negative.start():])
            if not authored or not result_claim:
                continue
            covered = any(item['evidence'] == source['evidence']
                          and re.search(r'\b(?:not(?! only\b| just\b)|no|never|cannot)\b', item['concept'], re.I)
                          for item in value['contribution'])
            if not covered:
                assessment['validation_errors'].append(
                    f'contribution: omitted explicit negative finding in {evidence_id}; review the whole source sentence: {source["evidence"]}')
    return value, selection, assessment


def attempt_rank(attempt, policy, *, prompt_version=None):
    if policy == '3.1':
        rank = base.attempt_rank(attempt)
        return rank + (attempt['stage'] == 'review', attempt['attempt']) if prompt_version in ('3.6', '3.7') else rank
    omitted = sum('omitted explicit negative finding' in e for e in attempt['validation_errors'])
    return (attempt['schema_valid'], attempt['parseable'], -omitted, attempt['score'],
            attempt['stage'] == 'review', attempt['attempt'])


def review_facets(previous, prompt_version='3.6'):
    if previous is None or not previous['schema_valid']:
        return list(base.FACET_NAMES)
    scope = {'problem', 'dataset'}
    if prompt_version == '3.7':
        scope.update(('method', 'contribution'))
    for error in previous['validation_errors']:
        facet = error.split(':', 1)[0].split('[', 1)[0]
        if facet not in base.FACET_NAMES:
            return list(base.FACET_NAMES)
        scope.add(facet)
    return [facet for facet in base.FACET_NAMES if facet in scope]


def preserve_review_items(previous, reviewed, paper, facet, policy):
    """Keep source-valid items while accepting additions and same-sentence expansions."""
    result = list(reviewed)
    options = base.evidence_options(paper)
    duplicates = len({base.normalize(item['concept']) for item in reviewed}) != len(reviewed)

    def valid(item):
        if not isinstance(item['evidence_id'], str) or item['evidence_id'] not in options:
            return False
        one = dict(paper_id=paper['paper_id'], **{f: [] for f in base.FACET_NAMES})
        one[facet] = [dict(concept=item['concept'], **options[item['evidence_id']])]
        try:
            validate_response(one, paper, policy=policy)
        except ValueError:
            return False
        return True

    def contains(whole, part):
        try:
            matching_span(part, whole)
        except ValueError:
            return False
        return True

    for old in previous:
        if not valid(old):
            continue
        if any(base.normalize(old['concept']) == base.normalize(new['concept']) for new in result):
            continue
        related = [(i, new) for i, new in enumerate(result)
                   if new['evidence_id'] == old['evidence_id'] and valid(new)]
        # shortcut: ordered-word containment preserves wording, not semantic equivalence or facet role.
        if any(contains(new['concept'], old['concept']) for _, new in related):
            continue
        shorter = [i for i, new in related if contains(old['concept'], new['concept'])]
        if shorter and not duplicates:
            result[shorter[0]] = old
            for i in reversed(shorter[1:]):
                del result[i]
        else:
            result.append(old)
    return result


def coverage_candidates(paper, selection):
    """Highlight uncited source sentences for review; these are not validation failures."""
    candidates = dict(method=[], contribution=[])
    options = base.evidence_options(paper)
    cited = {f: {item['evidence_id'] for item in (selection or {}).get(f, [])
                 if isinstance(item['evidence_id'], str) and item['evidence_id'] in options} for f in candidates}
    for evidence_id, option in options.items():
        text = option['evidence'].casefold()
        method = re.search(r'\b(?:algorithms?|models?|features?|classifiers?|frameworks?|procedures?|'
                           r'meta-analysis|synthesis|survey|adaptation|training|analysis|we (?:use|utilize|apply|adopt))\b', text)
        artifact = re.search(r'\bwe (?:present|propose|introduce|develop|construct|design|build|built)\b|'
                             r'\b(?:presented|introduced|developed) in (?:this|the) paper\b|'
                             r'\bscripts?\b.*\bavailable\b', text)
        negative = re.search(r'\b(?:not|no|never|cannot)\b.*\b(?:improv\w*|obtain\w*|achiev\w*|'
                             r'mitigat\w*|outperform\w*|effective|significant)\b', text)
        for facet, cue in (('method', method), ('contribution', artifact or negative)):
            if cue and evidence_id not in cited[facet]:
                candidates[facet].append(evidence_id)
    return candidates


def assess_attempt(raw, paper, policy, *, prompt_version, dataset_resource_filter=False, previous=None):
    options = dict(prompt_version=prompt_version, dataset_resource_filter=dataset_resource_filter)
    value, selection, assessment = assess_generation(raw, paper, policy, **options)
    if prompt_version not in ('3.6', '3.7'):
        return value, selection, assessment, {}
    scope = review_facets(previous[0] if previous else None, prompt_version)
    applied = raw
    if previous and previous[0]['schema_valid'] and assessment['schema_valid']:
        merged = dict(previous[1], **{facet: selection[facet] for facet in scope})
        if prompt_version == '3.7':
            for facet in ('method', 'contribution'):
                merged[facet] = preserve_review_items(previous[1][facet], selection[facet], paper, facet, policy)
        applied = json.dumps(merged, ensure_ascii=False)
        value, selection, assessment = assess_generation(applied, paper, policy, **options)
    return value, selection, assessment, dict(applied_output=applied, review_facets=scope)


def filter_named_datasets(value, paper):
    """Apply the measured resource guard without treating lexical errors as semantic errors."""
    kept, removed = [], []
    for index, item in enumerate(value['dataset']):
        one = dict(paper_id=paper['paper_id'], **{facet: [] for facet in base.FACET_NAMES})
        one['dataset'] = [item]
        try:
            validate_response(one, paper, policy='3.2')
        except ValueError as error:
            if 'dataset requires an explicit named resource' in str(error):
                removed.append(dict(index=index, **item, reason=str(error)))
                continue
        kept.append(item)
    return dict(value, dataset=kept), dict(policy='named_resource_v3_2', removed=removed)


def validate_saved(value, paper, metadata):
    policy = metadata.get('request_parameters', {}).get('extraction_policy_version', '3.1')
    prompt_version = metadata.get('prompt_version', metadata.get('request_parameters', {}).get('extraction_prompt_version', policy))
    base.require(policy == policy_for_prompt(prompt_version),
                 'saved extraction policy differs from prompt version')
    base.require(metadata.get('request_parameters', {}).get('extraction_prompt_version', prompt_version) == prompt_version,
                 'saved extraction prompt version audit differs')
    attempts = metadata.get('attempt_scores', [])
    base.require(isinstance(attempts, list) and len(attempts) >= 2, 'missing extract/review audit')
    base.require(metadata.get('self_review_completed') is True
                 and metadata.get('attempts_used') == len(attempts), 'incomplete review audit')
    base.require([row.get('attempt') for row in attempts] == list(range(1, len(attempts)+1))
                 and [row.get('stage') for row in attempts] == ['extract'] + ['review'] * (len(attempts)-1),
                 'extract/review audit order differs')
    selected = None
    recovered = None
    filtered = metadata.get('request_parameters', {}).get('dataset_resource_filter', False)
    base.require(type(filtered) is bool, 'dataset_resource_filter must be boolean')
    if prompt_version in ('3.6', '3.7'):
        application = 'coverage_preserving_v3_7' if prompt_version == '3.7' else 'facet_scoped_v3_6'
        base.require(metadata['request_parameters'].get('review_application') == application,
                     'saved review application differs')
    previous = None
    for row in attempts:
        candidate, selection, assessment, application = assess_attempt(row['raw_output'], paper, policy,
            prompt_version=prompt_version, dataset_resource_filter=filtered, previous=previous)
        base.require(all(row.get(key) == expected for key, expected in application.items()),
                     'saved review application differs from raw output and previous attempt')
        base.require(all(row.get(key) == assessment[key]
                         for key in ('score', 'schema_valid', 'parseable', 'validation_errors')),
                     'attempt score or validation errors differ from raw output')
        if row['attempt'] == metadata.get('attempt'):
            selected, recovered = row, candidate
        previous = row, selection
    if filtered and recovered is not None:
        recovered, audit = filter_named_datasets(recovered, paper)
        base.require(metadata.get('postprocessing') == audit, 'dataset filter audit differs from selected raw output')
    else:
        base.require('postprocessing' not in metadata, 'unexpected dataset filter audit')
    base.require(selected is not None and recovered == value, 'selected evidence differs from raw output')
    base.require(metadata.get('selected_score') == selected['score'], 'selected score differs from audit')
    fallback = metadata.get('fallback_used')
    base.require(type(fallback) is bool and metadata.get('validation_passed') is (not fallback),
                 'fallback cannot claim successful validation')
    if fallback:
        base.require(selected == max(attempts, key=lambda row: attempt_rank(row, policy, prompt_version=prompt_version)),
                     'fallback is not the best scored attempt')
        base.require(not any(row['stage'] == 'review' and not row['validation_errors'] for row in attempts),
                     'fallback hides a valid self-review')
        base.require(metadata.get('validation_errors') == selected['validation_errors'] + [NO_VALID_REVIEW],
                     'fallback hides selected errors or incomplete self-review')
    else:
        base.require(selected == attempts[-1] and selected['stage'] == 'review'
                     and not selected['validation_errors'] and metadata.get('validation_errors') == [],
                     'missing valid review audit')
    base.require(metadata.get('source_quality') == source_quality(paper, attempts, policy=policy), 'source-quality audit differs')
    return base.validate_response(value, paper, allow_quality_errors=True) if fallback else validate_response(value, paper, policy=policy)


def annotate(paper, instruction, config, runtime, generate_text, failure_path):
    base.require(config['max_attempts'] >= 2, 'two passes require at least two attempts')
    policy = policy_for_prompt(config.get('prompt_version', '3.1'))
    source = dict(paper_id=paper['paper_id'], evidence_options={k: v['evidence'] for k, v in base.evidence_options(paper).items()})
    original = [dict(role='system', content=instruction + '\nReturn JSON only. Schema: ' + json.dumps(base.SCHEMA)),
                dict(role='user', content=json.dumps(source, ensure_ascii=False))]
    attempts, candidates, feedback, previous = [], [], '', None
    audit_path = failure_path.parent / 'attempt_audits' / f'{paper["paper_id"]}.json'
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    def finish(index, fallback):
        value, selected = candidates[index]
        chosen = attempts[index]
        postprocessing = None
        if config.get('dataset_resource_filter', False):
            value, postprocessing = filter_named_datasets(value, paper)
        errors = chosen['validation_errors'] + ([NO_VALID_REVIEW] if fallback else [])
        quality = source_quality(paper, attempts, policy=policy)
        usage = {key: sum(row['usage'].get(key, 0) for row in attempts)
                 for key in {key for row in attempts for key in row['usage']}}
        audit = dict(paper_id=paper['paper_id'], selected_attempt=chosen['attempt'], selected_score=chosen['score'],
                     fallback_used=fallback, validation_passed=not fallback, validation_errors=errors,
                     source_quality=quality, attempt_scores=attempts)
        if postprocessing is not None:
            audit['postprocessing'] = postprocessing
        base.write_json(audit_path, audit)
        if fallback:
            base.write_json(failure_path, audit)
            print(f"BEST AVAILABLE {paper['paper_id']}: attempt {chosen['attempt']}; "
                  f"score={chosen['score']:.2f}/100; saved with review flags", flush=True)
        if quality['issues']:
            print(f"SOURCE QUALITY {paper['paper_id']}: {quality['status']}", flush=True)
        metadata = dict(**runtime, extraction_protocol=PROTOCOL, self_review_completed=True,
                           attempts_used=len(attempts), attempt=chosen['attempt'], seed=chosen['seed'],
                           selected_score=chosen['score'], attempt_scores=attempts, evidence_selection=selected,
                           usage=usage, generation_seconds=sum(row['generation_seconds'] for row in attempts),
                           fallback_used=fallback, validation_passed=not fallback, validation_errors=errors,
                           source_quality=quality, request_parameters=dict(
                               max_new_tokens=config['max_new_tokens'], max_attempts=config['max_attempts'],
                               do_sample=False, source_grounding='ordered_source_words', self_review=True,
                               score_kind='source_validity_fraction' if policy == '3.2' else 'source_support_heuristic',
                               extraction_prompt_version=config.get('prompt_version', '3.1'),
                               extraction_policy_version=policy))
        if postprocessing is not None:
            metadata['postprocessing'] = postprocessing
            metadata['request_parameters']['dataset_resource_filter'] = True
        if config.get('prompt_version') in ('3.6', '3.7'):
            metadata['request_parameters']['review_application'] = (
                'coverage_preserving_v3_7' if config['prompt_version'] == '3.7' else 'facet_scoped_v3_6')
        return value, metadata

    for attempt in range(config['max_attempts']):
        stage = 'extract' if attempt == 0 else 'review'
        messages = list(original)
        if previous is not None:
            checklist = ('\nBefore revising, inventory the source sentences for the main task, actual techniques, '
                         'named resources, introduced artifacts, and positive AND negative findings. '
                         'Compare that inventory with the draft; restore omitted ideas. Keep one independent '
                         'technique per label. A named language or a sample description is not a named dataset. '
                         'Retain leading conditions, population/language scope, and whether/hypothesis status. '
                         'An empty unsupported facet is correct and earns no penalty.\n' if policy == '3.2' else '')
            if config.get('prompt_version') in ('3.3', '3.4', '3.5', '3.6', '3.7'):
                checklist = {'3.3': REVIEW_33, '3.4': REVIEW_34, '3.5': REVIEW_35, '3.6': REVIEW_36, '3.7': REVIEW_37}[config['prompt_version']]
            if config.get('prompt_version') in ('3.6', '3.7'):
                checklist += '\nReview scope: ' + json.dumps(review_facets(attempts[-1], config['prompt_version'])) + '.\n'
                if config['prompt_version'] == '3.7':
                    selection = candidates[-1][1] if attempts[-1]['schema_valid'] else None
                    checklist += '\nUncited source sentence candidates to inspect: ' + json.dumps(coverage_candidates(paper, selection)) + '.\n'
                if (len(attempts) >= 2 and candidates[-1][1] == candidates[-2][1]
                        and attempts[-1]['validation_errors'] == attempts[-2]['validation_errors']):
                    checklist += STAGNANT_REVIEW
            messages += [dict(role='assistant', content=previous), dict(role='user', content=REVIEW + checklist + feedback)]
        seed = config['seed'] + int(paper['paper_id'][1:]) * config['max_attempts'] + attempt
        raw, generation = generate_text(messages, seed)
        raw = raw.encode('utf-8', errors='backslashreplace').decode('utf-8')
        value, selected, assessment, application = assess_attempt(raw, paper, policy,
            prompt_version=config.get('prompt_version'),
            dataset_resource_filter=config.get('dataset_resource_filter', False),
            previous=(attempts[-1], candidates[-1][1]) if attempts else None)
        errors = assessment['validation_errors']
        candidates.append((value, selected))
        attempts.append(dict(attempt=attempt+1, stage=stage, seed=seed, raw_output=raw,
                             **assessment, **application, usage=generation.get('usage', {}),
                             generation_seconds=generation.get('generation_seconds', 0)))
        base.write_json(audit_path, dict(paper_id=paper['paper_id'], attempt_scores=attempts))
        print(f"{paper['paper_id']}: {stage} {attempt+1}/{config['max_attempts']}; "
              f"score={assessment['score']:.2f}/100; validation_errors={len(errors)}", flush=True)
        for error in errors:
            print(f"  {error}", flush=True)
        if stage == 'review' and not errors:
            return finish(attempt, False)
        feedback = '\nCorrect these validation errors using the original source. Return complete JSON:\n' + '\n'.join(errors)
        previous = application.get('applied_output', raw)
    best = max(range(len(attempts)), key=lambda index: attempt_rank(attempts[index], policy,
        prompt_version=config.get('prompt_version')))
    return finish(best, True)
