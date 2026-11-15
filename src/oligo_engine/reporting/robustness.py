"""Standalone audit summaries and optional standard plotting artifacts."""

from pathlib import Path


def write_report(path: Path, result: dict) -> None:
    metrics = result["metrics"]
    text = [
        "# Predictor robustness diagnostic",
        "",
        f"Status: {result['status']}",
        "",
        f"Scored coverage: {metrics['scored_rows']}/{metrics['total_rows']} rows.",
        f"Final groups: {metrics['groups_total']} ({metrics['inference_status']}).",
        f"Compound-balanced macro RMSE: {metrics['macro_rmse']}.",
        f"Compound-balanced macro MAE: {metrics['macro_mae']}.",
        "",
        "## Held-out groups",
        "",
        "| Group | Scored / total | RMSE | MAE | Pearson |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in metrics["groups"]:
        text.append(
            f"| {row['group']} | {row['n']} / {row['total']} | {row['rmse']} | "
            f"{row['mae']} | {row['pearson']} |"
        )
    text.extend(
        [
            "",
            "## Diagnostic risk-coverage",
            "",
            "| Signal | Diagnostic AURC | Random AURC | Diagnostic coverage |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for name, values in result["diagnostics"].items():
        text.append(
            f"| {name} | {values['diagnostic']['aurc']} | "
            f"{values['random']['aurc']} | {values['diagnostic']['coverage']} |"
        )
    text.extend(
        [
            "",
            "## Recorded-pool selection",
            "",
            "| Method | Seed | Guarded | Shortlist count | Measured mean | Requests |",
            "| --- | ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for row in result["selection"]:
        text.append(
            f"| {row['method']} | {row['seed']} | {row['guarded']} | {row['n']} | "
            f"{row['measured_mean']} | {row['requests']} |"
        )
    text.extend(
        [
            "",
            "## Limits",
            "",
            result["claims"],
            "",
            f"Prior exposure: {result['prior_exposure']}.",
            "Calibration coverage under shifted target groups is empirical only.",
            "Precomputed predictor-table construction has a separate cost receipt.",
            "Partial shortlist quality and retention must be interpreted together.",
            "",
        ]
    )
    content = "\n".join(text)
    if path.exists():
        if path.read_text() != content:
            raise ValueError("Refusing to replace a different report")
    else:
        with path.open("x") as handle:
            handle.write(content)


def plot_report(directory: Path, result: dict) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    target = directory / "risk-coverage.png"
    if target.exists():
        raise FileExistsError(target)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for name, curves in result["diagnostics"].items():
        curve = curves["diagnostic"]["curve"]
        if curve:
            ax.plot(
                [r["coverage"] for r in curve], [r["risk"] for r in curve], label=name
            )
    ax.set(
        xlabel="Fraction of compounds retained within each group",
        ylabel="Group-balanced MAE (original endpoint units)",
        title=f"Diagnostic ordering: {result['status']}",
    )
    if ax.lines:
        ax.legend()
    else:
        ax.text(
            0.5,
            0.5,
            "No scored final records; accuracy is undefined",
            transform=ax.transAxes,
            ha="center",
            va="center",
            wrap=True,
        )
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(target, dpi=160)
    plt.close(fig)
    return [str(target)]
