# Adaptive dose-response measurement: executed final extension

November 15, 2026. **Completed retrospective diagnostic, not wet-lab validation.**
The experiment asks whether sequential concentration selection can classify an
ASO's apparent absolute IC₅₀ against **500 nM** with fewer recorded concentrations
than a strong fixed-order early-stopping protocol.

**The adaptive methods did not improve the primary comparison.** Across 240
assessment ASOs in five target/patent groups, fixed early stopping used **1.592
concentrations per ASO**, decision-aware selection **1.683**, and parameter
information gain **2.817**, versus **4.400** for full grids. Fixed early stopping
matched all 239 resolvable full-curve labels; decision-aware selection made three
binary errors. All three early methods classified the one reference-unresolved
panel, so none passed the complete prespecified reliability gate. A limited
TMPRSS6 subgroup and one-measurement coverage result are interesting diagnostics,
not a general adaptive-selection win.

## Frozen question, information boundary and splits

The protocol was sealed before this experiment read outcome columns:

`3e28ee934ef260cd336158d3d4de693a606ab00e8759994af51c5b6235fa2ba2`.

Selection used only ASO Atlas's pinned source metadata: human species, complete
assay/table context, distinct positive concentration grids of four to ten values,
and at least 12 complete panels in a common grid. For each prespecified target,
the largest eligible common-grid campaign was selected, with at most 48 compounds
chosen by a fixed identity hash. No panel was filtered using hidden response or
curve quality. Chemistry was parsed for compound identity; sequence alone did not
merge chemical structures.

| Role | Target | Patent/table | Cell/delivery/time | Doses, nM | Selected / eligible |
|---|---|---|---|---|---:|
| Development | F7 | US20150031747A1 / 28 | Hep3B, electroporation, 16 h | 50, 150, 440, 1,330, 4,000 | 45 / 45 |
| Development | STAT3 | US20160348104A1 / 15 | HUVEC, electroporation, 16 h | 39.1, 156.3, 625, 2,500 | 48 / 106 |
| Assessment | DNM2 | US20200392510A1 / 8 | A431, gymnosis, 48 h | 31.25, 125, 500, 2,000 | 48 / 379 |
| Assessment | PCSK9 | US20180311365A1 / 21 | HepG2, electroporation, 16 h | 46.875, 187.5, 750, 3,000 | 48 / 145 |
| Assessment | KRAS | US20180273577A1 / 40 | A431, gymnosis, 72 h | 148, 444, 1,333, 4,000 | 48 / 55 |
| Assessment | TMPRSS6 | US20240026364A1 / 5 | Hep3B, electroporation, 16 h | 150, 440, 1,330, 4,000, 12,000 | 48 / 52 |
| Assessment | AGT | US20190160090A1 / 18 | HepG2, electroporation, 16 h | 312.5, 625, 1,250, 2,500, 5,000 | 48 / 50 |

There are **93 development and 240 assessment ASOs**, with disjoint targets,
recorded patent IDs and source rows. Assessment sequences are excluded when they
match development sequences within two equal-length mismatches or a one-base shift.
These are conservative local linkage checks, not complete patent-family resolution.

All matching patents and exact/near sequences from the existing 304-record
risk-final allocation were excluded without reading those risk outcomes. Seven
historically reserved Atlas targets and NLRP3 were also excluded. The latter has an
unavailable historical within-target split. The five assessment campaigns are
held out from **this experiment's** operating-point selection, but broad prior
Atlas work and incomplete historical access manifests prevent a claim of globally
untouched final data. F7/STAT3 have explicit prior development exposure.

Every policy receives the same available dose grid. It purchases an existing
concentration, sees that recorded response, updates its state, and may stop with
potent, not potent or inconclusive. It cannot request an unrecorded concentration
or receive interpolated values as measurements. The model is reset independently
for each ASO; assessment feedback never updates another ASO's prior or any global
hyperparameter. Full-curve reference labels and unpurchased outcomes never enter
policy calls. At least one paid concentration is mandatory before a decision.

The runner caches complete paid-response orderings to evaluate several frozen
stopping prefixes efficiently. Decisions at a prefix use only that prefix; tests
poison later values and verify unchanged decisions and next actions. Physical
historical data access is **1,473 distinct source rows** across 333 panels, not the
smaller simulated prefix cost. Complete cached orderings are not described as
actual laboratory savings.

## Reference endpoint and curve adjudication

The reference is an operational **absolute 50% inhibition crossing**, not half of
an arbitrary fitted top/bottom response range. These definitions differ; see the
[Assay Guidance Manual](https://www.ncbi.nlm.nih.gov/sites/books/NBK91994/).

After policy trajectories are fixed, the evaluator applies the existing declared
curve rule to each full panel:

- Require at least four distinct positive finite doses.
- Preserve raw inhibition. Missing/nonfinite values or values outside [−20, 120]
  percentage points make the panel unresolved.
- Fit an increasing PAVA curve; adjustment exceeding 15 percentage points makes
  the panel unresolved. This tolerance is an operational choice, not a validated
  measurement-error estimate.
- A crossing inside the grid yields a log-dose interpolated estimate and bracket.
  Estimates at or below 500 nM are potent under this definition.
- If response already reaches 50% at the lowest dose, preserve an upper bound;
  credit potency only when that bound is at most 500 nM.
- If response remains below 50% at the highest dose, preserve a strict lower bound;
  infer nonpotency only when that bound is at least 500 nM.
- Other curves remain unresolved. A missing crossing does not prove biological
  inactivity, and an interpolated estimate is not a noise-free biological truth.

No raw controls, viability measurements, replicate uncertainty or extraction
accuracy were independently established. A prespecified strict-monotonicity
sensitivity requires zero isotonic adjustment. This sensitivity re-scores the
original decisions; it does not rerun or retune policies.

## Methods and stopping-point selection

**Full grid:** purchase every available concentration, then apply the common
reference adjudicator. Its perfect agreement on resolvable references is by
construction, not external biological accuracy.

**Fixed early stopping:** order concentrations by increasing log-distance from
500 nM. Stop on a monotonic witness: response at a dose ≤500 is at least 50%, or
response at a dose ≥500 is below 50%. If both nearest available doses bracketing
500 have been purchased and their responses bracket 50%, use their log-dose
interpolation. Observed monotonicity violations or out-of-range values prevent
these early certificates. This is deliberately stronger than just buying a
fixed low-to-high grid. Margins of 0, 5, 10 or 15 percentage points and a full-only
fallback were prespecified development candidates.

**Bayesian parameter information gain:** maintain a finite posterior over 1,500
monotone Hill curves and choose the available dose maximizing expected information
about all curve parameters.

**Decision-aware selection:** use the same posterior and likelihood, but choose
the concentration minimizing expected posterior binary classification risk
`E[min(P(potent|next result), P(not potent|next result))]`. This is a one-step
Bayesian decision policy, not PPO or a globally optimal planner.

The shared prior is uniform over bottom [−10, 0, 10], top [30, 60, 80, 100, 120],
Hill slope [0.5, 1, 2, 4], and 25 log₁₀ midpoint values from −1 to 5. The sub-50%
tops allow partial/noncrossing responses. Potency means predicted response at
500 nM ≥50%, so the Hill midpoint is not automatically called absolute IC₅₀.
Gaussian observation SD is fixed at 10 percentage points. These assumptions are
not fitted assay calibration or validated biological priors.

Prospective outcome integration uses exact Gaussian CDF mass in bins bounded by
−30, −20, …, 130, plus two infinite tails. This is a declared numerical
approximation to continuous expected information/risk. Actual paid observations
update the posterior using the continuous Gaussian likelihood. Bayesian stopping
requires posterior confidence 0.90, 0.95, 0.975, 0.99 or 0.995; full-only is also
available. Observed invalid values or PAVA adjustment >15 prevent early stopping.

All methods apply the **same full-paid-grid fallback** if they have not stopped:
once all doses are purchased, adjudication uses only those paid values. This
preserves comparable resolved-reference coverage but means final accuracy may
partly come from common adjudication rather than the Bayesian model.

Operating points are selected on development only, minimizing mean concentrations
subject to empirical FPR ≤5%, FNR ≤5%, at least 95% resolved-reference coverage,
and at most 5% definitive assertions on reference-unresolved panels when that
last denominator exists. Bayesian coverage must also be within two percentage
points of the selected fixed baseline. Undefined positive/negative-class error
rates prevent qualification. A missing unresolved-reference denominator is marked
**unassessed**, not zero. Ties favor stricter settings. If no candidate is feasible,
selection falls back to full-only. These are empirical development constraints, not
population error guarantees.

Selected settings were sealed **before assessment outcomes were accessed**:
fixed margin **0**, parameter information-gain confidence **0.95**, and decision-aware
confidence **0.90**. Development contained 75 potent, 18 nonpotent and zero
unresolved references. All selected policies had zero development binary errors;
unknown-reference assertion behavior could not be assessed there.

## Primary assessment result

Full assessment adjudication gives **209 interpolated, 15 upper-bound, 15
lower-bound and one unresolved panel**. At 500 nM this yields 108 potent and 131
nonpotent references. The remaining panel stays unresolved.

| Method | Total charged doses | Mean doses / ASO | False positives / 131 | False negatives / 108 | Resolved-reference coverage | Assertions on unresolved / 1 |
|---|---:|---:|---:|---:|---:|---:|
| Full grid | 1,056 | 4.400 | 0 | 0 | 100% | 0 |
| Fixed early stopping | 382 | 1.592 | 0 | 0 | 100% | 1 |
| Parameter information gain | 676 | 2.817 | 0 | 0 | 100% | 1 |
| Decision-aware | 404 | 1.683 | 1 | 2 | 100% | 1 |

Decision-aware FPR is **0.763%**, FNR **1.852%**, and resolved-reference accuracy
**98.745%**. Its false discovery rate is 0.935% and false omission rate 1.515%.
Fixed early stopping and parameter information gain have 100% agreement with the
239 resolvable labels. All early methods have zero inconclusive calls; full grid
has 1/240 inconclusive. A lower inconclusive rate is not automatically desirable.

Against the required strong fixed baseline, decision-aware selection uses
**5.76% more measurements**, and information gain **76.96% more**. Relative to
full grids, fixed early stopping saves 63.83%, decision-aware 61.74%, and
information gain 35.98%. The latter comparisons alone would overstate the benefit
of sophisticated selection because the simple baseline captures more savings.

**None of the early methods passes the entire frozen reliability gate:** each
makes a definitive call on the one reference-unresolved ASO. The 100% assertion
rate is **1/1**, not an estimate based on many failed curves or proof of biological
misclassification. The reference-unresolved DNM2 curve is monotone but has −25%
inhibition at its lowest concentration, outside the operational [−20,120] range.
At 500 nM its response is 8%; early stopping gives nonpotent without observing
the low-dose QC failure. The failure exposes a distinction between deciding a
threshold and certifying the validity of an entire curve.

## Target-level results and descriptive exceptions

All assessment groups have 48 ASOs. Errors below are FP/FN counts under the primary
reference, not independent study replications.

| Target | Full-grid mean | Fixed mean | Information-gain mean | Decision-aware mean | Decision-aware FP/FN |
|---|---:|---:|---:|---:|---:|
| DNM2 | 4.000 | 1.000 | 2.250 | 1.021 | 0 / 0 |
| PCSK9 | 4.000 | 1.646 | 2.667 | 1.833 | 1 / 0 |
| KRAS | 4.000 | 1.458 | 3.396 | 1.771 | 0 / 0 |
| TMPRSS6 | 5.000 | 2.417 | 1.729 | 1.208 | 0 / 0 |
| AGT | 5.000 | 1.438 | 4.042 | 2.583 | 0 / 2 |

DNM2 contains an exact 500 nM measurement, making one-dose classification
especially strong. The other four grids bracket but do not contain 500 nM.

TMPRSS6 is the one target where decision-aware selection halves the fixed
baseline's mean measurements, with no observed binary errors. Both methods begin
at **440 nM for all 48 ASOs**, so the advantage cannot be attributed to a better
initial dose. It is compatible with posterior-based early stopping below the
threshold, whereas a monotonic nonpotency certificate needs a dose at or above
500 nM. This descriptive observation does not isolate sequential dose adaptation
from the stopping rule or validate the prior/noise assumptions. Other targets
show that the same policy can lose to the fixed baseline.

The log-only first-dose diagnostic found fixed/decision first doses identical for
DNM2 (500), PCSK9 (750), KRAS (444) and TMPRSS6 (440), differing for AGT (625 vs
312.5). Information gain often starts higher. No new policy or subgroup tuning
was launched after observing these results.

## Accuracy, coverage and measurement trade-off

The prespecified budget analysis truncates the same frozen policy prefixes at
caps of one through five concentrations. Curves plot **actual mean charged
measurements**, not the maximum cap alone. They distinguish:

- Correct decisions divided by all reference-resolved panels, counting abstention
  as not yet correct.
- Decision coverage among reference-resolved panels.
- Selective accuracy among classified reference-resolved panels, undefined when
  no such decisions are made.

At one concentration, decision-aware selection covers **70.29%** of resolved
panels with **98.21% selective accuracy**; fixed early stopping covers **49.37%**
with **100% selective accuracy**. This is an early coverage/accuracy trade-off,
not the primary measurement-reduction result at the frozen reliability gate.
The one unresolved panel is reported separately rather than treated as correct.

![Accuracy and coverage versus charged concentrations](../artifacts/adaptive-dose-response-v1/accuracy-measurements.png)

Standalone [PNG](../artifacts/adaptive-dose-response-v1/accuracy-measurements.png)
and [PDF](../artifacts/adaptive-dose-response-v1/accuracy-measurements.pdf) are local
ignored artifacts. They are not distributed automatically with a Git clone.

## Prespecified strict-QC sensitivity

Requiring exactly monotone raw responses increases assessment reference-unresolved
panels from **one to 27**, leaving 105 potent and 108 nonpotent references.
The original fixed and information-gain decisions still make no binary errors on
that resolved subset; decision-aware still makes one FP and two FN. All early
methods make definitive assertions on all 27 newly defined unknowns.

This is **fixed-decision rescoring**. Even the original full-grid arm retains its
primary-QC decisions, so it asserts labels on 26 of those 27 strict-reference
unknowns. That is an adjudication-definition change, not a failure of a hypothetical
full-grid policy actually rerun with strict QC. No policy settings were changed
from assessment results.

## What is and is not established

This implements the proposed concentration-level environment and executes the
comparison on recorded ASO panels. It demonstrates why full-grid measurement alone
is an insufficient comparator: a threshold-nearest fixed early-stop protocol can
capture most observed efficiency gains. The Bayesian decision rule offers earlier
partial coverage and a context-specific TMPRSS6 improvement, but no overall gain
over that baseline under the frozen objective. Parameter information gain spends
measurements learning curve details that may not be needed for the binary decision.
The latter is an interpretation of the observed behavior, not a causal proof.

The study does not establish calibrated 5% population error, statistically
significant biological generalization, optimal concentration design, or laboratory
cost savings. Five assessment target/patent groups, historical selection and prior
exposure limit inference; no row-level significance test is used. The Bayesian
model's prior, Gaussian noise, discretization and partial-response assumptions can
be misspecified. Error-free agreement with a full-curve operational reference is
not agreement with independent biological truth.

Sequential execution can require additional plate rounds or delays. Fewer sampled
concentrations do not imply proportional savings once setup, controls, replicates,
plate utilization and batching are included. This is the final bounded major
extension requested; no post-result PPO, model-scale or policy-tuning sweep ran.

## Reproduction, artifacts and actual checks

Owned implementation:

- `experiments/adaptive_dose_response/core.py`: posterior, paid-only selection,
  stopping prefixes, references and abstention-aware metrics.
- `experiments/adaptive_dose_response/run.py`: metadata preparation, separate
  development/assessment stages, sealed selection and results.
- `experiments/adaptive_dose_response/audit.py`: post-completion independent
  provenance/metric checks and plots; its source hash is recorded separately.
- `tests/test_adaptive_dose_response.py`: 12 invariant tests.

Use a fresh output directory; sealed files refuse overwrite:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONPATH=src:. \
  /private/tmp/oligoal-atlas-rnafm-20261114/.venv-atlas/bin/python \
  -m experiments.adaptive_dose_response.run prepare \
  --output artifacts/adaptive-dose-response-new-run
# Run development, select, assessment and report in that order with the same args.
MPLCONFIGDIR=/private/tmp/adaptive-dose-mpl PYTHONPATH=src:. \
  /private/tmp/oligoal-atlas-rnafm-20261114/.venv-atlas/bin/python \
  -m experiments.adaptive_dose_response.audit \
  --output artifacts/adaptive-dose-response-new-run
.venv/bin/python -m pytest tests/test_adaptive_dose_response.py -q
```

Completed artifacts are under `artifacts/adaptive-dose-response-v1/`:
`protocol.json`, `config.json`, `development-traces.json`, `selection.json`,
`assessment-traces.json`, `report.json`, `completion-audit.json`,
`selected-prefix-ledger.json`, and standalone figures. Data, model and generated
run artifacts remain ignored and uncommitted. No dependency or shared scientific
contract was changed.

Actual checks: all 12 new invariant tests pass; owned Ruff lint/format checks pass;
root's integrated lint, format, import and **330-test** run passed. Protocol/code,
config, role, selection and result seals were verified independently; target,
patent, near-sequence and row separation and every unique-dose ordering were
checked. Metrics and selected-prefix charges recompute exactly. Plots were
rendered and visually inspected. The model has no full-reference field; poisoning
unpurchased values leaves the decision prefix unchanged. Core development and
assessment replay took approximately 0.57 and 1.32 seconds, respectively, excluding
metadata preparation and plotting. No neural fitting, external inference or
new wet-lab measurement occurred.
