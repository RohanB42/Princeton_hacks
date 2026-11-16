"""Scientific invariants for the new molecular construction/search boundary."""

from dataclasses import replace

import pytest

from oligo_engine.molecular_design.artifacts import panel, seal, verify, write_new
from oligo_engine.molecular_design.bundles import fixture, portable_bundle
from oligo_engine.molecular_design.environment import DesignCore
from oligo_engine.molecular_design.grammar import Construction, Token
from oligo_engine.molecular_design.optimizers import DesignSpace, search
from oligo_engine.molecular_design.preflight import (
    audit_membership,
    audit_partitions,
    preflight,
)
from oligo_engine.molecular_design.scoring import (
    FrozenRegistry,
    Head,
    InferenceFailure,
    Prediction,
    Session,
    hypervolume,
)


def act(core, kind, value=None):
    return core.step(core.grammar.tokens.index(Token(kind, value)))


def construct(core, design):
    pattern = next(
        p for p in core.campaign.profile.patterns if p.name == design.pattern
    )
    rewards = []
    for kind, value in [
        ("NEW", None),
        ("LENGTH", pattern.length),
        ("SITE", design.start),
        ("LAYOUT", pattern.layout),
        ("PATTERN", pattern.name),
        ("TERMINAL", design.terminal),
        ("COMMIT", None),
    ]:
        rewards.append(act(core, kind, value)[1])
    return rewards


def test_every_complete_design_reachable_in_seven_actions_without_partial_scoring():
    c, r = fixture(requests=3)
    c = replace(c, starts=())
    for d in c.designs():
        core = DesignCore(c, r)
        rewards = construct(core, d)
        assert rewards[:6] == [0] * 6
        assert core.session.requests == 1
        assert d.key in core.session.archive


def test_molecular_identity_excludes_provenance_but_preserves_chemistry_and_target():
    c, _ = fixture()
    ds = list(c.designs())
    d = ds[0]
    assert replace(d, parent="different-path").key == d.key
    assert replace(d, target_id="another-transcript").compound_id == d.compound_id
    assert replace(d, target_id="another-transcript").key != d.key
    assert (
        c.construct(d.start, c.profile.patterns[1].name, "none").compound_id
        != d.compound_id
    )
    with pytest.raises(ValueError):
        c.validate(replace(d, sequence="A" * len(d.sequence)))


def test_coupled_masks_edit_invalidation_and_mask_violation_no_charge():
    c, r = fixture()
    core = DesignCore(c, r)
    with pytest.raises(ValueError, match="forbidden"):
        act(core, "COMMIT")
    assert core.session.requests == 1 and core.steps == 0
    act(core, "PARENT", 0)
    act(core, "EDIT", "length")
    assert core.construction == Construction(
        stage="length", parent=core.session.parents[0].key
    )
    act(core, "LENGTH", 10)
    invalid = core.grammar.tokens.index(Token("SITE", 24))
    assert not core.masks()[invalid]
    act(core, "SITE", 1)
    invalid_layout = core.grammar.tokens.index(Token("LAYOUT", (2, 4, 2)))
    assert not core.masks()[invalid_layout]


def test_archive_reward_telescopes_duplicates_cost_and_reset_isolates():
    c, r = fixture(requests=4)
    core = DesignCore(c, r, decoder="legacy-v1")
    design = list(c.designs())[12]
    total = sum(construct(core, design))
    total += sum(construct(core, design))
    assert core.session.trace[-1]["cache_hit"]
    assert core.session.trace[-1]["gain"] == 0
    total += act(core, "STOP")[1]
    assert total == pytest.approx(core.session.quality - core.session.initial_quality)
    best = core.session.quality
    assert core.receipt()["final_quality"] == best
    core.reset()
    assert core.session.requests == 1 and core.steps == 0


def test_budget_terminal_partial_construction_preserves_incumbent():
    c, r = fixture(requests=2)
    core = DesignCore(replace(c, tokens=2), r, decoder="legacy-v1")
    before = core.session.quality
    act(core, "NEW")
    act(core, "LENGTH", 8)
    assert core.done and core.end_reason == "construction_budget"
    assert core.session.quality == before
    with pytest.raises(RuntimeError):
        act(core, "STOP")


def test_screened_molecules_remain_editable_and_missing_risk_never_zero():
    c, r = fixture()
    risk = r.heads[1]
    bad = Head(risk.manifest, lambda d, ctx: Prediction(1.0))
    registry = FrozenRegistry(c.profile, (r.heads[0], bad))
    core = DesignCore(c, registry)
    assert core.session.quality == 0
    assert not core.session.archive[core.session.parents[0].key][1].eligible
    assert core.masks()[core.grammar.tokens.index(Token("PARENT", 0))]
    with pytest.raises(ValueError, match="unavailable"):
        FrozenRegistry(c.profile, (r.heads[0], Head(risk.manifest, None)))


def test_model_failure_is_durable_execution_failure_and_still_charged():
    c, r = fixture()
    c = replace(c, starts=())
    bad = Head(r.heads[0].manifest, lambda d, ctx: Prediction(float("nan")))
    session = Session(c, FrozenRegistry(c.profile, (bad, r.heads[1])))
    with pytest.raises(InferenceFailure):
        session.query(next(c.designs()))
    assert session.requests == 1 and session.failed
    assert session.trace[0]["status"] == "execution_failed"
    assert session.trace[0]["gain"] is None


def test_actual_endpoint_contexts_remain_separate_and_no_free_filtering():
    c, r = fixture()
    seen = []
    heads = tuple(
        Head(h.manifest, lambda d, ctx: (seen.append(ctx) or Prediction(0.5)))
        for h in r.heads
    )
    Session(c, FrozenRegistry(c.profile, heads))
    assert seen[0] != seen[1]
    unsupported = replace(r.heads[1].manifest, pattern_ids=())
    registry = FrozenRegistry(
        c.profile, (r.heads[0], Head(unsupported, r.heads[1].predict))
    )
    assert preflight(c, registry)["status"] == "blocked"
    session = Session(replace(c, starts=()), registry)
    score, gain = session.query(next(c.designs()))
    assert session.requests == 1 and gain == 0 and not score.eligible


def test_all_conventional_controls_obey_same_budget():
    c, r = fixture(requests=9)
    for method in ("initial", "random", "greedy", "genetic", "sweep"):
        receipt = search(Session(c, r), method, 23)
        assert receipt["requests"] <= c.requests
        assert receipt["trace"][0]["initial"]
        assert receipt["final_quality"] >= receipt["initial_quality"]
    space = DesignSpace(c)
    expanded = replace(c, requests=space.capacity + len(c.starts))
    exact = search(Session(expanded, r), "exhaustive", 0)
    assert exact["unique_designs"] == space.capacity
    with pytest.raises(ValueError, match="full"):
        search(Session(c, r), "exhaustive", 0)


def test_hypervolume_overlap_duplicate_and_dominance():
    assert hypervolume(((0.5, 0.5), (0.8, 0.2)), (0, 0)) == pytest.approx(0.31)
    assert hypervolume(((0.5, 0.5), (0.5, 0.5), (0.1, 0.1)), (0, 0)) == 0.25


def test_seal_refuses_mutation_and_write_refuses_overwrite(tmp_path):
    a = seal({"selected": ["molecule"]})
    verify(a, a["seal"])
    write_new(tmp_path / "receipt.json", a)
    with pytest.raises(FileExistsError):
        write_new(tmp_path / "receipt.json", a)
    a["selected"].append("another")
    with pytest.raises(ValueError):
        verify(a)


def test_profile_partition_exposure_and_full_scope_gates():
    c, r = fixture()
    with pytest.raises(ValueError, match="crosses"):
        audit_partitions((c, replace(c, partition="final")))
    assert not audit_partitions((c,))["cross_target_claim_ready"]
    m = replace(r.heads[0].manifest, training_ids=("held-out",))
    registry = FrozenRegistry(c.profile, (Head(m, r.heads[0].predict), r.heads[1]))
    with pytest.raises(ValueError, match="exposure"):
        audit_membership(registry, ("held-out",))
    with pytest.raises(ValueError, match="Fixture"):
        FrozenRegistry(replace(c.profile, purpose="full"), r.heads)


def test_real_portable_checkpoint_inference_and_missing_risk_are_explicit():
    from pathlib import Path

    path = Path("model_checkpoints/supported-aso-v1/efficacy.json")
    profile, registry = portable_bundle(
        path, "44f975ae47c1a073ec52bde1e3403baa21de8a1b0b733e4bcac1a9b236252a84"
    )
    c, _ = fixture()
    c = replace(c, profile=profile, starts=())
    score, gain = Session(c, registry).query(next(c.designs()))
    assert score.eligible and 0 <= gain <= 1
    assert profile.purpose == "efficacy_ablation"
    assert registry.heads[0].manifest.parity_receipt


def test_panel_deduplicates_compounds_and_never_fills_with_ineligible():
    c, r = fixture()
    receipt = search(Session(c, r), "random", 8)
    rows = panel(receipt, 100)
    assert len({x["compound_id"] for x in rows}) == len(rows)
    assert all(x["claim"] == "unvalidated computational hypothesis" for x in rows)


def test_final_outcome_poisoning_cannot_change_selection_and_missing_stays_missing():
    from oligo_engine.molecular_design.artifacts import run_artifact
    from oligo_engine.molecular_design.evaluation import assess_exact

    c, r = fixture()
    first = run_artifact(c, search(Session(c, r), "random", 8))
    original_ids = [v["compound_id"] for v in first["panel"]]
    allowed = frozenset(
        p["assessment_id"]
        for row in first["panel"]
        for p in row["predictions"]
        if p["endpoint"] == "synthetic_activity"
    )
    positive = assess_exact(
        first,
        first["seal"],
        "synthetic_activity",
        allowed,
        lambda ids: dict.fromkeys(ids, 100.0),
    )
    negative = assess_exact(
        first,
        first["seal"],
        "synthetic_activity",
        allowed,
        lambda ids: dict.fromkeys(ids, -100.0),
    )
    assert positive["measured_mean"] != negative["measured_mean"]
    assert original_ids == [v["compound_id"] for v in first["panel"]]
    missing = assess_exact(
        first,
        first["seal"],
        "synthetic_activity",
        frozenset(),
        lambda ids: pytest.fail("No outcomes may be read"),
    )
    assert missing["measured_mean"] is None
    assert missing["status"] == "no_exact_measurements"


def test_same_current_molecule_different_history_is_observable():
    c, r = fixture()
    a, b = DesignCore(c, r), DesignCore(c, r)
    construct(a, list(c.designs())[5])
    assert a.construction == b.construction
    assert a.observe()["history"] != b.observe()["history"]


def test_terminal_chemistry_length_and_base_modification_change_identity():
    c, _ = fixture()
    p = replace(c.profile.patterns[0], terminals=("none", "PO", "PS"))
    from oligo_engine.reward.chemistry import parse_helm

    sequence = "ACGTACGT"
    ids = {parse_helm(p.helm(sequence, t)).identity for t in p.terminals}
    assert len(ids) == 3
    plain = replace(p, methyl_c=(False,) * p.length)
    assert parse_helm(plain.helm(sequence, "none")).identity not in ids


def test_lower_bound_screen_and_direction_correct_utility():
    c, r = fixture()
    m = replace(r.heads[0].manifest, reference=(0.0, 0.5, 1.0), direction="lower")
    risk = replace(r.heads[1].manifest, lower=0.4, upper=0.8)
    registry = FrozenRegistry(
        c.profile,
        (
            Head(m, lambda d, ctx: Prediction(0.0)),
            Head(risk, lambda d, ctx: Prediction(0.2)),
        ),
    )
    score, gain = Session(replace(c, starts=()), registry).query(next(c.designs()))
    assert not score.eligible and gain == 0
    assert score.objectives[0] == pytest.approx(5 / 6)


def test_local_service_uses_frozen_profile_enforces_budget_and_exports(tmp_path):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "molecular_server", "app/molecular_server.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    service = module.MolecularService(
        Path("configs/molecular-design/fixture.json"), tmp_path
    )
    result = service.run({"campaign": 0, "method": "random", "requests": 4})
    assert result["artifact"]["run"]["requests"] == 4
    assert (tmp_path / (result["run_id"] + ".csv")).is_file()
    with pytest.raises(ValueError, match="Budget"):
        service.run({"requests": 100000})
    with pytest.raises(ValueError, match="final"):
        service.run({"campaign": 6})


def test_initial_inference_failure_is_durable_and_charged(tmp_path):
    import json

    from oligo_engine.molecular_design.artifacts import QueryJournal

    c, r = fixture()

    def fail(design, context):
        raise TimeoutError("predictor unavailable")

    registry = FrozenRegistry(c.profile, (Head(r.heads[0].manifest, fail), r.heads[1]))
    journal = QueryJournal(tmp_path / "queries.jsonl")
    with pytest.raises(InferenceFailure):
        Session(c, registry, journal)
    record = json.loads(journal.path.read_text())
    verify(record)
    assert record["event"]["request"] == 1
    assert record["event"]["status"] == "execution_failed"
    assert record["event"]["gain"] is None
    assert record["event"]["head_calls"] == {r.heads[0].manifest.name: 1}


def test_exhaustive_counts_initial_design_and_visits_every_complete_candidate():
    c, r = fixture()
    capacity = DesignSpace(c).capacity
    result = search(Session(replace(c, requests=capacity), r), "exhaustive", 0)
    assert result["requests"] == capacity
    assert result["unique_designs"] == capacity
    assert not any(e["cache_hit"] for e in result["trace"])


def test_pareto_panel_cannot_prioritize_a_dominated_design_for_diversity():
    c, r = fixture()
    receipt = search(Session(c, r), "random", 9)
    events = [e for e in receipt["trace"] if e["score"]["eligible"]]
    a, b = events[:2]
    a["score"]["objectives"] = (0.8, 0.8)
    b["score"]["objectives"] = (0.6, 0.7)
    result = panel({"trace": [b, a]}, 2, diversity=1)
    assert result[0]["compound_id"] == a["compound_id"]
    assert [r["pareto_tier"] for r in result] == [0, 1]


def test_chemical_features_retain_structure_and_frozen_ridge_parity(tmp_path):
    import hashlib
    import json

    import numpy as np
    from sklearn.linear_model import Ridge

    from oligo_engine.molecular_design.chemical_model import (
        ChemicalRegressor,
        chemical_features,
    )

    c, _ = fixture()
    designs = list(c.designs())[:12]
    x = np.asarray([chemical_features(d.helm) for d in designs])
    y = np.arange(len(x)) * 0.1
    model = Ridge(alpha=10).fit(x, y)
    bundle = {
        "schema": "frozen-chemical-regressor-v1",
        "model": "ridge",
        "parameters": {
            "coefficients": model.coef_.tolist(),
            "intercept": float(model.intercept_),
        },
        "context": {"assay": "test"},
        "parity": [
            {"helm": d.helm, "mean": float(mean)}
            for d, mean in zip(designs, model.predict(x), strict=True)
        ],
    }
    path = tmp_path / "model.json"
    path.write_text(json.dumps(bundle))
    frozen = ChemicalRegressor(path, hashlib.sha256(path.read_bytes()).hexdigest())
    assert frozen(designs[0], (("assay", "test"),)).mean == pytest.approx(
        model.predict(x[:1])[0]
    )
    with pytest.raises(ValueError, match="context"):
        frozen(designs[0], (("assay", "wrong"),))
    p = c.profile.patterns[0]
    original = chemical_features(p.helm("ACGTACGT", "none"))
    changed = chemical_features(
        replace(p, methyl_c=(False,) * 8).helm("ACGTACGT", "none")
    )
    assert original != changed


def test_full_profile_cannot_be_created_from_extrapolation_stress():
    c, _ = fixture()
    with pytest.raises(ValueError, match="Extrapolation"):
        replace(c.profile, purpose="full", applicability="extrapolation_stress")


def test_transactional_decoder_removes_reproduced_parent_cancel_cycle():
    c, r = fixture(requests=3)
    old = DesignCore(c, r, decoder="legacy-v1")
    for _ in range(10):
        act(old, "PARENT", 0)
        act(old, "CANCEL")
    assert old.session.requests == len(c.starts)
    assert old.session.quality == old.session.initial_quality
    new = DesignCore(c, r, decoder="transactional-v2")
    assert not new.masks()[new.grammar.tokens.index(Token("STOP"))]
    act(new, "PARENT", 0)
    assert new.construction.edit_pending
    assert not new.masks()[new.grammar.tokens.index(Token("CANCEL"))]
    assert not new.masks()[new.grammar.tokens.index(Token("COMMIT"))]


def test_every_transactional_first_proposal_path_completes_without_cycles():
    from oligo_engine.molecular_design.grammar import TransactionalGrammar

    c, r = fixture(requests=3)
    c = replace(c, target=replace(c.target, intervals=((0, 10),)))
    session = Session(c, r)
    grammar = TransactionalGrammar(c, len(c.target.sequence), c.requests)
    frontier = [(Construction(), 0)]
    seen, completed = set(), set()
    while frontier:
        state, depth = frontier.pop()
        if state in seen:
            continue
        seen.add(state)
        masks = grammar.legal(state, session.parents)
        assert any(masks)
        for i, legal in enumerate(masks):
            if not legal:
                continue
            successor, design, stop = grammar.apply(state, i, session.parents)
            assert not stop
            assert depth + 1 <= 8
            if design is None:
                ranks = {
                    "ready": 0,
                    "length": 2,
                    "site": 3,
                    "layout": 4,
                    "pattern": 5,
                    "terminal": 6,
                    "review": 7,
                }
                before_rank = 1 if state.edit_pending else ranks[state.stage]
                after_rank = 1 if successor.edit_pending else ranks[successor.stage]
                assert after_rank > before_rank
                frontier.append((successor, depth + 1))
            else:
                assert design.key not in session.archive
                completed.add(design.key)
    assert completed == {d.key for d in c.designs()} - set(session.archive)


def test_transactional_masks_are_score_blind_and_budgeted_without_duplicates():
    c, r = fixture(requests=6)
    negative = FrozenRegistry(
        c.profile,
        (
            r.heads[0],
            Head(r.heads[1].manifest, lambda d, ctx: Prediction(1.0)),
        ),
    )
    positive_core = DesignCore(c, r, decoder="transactional-v2")
    negative_core = DesignCore(c, negative, decoder="transactional-v2")
    while not positive_core.done:
        assert positive_core.masks() == negative_core.masks()
        legal = [i for i, valid in enumerate(positive_core.masks()) if valid and i != 0]
        action = legal[0] if legal else 0
        positive_core.step(action)
        negative_core.step(action)
    assert positive_core.session.requests == negative_core.session.requests == 6
    assert positive_core.session.requests == len(positive_core.session.archive)
    assert not any(e["cache_hit"] for e in positive_core.session.trace)
    assert negative_core.session.quality == 0
    assert positive_core.steps <= 7 * (c.requests - len(c.starts))


def test_transactional_reserves_completion_tokens_and_exhausts_small_space():
    c, r = fixture(requests=3)
    core = DesignCore(replace(c, tokens=7), r, decoder="transactional-v2")
    assert not core.masks()[core.grammar.tokens.index(Token("PARENT", 0))]
    while not core.done:
        core.step(next(i for i, valid in enumerate(core.masks()) if valid))
    assert core.session.requests == 2
    assert core.end_reason == "construction_budget"
    tiny = replace(
        c,
        target=replace(c.target, intervals=((0, 8),)),
        profile=replace(c.profile, patterns=(c.profile.patterns[0],)),
    )
    registry = FrozenRegistry(tiny.profile, r.heads)
    exhausted = DesignCore(tiny, registry, decoder="transactional-v2")
    assert exhausted.masks()[0] and sum(exhausted.masks()) == 1
    act(exhausted, "STOP")


@pytest.mark.parametrize("method", ["random", "greedy"])
def test_controls_reuse_history_without_requerying_and_have_budget_prefixes(method):
    c, registry = fixture(requests=12)
    full = search(Session(c, registry), method, 42)
    short = search(Session(replace(c, requests=6), registry), method, 42)
    assert full["requests"] == full["unique_designs"] == 12
    assert full["optimizer_version"] == "queried-history-v2"
    assert not any(e["cache_hit"] for e in full["trace"])
    assert [e["design_id"] for e in short["trace"]] == [
        e["design_id"] for e in full["trace"][:6]
    ]
    tiny = replace(c, target=replace(c.target, intervals=((0, 10),)))
    capacity = len({d.key for d in tiny.designs()})
    complete = search(
        Session(replace(tiny, requests=capacity + 4), registry), method, 42
    )
    assert complete["requests"] == complete["unique_designs"] == capacity
    assert complete["end_reason"] == "space_enumerated"
