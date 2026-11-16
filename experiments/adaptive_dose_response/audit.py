"""Post-completion integrity audit and prespecified trade-off figures.

This module is added after execution; it never changes frozen policies or reads
new source outcomes. Its own source hash is recorded separately.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.ic50_qwen.run import read, sha

from oligo_engine.molecular_design.artifacts import seal, verify, write_new

from .run import METHODS, load, near, score


def audit(output: Path) -> dict:
    """Verify role separation, chained seals, charged prefixes and source identity."""
    protocol, config = load(output)
    selection = read(output / "selection.json")
    report = read(output / "report.json")
    for obj in (selection, report):
        verify(obj)
        assert obj["protocol_seal"] == protocol["seal"]
    assert selection["no_assessment_access"] is True
    assert report["selection_seal"] == selection["seal"]
    campaigns = config["campaigns"]
    dev = [c for c in campaigns if c["role"] == "development"]
    assess = [c for c in campaigns if c["role"] == "assessment"]
    for field in ("target",):
        assert not ({c[field] for c in dev} & {c[field] for c in assess})
    assert not (
        {c["context"]["USPTO ID"] for c in dev}
        & {c["context"]["USPTO ID"] for c in assess}
    )
    dev_sequences = [p["sequence"] for c in dev for p in c["panels"]]
    assert not any(
        near(p["sequence"], seq)
        for c in assess
        for p in c["panels"]
        for seq in dev_sequences
    )
    costs, ledger = {}, []
    source_ids = set()
    for role in ("development", "assessment"):
        artifact = read(output / f"{role}-traces.json")
        verify(artifact)
        assert artifact["protocol_seal"] == protocol["seal"]
        if role == "development":
            assert selection["development_seal"] == artifact["seal"]
        else:
            assert artifact["selection_seal"] == selection["seal"]
        expected_ids = {
            i
            for c in campaigns
            if c["role"] == role
            for p in c["panels"]
            for i in p["row_ids"]
        }
        assert expected_ids == set(artifact["outcome_ids"])
        assert not (expected_ids & source_ids)
        source_ids |= expected_ids
        for p in artifact["panels"]:
            for trace in p["traces"].values():
                assert sorted(x["index"] for x in trace) == list(range(len(p["doses"])))
                assert all(x["dose_nm"] == p["doses"][x["index"]] for x in trace)
        costs[role] = {}
        for method in METHODS:
            metric, rows = score(
                artifact["panels"], method, selection["settings"][method]
            )
            assert metric == report["roles"][role]["methods"][method]
            costs[role][method] = sum(r["n"] for r in rows)
            ledger.extend({"role": role, "method": method, **r} for r in rows)
    output_record = seal(
        {
            "protocol_seal": protocol["seal"],
            "report_seal": report["seal"],
            "audit_code_sha256": sha(Path(__file__)),
            "physical_distinct_historical_rows_read": len(source_ids),
            "charged_selected_prefixes": costs,
            "checks": (
                "all seals, source hashes, disjoint target/patent/near sequences, "
                "role IDs, no repeated doses, exact metric recomputation"
            ),
            "unknown_reference_in_development": report["roles"]["development"][
                "methods"
            ]["full_grid"]["reference_unknown"],
            "note": (
                "No new outcomes, fitting, model calls or policy tuning; "
                "reference-unresolved gate unassessed if development denominator zero"
            ),
        }
    )
    write_new(output / "completion-audit.json", output_record)
    write_new(
        output / "selected-prefix-ledger.json",
        seal({"protocol_seal": protocol["seal"], "rows": ledger}),
    )
    return output_record


def plot(output: Path) -> None:
    """Render accuracy and coverage against actual charged measurement counts."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    report = read(output / "report.json")
    verify(report)
    curves = report["roles"]["assessment"]["budget_curves"]
    labels = {
        "full_grid": "Full grid",
        "fixed_early": "Fixed early stopping",
        "information_gain": "Parameter information gain",
        "decision_aware": "Decision-aware",
    }
    colors = {
        "full_grid": "#777777",
        "fixed_early": "#2171b5",
        "information_gain": "#7a5195",
        "decision_aware": "#d95f02",
    }
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for method in METHODS:
        c = curves[method]
        x = [p["mean_measurements"] for p in c]
        for ax, metric in zip(
            axes,
            ("correct_decision_rate", "resolved_coverage", "selective_accuracy"),
            strict=True,
        ):
            y = [100 * p[metric] if p[metric] is not None else float("nan") for p in c]
            ax.plot(x, y, "o-", label=labels[method], color=colors[method], lw=1.8)
            ax.set_xlabel("Mean charged concentrations per ASO")
            ax.grid(alpha=0.2)
            ax.set_xlim(0.8, 4.6)
        axes[0].set_ylabel("Correct decisions / reference-resolved ASOs (%)")
        axes[1].set_ylabel("Decisions / reference-resolved ASOs (%)")
        axes[2].set_ylabel("Correct / classified reference-resolved ASOs (%)")
    axes[0].set_ylim(-2, 103)
    axes[1].set_ylim(-2, 103)
    axes[2].set_ylim(90, 100.5)
    axes[0].legend(fontsize=8, loc="lower right")
    fig.suptitle(
        "Adaptive concentration selection: 240 historical ASOs, "
        "five target/patent groups",
        fontsize=12,
    )
    fig.text(
        0.5,
        0.01,
        "Frozen development-selected policies; prefix budget caps 1–5. "
        "One reference-unresolved panel excluded from accuracy denominators; "
        "all early methods classify it.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(output / "accuracy-measurements.png", dpi=180)
    fig.savefig(output / "accuracy-measurements.pdf")
    plt.close(fig)


def main() -> None:
    """Run once into the existing completed artifact directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.output)
    plot(args.output)


if __name__ == "__main__":
    main()
