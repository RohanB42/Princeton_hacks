"""Three bounded ASO checks: validity, synthetic optimizers, measured feasibility.

Each phase writes a new ignored JSON receipt. No production models are changed.
The measured phase uses only already-scored development assays and saved predictions;
it never fits models, selects settings, or reads reserved-target outcomes.
"""

import argparse
import csv
import gzip
import hashlib
import json
import random
import subprocess
from collections import Counter
from dataclasses import replace
from pathlib import Path
from time import perf_counter


def structural() -> dict:
    import numpy as np

    from oligo_engine.design.aso_space import (
        ASODesignSpace,
        TargetContext,
        candidate_identity,
    )
    from oligo_engine.design.candidates import reverse_complement
    from oligo_engine.reward.atlas import atlas_helm
    from oligo_engine.reward.chemistry import parse_helm
    from oligo_engine.rl.environment import ASOEnv
    from oligo_engine.rl.fixture import fixture_session

    rng = random.Random(20261114)
    candidates = transitions = rejected_mutations = observations = 0
    for i in range(100):
        sequence = "".join(rng.choice("ACGT") for _ in range(rng.randint(30, 100)))
        target = TargetContext(
            f"PROBE{i}",
            f"synthetic-probe-{i}.1",
            sequence,
            "synthetic",
            "validity-stress-v1",
        )
        space = ASODesignSpace(target, rng.randrange(len(sequence) - 18))
        for position in space.reachable():
            candidate = space.candidate(position)
            parsed = parse_helm(atlas_helm(candidate, target))
            assert candidate.sequence == reverse_complement(
                sequence[position : position + 19]
            )
            assert parsed.sugars == ("MOE",) * 5 + ("DNA",) * 10 + ("MOE",) * 4
            assert parsed.links == ("PS",) * 18 + ("END",)
            assert parsed.terminal == "none"
            assert parsed.bases.count("5meC") == candidate.sequence.count("C")
            candidate_identity(candidate, target)
            candidates += 1
            try:
                candidate_identity(
                    replace(candidate, helm=candidate.helm + "bad"), target
                )
            except ValueError:
                rejected_mutations += 1
            else:
                raise AssertionError("Corrupt HELM accepted")
        env = ASOEnv(space, fixture_session(space, max_unique=100, max_requests=200))
        for episode in range(5):
            obs, _ = env.reset(seed=i * 5 + episode)
            assert env.observation_space.contains(obs)
            observations += 1
            for _ in range(9):
                legal = np.flatnonzero(env.action_masks()).tolist()
                action = rng.choice(legal)
                obs, reward, terminal, truncated, info = env.step(action)
                assert env.observation_space.contains(obs)
                assert np.isfinite(reward) and not truncated
                observations += 1
                transitions += 1
                if terminal:
                    break
            else:
                raise AssertionError("Episode did not terminate")
    return {
        "status": "passed_synthetic_invariants",
        "transcripts": 100,
        "episodes": 500,
        "candidates_checked": candidates,
        "corrupt_candidates_rejected": rejected_mutations,
        "transitions_checked": transitions,
        "observations_checked": observations,
    }


def optimizers(output: Path) -> dict:
    from oligo_engine.rl.environment import ASOEnv
    from oligo_engine.rl.fixture import fixture_session, fixture_space
    from oligo_engine.rl.ppo import load_policy, rollout, train, verify_runtime
    from oligo_engine.rl.search import search

    rows, training = [], []
    for seed in (7, 17, 27):
        space, val = fixture_space("TRAIN"), fixture_space("VALIDATION")
        model, manifest = train(
            ASOEnv(space, fixture_session(space, max_requests=10000)),
            ASOEnv(val, fixture_session(val, max_requests=1000)),
            output / f"policy-{seed}",
            steps=2048,
            seed=seed,
        )
        training.append(
            {
                "seed": seed,
                "requests": manifest["training_cost"]["requests"],
                "unique": manifest["training_cost"]["unique_scores"],
                "head_calls": manifest["training_cost"]["head_calls"],
                "validation_requests": manifest["validation_cost"]["requests"],
                "seconds": manifest["total_wall_seconds"],
            }
        )
        for budget in (6, 10):
            final = fixture_space("FINAL")
            for method in ("unchanged", "random", "greedy", "genetic", "ppo"):
                session = fixture_session(final, max_unique=budget)
                if method == "ppo":
                    env = ASOEnv(final, session)
                    result = rollout(model, env, seed)
                    second_env = ASOEnv(
                        final, fixture_session(final, max_unique=budget)
                    )
                    replay = rollout(
                        load_policy(output / f"policy-{seed}", second_env),
                        second_env,
                        seed,
                    )
                    assert result["actions"] == replay["actions"]
                    assert result["archive"] == replay["archive"]
                else:
                    result = search(final, session, method, seed)
                assert result["unique_scores"] <= budget
                assert result["requests"] <= 100
                (output / f"{method}-{seed}-{budget}.json").write_text(
                    json.dumps(result, indent=2) + "\n"
                )
                rows.append(
                    {
                        "seed": seed,
                        "budget": budget,
                        "method": method,
                        "best_reward": result["best_reward"],
                        "unique_scores": result["unique_scores"],
                        "requests": result["requests"],
                        "head_calls": result["head_calls"],
                        "status": result["status"],
                        "terminal_reward": result.get("terminal_reward"),
                    }
                )
        print(f"optimizer seed {seed} complete", flush=True)
    return {
        "status": "synthetic_comparison_only",
        "runtime": verify_runtime(),
        "steps_per_policy": 2048,
        "rows": rows,
        "training": training,
        "known_optimum": 0.95,
        "limitation": "Same monotonic toy objective and periodic transcript across "
        "train/validation/final; no biological generalization.",
    }


def measured(root: Path) -> dict:
    import numpy as np
    import pyarrow.parquet as pq

    from oligo_engine.design.candidates import build_helm
    from oligo_engine.reward.chemistry import parse_helm

    prepared, runs = root / "preparation-v1", root / "scaling-v1"
    manifest = json.loads((prepared / "manifests.json").read_text())
    campaigns = [c for c in manifest["campaigns"] if c["role"] == "development"]
    allowed_test = {i for c in campaigns for i in c["test_ids"]}
    source_ids = set(manifest["source_train_ids"])
    reserved = {
        i
        for c in manifest["campaigns"]
        if c["role"] != "development"
        for i in c["test_ids"] + c["pool_ids"]
    }
    assert not (source_ids | allowed_test) & reserved
    metadata = pq.read_table(
        prepared / "cohort.parquet",
        columns=[
            "source_row_id",
            "HELM Annotation",
            "target_key",
            "cell_line",
            "cell_line_species",
            "transfection_method",
            "dosage_nm",
            "treatment_period_hrs",
        ],
        filters=[("source_row_id", "in", sorted(source_ids | allowed_test))],
    ).to_pandas()
    cache = {}
    for raw in metadata["HELM Annotation"].unique():
        c = parse_helm(raw)
        length19 = len(c.bases) == 19
        sugar = c.sugars == ("MOE",) * 5 + ("DNA",) * 10 + ("MOE",) * 4
        backbone = c.links == ("PS",) * 18 + ("END",) and c.terminal == "none"
        exact = False
        if length19:
            generated = build_helm(c.natural_rna.replace("U", "T"), "ps_moe_gapmer")
            # Chemical identity excludes raw HELM spelling/braces.
            exact = (
                c.identity == parse_helm(generated.replace("[m5C]", "[5meC]")).identity
            )
        cache[raw] = (length19, sugar, backbone, exact)
    columns = ["length19", "sugar_template", "backbone_template", "exact_template"]
    for index, column in enumerate(columns):
        metadata[column] = metadata["HELM Annotation"].map(lambda h: cache[h][index])
    coverage = []
    subsets = [("source_training", source_ids)] + [
        (c["target"], set(c["test_ids"])) for c in campaigns
    ]
    for name, ids in subsets:
        sub = metadata[metadata.source_row_id.isin(ids)]
        coverage.append(
            {
                "partition": name,
                "rows": len(sub),
                **{col: int(sub[col].sum()) for col in columns},
            }
        )
    exact_test = set(
        metadata.loc[
            metadata.exact_template & metadata.source_row_id.isin(allowed_test),
            "source_row_id",
        ]
    )
    # Define fixed model/protocol, top-k and tie handling before accessing labels.
    # Existing development evaluations only. No fine-tuning or model selection here.
    locked = []
    for p in sorted(runs.glob("target-*/predictions.json")):
        saved = json.loads(p.read_text())
        m = saved["metadata"]
        if not (
            (m["model"] == "target_only_ridge" and m["protocol"] == "target_only_all")
            or (
                m["model"] == "ridge"
                and m["source_budget"] == 4781
                and m["protocol"] == "sourcebest_offset_all"
            )
        ):
            continue
        ids, pred = saved["test_ids"], saved["predictions"]
        assert set(ids) <= allowed_test and not set(ids) & reserved
        for scope in ("all_development_chemistries", "exact_environment_template"):
            eligible = [
                i
                for i in range(len(ids))
                if scope.startswith("all_") or ids[i] in exact_test
            ]
            if len(eligible) < 20:
                continue
            chosen = sorted(eligible, key=lambda i: (-pred[i], ids[i]))[:20]
            locked.append(
                {
                    "model": m["model"],
                    "target": m["target"],
                    "seed": m["target_seed"],
                    "scope": scope,
                    "eligible_ids": [ids[i] for i in eligible],
                    "selected_ids": [ids[i] for i in chosen],
                }
            )
    labels = (
        pq.read_table(
            prepared / "cohort.parquet",
            columns=["source_row_id", "Inhibition_pct"],
            filters=[("source_row_id", "in", sorted(allowed_test))],
        )
        .to_pandas()
        .set_index("source_row_id")
        .Inhibition_pct
    )
    rows = []
    for selection in locked:
        all_y = labels.loc[selection["eligible_ids"]].to_numpy(float)
        selected_y = labels.loc[selection["selected_ids"]].to_numpy(float)
        assert np.isfinite(all_y).all() and np.isfinite(selected_y).all()
        # No unvalidated efficacy threshold; quality is the recorded endpoint itself.
        rows.append(
            {
                k: v
                for k, v in selection.items()
                if k not in ("eligible_ids", "selected_ids")
            }
            | {
                "n_candidates": len(all_y),
                "shortlist_size": 20,
                "selected_mean_inhibition": float(selected_y.mean()),
                "uniform_random_expected_mean": float(all_y.mean()),
                "difference_percentage_points": float(selected_y.mean() - all_y.mean()),
                "selected_ids": selection["selected_ids"],
            }
        )
    contexts = metadata[
        metadata.exact_template & metadata.source_row_id.isin(source_ids)
    ]
    keys = [
        "cell_line",
        "cell_line_species",
        "transfection_method",
        "dosage_nm",
        "treatment_period_hrs",
    ]
    common = (
        contexts.groupby(keys, dropna=False).size().sort_values(ascending=False).head(5)
    )

    def sugar_pattern(chemistry):
        segments = []
        for sugar in chemistry.sugars:
            if segments and segments[-1][0] == sugar:
                segments[-1][1] += 1
            else:
                segments.append([sugar, 1])
        return "/".join(f"{count}{sugar}" for sugar, count in segments)

    source_patterns = Counter(
        sugar_pattern(parse_helm(raw))
        for raw in metadata.loc[
            metadata.length19 & metadata.source_row_id.isin(source_ids),
            "HELM Annotation",
        ]
    )
    moe_counts, moe_patterns = Counter(), Counter()
    moe_path = Path("data/oligogym/MOE_Neurotox_1_processed.csv.gz")
    with gzip.open(moe_path, "rt", newline="") as handle:
        for row in csv.DictReader(handle):
            # Only HELM is analyzed; outcome columns are not accessed.
            chemistry = parse_helm(row["x"].replace("[m5C]", "[5meC]"))
            moe_counts["rows"] += 1
            if len(chemistry.bases) != 19:
                continue
            moe_counts["length19"] += 1
            pattern = sugar_pattern(chemistry)
            moe_patterns[
                (
                    pattern,
                    chemistry.links.count("PS"),
                    chemistry.links.count("PO"),
                    chemistry.terminal,
                )
            ] += 1
            generated = build_helm(
                chemistry.natural_rna.replace("U", "T"), "ps_moe_gapmer"
            )
            projected = parse_helm(generated.replace("[m5C]", "[5meC]"))
            if chemistry.identity == projected.identity:
                moe_counts["exact_template"] += 1
    return {
        "status": "posthoc_development_diagnostic_not_generated_candidate_validation",
        "coverage": coverage,
        "ranking_rows": rows,
        "source_context_examples": [
            dict(zip(keys, k)) | {"rows": int(v)} for k, v in common.items()
        ],
        "atlas_source_19mer_sugar_patterns": dict(source_patterns),
        "moe_structural_coverage": dict(moe_counts),
        "moe_common_19mer_patterns": [
            {
                "sugars": pattern,
                "PS_links": ps,
                "PO_links": po,
                "terminal": terminal,
                "rows": count,
            }
            for (pattern, ps, po, terminal), count in moe_patterns.most_common(10)
        ],
        "moe_file_sha256": hashlib.sha256(moe_path.read_bytes()).hexdigest(),
        "moe_outcomes_analyzed": False,
        "reserved_labels_read": False,
        "models_refit": False,
        "limitations": [
            "Existing development targets already evaluated in scaling study.",
            "Top20 are assay rows; repeated compounds and contexts may exist.",
            "This is not the PPO-generated panel and not a safety evaluation.",
            "No measurements exist for the synthetic CLI candidates.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["structural", "optimizers", "measured"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--atlas-root", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    receipt = args.output / f"{args.phase}.json"
    if receipt.exists():
        parser.error("Preserve existing receipt; use a new output directory")
    started = perf_counter()
    if args.phase == "structural":
        result = structural()
    elif args.phase == "optimizers":
        result = optimizers(args.output)
    else:
        if args.atlas_root is None:
            parser.error("--atlas-root required")
        result = measured(args.atlas_root)
    result["elapsed_seconds"] = perf_counter() - started
    result["code_revision"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    result["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result["dirty_checkout"] = bool(
        subprocess.check_output(["git", "status", "--porcelain"], text=True)
    )
    receipt.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Saved {receipt}", flush=True)


if __name__ == "__main__":
    main()
