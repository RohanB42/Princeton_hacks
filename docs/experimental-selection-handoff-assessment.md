# Experimental-selection handoff assessment

November 15, 2026. Source: the user-provided “Hack Princeton ASO project | Chat
context and handoff,” dated November 14. Historical results below are reported by
that handoff, not independently reconstructed from the unavailable artifacts.

## Provenance and the two systems

The handoff identifies later experimental-selection work at
`/Users/harrisonmartel/hackprinceton/work/experimental-selection-rl`, local branch
`codex/experimental-selection-llm-agent`, commit `30ac0e9`. The exact worktree path
is inferred from the handoff's relative links; neither it nor the named Harrison
checkout exists in this environment. Objects `30ac0e9` and `4c38769` are absent
from this repository. The fetched experimental-selection remote remains
`1b92731`; refreshing all 11 remote branches did not retrieve the later work.
That explains the earlier unsuccessful search without implying the experiments
never existed. Source reports, ledgers and weights on that machine are still
needed for byte-verified reproduction.

The current molecular-design system in this checkout constructs ASOs and searches
frozen inhibition/risk predictions. Its candidate-MLP pretraining, eight-target
utility comparison, 2,284-row efficacy Ridge and 873-row risk Ridge belong to that
system. They are not the experimental-selection V3 priors described in the handoff.

The side process chooses paid assays for existing recorded compounds. The handoff
reports source-only inhibition and log10-IC50 Ridge priors fitted on EZH2/SPDEF,
with Bayesian residual updates from paid observations. Its Qwen models keep their
weights frozen. The old OligoGym GP/RF endpoint models and RNA-FM study have other
roles; their performance or training memberships cannot be substituted for V3's.

## Assessment of the side process

The strongest supported contribution is a carefully instrumented measured-assay
replay benchmark, including negative optimizer and interface results. The reported
controls span expert-action PPO, direct-action PPO, residual PPO, supervised
initialization, conditional confirmation models, Bayesian lookahead and language
agents. Increasing action access or model complexity did not establish reliable
superiority over direct greedy. Completed software tests and ledger reproduction
support engineering correctness; they do not establish biological generalization.

Direct greedy remains the reference selector. The reported eight-cohort comparison
has mean original-rule confirmed hits 3.000 for greedy, 3.125 for Bayesian
lookahead, 2.500 for Qwen3-4B and 2.234375 for random. These do not establish a
significant advantage of the learned selector. The earlier NLRP3 availability
resampling is variation within one historical test panel, not hundreds of
independent biological replications.

The most actionable finding concerns endpoint adjudication. Under the reported
V3 protocol, a paid potency curve counts only with a usable in-range absolute
IC50 estimate <=500 nM. Three MSH3 curves purchased by Qwen already exceed 50%
inhibition at the lowest dose, 62.5 nM, and increase across the observed grid.
Under the handoff's post-hoc bound rule, the same purchases change from:

| Selector | Original point-estimate hits | Exact plus bound-supported hits |
|---|---:|---:|
| Qwen3-4B | 2 | 5 |
| Direct greedy | 3 | 5 |
| Random, 32 seeds | 2.1875 | 3.03125 |

This removes the observed Qwen–greedy deficit on that panel; it does not establish
Qwen superiority. It is a post-hoc rescoring of unchanged purchases, not an
adaptive replay or PPO retraining result. The scientific issue is that requiring
an in-range point estimate can misalign the reward with a threshold-discovery
question. Whether any code violates its original specification is a different
question. Bound qualification still needs prespecified endpoint, monotonicity,
measurement uncertainty and assay-QC assumptions, especially near 50% response.

The reported Qwen interface is also a material limitation: it selected the first
letter on 93/116 calls, and reordered prompts changed the selected assay in all
16 tested cases while preserving the chosen letter. That supports a problem with
this tested decision interface. It does not establish an intrinsic inability of
all language models to plan assays. Compare counterbalanced/stable identifiers
and deterministic/random policies using the same candidate menu before attributing
performance to reasoning or scaling the model.

## Original benchmark contract to preserve

- A $500 single-dose screen must show measured inhibition strictly above 80%
  before its linked $2,000 potency curve can be purchased.
- The nominal budget is $15,000; curve-cost sensitivities are $1,000 and $4,000.
  These are modeled acquisition costs, not incurred wet-lab expenses.
- Original success uses absolute IC50 <=500 nM and in-range curve QC. The handoff
  names at least four finite distinct positive doses, observed-span requirements
  and fit R² >0.5; the source implementation must supply exact remaining settings.
- Full direct PPO and greedy have all eligible compound–assay actions. The Qwen
  pilot has up to six ranker-generated proposals, a different action interface.
- Linked panels are historically advanced compounds with recorded follow-ups.
  They are not an unbiased sample of all initial screening candidates.
- Preserve original point-estimate results and all already-inspected target roles.
  No revised final labels may feed fitting, prompt selection or stopping.

## Relationship to the newly requested experiments

The [new IC50/Qwen pilot](ic50-qwen-from-scratch.md) had already sealed its protocol
and loaded selected outcomes before this handoff arrived. It uses Qwen2.5-3B,
direct complete-panel purchases, a fixed eight-panel cap and an operational
100 nM primary cutoff on F7/STAT3/NLRP3. Its exact-only comparator is constructed.
These choices stay frozen, and its results remain a separate retrospective
diagnostic. They must not be relabeled a reproduction of Qwen3-4B, the 500 nM
two-stage benchmark or its original screen/curve linkage gate. A sealed late
scope note records the new information, including unavailable NLRP3 split IDs.

The [planning experiment](value-of-planning-experiment.md) solves an explicit
four-candidate probabilistic model, with noisy cheap screens and perfect binary
confirmations that can be bought directly. Its value-of-planning map identifies
mechanisms worth testing but is not calibrated to V3 and does not implement its
mandatory screening gate. Greedy is optimal in 108/162 model settings; one-step
rollout is optimal in 150. That can motivate a matched V3 planning study, not
retroactively explain every reported PPO failure.

The [evaluation-data investigation](molecular-evaluation-data-expansion.md) now
distinguishes data held out from each current molecular predictor from globally
fresh confirmation. The new handoff adds reported exposure of KCNQ2/FUS/YAP1 in
conditional training and NLRP3 within-target partitions. Those roles need exact
manifest recovery before any new independent-cohort claim. Reported safety
linkages are leads, not automatically compatible new validation measurements.

The next matched side-process study should recover the original source/curve
review, frozen predictors and saved ledgers; freeze the bound-aware 500 nM rule;
first re-score fixed traces, then replay adaptive policies under the same gating,
costs and menus. Counterbalance the Qwen interface and retain greedy and Bayesian
lookahead. A later PPO retraining comparison is separate from both re-scoring and
frozen-policy replay. Independent reviewed campaigns are needed before making
broader scientific claims.
