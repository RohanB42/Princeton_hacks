# Oligo design engine

**Repository scaffold only. No models, active-learning experiments, design agent, or application have been implemented or evaluated.**

This HackPrinceton project asks whether active acquisition can approach a comparable full-training-data model using fewer measured oligonucleotide labels. This is a hypothesis, not a result or a claim of equivalence to Creyon's proprietary system.

Planned parts: a multi-endpoint predictor, a measured-label active-learning comparison, an optional PS/2'-MOE design agent, and an optional single-page results surface. The required future result is a reproducible learning curve. Newly proposed molecules would be unvalidated hypotheses.

Install Python 3.11 and Poetry 2.1.4, then run `make setup`, `make lint`, `make format-check`, `make import-check`, and `make test`. These check repository health only. No datasets, weights, paid services, or GPU are needed.

`src/oligo_engine/` holds future module boundaries; `configs/` has non-executable examples; `docs/` defines the scientific and interface contract. `app/`, `scripts/`, `data/`, `artifacts/`, and `notebooks/` explain future use. See [architecture](docs/architecture.md), [interfaces](docs/interfaces.md), and [workflow](docs/team-workflow.md).

Next, verify a pinned OligoGym revision and dataset identities, reproduce Gate 1 on the nucleobase split, then compare active and random acquisition against a full-data reference on fixed test sets across at least five seeds. Reference Pearson values in [data and provenance](docs/data-and-provenance.md) come from source documents; they are not results from this repository. Huesken siRNA potency may not transfer to PS/2'-MOE ASOs; immune and MOE endpoints are separate experiments. See [evaluation](docs/evaluation-protocol.md) and [open questions](docs/open-questions.md).
