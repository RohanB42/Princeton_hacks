# Supported ASO efficacy and optimizer diagnostic

Checkpoint: November 14, 2026, 19:10 EST (November 15, 00:10 UTC).
This completes the ordered [execution plan](updates/2026-11-14-1845-est-supported-aso-execution.md).
The measured ranking gate passed; the PPO expansion gate failed. Larger RL runs
were therefore not launched. Generated candidates remain unvalidated hypotheses.

## 1. Supported chemistry and assay

The new explicit template is `ps_moe_20_gapmer`: 20 nucleotides, MOE 5 / DNA 10 /
MOE 5, all 19 internucleotide linkages PS, methylcytosine at every C, and no terminal
phosphate. It preserves target complementarity while moving the binding window.
The legacy 19-mer template remains available and retains its own limitations.

The assay is **human HepG2, electroporation, 4,500 nM, 24 hours**, predicting
`Inhibition_pct`. This is a context-specific inhibition endpoint, not IC50,
clinical efficacy, accessibility, off-target selectivity or safety.

Selection used source metadata and availability of matching external holdout
metadata, without efficacy outcomes. The largest source-supported exact MOE profile
initially considered (A431/gymnosis, 4,000 nM, 48 hours, mixed PS/PO) had no matching
source-validation records. The selected profile was the largest with at least
three training patent identifiers and 100 matching external rows. This is a
data-derived development profile; selecting it with holdout metadata does not
constitute a preregistered independent confirmation study.

Before filtering there were 2,245 matching source-training rows and 2,351 matching
source-validation rows. Ambiguous `EXON`/`EXON1`–`EXON6` targets were excluded.
The first immutable source ID per natural sequence was retained within each
partition. We removed 390 assessment sequences with Hamming distance ≤2 or an
exact one-base window shift from any retained training sequence. The final split:

| Partition | Molecules/records | Patent identifiers | Target identifiers |
|---|---:|---:|---|
| Fitting | 2,000 | 5 | ATXN2, CFB, DGAT2, FGFR4 |
| Assessment | 1,924 | 3 | ATXN2, DGAT2, SERPINA1 |

Training and assessment patent identifiers are disjoint. Patent **families** have
not been resolved. Source-internal CV joins target, patent and nearby-sequence
links into four components, then uses three grouped folds. It preserves provenance
from duplicate source rows when constructing those links. There is no local target
adaptation and none of the seven reserved Atlas target campaigns was scored.

## 2. Real predictor integration

A position-specific one-hot Ridge model was fit on 2,000 measured source labels.
Source-only grouped CV over alpha `[0.1, 10, 100]` selected **100**. Chemistry and
assay are fixed, so this deliberately simple model encodes only base positions;
it is not a learned chemistry model or a LoRA model.

The exported JSON contains coefficients, intercept, training provenance and a fixed
training-prediction normalization reference. Inference requires no fitting,
unpickling, external project imports or outcome access. Hash checks bind the model
to its manifest. Exact chemistry and assay gates reject unsupported inputs.
Pure-Python predictions match sklearn on all 3,924 fitting/assessment feature rows
to maximum absolute error **1.42 × 10⁻¹⁴**.

The model feeds the shared scorer and real 20-mer Gymnasium observations, with
direct/scorer/environment parity checked. Utility is the fixed training-prediction
percentile. Neurotoxicity is explicitly unavailable, not zero. Nearest-training
Hamming distance is diagnostic only; it is neither calibrated uncertainty nor an
implemented OOD rejection threshold. No independent safety head has been admitted.

## 3. Ranking recorded, held-out measurements

Predictions and top-20 IDs were saved before loading the assessment outcomes.
The fixed random comparator is the exact mean of the eligible target pool, which
is the expected mean of a uniformly sampled panel of 20 without replacement.

| Target | Eligible rows | Predicted top-20 measured mean | Random expected mean | Lift (percentage points) | Pearson r |
|---|---:|---:|---:|---:|---:|
| ATXN2 | 74 | 72.35 | 61.46 | +10.89 | 0.306 |
| DGAT2 | 1,828 | 64.65 | 54.77 | +9.88 | 0.301 |

Equal-target mean lift is **+10.39 percentage points**. SERPINA1 has 22 rows,
below the frozen minimum of 30 for target ranking, and contributes only to aggregate
error. Across all 1,924 rows, RMSE is **23.27** and MAE **19.69**; predicting the
training-label mean gives RMSE **24.16**. Thus absolute predictive accuracy remains
modest despite useful ranking in these two development panels.

The provisional readiness criterion required two evaluable targets, positive
target-macro lift and positive lift on at least two targets. It passed. There are
no target-level significance claims or confidence intervals from just two targets.
These results concern mostly familiar targets in new patents; they neither prove
unseen-gene transfer nor validate the generated panel.

## 4. Real transcript candidates and fair local search

A deterministic panel of 64 evenly spaced DGAT2 transcript windows was scored.
Predicted inhibition ranges from **27.15 to 64.57** percentage points; nearest-source
Hamming distances range from **6 to 9 of 20**. All safety values remain unknown.
The panel is saved locally as `artifacts/supported-aso-v1/real-panel.json`.
Target complementarity is verified against the pinned transcript sequence, not
against a whole transcriptome or measured RNA accessibility profile.

The separate optimizer diagnostic uses the center window of public human DGAT2
(policy training), CFB (policy validation) and FGFR4 (final policy comparison)
transcripts. Ensembl transcript IDs and exact sequence-content hashes are recorded.
All three genes occur in efficacy source training: these are disjoint **policy**
roles, not unseen-target predictor evaluation. Each space has radius 8 and an
eight-move horizon. Chemistry is fixed; actions are STOP/LEFT/RIGHT, not arbitrary
sequence or chemistry edits.

Conventional proposals now execute and pay for every intermediate ±1 move. All
methods start at the same site with separate caches, the same unique-score cap,
request cap of 100, and movement horizon. Revisits consume requests and moves.
This removes the earlier free-jump advantage. This is a **local-access** comparison;
it does not establish that such movement restrictions are the optimal computational
design formulation. The genetic control is a small integer-window search, not a
strong general molecular genetic algorithm. Unrestricted enumeration is shown
separately and pays for all 17 sites.

Three PPO policies (seeds 7, 17, 27) trained for 2,048 steps each. Checkpoints were
selected by terminal reward on the CFB window only. Mean validation best-visited
utilities were: unchanged **0.7055**, random **0.8715**, greedy **0.8715**, genetic
**0.9137**, PPO **0.7528**. The frozen expansion rule required PPO to beat every
active control before final-window comparison. It failed, so 8,192-step runs were
not performed. This decision is saved separately before the final comparison.

| Final FGFR4 method | Mean best-visited utility, cap 6 | Mean best-visited utility, cap 10 |
|---|---:|---:|
| Unchanged starting site | 0.8285 | 0.8285 |
| Random proposals, local movement charged | 0.8575 | 0.8575 |
| Greedy | 0.8285 | 0.8285 |
| Genetic | 0.8285 | 0.8285 |
| PPO | 0.8285 | 0.8285 |

Random reached the unrestricted reference utility **0.8720** in two of three seeds.
The three PPO rollouts used 2, 6 and 1 unique scores respectively and did not improve
over the start. Budget 10 cannot permit more than nine distinct scores in eight
local moves. Policies reloaded with identical actions and archives. All 30 final
method/seed/budget combinations respected score and movement caps.

PPO training itself used 2,059 / 2,061 / 2,052 requests and 13 / 15 / 11 unique
training candidates; validation requests were 22 / 29 / 28. Training/validation
caches span episodes, whereas final comparisons use fresh caches per run. Per-seed
training plus checkpoint-selection wall times were about 2.19 / 0.63 / 0.64 seconds
in the small CPU runtime. These costs are recorded separately, not hidden within
the deployment budget. No end-to-end compute advantage is demonstrated.

One methodological limitation is deliberate and visible: PPO training optimizes
terminal utility, while the comparison also reports the best visited design.
Aligning the objective with shortlist quality is a future declared ablation, not
a post-hoc adjustment to this result. A single window per role is insufficient for
general optimizer conclusions. This experiment supports **no PPO advantage** here.

## Reproduction and artifacts

Protocol: `configs/research/supported-aso-v1.json` and
`configs/rl/supported_aso_comparison_v1.json`. Preserve existing output directories;
the runners refuse to overwrite completed phase outputs.

The cohort/preparation code is currently on the separate, published
`codex/atlas-lora-scaling` branch at **f197d79**, not merged into main. Use its
`scripts/prepare_atlas_study.py` and `docs/research/atlas-rnafm/ENVIRONMENT.md` with
the released Atlas data to recreate the preparation. The exact parquet SHA-256
used here is `bbc3edbef73f2f2b926cd1fcc63946f16d52238f994e99c620be9f756522165d`.
Serialization/runtime changes require an explicit new provenance audit; do not
remove the hash check to force a run. This dependency means main alone is not yet
a complete clean-install data-preparation package for this study.

Example from main, with the separately prepared directory available:

```sh
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
atlas_python=/private/tmp/oligoal-atlas-rnafm-20261114/.venv-atlas/bin/python
rl_python=/private/tmp/oligoal-aso-review-20261114-env/bin/python
prepared=/private/tmp/oligoal-atlas-lora-scaling-20261114/artifacts/atlas-rnafm/preparation-v1
study=artifacts/supported-aso-reproduction
comparison=artifacts/supported-aso-optimizer-reproduction
"$atlas_python" scripts/run_supported_aso.py prepare --prepared-root "$prepared" --output "$study"
"$atlas_python" scripts/run_supported_aso.py fit --output "$study"
"$atlas_python" scripts/run_supported_aso.py evaluate --output "$study"
"$atlas_python" -c 'from oligo_engine.design.transcripts import fetch; [fetch(g) for g in ("DGAT2", "CFB", "FGFR4")]'
"$atlas_python" scripts/run_supported_aso.py panel --output "$study" --transcript artifacts/transcripts/homo_sapiens.DGAT2.json
"$rl_python" scripts/compare_supported_aso.py --bundle-dir "$study" --output "$comparison"
"$rl_python" scripts/plot_supported_aso.py --study "$study" --comparison "$comparison" --output "$study/summary.png"
```

Paths above identify the execution environments on this workstation; they are not
portable installation commands. Source fitting used Python 3.11.13, numpy 1.26.4,
sklearn 1.4.0, pandas 2.2.3 and PyArrow 21.0.0. RL used the pinned optional stack:
Gymnasium 1.1.1, SB3/sb3-contrib 2.6.0, torch 2.3.1, CPU, one thread. Live transcript
fetches can change; exact reproduction requires the cached sequence hashes in the
original `frozen-config.json`, not merely the same gene symbols.

Local model bundle SHA-256:
`44f975ae47c1a073ec52bde1e3403baa21de8a1b0b733e4bcac1a9b236252a84`.
Local outputs: `artifacts/supported-aso-v1/` and
`artifacts/supported-aso-optimizer-v1/`. They include split IDs, locked predictions,
model provenance, score archives, checkpoint manifests and the expansion decision.
The summary figure is `artifacts/supported-aso-v1/summary.png`.
Code/aggregate findings are published; datasets, fitted weights, transcript caches
and generated run artifacts are not added to these commits.

Checks: **193 core tests and 6 optional RL tests passed**, Ruff and whitespace
checks passed. New tests cover exact 20-mer structure, alias conversion, assay/hash
rejection, direct/scorer parity, intermediate movement costs, revisits and the
20-mer observation/chemistry gate. Added input-integrity checks reproduced the
assessment byte-for-byte without changing the fitted model or selected panels.

## Next evidence to obtain

Retain this simple real-predictor integration and the negative PPO diagnostic.
Before scaling RL, define multiple development windows, align training and
reporting objectives, and compare both terminal and best-visited outcomes with
credible search baselines. Keep a new final policy benchmark untouched until that
protocol is fixed; the FGFR4 window above is now development evidence.

For biological value, resolve patent-family overlap and transcript mapping of
measured compounds, establish applicability and calibration of an independent
compatible evaluator, and test rankings on additional held-out assays. The present
study does not provide that independent evaluator, an applicable safety screen,
synthetic-augmentation evidence, or prospective measurements. Those are distinct
follow-ups, not benefits inferred from higher surrogate utility.
