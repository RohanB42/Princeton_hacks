"""Plot saved siRNA RL experiments without refitting or rescoring models."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import t

ROOT = Path("artifacts/rl_design")
OUT = Path("docs/figures/rl_insights")
OUT.mkdir(parents=True, exist_ok=True)
SEEDS = [11, 23, 37, 53, 71]
COLORS = {"PPO": "#2563eb", "Random": "#f59e0b", "Evolutionary": "#10b981"}


def save(name):
    plt.savefig(OUT / f"{name}.png", dpi=190, bbox_inches="tight")
    plt.savefig(OUT / f"{name}.svg", bbox_inches="tight")
    plt.close()


def mean_ci(values):
    x = np.asarray(values)
    m = x.mean()
    h = t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / len(x) ** 0.5
    return m, h


def budget_plot():
    short = json.loads((ROOT / "huesken_512_five_seed_summary.json").read_text())[
        "rows"
    ]
    long = json.loads((ROOT / "improvement_4096/summary.json").read_text())["rows"]
    fig, ax = plt.subplots(figsize=(8.5, 5.3))
    for name, key in [
        ("PPO", "ppo_best_reward"),
        ("Random", "random_best_reward"),
        ("Evolutionary", "evolutionary_best_reward"),
    ]:
        means, halves = [], []
        for rows in (short, long):
            m, h = mean_ci([r[key] for r in rows])
            means.append(m)
            halves.append(h)
        ax.errorbar(
            [512, 4096],
            means,
            yerr=halves,
            marker="o",
            markersize=7,
            capsize=4,
            linewidth=2,
            label=name,
            color=COLORS[name],
        )
    ax.set(
        xlabel="PPO environment steps (search budget matched within each study)",
        ylabel="Best frozen Ridge reward found",
        ylim=(0.55, 1.03),
        title="More training improved PPO; search remained competitive",
    )
    ax.set_xticks([512, 4096])
    ax.grid(alpha=0.22)
    ax.legend(frameon=False)
    fig.text(
        0.12,
        -0.015,
        "Five-seed means; 95% t intervals. Same predictor; no measured potency.",
        fontsize=9,
    )
    save("training_budget")


def fresh_plot():
    s = json.loads((ROOT / "fresh_shaping_v1/summary.json").read_text())
    names = ["unchanged", "random", "evolutionary", "terminal", "shaped"]
    labels = ["Unchanged", "Random", "Evolutionary", "PPO terminal", "PPO shaped"]
    colors = [
        "#64748b",
        COLORS["Random"],
        COLORS["Evolutionary"],
        COLORS["PPO"],
        "#7c3aed",
    ]
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    y = np.arange(len(names))
    for i, (n, c) in enumerate(zip(names, colors)):
        v = s[n]["seed_means"]
        m, h = mean_ci(v)
        ax.errorbar(
            m, i, xerr=h, fmt="o", color=c, markersize=9, capsize=4, linewidth=2
        )
        ax.scatter(
            v, np.full(5, i) + np.linspace(-0.12, 0.12, 5), s=25, color=c, alpha=0.55
        )
    ax.set(
        yticks=y,
        yticklabels=labels,
        xlabel="Best of 16 proposals: mean frozen Ridge reward",
        title="Fresh starts: PPO beat equal-request search at inference",
    )
    ax.grid(axis="x", alpha=0.22)
    fig.text(
        0.12,
        -0.015,
        "Five seeds; 95% t intervals. Shaping used ~6.9× more offline scores.",
        fontsize=9,
    )
    save("fresh_start_comparison")


def predictor_plot():
    rows = json.loads((ROOT / "main_predictors_v1/cross_scores.json").read_text())
    lookup = {(r["seed"], r["policy"], r["evaluator"]): r["mean_reward"] for r in rows}
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for i, ev in enumerate(["ridge", "gp", "rf"]):
        diffs = [lookup[(s, "gp", ev)] - lookup[(s, "ridge", ev)] for s in SEEDS]
        m, h = mean_ci(diffs)
        ax.errorbar(m, i, xerr=h, fmt="o", markersize=9, capsize=4, color="#7c3aed")
        ax.scatter(
            diffs,
            np.full(5, i) + np.linspace(-0.12, 0.12, 5),
            s=26,
            color="#7c3aed",
            alpha=0.5,
        )
    ax.axvline(0, color="#1e293b", linewidth=1)
    ax.set(
        yticks=range(3),
        yticklabels=["Ridge evaluator", "GP evaluator", "RF evaluator"],
        xlabel="GP-trained PPO minus Ridge-trained PPO reward",
        title="Changing the PPO reward model showed no clear gain",
    )
    ax.grid(axis="x", alpha=0.22)
    fig.text(
        0.12,
        -0.015,
        "Paired seeds; 95% t intervals. Compare within each evaluator only.",
        fontsize=9,
    )
    save("predictor_cross_scoring")


if __name__ == "__main__":
    plt.rcParams.update(
        {"font.size": 11, "axes.spines.top": False, "axes.spines.right": False}
    )
    budget_plot()
    fresh_plot()
    predictor_plot()
