# ASO Atlas 2.0 preparation audit — 2026-11-14

The four Parquet files were downloaded from the `neurips-rebuttal` Hugging Face release linked by the source repository. Original release files and the supplied seven fold files remain byte-for-byte unchanged in `data/aso_atlas_2/release/`; SHA-256 hashes are in `cleaned/audit.json`. Source repository code inspected at `bb90c946013f183379da04678340e193088e5f99`. This preparation is a lossless row-preserving view, not a reimplementation of the upstream patent-extraction pipeline.

## Transformations

1. Read each release Parquet and assert its row count and `model_eligible` count against the upstream release manifest. Reject a mismatch.
2. Keep every source row and every original column in original order. Add `source_row_id` as `<endpoint>:<zero-based source row index>`; the ID points back to the immutable release file.
3. Add `exact_helm_sha256` only for non-null HELM. This is a hash of the exact original HELM string. It does not claim chemistry canonicalization or merge notation variants. Keep the original HELM text unchanged.
4. Add `has_resolved_helm`, `has_uncertain_chemistry_marker`, and `has_helm_frame`. The latter checks only a basic RNA1 HELM prefix/suffix; it is not a full parser. Confirm the release `model_eligible` flag matches nonempty HELM and reject a mismatch.
5. Add `has_patent_id` and `has_target_name` as presence flags. No gene names, cell names, patents, compounds or molecular chemistry are normalized or inferred.
6. For inhibition tables, add `finite_endpoint`, `valid_dose` (finite, nonnegative nM), `out_of_0_100_inhibition`, and `has_cell_line`. Preserve negative and above-100 inhibition exactly.
7. For neurotoxicity and hepatotoxicity, inspect the list-valued FOB or biomarker channels and flag whether a row has at least one finite measurement. Preserve all lists, including empty/missing values. Add dose validity using each table’s original units.
8. Add `analysis_eligible` only as a conjunction of resolved chemistry, patent, and finite endpoint; for inhibition tables also require a finite nonnegative dose. No row is deleted for being false. Toxicity dose is flagged but not required because the first toxicity analysis might use a different exposure contract.
9. Write derived Parquet with the same source columns and rows. Read it back and require exact equality for every source column, matching row count and unique source-row IDs. Report file hashes, duplicates by exact HELM, missing fields and endpoint fold counts.

## Counts

| Endpoint | Source/cleaned rows | Release model eligible | Analysis eligible | Unresolved HELM | Invalid/missing dose | Missing/nonfinite endpoint |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| in_vitro_inhibition | 174,459 / 174,459 | 173,286 | 143,646 | 1,173 | 30,347 | 0 |
| dose_response | 99,821 / 99,821 | 97,236 | 97,236 | 2,585 | 0 | 0 |
| hepatotoxicity | 4,341 / 4,341 | 4,212 | 4,137 | 129 | 0 | 99 |
| neurotoxicity | 4,900 / 4,900 | 4,896 | 4,892 | 4 | 192 | 4 |

Across endpoints, the audit found 165,782 unique exact HELM strings, with 15,095 appearing in at least two endpoint tables. This is exact-string overlap, not the source `Compound ID` linkage statistic.

Additional observations:
- in_vitro_inhibition: 161,434 exact HELM strings, 21,324 rows belonging to repeated exact HELMs, 44 rows without a target name. 8,024 inhibition values outside 0–100 were preserved; No unresolved chemistry marker or basic HELM-frame failure was found among resolved strings.
- dose_response: 16,375 exact HELM strings, 99,416 rows belonging to repeated exact HELMs, 85 rows without a target name. 3,610 inhibition values outside 0–100 were preserved; No unresolved chemistry marker or basic HELM-frame failure was found among resolved strings.
- hepatotoxicity: 1,881 exact HELM strings, 3,214 rows belonging to repeated exact HELMs, 3,226 rows without a target name. No unresolved chemistry marker or basic HELM-frame failure was found among resolved strings.
- neurotoxicity: 3,312 exact HELM strings, 3,137 rows belonging to repeated exact HELMs, 139 rows without a target name. No unresolved chemistry marker or basic HELM-frame failure was found among resolved strings.

The 30,347 in-vitro rows without a valid numeric dose remain in the cleaned file. They are not in this preparation’s `analysis_eligible` subset because a future dose-aware predictor needs a defined dose. This is a modelling choice, not proof that those measurements are invalid. The neurotoxicity source has 4,900 rows but 4,896 finite FOB readouts; four rows remain without a finite outcome. Hepatic rows can contain several biomarker measurements, so row counts and readout counts differ.

## Scope and remaining checks

This pass does not prove that every resolved HELM parses correctly under our chemistry code, that repeated results are consistent, or that the provided folds are leakage-free for our combined endpoints. Those are required before model training. Patent and compound identifiers are preserved for those checks. Source patent tables were not manually reconciled here, and no outcome values were clipped, averaged, fabricated or removed. The source card says the dataset was extracted from patents with an LLM pipeline and carries extraction, reporting and protocol limitations.

CC BY 4.0 attribution is in `data/aso_atlas_2/README.md` and the copied source license. This dataset import does not select a project code license or grant rights to practise patented inventions.

## Main integration verification — November 14, 2026

Imported the Atlas-only commit `f0b69b34367e1e6b578688231ec0b0236f7a2236`
onto main without conflicts. No parent RL implementation, model dependencies,
lockfile changes or training behavior were imported. The repository owner explicitly
authorized this additional dataset. Source release files and prepared Parquet files
retain the branch's original bytes.

- Verified all eight source/prepared Parquet hashes and all seven supplied fold
  hashes against the committed audit. The four endpoint tables total **283,521
  assay rows**; the upstream **295,007 readouts** use a different counting unit.
- Re-executed the cleaner into a temporary directory. All original and derived
  columns match the committed prepared tables, including row order, values and
  dtypes. Every audit statistic and source/fold hash matches. The four regenerated
  Parquet file hashes differ despite equal decoded tables, so byte-identical
  regenerated serialization is **not** claimed. The committed files were not
  overwritten. The replay environment was Python 3.13.9, pandas 2.3.3,
  PyArrow 21.0.0 and NumPy 2.3.5, separate from the modeling environment.
- Checked each supplied fold table: no duplicate rows or exact representation
  appearing in multiple folds within a table; the six OligoGym tables also have
  no patent assigned to multiple folds within an endpoint. These checks do not
  establish cross-endpoint isolation, near-sequence isolation or correct joins to
  the raw release. Fold numbers must not be aligned across endpoints by assumption.
- The copied upstream folds README lists OligoAI per-fold sizes whose sum does
  not equal the supplied table's 117,780 rows. Preserve that source document and
  treat its size summary as unresolved; use the actual fold file and audit counts.
- Validation: 134 existing core tests and 12 new Atlas integrity tests passed;
  repository Ruff checks and formatting passed (103 Python files). The new tests
  require only the core test runtime, not pandas/PyArrow.

The data are available for experimental planning, but no Atlas predictive result
or active-learning benefit has been established here. Before training, specify the
endpoint, dose/context inputs, chemistry representation, compound/patent isolation,
fold joins and whether acquisition spends one assay readout or an entire dose panel.
Keep the efficacy study separate from auxiliary toxicity endpoints. The existing
OligoGym catalog and acquisition pipeline remain unchanged.
