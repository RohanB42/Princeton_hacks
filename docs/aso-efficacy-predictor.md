# ASO knockdown efficacy (ASOptimizer)

**Protocol frozen 2026-11-14 before any evaluation seed was run. Results are appended
below "Results" only after the runs finish; nothing above that line changes
afterwards.** Fifth endpoint, and the one the design surface was missing: potency.

## Why this was missing, and why that was a modality problem rather than a data gap

The project's efficacy work is Huesken — 2,431 siRNAs, knockdown potency, the
headline GP at r = 0.616 and the whole acquisition study. That is efficacy, and it is
the strongest result here. But Huesken is **siRNA**, and the design surface generates
**ASOs**. Applying an siRNA potency model to an ASO is the same class of error as
scoring a 2'-MOE candidate with an LNA toxicity model, which this project already
corrected once on Dr. Sun's advice. So the surface withheld potency entirely and said
so, rather than showing a number it could not justify.

Meanwhile `Hwang_2024_1` (ASOptimizer) has been vendored and validated since the data
audit: 32,602 ASO gapmers over 18 targets, percentage inhibition of target mRNA.
It was never trained on. This document trains it.

## Design

Two scopes, answering two different questions.

**Matched scope (the model the surface uses).** The 5,586 rows whose chemistry sits
inside the surface's `ps_moe_gapmer` space: 2'-MOE wings over a DNA core, PS or PO
backbone, unmodified bases, at most 20 monomers. Arms: one-hot GP and one-hot RF over
base+sugar+phosphate at 20 positions. **There is no published anchor for this scope**,
because the published runs used the whole heterogeneous dataset; these are new
numbers and are reported as such.

**Full scope (reproduction).** All 32,602 rows, RF only — a GP on 26,000 training
rows is not tractable — against the published mean of 0.4094 for exactly that
configuration (RF, one-hot base+sugar+phosphate, depth 20, 100 trees). The full
dataset mixes 2'-MOE, cEt, LNA, 2'-OMe and amino sugars with PS, PO and methoxypropyl
linkages, so the featurizer alphabets are widened **locally in the loader**, never in
the shared constants: growing `SUGAR_ALPHABET` would silently change the feature
width of every other endpoint's fitted model, which nearly happened once already.

- Split: official OligoGym `nucleobase` split per seed (8 k-mer clusters,
  `kmer_max=3`, `strand="RNA1"`, `test_size=0.2`).
- Seeds **400-429** (30) for the matched scope, **400-409** (10) for the full scope,
  fixed before any evaluation and disjoint from every earlier study.
- GP kernel frozen on Huesken (RBF, initial length scale 4); not re-selected here.

## Three properties of this data that constrain what can be claimed

1. **Five targets in the matched subset**, dominated by DGAT2 (2,536 of 5,586), then
   HBV (1,147), KLKB1 (1,089), SOD1 (773), MALAT1 (41). No target split is possible
   and none is claimed. A model fitted here has seen very few distinct mRNAs, so its
   predictions for a new gene are extrapolation — which is exactly what the surface's
   novelty percentile is for.
2. **2,638 of 5,586 rows repeat a sequence** that appears in another row, at a
   different dose, assay or source. Identical sequences share a k-mer vector and so
   land in the same cluster, meaning the nucleobase split keeps them on one side.
   The run **asserts zero shared sequences across the split on every seed** and fails
   rather than reporting a leaked number.
3. **Lengths are 16, 17, 18 and 20.** A 19-mer is encodable, since shorter sequences
   pad, but 19 is absent from training. The surface generates 19-mers to fit the
   neurotox model's 19-position featurizer, so efficacy predictions there are an
   interpolation in length. Stated on the page.

## Metrics (fixed in advance)

Pearson r (primary) and Spearman rho, plus RMSE, MAE, runtime and the uncertainty
diagnostics used on every other endpoint. Mean over seeds with **sample SD**.

## Expectations stated before running

- Absolute accuracy will be **low**. The published best on the full dataset is 0.479,
  the RF anchor 0.409, and that is with 18 targets; expect the matched subset to land
  near or below the RF anchor and well under the efficacy numbers on Huesken siRNA.
  A weak but honest potency signal is still worth more to the surface than no potency
  column, provided the page shows how weak it is.
- Chemistry encoding should matter, as it did on MOE neurotox and as the published
  gap (0.409 chem vs 0.275 base-only) independently suggests.

## Non-claims

No claim that any designed candidate knocks down its target. No target
generalization. No combined potency/safety score: the surface shows the endpoints
side by side in their own units and ranks on one at a time. Predicted inhibition is a
prediction, not a measurement, and this endpoint is patent-sourced.

## Results

Run 2026-11-14 under the protocol frozen in commit `aa98d9e` before any of these
seeds. Matched scope: 30 seeds (400-429), 4,041 train / 1,545 test, about 21 s per
seed for the GP. Full scope: 10 seeds (400-409), about 32 s per seed. No failures.
Dispersion is sample SD across seeds.

### Full scope: the published anchor reproduces

| Arm | Rows | Mean Pearson r +- SD | Published | Gap | Gap in combined SE |
| --- | ---: | ---: | ---: | ---: | ---: |
| RF, base+sugar+phosphate, depth 20, 100 trees | 32,602 | 0.4326 +- 0.0594 | 0.4094 | **+0.0232** | +0.67 |

Both parts of the revised Gate 1 criterion pass. That is the **fifth endpoint whose
published anchor reproduces**, after Huesken, MOE neurotox and both TLR assays, and
the discrepancies across all five now straddle zero: -0.027, -0.021, +0.007, +0.032,
+0.0015, +0.0081, +0.0232.

### Matched scope: the model the surface uses

| Arm | Mean Pearson r +- SD | Mean Spearman rho | Mean RMSE | Range over seeds |
| --- | ---: | ---: | ---: | ---: |
| **GP, base+sugar+phosphate** | **0.3170 +- 0.0614** | 0.3279 | 25.13 | 0.172 - 0.428 |
| RF, base+sugar+phosphate | 0.2886 +- 0.0686 | 0.2948 | 25.34 | - |

The GP wins the paired comparison (+0.0283, better in 22 of 30 seeds, p = 0.0006,
exploratory) and is the arm the surface uses. Label SD is 26.4 percentage points and
the model's RMSE is 25.1, so **this predictor explains about a tenth of the variance
in knockdown**. It is a weak signal and the surface says so next to every number.

**The pre-stated expectation held.** The protocol predicted the matched subset would
land near or below the full-dataset RF anchor and well under the siRNA efficacy
numbers. It did: 0.317 against 0.409 published / 0.433 measured on the full set, and
against 0.616 for the Huesken siRNA GP. Narrowing to one chemistry costs accuracy,
because 5,586 rows over five targets carry much less signal than 32,602 over
eighteen. We take that trade deliberately: a weaker number inside the chemistry we
design in is worth more than a stronger number obtained by scoring 2'-MOE candidates
with a model fitted largely on cEt and LNA molecules.

### Leakage check passed on every seed

2,638 of 5,586 rows repeat a sequence. **Zero sequences appeared on both sides of the
split on any of the 30 seeds**, because identical sequences share a k-mer vector and
therefore a cluster. The run asserts this and would have failed rather than report a
leaked number.

### Uncertainty, sixth endpoint

GP latent SD against distance to the nearest labelled row: rho **+0.674**. Against
absolute error: **-0.028**. The same finding as every other endpoint in this project,
now across four chemistries and both modalities: the GP's uncertainty is a novelty
signal, not an error signal. It is useful for telling a user that a candidate is
unlike anything measured, and it is not a confidence interval on being right.

### What can and cannot be said

Can: ASO knockdown is predictable from sequence and chemistry at r = 0.317 over 30
seeds within the PS/2'-MOE design space, and at r = 0.433 across the full
heterogeneous dataset, where the published anchor reproduces within noise.

Cannot: that any designed candidate knocks down its target; anything about genes
outside the five in the matched subset, which is most genes a user will type; any
combined potency/safety score. The endpoint is patent-sourced, so the labels record
what was worth patenting.
