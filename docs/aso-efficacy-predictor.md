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

To be appended after the run.
