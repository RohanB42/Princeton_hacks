"""Reproduction must distinguish requested arguments from effective training."""

from types import ModuleType

import pytest

from oligo_engine.reproduce import execution_mode, prepare_baseline_model


def config(mode="direct_wrappers"):
    return {
        "seeds": [0, 1, 2, 3, 4],
        "execution_mode": mode,
        "split": {
            "strategy": "nucleobase",
            "test_size": 0.2,
            "n_clusters": 8,
            "kmer": True,
            "kmer_max": 3,
            "strand": "RNA1",
        },
        "model": {
            "name": "RandomForestModel",
            "n_estimators": 100,
            "max_depth": 20,
        },
    }


class Estimator:
    def __init__(self, **kwargs):
        self.params = {
            "n_estimators": 100,
            "max_depth": None,
            "random_state": None,
            "n_jobs": None,
            **kwargs,
        }

    def get_params(self, deep=False):
        return dict(self.params)

    def set_params(self, **kwargs):
        self.params.update(kwargs)


class Wrapper:
    def __init__(self, n_estimators=100, **model_kwargs):
        self.model = Estimator(n_estimators=n_estimators, **model_kwargs)


@pytest.mark.parametrize(
    "mode,depth,random_state,n_jobs",
    [
        ("direct_wrappers", 20, 2, 2),
        ("benchmark_model_factory", None, 2, 2),
        ("benchmark_helpers", None, None, None),
    ],
)
def test_factory_parameters_are_observed_without_reapplying_filtered_args(
    mode, depth, random_state, n_jobs
):
    calls = []
    benchmark = ModuleType("fixture_benchmark")

    def factory(value):
        calls.append(value)
        # Deliberately ignore max_depth/input_dim, as the audited factory does.
        return Wrapper(n_estimators=value["model_args"]["n_estimators"])

    benchmark.prepare_model = factory
    model, trace = prepare_baseline_model(config(mode), 2, 176, Wrapper, benchmark)
    assert model.model.get_params() == {
        "n_estimators": 100,
        "max_depth": depth,
        "random_state": random_state,
        "n_jobs": n_jobs,
    }
    assert trace["effective_estimator_params"] == model.model.get_params()
    assert trace["requested_model_args"]["max_depth"] == 20
    if mode == "direct_wrappers":
        assert calls == []
        assert trace["arguments_filtered_by_benchmark"] == {}
    else:
        assert calls == [
            {
                "model": "RandomForestModel",
                "model_args": {
                    "n_estimators": 100,
                    "max_depth": 20,
                    "input_dim": 176,
                },
            }
        ]
        assert trace["arguments_filtered_by_benchmark"] == {
            "max_depth": 20,
            "input_dim": 176,
        }
    assert trace["explicit_estimator_overrides"] == (
        {} if mode == "benchmark_helpers" else {"random_state": 2, "n_jobs": 2}
    )


def test_script_helpers_cannot_silently_ignore_a_changed_split_config():
    value = config("benchmark_helpers")
    value["split"]["n_clusters"] = 9
    with pytest.raises(ValueError, match="audited default split"):
        execution_mode(value)
    value = config("benchmark_helpers")
    value["split"]["strategy"] = "target"
    with pytest.raises(ValueError, match="audited default split"):
        execution_mode(value)


@pytest.mark.parametrize("seeds", [[], [0, 0], [-1], [True], [1.5]])
def test_baseline_seed_schedule_is_validated(seeds):
    value = config()
    value["seeds"] = seeds
    with pytest.raises(ValueError, match="distinct nonnegative"):
        execution_mode(value)


def test_unknown_execution_mode_and_missing_helpers_fail_closed():
    with pytest.raises(ValueError, match="Unknown baseline"):
        execution_mode(config("unknown"))
    with pytest.raises(ValueError, match="audited training helpers"):
        prepare_baseline_model(config("benchmark_helpers"), 0, 176, Wrapper, None)


def test_old_configs_preserve_direct_wrapper_semantics():
    value = config()
    value.pop("execution_mode")
    assert execution_mode(value) == "direct_wrappers"
