# Dataset registry template

Rows/target counts and loader keys below are verified in the pinned registry at
97f5b9f58d9e445a8ecb0218037af7465c3708c0. Benchmark aliases are mapped explicitly in
Analysis.ipynb. Reference Pearson values are upstream benchmark summaries, not local
reproduced scores or target-holdout results. All 12 datasets are now included locally;
see dataset-pipelines.md for all rows/keys and diagnostic coverage. Source bytes,
metadata and y/y_raw are preserved; the November 14 user request authorizes inclusion.

| Role | Display/source name | Rows | Targets | Reference r | Loader handle |
| --- | --- | ---: | ---: | ---: | --- |
| Primary siRNA efficacy | Huesken / Ichihara_2007_1; alias `siRNA1` | 2,431 | 30 | 0.631 | `Huesken` |
| Separate exploratory ASO immune | Alharbi_2020_1; assay description conflicts | 192 | 4 | 0.727 | `TLR7` |
| Separate exploratory ASO immune | Alharbi_2020_2; assay description conflicts | 192 | 4 | 0.699 | `TLR8` |
| Separate optional ASO toxicity | MOE_Neurotox_1; alias `acute_neurotox_moe_cleaned` | 2,437 | 13 | 0.703 | `Neurotox MOE` |
| Separate optional ASO efficacy | McQuisten_2007_1; alias `openASO` | 3,913 | 86 | 0.291 | `OpenASO` |

Huesken is unmodified siRNA; the primary task stays in that modality. Optional
PS/2'-MOE ASO design must not use siRNA potency as an unqualified surrogate. Immune
and MOE labels are separate experiments with different chemistry and missing endpoints.
At the pinned revision, `TLR7` points to `Alharbi_2020_1`, whose JSON describes a
TLR8 assay; `TLR8` points to `Alharbi_2020_2`, whose JSON describes TLR7. Correct
assay identities remain unresolved. The supplied plan describes MOE as a
patent-derived rounded three-hour
FOB outcome over seven ordinal categories, treated as regression; assay species,
route/dose and endpoint direction need source verification. Patent selection effects
are a caveat. ASO toxicity diagnostic replays have run independently; they do not
establish therapeutic safety. Sherwood is included in the full diagnostic matrix
but remains outside the primary siRNA efficacy study.

The upstream Apache-2.0 license and unchanged released datasets are included under
`data/oligogym/` with provenance and attribution. Source-specific dataset rights
and any future weight usage require review; no project license is selected here.
Source PDFs and model weights are not included.
