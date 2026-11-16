# Repair of the no-COMMIT failure

The failure was in the **search-policy interface**, not a disabled COMMIT action
or an incorrectly computed molecular reward. `Grammar.legal()` exposed a general
draft editor to PPO: STOP/CANCEL during construction, repeated EDIT from review,
and PARENT → COMMIT of an unchanged cached design. There was no progress invariant
between choosing a proposal and scoring it. The policy could enter a legal
zero-reward cycle such as PARENT → CANCEL indefinitely.

The historical batch-64 runs illustrate the consequence. With 2,048 actions each,
seeds 700/701/702 made 46/41/42 training commits, but only **1/1/0** were new
designs within their campaigns. They received **1/1/0** positive-reward commits.
Most requests were charged initial designs after frequent resets or cached-parent
replays. A critic predicting almost zero could have low MSE without useful search.

Direct diagnosis established that legal construction of a known positive control
gave six zero construction rewards followed by **+0.4063 at COMMIT**. The review
mask admitted COMMIT, with nonzero policy probability. Sampling the old frozen
policies also failed in the checked small diagnostic; changing argmax evaluation
alone was not a demonstrated remedy. No molecular reward bonus was added.

## Implemented correction

`TransactionalGrammar` is now the default for `DesignCore`, `MolecularEnv` and
new training. Its version is `transactional-v2`.

- NEW completes length/site/layout/pattern/terminal/COMMIT in seven tokens.
- PARENT selects one edit field, then proceeds forward to COMMIT in at most eight
  tokens. A completed draft cannot return to the editor repeatedly.
- No CANCEL or STOP interrupts an in-progress proposal. The old editor remains
  available only through explicit `legacy-v1` mode for historical replay.
- A search episode attempts at least one new proposal before STOP is offered.
  After that, STOP is available at proposal boundaries. Exhausted design spaces
  may stop immediately. This minimum-work rule is an explicit interface change.
- Each conditional mask retains choices with at least one unqueried complete
  design. The filter uses candidate identity and prior-query membership only;
  it does not inspect efficacy, risk, eligibility, reward or unqueried predictions.
- The decoder reserves enough construction tokens before starting a proposal.
  A NEW path requires seven remaining tokens; PARENT conservatively reserves eight.
- Complete-design reachability is preserved. Duplicate requests remain charged by
  the common scorer if another caller explicitly requests them; the new decoder
  simply avoids proposing previously queried designs to a deterministic scorer.

All chemical profiles, contexts, predictor artifacts, screening bounds, reward
normalizers and `Q(next archive) − Q(current archive)` rewards are unchanged.
The construction observation adds an explicit pending-parent-edit flag. The
observation/action schema is versioned; old policies cannot silently enter v2.
CLI/app inference reconstructs the decoder recorded in each policy receipt.
Old receipts without a decoder field mean legacy-v1, not the new default.

New training records proposal counts during validation and fails explicitly if a
nonexhausted v2 campaign makes no new proposal. Forced completion and identity
filtering repair the search interface; they do not prove that the learned policy
selects better molecules than an untrained decoder or a conventional optimizer.

## Verification

Regression checks reproduce the original parent/cancel cycle, then verify that it
is forbidden in v2. An exhaustive traversal of a small proposal grammar establishes
that every legal edge advances the construction stage, every path completes within
eight tokens, and the same unqueried complete designs remain reachable. Additional
checks cover score-blind masks, screened-parent editing, token reservation, exhausted
spaces, absence of duplicate queries, untrained-policy completion, unchanged reward
telescoping, deterministic reload and exact optimizer/RNG/environment resume.

An actual historical checkpoint reproduces its original 160-action trace exactly
when explicitly loaded into legacy-v1. Loading it into v2 is rejected. The current
suite passes **228 core tests and six optional Gym/PPO tests**, with lint, formatting
and import checks passing.

## Matched bounded rerun

The table below preserves the original three-seed repair experiment. A subsequent
[five-seed comparison](molecular-optimizer-comparison.md) uses corrected random and
greedy controls that avoid spending requests on already scored designs. Use that
comparison for the current optimizer assessment; do not pool the two protocols.

Local artifacts: `artifacts/molecular-decoder-fix-v2/`. The sealed protocol retains
the same seeds 700/701/702, batch size 64, 2,048 training actions, 256-action rollouts,
four PPO epochs and eight-request search cap. Decoder/schema change; predictors,
eligibility and reward do not. Acceptance concerns construction progress, not
obtaining a positive optimizer comparison. Final outcome data remain sealed.

| Per training run | Legacy | Corrected |
| --- | ---: | ---: |
| New proposals within campaigns | 0–1 | 274–281 |
| Positive-reward commits | 0–1 | 59–64 |
| Total charged requests, including starts | 514–746 | 328–341 |

All **nine corrected deterministic evaluations** (three trained seeds × three
targets) commit **seven new designs**, use all **eight requests** including the
start, and finish by request-budget exhaustion. There are no cached recommits,
edit/cancel loops or zero-proposal evaluations. Construction takes 49–56 tokens.
These results fix the observed failure; no extra predictor budget was granted at
evaluation. Fixed training actions do not imply equal training predictor queries.

Mean best eligible archive utility (0–1), paired seeds:

| Method | DGAT2, training | CFB, validation | FGFR4, development |
| --- | ---: | ---: | ---: |
| Legacy PPO, batch 64 | 0.000000 | 0.000000 | 0.000000 |
| Corrected PPO, batch 64 | 0.711763 | 0.141856 | 0.000000 |
| Untrained corrected decoder | 0.487449 | 0.094425 | 0.000000 |
| Random | 0.600846 | 0.000000 | 0.000000 |
| Greedy | 0.000000 | 0.145943 | 0.000000 |

The untrained control uses the same architecture and seeds, with zero PPO updates.
It also completes seven new proposals in all nine evaluations: reliable completion
comes from repairing the decoder, not from claiming PPO learned administrative
correctness. The trained mean exceeds that control here, but three seeds and
previously used development targets do not establish a learning/generalization
claim. Corrected PPO still trails greedy slightly on validation CFB; FGFR4 remains
zero for all methods. Expanded efficacy applicability and independent-evaluator
gates remain open. None of these predictions establishes biological benefit.

To run the corrected first-seed policy locally:

```sh
poetry run python app/molecular_server.py \
  --config artifacts/molecular-design-v1/multi-endpoint-config.json \
  --policy artifacts/molecular-decoder-fix-v2/batch-64/seed-700 \
  --output artifacts/molecular-app-v2 --port 8001
```

Policy weights and run artifacts remain ignored local files. No commit or push was
performed. Historical artifacts are preserved; they must not be silently compared
as if the old and new decoder were the same task interface.
