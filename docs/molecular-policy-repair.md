# Shared-candidate molecular policy repair

Follow-up: the user-requested [data-scaling investigation](molecular-data-scaling-plan.md)
separates measured predictor data from policy experience and defines the next
staged experiments. Its proposals do not replace the completed results below.

The user authorized addressing the weaknesses diagnosed after the five-seed PPO
comparison. This revision changes the policy representation, training experience
and learning schedule. It preserves the frozen endpoint predictors, screens,
normalizers, complete legal design space and archive-improvement objective.
Performance must be evaluated; a functioning implementation does not establish
that PPO is superior to random search.

The completed study contains **360 evaluation runs**: 300 from the original
five-method matrix and 60 from a separately declared full-budget pretrained-prior
control. All runs spend exactly their scoring caps without repeated design queries.
The full pipeline has higher mean utility than random and greedy on four of six
reported targets. The no-PPO ablations do not support attributing the full gain to
PPO; the learned representation and pretraining contribute substantially.

## Completed results

At eight requests including the start, mean best eligible surrogate utility over
five seeds (800–804):

| Target / role | Revised PPO | Architecture only | Pretrained staged policy, no PPO | Random | Greedy | Pretrained ranking, no PPO |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DGAT2 / training | 0.8884 | 0.8106 | 0.8884 | 0.4088 | 0.4869 | 0.8884 |
| CFB / validation | 0.7205 | 0.4749 | 0.4872 | 0.2221 | 0.0000 | 0.7982 |
| FGFR4 / previously used development | 0.6943 | 0.3982 | 0.7094 | 0.0000 | 0.1479 | 0.2657 |
| F9 / new to policy fitting/selection | 0.9578 | 0.8485 | 0.9578 | 0.8905 | 0.9597 | 0.9578 |
| F12 / new to policy fitting/selection | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| TTR / new to policy fitting/selection | 0.6944 | 0.6239 | 0.7045 | 0.6239 | 0.6116 | 0.6843 |

Revised PPO's sample SD is 0.0000, 0.1695, 0.0412, 0.0043, 0.0000 and 0.0276,
respectively. These are bounded surrogate scores, not efficacy percentages. The
common TTR starting utility is 0.5959; its mean PPO archive gain is 0.0985. Other
reported starting utilities are zero. Comparisons are paired within this study;
the historical seeds 700–704 are not pooled with the fresh 800–804 seeds.

For the four development targets, revised PPO versus random has paired
win/tie/loss counts of 5/0/0 (FGFR4), 4/1/0 (F9), 0/5/0 (F12), 4/0/1 (TTR).
Against greedy the counts are 4/1/0, 0/4/1, 0/5/0 and 4/1/0. This is a small,
surrogate-only diagnostic, not a confirmatory cross-target superiority claim.

The pretrained staged policy matches or exceeds the full PPO mean on five of six
targets at the primary cap. PPO improves CFB versus that ablation, but CFB selected
checkpoints and the simpler pretrained ranking control performs better there.
Consequently **PPO's incremental value over pretraining is not established**.
At the secondary 32-request cap, full PPO matches or exceeds the staged no-PPO
mean on all six targets; that request horizon was outside training and remains
a separately labeled budget-extrapolation diagnostic.

The F12 zero is not a construction failure. The union of already charged evaluation
queries covers exactly all 89 legal design identities, and every design fails the
frozen development mouse-risk screen. No optimizer can earn positive eligible
archive utility in that fixed space. The post-evaluation identity audit costs no
additional queries and is saved in `f12-coverage-audit.json`. This does not establish
actual biological risk, and no screen threshold or target interval was relaxed.

All 360 indexed artifact seals were verified against their result records. The
budget curves were visually inspected. Administrative orchestration attempted to
start two already-running seeds when earlier shell queues advanced; the existing
directory guards rejected those duplicate launches before queries or writes.
Every intended training run completed once, with its original artifacts preserved.

Training changes are measurable: the full policies make **3,838–4,262 new proposals**,
encounter **736–986 distinct proposed compounds**, and receive **1,052–1,206 positive
archive-gain commits** per run, versus roughly 280 proposals and 60 positive commits
in the earlier bounded training. Each full policy also consumes 576 pretraining
requests. Across five full policies the cost is **23,188 PPO training requests +
2,880 pretraining requests + 960 checkpoint-validation requests**. The small-data
architecture arm costs 1,701 training + 80 validation requests. The 360 evaluation
runs cost 7,200 requests. Scientific head calls are twice those request counts.
Costs are not concealed inside the common eight-request deployment cap.

Full-policy selected decision counts are 4,096 / 4,096 / 8,192 / 4,096 / 16,384
for seeds 800–804. All trained to the frozen limit; longer training did not
monotonically improve validation. Earlier checkpoints are selected by the original
validation rule, and all incurred costs remain reported.

- [Budget curves](../artifacts/molecular-policy-repair-v3/comparison.png)
- [Report with seed SD and query counts](../artifacts/molecular-policy-repair-v3/report.md)
- [All main-run metrics](../artifacts/molecular-policy-repair-v3/results.csv)
- [Paired contrasts](../artifacts/molecular-policy-repair-v3/summary.json)
- [Supplemental pretrained ranking control](../artifacts/molecular-policy-repair-v3/prior-control-results.json)

## Position-independent molecular actions

The earlier policy used a separate output weight for each absolute transcript
position. DGAT2's training sites did not overlap the sites used on CFB or FGFR4.
Those evaluation-site outputs consequently lacked direct policy-gradient training.

`CandidatePolicy` replaces molecular-field outputs with one shared function of
complete candidate sequence and chemistry. The candidate encoding contains the
actual antisense bases, per-nucleotide sugar, methylation, linkage, gap/presence and
terminal tracks, with explicit zero padding. It contains neither absolute site
coordinates nor unqueried endpoint scores. Full transcript, construction, context
and query-history observations remain available to the history-conditioned actor
and critic. Candidate features describe every legal complete design; undersized
candidate capacities fail rather than truncate the design space.

For a candidate `d`, the scorer combines a learned molecular prior with a
history-conditioned residual:

```text
h(d) = shared sequence/chemistry encoder
z(d,s) = 4 × sigmoid(eligibility_logit(d)) × sigmoid(utility_logit(d))
         + dot(h(d), query(policy_context(s))) / sqrt(64)
```

The two prior outputs are uncalibrated policy components. They are not replacement
scientific endpoint models, reported biological measurements or certified risk
probabilities. The frozen scientific scorers still evaluate only charged queries.

At a molecular-field decision, the action logit is the log-sum-exp of candidate
scores over legal, unqueried completions matching that action. This preserves the
staged length/site/layout/pattern/terminal construction interface while sharing
parameters across sites and chemistry choices. The completion mask is determined
only by grammar, draft state and previously queried identities. No oracle score
affects it. Administrative choices retain history-conditioned logits.

The architecture therefore represents a distribution over complete designs through
their partial constructions. Marginalization is over model scores, not extra
endpoint queries. A large branch can have more probability mass; this is the
declared completion-based parameterization, not a hidden greedy oracle. Scores
can change as construction/history context changes, so this is not claimed to be
one fixed joint distribution throughout an entire episode.

## Informative learning without changing the reward

The exact objective remains:

```text
r = Q(archive_after) - Q(archive_before)
gamma = 1; GAE lambda = 1
sum(rewards) = final_archive_quality - starting_archive_quality
```

No bonus is awarded for validity, committing, surviving a screen, or ending an
episode. Poor or non-improving molecules can still have zero reward. That is the
correct consequence of the specified best-eligible-archive objective.

Two changes address learning efficiency:

1. When only one action is legal, the optional Gym adapter executes it and combines
   its reward with the preceding decision transition. Every original construction
   token, scoring query and reward remains in the audit trace and consumes its
   original budget. Reset does not execute scoring actions. Because gamma is one
   and budgets are intrinsic, removing actionless decisions preserves the return.
   PPO now spends its training decision budget predominantly on actual choices.
2. A fixed pretraining phase makes explicitly charged queries only within training
   campaigns. Every queried response supplies an eligibility target and an efficacy
   utility target, including rejected and non-improving candidates. Binary
   cross-entropy plus sigmoid-utility MSE initializes the shared molecular encoder
   and prior. These targets are frozen-surrogate predictions, not observations.
   No validation/development/final campaign is accepted by this fitting interface.
   Predictor parameters and reward definitions never change.

Pretraining uses uniform sampling without replacement within each campaign,
32 requests including the start, 20 fixed epochs, batch size at most 64 and Adam
learning rate 0.001. There is no outcome-dependent sample enrichment, epoch
selection or stopping. Its queries, endpoint calls, candidate identities, seed,
loss trajectory and artifact seal are recorded separately. The warm-start weights
are saved and hashed before PPO, enabling a no-PPO ablation. PPO subsequently
fine-tunes policy parameters using the original clipped objective.

## Broader, frozen development protocol

Local protocol/configuration: `artifacts/molecular-policy-repair-v3/`.
The nine newly downloaded public Ensembl cDNA sequences are hashed and embedded in
the frozen configuration. Only gene symbols were sent to the public service.
No measured outcomes were downloaded or read for this experiment.

| Policy partition | Genes | Regions |
| --- | --- | --- |
| Training | DGAT2, SOD1, B2M, HPRT1, PCSK9, VEGFA | Three 48-nt windows per gene, starting at 20%, 50%, 80% of transcript length |
| Checkpoint validation | CFB, F7 | The same three fixed fractions per gene |
| Development evaluation | FGFR4, F9, F12, TTR | One midpoint 48-nt window per gene |

Windows are selected from sequence metadata before querying. Each has 89 legal
complete designs. Gene/transcript/sequence partition overlap and exact compound
overlap across partitions are rejected. This provides 18 training campaigns
instead of one. Gene grouping does not establish absence of all homology-related
dependence, and supervised predictor exposure remains separately unqualified.

Five fresh policy seeds, 800–804, are frozen before training. The full arm uses
16,384 policy decisions, 256-decision rollouts, minibatches of 64, four PPO epochs,
learning rate 0.0003 and entropy coefficient 0.01. Validation occurs every 4,096
decisions across the six validation campaigns; the earliest maximum-mean-utility
checkpoint is retained. Training episodes still have eight requests and 160
construction tokens. Pretraining costs 576 requests per policy, separately from
PPO exploration and checkpoint validation.

The architecture-only arm trains on the original DGAT2 midpoint campaign for
2,048 uncollapsed actions, validates on the CFB midpoint campaign every 1,024
actions, and uses no pretraining. It checks the shared molecular scorer at the
earlier training scale. Both new arms use the broader study's common transcript
capacity and 32 archive slots, so this is not an otherwise byte-identical ablation
against the historical pooled policy. The full arm changes several factors jointly; comparing
these arms cannot identify each factor's independent causal effect.

Evaluation compares the full arm, architecture-only arm, warm-start policy before
PPO, random, and greedy. The six reported targets are DGAT2, CFB and the four
development targets. DGAT2 and CFB retain training/selection roles; FGFR4 was
previously inspected. F9/F12/TTR are new to policy fitting and selection, but are
not qualified independent biological targets. No final measured data are read.

The primary cap is eight requests including the common start. A secondary cap of
32 requests tests extrapolation beyond the training request horizon, including
previously unused archive slots; it is not an in-distribution training result.
All methods receive the same frozen scorer, legal designs, start and request cap.
Random and greedy retain the duplicate-free `queried-history-v2` implementation.
Early stopping is recorded with actual costs; unspent requests are not imputed as
queries. There is no claim of a cold-start advantage: policy pretraining, PPO and
validation costs are reported in addition to deployment costs.

The protocol fixes the schedule without extensions based on evaluation outcomes.
Report per-target means and sample SD over five seeds, paired differences and
success counts. Seed SD is not a cross-target confidence interval. A warm-start
advantage over PPO is a valid result and must not be attributed to reinforcement
learning. Expanded predictor applicability and independent evidence gates remain
open regardless of optimizer performance.

Before inspecting evaluation outcomes, a supplemental protocol was sealed for a
full-budget pretrained ranking control. It sorts unqueried complete designs by
the pre-PPO molecular prior (eligibility sigmoid × utility sigmoid), breaking ties
by design identity. It makes no additional scientific-head calls while ranking;
only the subsequent selected queries are scored and charged. It costs the same
576 training queries per seed as the staged warm-start policy and requires no PPO
training or checkpoint selection. This tests whether administrative early stopping
could make the staged ablation artificially weak. In the actual results, both
staged policies use their full budgets. The supplemental controller remains
separate from the original frozen five-method comparison.

## Integration and verification

The optional settings are versioned by the environment schema. Existing policies
retain their original decoder/observation schema and remain loadable. The CLI and
local app reconstruct candidate capacity and forced-step behavior from saved
training configuration. Saved policies include their architecture; resume retains
the policy decision count, optimizer, RNG and exact construction state.

Tests verify candidate-order invariance, site-independent molecular scoring,
gradient propagation to the shared encoder, no hidden predictor calls, exact
antisense/chemical encoding, refusal to truncate candidates, forced-transition
reward/query equivalence, rejection of validation pretraining, deterministic reload
and parameter-for-parameter continuation after resume. All 230 core tests and ten
optional Gym/PPO tests pass; lint, formatting and import checks pass. The local app
also loads the new architecture and produces query journals and JSON/CSV exports.
An existing historical checkpoint reproduces its normalized saved action trace and
quality exactly under the updated code.

Run with a fresh output directory and the pinned molecular runtime:

```sh
PYTHONPATH=src poetry run python scripts/molecular_policy_repair.py prepare \
  --config artifacts/molecular-optimizer-comparison-v2/config.json \
  --output artifacts/molecular-policy-repair-replay
# Repeat each arm for seeds 800, 801, 802, 803, 804.
PYTHONPATH=src poetry run python scripts/molecular_policy_repair.py train \
  --output artifacts/molecular-policy-repair-replay --arm full --seed 800
PYTHONPATH=src poetry run python scripts/molecular_policy_repair.py train \
  --output artifacts/molecular-policy-repair-replay --arm architecture --seed 800
PYTHONPATH=src poetry run python scripts/molecular_policy_repair.py evaluate \
  --output artifacts/molecular-policy-repair-replay
PYTHONPATH=src poetry run python scripts/molecular_policy_repair.py report \
  --output artifacts/molecular-policy-repair-replay
```

The supplemental ranking controller is `scripts/molecular_prior_control.py`; it
requires an explicit `prior-control-protocol.json` identifying the parent protocol,
seeds, budgets and evaluation campaign identities before execution.

Source/configuration identities and scientific predictor receipts are verified.
This local replay requires the cached transcript and predictor artifacts. New
policy weights, transcript downloads and generated results remain ignored and
are not committed or published.

For ordinary CLI training or app inference, the local `full-config.json` contains
the full arm's training settings and seeds. The study runner's original sealed
`config.json` supplies scientific campaigns; its arm settings live in `protocol.json`.
Example inference, using the predeclared first seed rather than selecting a seed
based on evaluation performance:

```sh
poetry run python app/molecular_server.py \
  --config artifacts/molecular-policy-repair-v3/full-config.json \
  --policy artifacts/molecular-policy-repair-v3/full-800 \
  --output artifacts/molecular-app-v3 --port 8001
```
