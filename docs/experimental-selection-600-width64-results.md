# Three-layer PPO: matched 64-neuron follow-on

The user requested widening each hidden layer from 32 to 64 neurons. The
[extension protocol](experimental-selection-600-width64-protocol.md) fixed this
change before training the new policies. All other configuration values match
the [32-neuron experiment](experimental-selection-600-results.md).

## Result

Widening did not improve mean new-hit discovery in this exploratory replay:

| Method | Mean new hits | PSD3 | SMAD7 |
|---|---:|---:|---:|
| Updated greedy | 9.00 | 18.00 | 0.00 |
| PPO, three layers of 32 | 8.96 | 17.92 | 0.00 |
| PPO, three layers of 64 | 8.86 | 17.72 | 0.00 |
| Frozen source ranking | 8.40 | 16.80 | 0.00 |
| Random | 6.70 | 13.40 | 0.00 |

The primary width contrast, 64 minus 32, is -0.10 new hits. Wider PPO minus updated
greedy is -0.14, and versus random is +2.16. These are descriptive differences,
not demonstrated superiority/inferiority on new biological targets. Every method
again missed the rare SMAD7 hits in the selected forty assays.

## Controlled setup and behavior

The exact source fitting/calibration IDs, source prior identity, candidate/sentinel
IDs, and initial measurements match across widths. All thirty baseline acquisition
ledgers (random, updated greedy, frozen ranking) are identical between runs.
Configuration differs only in `hidden_layers = [64, 64, 64]`. The report version
and source-file receipts also reflect the code extension needed to accept width 64.

Both actor and critic have three hidden layers plus output heads. Widening raises
the total policy parameter count from 5,642 to 19,466 (about 3.45 times). Both
versions use 16 aggregate observations and acquisition-expert actions, not direct
600-candidate action logits or an LLM. Reward is new recorded inhibition above 80
percentage points, with ten initial assays excluded from hit credit but included
in the fifty-assay budget. Each evaluation campaign has exactly 600 candidates.

Train seeds 613–617 each receive 8,192 decisions. Development-only checkpoint
selection uses DMPK/PLN; final replay uses PSD3/SMAD7 and seeds 71–75. All five
policies were fixed before constructing final acquisition environments. Candidate
pool, predictor fitting and budget rules remain unchanged.

| Policy seed | Width-32 hits | Width-64 hits | Difference | Selected width-64 step |
|---|---:|---:|---:|---:|
| 613 | 9.40 | 9.00 | -0.40 | 3,072 |
| 614 | 9.00 | 8.40 | -0.60 | 1,024 |
| 615 | 9.00 | 9.00 | 0.00 | 7,168 |
| 616 | 8.40 | 9.00 | +0.60 | 5,120 |
| 617 | 9.00 | 8.90 | -0.10 | 2,048 |

Width-64 training-seed sample SD of target-macro hit counts was 0.261, versus
0.358 for width 32. The primary average includes every seed; no final-result seed
selection was performed. Across 2,000 final PPO decisions, 1,596 chose updated mean
(79.8%), 400 chose source mean (20.0%), and four chose random (0.2%). Three policies
always chose updated greedy, one always chose frozen ranking, and one mostly chose
updated greedy with four random choices. More capacity did not create a stronger
acquisition strategy in this setup.

## Checks, timing and limits

- `make lint format-check import-check test` passed, including 225 repository tests.
  Thirteen optional tests passed in the pinned isolated runtime, including actual
  width-32 and width-64 actor/critic architectures and deterministic save/reload.
- All eighty final ledgers passed unique-purchase, seed-budget, reward,
  remaining-budget and fit-label-count checks. The deferred-sentinel acquisition
  seal and executed source hashes match. Preflight and executed manifests match.
- Training/checkpoint-selection/reload phases took 23.36 seconds total for five
  wider policies, versus 21.99 seconds for the narrower run. The complete wider run
  function took 28.75 seconds; installation, process startup and tests are excluded.
  Timing is descriptive, not a controlled compute benchmark.
- This is a requested follow-on after inspecting the previous results. Both
  evaluation targets have prior outcome exposure; two target groups cannot support
  broad inference. No new threshold, split, seed search or training-budget change
  was selected from this result. Gate 1 remains open.
- Only recorded-assay replay was performed. No laboratory test, LLM fine-tuning,
  clinical safety claim or real-dollar saving is established. The $30,000 mapping
  remains unresolved; the user accepted a fifty-assay comparison.
- Previous artifacts were preserved. New policies and outputs remain ignored;
  no commit, push or remote CI run is claimed.

## Artifacts

`artifacts/experimental-selection-600-width64/run-v1/` contains the full report,
eighty episode ledgers, five policy checkpoints/receipts/reload probes, source and
policy seals, and `width-comparison.json` / `width-comparison.png`. The parent has
the matched preflight and metadata-only manifest. These are local ignored artifacts.

Use `configs/experimental_rl/atlas_600_3layer_64.toml` with the command in the
extension protocol to reproduce into a fresh output directory. The practical result
remains that updated greedy is the strongest tested method at the final budget.
