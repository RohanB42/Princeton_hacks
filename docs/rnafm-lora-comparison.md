# Bounded multi-seed RNA-FM LoRA comparison

Authorized November 14, 2026, following the single-seed feasibility result and
negative frozen-representation studies. This new development comparison asks
whether adaptation merits continued work against tuned classical predictors.
Earlier studies remain separate and preserved. This is not a clinical claim.

## Protocol frozen before new test outcomes

Five official nucleobase holdouts: seeds400–404. Nested random label budgets50,
100 and200, with identical IDs for every arm. Full Huesken source bytes and source
splitter are verified against pinned OligoGym. Models see only acquired labels;
all train/validation labels count against the same budget. Official holdouts share
target genes and overlap across seeds. Huesken has informed previous development.

Four arms: one-hot+tuned Ridge; frozen RNA-FM+tuned Ridge; frozen RNA-FM+linear
neural head; Q/V rank4 LoRA RNA-FM+the same head. Separate strand encoding,
nucleotide-mean pooling and source RNA1/RNA2 concatenation remain identical.
No guide-orientation inference or chemistry encoding is added.

Ridge uses acquired-only three-fold target-group validation (row fallback if
needed), with training-only StandardScaler in each fold, alpha grid0.1,1,10,100,1000,
minimum mean RMSE and first-grid tie-breaking; final fit uses all acquired rows.

Each neural arm independently selects3 or10 epochs by RMSE on a fixed20% held-out
subset of its acquired labels, withholding target groups when possible. Neither
arm gets extra measured labels. Both candidates and the final all-acquired refit
start from fresh verified base/head/adapter initialization. Internal validation
normalization uses inner-fit labels only. No larger-budget adapter is reused.
Other settings: rank4, alpha8, AdamW lr0.001, weight decay0, gradient norm cap1,
batch8, CPU1thread, seed-matched canonical fitting order. No test-derived stopping.
Frozen-head optimization uses cached frozen embeddings to avoid repeated encoding;
its feature values, head initialization and optimizer procedure match the adapter
arm's base representation. Different neural/classical model-selection mechanisms
are disclosed; there is no claim of identical compute expenditure.

All arms and budgets within a split are fitted before test scoring begins. Two
classical full-pool references use separate oracles. No LoRA or frozen neural
full-pool reference is claimed. Scores from other seeds or earlier studies are
never substituted as these references.

Primary: paired LoRA minus one-hot Ridge normalized Pearson learning-curve area
across50–200 labels. Secondary: LoRA minus frozen-head and frozen-Ridge. Report
all per-seed differences, mean/sample SD, RMSE/MAE, runtime/RSS, selected epochs,
and actual adapter/base integrity. Absolute Pearson0.60 is the common threshold;
not_reached stays explicit, with no interpolation or extrapolated savings.
This tiny budget range can establish comparative low-label behavior, not broad
label efficiency or superiority over every classical model.

## Compute evidence and cap

Before test scoring, a seed400 training-only profile used200 acquired labels,
one epoch and batch8:9.43s, peak process RSS2.03GiB, CPU1thread. It read no test
labels. Receipt: artifacts/rnafm-lora-training-profile.json. Estimated full matrix
20–35min; hard between-fit wall-clock cap7200s. If exceeded, preserve incomplete
attempt; do not report a selected subset as the complete result. Frozen-head
caching reduces redundant backbone work. No paid/cloud resources are used.

## Commands

```sh
PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  .venv-rnafm/bin/python -m oligo_engine.rnafm_lora_study \
  --output artifacts/rnafm-lora-comparison-smoke --smoke

PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  .venv-rnafm/bin/python -m oligo_engine.rnafm_lora_study \
  --output artifacts/rnafm-lora-comparison-development
```

Existing outputs are refused. Suite JSON records failure/current progress and
completed seed receipts. Outputs include executed-source snapshot, frozen config,
IDs, inner validation membership, model settings, integrity audits and report/plot.
Generated artifacts/checkpoints are ignored and must not be committed.

Tests cover held-out-label poisoning, budget-prefix invariance to unrevealed labels,
inner-validation boundaries, matched IDs, deferred scoring, adapter reset and base
integrity. Real smoke and five-seed status/results are appended after completion.
