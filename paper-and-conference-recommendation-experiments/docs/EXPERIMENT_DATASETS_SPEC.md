# Dataset specification — current version 2.0

The current specification is [EXPERIMENT_PROTOCOL.md](EXPERIMENT_PROTOCOL.md).

Order: A extraction → B retrieval → C implicit/search profile → D automatic session direction → E temporal.
C replaces former D; D replaces former C. D/E share C users and verified C manifest;
D uses C history/search with the same profile estimator. B remains independent of C after full A.

Schemas, quotas, labels, exposure/query links, per-case temporal visibility, oracle privilege,
metrics and simulator limitations are specified in the protocol and [DATA_CONTRACT](../DATA_CONTRACT.md).
Run commands are in [RUN_EXPERIMENTS](RUN_EXPERIMENTS.md).

B–E/evaluation manifests must be version 2.0. Legacy version 1.0 datasets are preserved and rejected.
Human gold is never generated automatically; no test fixture is substituted for real A facets.
