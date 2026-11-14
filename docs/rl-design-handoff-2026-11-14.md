# Restricted Huesken RL design handoff — 2026-11-14

## Scope and eligibility

This is a bounded engineering experiment in **unmodified siRNA RNA1 sequence proposals**. It uses one frozen Huesken Ridge potency predictor as a surrogate reward. There is no target transcript, second-strand design, modification editing, neurotoxicity or immune scorer, or experimental validation. The generated 19-mers have **no verified target binding or gene specificity**. PS/2'-MOE ASO efficacy and safety design remains ineligible. The prior acquisition/active-learning studies are unchanged.

The source is pinned OligoGym revision `97f5b9f58d9e445a8ecb0218037af7465c3708c0`, Huesken/Ichihara 2007 set, 2,431 rows. The saved predictor uses the seed-0 exact-HELM grouped outer training partition (1,944 rows) only. Its alpha, 10.0, was selected by five shuffled training-only K folds. All 2,431 source rows were checked against the existing positional feature implementation; reload prediction error on ten held-out feature vectors was exactly zero. No outer-test labels were used to fit the bundle, select alpha, or score RL candidates. The outer-test partition is deliberately not an RL performance evaluation. See the ignored local `artifacts/rl_design/huesken_ridge_bundle_seed0/fit_audit.json` for row IDs, source hashes, and the full fitting audit. Bundle identity: `f594788966c4a354d19b556305c88cd21ed31811248e1a9b51036f7d86df32b4`.

The bundle is a JSON numeric model, not a pickle. Its 57 features are three indicators per position of the 19-base RNA1 strand, with A as reference. The loaded coefficient vector, intercept, training-label mean/SD, training sequences, hashes, and source metadata are fixed during every design run. `python -m oligo_engine.design.rl audit` records this restricted eligibility. The predictor was frozen afresh from the documented split; this does not change, replace, or claim reproduction of any earlier benchmark estimate.

## Reward and legal actions

The single active endpoint is predicted Huesken inhibition, higher is preferred. Raw predictions retain the model's unbounded scale. Engineering reward is `tanh((prediction - training_label_mean) / training_label_sd) - 0.1 × max(0, nearest_training_sequence_Hamming_distance - 4)`. The fixed distance penalty discourages distant proposals; the value 0.1 and distance threshold 4 are engineering choices, not validated biological thresholds. Predictor uncertainty is **unavailable**. No missing safety score is treated as zero. Results are cached by sequence under a scorer identity that includes the bundle and reward settings.

The environment has 77 stable actions: STOP and four base substitutions at each of 19 positions. No-op substitutions are masked. Eight legal edits or STOP ends an episode; the only normal reward is on the terminal sequence, with gamma 1. The observation contains the current full RNA1 one-hot sequence and remaining edit fraction. Invalid actions terminate with a failure reward. The same start pool, sequence domain, frozen scorer, and maximum edit distance apply to random and evolutionary search. PPO, validation, and final starts are separately listed in each run's ignored `starts.json`. These are **held-out RL starting sequences drawn from predictor training**, not held-out biological targets.

## Implementation and runs

- Modules: `src/oligo_engine/design/{huesken_bundle,scoring,environment,search,rl}.py`.
- Freeze command: `PYTHONPATH=src python scripts/freeze_huesken_ridge.py --output artifacts/rl_design/huesken_ridge_bundle_seed0`.
- Eligibility: `PYTHONPATH=src python -m oligo_engine.design.rl audit --bundle artifacts/rl_design/huesken_ridge_bundle_seed0/ridge_bundle.json`.
- Toy check: `PYTHONPATH=src python -m oligo_engine.design.rl smoke --output artifacts/rl_design/toy_smoke_final_20261114`. The count-G toy reached its known `GGGG` optimum, reward 1.0; it is engineering-only.
- Huesken example: `PYTHONPATH=src python -m oligo_engine.design.rl train --bundle artifacts/rl_design/huesken_ridge_bundle_seed0/ridge_bundle.json --output artifacts/rl_design/huesken_512_seed11 --seed 11 --updates 4 --n-steps 128`. Repeat for seeds 23, 37, 53, 71 in separate output directories.
- Summary: `python scripts/summarize_rl_pilots.py artifacts/rl_design/huesken_512_seed{11,23,37,53,71}/report.json --output artifacts/rl_design/huesken_512_five_seed_summary.json`.
- Re-evaluate a saved policy on the fixed final starts: `PYTHONPATH=src python -m oligo_engine.design.rl evaluate --checkpoint artifacts/rl_design/huesken_512_seed11/best.zip --bundle artifacts/rl_design/huesken_ridge_bundle_seed0/ridge_bundle.json --output artifacts/rl_design/huesken_512_seed11/evaluation_final.json --split final`.
- Export unique proposals: `PYTHONPATH=src python -m oligo_engine.design.rl generate --checkpoint artifacts/rl_design/huesken_512_seed11/best.zip --bundle artifacts/rl_design/huesken_ridge_bundle_seed0/ridge_bundle.json --output artifacts/rl_design/huesken_512_seed11/generation_final.json --split final --count 20`. This returned 16 unique proposals from 16 starts and reported a shortfall of four; it did not silently fill with duplicates. The command applies the same action masks and checks the saved bundle/scorer/manifest identities.

The optional RL dependencies are locked at Gymnasium 1.1.1, Stable-Baselines3 2.6.0, sb3-contrib 2.6.0, and PyTorch 2.3.1. The actual run used Python 3.11.16, NumPy 1.26.4, and CPU. MaskablePPO used a 64/64 MLP, learning rate 0.0003, `n_steps=128`, batch 64, 5 epochs, and four updates (512 environment steps). This is a small pilot, not the mega prompt's suggested 256-step rollout or a 5,000-score standard run. No settings were tuned based on the observed scores.

Each run saves `best.zip` selected by mean reward on 16 validation starts after each update, `last.zip`, each update checkpoint, action vocabulary, starts, training history, candidate CSV, report, and search curve. A saved checkpoint reproduced masked deterministic inference and policy weights changed. The final policy was evaluated once on 16 separately selected starting sequences. Artifacts and weights remain local and Git-ignored.

## Five-seed matched-budget search comparison

**Metric:** best predictor-based engineering reward seen during each method's training/search, at the same number of *unique* frozen-scorer evaluations within each seed. This is an optimization comparison, not Pearson r, measured inhibition, or test-set accuracy. PPO's 512 environment steps produced about 69 terminal scores; random and evolutionary search each received exactly that seed's unique-score budget. Requests, cache misses, and per-score traces are saved in each report.

| Seed | Unique scores | PPO | Random | Evolutionary |
| ---: | ---: | ---: | ---: | ---: |
| 11 | 69 | 0.9103 | 0.8853 | 0.7926 |
| 23 | 68 | 0.6776 | 0.8536 | 0.8503 |
| 37 | 68 | 0.6997 | 0.7706 | 0.9335 |
| 53 | 69 | 0.7896 | 0.8286 | 0.8865 |
| 71 | 70 | 0.7544 | 0.8605 | 0.9039 |
| **Mean ± sample SD** | **68.8 ± 0.8** | **0.7663 ± 0.0918** | **0.8397 ± 0.0436** | **0.8734 ± 0.0543** |

Paired mean PPO minus random was −0.0734 (sample SD 0.0750); PPO minus evolutionary was −0.1070 (sample SD 0.1349). PPO won 1/5 seeds against each comparator. Mean validation-selected PPO reward on validation starts was 0.3740 ± 0.1881; mean final held-out-start PPO reward was 0.4613 ± 0.1075. Baselines were **not** evaluated on the final starts, so those numbers are not a matched final policy comparison. The five seeds repeat optimization on one frozen predictor and one fixed start manifest; they are not five independent biological targets. The curve at `artifacts/rl_design/huesken_512_five_seed_curve.png` shows mean best reward and between-seed SD through the shared first 68 unique scores.

## Verification and limitations

`PYTHONPATH=src /tmp/oligo-train-venv/bin/python -m pytest -q` passed 72 tests. Ruff check and format check passed on the new design code, freeze/summary scripts, and RL tests. `poetry check --lock` passed with existing metadata deprecation warnings. The five-run summarizer rejects mixed bundle/scorer/environment/algorithm identities and unmatched score budgets.

The repository's `make lint`, `make format-check`, and `make import-check` wrappers could not start because `poetry` is not on this shell's PATH. Their underlying equivalents succeeded: `ruff check .`, `ruff format --check .` (58 files), and importing `oligo_engine` with `PYTHONPATH=src` in the Python 3.11 run environment.

This implementation supports fresh runs and checkpoint reload for inference. It **does not** implement full interruption resume with restored optimizer, RNG, rollout/environment, and score-cache state. Do not treat `last.zip` as a budget-safe exact resume. The pilot also does not provide target-aware validity, chemistry/template support, uncertainty estimates, measured-label assessment of proposals, independent predictor cross-checking, or a matched held-out-start comparison against baselines. The reward penalty may be exploited even with this constrained action space. These are prerequisites for stronger scientific claims, not outcomes of this pilot. No active-learning or RL-to-assay loop was run.
