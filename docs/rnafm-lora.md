# Bounded RNA-FM adaptation proof

Status: four synthetic integrity tests pass, and an actual official-checkpoint
adaptation proof completed on November14,2026. This establishes executable LoRA
training under the declared budget, not general label efficiency.

## Measured proof result

Receipt: ignored local `artifacts/rnafm-lora-proof-seed300/profile.json`.
Both arms use the same50 revealed rows and661 official held-out rows at seed300.

| Model | Test Pearson r | RMSE | MAE | Fit seconds | Trainable parameters |
|---|---:|---:|---:|---:|---:|
| Frozen RNA-FM + fixed-epoch linear head |0.103146|19.476753|15.937639|9.47|1,281|
| Q/V LoRA RNA-FM + same linear head |0.244311|18.953783|15.136161|11.52|124,161|

All24 Q/V projections received rank4 adapters; the saved audit verifies actual
adapter updates and unchanged frozen-base tensor hashes. End-to-end per-arm time
including full-test prediction was37.12s and37.87s. Peak process RSS was1.854GiB
on CPU with one thread; this high-water mark is shared across the sequential arms.
MPS was not tested. Three fixed epochs were not tuned against the test set.

Interpretation: LoRA is technically feasible at this bounded label/compute budget
and outperformed this identically initialized frozen-head control on one split.
The control is a three-epoch linear head, not the stronger tuned Ridge benchmark.
This single-seed gap is not statistical confirmation, label savings, or superiority
over classical predictors. The head/adapter schedule needs training-internal
validation and multiple seeds before stronger comparison. Larger-budget and
iterative acquisition sweeps have not been run.

## Architecture and scope

The official RNA-FM source is pinned by the representation owner. Its attention
implementation exposes `layers.*.self_attn.q_proj` and `v_proj` linear projections.
The fused path calls functional attention with their `.weight` tensors, bypassing
projection forward methods. We therefore use PyTorch weight parametrizations:
W_effective = W_frozen + (alpha/rank) B A. B starts at zero. This affects both fused
and explicit attention paths and avoids a misleading forward-hook-only adapter.

`models/rnafm_lora.py` provides `RNAFMLoRAPredictor` behind fit/predict/config. Each
fit invokes a fresh verified-base factory, freezes all base parameters, initializes
new Q/V adapters and a linear regression head, and trains only the adapters/head.
A frozen-head control uses the same head initialization, fixed epochs, order and
learning rate. Backbone dropout is disabled; autograd remains enabled for adapters.
Targets are standardized using the supplied training labels only. No test-derived
early stopping or hyperparameter selection exists in this bounded proof.

The verified encoder's strict HELM parser supplies RNA1 and RNA2 independently.
The last hidden layer is mean-pooled over nucleotide tokens only for each strand;
the two strand means are concatenated. The order does not assert guide orientation.
T->U and natural-base projection are explicit. Chemistry information is not modeled.

## Frozen proof declaration

Before any adaptation outcome: seed300, official source-pinned nucleobase split;
50 initial labels sampled exactly as in the representation prediction study;
rank4, alpha8, three epochs, batch2, AdamW learning rate0.001, weight decay0,
gradient norm limit1. Both methods start from the same official checkpoint and
head seed. Full held-out predictions are scored only after both models finish.
This is a feasibility proof and one-seed diagnostic, not a label-efficiency finding
or a replacement for the five-seed Ridge representation comparison.

Run in the encoder-owned isolated environment:

```sh
PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  .venv-rnafm/bin/python scripts/profile_rnafm_lora.py \
  --checkpoint artifacts/rnafm-checkpoint/RNA-FM_pretrained.pth \
  --checkout /private/tmp/oligoal-upstream-97f5b9f \
  --output artifacts/rnafm-lora-proof-seed300
```

An explicit `--device mps` is accepted only if available; no MPS performance is
claimed without a measured run. Source, checkpoint, split and training IDs,
optimizer settings, losses, time and peak process RSS are saved. Peak RSS is a
process-wide high-water mark, not separate per-model allocated memory.

## Integrity requirements

Tests exercise Q/V weight use through functional linear operations, adapter
nonzero gradients and updates, zero residual at initialization, base tensor hash
invariance, canonical fit ordering, independent lower-budget resets, matched head
initialization, and adapter-only save/load with config and SHA256 checks.
An adapter checkpoint contains only trainable tensors, label normalization and
provenance; restoring requires the same verified base/config. Loading a larger-budget
adapter is never part of a smaller-budget fit. `fit` resets from base every time.

The public constructor accepts a model factory so synthetic tests can use tiny
fixtures. Real efficacy claims must use the verified `FrozenRNAFM` loader; a caller-
supplied identity alone is not independent proof of checkpoint provenance.

No uncertainty estimate is emitted. A trained adapter's `predict()` returns only
regression means. Iterative acquisition, ensembles and larger LoRA sweeps are
separate later tasks. Weights, caches and results remain ignored local artifacts.

Sources inspected: official RNA-FM `fm/model.py` and `fm/multihead_attention.py`,
source revision348951516e0963d22bbb33b3c9fc18c89081d38e, especially the functional
attention branch reading Q/V projection weights directly.
