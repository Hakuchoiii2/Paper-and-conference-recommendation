"""Small source-only R2a interventions; no evaluator or reference dependency."""
import copy
from contextlib import contextmanager
import json
import re
import unicodedata


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_scoped(shared, original, value, paper, *, policy='3.1'):
    if policy != '3.1':
        return original(value, paper, policy=policy)
    v3, base = shared.v3, shared.base
    labels = base.validate_response(value, paper, allow_quality_errors=True)
    for facet in base.FACET_NAMES:
        seen = set()
        for item in value[facet]:
            concept, evidence, source = (item[k] for k in ('concept', 'evidence', 'source'))
            require(source in ('title','abstract') and evidence and evidence in paper[source],
                    'evidence must be an exact source sentence')
            span, prefix, raw_span, suffix = v3.matching_span(concept, evidence)
            words = {w.strip('.,;:!?()') for w in base.normalize(concept).split()}
            span_words = {w.strip('.,;:!?()') for w in span}
            claim_span = raw_span
            if evidence.casefold().lstrip().startswith('although '):
                # Same narrow scope rule already present in policy3.2, without its other changes.
                claim_span = re.split(r',\s*we\s+(?:show|find|demonstrate|report)\b',raw_span,flags=re.I)[-1]
            negations = set(re.findall(r'\w+',claim_span.casefold()))
            require((negations & v3.NEGATIONS) <= words, 'shortening drops source negation')
            if facet == 'contribution':
                require(({w.strip('.,;:!?()') for w in prefix} & v3.NEGATIONS) <= words,
                        'shortening drops nearby source negation')
                require(set(re.findall(v3.NUMBER,raw_span)) <=
                        set(re.findall(v3.NUMBER,unicodedata.normalize('NFKC',concept))),
                        'shortening drops a quantity inside the finding')
                require((span_words & v3.QUALIFIERS) <= words,
                        'shortening drops a source qualification or caveat')
                require(not re.match(r'\s*[,;:-]?\s*(although|but|however|only|unless|provided)\b',suffix),
                        'finding ends before a source qualification or caveat; include the limiting clause')
            if facet == 'dataset':
                require(not re.match(r'(?i)^(?:(?:a|an|the)\s+)?(?:dataset|corpus|collection|set)\s+(?:of|on|with|containing)\b',concept)
                        and not re.match(r'(?i)^\d[\d,.]*\s+(?:tweets|posts|articles|participants|samples|documents)\b',concept),
                        'dataset requires an explicit named resource, not a collection description')
            key = base.normalize(concept).casefold()
            require(key not in seen,'duplicate concept')
            seen.add(key)
    return labels


@contextmanager
def scope_validator(shared, enabled):
    original = shared.v3.validate_response
    if enabled:
        shared.v3.validate_response = lambda value,paper,policy='3.1': validate_scoped(
            shared,original,value,paper,policy=policy)
    try:
        yield
    finally:
        shared.v3.validate_response = original


def assess(shared, raw, paper, *, scoped=False):
    with scope_validator(shared,scoped):
        return shared.v3.assess_generation(raw,paper,'3.1',prompt_version='3.7',dataset_resource_filter=True)


def flagged_items(errors):
    targets=set()
    for error in errors:
        match=re.match(r'^(problem|task|method|dataset|contribution)\[(\d+)\]:',error)
        if match:
            targets.add((match[1],int(match[2])))
    return targets


def apply_patch(shared, selection, reply, paper, targets):
    require(isinstance(reply,dict) and set(reply)=={'paper_id','edits'}
            and reply['paper_id']==paper['paper_id'],'Patch paper/schema differs')
    edits=reply['edits']
    require(isinstance(edits,list) and len(edits)<=len(targets),'Invalid edit count')
    options=shared.base.evidence_options(paper)
    seen=set(); log=[]
    for edit in edits:
        require(isinstance(edit,dict),'Edit must be an object')
        op=edit.get('op'); facet=edit.get('facet'); index=edit.get('index')
        require(isinstance(facet,str) and type(index) is int and (facet,index) in targets,
                'Edit targets an unflagged item')
        require((facet,index) not in seen,'Duplicate edit target')
        require(facet in selection and 0<=index<len(selection[facet]),'Invalid snapshot index')
        seen.add((facet,index))
        fields={'op','facet','index','reason'}
        if op=='replace':fields|={'concept','evidence_id'}
        elif op=='remove':fields|={'evidence_id','explanation'}
        else:require(op=='unresolved','Unknown patch operation')
        require(set(edit)==fields,'Wrong patch operation keys')
        require(isinstance(edit['reason'],str) and edit['reason'].strip(),'Missing source-based reason')
        if op in ('replace','remove'):
            require(isinstance(edit['evidence_id'],str) and edit['evidence_id'] in options,'Unknown source ID')
        if op=='replace':
            require(isinstance(edit['concept'],str) and edit['concept'].strip()==edit['concept']
                    and bool(edit['concept']),'Empty/untrimmed replacement')
        if op=='remove':
            require(edit['reason'] in ('unsupported','wrong_role','duplicate'),'Removal needs semantic reason')
            require(isinstance(edit['explanation'],str) and edit['explanation'].strip(),
                    'Removal needs explanation tied to source')
        log.append(dict(**edit,before=copy.deepcopy(selection[facet][index])))
    result=copy.deepcopy(selection)
    # Apply against original indices, descending: removals cannot shift later replacements.
    for edit in sorted(edits,key=lambda e:(e['facet'],e['index']),reverse=True):
        if edit['op']=='replace':
            result[edit['facet']][edit['index']]={k:edit[k] for k in ('concept','evidence_id')}
        elif edit['op']=='remove':
            result[edit['facet']].pop(edit['index'])
    for edit in edits:
        if edit['op']=='replace':
            normalized=shared.base.normalize(edit['concept']).casefold()
            require(sum(shared.base.normalize(i['concept']).casefold()==normalized
                        for i in result[edit['facet']])<=1,'Replacement duplicates another item')
    return result,log


PATCH_INSTRUCTION='''You repair ONLY the flagged facet/index items of the supplied annotation.
Use only the original evidence_options. All unflagged items are immutable. No additions.
Choose an evidence_id, then source words in original order. Preserve the original meaning,
subject, negation, metric, quantities, comparator and conditions; do not replace a positive
finding with a prior negative finding just to pass validation. Do not silently fix OCR.
Return JSON only: {"paper_id":"supplied ID","edits":[...]}.
Each edit is exactly one of:
{"op":"replace","facet":"method","index":0,"concept":"source phrase","evidence_id":"A0","reason":"source-based explanation"}
{"op":"remove","facet":"method","index":0,"evidence_id":"A0","reason":"unsupported","explanation":"why source does not support this idea"}
{"op":"unresolved","facet":"method","index":0,"reason":"why it cannot be safely repaired"}.
Removal reasons are only unsupported, wrong_role, duplicate. A lexical/order error alone
does not justify removal. Repair supported content first. Reasons are audit evidence,
not proof of semantic correctness. Indices refer to the supplied current annotation.
Use [] for edits if no safe changes exist. Never return the complete annotation.'''
