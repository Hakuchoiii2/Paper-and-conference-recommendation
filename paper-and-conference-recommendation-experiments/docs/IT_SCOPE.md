# IT scope and corpus review

Versioned policy: `configs/scope.json`. Include computing research and software:
AI/ML, NLP, retrieval, software engineering, databases, networks/security,
distributed systems, computer vision, HCI and explicit computational/bioinformatics
methods applied to other fields. Do not include an ordinary medical/biological
finding just because it mentions models, networks, statistics or images.

CSFCube datasheet documents ACL query papers and CS arXiv candidate papers sampled
from S2ORC: https://github.com/iesl/CSFCube/blob/v1.1/datasheet.md . This is source
sampling evidence, not a fabricated per-paper subject label. Overrides can exclude
individual CSFCube records if later audit finds out-of-scope/noisy data.

SciFact has no universal IT classification. Admission requires an explicit IT
phrase in the title or an IT phrase plus method marker in the same abstract
sentence. A known scope override can supersede that heuristic with an auditable
reason. The software/bioinformatics papers found by Codex were inspected to correct
known false positives/negatives; this is not an exhaustive human review.

Outputs:
- `scope_audit.jsonl`: every raw paper's source ID, title, source line,
  included flag, reason, and evidence. Unclear matches are `review_pending` and
  excluded until an override is approved.
- `corpus_report.json`: source counts, merged duplicates, conflicting titles,
  target gaps and provisional status.
- `id_map.jsonl`: all source aliases with canonical IDs and source fingerprints.

To review, locate the raw source record by its ID/line, inspect title/abstract and
metadata, then add an override keyed by `source:source_id`, for example:

```json
{"include": false, "reviewer": "Khai", "reason": "Only reports a biological result; no IT method or software contribution."}
```

Increment the scope policy version when its meaning changes. Run corpus and
fixture builders sequentially, then validator/tests. Do not edit processed papers
directly or delete the delivered ID map to resample IDs. Existing source IDs are
reserved and re-inclusions recover them. Conflicting issued dedup IDs require
manual versioned reconciliation, not silent renumbering.

Limit: exact phrases miss synonyms and method markers may match background prose.
The full audit remains provisional; review before a dataset freeze. The corpus is
a source-supported IT subset, not an exhaustive collection of all IT papers.
