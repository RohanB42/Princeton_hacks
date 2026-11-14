# Collection-wide data and pipelines

Implemented at the user's explicit request on 2026-11-14. All 12 released processed
datasets now live in `data/oligogym/`; no temporary checkout is needed for collection
validation or measured diagnostic replay. This authorization supersedes the old
dataset exclusion and synthetic-only implementation boundary. Gate 1 historical
reproduction remains unresolved, so these replays explicitly declare diagnostic
purpose. They do not claim baseline reproduction or scientific generalization.

## Exact source collection

Pinned revision: `97f5b9f58d9e445a8ecb0218037af7465c3708c0`. Preserve compressed CSVs,
registry, per-dataset JSON, upstream license and source attribution. The manifest
records all upstream resource paths and checksums. Loading rejects changed files,
unknown dataset keys, missing required columns, invalid labels and row-count mismatch.
Raw label columns and source values are never rewritten.
The [Huesken label review](huesken-label-review.md) records its 134 source labels
above 100 and the limits of the available assay explanation.
Git line-ending conversion and text-fixing pre-commit hooks are disabled for the
vendored directory so they cannot invalidate upstream checksums on another platform.

| Dataset key | Source name | Rows | Modality |
| --- | --- | ---: | --- |
| Huesken | Ichihara_2007_1 | 2,431 | siRNA |
| Ichihara | Ichihara_2007_2 | 419 | siRNA |
| Shmushkovich | Shmushkovich_2018_1 | 356 | siRNA |
| siRNAmod | Martinelli_2023_1 | 907 | siRNA |
| Sherwood | Knott_2014_1 | 291,551 | shRNA |
| OpenASO | McQuisten_2007_1 | 3,913 | ASO |
| ASOptimizer | Hwang_2024_1 | 32,602 | ASO |
| TLR7 | Alharbi_2020_1 | 192 | ASO |
| TLR8 | Alharbi_2020_2 | 192 | ASO |
| Cytotox LNA | Papargyri_2020_1 | 768 | ASO |
| Neurotox LNA | Hagedorn_2022_1 | 1,825 | ASO |
| Neurotox MOE | MOE_Neurotox_1 | 2,437 | ASO |

Total: **337,593 measured rows**. These are measurements, not necessarily unique
compounds. For example ASOptimizer contains 11,853 repeated-sequence rows; they can
represent differing assay context. Do not average or discard them silently.

## Commands

Use Python 3.11 or 3.12 and Poetry 2.1.4. The optional science group pins numpy
1.26.4, scipy 1.15.3 and sklearn 1.4.0. Core synthetic tests and
collection validation do not require this group; measured integration tests skip
when sklearn is absent. CI installs the science group and tests the real adapters.

```sh
make setup-science
make lint format-check import-check test
make data-check
make data-smoke
```

`data-check` verifies the entire collection and scans all rows. `data-smoke` runs
random and uncertainty acquisition separately on **128 label-blind sampled rows per
dataset**, seed 0, budgets 8/16/24, plus a reference using all eligible sampled
training rows. Its purpose is end-to-end engineering coverage of every dataset,
not a five-seed research result. Output is `artifacts/collection-smoke/`; choose a
fresh path if an output already exists:

```sh
poetry run python -m oligo_engine.collection --list-datasets
poetry run python -m oligo_engine.collection --validate --output artifacts/data-validation.json
poetry run python -m oligo_engine.collection \
  --config configs/all-datasets-smoke.toml --output artifacts/collection-check-new
poetry run python -m oligo_engine.collection \
  --config configs/measured-diagnostic.toml --output artifacts/measured-check-new
```

The last config uses full Huesken data and five seeds. Change `dataset` to any
catalog key, canonical source name, historical benchmark alias, or `all`. Omit
`max_rows` for full data. A declared cap selects rows by seeded reservoir sampling,
without looking at their label values; original row IDs remain stable across caps.
IDs encode source checksum, canonical dataset and original zero-based row index.
The full source size, selected size, cap, selection seed and complete selected split
IDs are persisted. Full-data Sherwood is substantially more expensive than the
smoke check; its full training reference also uses the entire eligible pool.

## Splits and budgets

- `sequence_group`: local diagnostic holdout by exact HELM identity. Repeated
  sequences remain together. This is **not** the published kmer/KMeans nucleobase
  split, and does not establish unfamiliar sequence-family generalization.
- `target`: local target-group holdout. It fails explicitly for missing targets,
  fewer than two distinct groups, or exact sequences crossing the resulting split.
  No fallback to another split and no silent removal of missing-target rows.
  TLR sets have only four target groups: executable does not mean statistically
  reliable. Cytotox LNA has one target group; siRNAmod and Shmushkovich
  have no known targets after their `undefined` placeholders are normalized.
- Target strings marking unknown/missing are represented as absent; the original
  value is preserved in observation context and source data. Targets are never
  fabricated or populated from labels. The `undefined` token is also treated as
  missing in the loader and validation report; this affects Shmushkovich (356
  rows) and siRNAmod (907 rows) without changing their source files.
- Each new run JSON saves `execution.data_audit`: actual train/test row counts,
  exact-HELM repeat groups and rows, missing-target rows, full per-target row
  counts, and exact-HELM/target overlap group counts. This is derived from the
  frozen split and label-free records; it does not expose held-out labels.
  The separate `artifacts/data-audit-20261114.json` profiles seeds 0–4 across
  both local split strategies without retraining or altering older run files.
  See [the data update handoff](data-update-handoff-2026-11-14.md) and its
  regeneration command for future work.
- Budgets are positive integer caps. Effective maximum is min(requested maximum,
  eligible training rows); effective initial count is min(requested initial,
  effective maximum). Effective settings and original requested config are logged.
  The final batch uses the exact remainder. Policies share the split, initial IDs,
  model settings and actual budgets for each seed.

`suite.json` records every dataset/run and its status. Unsupported splits and failures
give a reason and a nonzero CLI exit status; successful preceding work is retained.
There is no single combined score across datasets or silent exclusion of failures.

## Predictor and output boundaries

The common diagnostic predictor is a RandomForestRegressor over a stateless,
case-sensitive character hash of raw HELM. It accepts modified, duplex and
variable-length records with a fixed feature dimension. No test or unlabeled
vocabulary is fitted. This representation is not an official OligoGym featurizer or
a validated chemistry model. Tree prediction spread is named
`tree_prediction_sd_uncalibrated`, not a calibrated posterior. Candidate prediction
is chunked (default 2,048 rows), so tree-spread calculation does not allocate a
trees-by-entire-Sherwood-pool prediction matrix. Full-pool fitting still scales
with the chosen dataset and model size.

Only acquired labels enter fitting. Test scoring is deferred until the acquisition
campaign completes; the full eligible-pool reference is separately fitted afterward.
Assay context such as ASOptimizer cell line and concentration is preserved but is
not used by this diagnostic predictor. Labels retain upstream `y` units/scaling;
`y_raw` is retained on disk. Upstream curation may already have applied transforms
to the full source collection; these are not retroactively train-only transforms.
The pipeline fits no additional label transformation. It assumes no universal
endpoint direction and does not combine siRNA efficacy with ASO safety.

TLR key/assay-description conflicts remain explicit caveats in records and artifacts.
MOE patent provenance, chemistry compatibility and assay limitations still apply.
Successful execution is not evidence that any compound is safe or effective.

Schema 0.2 outputs are separate per dataset and policy: seed-level JSON, metrics CSV
and summary JSON. Mean/sample SD summaries group by exact measured-label count;
contributing seed counts are recorded, without interpolation. Full-pool references
are stored separately. A Pearson threshold is unset for diagnostics; there is no
inherited Huesken-specific success threshold. Existing output directories are preserved.

## Official baseline command

The existing source-audited upstream reproduction command now accepts every catalog
dataset via `--dataset`. It reads the vendored source bytes and verifies they match
the audited upstream checkout; official Dataset/split/featurizer/model APIs still
run in the separately installed pinned OligoGym environment. See
[upstream setup](upstream-verification.md). Example:

```sh
PYTHONPATH=src "$OLIGOAL_UP_ENV/bin/python" -m oligo_engine.reproduce \
  --checkout /tmp/oligoal-upstream --config configs/reproduce-rf.toml \
  --dataset Ichihara --output artifacts/ichihara-reference-check.json
```

An override derives the selected dataset's matching published configuration mean;
it never reuses Huesken's reference. No matching benchmark configuration yields a
null reference/tolerance outcome, not a fabricated number. Exact historical
reproduction remains false because original split/model seeds and environment
comparability are unresolved. The failed Huesken baseline attempts remain recorded.

## Local verification on November 14

- All 26 upstream resource/license files pass their manifest hashes and all 337,593
  measurement rows pass required-column, sequence and finite-label validation.
- All 24 sampled campaigns complete: 12 datasets × random/uncertainty, 128 selected
  rows each, seed 0, exact 8/16/24 label checkpoints, and separate full-eligible-pool
  references. These are diagnostic outcomes, not evidence of acquisition benefit.
- A fresh Poetry-managed Python 3.11.13 environment installed the lock with the
  science group; all 47 tests, Ruff lint/format and import checks pass. Remote CI
  is configured but has not been observed running.
- The generalized official command was exercised on Ichihara with the RF config:
  it selected Ichihara_2007_2 and its own five-row published reference, without
  inheriting Huesken's reference or declaring exact historical reproduction.
