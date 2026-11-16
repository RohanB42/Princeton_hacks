# Eight-target results and molecular scientific experiments

November 15, 2026. This integrates three user-requested investigations and the
requested extension to eight evaluated targets. The environment runs end to end;
the scientific claim is still **development-stage search under frozen predictors**.
The scores below are normalized eligible archive utility, not measured inhibition,
success probabilities or evidence that generated molecules work biologically.

Follow-up investigations: the [compatible-data experiment](molecular-compatible-data-experiment.md)
adds provenance recovery and cross-source/near-sequence exclusions to the earlier
metadata counts below. Only one 298-row component remains for an active pattern
in a different efficacy context; no independent fitting/evaluation cohort was
certified. The separate [censored-IC50 preparation](censored-ic50-policy-experiment.md)
implements endpoint adjudication, but has no real policy result pending the
location of the reported completed V3/Qwen potency runs. These follow-ups do not
change the eight-target scores or current reward models.

## Eight targets, with the evaluation roles retained

Each cell is a mean across seeds 800–804 at eight scoring requests per run,
including the starting molecule. The original study evaluated six targets.
APOC3 and ANGPTL3 are two newly executed evaluations with the same frozen weights,
predictors, reward, risk screen and query budget. They were chosen and sealed
before their scores were requested. They are an extension, not two previously
missing observations from the original study.

| Target | Evaluation role | Pretraining + PPO | Pretrained staged policy | Pretrained ranking | Random | Greedy |
|---|---|---:|---:|---:|---:|---:|
| DGAT2 | Policy training | 0.8884 | 0.8884 | 0.8884 | 0.4088 | 0.4869 |
| CFB | Policy checkpoint validation | 0.7205 | 0.4872 | 0.7982 | 0.2221 | 0.0000 |
| FGFR4 | Previously inspected development | 0.6943 | 0.7094 | 0.2657 | 0.0000 | 0.1479 |
| F9 | Development | 0.9578 | 0.9578 | 0.9578 | 0.8905 | 0.9597 |
| F12 | Development | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| TTR | Development | 0.6944 | 0.7045 | 0.6843 | 0.6239 | 0.6116 |
| APOC3 | New development | 0.8863 | 0.8771 | 0.8771 | 0.7564 | 0.1983 |
| ANGPTL3 | New development; efficacy-predictor seen | 0.9258 | 0.9258 | 0.9218 | 0.7950 | 0.6145 |

The revised pipeline has higher means than random and greedy on six of eight
targets; F9 slightly favors greedy and F12 ties at zero. The staged pretrained
policy matches or exceeds full PPO on six of eight. PPO improves that comparison
on CFB, which was used for checkpoint selection, and slightly on new-development
APOC3. This supports continued experiments, not a significant general PPO effect.
Pooling training, selection and development targets would obscure their roles.

The eight-target report includes sample SDs, both pretrained controls and the
architecture-only arm. Five shared policy seeds are not forty independent policy
replications. Existing efficacy exposure includes FGFR4, F12 and TTR as well as
ANGPTL3; the complete ledger is in the generalization report. APOC3 has no active
efficacy fit/selection rows but only one row in the historical strict cohort.
Neither new target establishes current-profile applicability or biological transfer.

TTR begins at utility 0.5959, so its terminal full-PPO utility includes only 0.0985
improvement over the start. F12's existing exhaustive catalog audit found all 89
legal compounds fail the unchanged risk screen. It is retained as a zero-result
target rather than dropped or rescued by changing thresholds.

## What executed in this task

| Workstream | Completed experiment | New predictor requests | Measured outcomes read |
|---|---|---:|---:|
| Eight-target extension | Two targets × six methods × five seeds; 60 runs | 480 | 0 |
| Predictor validity | Full inhibition/neurotoxicity metadata applicability and protected-component audit | 0 | 0 |
| PPO attribution | Reanalyzed 360 original runs, query trajectories, checkpoints and offline costs | 0 | 0 |
| Generalization | Exposure ledger, candidate feasibility and assumption-based precision scenarios | 0 | 0 |

The extension used 960 endpoint-head calls. All 60 runs ended at the eight-request
budget with distinct scored proposals. Content seals and every query-journal link
were checked against the run receipts, including monotone archive trajectories.
The two transcripts are APOC3 ENST00000227667 (535 nt) and ANGPTL3
ENST00000371129 (2,926 nt), fetched from Ensembl and hashed. Their full lengths fit
the saved 3,637-position schema. Both use a fixed 48-nt midpoint region with 89
legal designs, matching the earlier development convention. Candidate compound
identities were checked against policy training and validation catalogs.

No new fitting, reward changes, checkpoint selection or risk-final access occurred.
Both added targets now count as inspected development targets. The existing
seven historical reserved targets and 304 sealed risk-final rows remain reserved.

## Three scientific questions and their answers so far

### 1. Are the reward predictors supported in the intended design domain?

The [executed validity audit](molecular-validity-experiment.md) projected metadata
from 174,459 inhibition and 4,900 neurotoxicity rows. At the current human
HepG2/electroporation/4,500 nM/24 h efficacy context, there are zero verified exact
matches to the three active chemistry patterns among parsable rows. This is an
applicability gap; the current optimization result cannot close it.

Changing context reveals real support. Human A431/gymnosis/4,000 nM/48 h has
8,295 and 1,683 rows for the two active 20-mer patterns. But preserving selection,
development, calibration, final and historical reserved roles, then closing
exact-sequence/patent connections, leaves only 1,689 and zero candidate rows.
The remaining candidates still need near-family, cross-source and broader
project-exposure checks. All 2,694 exact active 18-mer matches across contexts
belong to protected components. Merely pooling more rows cannot qualify the full
current grammar and assay context.

**Next experiment:** recover remaining exposure receipts and resolve compound,
species-qualified target and patent-family links before opening permitted
development labels. Then declare a separate retrospective transfer study with
fixed endpoints, compatible observed compounds, common comparison rows and
group-level ranking/error statistics. A one-pattern alternative is a possible
new scope, not an implemented replacement. Keeping the exact current scope
requires new compatible observations or an explicit extrapolation-validation
study. No silent chemistry/context relaxation is planned.

### 2. What does PPO add beyond pretraining and search heuristics?

The [attribution experiment](molecular-ppo-attribution-experiment.md) verified all
360 original receipts and journal chains. On the four original development
targets, mean full-PPO minus staged-pretrained terminal utility is **−0.006283**
at eight requests and **+0.006283** at 32. Full-PPO minus direct pretrained ranking
is +0.109676 at eight but only +0.000482 at 32. Which pretrained deployment rule
is used materially changes the conclusion.

Speed and final quality differ. FGFR4's full PPO has lower final utility than the
staged pretrained policy at eight requests but higher area under its query-quality
curve. CFB's final advantage occurs on checkpoint-selection data. Some 32-request
warm-start runs have different first-eight proposals from eight-request runs;
the two horizons must be treated as separate experiments.

Across five seeds, full training used 27,028 offline predictor requests including
pretraining, PPO and validation, versus 2,880 pretraining requests for the frozen
pretrained policies. Equal deployment-query budgets alone do not establish equal
total resource efficiency. Current saved intermediate validation metrics cannot
reconstruct unsaved policy checkpoints, and the old selector excluded zero-step
pretraining as a candidate.

**Next experiment:** a paired fresh-development ablation with seeds 1800–1804,
identical candidate architecture, construction interface and frozen reward heads;
576/2,304 pretraining examples on the same expanded, qualified training catalog
crossed with PPO prefixes 0/4,096/16,384. The primary contrast is the fixed 16,384
prefix against its exact zero-step initialization at 2,304 examples. The broader
catalog is conditional on metadata/exposure checks; its rows cannot be supplied
by reserved targets or fabricated from repeated requests. Save each prefix's
weights and full RNG/optimizer state. Evaluate fixed prefixes directly
and report validation-selected deployment separately, with zero-step included in
the selector and a fixed tie-break. Include staged pretraining, direct prior
ranking, random, greedy and additional-data supervised controls. Separate fixed
experience comparisons from a matched total-query comparison; extra PPO queries
must be charged. Eight requests is primary; 32 and query-quality AUC are secondary.
Five seeds provide development evidence, not a powered final claim.

### 3. Does improvement generalize to independent targets and measurements?

The [generalization audit](molecular-generalization-experiment.md) found 131
nonempty normalized target identifiers, not 131 verified independent genes.
Seven nonreserved/noninspected large-campaign identifiers have no active efficacy
fit/selection rows; only NOX4 appears in the historical strict chemistry cohort.
Alias/species, patent-family, near-sequence, all-head exposure and applicability
checks remain unresolved. **Zero final groups are presently certified for the
active joint profile.** The eight-target table is a development panel.

**Next experiment:** freeze a complete component/exposure manifest and an adequate
number of independently eligible groups before any final scoring. Prespecify
whether the estimand is policy-only transfer under frozen predictors,
predictor-unseen transfer, or measured recorded-compound ranking. Those require
different exclusions and cannot share a vague “held-out” label. Average regions
within groups and give groups equal weight; preserve paired methods and crossed
target/seed dependence. A final biological panel needs compatible independent
measurements, not just a second model agreeing with the first.

The report gives explicit variance-based planning scenarios: at 20 groups and
ten seeds, target SD 0.05, seed SD 0.02 and interaction SD 0.05 imply an approximate
95% half-width 0.0261 and 80% detectable effect 0.0373. These are assumptions,
not achieved power. The proposed computational meaningful-effect threshold 0.03
requires a final sample-size decision before outcome access. Small-sample RL
uncertainty motivates this caution; see [Agarwal et al.](https://arxiv.org/abs/2108.13264).
No significance-driven addition of targets or seeds is allowed.

## Execution order and decision criteria

1. Finish identity/exposure recovery and select a feasible assay/chemistry scope
   from metadata. Record unresolved support and exclusions explicitly. Stop a
   measured study before outcome access if its cohort or independence fails.
2. Run the paired PPO-attribution development experiment under the existing
   diagnostic scorer. This can answer a computational question while predictor
   qualification proceeds independently; it cannot validate biological rewards.
3. Run a permitted, fixed measured predictor development comparison. If adequate
   fitting cohorts exist, add nested data sizes with fixed assessment groups and
   classical baselines before larger neural fitting. Include all-negative results.
4. Freeze a qualified scorer and the chosen optimizer/control rules, complete
   final-group certification and power planning, then execute confirmation once.
   Report endpoint-specific evidence, costs, all failures and undefined metrics.

This task executed the bounded audits and additional frozen-policy evaluations.
It did not launch this prospective training matrix or change the scientific scope.
The result is a usable computational research system with concrete experimental
next steps; it is not a finalized biological design claim or established PPO
superiority.

## Reproduction and local outputs

`scripts/molecular_eight_target_extension.py` provides separate `prepare`,
`evaluate` and `report` phases. Preparation seals the parent protocol, transcripts,
config, policy hashes, source hashes and runner hash before new target queries.
Use a fresh output directory to repeat the experiment; original receipts refuse
overwrite. The installed RL environment was used as follows:

```sh
MPLCONFIGDIR=/private/tmp/oligo-molecular-mpl PYTHONPATH=src \
  /private/tmp/oligoal-aso-review-20261114-env/bin/python \
  scripts/molecular_eight_target_extension.py prepare \
  --output artifacts/molecular-eight-target-extension-v1
# Same command with evaluate, then report, instead of prepare.
```

Local outputs (ignored; not committed):

- `artifacts/molecular-eight-target-extension-v1/report.md`: eight-target means/SDs.
- `artifacts/molecular-eight-target-extension-v1/eight-target-summary.json`: sealed
  machine-readable means, SDs, roles and actual mean query counts for all six methods.
- `artifacts/molecular-eight-target-extension-v1/runs/`: 60 receipts and journals.
- `artifacts/molecular-ppo-attribution-v1/`: eight-request trajectories, plot,
  paired contrasts, cost and checkpoint audits for the original study.
- `artifacts/molecular-validity-experiment-v1/`: metadata support and exclusions.
- `artifacts/molecular-generalization-audit-v1/`: exposure manifest with all new
  final assignments null, and assumption-based precision scenarios.

Each workstream report supplies its reproducible command, provenance inputs,
scope limitations and invariant tests. No raw dataset, weights or generated run
artifacts were added to version control.

Integrated checks: `make lint format-check import-check test` passed, including
251 core tests (21 new analysis invariants). `git diff --check` passed. The new
evaluation also executed all six methods in the installed RL runtime and passed
the 60-run receipt/journal/budget verification described above. The optional RL
unit suite was not rerun for this analysis-only change; no shared environment or
policy implementation files were edited by these experiments.
