# Facet annotation prompt (draft v1.0)

Not executed; no API keys, model choice or budget are configured.

```text
Given the paper_id, title and abstract below, return a JSON object with exactly
paper_id, problem, task, method, dataset, contribution. Each facet is a list of
concept strings supported directly by the supplied text. Use [] when absent.
Do not guess datasets or contributions, and distinguish problem from task and
method from contribution according to FACET_GUIDELINE.md. Do not add relevance,
intent labels, user preferences or external knowledge. Preserve paper_id.

paper_id: <canonical ID>
title: <source title>
abstract: <source abstract>
```

An automated output is silver until human review. Metadata records prompt and
guideline versions, actual model/annotator, dataset kind and review status.
