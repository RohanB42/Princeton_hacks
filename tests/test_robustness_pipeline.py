"""End-to-end scientific leakage, archive sealing and immutable resume tests."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from oligo_engine.robustness.adapters import OutcomeCapability
from oligo_engine.robustness.fixture import source
from oligo_engine.robustness.optimization import optimize, verify_seal
from oligo_engine.robustness.pipeline import STAGES, AuditPipeline


def config():
    return json.loads(Path("configs/robustness/fixture-v1.json").read_text())


class LoggedSource:
    def __init__(self, underlying, final_ids=(), offset=0.0):
        self.rows, self.receipt = underlying.rows, underlying.receipt
        self.underlying, self.final_ids, self.offset = (
            underlying,
            set(final_ids),
            offset,
        )
        self.reads = []

    def outcomes(self, allowed):
        original = self.underlying.outcomes(allowed)

        def read(ids):
            self.reads.extend(ids)
            values = original.read(ids)
            return {
                key: value + (self.offset if key in self.final_ids else 0)
                for key, value in values.items()
            }

        return OutcomeCapability(allowed, read)


def test_final_poisoning_cannot_change_models_guardrails_or_search(tmp_path):
    original = source()
    first_source = LoggedSource(original)
    first = AuditPipeline(config(), tmp_path / "first", first_source)
    final = set(first.split.final)
    for stage in STAGES[:7]:
        first.run_stage(stage)
        assert not final & set(first_source.reads)
    second_source = LoggedSource(original, final, 10000.0)
    second = AuditPipeline(config(), tmp_path / "second", second_source)
    for stage in STAGES[:7]:
        second.run_stage(stage)
    for stage in ("predict", "diagnose", "select-guardrail"):
        assert first.store.read(stage) == second.store.read(stage)
    a, b = first.store.read("optimize"), second.store.read("optimize")
    assert [r["seal"] for r in a["runs"]] == [r["seal"] for r in b["runs"]]
    result = first.run_stage("evaluate")
    poisoned = second.run_stage("evaluate")
    assert result["metrics"]["macro_rmse"] != poisoned["metrics"]["macro_rmse"]
    assert final <= set(first_source.reads)
    assert result["guarded_minus_unguarded"]["mean_difference"] > 20
    assert result["guarded_minus_unguarded"]["ci95"] is None


def test_archive_mutation_and_wrong_protocol_invalidate_resume(tmp_path):
    pipeline = AuditPipeline(config(), tmp_path / "run")
    pipeline.run()
    original = (tmp_path / "run" / "predict.json").read_bytes()
    repeated = AuditPipeline(config(), tmp_path / "run")
    repeated.run()
    assert (tmp_path / "run" / "predict.json").read_bytes() == original
    wrong = AuditPipeline(config() | {"seed": 99}, tmp_path / "run")
    with pytest.raises(ValueError, match="mismatch"):
        wrong.run()
    path = tmp_path / "run" / "optimize.json"
    payload = json.loads(path.read_text())
    payload["payload"]["runs"][0]["shortlist"] = []
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="changed"):
        repeated.store.read("optimize")


def test_changed_science_runtime_invalidates_cached_stage(tmp_path, monkeypatch):
    pipeline = AuditPipeline(config(), tmp_path / "run")
    pipeline.run_stage("plan")
    monkeypatch.setattr("importlib.metadata.version", lambda name: "changed-runtime")
    changed = AuditPipeline(config(), tmp_path / "run")
    with pytest.raises(ValueError, match="mismatch"):
        changed.run_stage("plan")


def test_pool_budgets_unknown_graph_and_no_outcomes_in_trace():
    rows = source().rows[:20]
    called = []

    def score(row):
        called.append(row.sample_id)
        return {"sample_id": row.sample_id, "mean": 2.0, "diagnostics": {}}

    result = optimize(rows, score, "random", 1, 4, 5)
    assert result["requests"] == 4 == len(called)
    assert len(result["shortlist"]) == 4
    assert all("outcome" not in row for row in result["trace"])
    verify_seal(result)
    with pytest.raises(ValueError, match="not_applicable"):
        optimize(rows, score, "genetic", 1, 4, 5)
    result["shortlist"] = []
    with pytest.raises(ValueError, match="sealing"):
        verify_seal(result)


def test_cli_stage_order_and_config_validation(tmp_path):
    command = [
        sys.executable,
        "-m",
        "oligo_engine.robustness",
        "run",
        "--output",
        str(tmp_path / "cli"),
    ]
    subprocess.run(command, check=True, capture_output=True)
    report = (tmp_path / "cli" / "report.md").read_text()
    assert "fixture_only" in report and "limited_groups" in report
    pipeline = AuditPipeline(config(), tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        pipeline.run_stage("evaluate")
    with pytest.raises(ValueError, match="Unsupported"):
        AuditPipeline(config() | {"unknown": 1}, tmp_path / "bad")
