# Atlas RNA-FM research execution handoff

Created November 14, 2026, 13:11 EST (18:11 UTC). The user explicitly authorized
a subagent to implement and execute the next steps of the research plan, including
the context necessary to continue independently. This authorization advances the
plan beyond a proposal; scientific gates and honest reporting still apply.

## Location and ownership

- Integrator repository: `/Users/rohanbutani/Desktop/proj/Princeton_hacks`.
- Isolated worktree: `/private/tmp/oligoal-atlas-rnafm-20261114`.
- Branch: `codex/atlas-rnafm-research`, based on `42bb9b8`.
- Assigned agent task: `atlas_rnafm_research`.
- Plan: [aso-atlas-rnafm-research-plan.md](aso-atlas-rnafm-research-plan.md).
- Live execution records live in the isolated worktree under
  `docs/research/atlas-rnafm/{STATUS,TASKS,DECISIONS}.md`.
- Generated results, caches and profiles belong under that worktree's ignored
  `artifacts/atlas-rnafm/`. Do not modify or consume another running study's outputs.

The research owner may implement the independent Atlas namespace, new ASO encoder
and model adapters, Atlas configs/tests/scripts/reports, and optional environment
instructions. Shared runner/contracts, main dependency declarations and lockfile
changes require an integration proposal rather than edits in the main checkout.
Reuse existing code through imports where safe. A required change can be proposed
and tested on this isolated branch; never silently alter Huesken behavior.

## Execution mandate

Read AGENTS.md and the canonical scientific/evaluation docs, then the complete
research plan and local Atlas audit. Proceed through A0 and A1 first: verified
chemistry parsing, campaign/split contracts, classical baselines and a source anchor.
Then implement and profile A2, and proceed through prediction, transfer and sequential
acquisition when their prerequisites pass. Do not repeatedly seek approval for
routine reversible implementation or local experiments already within this scope.

A full-Atlas training sweep is not the first run. Inspect label-blind feasibility,
freeze development settings, profile a small panel, and bound expensive runs from
measured memory/time. Prefer one training process at a time on the 16 GB machine.
No paid compute, deployment, external messaging, branch merge or force-push is
authorized here. Use CPU as a tested fallback; do not claim MPS support without
testing actual parametrized forward/backward execution.

An unfavorable result is a completed scientific result, not a reason to tune on the
test set. A failed gate should produce its audit, a concrete diagnosis and the next
independent work that remains justified. Do not stop after scaffolding alone: deliver
tested code, executable configs, actual measured outputs and interpretation for each
completed stage. Do not claim A0–A6 completion when only a subset has run.

## Scientific invariants

1. Distinguish source historical measurements from newly acquired target labels.
   Classical and FM transfer models get equal source-data access.
2. Evaluation targets, relevant patents and compound/sequence equivalents must be
   excluded before source training. Public efficacy-trained checkpoints with unknown
   overlap are not clean evaluation baselines.
3. No final-test labels in fitting, feature fitting, policy choice, tuning, stopping
   or rewards. Validation labels count against the applicable budget. Source-only
   and full-pool references are separate capabilities, never acquisition feedback.
4. Preserve original measurements and source IDs. Unsupported chemistry fails
   explicitly. No invented second strand or silent modified-base removal.
5. Current metadata yields at most 24 provisional campaigns with >=400 exact HELMs,
   spanning 12 target identifiers. Recalculate after parsing/identity/assay checks.
   Five repeated seeds do not create five independent target experiments.
6. Preserve source files and supplied fold assignments. The upstream OligoAI fold
   size summary is inconsistent with its file; investigate joins, do not rewrite
   source data to make documentation match.
7. Keep inhibition, dose-response and toxicity separate. No clinical safety claims,
   surrogate scores promoted to measurements, or RL design claims from this study.
8. Do not call a learning-curve gain proven label savings. Report censoring and
   target-level uncertainty. Freeze the confirmatory protocol before test outcomes.

## Reusable resources (read-only)

- Main core runtime: `/Users/rohanbutani/Desktop/proj/Princeton_hacks/.venv/bin/python`.
  Run with `PYTHONPATH=src` from the research worktree; verify imports resolve there.
- Existing RNA-FM runtime:
  `/private/tmp/oligoal-rnafm-20261114/.venv-rnafm/bin/python`.
- Verified checkpoint:
  `/private/tmp/oligoal-rnafm-20261114/artifacts/rnafm-checkpoint/RNA-FM_pretrained.pth`.
  SHA-256 `5b5d7d87b37c291ef42c140ef9edf7aea29f255fa2a4fd435f776c52e93d5e99`.
- RNA-FM source: `/private/tmp/oligoal-rnafm-source`; verify the actual package
  location and revision using existing provenance code before reuse.
- Pinned OligoGym source: `/private/tmp/oligoal-upstream-97f5b9f`.
- Upstream Python 3.11 runtime:
  `/private/tmp/oligoal-upstream-envs/oligogym-2ScCOzQO-py3.11/bin/python`.
- Atlas preparation runtime: `/opt/anaconda3/bin/python`, Python 3.13.9 with pandas
  2.3.3, PyArrow 21.0.0 and NumPy 2.3.5. This is not a compatible substitute for the
  pinned modeling runtime. Prepare an isolated compatible optional environment as
  needed and record exact packages; do not mutate these shared environments.

All paths are local conveniences, not a portable installation promise. Preserve
environment receipts and provide reproducible installation instructions. No weights,
PDFs, caches or generated model/run artifacts in commits. Existing released Atlas
files are already tracked and explicitly authorized; do not add unrelated datasets.

## Prior evidence and literature

The final Huesken LoRA comparison exists in the earlier isolated checkout at
`docs/rnafm-lora-comparison.md`; root contains an older protocol copy. The complete
summary is in `docs/updates/2026-11-14-1150-est.md`. At 200 labels, one-hot Ridge
r=0.4910, LoRA r=0.4196; LoRA improved its matched frozen neural head but lost to
one-hot on the primary area statistic in 5/5 seeds. This motivates a new ASO
hypothesis rather than a claim that RNA-FM already improves label efficiency.

The plan links OligoAI, Atlas source/folds, RNA-FM, small-data target calibration and
the BMDAL regression framework. Inspect actual pinned source APIs before integration.
OligoAI already combines pretraining and chemistry and reports experimental screening;
our prospective distinction is fair, sequential, target-held-out label efficiency.

## Continuation and reporting

Update STATUS after each gate or meaningful run: commit/source hashes, commands,
environment, cohort sizes, completed/failed fits, artifact paths, current process IDs,
elapsed time and next action. Persist TASKS checkboxes and DECISIONS before model
outcomes whenever a protocol choice changes. Send the integrator the first cohort
finding, first real baseline, compute profile and each stage conclusion. Report
blocking scientific discrepancies with exact evidence; keep unaffected work moving.

Commit tested code and reports on the research branch in coherent units, preserving
generated artifacts locally. Never switch or merge the main checkout. The integrator
will review the branch and coordinate any changes to common contracts or dependencies.
