# OligoAL: project scope, architecture and contributions

**Snapshot: November 15, 2026.** Repository base: `62f68d9`, plus the current
uncommitted implementation and experiment reports. This document summarizes the
whole project, including the current molecular-search work. It does not change
scientific contracts, authorize new experiments or replace frozen study protocols.
Older documents sometimes describe components as future work or retired; the
latest implementation and experiment reports cited here determine their status.

## 1. What the project is

OligoAL is an oligonucleotide research platform for learning from measured assays,
choosing informative experiments, and searching constrained molecular design
spaces. Its original question is whether sequential acquisition improves siRNA
efficacy prediction at a fixed measured-label budget. Its subsequent ASO work
adds endpoint-specific prediction, representation learning, robustness audits,
chemistry-aware candidate construction and learned search.

There are three distinct scientific loops:

| Loop | What is selected or learned? | Feedback | Outcome being evaluated |
|---|---|---|---|
| Measured active learning | Which existing compound–assay observation to reveal next | Previously recorded experimental labels | Held-out prediction quality versus measured-label expenditure |
| Predictor development | A mapping from molecular features to one specified endpoint | Permitted fitting and selection measurements | Error, ranking, applicability and uncertainty on separate observations |
| Molecular search | Which valid candidate to construct and score next | Frozen predictor estimates and screening rules | Search quality versus predictor-query expenditure; independent biological evidence is a separate requirement |

These loops share software and provenance infrastructure, but their budgets and
evidence are not interchangeable. A predictor query is not a new experiment;
improving predicted reward is not demonstrating better biological efficacy.

**Current scientific position:** the project has a modest, protocol-defined
positive active-learning result on Huesken, several endpoint-specific predictive
studies, informative negative representation results, and a functioning molecular
search system. The latter has promising development results from pretraining,
but neither general PPO superiority nor biological design validity is established.

## 2. Scope and data foundations

The project preserves separate modality, chemistry and assay contracts. siRNA
efficacy, ASO inhibition, acute mouse neurotoxicity and TLR immunomodulation are
different tasks. No output means that an ASO is simultaneously clinically safe
and effective.

| Source | Available scope | How it is used |
|---|---|---|
| Pinned OligoGym release | 12 datasets; 337,593 source rows validated | Benchmark reproduction, measured-label replay and separate endpoint studies |
| Huesken / `Ichihara_2007_1` | 2,431 siRNAs; 30 reported targets | Main siRNA prediction and active-learning benchmark |
| ASO Atlas 2.0 | 283,521 assay rows across four tables | Lossless preparation, endpoint-specific prediction/transfer and applicability audits |
| Public transcript sequences | Versioned/cached accession and sequence identities | Exact-complement candidate generation; not measured efficacy labels |

Atlas contains 174,459 inhibition rows, 99,821 dose-response rows, 4,900
neurotoxicity rows and 4,341 hepatotoxicity rows. The source's 295,007 readouts
use a different counting unit. Rows are not necessarily independent molecules,
and source collections can overlap; these counts should not be added into a
claim about unique training compounds.

Preparation preserves source bytes, original columns, row order, assay units,
missingness and out-of-range observations. Derived tables add stable source-row
IDs, exact HELM hashes and explicit eligibility flags. An exact HELM-string hash
is not itself canonical chemical identity or evidence of split independence.

Sources: [data preparation](aso-atlas-data-cleaning-2026-11-14.md),
[collection pipeline](dataset-pipelines.md), [evaluation contract](EVALUATION.md).

## 3. End-to-end architecture

```text
Pinned source datasets / assay metadata       Pinned transcript sequences
                 |                                      |
     Integrity and chemistry parsing            Complementary candidate grammar
                 |                                      |
     Stable IDs, context contracts, exposure and group manifests
                 |
       +---------+---------------------+--------------------------+
       |                               |                          |
Measured acquisition             Predictor development       Molecular search
restricted label oracle          fit / select / calibrate    frozen model registry
select -> reveal -> refit         endpoint-specific models   construct -> score
       |                               |                    -> update archive
deferred test evaluation         independent assessment          |
       |                               |                  pretrained scorer
       |                         versioned exports         optional PPO / controls
       +-------------------------------+--------------------------+
                                       |
                   Sealed receipts, query/label ledgers, reports
                                       |
                  CLI tools, research reports and local interfaces
```

The diagram describes the implemented boundaries and intended assessment flow.
It does not imply that an independently qualified assessment exists for every
current molecular profile. That is one of the remaining scientific gaps.

### 3.1 Shared contracts and information boundaries

The core [contracts](interfaces.md) distinguish label-free observations, datasets,
split manifests, predictors, acquisition policies and run artifacts. A restricted
training oracle owns measured training labels. Policies receive eligible records,
revealed data and fitted predictors; they do not receive test labels or a test
metric to optimize. Evaluation is deferred until decisions have completed.

Feature fitting, normalization, tuning and stopping follow each frozen study's
permitted training/selection allocation. Initial labels count toward the campaign
budget. A separate full-training-pool reference is recorded without supplying its
labels or predictions to the acquisition policy. Undefined correlations remain
undefined, with a reason.

### 3.2 Measured active-learning execution

For a fixed dataset, split, initial set and label budget, the runner repeats:

1. Fit a predictor using only revealed labels.
2. Select the next eligible batch using random, diversity, uncertainty or a
   prespecified hybrid policy.
3. Validate unique IDs and budget compliance, then reveal those measured labels.
4. Refit and save predictions/receipts at declared checkpoints.
5. After acquisition finishes, evaluate on the fixed test rows and compare paired
   learning curves with a separately fitted full-pool reference.

The official OligoGym nucleobase split withholds whole sequence-derived clusters;
it is not a target-gene holdout. Local exact-sequence and target-group diagnostic
splits are separately identified. There are two distinct hybrid protocols in the
repository; their settings and results must not be pooled.

### 3.3 Predictor families and representation studies

| Family | Implemented or evaluated role | Important limit |
|---|---|---|
| Linear/Ridge, RF and GP | Baseline reproduction, endpoint prediction, acquisition and portable scoring | Performance and uncertainty semantics depend on dataset and representation |
| One-hot CNN | Published efficacy-baseline reruns and a Huesken acquisition pilot | These are not CNN-versus-MLP ablations for the current molecular scorer |
| Frozen RNA-FM | Verified sequence representations, Ridge/neural heads and acquisition-geometry studies | Natural-base projection and pooling can lose relevant chemistry or positional information |
| RNA-FM with LoRA | Bounded Huesken adaptation implementation and completed separate Atlas transfer/scaling work | More elaborate models have not established a consistent advantage over classical controls |
| XGBoost | Classical control in the separate Atlas transfer/scaling study | Its adapted results include measured target-label expenditure |
| Candidate MLP | Current molecular scorer trained on frozen-predictor pseudo-targets | Predicts teacher eligibility/utility, not independently measured molecular success |
| CNN plus attention | Current molecular policy's target/history context encoder | Its presence does not establish its incremental value in a controlled ablation |

No completed graph-neural-network comparison for the current molecular scorer
was identified in the inspected implementation and study reports. Architecture
availability, upstream dependencies and a trained comparative result are different
things. Current evidence does not establish that a GNN, CNN, transformer or MLP
is generally best for this project.

Sources: [RNA-FM study](rnafm-study.md), [LoRA protocol](rnafm-lora-comparison.md),
[completed Atlas audit](molecular-measured-data-scaling.md),
[baseline reproduction](gate1-efficacy-reproduction.md).

## 4. Molecular construction and learned search

The original target-window RL scaffold was retired. The current
`src/oligo_engine/molecular_design/` package is its implemented replacement;
historical retired commands and results are not current entry points.

### 4.1 Campaign and molecule definitions

A campaign fixes the transcript, permitted binding intervals, exact-complement
mechanism, chemistry patterns, endpoint contexts, starting designs and finite
construction/scoring budgets. Designs preserve ordered base, sugar, linkage,
methylation, gap/wing and terminal information. Unsupported chemistry is rejected.
The current task searches an explicit grammar, not arbitrary chemical graphs or
unrestricted nucleotide substitutions.

New construction follows:

```text
NEW -> LENGTH -> SITE -> LAYOUT -> PATTERN -> TERMINAL -> COMMIT
```

That is seven grammar tokens for a new proposal, although single-choice stages
can be collapsed so the learned policy makes fewer decisions. A complete campaign
can propose several molecules. Grammar actions and scoring requests are different
budgets. The revised transactional decoder prevents the previous edit/cancel loops
and cached-parent recommits, and constrains early stopping. Partial molecules do
not call predictors.

### 4.2 State, action masks and scoring

Observations contain the full bounded target tracks, allowed regions, chemistry
patterns, partial construction, query history, prediction/missingness diagnostics,
archive information and remaining budgets. Action masks depend on legal structure,
profile restrictions and visited identity, not unseen candidate rewards.

The frozen registry verifies model identities and assigns each head an explicit
objective, required-screen or advisory role. Each head retains its assay context
and units. Missing or unsupported required endpoints cannot silently pass a screen.
Infrastructure failures are recorded as failures, not adverse biological outcomes.
Starts, proposals and cache hits consume logical scoring requests; physical head
calls are counted separately.

### 4.3 Archive objective and reinforcement-learning reward

In the current constrained-efficacy setting, let `A` be the scored archive,
`eligible(x)` mean that all required screens pass, and `u(x)` be efficacy utility
under a fixed training-reference empirical CDF:

```text
Q(A) = max({u(x): x in A and eligible(x)} union {0})
r_t  = Q(A_(t+1)) - Q(A_t)
```

Construction-only transitions have zero reward. With gamma and GAE lambda set to
one, undiscounted episode return is final archive quality minus starting archive
quality. The start is charged and reported; a high terminal score can partly
reflect a good starting molecule. A separate fixed-reference hypervolume objective
is implemented for explicitly declared multiobjective profiles. This is not an
arbitrary clinical safety/efficacy weighted sum.

### 4.4 The pretrained candidate model

The current scorer is a shared feedforward MLP:

```text
Actual antisense sequence + ordered chemistry tracks
                  |
       max_length x 16 positional features
                  |
       flatten -> Linear(320,64) -> GELU
                  -> Linear(64,64) -> GELU
                  -> Linear(64,2)
                  |
       eligibility logit and utility logit
```

The 320-input size applies to the present 20-nucleotide maximum; shorter molecules
are zero-padded. Features encode bases, sugars, methylation, PS/PO links, valid
positions, gap membership and terminal chemistry. The same weights score every
candidate across transcript sites; this is not a position-specific action lookup.

Pretraining uses training-campaign queries to the frozen endpoint models. Its loss
is binary cross-entropy for screen eligibility plus mean squared error for sigmoid
utility. Only the molecular encoder and its two-output head are pretrained.
These are supervised pseudo-targets, not new biological observations. The current
study uses 576 examples per seed and 20 pretraining epochs.

The learned scorer can rank complete candidates directly or guide the staged
construction interface. Direct ranking and the staged pretrained policy are
distinct controls and can produce different results. The staged no-PPO controller
still contains context/action components that pretraining did not optimize.

### 4.5 What optional PPO adds

`SearchEncoder` uses two target-sequence convolutions, width 32 with kernels 5
and 3, followed by construction-conditioned attention over target and history
representations. Chemistry/context summaries join a 128-dimensional search
embedding. The candidate policy combines its pretrained molecular score with a
learned context-dependent residual; legal completion scores are aggregated into
grammar-action probabilities. Administrative actions have a separate head.

Masked PPO adds an actor–critic objective and can update the molecular and search
components using archive-gain feedback. The molecular MLP is therefore one part
of the full policy, not a description of the entire PPO network. Learned pooling
can discard information; a sufficient Markov representation has not been proved.

Current full runs used 16,384 policy decisions, rollout size 256, minibatch 64,
four update epochs and five training seeds. Checkpoint selection used validation
campaigns. Pretraining-only deployment is supervised learned search; pretraining
followed by PPO is supervised initialization plus RL fine-tuning. The environment
supports either and does not depend scientifically on PPO winning.

Source: [implementation](molecular-design-implementation.md),
[policy revision](molecular-policy-repair.md),
[candidate policy code](../src/oligo_engine/molecular_design/candidate_policy.py),
[pretraining code](../src/oligo_engine/molecular_design/pretraining.py).

## 5. Results and what they support

### 5.1 Measured active learning: the strongest positive result

On Huesken with a one-hot GP and official nucleobase holdouts, the separately
frozen 40-seed study reports uncertainty-minus-random normalized Pearson
learning-curve area of **+0.0095**, bootstrap 95% CI **[+0.0043, +0.0146]**,
paired t-test **p = 0.00095**, with 28/40 seeds positive. The protocol was frozen
before these seeds; earlier exploratory seeds were analyzed separately.

This supports a modest matched-label prediction improvement for that dataset and
protocol. It does not establish significant label savings, superiority over the
other nonrandom policies, independent target-gene transfer or cross-endpoint
generalization. Fresh repeated holdouts on one dataset are not fresh biological
datasets. The broader seven-dataset historical reproduction requirement also
remains unresolved. [Study and analysis](acquisition-comparison.md).

### 5.2 Broader evidence, including negative findings

| Study | Recorded result | Interpretation |
|---|---|---|
| Seven published best efficacy baselines | 35 fits; 4/7 within the fixed 0.03 Pearson tolerance; Huesken CNN 0.6096 vs published 0.6309 | Partial numerical reproduction; exact historical reproduction remains open |
| All-dataset diagnostic acquisition | 180 campaigns; uncertainty improves mean area on 5/12 sequence-group tasks and worsens it on 7/12 | No universal acquisition benefit; local diagnostic splits and hashed-HELM RF |
| Huesken CNN diversity pilot | Five paired seeds; AULC difference −0.0150, sample SD 0.0398 | No consistent diversity advantage in that setup |
| Frozen RNA-FM versus one-hot Ridge | Five seeds; frozen-minus-one-hot AULC −0.1013, sample SD 0.0512 | Negative for the tested pooling/head recipe; not all foundation models |
| Acute MOE neurotoxicity prediction | GP Pearson 0.597, sample SD 0.112 over 30 seeds | Endpoint-specific predictive signal; no clinical safety inference |
| TLR8 potentiation / TLR7 inhibition | Pearson 0.666 (GP) / 0.598 (RF), separate 30-seed studies | Separate assays; upstream TLR naming mismatch documented |
| ASOptimizer chemistry-matched efficacy | GP Pearson 0.317, sample SD 0.061 over 30 seeds | Weak predictive signal; not a general ASO efficacy model |
| Supported 20-mer efficacy ranking | Predicted top-20 measured lift +10.89 pp on ATXN2 and +9.88 pp on DGAT2 | Positive two-target development ranking; generated molecules remain unmeasured |
| Atlas adaptation/scaling | At larger source allocation, LoRA RMSE 22.340 vs Ridge plus offset 19.656 | No LoRA advantage in this recipe; each target used 200 adaptation labels |

The supported 20-mer study used fully PS, methylated MOE 5/DNA 10/MOE 5 at human
HepG2/electroporation/4,500 nM/24 h. It is not the current multi-pattern stress
profile. The Atlas scaling study also has changing inner validation membership
and documented compound overlaps, so it is not a clean nested data-size curve.

Sources: [baseline study](gate1-efficacy-reproduction.md),
[collection results](full-experiment-protocol.md),
[MOE study](neurotox-moe-predictor.md), [TLR study](tlr-immunomodulation-predictors.md),
[ASO efficacy](aso-efficacy-predictor.md),
[supported-profile ranking](supported-aso-results-2026-11-14.md),
[scaling audit](molecular-measured-data-scaling.md).

### 5.3 Current eight-target molecular-search comparison

Mean best eligible surrogate utility across five seeds, eight scoring requests
including the start. These values are not inhibition percentages or success
probabilities. APOC3/ANGPTL3 were a separately frozen two-target extension.

| Target | Role | Pretraining + PPO | Pretrained staged policy | Random | Greedy |
|---|---|---:|---:|---:|---:|
| DGAT2 | Policy training | 0.8884 | 0.8884 | 0.4088 | 0.4869 |
| CFB | Checkpoint validation | 0.7205 | 0.4872 | 0.2221 | 0.0000 |
| FGFR4 | Previously inspected development | 0.6943 | 0.7094 | 0.0000 | 0.1479 |
| F9 | Development | 0.9578 | 0.9578 | 0.8905 | 0.9597 |
| F12 | Development | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| TTR | Development | 0.6944 | 0.7045 | 0.6239 | 0.6116 |
| APOC3 | New development | 0.8863 | 0.8771 | 0.7564 | 0.1983 |
| ANGPTL3 | New development; predictor-seen | 0.9258 | 0.9258 | 0.7950 | 0.6145 |

Several targets have supervised-predictor exposure, not only ANGPTL3. These are
not eight independent held-out targets. The revised pipeline exceeds random and
greedy means on six targets, but pretraining alone matches or exceeds full PPO
on six. CFB's PPO improvement is on checkpoint-validation data. F12 has no eligible
design among its 89 legal candidates under the fixed screen; its zero is retained.

Across the four original development targets, full PPO minus staged pretraining
is −0.006283 at eight requests and +0.006283 at 32. Search speed and final utility
can differ. Full fitting/selection across five seeds consumed 27,028 offline
predictor requests versus 2,880 for pretraining alone. Equal deployment caps do
not imply equal total cost. The original 360 evaluations and extension's 60 runs
are related cells of a study, not 420 independent scientific replications.

Source: [eight-target synthesis](molecular-scientific-experiments.md),
[PPO attribution](molecular-ppo-attribution-experiment.md).

## 6. Scientific reliability and remaining limits

### Predictor applicability

The current expanded profile uses three 18/20-mer chemistry patterns. A full
metadata audit found zero verified exact matches to these patterns at the chosen
HepG2 efficacy context among parsable rows. Other contexts have thousands of
matches, but protecting existing selection/reserved groups and connected
sequence/patent components removes much of the apparent new fitting pool.

The active efficacy allocation is 2,869 rows: 2,284 fitting and 585 selection,
about 2% of broadly analysis-eligible inhibition rows. That denominator does not
mean the remaining 98% is compatible unused training data. Policy pretraining
already covers about 36% of its 1,602-compound training catalog per seed.

The separate acute mouse-risk head uses 873 observed fitting labels, 259
development and 283 calibration rows; 304 final rows remain sealed. Its relative
screen is a development rule, not a validated human safety threshold.

### Independence and robustness

The exposure audit currently certifies **zero independent final groups for the
active joint molecular profile**. Exact identity checks alone do not resolve
species aliases, near-sequence families, patent families or all previous study
exposure. Existing reserved campaigns remain protected.

Robustness infrastructure implements grouped splits, representation-preserving
perturbations, domain distance, error/uncertainty diagnostics, calibration,
abstention and post-selection audits. Synthetic exploitation detection works.
The executed ASOptimizer real audit had zero admitted final assay-context coverage;
real final accuracy and an effective guardrail were therefore undefined. That
is a feasibility failure to fix before evaluation, not a positive robustness result.

Sources: [validity audit](molecular-validity-experiment.md),
[generalization audit](molecular-generalization-experiment.md),
[robustness implementation](predictor-robustness-implementation.md).

## 7. Contributions: demonstrated, implemented and still prospective

| Contribution | Current evidence level |
|---|---|
| Auditable retrospective experiment-selection framework | Implemented, with restricted label access, matched budgets, deferred evaluation and invariant tests |
| Modest Huesken active-learning improvement | Supported under the fixed one-hot GP/nucleobase protocol; limited to that setting |
| Reproduction and data-provenance audit | Concrete findings include effective RF argument mismatch, TLR label mismatch, partial numerical reproduction and lossless Atlas preparation |
| Endpoint-specific prediction and representation comparison | Executed positive and negative development evidence, including chemistry-sensitive prediction and unfavorable FM/LoRA comparisons |
| Chemistry-aware budgeted molecular search | Implemented grammar, real frozen adapters, conventional controls, learned scorer, optional PPO, persistence and interfaces |
| Surrogate-guided molecular pretraining | Promising computational development evidence; causal gain over the same architecture without pretraining still needs a clean ablation |
| General PPO superiority | Not established; current incremental effects are mixed and carry extra query costs |
| Reliable biological molecular design | Not established; applicable independent measurements and qualified final evaluation remain missing |

These are project contributions, not claims of first-in-literature novelty.
The current molecular evidence supports emphasizing **chemistry-aware,
surrogate-guided learned search**, with PPO as an optional refinement under
evaluation. Switching the scientific framing does not remove the RL code or
turn pseudo-label training into measured biological validation.

## 8. User interfaces, artifacts and reproducibility

Two local surfaces serve different purposes:

- [Candidate-ranking app](../app/README.md): gene or pasted transcript to tiled,
  chemistry-matched ASO hypotheses, separate endpoint columns, sequence/structure
  diagnostics and exports. Its endpoint models are fitted for demonstration;
  that route is not a held-out benchmark. Its idealized helix is not a predicted
  three-dimensional molecular structure.
- [Molecular-search interface](molecular-design-implementation.md): frozen
  campaigns and policy/control comparisons, charged scoring budgets, archive
  panels, endpoint status, shortfalls and JSON/CSV exports. Final campaigns are
  blocked from interactive use; request handling does not fit models.

Artifacts record configuration, source/model identities, split memberships,
seeds, costs, provenance and environment. Molecular runs additionally use
content-sealed receipts and hash-chained query journals. Seals detect changed
content; they do not establish biological validity. Reload and consumed-rollout
continuation have explicit schema/RNG/optimizer checks; arbitrary mid-rollout
resume is not promised.

Python 3.11 and Poetry 2.1.4 are the working baseline. Optional groups separate
science, reporting, molecular RL and molecular data dependencies. The molecular
runtime pins Gymnasium 1.1.1, SB3/sb3-contrib 2.6.0 and Torch 2.3.1. RNA-FM/Atlas
research uses separately documented runtimes and an external verified backbone.
Real clean-machine reproduction still requires the relevant owner artifacts.

The latest integrated experiment report records 251 passing core tests plus lint,
format and import checks; those are historical verification results, not tests
rerun while writing this summary. Tests exercise label isolation, replay,
identity/masking, reward accounting and metadata-only audit boundaries. Synthetic
fixtures prove plumbing rather than scientific performance.

Raw authorized releases retain notices and manifests. Generated runs and RL
weights remain ignored. Only the specific existing prediction checkpoints in
`model_checkpoints/manifest.json` have the recorded publication exception; the
external RNA-FM backbone is not redistributed under that exception. Project
licensing and broader publication rights remain owner decisions.

## 9. What the next scientific stage should establish

The existing [experiment plan](molecular-scientific-experiments.md) separates
three questions that should remain independently answerable:

1. **Predictor validity:** complete exposure/context qualification, then compare
   predictors on common permitted measured observations. Larger data fractions
   require fixed assessment groups and nested fitting allocations, not changing
   validation membership or silently pooling incompatible assays.
2. **Pretraining and PPO attribution:** use the same candidate architecture,
   grammar, scorer and deployment budget; compare exact pretraining-only states,
   fixed PPO prefixes, direct ranking and extra supervised training with matched
   query expenditure. Save zero-step checkpoints and allow them to win selection.
3. **Generalization and discovery:** certify genuinely independent groups before
   final scoring; predefine effect sizes, sample counts and paired analyses that
   respect crossed target/seed dependence. Generated molecules need compatible
   independent measurements to support biological claims.

Alternative molecular encoders are a possible separate experimental factor.
They should not be credited as evaluated merely because CNNs or RNA-FM have
been used elsewhere in the project. Architecture comparisons and larger training
matrices are prospective unless an executed report explicitly says otherwise.

## 10. Code and documentation map

| Area | Main implementation / evidence |
|---|---|
| Scientific contracts | [SPEC](SPEC.md), [EVALUATION](EVALUATION.md), [interfaces](interfaces.md) |
| Data, IDs and restricted labels | `src/oligo_engine/data/`, `contracts.py`, `provenance.py` |
| Acquisition and replay | `acquisition/`, `evaluation/`, `active_learning.py`, `collection.py` |
| Reproduction | `audit_upstream.py`, `reproduce.py`, `efficacy_reproduction.py` |
| Predictors and representations | `models/`, `features/`, `representations/`, `rnafm_study.py`, `rnafm_lora_study.py` |
| Frozen endpoint adapters | `reward/`; molecular-specific adapters in `molecular_design/` |
| Molecular search | `molecular_design/`; [final specification](FINAL_MOLECULAR_DESIGN_RL_SPEC.md) |
| Robustness | `robustness/`, `reporting/robustness.py` |
| Research allocation | `research/`, `configs/research/studies.toml` |
| Interfaces | `app/server.py`, `app/molecular_server.py`, `app/static/` |
| Experiment evidence | `docs/`, ignored `artifacts/`, manifest-listed prediction checkpoints |

Paths in the map are relative to `src/oligo_engine/` unless otherwise indicated.
This overview adds documentation only; it does not launch experiments, alter the
main thread's ongoing work, or change any endpoint, data partition or model.
