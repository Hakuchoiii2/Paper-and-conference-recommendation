"""Shared optional paper-ID scope for calibration runs."""

import os
import random


def get_scope_ids():
    value = os.environ.get("DATA_PREPARATION_SCOPE_IDS")
    if value is None:
        return None
    paper_ids = {paper_id.strip() for paper_id in value.split(",") if paper_id.strip()}
    if not paper_ids:
        raise ValueError("DATA_PREPARATION_SCOPE_IDS was set but contains no paper IDs")
    return paper_ids


def filter_by_scope(records):
    paper_ids = get_scope_ids()
    if paper_ids is None:
        return records
    return [record for record in records if record.get("paper_id") in paper_ids]


def split_gold_ids(paper_ids):
    shuffled_ids = sorted(paper_ids)
    random.Random(42).shuffle(shuffled_ids)
    split_point = int(len(shuffled_ids) * 0.7)
    return set(shuffled_ids[:split_point]), set(shuffled_ids[split_point:])
