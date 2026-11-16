# From-scratch IC50 adjudication and Qwen recorded-panel pilot

November 15, 2026. This experiment was newly authorized after the completed V3/Qwen
potency runs could not be located. It is a **new retrospective fixed-policy pilot**,
not a reconstruction of an earlier result. The exact-only rule is a constructed
counterfactual; no historical V3 censoring bug is assumed or claimed.

## Question and frozen design

Does crediting threshold-qualified, below-range potency change discovery counts,
policy rankings, or the panels selected by a real Qwen model? We distinguish:

1. Re-scoring exactly the same selected panels under both definitions: a measurement
   definition effect, without any changed acquisition decisions.
2. Running policies separately with the two feedback definitions, then scoring
   both trajectories using the common bound-aware evaluator: an acquisition effect.

The primary operational threshold is apparent absolute IC50 at or below **100 nM**.
The 10 and 1,000 nM cutoffs are prespecified fixed-trace sensitivity analyses.
These are computational screening definitions, not validated clinical cutoffs.
No threshold, target, prompt, model or stopping rule was selected from the pilot's
outcomes. The protocol and all code, source, model and configuration hashes were
sealed before the selected dose-response outcomes were read.

Protocol seal:
`dc27cf2aea172abaa90f849146caa4f61e98c934f780acd1c4f16b3981c02de0`.

## Source, campaign selection and exposure

The pinned ASO Atlas dose-response release contains 99,821 rows. Metadata selection
used only HELM, source/table/compound identifiers, doses and assay context. The
three genes F7, STAT3 and NLRP3 were fixed first because they were already used in
historical development and experimental-selection training. They are not fresh
held-out target groups. We excluded the seven historical reserved targets and
all patent IDs and exact natural sequences represented in the 304 sealed risk-final
records, without reading those risk outcomes.

For each gene, select the largest single patent/table/context cohort with at least
four distinct positive doses and at least eight complete molecular panels sharing
the exact same dose grid. Complete panels require one source row per dose; duplicate
or ambiguous dose records are excluded from metadata, not averaged into invented
independent replicates. Keep at most 24 panels by a fixed hash of compound identity.
Ties in campaign size are broken by context hash. The chemistry parser and metadata
completeness rules are fixed. No molecule was selected because it had a favorable
response, successful fit or useful censoring category.

| Gene | Source patent / table | Context | Dose grid, nM | Selected panels |
|---|---|---|---|---:|
| F7 | US20150031747A1 / 28 | Human Hep3B, electroporation, 16 h | 50, 150, 440, 1,330, 4,000 | 24 |
| STAT3 | US20160348104A1 / 15 | Human HUVEC, electroporation, 16 h | 39.1, 156.3, 625, 2,500 | 24 |
| NLRP3 | US20240191233A1 / 27 | Human THP-1, electroporation, 24 h | 16, 63, 250, 1,000, 4,000 | 15 |

This creates **63 recorded panels and 291 dose-response observations**. Their source
IDs were sealed before the outcome-column projection. Only these selected rows
entered the private recorded oracle. The pilot does not fit a transferable efficacy
model or use unrelated held-out labels to train a policy. It does not establish
absence of related compounds from all prior studies; development exposure is
explicit. The existing molecular-design predictors, screening threshold and
construction environment are not involved.

## Operational curve definition

The source reports normalized inhibition percentages. We estimate an **apparent
absolute 50% crossing**, not a relative half-maximal response. Those definitions
are different; see the [Assay Guidance Manual](https://www.ncbi.nlm.nih.gov/books/NBK91994/?report=printable).

The frozen procedure is:

- Retain raw responses. Missing/nonfinite or outside [-20, 120] percentage points
  produces an unresolved panel; no clipping is performed.
- Fit an increasing isotonic response by unweighted PAVA. If any response needs
  more than 15 percentage points of adjustment, mark it unresolved. This tolerance
  is a declared operational diagnostic choice, not validated assay uncertainty.
- If the fitted response at the lowest tested concentration is at least 50%, retain
  an upper bound at that concentration. Never invent an extrapolated IC50 point.
- If the fitted response at the highest concentration is below 50%, retain a strict
  lower bound. This does not prove a biological maximum below 50%.
- Otherwise estimate the crossing by interpolation linear in log concentration
  between the two bracketing fitted responses. Preserve the bracket as well as
  the estimate; it is not an exact biological constant or confidence interval.
- Repeat adjudication with zero permitted isotonic adjustment as a prespecified
  strict-monotonicity sensitivity. This re-scores fixed traces and does not tune
  or rerun the policies.

Raw untreated/positive controls, viability measurements, independent replicate
uncertainty and patent extraction accuracy have not been established by this
pilot. Thus the result concerns an operational interpretation of reported curves,
not validated biological potency. Isotonic fit acceptance alone is insufficient
for that stronger claim.

Under both rules, an in-grid estimate below the cutoff is a success; a strict
lower bound at/above it is a threshold failure; other unresolved results remain
unknown. The constructed **exact-only** rule gives no hit credit to a qualified
upper bound and feeds that nonhit label to its policy. The **bound-aware** rule
credits such a bound when its upper endpoint is at/below the cutoff. Only that
case changes the success label. Unknown curves are not silently converted into
biological failures in either rule.

## Policies, costs and actual Qwen execution

Each campaign has three common-start seeds (1900, 1901, 1902), two common randomly
selected starting panels, and a fixed eight-panel cap, including the starts.
The primary outcome is the number of **new** credited discoveries in the remaining
six purchases. Total credited discoveries, unknown counts and all individual
trajectories are also retained.

One purchase reveals a complete historical dose panel. Every selected panel in a
campaign has the same dose count, so panel budgets also match dose-readout costs
within that campaign. We report both cost units. This experiment chooses molecules
for complete panels; it does not compare choosing individual doses or assay types.
There are no new wet-lab measurements.

Four policies run under both feedback definitions:

- Uniform random without replacement.
- Greedy highest posterior mean of a Beta-Bernoulli hit model in four fixed GC
  fraction bins, with Beta(1,1) priors and seeded uniform ties.
- Bayesian group Thompson sampling from that same exact conjugate model. Unknown
  panels do not update it. This is a simple group-success model, **not COBALT or a
  continuous censored-Gaussian-process optimizer**.
- Actual local **Qwen2.5-3B-Instruct**, MLX four-bit quantization, frozen weights.
  No Qwen fine-tuning or PPO training is performed. A common prompt supplies
  label-free molecular sequence/chemistry descriptors and only previously purchased
  curve interpretations. It never receives unpurchased responses or pool-level
  outcome summaries.

Qwen is `mlx-community/Qwen2.5-3B-Instruct-4bit`, revision
`4f83f8f146fdf28b512a06562b671d7af4fab457`, tied to the official Qwen base in the
runtime receipt. The model is licensed under the Qwen research license; no model
weights are redistributed by this work. The source model/card and quantization
receipts are under `artifacts/ic50-qwen-runtime-v1/`.

At every Qwen choice, its next-token logits are masked to the legal candidate
letters and greedy argmax chooses one token. All letters must have distinct
single-token encodings. A fixed seeded permutation maps display letters to actual
panels; the same mapping is used in both feedback arms. This prevents a fixed
letter preference from always identifying the same physical compound across
seeds, but does not eliminate all presentation bias. Every prompt and response is
saved with hashes and permitted-action metadata. There is no repair retry,
heuristic fallback or invented Qwen answer. An invalid response or inference
failure aborts the arm and is recorded.

The design requires 72 policy runs, 576 charged panel purchases (repeated across
arms), and **108 actual one-token Qwen choices**. The three seeds vary starts and
stochastic policies, not the Qwen model weights; they are not three independently
trained language models. Campaigns, seeds and dose points are not pooled as
independent biological replicates. Statistical significance and broad optimizer
superiority are not claimed.

## Reproduction and implementation

- `experiments/ic50_qwen/core.py`: operational curve adjudication, policy views,
  simple comparator policies, query budgets and fixed/adaptive trace accounting.
- `experiments/ic50_qwen/run.py`: metadata selection, protocol sealing, filtered
  selected-row outcome access, actual Qwen adapter and reporting.
- `tests/test_ic50_qwen_experiment.py`: 17 invariant cases for bounds, log-dose
  interpolation, unknowns, QC, policy information isolation, costs, common random
  traces and prohibition of silent Qwen substitution.

Use a new output directory; sealed artifacts refuse overwrite. Preparation and
adjudication use the existing Atlas science runtime; model execution uses the
isolated MLX runtime, with Metal access enabled by the parent:

```sh
PYTHONPATH=src:. /private/tmp/oligoal-atlas-rnafm-20261114/.venv-atlas/bin/python \
  -m experiments.ic50_qwen.run prepare --output artifacts/ic50-qwen-from-scratch-v1
# Same command with adjudicate instead of prepare.
HF_HOME=/private/tmp/oligoal-qwen-hf-cache PYTHONPATH=src:. \
  /private/tmp/oligoal-qwen-ic50-env/bin/python -m experiments.ic50_qwen.run evaluate \
  --output artifacts/ic50-qwen-from-scratch-v1
# Report with either Python runtime using the report phase.
```

Model and dataset bytes, assay roles, source code, prompt and runtime receipts are
recorded. The private oracle contains all 63 selected curves but is never a policy
input. All policies commit their complete trajectories before aggregate results
are inspected. Local generated outputs, raw curves and weights remain ignored.

## Later handoff discovered during execution

After the pilot protocol was sealed, its selected outcomes loaded and Qwen calls
started, the user supplied a handoff describing a different, unpushed experiment
on Harrison's machine (`codex/experimental-selection-llm-agent`, commit `30ac0e9`).
That study reportedly used Qwen3-4B, a two-stage $500 inhibition screen / $2,000
potency assay, a $15,000 budget and an absolute-IC50 cutoff of 500 nM. Those are
materially different from this pilot's Qwen2.5-3B, direct full-panel purchases and
100 nM operational primary cutoff. The later handoff does not retroactively turn
this newly built pilot into a reproduction of that study.

The handoff also describes a later NLRP3 training/development/test allocation that
was unavailable during this pilot's metadata audit. Its exact source-row overlap
requires the original manifest. This is an additional exposure limitation, not
permission to call NLRP3 untouched or to move known final records into policy
feedback. The original checkout, commit objects and exact split manifest were not
accessible here. Therefore the selected NLRP3 records cannot be certified as clean
development or independent test data. No pilot outputs may be reused for fitting
or tuning future policies. The existing frozen pilot is preserved; its threshold and candidate
membership are not changed after observing outcomes to match the new narrative.

The original sealed protocol retains its pre-handoff wording. The separate
`late-handoff-scope-amendment.json` records when this information arrived and
supersedes its development-only scope claim. Likewise the generated report's
generic final-label exclusion sentence refers to the exclusions originally audited;
it does not establish exclusion from Harrison's unavailable NLRP3 partition.

## Completed results

All **72 arms completed**, with **108 actual Qwen choices**, no invalid actions,
inference failures, retries or heuristic substitutions. Costs were 576 charged
panels and 2,688 dose readouts across repeated arms, drawn from the same 63 panels
and 291 distinct recorded source observations. Qwen generation took 369.6 seconds
in total (median 3.72 seconds per choice). This was local inference with no API bill.

The primary endpoint below is mean **new discoveries among six selected panels**,
after two common starting panels; all eight panels consume budget. Each mean uses
three matched seeds. Values are counts, not success probabilities.

| Target | Policy | Exact-only | Bound-aware |
|---|---|---:|---:|
| F7 | Random | 1.667 | 2.000 |
| F7 | GC-group greedy | 1.667 | 2.000 |
| F7 | GC-group Thompson | 0.333 | 0.333 |
| F7 | Qwen2.5-3B | 1.667 | 2.000 |
| STAT3 | All four policies | 0.000 | 0.000 |
| NLRP3 | All four policies | 0.000 | 0.000 |

F7 contains six in-range estimates qualifying at 100 nM and two additional
upper bounds of at most 50 nM. Thus the full eligible pool changes from 6/24 to
8/24 when those bounds are credited. STAT3 and NLRP3 have **no qualifying panel**
at the frozen 100 nM threshold. Their zero discoveries do not distinguish policies.
One NLRP3 curve is unresolved under primary QC; an unresolved curve is not a proven
inactive molecule. Full primary curve counts are F7: 21 interpolated, two upper
bounds, one lower bound; STAT3: 24 interpolated; NLRP3: 14 interpolated, one unresolved.

For F7, re-scoring each exact-only trajectory with the bound-aware evaluator adds
0.333 discoveries per run for every policy. After scoring both adaptive arms with
that same evaluator, acquisition gain is **0 for Qwen, random and greedy**, and
**-0.333 for Thompson**. Qwen's increased reported discovery count is therefore
an adjudication effect, with no measured improvement in acquisition yield here.
Neither the primary ordering nor Qwen's tie with random and greedy changes.
The GC-group greedy comparator is a simple Beta-bin policy, not the original V3
Ridge-based greedy algorithm.

All nine paired Qwen trajectories change order or membership across rules, including
STAT3 and NLRP3 where no qualified censoring labels change. The observation includes
the active rule name, so rule framing changes the prompt even when paid hit labels
are identical. These trajectory differences cannot be attributed exclusively to
changed reward feedback. There is no acquisition gain to explain away, but this
is a design limitation for any future causal interpretation of action changes.

### Prespecified sensitivity analyses

Re-scoring fixed traces at 10 nM produces no credited discoveries anywhere; the
F7 upper bounds at 50 nM cannot resolve success at 10 nM. At 1,000 nM the pools
become nearly saturated: F7 23/24, STAT3 24/24, NLRP3 13/15 qualify. These are
sensitivity analyses of previously chosen traces, not policies retrained or
rerun to optimize the alternative cutoff.

For the bound-aware feedback trajectories, mean new hits at 1,000 nM are:

| Target | Random | GC-group greedy | GC-group Thompson | Qwen |
|---|---:|---:|---:|---:|
| F7 | 5.667 | 5.667 | 5.333 | 5.333 |
| STAT3 | 6.000 | 6.000 | 6.000 | 6.000 |
| NLRP3 | 5.000 | 4.667 | 5.000 | 5.333 |

Requiring zero isotonic adjustment leaves primary 100 nM hit counts unchanged,
including both F7 upper bounds, but increases unresolved panels. It makes three
F7 and six NLRP3 pool panels unresolved. At 1,000 nM it reduces NLRP3 mean new hits
to 4.000 random, 3.667 greedy, 3.667 Thompson and 3.000 Qwen. This reversal of the
small apparent Qwen advantage under a stricter curve rule argues against a robust
model-superiority claim. Unknowns remain unknown rather than asserted failures.

### Post-hoc interface diagnostic

Requested after the later handoff, log-only analysis found Qwen selected the first
available displayed letter **0/108 times**; uniform selection would have a mean
per-choice probability of 6.71% given the changing menus. The observed letter counts
were E:5, F:8, G:4, H:4, I:6, J:13, K:1, N:6, O:6, P:12, S:5, T:3, U:6, V:12,
W:12, X:5. This does not reproduce the other model/interface's reported first-letter
attraction. Nor does it establish absence of presentation bias: avoidance of early
letters and other preferences remain possible, and no matched permutation test
was run. Adaptive choices are correlated; these counts are not an independent
binomial significance test.

### Evidence and limits

The useful positive finding is that two real reported F7 dose panels cross 50%
already at the first tested dose and materially change credited discovery counts.
This bounded experiment does **not** establish Qwen superiority, policy ranking
reversal caused by censoring, new biological validation, independent generalization,
or reproduction of the original V3/Qwen3-4B two-stage benchmark. The sample comprises
three reused target campaigns, only one informative at the primary threshold,
three common-start seeds and a simple comparator family. No significance claim is
justified. A stronger prospective benchmark would need its assay objective and
clean partitions fixed before outcomes, enough distinct campaigns informative at
that objective, stronger matched comparators and a menu-permutation control.

Durable local evidence lives under `artifacts/ic50-qwen-from-scratch-v1/`:
`protocol.json`, `late-handoff-scope-amendment.json`, `results.json`, `summary.json`,
`completion-audit.json`, `runs/` and `calls/`. The completion audit verifies all
72 unique arms, common starts, eight unique panels per arm, identical random
trajectories across feedback rules, all 108 sealed request/response pairs, legal
choices and charged costs. `experiments/ic50_qwen/audit.py` reproduces that audit
without model calls or new assay reads. Original frozen source/model hashes remain
unchanged. The 17 scientific invariant tests and owned-file Ruff checks pass.
