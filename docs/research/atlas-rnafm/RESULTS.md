# Atlas RNA-FM development results

Status: completed bounded development report. This is a new ASO study, not a reinterpretation
of the earlier Huesken siRNA findings. Reserved targets are not evaluated.

## Cohort and split audit

The strict cohort has 133,304 first-source measurements after positive-dose,
complete assay metadata and DNA/MOE/cEt gapmer restrictions. Modified bases,
linkages and terminal tokens are retained. Malformed concatenated nucleotides and
unsupported bases raise instead of being skipped. Cohort counts are 97 source
identifier targets and 157 patents; aliases have not been externally resolved.

Ten human campaigns have >=400 distinct compounds and adequate grouped pool/test
sizes. Metadata-only hash allocation selects F7, STAT3, NLRP3 for development; PTBP1,
KCNQ2, DMPK, PLN, SMAD7, PSD3, DUX4 remain reserved. All allocated targets and their
patents/exact compound and base equivalents are removed from source fitting.
Source pool: 95,638 train, 14,614 validation. Campaign test groups connect same-length
sequences within two substitutions or an exact one-base shift. This is not a full
homology/patent-family audit or proven gene-alias normalization.

## Native Atlas anchor

The exact Atlas adapter at bb90c946013f183379da04678340e193088e5f99 aggregates max
inhibition per HELM+dose across assay contexts. It produces 135,891 rows and 468
features. All rows join the supplied 134,388-unique-HELM fold map; no native/supplied
fold disagreement. Five native-default Ridge fits completed in 135.6 seconds:

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

Frozen config: `configs/atlas/development-v1.json`. Source budgets 50/200/1,000,
seeds 510–512; all fitting and grouped internal model-selection labels count.
Three development target campaigns, budgets 50/100/200 and seeds 610–612. Transfer
models share 1,000 source labels / seed 510. Target-only Ridge has no historical data, so it is
an additional comparator rather than the only classical control.

| Source model | Mean source-validation RMSE at 1,000 labels |
|---|---:|
| Context-only Ridge |28.7191|
| Chemistry/context Ridge |28.9004|
| Chemistry/context XGBoost |29.2069|

| Target adaptation | Mean campaign RMSE at 200 new-target labels |
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
Ridge matches the source-calibrated models at 200 labels. This challenges a simple
assumption that more historical data necessarily delivers useful target transfer.
All target scoring followed completion of fitting decisions.

## Real ASO FM engineering profile

Single-strand token features plus aligned base/sugar/linkage/terminal embeddings,
source-fitted assay context and a shared fusion head are implemented. No artificial
second strand is used. Cached and batched frozen token features agree exactly on
eight real source examples. Source-prior restoration reproduces predictions exactly.
A 50-label, one-epoch source-only profile changed LoRA adapters and preserved the
base weights: 171,269 trainable parameters, 1.40 seconds fit, peak process RSS 2.01 GB.
MPS was unavailable in the actual runtime; CPU, one thread was used. This is feasibility,
not an efficacy result. Thirteen focused tests passed before the matched study.

## Matched source and target adaptation

Both FM arms used the same 1,000 historical measurements (source seed 510), then
50/100/200 measured target labels (seeds 610–612) on F7, STAT3 and NLRP3.
Three source and target epochs were fixed in advance. Every target budget restores
the source checkpoint first; no larger-budget adapter selects smaller-budget data.
The full run took 357.1 seconds with peak RSS 1.93 GB on one CPU thread. All 56
fits preserved base weights; all 28 LoRA fits changed adapters. This verifies
execution, not calibration or a predictive benefit.

| Predictor | Mean RMSE at 200 target labels | RMSE-AULC difference vs source Ridge + offset |
|---|---:|---:|
| Source Ridge + offset | 19.6342 | 0 |
| Target-only Ridge | 19.6256 | +0.1630 |
| Frozen RNA-FM + chemistry | 22.3546 | +2.0393 |
| LoRA RNA-FM + chemistry | 21.9861 | +2.3694 |

AULC is trapezoidal RMSE area from 50 to 200 labels divided by 150, so its units
are inhibition percentage points; negative differences favor the candidate. Means
first average seeds within target, then targets. LoRA improves over frozen at the
200-label endpoint but is 0.3300 points worse across the full budget curve.
Both FM arms lose to source Ridge + offset on all three target-level AULCs.
Zero-shot mean RMSE was 32.4432 (frozen) and 34.0826 (LoRA), showing a substantial
need for new-target calibration in this setting. No inferential claim follows
from three development targets and one historical source initialization.

## Acquisition geometry with a fixed predictor

This follow-up was specified before acquisition outcomes. All six arms use the
same source Ridge + acquired-only residual Ridge predictor and 1,000 historical
labels. Only selection changes. Classical features use a fixed random projection
to 64 dimensions; frozen and LoRA geometries use their source-trained 64-dimensional
chemistry-fusion representations. Source-only scaling and L2 normalization are
identical; no evaluation sequences enter the geometry. The encoders remain fixed
during this experiment, so it does not test target-adapted geometry. The uncertainty
policy ranks linear feature-posterior variances with identity regularization/noise;
it is not a calibrated efficacy uncertainty estimate from Ridge or RNA-FM. MaxDet
updates that covariance after each provisional batch selection, accounting for
redundancy. Diversity greedily maximizes distance from already labeled/selected
points. None of these policies can read unrevealed efficacy labels.

There are three targets x three seeds (710–712) x six policies = 54 campaigns,
initial 50 labels, batches of 25, final 200. The 378 checkpoints have matched
initial IDs, unique reveals and deferred evaluation. Selection/fitting took
23.0 seconds after geometry extraction (this timing excludes model loading and
geometry extraction). Full-pool references are fitted separately for reporting.

| Acquisition policy | F7 ΔRMSE-AULC vs random | STAT3 | NLRP3 | Target macro mean |
|---|---:|---:|---:|---:|
| Classical diversity | -0.3050 | -0.1666 | +0.2164 | -0.0850 |
| Classical uncertainty | -0.8233 | +0.1727 | -0.0261 | -0.2256 |
| Classical MaxDet | -0.3982 | +0.2354 | -0.2566 | -0.1398 |
| Frozen-fusion MaxDet | +0.1939 | +0.1299 | -0.1447 | +0.0597 |
| LoRA-fusion MaxDet | -0.2555 | +0.1544 | +0.0050 | -0.0321 |

The primary geometry contrast, LoRA MaxDet minus classical MaxDet, is **+0.1078**
RMSE-AULC points (worse). Classical uncertainty has the lowest macro AULC in this
small exploratory comparison but is worse than random on STAT3. Seeds are paired
replications, not additional independent genes. We have not established a robust
acquisition improvement or pretrained-representation advantage.

The predeclared threshold was RMSE <= 1.10 times each full-pool reference. Every
policy/seed already meets it at the shared initial 50 labels, before selection can
differ. Threshold crossing is therefore uninformative for differential savings.
We report the actual crossings and do not substitute an outcome-selected threshold.
Full-pool reference RMSE is 19.9401 (F7), 19.5584 (STAT3), 18.6324 (NLRP3); it is a
measured comparator, not a guaranteed optimal score or theoretical ceiling.

## Gate decision and limits

Do not advance this exact recipe to expensive confirmation or target-adaptive FM
acquisition on the present results. The engineering gate passed; the predictive/
geometry advantage gate did not. Seven reserved target campaigns remain unscored.
The broader hypothesis is still open: this run uses only 1,000 source labels,
three fixed epochs, one source initialization and three development targets.
It is not full-Atlas fine-tuning, optimized model selection, independent biological
validation, or evidence that RNA foundation models cannot help ASOs.

A future proposal can test a clearly specified source-scale or optimization
hypothesis using training-internal development, resolve target aliases/patent
families, and define a new confirmation design before reading reserved labels.
That would be a new experiment, not a reclassification of these negative findings.

Generated plots are `artifacts/atlas-rnafm/summary-v1/transfer-curves.png` and
`acquisition-curves.png`; bands show within-target seed SD, not target-level
confidence intervals. Reports preserve Pearson, Spearman, RMSE and MAE even though
this development contrast was RMSE-AULC. No weights or generated reports are committed.
