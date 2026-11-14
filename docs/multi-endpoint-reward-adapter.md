# Multi-endpoint reward adapter specification

Status: proposed independent implementation spec

This document defines the contract for a deterministic adapter that scores an
ASO design candidate with independently trained, frozen endpoint predictors. It
is deliberately implementable with mock predictors before Atlas post-training
is available. It does not authorize model selection, endpoint pooling, or
biological claims.

## 1. Purpose and boundary

The adapter is a policy-facing boundary between candidate generation and one or
more frozen predictors. It must preserve endpoint identity while producing a
scalar reward only when the candidate is applicable to every required endpoint
and passes all hard constraints.

The adapter may optimize frozen surrogate predictions. It must never imply that a
candidate is measured, potent, safe, clinically useful, or experimentally
validated. A prediction is not an observation.

The first implementation should support injected deterministic mock predictors
and existing compatible OligoGym predictors. Atlas predictors can be added later
without changing the adapter contract.

Out of scope:

- training, fine-tuning, or selecting endpoint models;
- combining siRNA efficacy with ASO safety or efficacy;
- silently imputing missing endpoint predictions;
- treating an unavailable safety head as zero risk;
- using test labels, candidate measurements, or downstream wet-lab results;
- making dose, cell line, target, or chemistry an optimization action unless a
  separate approved environment contract exists.

## 2. Required concepts

### 2.1 Candidate

A candidate is an immutable, label-free design record containing at least:

```text
candidate_id       stable hash of canonical candidate content
modality           e.g. ASO; never inferred from sequence alone
sequence_or_helm   original candidate representation
canonical_chemistry chemistry identity and ordered modification pattern
target_context     target/site identifier and any required context
assay_context      dose, cell, species, route, duration, if required by a head
source             generated, fixture, or imported; never measured by inference
```

Canonicalization must be lossless with respect to the original representation.
The original sequence/HELM is retained for reporting, while the canonical form
is used only for identity and applicability checks. Unsupported or ambiguous
chemistry fails closed.

### 2.2 Frozen endpoint predictor

Every predictor is loaded from a versioned artifact and exposes metadata before
it can score a candidate:

```text
endpoint_id       unique stable name, e.g. aso_potency
modality          compatible modality
endpoint_kind     efficacy, potency, neurotoxicity, hepatotoxicity, etc.
direction         higher_is_better or lower_is_better
units             source units, never inferred by the adapter
chemistry_scope   explicit allowed chemistry family/pattern
context_schema    required candidate context fields
feature_schema    representation and version
label_range       training-label range, if defined
normalization     frozen training-only rank/quantile parameters
uncertainty_type  none, ensemble_spread, GP_std, interval, or other named type
training_hash     training-row/data identity hash
split_hash        split-manifest identity hash
model_hash        artifact/checkpoint hash
software_identity package and revision identity
```

The predictor interface is conceptually:

```python
predictor.predict(candidate) -> RawPrediction
predictor.metadata -> EndpointMetadata
```

The adapter must reject a predictor whose metadata is incomplete, inconsistent,
or incompatible with the candidate contract.

### 2.3 Reward configuration

The configuration is immutable for a run and contains:

```text
required_endpoints        endpoint IDs that must score successfully
optional_endpoints        endpoint IDs reported when applicable
hard_constraints           named predicates and thresholds
normalization_policy      frozen per-endpoint training-only transforms
endpoint_weights           only for approved scalar composition
disagreement_policy       heads, metric, scale, threshold, penalty
novelty_policy             reference set, representation, threshold, penalty
missing_head_policy       fail, reject, or report-only; never zero-risk
out_of_range_policy       clip for reward, preserve raw value for reporting
reward_formula_version     explicit semantic version
```

Weights and thresholds must be present in the versioned config, not hidden in
code or tuned from held-out outcomes.

## 3. Output contract

The adapter returns a complete immutable `RewardScore` even for rejected
candidates. Rejected candidates must explain why and must not contain an
executable scalar reward.

```text
RewardScore
  candidate_id
  status                    accepted | rejected | not_applicable | error
  raw_predictions[]
    endpoint_id
    value
    units
    direction
    uncertainty
    uncertainty_type
    model_identity
  normalized_scores[]
    endpoint_id
    value in declared normalized range
    normalization_identity
  applicability[]
    endpoint_id
    applicable: bool
    chemistry_result
    context_result
    reason_codes[]
  constraints[]
    name
    passed: bool
    observed_value
    threshold
    units
    reason
  disagreement
    participating_endpoints[]
    metric
    value
    threshold
    penalty
    status
  novelty
    reference_identity
    representation
    nearest_distance
    threshold
    penalty
    status
  reward
    value or null
    reward_formula_version
  provenance
    source_revision
    model_artifacts[]
    config_hash
    candidate_hash
    code_revision
    environment_identity
```

Raw predictions and units are never replaced by normalized values. The scalar
reward is optional and is present only for `accepted` results.

## 4. Scoring algorithm

The scoring order is fixed to make failures auditable:

1. Validate the candidate schema and compute its stable identity.
2. Validate all predictor metadata and the reward configuration.
3. Check modality, chemistry, representation, and required context for every
   required endpoint.
4. Reject immediately if a required endpoint is not applicable. Optional heads
   may be reported as unavailable, but may not silently contribute zero risk.
5. Obtain raw predictions from frozen predictors. Reject nonfinite, malformed, or
   unit-inconsistent outputs.
6. Preserve raw values exactly as returned. Apply declared training-range
   clipping only to the reward path and record both original and clipped values.
7. Apply training-only normalization. Normalization parameters must come from the
   predictor artifact or immutable config, never from candidate, test, or reward
   results.
8. Evaluate hard constraints. A failed safety, chemistry, validity, or domain
   constraint rejects the candidate.
9. Compute disagreement only among compatible heads with an explicitly declared
   comparable endpoint scale. Incompatible endpoints must not be compared.
10. Compute novelty against a frozen, label-free reference representation. Record
    the nearest distance and whether the candidate exceeds the declared threshold.
11. Compose the scalar reward from normalized endpoint terms and declared
    penalties only if all required gates pass.
12. Emit the complete result and deterministic provenance record.

The adapter must be pure from the caller's perspective: identical candidate,
predictor artifacts, configuration, and environment identity produce identical
status, values, reason codes, and reward. Caching is allowed only if cache keys
include all scoring identities.

## 5. Applicability and chemistry gates

Applicability is endpoint-specific. Each head declares its accepted modality,
chemistry family, positional pattern, length range, context requirements, and
training-domain bounds.

Minimum gates:

- modality matches exactly;
- chemistry is fully parsed and supported;
- ordered sugar/backbone/base modifications match the head scope;
- length and required structural fields are valid;
- required target, assay, dose, cell, species, route, and duration fields exist;
- candidate representation matches the predictor feature schema;
- no unsupported or ambiguous token was silently skipped;
- no candidate edit violates the upstream environment's validity contract.

Reason codes must be stable strings such as `MODALITY_MISMATCH`,
`CHEMISTRY_UNSUPPORTED`, `PARTIAL_PARSE`, `MISSING_CONTEXT`,
`LENGTH_OUT_OF_RANGE`, and `FEATURE_SCHEMA_MISMATCH`.

## 6. Constraints, disagreement, and novelty

### Hard constraints

Constraints are predicates, not arbitrary reward subtractions. Examples include
chemistry validity, complementarity preservation, maximum predicted toxicity,
minimum applicability coverage, and declared domain-distance limits.

Each constraint records its observed value, threshold, units, and source. Missing
required safety coverage fails closed; it is never converted to a safe value.

### Model disagreement

Disagreement is computed only where models predict the same endpoint, units,
direction, and compatible chemistry/context domain. The first supported metric
should be absolute difference after endpoint-specific training-only normalization.

If the value exceeds the configured threshold, the adapter either rejects the
candidate or applies a declared penalty. The choice is configuration-driven and
reported in the output. Cross-endpoint disagreement, such as potency versus
neurotoxicity, is invalid.

### Novelty

Novelty uses a frozen label-free reference set and a versioned representation.
The first implementation may use normalized one-hot or k-mer distance, but must
record the representation version and reference hash. A candidate beyond the
declared extrapolation threshold is rejected or penalized according to config.

Novelty is not uncertainty and must not be described as calibrated uncertainty.
The reference set may contain training candidates, but must not contain hidden
evaluation labels or predictions used to tune the threshold.

## 7. Reward composition

The initial composition is intentionally simple:

```text
base = sum(weight_i * normalized_endpoint_i)
reward = base - disagreement_penalty - novelty_penalty
```

All endpoint terms must have an explicitly documented direction. Lower-is-better
endpoints must be transformed before composition, while raw values remain in the
original units. Hard constraints are evaluated before composition and are not
replaced by large negative rewards.

The adapter must expose the contribution of every endpoint and penalty so a
caller can audit why two candidates ranked differently. Reward weights are not
scientific evidence of biological importance.

## 8. Validation plan

### Unit validation

Implement tests for:

1. deterministic scoring with a fixed mock predictor;
2. stable candidate hashing and canonicalization;
3. raw values and units preserved exactly;
4. correct higher/lower-is-better normalization;
5. training-only clipping and normalization;
6. modality and chemistry rejection;
7. partial-parse and unsupported-token rejection;
8. missing required context rejection;
9. nonfinite prediction rejection;
10. missing required safety head rejection;
11. optional-head reporting without zero-risk substitution;
12. hard-constraint pass and fail paths;
13. disagreement calculation and threshold behavior;
14. novelty calculation and threshold behavior;
15. deterministic reward composition and per-term contributions;
16. provenance completeness and config/model hashes;
17. cache-key separation across model/config/reference revisions.

### Invariant and adversarial validation

Add tests proving that:

- changing a hidden label does not change a score;
- predictions cannot be promoted to observations;
- a test-set row or test label cannot enter normalization, novelty, or tuning;
- incompatible siRNA and ASO predictors cannot score one candidate together;
- a missing toxicity prediction never becomes zero toxicity;
- changing raw prediction units without changing metadata fails validation;
- changing a predictor artifact changes provenance and invalidates stale caches;
- a rejected candidate never exposes a usable scalar reward;
- repeated scoring is bitwise-equivalent for deterministic predictors;
- all output reason codes are stable and machine-readable.

### Property-based validation

For generated valid candidates, assert that canonicalization is idempotent,
candidate IDs are stable, and accepted rewards remain finite. For generated
invalid chemistry/context records, assert fail-closed behavior and no reward.
For monotonic mock predictors, verify that improving a higher-is-better endpoint
cannot lower the reward unless a declared constraint, disagreement penalty, or
novelty penalty changes.

### Integration acceptance test

Create three deterministic mock heads:

- potency: higher is better, chemistry `PS_2MOE`;
- neurotoxicity: lower is better, chemistry `PS_2MOE`;
- incompatible TLR head: `2OMe` only.

Run a fixed panel containing valid, unsupported-chemistry, missing-context,
high-disagreement, novel, and hard-constraint-failing candidates. The acceptance
report must include exact expected raw predictions, normalized terms, reason
codes, penalties, status, and reward. No Atlas training, network access, or
measured test labels are allowed in this test.

## 9. Artifact and provenance requirements

Every scoring batch writes or returns:

- reward-config hash and semantic version;
- candidate identity and original representation hash;
- endpoint model IDs, artifact hashes, training-data hashes, and split hashes;
- feature and normalization identities;
- chemistry/parser version;
- novelty reference hash and representation;
- code revision and clean/dirty status;
- environment/package identity;
- complete reason codes and gate outcomes.

Generated scoring artifacts are diagnostic outputs and should remain ignored
unless a reviewed report explicitly promotes a small reproducible fixture.

## 10. Implementation sequence and exit criteria

### Slice A: contracts and mocks

Add typed metadata, candidate, prediction, applicability, constraint, provenance,
and `RewardScore` contracts plus deterministic mock predictors. Exit when unit,
schema, and adversarial tests pass.

### Slice B: deterministic adapter

Implement the scoring order, fail-closed behavior, normalization, clipping,
disagreement, novelty, and reward composition. Exit when the integration panel
matches its frozen expected output.

### Slice C: existing compatible predictor integration

Connect only predictors whose modality, chemistry, units, feature schema, and
evaluation evidence are documented. Do not add Atlas predictors until their
post-training owner supplies a loadable artifact and manifest. Exit when save,
reload, and score equality pass.

### Slice D: policy-facing integration

Expose accepted scalar rewards to an optimizer while exposing complete rejected
results for diagnostics. Enforce scorer budgets and cache identity. Exit when an
optimizer cannot obtain a reward from a rejected or inapplicable candidate.

The adapter is ready for ASO RL engineering when all four slices pass, all
required invariants pass, and the output manifest is complete. It is ready for a
scientific ASO reward claim only after endpoint-specific held-out evidence and
independent measured validation satisfy the project evaluation protocol.

## Mock implementation and predictor handoff (2026-11-14)

`src/oligo_engine/design/reward.py` now provides a restricted `fixture-acgt-v1`
contract. The chemistry string is a declared fixture scope, not a full HELM parser.
Production chemistry and model artifacts remain unconnected. A production wrapper
must supply a verified parser and feature schema before it can score candidates.

Minimal deterministic example:

```python
from oligo_engine.design.reward import (
    Candidate, EndpointMetadata, MockPredictor, MultiEndpointReward, RewardConfig,
)

metadata = EndpointMetadata(
    endpoint_id="potency", endpoint_kind="efficacy", modality="ASO",
    direction="higher_is_better", units="percent",
    chemistry_scope=("PS_2MOE",), label_range=(0.0, 100.0),
    artifact_hash="fixture-model-v1", training_hash="fixture-training-v1",
    split_hash="fixture-split-v1", normalization_hash="fixture-range-v1",
)
engine = MultiEndpointReward(
    (MockPredictor(metadata, 80.0),),
    RewardConfig(("potency",), (("potency", 1.0),)),
)
result = engine.score(Candidate("AAAA", "ASO", "PS_2MOE"))
assert result.reward == 0.8
```

The post-training owner should provide a versioned manifest with endpoint ID,
kind, direction, units, modality, chemistry scope, required assay and target
context, feature and parser schema, training and split hashes, training-label
normalization range and hash, held-out evaluation evidence and limits, artifact
hash, source revision, and software versions. The predictor wrapper must expose
this metadata and `predict(candidate) -> RawPrediction`; it must be verified
against the saved model before integration. No general pickle or joblib loader is
provided, and no Atlas predictor is approved here.

Current code validates exact fixture A/C/G/T sequences, model applicability,
required context, frozen range scaling, optional heads, typed length,
complementarity and endpoint-max gates, endpoint-compatible disagreement,
fractional Hamming novelty, provenance hashes and a policy-facing scalar method.
The example's `PS_2MOE` name does not verify sugar or backbone positions. A real
candidate requires the later chemistry adapter and verified transcript context.

Validation: 13 adapter tests passed under the available Python 3.13 environment;
Ruff checks and formatting passed on the adapter files. The prescribed `make lint
format-check import-check test` could not start because Poetry was not installed
in this shell. No scientific endpoint metrics are produced by these mock tests.
