# Data audit handoff, 2026-11-14

This note records the user-approved data handling updates after the detailed
audit. It is for agents working on future training or evaluation. The pinned
OligoGym source revision remains
`97f5b9f58d9e445a8ecb0218037af7465c3708c0`. All 12 released source files,
metadata, license, and manifest remain byte-for-byte unchanged. No measurement
was averaged, clipped, discarded, or reassigned.

## Implemented behavior

- `Catalog` now treats the exact, case-insensitive `undefined` target token as
  missing, alongside its existing missing tokens. The original string remains
  in `Observation.context["source_target_id"]` and in the source CSV. This changes
  the reported missing-target count to 356/356 for Shmushkovich and 907/907 for
  siRNAmod; both have zero *known* targets. Target holdout remains unsupported.
- `audit_split` counts rows, distinct exact HELMs, repeated-HELM groups, rows in
  repeated groups, extra repeated rows, known targets, missing targets, and full
  per-target row counts in each train/test partition. It also counts exact-HELM
  and known-target overlaps across partitions. It reads only label-free records.
- Every **new** `RunArtifact` saves this result under
  `execution.data_audit`, alongside the existing saved split IDs. Old run files
  were not rewritten; they should be identified by code revision if compared.
- `scripts/audit_data_splits.py` creates a standalone report without training.
  Regenerate it with:

  ```sh
  PYTHONPATH=src python scripts/audit_data_splits.py \
    --output artifacts/data-audit-new.json
  ```

  The default is seeds 0–4, 20% of groups held out, separately for the local
  `sequence_group` and `target` strategies. Use a new output path; the script
  refuses to overwrite an existing report. Generated JSON stays in `artifacts/`
  and is ignored by Git under the repository's artifact policy.

## Measured results

The full collection has 337,593 rows. With `undefined` correctly counted, 55,593
rows have no known target: 54,317 Sherwood, 907 siRNAmod, 356 Shmushkovich, 12
Ichihara, and 1 OpenASO. There are 63,740 additional rows beyond each dataset's
distinct exact-HELM count. These are retained measurements, not a proposed
deduplication list.

The standalone report contains 120 attempted dataset/strategy/seed splits:
60 supported exact-HELM splits, 30 supported target splits, and 30 unsupported
target splits. Supported splits have zero exact-HELM overlap. Supported target
splits also have zero known-target overlap. Target holdout is unsupported for
Ichihara, Shmushkovich, OpenASO, Cytotox LNA, siRNAmod, and Sherwood under the
current no-exclusion rule. This audit does not test near-duplicate sequence
families or establish benchmark comparability.

For Huesken seed 0, the local exact-HELM holdout has 1,944 train and 487 test
rows, with all 30 source target strings on both sides. The separate target
holdout has 1,989 train and 442 test rows, with 24 and 6 target groups and no
target overlap. These are local diagnostic splits; the published OligoGym
nucleobase split is a different protocol.

## Huesken label finding

The pinned Huesken processed file has 2,431 rows, identical `y` and `y_raw`
columns, a 0–134.1 label range, and 134 values above 100 across 16 targets
(5.51% of rows). See [the label review](huesken-label-review.md) for sources.
OligoGym describes the endpoint as inhibition percentage derived from an
eYFP/eCFP dual-reporter ratio. Available source descriptions do not establish
why individual values exceed 100 or warrant a 0–100 cap. Keep the source
values unchanged and disclose the range. The original study describes 34
target mRNA species; this processed file has 30 distinct nonempty target
strings. Their row-level mapping remains unverified.

## Remaining evaluation limits

- Exact-HELM grouping prevents one form of train/test leakage. It does not
  ensure unfamiliar sequence-family or new-target generalization.
- Repeated measurements can have different labels. Keep every row and all
  rows of one exact HELM in one partition. Report row-level scores and repeated
  molecule counts; do not silently average or drop measurements.
- ASOptimizer records cell line and concentration, but the current diagnostic
  HELM-hash forest ignores them. Any context-aware model needs a separate,
  matched-split evaluation.
- TLR7/TLR8 registry keys and assay descriptions conflict. Do not assert an
  endpoint identity until source mapping is resolved.
- Gate 1 historical benchmark reproduction remains open. The local split
  audits do not alter that status or establish a published-score comparison.

The subsequent [simple Huesken baseline study](simple-huesken-baselines-2026-11-14.md)
uses these audited local splits with training-only Ridge selection. Its results
remain diagnostic and separate from historical benchmark reproduction.

## Verification performed

The direct full-collection validator passed all 337,593 rows and manifest
hashes. A Huesken smoke run and a four-run OpenASO integration replay saved
the new audit fields. The regeneration script reproduced the full 120-split
report exactly. All 60 repository tests passed with the available Python
3.13 environment; the training smoke used the available Python 3.11 environment.
Ruff lint/format, Python compilation, and `git diff --check` also passed.
