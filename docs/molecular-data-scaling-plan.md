# Integrated molecular-data scaling investigation

November 15, 2026. The user requested two parallel investigations: measured data
for scientific predictors, and experience for policy pretraining/PPO. Both findings
are integrated here. This document proposes the next experiments; it does not
authorize a scientific claim, report new training, or replace the existing frozen
protocols.

- [Measured predictor data audit and protocol](molecular-measured-data-scaling.md)
- [Policy experience audit and protocol](molecular-policy-data-scaling.md)
- [Completed policy repair and optimizer results](molecular-policy-repair.md)

## What the audits change

The “2%” statement applies to the active efficacy predictor's 2,869-row development
allocation divided by 143,646 broadly analysis-eligible inhibition rows. It includes
585 selection rows; the actual 2,284 fitting rows are 1.59%. The earlier source
study called the same allocation 3% of its narrower 95,638-row allowable pool.
These denominators do not describe PPO or policy pretraining.

| Component | Verified current exposure | Main constraint |
| --- | --- | --- |
| Efficacy predictor | 2,284 measured fit rows + 585 selection rows | No established exact chemistry/context support for the active profile in the release |
| Acute-risk predictor | 873 fit, 259 development, 283 calibration, 304 sealed final rows | Other species, routes, doses and endpoints are not interchangeable spare data |
| Policy pretraining | 576 distinct compounds per seed | 36.0% of the current 1,602-compound training universe |
| Pretraining plus PPO | 1,036–1,206 distinct compounds per policy | 64.7–75.3% of that universe; broad coverage requires new campaigns |
| Five-policy union | 1,575 distinct compounds | 98.3% collectively, but individual policies do not share their data |

The efficacy audit checked metadata across the full release at human HepG2,
Electroporation, 4,500 nM and 24 hours: 5,870 rows, 23 parser rejections, and zero
verified exact matches to the three active chemistry patterns among parsable rows.
It did not read inhibition outcomes. Structural overlap alone cannot establish
support for the methylated molecular profile. The current system remains an
explicit extrapolation diagnostic.

Larger source Ridge checkpoints already exist: roughly 3,800 fitting rows instead
of 2,284. An earlier completed 3%-versus-5% study also exists and did not establish
a consistent RNA-FM/LoRA advantage. Its variable validation membership and small
compound overlaps make it unsuitable as a clean data-size curve. Audit/reuse its
artifacts and negative evidence before spending compute on a repeat.

## Two separate experimental axes

For predictor scaling, measure whether more compatible measured training data
improves error/ranking on fixed, independent observations. Do not judge a new
predictor by the rewards it assigns its own selected molecules. Refitting changes
the oracle, and changing its reference ECDF can change the numeric utility scale.

For policy scaling, freeze the scientific oracle, screens, normalization and legal
chemistry profile. Vary the policy's training examples or experience while keeping
deployment query budgets and evaluation campaigns fixed. This isolates search
improvement under a specified oracle; it does not validate biological efficacy.

A supported-profile data curve and a current-profile extrapolation stress test are
different experiments. Choose and label that scope using metadata before model
outcomes. Zero verified exact-context coverage blocks a direct-support claim; it
does not become solved by fitting all remaining rows.

## Recommended execution sequence

1. **Recover and audit existing predictor artifacts.** Check the larger classical
   checkpoints, exact fitting/selection membership, feature construction, owner
   runtime and export parity. Preserve the historical overlap findings. Establish
   the compatible cohort and exposure graph before allowing additional labels into
   fitting. The previously reserved 304 final risk outcomes remain sealed.

2. **Build one clean predictor scaling protocol.** Connect compound/sequence and
   declared target/patent groups before splitting; freeze development, calibration
   and final memberships across all tiers. Use nested additions within the fitting
   partition. Candidate tiers are approximately 2k/4k/8k/16k fitting rows, then 32k
   only if support, independent groups and development evidence justify it. Actual
   compatible counts may prevent these tiers. Start with classical and context-only
   controls; treat neural scaling as a separate matched-data/compute comparison.

3. **Run a cheap policy-pretraining breadth experiment under the frozen diagnostic
   oracle.** Proposed equal-cost arms are 6 genes × 3 windows × 32 queries,
   12 × 3 × 16, and 24 × 3 × 8: all 576 requests per policy. Keep 48-nt windows
   and 89 legal designs
   per campaign initially. Additional genes are contingent on metadata and exposure
   audits; do not reuse inspected evaluation genes as new confirmation targets.

4. **Then test pretraining depth on a common broad panel.** For 24 genes × 3 windows,
   compare 576, 2,304 and 6,408 queries (8, 32 and 89 per campaign). Fix optimizer-update
   checkpoints for the primary compute-matched comparison: increasing data while
   retaining 20 epochs would also increase gradient updates. Report any separately
   declared convergence-controlled analysis distinctly. Retain both the staged
   pretrained policy and the full-budget pretrained ranking control.

5. **Test PPO's increment only after the pretraining comparison.** On the same
   broad gene panel, cross two pretraining sizes (576/2,304) with PPO prefixes
   0/4,096/16,384 decisions, using five fresh development seeds. The prefixes come
   from common per-seed initializations/trajectories, not independent cherry-picked
   policies. This needs ten longest-prefix PPO runs, not thirty independent fits.
   Include a control that spends comparable additional query/learning resources on
   pretraining without PPO. Do not escalate to 64k merely because more steps are
   available; require a development benefit over both no-PPO controls first.

6. **Confirm a frozen choice on fresh target groups.** All currently inspected
   targets and prior study targets belong in the exposure ledger. Reserve fresh
   groups before adding training genes. One primary pipeline-versus-conventional
   contrast and a separate PPO-attribution contrast answer different questions;
   specify multiplicity handling. Power planning uses a meaningful effect threshold
   and target-level variability, not a desired p-value or an arbitrary seed count.
   The canonical minimum of five final target groups is a floor, not a guarantee
   of adequate precision. Label computational and measured claims separately.

The predictor and policy audits can proceed independently. Policy scaling under
the existing scorer remains a diagnostic while predictor applicability is open.
After a new predictor is qualified and frozen, a subsequent versioned integration
study can test whether better prediction translates into better discovery under
a common independent evaluator. Do not change oracle and policy data together
and attribute the resulting difference to either one alone.

## Costs, infrastructure and reporting

Count measured fitting, model-selection and calibration labels separately. Count
surrogate pretraining requests, PPO exploration requests, checkpoint validation,
deployment requests and actual endpoint calls separately. Repeated trajectories
and reused deterministic predictions are not new measured evidence. Report unique
compounds, genes, regions and exposure counts alongside nominal sample counts.

The current full-policy runs took roughly 16 minutes per seed under their logged
conditions. Ten runs at that scale would be roughly 2.6 worker-hours before
additional validation or broader-input costs, not a guaranteed elapsed time on a
shared machine. More/longer transcripts can increase global observation capacity;
larger chemistry catalogs also increase observation/buffer cost. Profile the new
metadata-only schemas and a bounded development run before committing a large
matrix. Keep the existing profile/decoder/checkpoints replayable.

Needed implementation includes immutable nested sample manifests, exact per-prefix
checkpoints, training-only replay/label ledgers, explicit optimizer-update budgets
for pretraining, and target-group confidence intervals. These are proposed work,
not capabilities newly implemented by this investigation. Never stop, select
targets, relax a screen, or extend a run based on final evaluation outcomes.

## Repository synchronization

At the user's request, fetched `origin` and ran `git pull --ff-only origin main`
on `feature/molecular-design-v1`. Both HEAD and origin/main are
`62f68d9e38a94439e84e6e762ec4f4b8394f3c96`; Git reported already up to date.
The fetch discovered remote refs for `codex/experimental-selection-rl` and
`codex/predictor-robustness`. Those separate branches were fetched, not merged into
the molecular implementation. All pre-existing uncommitted work was preserved.
No commit or push was performed, and no training or held-out outcome read was
started by these two investigations.
