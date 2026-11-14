# RNA-FM low-label prediction study

This supporting branch evaluates representation quality before acquisition policy
changes. It preserves the original running GP study and uses the isolated checkout
specified in rnafm-allocation.md. All results remain measured diagnostic replay;
seven-dataset historical reproduction is unresolved. Huesken has informed previous
method development, so new seeds do not constitute independent biological validation.

## Frozen first comparison

Config: configs/rnafm-prediction.toml, declared before measured outcomes.
Huesken, all2,431 source rows, official nucleobase holdouts at pinned OligoGym
97f5b9f, NumPy-global source-compatible seeding, seeds300–304. Budgets50,100,200,
400,800 and a separate full eligible-training-pool reference. The initial50 IDs
are Random(seed).sample(train_ids,50); a separate string-seeded RNG permutes the
remaining pool. Nested pools are identical for every representation. Model fitting
uses lexicographically sorted IDs. No efficacy values are clipped or changed.

Compare fixed one-hot base features, frozen pretrained RNA-FM embeddings and an
architecture-matched random-initialized RNA-FM encoder (seed1729). The latter is
explicitly not pretrained. Both RNA-FM arms encode RNA1 and RNA2 separately,
mean-pool nucleotide tokens and concatenate the two640-dimensional means. Exclude
special tokens and record natural-base projection and T->U handling. Original
HELM/chemistry metadata remain preserved. RNA1 is not assumed to be guide strand.

All arms use Ridge with the same alpha grid[0.1,1,10,100,1000], StandardScaler,
and three-fold acquired-training-only validation. GroupKFold uses target groups
when at least3 populated groups exist; otherwise seeded shuffled KFold. Every
inner scaler fits only inner-training records. Mean validation RMSE selects alpha,
with original grid order breaking ties. A fresh final scaler/head then fits all
currently acquired rows. No unrevealed pool or test labels enter selection.

Frozen extraction may cache every sequence in evaluation/no-gradient mode since
it fits no preprocessing or labels. Head scaling is always acquired-training-only.
The random encoder uses identical extraction, pooling and head procedures.

## Analysis and boundaries

Primary comparison: paired normalized Pearson AULC, frozen RNA-FM minus one-hot,
over50–800 measured labels. Report Pearson/RMSE/MAE means and sample SD over5 seeds;
never substitute zero for undefined correlation. The random encoder supplies a
secondary control, with per-seed AULC differences also reported against it.

Cross-predictor label efficiency uses the shared absolute threshold r=0.60. It
never measures each model against an easier private target. First observed budget
crossing is reported; if only the separate full reference crosses, explicitly mark
reached_at_full_reference. If neither crosses, report not_reached and no numeric
savings. Summaries include contributing-pair n and all threshold status counts;
conditional savings must not be advertised as unconditional. No interpolation.

All representations and reference models are fitted before each seed's evaluator
scores test predictions. Alpha choices, fit IDs and inner fold IDs are saved.
Reporting independently checks exact pairing, label budgets, inner-fold boundaries,
reference scope and artifact hashes. Source changes in executed modules fail the
study while unrelated sibling-agent files may change. Failed attempts preserve
failure state and completed seed artifacts; output reuse is refused.

This is prediction under random acquisition, not evidence that active selection
improves. It does not establish therapeutic efficacy or a deployable design agent.
Frozen negative results remain useful, and do not by themselves rule out LoRA.

## Running

Use the encoder owner's isolated .venv-rnafm, verified checkpoint and pinned source:

```sh
PYTHONPATH=src OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  .venv-rnafm/bin/python -m oligo_engine.rnafm_study \
  --checkout /private/tmp/oligoal-upstream-97f5b9f \
  --checkpoint artifacts/rnafm-checkpoint/RNA-FM_pretrained.pth \
  --cache artifacts/rnafm-cache \
  --output artifacts/rnafm-prediction-smoke --smoke
```

Omit --smoke and choose a new output path for all five seeds. Smoke uses one seed,
budgets50/100, plus full references; its AULC interval is explicitly50–100.
The script produces source snapshots, config, source/checkpoint/feature identity,
seed ledgers, report.json, learning-curves.png and learning-curves.svg.

Dependencies and checkpoint are owned by the encoder track; no weights/caches/
reports are committed. A direct target holdout can be declared in a separate config;
it is not a published nucleobase comparison. Frozen-embedding acquisition geometry
is subsequent work and must keep the predictor fixed across selection spaces.

## Attribution limits

The random-encoder control uses one fixed initialization (1729); split variability
is not random-backbone variability. A favorable contrast should be replicated with
additional backbone initializations before a broad pretraining attribution. RNA-FM
also uses external unlabeled pretraining data and compute; experimental-label
savings are not a claim of less total data or lower total computational cost.

## Completed prediction result (November 14)

Five official holdouts (seeds300–304), all90 Ridge budget/reference fits completed.
At800 labels, mean Pearson r was0.6131(one-hot),0.5256(frozen RNA-FM), and0.6103
(random RNA-FM). Full-pool references were0.6358,0.5783 and0.6430, respectively.
Frozen-minus-one-hot normalized Pearson AULC was-0.1013 +/-0.0512 sample SD.
Frozen-minus-random-encoder AULC was negative on all5seeds. Frozen never reached
r=.60 by800 labels;1seed reached it only at its full reference and4never reached.
One-hot reached by800 in4/5seeds and at full reference in the remaining seed.

This is a negative result for this frozen token-mean/concatenation representation
and Ridge head, not all possible RNA-FM pooling, layer selection or adaptation.
No pooling/head/model settings were changed in response. The single random encoder
control is a useful architecture check but does not estimate backbone-seed variance.
Reports and exact executed source snapshots are in the ignored local directory
artifacts/rnafm-prediction-development-20261114/. The real three-arm smoke also
completed. All8study tests pass, including hidden-label poisoning, deferred scoring,
inner-fold boundaries and fixed-predictor geometry pairing.

## Fixed-predictor acquisition geometry

Next authorized comparison uses --geometry with configs/rnafm-geometry.toml. Its
settings are declared before geometry outcomes; the preceding prediction results
have been observed and are explicitly disclosed. The predictor remains one-hot
Ridge for every policy. Compare nested random selection with greedy max-min
coverage in one-hot, frozen RNA-FM and random RNA-FM spaces. All spaces receive
per-row L2 normalization; no learned PCA/scaler is fitted for acquisition. Head
scaling and alpha tuning still use only each policy's currently acquired labels.

Seeds300–304 and budgets50,100,200,400,800 match prediction. Initial IDs match;
subsequent diversity selections can differ, while random selection exactly matches
the prediction study. Full references are trained once per seed and reused only
across matching predictor/split pairs. Primary contrast is frozen-embedding
diversity minus one-hot diversity Pearson AULC over50–800. Random comparisons and
random-encoder geometry are secondary controls. Log selected-ID Jaccard overlaps,
all fitted and validation IDs, and shared r=.60 threshold crossing/censoring.

```sh
PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  .venv-rnafm/bin/python -m oligo_engine.rnafm_study \
  --geometry --config configs/rnafm-geometry.toml \
  --checkout /private/tmp/oligoal-upstream-97f5b9f \
  --checkpoint artifacts/rnafm-checkpoint/RNA-FM_pretrained.pth \
  --cache artifacts/rnafm-cache \
  --output artifacts/rnafm-geometry-new
```

The geometry entry point is separate from prediction orchestration; prediction
source snapshots remain in their original result directories. No prior output is
rewritten by subsequent development.

## Completed geometry result (November 14)

All20campaigns completed (five seeds, four acquisition policies), with100budget
fits and5independent full references. The primary frozen-RNAFM-diversity minus
one-hot-diversity normalized Pearson AULC difference is-0.000108 +/-0.014906
sample SD. Frozen geometry beat one-hot geometry on2/5seeds; no consistent
advantage is established. Against random selection its difference is-0.001089
+/-0.021050 SD. At800labels, mean r is0.6131(random),0.6191(one-hot diversity),
0.6143(frozen diversity), and0.6151(random-encoder diversity). Shared r=.60 is
reached by800 in4/5,5/5,4/5and3/5campaigns respectively.

All five random-selection curves and full references exactly equal the earlier
prediction study's one-hot arm. This verifies alignment of labels, fitting order,
head tuning and evaluation between prediction and acquisition pipelines. Geometry
artifacts are in artifacts/rnafm-geometry-development-20261114/. Both final plots
were visually inspected. Interpretation remains specific to token-mean duplex
features, L2 max-min geometry, these budgets and overlapping Huesken holdouts.
