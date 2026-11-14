# Reward adapter: how it works

The adapter scores an unmeasured ASO candidate with independently supplied
predictors. It returns an inspectable `RewardScore` and gives an optimizer a
number only when every required check passes. The current implementation uses
deterministic mock predictors and a restricted A/C/G/T fixture representation.

## Scoring path

1. A `Candidate` records its sequence, modality, chemistry name, target and assay
   context. Its content hash changes when any of these fields changes.
2. Each predictor declares its endpoint, units, direction, accepted chemistry,
   required context, artifact identity, and frozen training range. The adapter
   checks applicability before requesting a prediction.
3. The result keeps the original prediction and units. The value used in the
   reward is clipped to the declared training range and scaled to 0–1. For a
   lower-is-better endpoint, the scale is reversed.
4. Configured constraints can reject a candidate. The provided checks cover
   length, a maximum endpoint value, and complementarity to an explicitly
   supplied `verified_target_site`. Missing inputs fail the check.
5. Disagreement groups compare normalized predictions only when their models
   declare the same endpoint, units, direction, chemistry scope, context,
   training range, and normalization identity. Novelty uses fractional Hamming
   distance to a frozen, chemistry-matched A/C/G/T reference.
6. Accepted candidates receive a weighted sum of normalized endpoint scores
   minus declared penalties. Rejected candidates have `reward=None` and stable
   reason codes. `policy_reward()` raises on rejection.

The result also includes individual endpoint scores, constraint decisions,
disagreement and novelty diagnostics, reward contributions, and hashes of the
candidate, configuration, models, and novelty reference. `predictor_calls`
counts actual calls to injected predictors; no cache is currently used.

## Minimal mock example

```python
from oligo_engine.design.reward import (
    Candidate, EndpointMetadata, MockPredictor, MultiEndpointReward, RewardConfig,
)

model = MockPredictor(
    EndpointMetadata(
        endpoint_id="potency", endpoint_kind="efficacy", modality="ASO",
        direction="higher_is_better", units="percent",
        chemistry_scope=("PS_2MOE",), label_range=(0.0, 100.0),
        artifact_hash="fixture-model", training_hash="fixture-training",
        split_hash="fixture-split", normalization_hash="fixture-range",
    ),
    value=80.0,
)
adapter = MultiEndpointReward(
    (model,), RewardConfig(("potency",), (("potency", 1.0),))
)
result = adapter.score(Candidate("AAAA", "ASO", "PS_2MOE"))
assert result.reward == 0.8
```

The `PS_2MOE` string in this fixture is an applicability label. It does not
verify an ordered sugar/backbone modification pattern. Production scoring needs
a verified chemistry parser, feature schema, and loadable model manifest from
the predictor owner. The adapter does not train or reload models. Its scores are
surrogate engineering outputs, not measured efficacy or safety.

See [the detailed contract](multi-endpoint-reward-adapter.md) and
`tests/test_reward_adapter.py` for rejection cases and invariant checks.
