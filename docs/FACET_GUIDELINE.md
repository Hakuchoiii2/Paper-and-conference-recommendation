# Five-facet annotation guideline

Owner: Kien; global vocabulary approval: Khai. Guideline version 1.0 draft.

| Facet | Meaning | Distinguish from |
|---|---|---|
| problem | Limitation/research question addressed | task: what the system does |
| task | Operational objective, e.g. retrieval | method: how it does it |
| method | Algorithm/technique actually used | contribution: what is introduced |
| dataset | Named data/resource used in the study | domain or venue |
| contribution | Claimed new artifact/finding supported by text | generic method name |

Read only source-supported title/abstract. Use `[]` for missing evidence. Do not
infer datasets, model names or novelty from plausibility. Use lower-case canonical
concepts except recognized proper names and maintain a versioned alias map once
the pilot reveals actual variants. No speculative synonym dictionary is created.
The local Qwen pipeline stores exact supporting quotations in annotation metadata;
do not alter raw abstracts. Quote presence alone is not semantic validation.

CSFCube's rhetorical background/objective/method/result sentence labels cannot
be copied into these five concept-list fields. Native annotations remain in raw.

Pilot protocol: two people independently review a common subset; discuss
problem/task and method/contribution disagreements; Khai approves shared meanings.
Gold means human review completed. Silver means automatic annotation with declared
prompt/model/version. Split gold independently of prompt tuning and keep held-out
gold out of prompt examples. Gold target 400 is a workload goal, not delivered.
For the current run, the user selected Qwen3 locally on this machine. Model/
revision/runtime and seed are recorded; API keys are not required. Human review
is still required for gold and semantic quality.