# Shared infrastructure for prediction, acquisition and robustness studies

November 14, 2026. The user requested that the research program remain broader than
RL and authorized starting infrastructure for the parallel experiments. This first
slice adds a study catalog and a label-free allocation planner. It does not launch
new training, choose favorable settings, merge research branches, or automate RL.

## Completed fine-tuning checkpoint

The Atlas scaling agent finished at `codex/atlas-lora-scaling@f197d79`: 240
fits/calibrations, 216 deferred target evaluations, zero failures, 100.6 minutes.
There is no training process still running. The completed report and five commits
after the published `1b3fc1e` snapshot remain local to the research worktree; main
does not yet contain that implementation.

For validation-selected source checkpoints and fixed three-epoch adaptation on
200 target labels, target-macro mean RMSE (lower better) was:

| Model | 3% source | 5% source |
| --- | ---: | ---: |
| LoRA + chemistry | 22.391 | 22.340 |
| Frozen RNA-FM + chemistry | 20.893 | 21.208 |
| Matched source Ridge + target offset | 19.883 | 19.656 |

LoRA lost to matched Ridge on every target-level mean at both budgets, including
the separate validation-selected target-duration protocol. Target-only XGBoost
reached RMSE 19.366 and target-only Ridge 19.626 using only the 200 target labels.
Extra source data and epochs did not establish a LoRA advantage for this recipe.
This is a negative development result on three targets, not evidence against all
foundation models. Seven reserved target campaigns remain untouched.

The study identified a design limitation: total acquired budgets were nested but
the inner fitting rows changed as validation groups were reassigned. The new
planner fixes the group partition before sampling any budget. It preserves the
earlier results rather than retroactively replacing their splits.

## Independent research tracks

The [predictor robustness design specification](predictor-robustness-design-spec.md)
defines held-out groups, perturbations, diagnostics and exploitation tests.
The subsequent [local implementation](predictor-robustness-implementation.md) adds
the audit pipeline, a known-failure fixture and an ASOptimizer context-support
diagnostic. It does not establish a validated real guardrail or augmentation result.

1. **Prediction and target transfer:** classical versus frozen/adapted encoders,
   chemistry/context ablations and a bounded optimization/regularization study.
   Keep gradient and validation allocations matched when isolating duration. Use
   training-internal held-out targets for transfer-aware selection, not final test
   targets. An improved predictor is a result even without RL.
2. **Experimental selection:** fixed-predictor random, diversity, uncertainty and
   batch-information policies on recorded compound–assay pairs. Report prediction
   quality and measured hit discovery separately. Uncertainty needs empirical
   checking; embeddings alone do not provide calibrated error bars.
3. **Surrogate robustness and augmentation:** real-only, regularized and augmented
   predictors with equal real-label budgets and comparable tuning effort. Start
   with held-out real-assay prediction, counterfactual diagnostics and simple
   search; PPO is a later optimizer comparison. Never copy measured labels onto
   edited molecules or use the teacher as the only independent evaluator.
4. **Molecular design:** one consumer of the common predictors and evaluation
   infrastructure. Compare enumeration and simpler search alongside PPO. Reward
   improvement alone is not evidence of better biological candidates.

`configs/research/studies.toml` records explicit completed, infrastructure-only and
planned status. Entries are handoff metadata, not automatic authorization or live
job tracking. Evidence on a different branch is identified as such.

## Commands

From the repository root, using the existing core environment:

```sh
PYTHONPATH=src .venv/bin/python -m oligo_engine.research list
PYTHONPATH=src .venv/bin/python -m oligo_engine.research plan \
  --pool artifacts/research/eligible-pool.json \
  --budgets 50 100 200 400 --seed 510 \
  --output artifacts/research/seed-510-plan.json
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_research_infrastructure.py
```

The input metadata contract is deliberately narrow:

```json
{
  "records": [
    {"id": "training-observation-1", "group": "component-A"},
    {"id": "training-observation-2", "group": "component-B"}
  ],
  "excluded_ids": ["final-evaluation-observation-1"]
}
```

The two-record example illustrates the schema only; the larger budgets above need
an actual eligible pool of sufficient size. Export metadata from a verified adapter
after source/target exclusion. Only `id` and `group` are accepted per row. Extra
endpoint columns fail rather than silently entering this planner. The explicit
exclusion list is checked against all eligible IDs.

The planner assigns validation groups once using a shuffled group prefix closest
to the requested row fraction, then independently samples canonicalized fitting
and validation rows. Both sequences retain prefixes across increasing budgets;
validation labels count toward the total. A pool-metadata hash, seed, capacities,
group assignments and selected IDs are saved. Existing output files are never
overwritten. No labels are loaded or revealed, no models run, and no results are
fabricated. Planning more IDs does not authorize their labels for smaller-budget
training: downstream fitters must receive only the selected allocation.

## Boundaries and next integration work

- Group construction remains the dataset adapter's responsibility. If both patent
  and compound disjointness are required, construct connected components of those
  relationships first. This planner does not infer biological equivalence from IDs
  or guarantee absence of near-sequence or cross-source leakage.
- One group or insufficient partition capacity fails explicitly. Do not retry seeds
  after outcomes to obtain an attractive split. Unequal groups can make the exact
  desired validation fraction or full-pool budget infeasible. Full-pool references
  need their own declared protocol; this utility does not silently refit them.
- This is a random budget allocation/control utility, not an active acquisition
  algorithm. Acquisition runners must retain their protected oracle, label-blind
  selection and deferred evaluation. Integrate a common initial allocation without
  exposing future randomly sampled labels to a learned acquisition policy.
- No generic training scheduler or automatic compatibility layer is implemented.
  Existing study runners remain authoritative. Next work is to export verified
  metadata, connect one runner to these allocations, and record matched model,
  endpoint, split, label budgets and metrics in a shared comparison receipt.
- Do not interpret correlation ratios as percentages of biological validity, or
  turn a toxicity endpoint into a general safety claim. Assay/context compatibility
  and measured-label provenance apply equally to every research track.

The new code uses only Python's standard library. It does not alter shared
dependencies, existing study configurations, the core oracle, or the running-model
implementation. Generated plans remain under ignored `artifacts/`.

## Verification of this infrastructure slice

Completed locally: 158 core tests passed, including 12 new infrastructure cases;
Ruff lint and formatting passed on 109 files. A synthetic CLI smoke run allocated
budgets 10/20/50/100 with fitting counts 8/16/40/80 and validation counts 2/4/10/20.
Its ignored output is
`artifacts/research-infrastructure-smoke-20261114/seed-510-plan.json`.
This verifies planning and accounting, not measured-data performance. No new
scientific training campaign was launched. The user subsequently authorized publishing
this infrastructure with the timestamped RL framework context; that publication does
not launch additional experiments.
