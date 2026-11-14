# Atlas RNA-FM development results

Status: partial development report. This is a new ASO study, not a reinterpretation
of the earlier Huesken siRNA findings. Reserved targets are not evaluated.

## Cohort and split audit

The strict cohort has133304 first-source measurements after positive-dose,
complete assay metadata and DNA/MOE/cEt gapmer restrictions. Modified bases,
linkages and terminal tokens are retained. Malformed concatenated nucleotides and
unsupported bases raise instead of being skipped. Cohort counts are97 source
identifier targets and157 patents; aliases have not been externally resolved.

Ten human campaigns have >=400 distinct compounds and adequate grouped pool/test
sizes. Metadata-only hash allocation selects F7,STAT3,NLRP3 for development; PTBP1,
KCNQ2,DMPK,PLN,SMAD7,PSD3,DUX4 remain reserved. All allocated targets and their
patents/exact compound and base equivalents are removed from source fitting.
Source pool:95638 train,14614 validation. Campaign test groups connect same-length
sequences within two substitutions or an exact one-base shift. This is not a full
homology/patent-family audit or proven gene-alias normalization.

## Native Atlas anchor

The exact Atlas adapter atbb90c946013f183379da04678340e193088e5f99 aggregates max
inhibition per HELM+dose across assay contexts. It produces135891 rows and468
features. All rows join the supplied134388-unique-HELM fold map; no native/supplied
fold disagreement. Five native-default Ridge fits completed in135.6seconds:

| Metric | Mean over five folds |
|---|---:|
| Pearson r |0.190162|
| Spearman |0.205397|
| RMSE |30.160151|

The source benchmark JSON is absent from the pinned checkout, so numerical paper
reproduction remains unverified. The native reproduction path includes global
featurizer fitting and max-over-context aggregation. Neither is adopted in the
separate budget-controlled campaign study. Native Ridge emitted ill-conditioning
warnings; no model or seed was changed to improve its score.

## Classical development

Frozen config: `configs/atlas/development-v1.json`. Source budgets50/200/1000,
seeds510–512; all fitting and grouped internal model-selection labels count.
Three development target campaigns, budgets50/100/200 and seeds610–612. Transfer
models share source1000/seed510. Target-only Ridge has no historical data, so it is
an additional comparator rather than the only classical control.

| Source model | Mean source-validation RMSE at1000 labels |
|---|---:|
| Context-only Ridge |28.7191|
| Chemistry/context Ridge |28.9004|
| Chemistry/context XGBoost |29.2069|

| Target adaptation | Mean campaign RMSE at200 new-target labels |
|---|---:|
| Context-only source + target offset |20.0261|
| Source Ridge + target offset |19.6342|
| Source Ridge + residual Ridge |19.7118|
| Source XGBoost + target offset |19.7382|
| Source XGBoost + residual Ridge |19.8107|
| Target-only Ridge |19.6256|

Means above average three seeds within each of three campaigns, then targets.
These are descriptive development outcomes, not confidence intervals or a claim
of transfer improvement. The source-context control is competitive, and target-only
Ridge matches the source-calibrated models at200 labels. This challenges a simple
assumption that more historical data necessarily delivers useful target transfer.
All target scoring followed completion of fitting decisions.

## Real ASO FM engineering profile

Single-strand token features plus aligned base/sugar/linkage/terminal embeddings,
source-fitted assay context and a shared fusion head are implemented. No artificial
second strand is used. Cached and batched frozen token features agree exactly on
eight real source examples. Source-prior restoration reproduces predictions exactly.
A50-label, one-epoch source-only profile changed LoRA adapters and preserved the
base weights:171269 trainable parameters,1.40seconds fit, peak process RSS2.01GB.
MPS was unavailable in the actual runtime; CPU1thread was used. This is feasibility,
not an efficacy result. Thirteen focused tests passed before the matched study.

The frozen-chemistry versus LoRA-chemistry matrix is running. Both use1000 identical
source measurements, matched three-epoch source and target fitting, and exactly
paired target IDs. No result is claimed until completion and integrity audit.
