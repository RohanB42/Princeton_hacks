# ASO Atlas × RNA-FM: chemistry-aware transfer and sequential acquisition

**Prepared:** November 14, 2026, 12:29 EST / 17:29 UTC.

**Repository baseline:** `42bb9b8`.

**Status:** research proposal informed by source review and local, label-blind feasibility counts. No Atlas model training or new acquisition experiment has been launched. Settings below are proposed defaults; freeze the final cohort, manifests, compute allocation and analysis before confirmatory evaluation.

## 1. Recommendation and intended contribution

Continue the RNA-FM work as an independent ASO study. The principal question is:

> With the same historical ASO training data and the same budget of newly revealed measurements, does chemistry-aware RNA-FM adaptation improve prediction and experiment selection for a target absent from source training?

Separate three possible contributions: better prediction, better transfer to a new campaign, and better sequential selection. An improvement in one does not establish the others. The desired final result is a measured reduction in new-campaign assay requirements, with uncertainty across targets, against strong source-trained classical and batch-selection baselines.

The architecture is not itself a novelty claim. OligoAI already combines a pretrained RiNALMo encoder, position-specific chemistry, target context and experimental conditions; its paper reports model-guided experimental screening on KCNT2. Its published screening comparison is not equivalent to our proposed repeated select–reveal–retrain experiment. We should investigate that narrower distinction, not claim to introduce foundation models or model-guided screening to ASOs. [OligoAI paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13427547/).

New-target transfer alone also has prior art, including a published small-data study using target-specific offset calibration. Include a cheap calibration comparator rather than assuming adaptation requires a large model. [Small-data ASO transfer study](https://www.frontiersin.org/journals/systems-biology/articles/10.3389/fsysb.2026.1921636/full).

The plausible research contribution is a transparent, cost-accounted comparison of chemistry-aware transfer and sequential batch acquisition under stringent target/patent isolation. This remains a research opportunity, not a verified first. A limited literature search cannot establish exclusivity.

## 2. What the existing evidence actually supports

Our Huesken comparison at 200 labels gave Pearson r of 0.4910 for one-hot Ridge, 0.3374 for frozen RNA-FM/Ridge, 0.2801 for a frozen neural head, and 0.4196 for LoRA plus that head. LoRA improved its matched head control but lost to one-hot on the primary learning-curve statistic in all five seeds. Frozen acquisition geometry showed no consistent advantage. Preserve these results as a separate siRNA study; they motivate a new hypothesis but do not predict an ASO win. [Project snapshot](updates/2026-11-14-1150-est.md).

Reusable components are checkpoint verification, base-model loading, Q/V weight parametrization, adapter integrity checks, protected label access, matched-budget reporting and provenance. The input pipeline needs real changes: current `FrozenRNAFM` requires exactly RNA1 and RNA2, rejects modified bases and produces 1,280 pooled duplex features. `RNAFMLoRAPredictor` also hard-codes paired strands and a two-strand head. A single-stranded ASO is not a drop-in input. [Representation code](../src/oligo_engine/representations/rnafm.py), [LoRA code](../src/oligo_engine/models/rnafm_lora.py).

Keep the verified general RNA-FM checkpoint; initialize fresh ASO adapters. Do not initialize the main experiment from Huesken-trained adapters. RNA-FM's original self-supervised training is an RNA representation prior, not ASO chemistry or efficacy training. [Official RNA-FM repository](https://github.com/ml4bio/RNA-FM).

## 3. Cohort: available data versus usable campaigns

The released Atlas in-vitro table has 174,459 rows, of which 173,286 have resolved HELM. Patent-grouped folds are endpoint-specific; matching fold numbers across tasks does not produce a joint split. The single-dose inhibition and dose-response tables also represent different experimental objects. [Atlas release card](https://huggingface.co/datasets/barneyhill/aso-atlas-2/blob/main/README.md), [fold definitions](https://huggingface.co/datasets/barneyhill/aso-atlas-2/blob/main/folds/README.md).

Local counts below were computed from the committed prepared table on November 14. They use `analysis_eligible` and group metadata only, without selecting on efficacy values:

| Quantity | Count |
|---|---:|
| Current eligible in-vitro assay rows | 143,646 |
| Distinct exact HELM strings in those rows | 134,390 |
| Non-null target identifiers | 134 |
| Patent identifiers | 203 |
| Rows missing delivery method | 4,909 |
| Rows missing treatment duration | 4,311 |
| Rows with human cell-line species | 138,569 |

These 134 target identifiers are not yet a verified canonical gene count. The conservative dose-aware filter substantially reduces the target coverage relative to the full source. No target transcript sequence or binding coordinate is present among this table's columns.

Define a provisional campaign by `(patent, table, target, cell line, species, delivery method, duration, dose)`. Grouping the current eligible rows with missing values retained gives:

| Minimum distinct exact HELMs per provisional campaign | Campaigns | Target identifiers | Patents |
|---|---:|---:|---:|
| 100 | 98 | 28 | 39 |
| 200 | 65 | 17 | 24 |
| 400 | 24 | 12 | 13 |
| 1,000 | 4 | 4 | 4 |

These are planning upper bounds before chemistry parsing, identity normalization and overlap exclusions. Missing metadata must not be interpreted as proof of identical assay conditions. Table boundaries may also split a real screen. Thus, 1,000- or 5,000-label budgets are plausible for pooled source learning, but not broadly supported for individual assay-consistent target campaigns. Do not silently merge incompatible campaigns to enlarge their pools.

### Cohort contract

- Start with single-task in-vitro inhibition. Target is original `Inhibition_pct`, in percentage points, conditional on dose and available assay context. Retain out-of-range measurements; no sigmoid output or automatic clipping. RMSE and MAE remain on the original scale.
- Require finite endpoint, positive dose for the primary treatment cohort, source patent and parseable supported chemistry. Audit zero-dose controls separately; the existing generic eligibility flag permits zero and is not the final cohort.
- Require known cell/species/delivery/duration for primary campaign comparisons when enough data remain. Report attrition. Any missing-context extension is explicitly separate and uses missingness indicators.
- Record assay ID, exact HELM, parsed chemistry identity, natural-base projection, target mapping, context and source row IDs. Compound IDs must be qualified by patent; do not assume globally unique identifiers.
- Group repeat measurements and compound identities before splitting. Do not average across doses, delivery methods or endpoints. If exact duplicate assay rows are collapsed, distinguish extraction duplicates from biological replicates and retain the source mapping.
- Reserve targets by metadata before examining model outcomes. Select sufficient campaign sizes, not favorable label distributions or easy prediction targets.

All eligible local HELMs begin with `RNA1{{...}}$$$$`; some contain `[5meC]`, modified sugars and linkage tokens. This calls for a pinned, tested normalization/parser path. Preserve raw strings. Inspect the upstream adapter before reproducing its normalization; never solve it by deleting punctuation or modifications without a mapping audit. [Local preparation audit](aso-atlas-data-cleaning-2026-11-14.md).

## 4. Two evaluation tracks, with different claims

### Track A: source-task prediction and benchmark comparability

First reproduce one feasible released Atlas classical efficacy baseline using its actual adapter, aggregation, model settings and fold joins. This is a new Atlas reproduction check; it does not close the unresolved OligoGym seven-dataset Gate 1.

For method comparisons, use common rows and identical inputs for all arms. Follow the official endpoint folds only after joining normalized model inputs to source IDs and accounting for unmatched or many-to-one rows. If we choose a stricter assay-consistent cohort, report it as a new subset analysis, not exact published reproduction. The imported fold README has an unresolved OligoAI size-summary discrepancy; the actual supplied file has 117,780 rows.

Proposed pooled training budgets: **50, 200, 1,000 and 5,000 labels**, then 20,000 and full eligible training data only after profiling. Use nested random selections shared across models. Every fitting/validation label counts. Start with one development partition and three seeds; expand only the narrowed comparison to all relevant folds and five seeds. Epoch selection and feature fitting remain inside acquired training data.

Patent holdout tests patent-distribution transfer. It does not automatically test unseen target genes or unseen patent families.

### Track B: new-target adaptation, the primary research setting

Construct explicit source, development and final target groups before source adaptation. Withhold each evaluation target across **every dataset and endpoint used by the source model**. Also remove its evaluation patents and exact compounds/base-sequence equivalents from source training. Audit shifted sequence neighbors and chemistry variants; predeclare a stricter sequence-cluster sensitivity split. If patent families are not resolved, call it patent-ID isolation, not family isolation.

A target's campaign is split once into an eligible acquisition pool and a permanently held-out test set, grouped by compound and the frozen sequence-family rule. Target labels in the pool can then be revealed for adaptation. “Unseen target” means absent during source training; after adaptation it is a few-shot target, not zero-shot generalization.

Proposed pilot: campaigns with at least 400 supported distinct compounds, approximately 20% held out, and at least 200 pool compounds plus 80 test compounds after grouping. Budgets **0, 50, 100 and 200**; zero labels is the source-only transfer baseline. Five paired acquisition/initialization seeds per campaign. All arms use the same split and initial 50 IDs.

Choose development targets and final targets without using outcomes. The preliminary count of 12 target identifiers with large campaigns is a ceiling, not a promise of adequate power. Aim for at least eight final target groups after development allocation and exclusions; fewer supports an explicitly exploratory pilot. Use development target-level variance for a prospective power analysis before a larger confirmation. Five seeds on one gene do not become five independent genes.

Use one source checkpoint per outer target partition, excluding all targets held out in that partition. Within the same partition all methods receive the same source labels. Source hyperparameters are selected using source-internal patent groups and separate development targets. Checkpoint provenance must make supervised overlap auditable. A released OligoAI checkpoint with unknown training overlap is not a clean comparator; use fold-excluded retraining or label it an external, potentially contaminated diagnostic.

## 5. Proposed chemistry-aware model and controls

Represent an ASO as aligned per-position tracks: canonical parent base for RNA-FM, original modified-base identity, sugar identity, adjacent backbone identity, terminal markers and a length mask. Encode PS/PO explicitly; do not invent stereochemistry absent from the source. Unsupported monomers fail or enter an explicitly documented unknown category, never silently become ordinary RNA.

RNA-FM sees only the documented natural-base projection (for example T→U, with the original chemistry retained separately). This is an approximation for DNA-rich gapmers. Test that chemistry changes alter chemistry features even when natural-base embeddings match.

Start with token-level fusion: concatenate the RNA-FM token state and small chemistry embeddings, apply a modest shared fusion layer, then masked pooling. Combine the pooled representation with log-dose, delivery method, cell/species and duration features. Do not use patent IDs or raw target-name IDs as predictive shortcuts. Fit vocabularies/scalers from source training and currently acquired rows only; reserve unknown tokens.

Token-level chemistry fusion is necessary to retain position and gapmer pattern. Use late pooled fusion as an ablation. The initial model is **ASO + assay context**, not a target-accessibility model. Add transcript context only after verified transcript versions, coordinates, strand orientation and ambiguous-match handling are available, and give equivalent context to the comparator models.

| Arm | Inputs and adaptation | Purpose |
|---|---|---|
| C0 | Source mean/context-only regression | Detect gains explained by assay context |
| C1 | Positional base/sugar/linkage features + Ridge and XGBoost | Strong inexpensive baselines |
| N0 | Small trainable sequence/chemistry CNN + matched context | Test whether a large pretrained encoder is needed |
| F0 | Frozen RNA-FM + matched head/context, chemistry removed | Chemistry ablation |
| F1 | Frozen RNA-FM + trainable chemistry/fusion/head/context | Main frozen control |
| L1 | RNA-FM Q/V LoRA + the identical chemistry/fusion/head/context | Main adaptation arm |
| R0 | Architecture-matched random frozen encoder + chemistry/head | Diagnostic of pretrained features, not a complete training-from-scratch comparator |

At low budgets retain one-hot Ridge, which won our Huesken comparison. Tune classical and neural baselines on development data with declared search and compute budgets. Match the head, initialization and optimization candidates between F1 and L1. Proposed LoRA starting point is rank 4, alpha 8; choose learning rate and training duration using source/development validation, not historical Huesken test performance or final Atlas campaigns. Do not run the full Cartesian product immediately: C0/C1/F1/L1 first, then causal ablations on development targets.

The main experiments reuse a single-task efficacy model. Multi-task losses, dosage-response fitting, larger encoders and transcript context are independent extensions.

## 6. Two-stage transfer and honest label accounting

Stage 1: adapt on **source-target ASO labels only**, with chemistry and assay context. Stage 2: for each new target and budget, reset to that source checkpoint and adapt using only the revealed campaign labels. Do not train a 200-label adapter and use it to select the 50-label batch.

Compare four transfer procedures: source-only prediction; source predictor plus a target-specific offset estimated from acquired labels; source model plus a small residual head; and further target-specific LoRA. A source-trained XGBoost/Ridge comparator gets the same historical data, with its target calibration/residual adaptation selected on development targets. Also include target-only classical learning to quantify the value of historical data, without treating it as the sole FM comparator.

Log three distinct quantities:

1. **Source measured labels** used for ASO post-training and source validation.
2. **New-target measured labels** used for adaptation, internal validation and acquisition.
3. **Compute** for source training, per-target fitting and selection, plus dataset overlap identities.

A model trained on 100,000 source measurements and 50 new-target labels is not a 50-total-label model. Any savings claim must specify marginal new-target measurements and matched access to historical labels. Report amortized source cost across multiple campaigns separately; do not erase it.

## 7. Acquisition experiments after predictor/transfer gates

Begin with fixed source-adapted representations and cheap heads. This allows acquisition analysis without repeatedly training the full encoder. Then test encoder updates at prescribed acquired-label checkpoints only if their predictive benefit warrants the cost.

For the narrowed classical and FM predictors compare random, top epistemic uncertainty, sequence/chemistry diversity, and **MaxDet** batch selection. Add integrated variance reduction/BAIT if feasible. These methods have established regression benchmarks; adopting them is a stronger baseline, not algorithmic novelty. [Batch active-learning framework](https://www.jmlr.org/papers/v24/22-0937.html).

MaxDet should use a conditional predictive kernel updated against labeled examples and within-batch selections, rather than merely taking large marginal variances. Use consistent last-layer/kernel constructions when comparing feature spaces. Fit regularization/scaling from permitted data; variance-reduction reference points can come from the eligible training pool, never the held-out test set. Pin the implementation revision and audit unique eligible selections, because the public implementation documents fixes involving accidental selection of training points. [BMDAL code](https://github.com/dholzmueller/bmdal_reg).

Separate two ablations:

- **Geometry:** fix the downstream predictor and acquisition algorithm; change only classical versus frozen/source-adapted/task-adapted acquisition features.
- **Predictor–policy interaction:** compare the selected classical and FM models under random and the selected active policy, on identical campaigns and budgets.

Proposed target campaign schedule: initial 50, batches of 25, report every batch through 200. Use three-to-five independently fitted heads/ensembles or a declared Bayesian head for uncertainty. Report uncertainty type and training-internal reliability checks; FM embeddings and LoRA do not inherently provide calibrated uncertainty. Distinguish epistemic uncertainty from irreducible assay noise.

Two decision objectives require separate studies. Model-improvement acquisition is scored on held-out predictions. Hit-discovery acquisition (static ranking, greedy predicted potency, or UCB) is scored on newly revealed pool measurements, with fixed hit criteria within comparable assays. A static source-ranked list is an essential comparator to show whether sequential updating adds value over ranking once. Test labels never become rewards or stopping feedback.

## 8. Primary metrics, statistics and decision rules

Primary transfer endpoint: **target-macro normalized area under the RMSE-versus-label curve over 50–200 labels**, comparing the development-selected adapted model with the strongest development-selected source-trained classical comparator. Lower is better. Report Pearson r and Spearman within campaigns, MAE, raw learning curves and zero-shot performance alongside it. Aggregate seeds within campaigns, campaigns within targets, then targets equally; do not let a large patent dominate the result.

Use a paired target-cluster bootstrap, retaining all methods and seeds within each sampled target. If targets share evaluation patents/families, use connected groups as the sampling unit or report the dependence explicitly. Predeclare undefined-correlation handling; keep RMSE results for those campaigns. Report all per-target differences and the number of independent groups. For a confirmatory study, freeze one primary contrast; apply Holm correction within the declared secondary contrast family. Development results remain descriptive.

**Label-efficiency endpoint:** before final outcomes, fix a common target quality per campaign. Proposed relative rule is RMSE no worse than 1.10 times an independently fitted full-pool classical reference, using the same reference for every arm. The reference uses eligible training labels only and is withheld from acquisition and tuning. Absolute application-specific thresholds can replace this only if justified and frozen on development data.

Record first observed checkpoint crossing without interpolation. Unreached thresholds remain right-censored, never assigned a fabricated crossing at 225 or 1,050. Report crossing proportions and restricted labels-to-threshold through the cap; explain that a restricted cost is not proof that censored campaigns reached the target. Include a sustained-crossing sensitivity analysis for noisy curves. A weak full-pool reference makes the practical threshold weak; expose this rather than filtering campaigns after results.

Proposed practical target: **at least 20% lower marginal label cost**, with a paired interval excluding zero savings, across independent target campaigns. This is a project decision threshold, not an established biological constant. A positive AULC alone does not meet it. A confidence interval excluding zero but not excluding effects below 20% supports evidence of some savings, not certainty of at least 20% savings.

To claim that pretraining contributes, L1 must beat both matched F1 and a strong classical/small-network control under fair data access. To claim selection contributes, an active policy must improve on random for the same predictor. To claim discovery contributes, demonstrate measured pool hit enrichment or lower measured screening cost under a separately frozen objective. Surrogate optimization cannot establish improved molecules.

## 9. Dependency-ordered implementation and acceptance gates

These are proposed work packages, not active agents or launched jobs. Keep new files under an independent `atlas` study namespace; an integrator owns shared interfaces, dependencies and lockfiles.

| Gate | Proposed ownership/files | Acceptance and decision |
|---|---|---|
| A0: cohort and identity | `src/oligo_engine/atlas/data.py`, `chemistry.py`, `splits.py`; Atlas tests | Pinned parser, round-trip monomer mapping, immutable IDs, attrition, campaign counts, source/target/compound exclusion manifests; no silent parsing fallback |
| A1: anchor and controls | `atlas/baselines.py`, `configs/atlas/`, baseline report | Reproduce a feasible source baseline or document discrepancy; context-only, Ridge and XGBoost run on common splits; source-trained calibration comparator works |
| A2: ASO FM adapter | `representations/aso_rnafm.py`, `models/aso_rnafm.py`; dedicated tests | Single-strand support, chemistry-position alignment, masked pooling, frozen-feature parity, changed adapters/unchanged base weights, strict cache isolation |
| A3: source scaling | `atlas/prediction_study.py` and report | Matched random learning curves; source-data/compute accounting; freeze finalists using development outcomes only |
| A4: target transfer | `atlas/transfer_study.py` and frozen manifests | Held-out targets excluded before all source training; source-only/offset/residual/LoRA comparisons; multiple independent campaigns; honest negative results |
| A5: sequential selection | `atlas/acquisition_study.py`, MaxDet adapter/tests | Matched oracles, batch costs, no test or unrevealed-label feedback, paired random/active comparison, explicit censoring |
| A6: confirmation/package | report, figures, environment receipt and run commands | Locked final protocol, regenerated figures, all exclusions reported, claim limited to observed endpoints/tasks |

Required scientific tests include: held-out-label poisoning, unrevealed-label prefix invariance, source checkpoint exclusion checks, same-compound split exclusion, dose-group cost accounting, unknown-monomer behavior, terminal-linkage alignment, no synthetic second strand, complete model reset, fresh adapter cache identities, and no full-pool-reference exposure to acquisition.

## 10. Compute plan and stop rules

Profile the actual ASO implementation before committing to throughput. Our successful small CPU LoRA run does not establish MPS support or 100,000-row feasibility. Test forward/backward, parametrized attention and numerical parity on the installed CPU/MPS runtime. If MPS is incompatible, retain CPU for small development checks and evaluate an explicitly budgeted GPU run separately.

Cache frozen encodings by unique natural-base sequence plus checkpoint/tokenization/layer identity; retain chemistry and assay features separately. Token caches are needed for position-wise fusion. As a storage estimate, 134,390 sequences × 20 positions × 640 features × 4 bytes is about **6.9 GB** before overhead; pooled vectors are about **344 MB**. These estimates assume length 20, float32 and no sequence deduplication; use sharded disk caches and measured lengths. Adapted embeddings must be keyed by adapter state and cannot reuse the frozen cache.

Use an initial profile at 256 sequences and 50/200/1,000 labels. Cap source-development training at a declared wall time; narrow configurations before five-seed transfer sweeps. Exact dense GP covariance over the whole Atlas pool is not a default: use cheap heads, ensembles or justified low-rank kernels and report approximations.

Stop expansion if parsing leaves too few independent campaigns, if only assay metadata explains gains, if L1 fails to improve the matched controls, or if source/target overlap cannot be resolved. Preserve those findings. A worthwhile negative result would show that chemistry-aware classical transfer captures the available signal and that larger pretrained encoders do not buy measured-label efficiency under this protocol.

## 11. Deferred extensions and final research artifact

Dose selection is a particularly relevant later extension: acquiring `(compound, dose, assay)` or a dose panel can be a different experimental-design problem from molecule selection. It needs curve-level grouping, cost units, censoring-aware potency estimation and a new frozen protocol. The 99,821 dose-response rows are not 99,821 independent compounds or ready-made IC50 labels.

Multi-task training comes later, with a global source/test exclusion map across all endpoints, validated compound linkage, masked losses, task weighting and endpoint-specific scales. The reported source-ID cross-category linkage is not proof that assays or molecules are interchangeable. Missing endpoints remain missing, and clinical safety is not an output.

RL comes after strong acquisition and static-ranking baselines. The unmerged current RL pilot edits siRNA sequences against a frozen surrogate; it cannot be reused unchanged as target-valid ASO design. Any ASO design environment needs transcript/complementarity constraints, supported chemistry actions, out-of-distribution checks and independent measured evaluation. No target sequence means no defensible de novo target-specific design claim.

The minimum useful artifact is a reproducible **source-data × new-target-budget × acquisition-policy** comparison with target-level uncertainty, provenance, costs and honest limits. The central figure should show how much new experimental data is needed after equal historical-data access. Demonstrated transfer or acquisition benefit would support the broader discovery system; absent benefit, the benchmark should identify where the hypothesis fails.

## 12. Immediate next action

Implement A0 and A1 first: a supported-chemistry cohort, campaign manifests, split joins, and chemistry/context-aware classical controls. In parallel only when explicitly allocated, the FM implementation can add single-strand token/chemistry fusion behind its own interface. Freeze a small development experiment after those gates. Do not launch full-Atlas LoRA, multi-task training or RL as the first step.
