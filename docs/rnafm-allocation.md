# RNA-FM branch allocation — November 14, 2026

User authorized parallel development after review of additive value. Work ONLY in
/private/tmp/oligoal-rnafm-20261114. The original repository is running a source-hashed
GP experiment: never edit its source or environment. This checkout includes the
current uncommitted implementation snapshot; do not reset it or publish/push it.

## Contracts and ownership

Root is integration owner. Encoder agent is branch technical lead for checkpoint,
cache and runtime. Own src/oligo_engine/representations/, tests/test_rnafm_representation.py,
docs/rnafm-provenance.md, scripts/cache_rnafm.py, and its isolated environment.
Study agent owns src/oligo_engine/rnafm_study.py, models/rnafm_heads.py,
reporting/rnafm.py, tests/test_rnafm_study.py, configs/rnafm-*.toml and
docs/rnafm-study.md. Adaptation agent owns models/rnafm_lora.py,
tests/test_rnafm_lora.py, scripts/profile_rnafm_lora.py and docs/rnafm-lora.md.
No agent edits shared contracts.py, runner.py, pyproject.toml, lockfiles or baseline
modules. Propose changes to root. No src edits in the original checkout.

## Representation contract to implement

representations/rnafm.py exposes FrozenRNAFM(checkpoint_path, device='cpu',
cache_dir=None), encode(observations)->numpy.ndarray of aligned shape(n,1280), and
config dict. Mean-pool nucleotide tokens per source RNA1/RNA2 strand separately,
then concatenate in RNA1,RNA2 order. Exclude special/padding tokens, preserve raw
HELM metadata, explicitly record natural-base projection and T->U. Do not assume
RNA1 is the guide. Only claim pretrained RNA-FM after verified real checkpoint
loading; any parsing/loading/dimension failure raises, with no fallback features.
Checkpoint hash/source, encoder version, layer, pooling, normalization and strand
policy form cache identity. No batch-dependent or dataset-fitted transforms.
Encoder agent should message others immediately if API must change.

## Scientific scope and gates

Huesken primary, source-pinned official nucleobase splits, 5 matched seeds and
nested random measured-label budgets50,100,200,400,800/full pool. Match one-hot
Ridge vs frozen-FM Ridge first, train-only scaling and alpha selection. Retain
existing GP/CNN context but never mix their outcomes as matched comparisons.
Use source HELM and existing protected oracle. Test labels scored only after
training/model choices are frozen. Frozen extraction may cache test sequences in
eval/no-grad mode; never fit normalizers/PCA/selection on test rows. Same initial
and random nested IDs across representations. Random encoder control before
attributing gains specifically to pretraining. Shared absolute target for
cross-predictor efficiency; separate full-pool references. No invented results.

Priority: provenance/profile -> frozen prediction curves -> frozen acquisition
geometry with fixed predictor -> bounded actual LoRA proof -> iterative LoRA
acquisition only after earlier gates. Frozen negative results do not automatically
rule out LoRA, but require a reasoned hypothesis. Log all failed attempts.
LoRA profiling can proceed independently with random tiny fixtures; claim an
actual adapted efficacy model only with real weights, measured training-only
labels and verified adapter updates. No downstream Huesken-trained checkpoint.
No paid cloud services or large concurrent training jobs. Run heavy extraction
or adaptation after coordinating with root to protect current GP CPU/RAM use.
Weights/caches/results ignored and never committed. No new external data needed.

Each agent delivers tested code, exact commands, actual outputs and limitations.
Send progress and dependency messages directly to peers; root handles integration.
