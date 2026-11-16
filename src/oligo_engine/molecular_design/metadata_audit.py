"""Read source chemistry/context columns only; never load outcome columns."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from oligo_engine.provenance import identity
from oligo_engine.reward.chemistry import parse_helm

CONTEXTS = {
    "in_vitro_inhibition": (
        "cell_line",
        "cell_line_species",
        "dosage_nm",
        "transfection_method",
        "treatment_period_hrs",
    ),
    "neurotoxicity": (
        "species",
        "species_strain",
        "dosage_ug",
        "latency_time_hours",
        "administration_method",
        "tolerability_score_type",
    ),
    "hepatotoxicity": (
        "species",
        "species_strain",
        "dosage_mg_per_kg",
        "num_doses",
        "dosing_period_days",
        "adminstration_method",
        "measurement_source",
    ),
}


def audit_atlas(root: Path) -> dict:
    import pyarrow.parquet as pq

    reports, signatures = {}, {}
    source_manifest = json.loads((root.parent / "cleaned/audit.json").read_text())
    for endpoint, context_fields in CONTEXTS.items():
        source = root / f"{endpoint}.parquet"
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        if source_hash != source_manifest["endpoints"][endpoint]["source_sha256"]:
            raise ValueError("Atlas source bytes differ from pinned release")
        columns = ["HELM Annotation", "USPTO ID", "target_RNA", *context_fields]
        table = pq.read_table(root / f"{endpoint}.parquet", columns=columns)
        counts, contexts, patents = Counter(), Counter(), defaultdict(set)
        failures = missing = 0
        for row in table.to_pylist():
            helm = row["HELM Annotation"]
            if not isinstance(helm, str):
                missing += 1
                continue
            try:
                c = parse_helm(helm.replace("[m5C]", "[5meC]"))
            except ValueError:
                failures += 1
                continue
            signature = identity((c.sugars, c.links, c.terminal))
            signatures.setdefault(
                signature,
                {
                    "length": len(c.bases),
                    "sugars": c.sugars,
                    "links": c.links,
                    "terminal": c.terminal,
                },
            )
            counts[signature] += 1
            patents[signature].add(row["USPTO ID"])
            context = tuple((field, str(row[field])) for field in context_fields)
            contexts[context] += 1
        reports[endpoint] = {
            "source_sha256": source_hash,
            "source_rows": len(table),
            "missing_helm": missing,
            "parser_rejections": failures,
            "metadata_columns_read": columns,
            "patterns": {
                k: {"rows": v, "patents": len(patents[k])} for k, v in counts.items()
            },
            "contexts": [
                {"context": dict(k), "rows": v} for k, v in contexts.most_common()
            ],
        }
    efficacy = reports["in_vitro_inhibition"]["patterns"]
    neuro = reports["neurotoxicity"]["patterns"]
    shared = sorted(
        set(efficacy) & set(neuro),
        key=lambda k: -min(efficacy[k]["rows"], neuro[k]["rows"]),
    )
    return {
        "schema": "atlas-molecular-metadata-v1",
        "endpoints": reports,
        "shared_efficacy_neuro_structural_patterns": [
            {
                "signature": k,
                **signatures[k],
                "efficacy": efficacy[k],
                "neuro": neuro[k],
            }
            for k in shared
        ],
        "qualification": (
            "Structural overlap only. Base modifications, model "
            "membership, context transfer, screening and independent evidence "
            "remain unaudited."
        ),
        "outcomes_read": False,
    }
