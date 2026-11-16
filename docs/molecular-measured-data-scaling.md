# Measured-data scaling for molecular-design reward heads

Investigation date: November 15, 2026. This is an evidence audit and proposed
experiment, not a training execution or a newly qualified scientific profile.
The companion policy investigation concerns surrogate-scored experience; the
measurements discussed here train the predictors that supply that experience.
Read with [the final specification](FINAL_MOLECULAR_DESIGN_RL_SPEC.md) and
[the policy repair report](molecular-policy-repair.md).

## Decision

More measured data could improve the reward predictors, but available evidence
does not justify assuming that all remaining Atlas rows are usable or that a
larger RNA-FM/LoRA model will help. Audit the existing larger classical checkpoints
first, then construct a new, fixed-split learning curve. Evaluate predictors on
common measured endpoints before freezing a new scorer for policy experiments.

The immediate blocker is applicability: **the full inhibition release contains
zero parsable exact matches to the three active molecular-design chemistry
patterns at the currently configured efficacy assay context.** More rows from
other contexts do not automatically repair this. A conditioned transfer experiment
or a separately qualified profile is required; neither can silently widen the
present support claim.

## What “2% of the data” means

The active export is
`artifacts/molecular-design-v1/atlas-ridge-reference.json`, sourced from
`model_checkpoints/atlas-scaling-v1/source-2869-510-ridge/model.pkl`.

| Quantity | Count | Interpretation |
|---|---:|---|
| Active efficacy fitting rows | 2,284 | Labels used to fit the exported Ridge |
| Active efficacy selection rows | 585 | Additional labels used for selection |
| Active efficacy development allocation | 2,869 | Fit plus selection |
| Historical allowable source-training pool | 95,638 | After the earlier study's exclusions |
| Broad analysis-eligible inhibition rows | 143,646 | Before current profile/partition restrictions |
| Released inhibition rows | 174,459 | Raw release, including ineligible rows |

The 2,869-row development allocation is 2.00% of 143,646. Fitting alone uses 1.59%.
The same allocation was called **3%** in the original source study because its
denominator was 95,638. None of these fractions describes how much experience PPO
has used. Also, measured rows are not necessarily distinct molecules, independent
patents, independent targets, or compatible assay measurements.

The cleaned audit reports 173,286 upstream-model-eligible inhibition rows and
161,434 distinct exact HELMs across the raw inhibition release. Separate endpoints
include 99,821 dose-response rows (97,236 analysis eligible), 4,900 neurotoxicity
rows (4,892 eligible), and 4,341 hepatic rows (4,137 eligible). These endpoints
cannot be pooled as interchangeable efficacy labels. Preserve source bytes,
source-row IDs, assay units, missingness and endpoint provenance.

The earlier metadata plan found 134 target identifiers and 203 patents among
broadly eligible inhibition rows, but only 98 provisional assay-consistent
campaigns with at least 100 distinct HELMs, covering 28 target identifiers and
39 patents. Those counts are upper bounds, not 134 verified independent genes.
No binding coordinates or transcript sequences are supplied by that table.

## Exact applicability audit performed here

The metadata-only check projected `HELM Annotation`, `USPTO ID`, `target_RNA`,
`model_eligible`, and the five efficacy context columns from
`data/aso_atlas_2/release/in_vitro_inhibition.parquet`. It never requested
`Inhibition_pct` or another outcome column.

The context is human HepG2, Electroporation, 4,500 nM, 24 hours, as frozen in
`artifacts/molecular-design-v1/rebuilt-multi-endpoint-config.json`. There are
5,870 raw rows at that context, of which 5,854 carry upstream `model_eligible`.
Of these rows, 23 fail the current HELM parser. Each parsable molecule was compared
by full parsed identity to the profile-generated HELM for its natural sequence
and terminal. This comparison preserves sugar, linkage and base-modification
identity; a shared sugar/linkage shape alone is insufficient.

There were **zero matches** to `atlas-stress-18-0`, `atlas-stress-20-0`, or
`atlas-stress-20-1`. Repeating with the existing metadata auditor's
`[m5C]` → `[5meC]` alias normalization gave the same zero matches and 23 parser
rejections. Rejected rows cannot be counted as evidence without a separate parser
and chemical-identity audit. Thus there are no newly established exact-compatible
rows at this context in the full release, and no exact-compatible intersections
with the active fit or validation IDs.

The existing `efficacy-coverage.json` already reported 32 context-matching active
validation rows but no matching profile patterns. The full-release count above
extends that metadata result; it does not measure predictive accuracy.

The export's scope explicitly says inference parity does not establish scientific
support. Its source hash is
`447426f598d3c1763efd0eb31786cc8fdf3daecbcf594c5aa96a95964c367e7f`;
the active JSON hash is
`b5c38afdbc64b2dc6b2f29b291627ee1367180ee48fd7783b0d590d5597d2b46`.

## Larger models and prior negative results already exist

The manifest contains larger source-only Ridge checkpoints. Their model and
source-receipt SHA-256 values were verified against the local files during this
investigation, without loading any held-out outcomes:

| Total source allocation | Seed | Fit rows | Selection rows | Recorded Ridge fit/selection seconds |
|---|---:|---:|---:|---:|
| 2,869 | 510 | 2,284 | 585 | 0.079 |
| 2,869 | 511 | 2,300 | 569 | 0.092 |
| 2,869 | 512 | 2,295 | 574 | 0.097 |
| 4,781 | 510 | 3,813 | 968 | 0.141 |
| 4,781 | 511 | 3,834 | 947 | 0.132 |
| 4,781 | 512 | 3,847 | 934 | 0.117 |

Paths follow `model_checkpoints/atlas-scaling-v1/source-{allocation}-{seed}-ridge/model.pkl`.
The compatible loader commit is `f197d79`; the manifest explicitly does not assert
that this is the original training revision. Recover invocation provenance as
well as loader compatibility before reproducing training.

The completed study lives in the local worktree
`/private/tmp/oligoal-atlas-lora-scaling-20261114`, in
`docs/research/atlas-rnafm/SCALING-RESULTS.md`, `SCALING-METHODS.md`, and
`SCALING-STATUS.md`. Its ignored receipts are under
`artifacts/atlas-rnafm/scaling-v1/`. This completed result supersedes the older
136-record intermediate snapshot referenced by some main-branch documents.

It completed 240 fit/calibration records and 216 deferred target-scoring records
in 6,037.1 seconds (100.6 minutes). Under validation-selected source training and
fixed three-epoch adaptation using 200 measured labels per target:

| Predictor | 2,869 source allocation RMSE | 4,781 source allocation RMSE |
|---|---:|---:|
| Frozen RNA-FM plus chemistry | 20.893 | 21.208 |
| LoRA RNA-FM plus chemistry | 22.391 | 22.340 |
| Source Ridge plus target offset | 19.883 | 19.656 |
| Source XGBoost plus target offset | 20.403 | 20.292 |

Units are inhibition percentage points. These are descriptive macro means over
F7, STAT3 and NLRP3, with three paired seeds per target. Target-only Ridge and
XGBoost using the same 200 target labels reached 19.626 and 19.366 respectively.
No general FM advantage or consistent FM scaling improvement was demonstrated.
These adapted models are not valid substitutes for a zero-target-label reward
head without declaring and matching the 200-label adaptation budget.

The historical scaling contrast has two important limitations:

- Patent validation changed with sample size. The total cohorts were nested,
  but the fitting cohorts were not: 440, 340 and 336 smaller-cohort fit rows
  disappear from the corresponding larger fit sets. Target/patent composition
  changes therefore accompany the nominal sample-size change.
- Three of six source partitions share one normalized compound across fitting
  and validation, with 0–4 natural-sequence identity overlaps. The active
  2,869/510 split has one compound and two natural-sequence intersections;
  4,781/510 has one and four. Patent disjointness alone did not prevent leakage.

The receipt audit records these limitations rather than repairing the historical
experiment after seeing outcomes. Preserve those artifacts as diagnostics;
**do not reuse their validation membership as a clean scaling benchmark**.
No current molecular-policy evaluation target should be newly described as
untouched after the current development study. Earlier reports' seven reserved
Atlas campaigns need a current cross-study exposure audit before that designation
can be relied upon.

## Risk scaling has a different ceiling

`artifacts/molecular-design-v1/risk-qualification/protocol.json` contains 1,720
exact-compatible metadata rows across 14 connected groups: 166 for the 18-mer
pattern, and 720/834 for the two 20-mer patterns. The fixed context is mouse
C57BL/6, 700 micrograms, 3 hours, ICV, Behavioral tolerability score.

The partition allocates 874 fit, 259 development, 283 calibration and 304 final
rows. One absent fit outcome was excluded by the recorded input amendment, giving
873 actual fitting labels. The groups are allocated 5/2/2/5 respectively.
The 304 final outcomes remain sealed. Calibration and development rows are not
spare training data: folding them in would remove their independent roles.

Existing development aggregates select Ridge over the 256-tree random forest
(RMSE 1.286 versus 1.378; constant baseline 2.417). The screen retains 231/259
development rows. Its upper cutoff 2.8469757503787645 is the median fitted-training
prediction, a relative acute-FOB screen, not a clinical safety threshold.
Two development groups provide limited evidence for generalization.

Therefore, “use the remaining 98%” does not apply to this exact risk cohort.
Expanding across strain, dose, route, time, assay or chemistry requires a distinct
conditioned model and validation design. Hepatic measurements, siRNA efficacy,
and unlike neurotoxicity endpoints cannot silently supply missing acute-FOB labels.

## Proposed experiment, in execution order

1. **Audit and reuse before retraining.** Verify larger Ridge/XGBoost manifests,
   receipts, preprocessing and fit/selection ID provenance. Export label-free
   inference bundles using the existing trusted-owner loader and fixed synthetic
   chemistry/context anchors; test batch, singleton and reversed-batch parity.
   Score only permitted common development rows after overlap audit. Larger
   artifact existence establishes neither improved performance nor applicability.

2. **Declare the applicability question.** For the present exact profile/context,
   direct-support scaling is blocked by zero established compatible rows. A new
   experiment may evaluate cross-context/chemistry transfer, explicitly marking
   extrapolation, or select a supported alternative profile using metadata first.
   Keep the diagnostic profile and original results intact. Do not relax the risk
   screen to manufacture feasible candidates or choose assay scope by efficacy.

3. **Seal one metadata-first partition graph.** Record original row IDs, normalized
   compound identity, natural-sequence identity, declared near-sequence connections,
   patent identity/family where verified, target aliases where verified, and assay
   campaign. Construct connections on the full allowed metadata before sampling,
   so unselected rows cannot hide transitive leakage. For zero-shot target transfer,
   hold whole target groups out and exclude connected source patents/molecules;
   for within-target ranking, hold molecular/patent components out within target.
   State which estimand each split serves. Do not force balanced splits by breaking
   connected components. Record unresolved aliases, families and homology limits.

4. **Freeze selection, calibration and final memberships across all tiers.** Final
   labels are excluded at the Parquet read boundary; the current risk final304
   remain sealed. Use fixed development rows for model choice and separate
   calibration rows for any residual/uncertainty calibration. Current policy test
   targets become development evidence; final confirmation requires a separately
   exposure-audited cohort. A label-budget ledger counts fitting, selection and
   calibration labels separately and in total. Feature fitting, normalization,
   vocabulary and representation fitting use fitting rows only.

5. **Build nested training tiers within the permitted fit partition.** Suggested
   first curve: approximately 2,000, 4,000, 8,000 and 16,000 fitting rows, followed
   by 32,000 and the remaining permitted pool only if justified. Use stable group
   order, three paired sampling seeds and append-only group additions; report actual
   counts when components prevent exact budgets. These are candidate tiers, not
   promises of compatible data. Include a newly fitted small-data reference under
   the new split; retain the current 2,284-fit artifact as a historical comparator,
   not the uncontaminated lower point of the new curve. Report distinct molecules,
   groups, targets and contexts as well as rows. Distinguish more rows within fixed
   contexts from expanding the context/target distribution.

6. **Start with matched classical controls.** Fit mean/context-only baselines,
   chemistry-plus-context Ridge and XGBoost on identical tier memberships, with a
   locked small hyperparameter grid and equal selection-label access. Context-only
   strength diagnoses whether gains come from assay composition rather than
   molecular discrimination. Test frozen RNA-FM and LoRA only as a separate,
   matched-label/compute arm after this baseline curve. Preserve chemistry alignment,
   frozen-backbone checks, checkpoint restoration and training-only transforms.
   Source-only deployment and target-adapted deployment remain separate protocols;
   adaptation comparisons need matched source-plus-offset and target-only controls.

7. **Evaluate raw measured endpoints, then freeze the winner.** Select one primary
   metric and contrast before reading evaluation outcomes: target/campaign-macro
   RMSE or a specified within-campaign ranking metric, depending on the declared
   estimand. Treat the other as a prespecified secondary metric/guard; also report
   MAE, Pearson/Spearman, fixed top-k measured enrichment, coverage and undefined
   metrics. Prespecify shortlist sizes and calibration coverage targets before
   permitted labels are read. Estimate paired uncertainty across independent
   target/patent components, not by counting repeated seeds as new targets. Small
   group counts require descriptive conclusions. Report applicability failures and
   selection multiplicity. A winner needs better fixed-evaluator ranking with
   nondegrading raw-error/calibration criteria defined in advance; source training
   loss or a changed reward percentile is insufficient.

8. **Only then compare policies under a frozen scorer.** Pin the chosen weights,
   training IDs, assay scope, calibration, reference ECDF and screen thresholds in
   a new bundle. Run pretraining/PPO/random/greedy with equal scoring budgets and
   fixed evaluation campaigns. Compare old/new pipelines under a common independent
   evaluator; returns computed with different reward models or ECDFs are not a
   predictor-improvement metric. Predictions remain predictions. Better surrogate
   optimization is not measured efficacy, clinical safety, or biological validation.

## Compute budget and stopping gates

The historical Ridge receipts above measure only their fitting/selection stage;
subsecond figures exclude extraction, metadata audit, loading and broader study
overhead. They support doing the classical curve first, not a promise that the
entire audit runs in milliseconds. The native five-fold Atlas Ridge anchor took
135.6 seconds in the earlier study, under a different aggregation/feature protocol.

The completed neural scaling study used one CPU thread and recorded 1.64 GiB peak
RSS for its resumed matrix. The first LoRA source profile ran six epochs in
383.70 seconds on 2,284 fitting rows; the 3,813-row profile ran eight epochs in
916.85 seconds. That is roughly 64–115 seconds per epoch in those conditions.
Linear extrapolation alone suggests about five minutes per epoch at 10,000 fitting
rows and ten minutes at 20,000; this is a planning approximation, not a benchmark.
At 20 epochs and three seeds, even one LoRA arm could consume several hours before
other model arms. Reprofile actual extraction/cache/memory and one epoch before
approving larger neural matrices. Use one heavy process at a time on the local
16-GB machine; keep external backbone provenance and redistribution restrictions.

Stop before fitting if scope coverage is absent, overlap cannot be repaired, or
too few independent components remain. Stop a run on provenance/hash mismatch,
held-out-label access, invalid endpoint units, failed inference parity or unbounded
resource growth. Prespecify wall-time caps and early stopping; report partial
completion. Do not launch the next costly tier when consecutive development tiers
show no improvement beyond their group-level uncertainty or deteriorating
calibration, unless a new hypothesis is explicitly declared first. Do not inspect
final outcomes to decide whether to continue.

Promotion requires a clean split audit, reproducible artifacts, adequate exact or
explicitly transfer-qualified scope, predefined predictive/calibration criteria,
and the final specification's independent evaluation evidence. Those requirements
are not currently met for the active efficacy profile. More data is a plausible
route to a more reliable surrogate; the existing measurements do not establish
that it will make PPO outperform an equally pretrained policy or validate generated
molecules biologically.

## Work completed for this investigation

Read the required project/scientific contracts, current exports and qualification
metadata, checkpoint manifest, historical completed scaling report and aggregate
receipt audit. Verified six Ridge model hashes and their six receipt hashes.
Ran two metadata-only full-release context/chemistry checks (with/without the
documented methylcytosine alias normalization). No fitting, endpoint-label loading,
screen changes, raw-data edits or costly experiments were performed. This change
adds documentation only; no software test result is claimed.
