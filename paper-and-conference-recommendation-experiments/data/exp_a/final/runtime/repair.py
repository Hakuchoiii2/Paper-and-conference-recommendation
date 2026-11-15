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
    return gold_validator.validate_response(shared, value, paper)


@contextmanager
def scope_validator(shared, enabled):
    if enabled:
        with gold_validator.scope(shared):
            yield
    else:
        yield


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

import importlib.util
from pathlib import Path
_gold_spec = importlib.util.spec_from_file_location('gold400_packaged_validator', Path(__file__).with_name('gold_validator.py'))
gold_validator = importlib.util.module_from_spec(_gold_spec)
_gold_spec.loader.exec_module(gold_validator)
