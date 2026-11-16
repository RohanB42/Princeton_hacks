"""Post-completion audit; no model calls, policy tuning or new assay reads."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

from oligo_engine.molecular_design.artifacts import seal, verify, write_new

from .core import success
from .run import load, read


def audit(output: Path) -> dict:
    """Verify receipts and report prespecified sensitivities plus menu diagnostics."""
    protocol, config = load(output)
    results = read(output / "results.json")
    private = read(output / "private-oracle.json")
    for obj in (results, private):
        verify(obj)
        assert obj["protocol_seal"] == protocol["seal"]
    runs = []
    for receipt in results["runs"]:
        verify(receipt)
        assert receipt["protocol_seal"] == protocol["seal"]
        run = receipt["run"]
        assert len(run["history"]) == 8
        assert len({h["id"] for h in run["history"]}) == 8
        assert run["initial_ids"] == [h["id"] for h in run["history"][:2]]
        runs.append(run)
    assert len(runs) == 72
    by_cell = {(r["target"], r["method"], r["rule"], r["seed"]): r for r in runs}
    assert len(by_cell) == 72
    for target in protocol["targets"]:
        for seed in protocol["seeds"]:
            matched = [r for r in runs if r["target"] == target and r["seed"] == seed]
            assert len({tuple(r["initial_ids"]) for r in matched}) == 1
            a, b = [by_cell[target, "random", rule, seed] for rule in protocol["rules"]]
            assert [h["id"] for h in a["history"]] == [h["id"] for h in b["history"]]
    requests = sorted((output / "calls").glob("*/step-*/request.json"))
    responses = sorted((output / "calls").glob("*/step-*/response.json"))
    assert len(requests) == len(responses) == 108
    first, baseline, letters, seconds, checks = [], [], Counter(), [], []
    for path in requests:
        request = read(path)
        response = read(path.with_name("response.json"))
        verify(request)
        verify(response)
        allowed = request["allowed_ids"]
        answer = response["response"]
        assert answer in allowed and request["max_tokens"] == 1
        assert request["constrained_decoding"]
        first.append(answer == allowed[0])
        baseline.append(1 / len(allowed))
        letters[answer] += 1
        seconds.append(response["seconds"])
        checks.append(
            {
                "path": str(path),
                "request_seal": request["seal"],
                "response_seal": response["seal"],
            }
        )
    assert not list((output / "failures").glob("*.json"))
    sensitivity, pool = [], []
    for campaign in config["campaigns"]:
        target = campaign["target"]
        oracle = private["oracle"][campaign["id"]]
        strict = private["strict_monotonicity_oracle"][campaign["id"]]
        pool.append(
            {
                "target": target,
                "panels": len(oracle),
                "GC_bins": dict(
                    Counter(c["features"]["gc_bin"] for c in campaign["candidates"])
                ),
                "strict_curve_counts": dict(
                    Counter(c["kind"] for c in strict.values())
                ),
                "eligible_pool_counts": {
                    str(t): {
                        rule: sum(success(c, t, rule) is True for c in oracle.values())
                        for rule in protocol["rules"]
                    }
                    for t in protocol["secondary_thresholds_nm"]
                    + [protocol["primary_threshold_nm"]]
                },
            }
        )
        for method in protocol["methods"]:
            for feedback in protocol["rules"]:
                selected = [
                    r
                    for r in runs
                    if r["target"] == target
                    and r["method"] == method
                    and r["rule"] == feedback
                ]
                for threshold in (10, 100, 1000):
                    for qc, source in (("primary", oracle), ("strict", strict)):
                        sensitivity.append(
                            {
                                "target": target,
                                "method": method,
                                "feedback": feedback,
                                "threshold_nm": threshold,
                                "QC": qc,
                                "bound_aware_new_hits_mean": statistics.mean(
                                    sum(
                                        success(
                                            source[h["id"]], threshold, "bound_aware"
                                        )
                                        is True
                                        for h in r["history"][2:]
                                    )
                                    for r in selected
                                ),
                                "unknown_panels_mean": statistics.mean(
                                    sum(
                                        success(
                                            source[h["id"]], threshold, "bound_aware"
                                        )
                                        is None
                                        for h in r["history"]
                                    )
                                    for r in selected
                                ),
                            }
                        )
    out = seal(
        {
            "protocol_seal": protocol["seal"],
            "result_seal": results["seal"],
            "completed_arms": len(runs),
            "qwen_calls": len(requests),
            "charged_panels": sum(r["panels_purchased"] for r in runs),
            "charged_dose_readouts": sum(r["source_dose_measurements"] for r in runs),
            "selected_source_rows": len(private["outcome_ids_read"]),
            "no_invalid_actions_or_fallbacks": True,
            "receipt_checks": checks,
            "posthoc_menu_diagnostic": {
                "first_available_count": sum(first),
                "choices": len(first),
                "fraction": statistics.mean(first),
                "uniform_mean_expected_fraction": statistics.mean(baseline),
                "display_letter_counts": dict(sorted(letters.items())),
                "generation_seconds_total": sum(seconds),
                "generation_seconds_median": statistics.median(seconds),
                "interpretation": (
                    "Descriptive only; correlated adaptive choices, "
                    "no permutation robustness test."
                ),
            },
            "pool_diagnostics_after_all_traces": pool,
            "fixed_trace_sensitivity": sensitivity,
            "scope": (
                "Retrospective fixed-policy evaluation. Prior NLRP3 train/dev/test "
                "row roles unresolved; not independent validation."
            ),
        }
    )
    write_new(output / "completion-audit.json", out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.output)
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in {"receipt_checks", "fixed_trace_sensitivity"}
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
