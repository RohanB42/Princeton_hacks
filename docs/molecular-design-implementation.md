# Molecular design: implementation and execution record

Implemented on `feature/molecular-design-v1` after the user's explicit approval of
the [final specification](FINAL_MOLECULAR_DESIGN_RL_SPEC.md). The new environment,
frozen-model adapters, PPO/baselines, resume, exports and local interface execute
end to end. **The full scientific system is not yet qualified:** expanded-chemistry
efficacy validation and applicable independent evaluation remain blocked. The
combined real-model profile is explicitly a development diagnostic. Gate 1 and the
separate siRNA studies are unchanged. Generated molecules are unvalidated hypotheses.

Subsequent correction: the no-COMMIT failure is repaired by the versioned
[complete-proposal decoder](molecular-construction-fix.md). New training defaults
to `transactional-v2`; the editor-style behavior and bounded results described
below are historical v1 where indicated. The corrected three-seed rerun completes
seven new designs in every eight-request evaluation, without changing predictors,
screens or molecular rewards. Scientific qualification gates remain open.

## Contracts implemented

The package is `src/oligo_engine/molecular_design/`. It does not restore the retired
window-movement environment or use the candidate app's all-label fitting route.

| Component | Behavior and invariants |
| --- | --- |
| Campaign/profile | Immutable sequence, transcript/source identity, zero-based half-open permitted intervals, exact-complement mechanism, patterns, assay contexts and finite query/token budgets. Reject inadequate capacities rather than truncating inputs. |
| Chemistry | Ordered base/sugar/linkage tracks, methylated C, terminal groups, variable lengths and gap/wing layouts. Molecule, target-design and compound-assessment identities stay distinct. No invented stereochemistry or arbitrary base substitutions. |
| Construction | `NEW → LENGTH → SITE → LAYOUT → PATTERN → TERMINAL → COMMIT`: seven tokens for a new complete design. In v2, parent edits proceed forward to COMMIT and STOP occurs at campaign boundaries after one new proposal; open-ended cancellation remains legacy-only. Masks use structural/profile/visited-identity constraints, never unqueried scores. |
| Observation | Full target and allowed-region tracks, all chemistry tracks, construction state, full bounded query history including duplicates and failed screens, raw predictions/missingness/diagnostics and remaining budgets. |
| Policy | MaskablePPO; target convolutions and construction-conditioned attention over all target positions and history rows. Pooling remains lossy; representational sufficiency is not proven. |
| Scoring | Frozen hash-verified bundles, separate assay context per head, objective/required-screen/advisory roles. Unsupported or missing required endpoints cannot pass. Infrastructure failure aborts and is recorded, never treated as a biological penalty. |
| Cost | Starts, complete proposals and cache hits consume requests. Actual head calls are counted separately. No predictor calls at Gym construction or on partial molecules. Each arm owns its cache. |
| Reward | `Q(A_next) − Q(A)`; Q is best eligible training-reference empirical-CDF efficacy utility, zero for an empty eligible archive. Construction/cancel/STOP reward zero. Gamma and GAE lambda one. Return telescopes to improvement over the charged starting archive. |
| Alternative objective | Exact hypervolume union with fixed bounded reference and normalization; explicit dimensions. No arbitrary weighted safety/efficacy sum. |
| Controls | Uniform complete-design random proposals, multi-start greedy, structural genetic search, sweep, initial-only and costed exhaustive enumeration. Shared legal space, starts, scorer and request cap. |
| Training | Complete bounded rollouts, validation after updates, maximum validation mean archive quality with earliest tie. Final campaigns cannot tune checkpoint selection. Costs include the last partial training episode. |
| Persistence | Schema/hash-checked inference; exact continuation at consumed-rollout boundaries with optimizer, RNG, monitor, environment and archive. Mid-rollout resume is not offered. |
| Artifacts | Immutable sealed JSON, durable hash-chained query JSONL including initial failures, action traces, model manifests, costs and CSV. Seals detect modification, not scientific validity or external authorship. Existing outputs are never overwritten. |
| Panels | Unique compounds; Pareto tiers then deterministic utility/diversity. Diversity changes presentation only. Shortfalls and zero eligible candidates stay visible. |
| Evaluation | Separate sealed exact-assessment capability; missing measurements stay missing. Independent evaluator requires context/scope/overlap evidence. Target-level paired bootstrap reports insufficient groups as undefined. |
| Interface | Frozen campaign, method, budget, seed, panel preferences, coverage, initial/final quality, raw endpoints/units/status, matched session runs and JSON/CSV downloads. No fitting/download in request handling. |

## Real profiles and scientific limits

- Fixture: four MOE/cEt patterns at lengths 8 and 10 with synthetic efficacy/risk.
- Portable efficacy ablation: published 20-mer MOE 5-10-5/all-PS/m5C Ridge, human
  HepG2, electroporation, 4,500 nM, 24 h. Risk unknown.
- Atlas efficacy stress: actual source Ridge, lengths 18 and 20, three
  metadata-selected MOE patterns with different linkages; broader efficacy support
  unvalidated.
- Multi-endpoint development diagnostic: Atlas efficacy stress plus a separately
  fitted development mouse acute-FOB screen. Human cell efficacy and mouse risk
  retain different contexts/units; neither establishes human safety or in vivo efficacy.

The label-free metadata audit verifies release hashes and finds 24 shared
efficacy/neuro structural patterns. Structural overlap is not predictive validation.
The existing Atlas Ridge validation membership has **32 exact HepG2-context rows
and zero rows matching the three expanded patterns**. No outcomes were read in
that check. These saved validation data cannot qualify the expanded efficacy scope.

`full` profiles reject extrapolation-stress applicability. A real locked comparison
requires five final target groups, five paired policy/search seeds, a compatible
full profile and sealed gate evidence bound to the exact registry/campaigns. Plain
nonempty evidence strings cannot satisfy it. These checks prevent renaming the
diagnostic as the completed scientific system.

### Mouse acute-risk development

`scripts/qualify_molecular_heads.py` separates metadata preparation from fitting.
Context: C57BL/6 mouse, 700 micrograms ICV, 3 h, Behavioral FOB. Higher 0–7 scores
indicate more abnormal behavior; incompatible scales and chronic/human endpoints
must remain separate. Primary context references are the
[acute ASO response study](https://doi.org/10.1093/nar/gkaf1333) and
[patent assay description](https://patents.google.com/patent/US9605263B2/en).
These motivate interpretation, not blanket validation of every extracted record.

Exact chemistry/context selection admitted 1,720 records. Connected patent,
sequence, Hamming-distance-at-most-two and exact one-base-shift groups were built
before splitting: 14 groups. Fixed metadata-only allocation used five final, two
calibration, two development and five fit groups, with per-pattern minima. This
does not establish unseen-target generalization or complete patent-family linkage.

The initial fit stopped before model fitting on one absent fit outcome. A separate
sealed schema amendment records the discovery and the nonfinal outcomes already
read. That row was excluded without imputation; group allocation, model choices,
numeric labels and acceptance rules stayed fixed. Final outcomes were never read.
Usable counts: 873 fit, 259 development, 283 calibration; 304 final records sealed.

Fixed candidates: Ridge alpha 10 and RF 256 trees/depth 12/seed 1729, selected by
development RMSE, Ridge on ties. Ridge RMSE **1.2861**, RF **1.3776**, fit-mean
baseline **2.4166**. The relative screen from zero through median fit prediction
**2.8470** retained 231/259 development records (89.19%); measured mean **0.8049**
versus pool **0.8607**. This passes the predeclared development check. Enrichment
is modest and uses selection data; the threshold is not a clinical safety bound.
Calibration residuals are stored without claiming exchangeability or calibrated
uncertainty. Final risk qualification remains open.

Portable coefficients/trees pass direct sklearn anchor parity. The application
cannot fit them. New model weights remain ignored local artifacts, outside the
previously authorized published checkpoint directory.

## Executed evidence

Artifacts: `artifacts/molecular-design-v1/`, intentionally unversioned. All **287**
published checkpoints passed hash/size inventory. Atlas Ridge source/export parity
was exact on checked anchors. Actual frozen RNA-FM and LoRA workers reconstructed
their source checkpoints in the pinned owner runtime with the verified external
backbone. Reversed batches agreed exactly; singleton/batch maximum differences
were approximately `1.91e-6` and `3.81e-6`. These are inference checks, not
independent evaluation or evidence of architecture superiority.

| Artifact | Result and scope |
| --- | --- |
| `fixture-comparison-final/` | Five policy seeds × five final synthetic targets × six methods = 150 final arms; 12 requests. Development selected greedy. PPO-minus-greedy mean **−0.32772**, target-bootstrap 95% interval **[−0.46535, −0.19010]**. Engineering only. |
| `atlas-policy-v2/` | 2,048 tokens, policy seed 700; DGAT2 train, CFB validation; checkpoint selected at 1,024. 607 training requests, 583 head calls, two validation requests. Policy retained initial quality on all three diagnostic targets. |
| `multi-endpoint-controls/` | 75 arms: three targets, five seeds, five methods, eight requests including starts. Some methods found eligible DGAT2/CFB designs; all tested FGFR4 arms had zero eligible quality. |
| `multi-endpoint-policy/` | 2,048 tokens, one policy seed; 514 training requests, 938 head calls, two validation requests; selected at 1,024. |
| `multi-endpoint-policy-evaluation/` | 15 deterministic rollouts, all zero eligible quality. Five rollout seeds of one policy are not five independently trained policies. Negative development diagnostic, not final study. |

Bounded policies often stop without another complete proposal. No stopping bonus,
weaker screen or post hoc final tuning was added to manufacture a win. Before
expanding training, diagnose construction completion, sparse credit and campaign
diversity on development data. Efficacy-only DGAT2 starts near utility saturation,
so provides little improvement signal.
At the eight-request diagnostic cap, the default eight-member genetic population
only completes initialization; this arm does not demonstrate evolutionary search.
The final study must cost an informative population/search phase explicitly.

Earlier fixture runs are historical; `fixture-comparison-final/` includes the
constructor no-query regression, journals and sweep/exhaustive accounting fix.
`atlas-policy-v2/` supersedes `atlas-policy/`. Conventional results preceding the
sweep correction must not be silently pooled with later results.

## Reproduction

Python 3.11, Poetry 2.1.4. Core imports do not require Torch. Optional groups pin
NumPy 1.26.4, Gymnasium 1.1.1, SB3/sb3-contrib 2.6.0, Torch 2.3.1, pandas 2.2.3 and
PyArrow 21.0.0; science pins sklearn 1.4.0. Existing neural checkpoints retain their
separate pinned Atlas runtime.

```sh
make setup-molecular
make lint format-check import-check test
make molecular-test
make molecular-fixture
```

The fixture writes `artifacts/molecular-fixture`; use fresh output paths for reruns:

```sh
poetry run python -m oligo_engine.molecular_design preflight \
  --config configs/molecular-design/fixture.json --output artifacts/my-preflight.json
poetry run python -m oligo_engine.molecular_design search \
  --config configs/molecular-design/fixture.json --output artifacts/my-controls
poetry run python -m oligo_engine.molecular_design train \
  --config configs/molecular-design/fixture.json --output artifacts/my-policy
poetry run python -m oligo_engine.molecular_design policy-evaluate \
  --config configs/molecular-design/fixture.json --policy artifacts/my-policy \
  --output artifacts/my-rollouts
poetry run python app/molecular_server.py \
  --config configs/molecular-design/fixture.json --policy artifacts/my-policy \
  --output artifacts/my-app --port 8001
```

Open `http://127.0.0.1:8001`. Final campaigns are blocked in the interactive app.
JSON configuration is the compiler interface for new pinned transcripts/regions;
the page never silently accepts unsupported custom chemistries.

Existing local real diagnostic, after `make setup-molecular`:

```sh
poetry run python app/molecular_server.py \
  --config artifacts/molecular-design-v1/multi-endpoint-config.json \
  --policy artifacts/molecular-decoder-fix-v2/batch-64/seed-700 \
  --output artifacts/molecular-live --port 8001
```

For new real configs, run `metadata-audit`; export the manifest-listed Ridge with
`scripts/export_atlas_ridge.py` in its verified owner checkout; then run
`scripts/prepare_molecular_config.py --kind atlas-stress --atlas-export ...
--metadata-audit ... --output ...`. Cached transcripts are required at
`artifacts/transcripts` or `--transcripts`. Export checks source revision/hash,
training-reference membership and the source selection receipt. The owner
checkout/receipt and FM backbone remain external dependencies, not a self-contained
redistribution.

Risk preparation: `scripts/qualify_molecular_heads.py prepare --config ... --output
...`, followed by `fit --output ...`. Missing inputs block; missing-label amendments
must be separately sealed. Attach a passing development export using the profile
helper's `--risk-qualification ...`; it creates a diagnostic, never a `full` profile.
Neither phase exposes final outcomes. The separate evaluator accepts sealed
archives and restricted capabilities; it has no default final-dataset reader or
nearest-neighbor measurement substitution.

## Verification and remaining acceptance gates

The subsequent [shared-candidate revision](molecular-policy-repair.md) adds a
position-independent molecular scorer, costed training-only pretraining and
return-preserving forced transitions. Its fixed multi-target study and ablations
are separate from the historical experiments below. Ten optional RL tests cover
both original and new policies, including exact continuation and unchanged rewards.

The current [five-seed optimizer comparison](molecular-optimizer-comparison.md)
evaluates the corrected decoder against history-aware random and greedy controls.
All 135 runs complete their scoring budgets without duplicate queries. Performance
is mixed across the three development targets; PPO superiority is not established.
Current checks pass 230 core tests and six optional Gym/PPO integration tests.
The earlier batch-sweep results below remain historical diagnostics.

Follow-up requested minibatch sweep: `scripts/molecular_batch_sweep.py` now freezes
and executes sizes 32/64/128 with seeds 700/701/702 and 2,048 actions per arm. PPO
training persists critic/policy/entropy/KL diagnostics after every update, including
the last one. Results and PNG/PDF/CSV exports are in
`artifacts/molecular-batch-sweep-v1/`. Mean final-update critic MSE was 0.004596,
0.001228 and 0.001317 respectively. All 27 deterministic evaluations scored no
new molecule: 15 exhausted construction tokens in edit/cancel loops and 12 stopped
(nine immediately). This action audit refines the earlier broad stopping diagnosis:
failure to reach COMMIT, including looping, is central. Lower critic loss did not
produce better search. At the matched eight-request cap and these three seeds,
random averaged 0.600846 utility on DGAT2; greedy averaged 0.145943 on CFB; all PPO
arms had zero utility. Targets retain their training/validation/development roles.
No final outcomes were accessed and no optimal-batch-size claim is justified.

Local checks: **224 core tests**, **four real Gym/PPO tests**, **three optional
robustness tests**; Ruff lint/format, import and Poetry lock checks pass. Resume is
tested parameter-for-parameter against uninterrupted training. `make fixture`
refused an occupied historical output; the same command passed with a fresh
directory, producing five synthetic runs. Data integrity tests remain green. Local
HTTP/Chrome checks exercised real search, nonempty and empty panels, shortfall,
scope warnings and exports. The optional CI job is added but hosted CI was not run.

| Gate | Disposition |
| --- | --- |
| A: supported task | Blocked: zero matching expanded-chemistry efficacy validation rows at the selected context; final campaign/exposure qualification incomplete. |
| B: actual inference | Checked actual Ridge/FM/LoRA and risk parity pass; this does not prove full-profile applicability. |
| C: construction | Multiple patterns/lengths, canonical identity, complementarity and masks tested; support remains governed by A. |
| D: RL correctness | Reward, accounting, history, reload and resume checks pass; bounded policies underperform. |
| E: real study | Harness/synthetic matrix complete; real full-profile five-policy-seed/five-final-group study blocked by A/F. Diagnostics are not its replacement. |
| F: independent evidence | Boundary implemented; compatible evaluator unqualified, risk final outcomes sealed. No biological validation. |
| G: delivery | CLI/UI/exports/journals and pinned runtime work; clean-machine real replay still requires the external owner artifacts/backbone. |

Resolving A/F requires a separately frozen endpoint protocol with adequate expanded
efficacy coverage and an audited evaluator or exact recorded-pool assessment. This
is remaining scientific work, not permission to call an unsupported model safe or
to report the full intended study complete.
