# Censored IC50 adjudication and policy-comparison readiness

November 15, 2026. Requested experiment: determine whether recognizing bounded
potency outcomes changes discovery yield or the ranking of greedy, Bayesian, PPO
and random experimental-selection policies, reusing reported V3/Qwen experiments.

**No measured policy-ranking result is available from this task.** The completed
V3/Qwen potency experiments were not found in the accessible project records.
The mathematical adjudication layer and 19 invariant tests are implemented, and
a sealed nine-case synthetic check ran. No measured outcomes were read, no policy
was retrained or replayed, and no active molecular-design reward was changed.

## What the repository actually contains

The inspected working tree is `feature/molecular-design-v1` at `62f68d9`. Its
`molecular-policy-repair-v3` study searches frozen inhibition/risk predictors; it
does not purchase dose-response assays or optimize IC50.

Read-only inspection also covered the two existing Atlas worktrees, their local
artifact filenames, all local Git commit subjects, and these fetched references:

- `origin/codex/experimental-selection-rl` at `1b92731`: V1/V2 measured
  **single-dose inhibition** selection, with a hit defined as inhibition strictly
  greater than 80 percentage points. The report explicitly calls V3 a metadata-only
  linkage audit, with curve validation and implementation still gated. It reports
  5,126 candidate matched compounds across 44 target/patent groups; these counts
  do not certify fitted IC50 curves or independent assay replicates.
- Updated `origin/main` at `046ef5f`: additional experimental-selection runs and
  a published three-layer PPO checkpoint. The endpoint remains single-dose
  inhibition. Its portal handoff explicitly says IC50 needs checked curve fitting
  or researcher-supplied curve/method provenance. No Qwen or completed IC50-V3
  implementation appeared in those inspected sources.
- `/private/tmp/oligoal-atlas-lora-scaling-20261114` and
  `/private/tmp/oligoal-atlas-rnafm-20261114`: measured efficacy/predictor studies
  and upstream dose-response data assets, but no located saved V3/Qwen policy
  traces or potency adjudication protocol.

The user subsequently did not know an artifact location and authorized fetching
remote changes. The parent agent refreshed all branch refs; its fetchspec covers
all heads, and the remote advertised 11 heads with no additional Qwen/potency
branch. A deeper read-only search inspected **500 unique historical text blobs**
reachable through the fetched/local refs under `docs`, `src`, `scripts`, `configs`
and `tests`. The six IC50-containing historical blobs were documentation only;
the only curve-fitting code reference was the linkage audit's explicit
`curve_fit_and_independent_assay_verification: pending`. No completed potency
evaluation or Qwen implementation was located. A case-insensitive substring
search also checks names such as `Qwen2.5`, rather than requiring a bare `Qwen`
token. Sealed search receipts are saved alongside the synthetic artifact.

This is a bounded search result, not proof that the experiments do not exist
elsewhere or in an unpushed external checkout. No unrelated branch was merged or
cherry-picked into the working tree, and no dataset outcome values were opened
to reconstruct an undocumented experiment. No further location question is
needed to state the current result: the requested measured comparison cannot be
reused from the available sources.

The experimental-selection documents also reveal prior measured exposure of
historically reserved Atlas targets. The V1/V2 policy used DMPK/PLN for development
and DUX4/KCNQ2/PSD3/PTBP1/SMAD7 for final retrospective replay. These labels are
not globally untouched, and their existing roles still must not be moved into
fitting. This evidence was sent to the compatible-data workstream. The newer
published partition manifest is available read-only at
`origin/main:model_checkpoints/experimental-selection-ppo-3x32-v1/partition_manifest.json`.

## Scientific definition before outcome access

The primary success criterion must first be frozen as, for example,
`absolute IC50 <= tau nM`, using the **existing** assay-specific criterion and
justification. The implementation has no default scientific `tau`. Its toy CLI
uses 10 nM solely to exercise boundary cases, not to recommend a benchmark cutoff.

Absolute and relative IC50 are different estimands: an absolute 50% response uses
the assay reference range, whereas a relative half-maximal response uses the
compound's fitted response range. A weak partial response can have a finite
relative midpoint without reaching absolute 50% inhibition. The
[Assay Guidance Manual](https://www.ncbi.nlm.nih.gov/books/NBK91994/)
distinguishes these definitions and discusses curve-range/fit requirements.
The actual V3 assay contract must determine which endpoint is intended.

Given accepted assay/QC evidence and a fixed inclusive cutoff, classify records
as follows:

| Available evidence | Adjudication for success `IC50 <= tau` |
|---|---|
| Accepted point estimate `c` | Success if `c <= tau`; otherwise failure under this point-estimate rule |
| Accepted upper bound `IC50 < L` or `<= L`, with `L <= tau` | Threshold-qualified success; retain the bound, no invented exact potency |
| Upper bound with `L > tau` | Unresolved relative to the success threshold |
| Lower bound `IC50 > U`, with `U >= tau` | Threshold-qualified failure |
| Lower bound `IC50 >= U`, with `U == tau` | Unresolved: equality still satisfies the success criterion |
| Interval entirely at/below threshold | Threshold-qualified success |
| Interval entirely above threshold | Threshold-qualified failure |
| Interval spanning threshold | Unresolved |
| Failed or uncertain curve QC | Unresolved, even if an unconstrained fit prints a potent point estimate |
| Validated maximum absolute inhibition below 50% | Biological failure for the absolute-IC50 criterion; not a statement about a relative midpoint |
| Assay/instrument failure or missing result | Unavailable outcome, not established biological failure |

An IC50 below the lowest tested concentration is left-censored in concentration
space, represented by an upper bound. It is not the lowest tested concentration
divided by two. Likewise, absence of a crossing by the highest concentration does
not alone establish that a molecule can never reach 50%; it may provide a lower
bound or remain unresolved. A **validated maximum** response below 50% requires
appropriate plateau, controls and uncertainty evidence, not merely one low-effect
measurement at the maximum tested dose.

The supplied adjudicator accepts records whose evidence/QC has already been
established. It does **not** infer these conclusions from raw curves. That future
adapter must check response orientation, untreated/positive controls, viable-cell
confounding, dose identities, fit identifiability, monotonicity assumptions and
the prespecified treatment of replicate uncertainty. A printed out-of-range fit
is not by itself a certified bound. Raw records and rejected/QC-uncertain curves
must remain visible. Source-specific assay contexts cannot be pooled implicitly.

Unit conversion requires explicit molar concentration units. Mass concentration,
log-concentration and pIC50 are rejected rather than guessed. A pIC50 conversion
reverses inequality direction and requires its own explicit transformation.
Point estimates in the API are accepted estimates, not exact biological truth;
confidence intervals or censoring intervals should remain intervals when that is
what the assay actually supports.

## Experiment to run after locating the real artifacts

1. **Recover and seal the original evidence.** Hash source revisions, raw curves,
   endpoint definitions, original classification code, dose grids, acquisition
   ledgers, curve/QC outputs, assay costs, policy checkpoints, prompts and split
   manifests. Verify the claimed false-failure mechanism against actual records
   before calling it a bug. Freeze `tau`, adjudication and all exclusions using
   the existing contract or permitted development information, never final yields.
   Preserve the risk-final 304 and all unrelated protected partitions.

2. **First re-score fixed trajectories.** Apply original and revised adjudication
   to the *same purchased assays*, without changing any selected action. Count
   exact-estimate successes, threshold-qualified successes, threshold failures,
   genuine failures, unresolved curves and assay failures separately. This isolates
   evaluation-definition effects and requires no retraining. It cannot establish
   changes in which assays a policy purchases. Compare every originally recorded
   target/method/seed/budget cell, retaining negative and undefined results.

3. **Then replay adaptive policies separately.** Reuse the same targets, starting
   measurements, assay-cost schedule and seed-specific outcome/noise realization.
   Update a policy only from outcomes of permitted purchased assays. A random
   fixed-budget policy should preserve its trajectory; reward-dependent stopping
   or filtering must be audited. Greedy and Bayesian policies may change their
   choices when their observations or objective change. Existing Bayesian updates
   must explicitly accommodate interval/censored likelihoods; substituting a bound
   as an exact observation is not censoring-aware inference.

4. **Separate PPO evaluation from PPO learning.** Re-scoring an old PPO checkpoint
   measures its original behavior under a new evaluator. Replaying it with changed
   observations measures a different deployed behavior. Retraining under revised
   rewards is a third experiment, requiring identical permitted training targets,
   budgets and development-selection opportunities. It must not learn from final
   assessment outcomes. Qwen comparisons require the actual model/version, prompt,
   tool schema, decoding settings and saved responses. No API spend or invented
   replacement Qwen policy is part of this preparation.

5. **Report matched endpoint and decision changes.** Primary outcome: distinct
   threshold-qualified discoveries at the existing assay-cost budget, with initial
   assays charged and initial discoveries treated consistently with the original
   protocol. Show original-versus-revised yield and paired method differences,
   including target-level ranking reversals. Secondary outcomes: unresolved rate,
   exact/bound discovery composition, cost to first qualified hit, and assay-type
   purchases. Never-reached first hits remain censored at the budget, without a
   fictional later event. Separate targets from policy seeds; doses within a
   curve are not independent replicates. Already inspected final campaigns support
   retrospective diagnostic findings, not fresh confirmation.

Unknown outcomes stay in the denominator. For `s` qualified successes and `u`
unknown outcomes among `N` fixed discovery units, report the identification range
`[s/N, (s+u)/N]`, in addition to the observed qualified yield. These are not
confidence intervals. A policy-ranking conclusion can remain unresolved if such
ranges overlap. The `yield_bounds` helper requires the caller to supply **one
record per unique compound-assay discovery identity**. It rejects repeated
`record_id`s, but cannot detect that two different raw row IDs represent the same
compound/assay; canonical aggregation belongs in the source adapter. Repeated
assays still incur their declared costs without manufacturing new discoveries.

## Relation to existing censored-learning methods

The cited paper is verified: Karlova, Kabra, de Souza and Paige,
[COBALT: Censored Optimization and Bayesian Active Learning Techniques](https://proceedings.mlr.press/v337/karlova26a.html),
UAI 2026, PMLR 337:2713–2743. It develops censored-likelihood Bayesian learning and
an analytical information-acquisition formulation. It does not establish that
our absent V3 policy rankings change. The proposed contribution here would be a
measured benchmark consequence of an endpoint definition, not a claim to invent
censored optimization. No COBALT implementation or reproduction was attempted.

## Implemented and executed

- `scripts/censored_ic50_policy_experiment.py`: explicit point/bound/interval
  representation, units, endpoint/QC checks, unknown-preserving decisions and
  yield identification bounds. It imports no assay tables or policy weights.
- `tests/test_censored_ic50_policy_experiment.py`: 19 passing invariant cases for
  inequality direction/equality, unit conversion, endpoint mismatch, invalid
  numbers, unknown-versus-failure separation, interval validity and denominators.
- `artifacts/censored-ic50-policy-experiment-v1/{protocol,result}.json`: sealed
  synthetic-only check. Nine constructed records produce two qualified successes,
  three qualified failures and four unresolved/unavailable outcomes. This is a
  software check, not an ASO discovery result or policy-ranking demonstration.

```sh
PYTHONPATH=src .venv/bin/python scripts/censored_ic50_policy_experiment.py \
  --output artifacts/censored-ic50-policy-experiment-v1
.venv/bin/pytest -q tests/test_censored_ic50_policy_experiment.py
```

Use a new output directory when reproducing; sealed writes refuse overwrite.
Ruff lint and formatting passed for the owned script/tests. The scientific policy
comparison remains blocked on the actual V3/Qwen checkout and original potency
protocol, curve/adjudication records, policy traces/checkpoints and assay-cost/
label-access contracts. No real policy ranking or assay-choice change is claimed.
