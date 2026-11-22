# EXP-B initial ground truth

The generator reads only `data_preparation/output/validated_silver.jsonl`.
This input currently has no title or abstract. The build uses the available facet
text for selection and review. It counts nonempty facets independently of audit
status. Some facet text may still be pending review.

Run from the repository root with the local MiniLM model already cached.

```powershell
python .\ground_truth_generation\run_ground_truth.py
```

Ranking shares `output/query_split.json` and should use the entire eligible corpus
in `output/ranking_input.jsonl`. The 100 candidates per query are the initial
judgment pool. Query pair review excludes concept similarities of 0.75 and above
from simultaneous selection.

For the existing Pooling loader, `output/pooling_input.jsonl` provides the
same 5,000 pairs in its one-row-per-query format.

Open `output/human_review_template.xlsx` and enter grades in the light blue
columns. A blank grade is pending. Use `human_review/review_guidelines.md` for
the rubric. The worksheet hides retrieval groups and scores during judgment.

After grading, use a Python environment with openpyxl to import the workbook.
Use one consolidated workbook so the saved judgments reflect all completed rows.

```powershell
python .\ground_truth_generation\import_judgments.py .\ground_truth_generation\output\human_review_template.xlsx
```

The import writes `human_judgments.jsonl`, `initial_human_qrels.jsonl` and
`review_progress.json`. Final qrels belong to the later Pooling phase.
