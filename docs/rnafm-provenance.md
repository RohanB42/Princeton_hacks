# Frozen RNA-FM representation: source and execution record

This branch implements label-free frozen features for Huesken siRNA efficacy.
It does not establish improved efficacy prediction, acquisition, clinical effects,
or completion of the expanded seven-dataset reproduction gate.

## Source and checkpoint identity

- Official implementation: https://github.com/ml4bio/RNA-FM
- Source revision: `348951516e0963d22bbb33b3c9fc18c89081d38e` (`fm`0.2.2).
- Local source: `/private/tmp/oligoal-rnafm-source` (read-only during experiments).
- Checkpoint: `RNA-FM_pretrained.pth`, linked from official README to
  https://huggingface.co/cuhkaih/rnafm/tree/main . This is the base RNA model,
  not mRNA-FM or a downstream oligo-efficacy checkpoint.
- Official LFS metadata size:1,194,424,423 bytes. SHA-256:
  `5b5d7d87b37c291ef42c140ef9edf7aea29f255fa2a4fd435f776c52e93d5e99`.
- Loader requires that exact hash and source revision. It validates architecture
  and lets all loading/parsing failures raise. It never calls OligoGym's optional
  RNA-FM wrapper, which can substitute simple features after model-load failure.
- Current PyTorch's restricted loader is used with `weights_only=True` and only
  the official checkpoint's `argparse.Namespace` explicitly allowlisted. The
  official state-dictionary loader constructs the RNA alphabet and network.

Official source LICENSE is MIT. Official model card metadata declares Apache-2.0
for weights. These observations do not assign a project license or authorize
redistribution. Weights and outputs remain ignored local artifacts.

## Pretraining and contamination limits

The official model card describes self-supervised pretraining on23+million
noncoding RNA sequences, without experimental labels. No downstream Huesken
adapter is selected. This supports using the base model as a representation
prior; it does not prove individual Huesken sequences were absent from pretraining.
A sequence-level pretraining overlap audit has not been performed. Sequence
exposure without efficacy labels and supervised efficacy-label contamination
are distinct; both should be disclosed if independently established.

## Representation contract

`FrozenRNAFM(checkpoint_path, device='cpu', cache_dir=None).encode(observations)`
returns aligned float32 arrays of shape `(n,1280)`. Empty input returns `(0,1280)`.

The pinned OligoGym HELM parser must yield exactly RNA1 and RNA2. Each strand is
processed separately in source order. Only A/C/G/T/U base tokens are supported;
T becomes U. Missing/ambiguous/modified base tokens and extra polymers raise.
Sugar and backbone information are omitted from the FM projection and retained
in the original observation. RNA1 is not asserted to be the guide strand.

Layer12 nucleotide token vectors are mean-pooled per strand, excluding BOS/EOS
and padding, then concatenated RNA1 followed by RNA2. There is no fitted scaler,
PCA, vocabulary or use of labels. All encoder weights are frozen and inference
runs in eval/inference mode. This representation differs from OligoGym's original
per-token CNN comparison and must not be called its exact reproduction.

The cache is keyed by original HELM plus encoder/checkpoint/source identity,
PyTorch version, device, layer, pooling, projection and schema. Files include
shape/dtype validation and hashes for identity, sequence and vector contents.
Cache corruption fails explicitly. Batch size never determines the representation;
one duplex is encoded as two strands per forward call.

`FrozenRNAFM.random_initialized(checkpoint_path, seed=0, device='cpu', cache_dir=None)`
constructs the same architecture without loading pretrained state, using the
checkpoint only to obtain architecture arguments. Its config marks pretrained=false,
records the seed, and produces distinct cache keys. Constructor RNG changes are
scoped and restored. This control supports interpreting the value of pretraining.

## Isolated runtime and reproduction

Python: `/private/tmp/oligoal-rnafm-20261114/.venv-rnafm/bin/python`.
It uses its own virtual environment plus read-only paths to the existing scientific
packages, pinned OligoGym source and pinned RNA-FM source. Only ptflops0.7.5 was
installed in the isolated environment. No original environment or lockfile changed.
This is an explicit local environment receipt, not yet a portable clean-install lock.
`artifacts/rnafm-checkpoint/environment.json` records actual packages and Python.

```sh
PYTHONPATH=src .venv-rnafm/bin/python -m pytest tests/test_rnafm_representation.py -q
PYTHONPATH=src OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  .venv-rnafm/bin/python scripts/cache_rnafm.py \
  --checkpoint artifacts/rnafm-checkpoint/RNA-FM_pretrained.pth \
  --cache artifacts/rnafm-cache \
  --output artifacts/rnafm-profile --limit 8
```

Use `--limit 2431` for all Huesken records after the small-panel resource check.
Add `--random-seed 0` and a distinct cache/output for the random encoder control.
The CLI reads public observations only; no measurement labels are accessed.
Five focused representation tests cover parsing/projection, token pooling/masking,
strand order, exact cache reuse, tampering/version isolation and strict load failures.

## Verified small-panel execution

Official checkpoint size and SHA-256 match the published LFS metadata. The model
repository revision at retrieval is `91d4a46d28d8054a7b429955e8fc0c253ba0afd6`;
metadata and card snapshots are in artifacts/rnafm-checkpoint/.

On eight Huesken observations, real CPU extraction with two Torch threads produced
(8,1280) finite float32 embeddings. Model load/hash verification took2.225seconds;
first extraction took0.823seconds; cache reread took0.041seconds and matched exactly.
Peak process RSS was946,765,824bytes (~0.88GiB);99,521,546 total parameters and zero
trainable parameters. These are local measured timings, not guaranteed full-data
or MPS throughput. Full profile: artifacts/rnafm-profile/profile.json.


The architecture-matched random control also completed eight observations: load
1.550seconds, encode0.548seconds, cache0.043seconds, peakRSS875,675,648bytes.
It has the same99,521,546 parameters, zero trainable weights and exact cache reuse.
Its vectors differ from the pretrained vectors, and its cache identity is separate.
See artifacts/rnafm-random-profile/profile.json. The profile field saying labels
were not accessed means the encoder received no labels; Catalog still validates
source labels internally while exposing public observations.

The source is frozen for the prediction owner's full extraction/study. No scientific
performance result follows from successful extraction alone.

## Integrated test collection

RNA-FM tests require the research runtime and are excluded from default core CI
collection. Run `python -m pytest -m rnafm` in that runtime, or explicitly name
the test_rnafm files. Core dependencies and the project lock are unchanged.
The local runtime paths above are provenance receipts, not a portable environment
installation guarantee. Full clean-install packaging remains follow-up work.
