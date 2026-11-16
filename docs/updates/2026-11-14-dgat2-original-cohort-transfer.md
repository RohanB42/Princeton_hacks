# Original DGAT2 cohort: recovered metadata and frozen-model transfer test

The original compatibility question is now executable for the twelve published
Atlas scaling classical models. **2,500 of the original 2,536 DGAT2 records were
scored by every checkpoint; 36 records were excluded for sequence exposure during
fitting or model selection.** No predictor or feature transform was fitted.
This is explicitly an evaluation-only representation/assay-transfer development
study. It does not establish predictive robustness or validate deployment.

The old ASOptimizer audit and its zero-coverage result remain unchanged. That audit
used fresh RF/Ridge models and a fitting-context gate. This experiment instead
loads existing published Atlas Ridge/XGBoost checkpoints, retains unknown-context
flags and measures their predictions. It is not a rerun of those old audit models
with their gate quietly removed.

## What was recovered

The pinned OligoGym records retain cell line and an undocumented-unit concentration
column, but omit other assay fields. The
[original ASOptimizer source CSV](https://github.com/Spidercores/ASOptimizer/blob/c7716f223fa432ea4fb99401e680db9dc37d3add/dataset/experiments_with_smiles.csv)
explicitly supplies `ASO_volume(nM)`, `Treatment_Period(hours)`, `Transfection`,
compound identifiers, sugar patterns and chemistry descriptions.

Original source revision: `c7716f223fa432ea4fb99401e680db9dc37d3add`.
CSV SHA-256: `61db5466ead5c9bf1e34241d89c3a02a3e6b5e03d0930e1062cdd14799a2fa43`.
The byte-verified CSV is kept outside Git. Released source bytes are unchanged.

All 2,536 records match on sequence, sugar pattern, HepG2 cell line and the checked
1000-fold numerical correspondence between the reduced concentration field and
the explicitly labelled original nM field. Multiple matching original rows are
retained only when recovered assay/chemistry annotations agree. No inhibition
value participates in this join. This establishes a row-level dose crosswalk; it
does not globally rename the reduced dataset's concentration unit without evidence.

| Reduced concentration | Original dose, nM | Treatment, hours | Original records | Scored after exposure exclusion |
| ---: | ---: | ---: | ---: | ---: |
| 0.12 | 120 | 24 | 674 | 674 |
| 2.5 | 2,500 | 16 | 921 | 903 |
| 10 | 10,000 | 16 | 886 | 868 |
| 20 | 20,000 | 16 | 55 | 55 |
| **Total** | | | **2,536** | **2,500** |

Every source row records `Lipofectin reagent`. That exact original string is
retained. It is an unknown category to the saved Atlas context encoders, whose
original `handle_unknown="ignore"` transform maps it to zero indicator values.
This behaviour is flagged, not hidden or called supported assay calibration.
HepG2 species is recovered from the unique HepG2/human mapping in the pinned Atlas
metadata. No assay field is filled using inhibition outcomes or an arbitrary mean.

## Important corrections to the proposed experiment

**DGAT2 is not unseen by these Atlas models.** Exact saved fitting memberships
contain between 7 and 70 DGAT2 source rows per source checkpoint. The older audit's
HBV/SOD1 fitting split cannot be attributed to these different frozen models.
Consequently this is a seen-target transfer diagnostic, not a clean combined
unseen-target/assay-shift test. Four assay strata remain one target, not four
independent genes.

**There is an unresolved chemistry annotation discrepancy.** All reduced HELMs
encode ordinary C, while original textual metadata says
`MOE/5-methylcytosines/deoxy`. A spot-check of the first original molecule's SMILES
also finds ordinary cytosine, despite that textual declaration. We therefore do
not replace C with 5meC or pretend the physical chemistry has been resolved.
The experiment uses the released encoded HELM, with the discrepancy attached.
Predictions are evidence about this recorded representation, not confirmation of
correctly specified experimental molecules.

The original cohort contains 127 17-mers, 2,187 20-mer 5-10-5 gapmers and 222
20-mers with other wing/core patterns. Every reduced record contains ordinary C.
The published supported-profile JSON Ridge and earlier pilot Ridge/HGB require a
fixed methylcytosine/20-mer profile; no record passes that strict encoded-chemistry
contract. Their assay profiles also differ. They are not forced into this study.
Huesken GP/RF/LoRA are siRNA models and are incompatible with the ASO endpoint.
The broader Atlas scaling models explicitly encode the original bases, lengths
and sugar/linkage patterns, making this declared stress test computationally
meaningful despite the unresolved source-quality limitation.

## Frozen protocol and leakage audit

Use **all** twelve published classical source checkpoints: Ridge and XGBoost at
budgets 2,869/4,781 and seeds 510/511/512. No winning checkpoint was chosen using
DGAT2 outcomes. Load actual research classes at `f197d79`, verify checkpoint hashes
and use matching isolated Python 3.11 packages.

Reconstructed the original 95,638-record source-training denominator using label-free
Atlas metadata, the pre-existing endpoint-availability flag, and the pinned source
preparation/allocation rules. Reconstructed every sampled source cohort and its
patent-group fitting/validation partition. Saved fitting ID lists match **exactly
for all twelve checkpoints**. Validation exposure is conservatively reconstructed
from the same pinned protocol; the original full validation receipt was not bundled
with the checkpoint inventory.

Exclude any DGAT2 record whose natural base sequence appears anywhere in the union
of the six sampled fitting/validation cohorts. This also prevents methylcytosine
annotation differences from evading sequence-overlap checks. Thirty-six records
are excluded; the same 2,500-record cohort is used for all checkpoint comparisons.
This is exact-sequence exclusion, not a claim of patent-family or homology isolation.

Source metadata and membership receipts are persisted before numeric endpoint
access. Existing frozen transforms produce predictions and nearest-fitting-feature
Euclidean distances; Ridge/XGBoost disagreement supplies a second warning.
Neither signal is a calibrated probability. Native feature distance includes both
chemistry and frozen context features; it is not normalized sequence Hamming distance.

Five query seeds, a maximum of 50 scored compounds per assay stratum, and k=5 are
fixed. Ordinary ranking, uniform selection and disagreement thresholds 10/20/40
are sealed before evaluation. Threshold 20 is the predeclared primary descriptive
contrast; it is not a threshold validated on separate development measurements.
Every primary arm produced five distinct shortlisted compounds. Assay replicates
are averaged within compound/context, rather than selected by representative ID.
Query costs include both heads; full prediction-table precomputation is separate.

An inference guard rejected calls to eight estimator/preprocessing fit interfaces
throughout the actual run. It recorded **zero fit attempts**. Direct-estimator,
wrapper and reversed-row inference probes have zero maximum difference. All frozen
stage and checkpoint hashes were reverified after evaluation.

## Results

RMSE is in original percentage inhibition points, weighted equally across the four
assay strata and then across compounds. Shortlist differences average the twenty
matched stratum/query-seed pairs per checkpoint pair. There are no target-level
confidence intervals and no claim that six checkpoint pairs are independent data.

| Source budget / seed | Ridge RMSE | XGBoost RMSE | Disagreement/error Spearman | Primary guardrail retention | Guarded minus ordinary shortlist efficacy |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2,869 / 510 | 24.24 | 28.50 | -0.044 | 98.40% | -2.55 |
| 4,781 / 510 | 24.05 | 28.20 | -0.038 | 98.96% | +3.40 |
| 2,869 / 511 | 22.74 | 26.00 | -0.038 | 99.72% | +0.30 |
| 4,781 / 511 | 26.83 | 28.33 | -0.115 | 86.84% | -2.44 |
| 2,869 / 512 | 26.17 | 30.10 | -0.240 | 86.04% | -4.40 |
| 4,781 / 512 | 24.40 | 24.71 | -0.072 | 98.80% | 0.00 |

Larger disagreement does not consistently identify larger Ridge error; its observed
pooled rank association is negative for every checkpoint pair. Native feature
nearest-distance/error associations are small or negative, approximately -0.109 to
+0.048. These descriptive signals do not establish effective error warnings.
Guarded shortlist changes range from -4.40 to +3.40 points and are inconsistent.
The test is now measurable, but its results do not justify deploying this safeguard.
Stratified metrics, risk/coverage curves, guardrail-retained errors, uniform baselines,
sensitivity arms and exact query/selection records are preserved in JSON.

## Files, repeat command and checks

Implementation: `src/oligo_engine/robustness/dgat2.py`.
CLI: `scripts/test_dgat2_transfer.py`.
Frozen declaration: `configs/robustness/dgat2-transfer-v1.json`.
Local outputs: `artifacts/robustness/dgat2-transfer-v3/{preflight,predictions,sealed-search,report}.json`
and `report.md`. Earlier local versions are preserved. Report-v3 adds native-feature
distance, selected-threshold coverage/error reporting and the dynamic no-fit guard;
the same cohort, checkpoint set and threshold declaration were retained.

```sh
PYTHONPATH=src \
DYLD_FALLBACK_LIBRARY_PATH=/private/tmp/oligo-train-venv/lib/python3.11/site-packages/xgboost/.dylibs \
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
.venv-dgat2-audit/bin/python scripts/test_dgat2_transfer.py \
  --original-source /private/tmp/aso-original-metadata-source.csv \
  --output artifacts/robustness/dgat2-transfer-new \
  --trust-published-checkpoints
```

The isolated runtime pins NumPy 1.26.4, scipy 1.15.3, sklearn 1.4.0, pandas 2.2.3,
XGBoost 2.1.4, PyArrow 21.0.0 and joblib 1.5.2. A read-only existing OpenMP library
supplies XGBoost's native dependency; shared environments and the core lockfile were
not modified. Core tests do not require this research environment or downloaded CSV.

Tests cover lossless metadata/unit recovery, ambiguous joins, insufficient-cohort
stopping before outcome access, final-label poisoning with unchanged seals,
replicate-aware evaluation, and dynamic fitting denial/restoration.

## What remains unresolved

This recovers an honest test of the original records for the named existing Atlas
classical predictors. It does not resolve the physical methylcytosine annotation,
validate a novel target, create untouched confirmation data, calibrate uncertainty,
or integrate an RL environment. Resolve chemistry against original compound/patent
provenance before claiming chemically validated transfer. Fresh target/assay groups
or prospective measurements are needed for confirmation.

Atlas LoRA has compatible broad input vocabulary in its pinned research code, but
neural inference still needs the separately verified RNA-FM backbone and matching
runtime. The retired ASO deployment GP/RF checkpoints are not identified in this
published inventory; the saved locally tested GP/RF are Huesken siRNA-specific.
Neither unavailable inference nor incompatible fixed-profile models are reported
as successful tests here.

Verification completed: **212 core tests**, the **three optional robustness science
tests**, lint, formatting and imports all pass. The five new DGAT2 boundary tests
are included in the core count. Actual twelve-checkpoint inference and the pinned
membership/metadata reconstruction ran separately in the isolated research runtime.

Changes remain uncommitted on `codex/robustness-correction-tests`; nothing was
pushed. No checkpoint, released dataset, deployment gate or core dependency file
was changed.
