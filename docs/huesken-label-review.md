# Huesken processed-label review

Reviewed 2026-11-14 against the pinned OligoGym release at
`97f5b9f58d9e445a8ecb0218037af7465c3708c0`.

The local `Ichihara_2007_1_processed.csv.gz` contains 2,431 rows. Its `y` and
`y_raw` columns are identical in every row. Labels range from 0 to 134.1;
134 rows (5.51%) across 16 targets exceed 100. All such values are finite. There are 30 nonempty
source target strings, no repeated exact HELM strings, and no blank source fields.
No rows or labels were edited or excluded.

The [OligoGym paper](https://openreview.net/pdf/80f56887e6015b4d26fcebcfaab39a478927751c.pdf)
(Appendix A.1.7) describes these labels as inhibition percentages derived from
the eYFP/eCFP dual-reporter ratio. It cites the
[original Huesken study](https://doi.org/10.1038/nbt1118) and the
[Ichihara study](https://doi.org/10.1093/nar/gkm699). The vendored metadata's
`source` field lists only the Ichihara DOI. The accessible source descriptions
establish the assay and provenance, but do not explain individual values above
100 or justify a 0–100 bound. We therefore retain the released values unchanged
and describe the range in every result using this endpoint.

The source reports 34 targeted mRNA species before curation, while the released
processed CSV has 30 distinct nonempty target strings. The reason for that
difference has not been verified from row-level primary material. Do not treat
the 30 strings as a verified reconstruction of all original assay targets.
