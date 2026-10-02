# Verification — 2026-10-02

- Official raw files: 69 CSFCube files and 18 SciFact files, including original archives and documentation; checksums verified offline.
- Corpus gate: PASS, 4210 provisional IT-scoped canonical records, 4235 active source aliases, 9390 raw audit entries and 50 real sample papers.
- Standard-library test suite: PASS, 10 tests. Negative cases cover malformed IDs, empty text, invalid year type, unknown references, wrong facet keys, timezone absence, temporal overlap, unsafe archive paths and invalid review overrides.
- Reproducibility: PASS, two consecutive builds produce byte-identical content for all 10 corpus/fixture files including manifests and directory READMEs.
- Independent code review: primary-source persistence and override attribution issues reproduced, fixed and verified; narrow re-review found no remaining important issues.
- `--phase experiments`: intentionally exits 1; A–E datasets/full validators are not built. This is not a failed delivered corpus gate or a claim of full experiment validation.
- IT scope and five title conflicts remain provisional for Khai review; no gold/silver or model evaluation has occurred.
- No Git commit or remote push. Raw/full generated datasets, caches and secrets are excluded by .gitignore.
