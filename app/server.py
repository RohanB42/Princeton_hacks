"""Local JSON API and static host for the design surface.

Standard library only, so the surface runs in the same pinned environment as the
predictors and adds no dependency to the project. The front end is static files and
the API is plain JSON, so the same two pieces can later sit behind any production
server without changing either.

    PYTHONPATH=src python app/server.py --port 8000

Nothing here evaluates a model. Every prediction is produced by a predictor refit on
all labelled rows of its dataset, and every response carries the held-out accuracy
measured in the matching study document, the chemistry each model may be applied to,
and the endpoints that are not modelled at all.
"""

import argparse
import csv
import io
import json
import threading
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from oligo_engine.design import candidates as design
from oligo_engine.design.engine import DesignEngine
from oligo_engine.design.structure import duplex_pdb
from oligo_engine.design.transcripts import TranscriptError, fetch, from_sequence

STATIC = Path(__file__).resolve().parent / "static"
ENGINE = DesignEngine()
CACHE: dict[tuple, dict] = {}
LOCK = threading.Lock()
MAX_CANDIDATES = 4000
ENRICH_TOP = 60

NON_CLAIMS = [
    "Designed candidates are unvalidated hypotheses. None has been synthesised or"
    " tested, and no claim is made that any of them works or is safe.",
    "Predicted values are predictions, not observations.",
    "Target knockdown is not modelled at all; this ranks safety and sequence flags.",
    "A model is only applied to the chemistry it was fitted on. Endpoints outside"
    " that chemistry are withheld rather than extrapolated.",
    "The 3D view is an idealized helix drawn from the sequence, not a predicted"
    " structure.",
]


def _summary(rows: list[dict], endpoint: str | None) -> dict:
    """Headline honesty numbers: how far outside its training data this panel sits."""
    if not endpoint or not rows:
        return {}
    import numpy as np
    from scipy.stats import spearmanr

    model = ENGINE.model(endpoint)
    labels = model.label_stats["values"]
    low, high = min(labels), max(labels)
    values = np.array([r["predictions"][endpoint]["value"] for r in rows])
    novelty = np.array([r["predictions"][endpoint]["novelty_percentile"] for r in rows])
    guanine = np.array(
        [
            99
            if r["guanine_distance_from_3prime"] is None
            else r["guanine_distance_from_3prime"]
            for r in rows
        ]
    )
    runs = np.array([r["longest_g_run"] for r in rows])
    agreement = {}
    if len(rows) > 20 and endpoint == "neurotox_moe":
        agreement = {
            "guanine_distance_from_3prime": float(spearmanr(values, guanine).statistic),
            "longest_g_run": float(spearmanr(values, runs).statistic),
            "note": (
                "Published association: a guanine closer to the 3' end correlates"
                " with acute neurotoxicity. The model was never given that rule;"
                " a negative distance correlation means it agrees with it."
            ),
        }
    return {
        "candidates_scored": len(rows),
        "measured_label_range": [low, high],
        "outside_measured_range": int(((values < low) | (values > high)).sum()),
        "median_novelty_percentile": float(np.median(novelty)),
        "novelty_note": (
            "Percentile against how far labelled molecules sit from their own"
            " nearest labelled neighbour. Near 100 means this candidate is further"
            " from the training data than almost any training molecule is, so its"
            " prediction is an extrapolation."
        ),
        "heuristic_agreement": agreement,
    }


def _panel(params: dict, sequence: str | None = None) -> dict:
    gene = (params.get("gene", ["MAPT"])[0] or "MAPT").strip()
    chemistry = params.get("chemistry", ["ps_moe_gapmer"])[0]
    if chemistry not in design.CHEMISTRIES:
        raise ValueError(f"Unknown chemistry {chemistry!r}")
    step = max(1, min(50, int(params.get("step", ["3"])[0])))
    limit = max(1, min(200, int(params.get("limit", ["40"])[0])))
    sort = params.get("sort", ["safety"])[0]
    key = (gene, chemistry, step, sequence or "")

    with LOCK:
        cached = CACHE.get(key)
    if cached is None:
        transcript = from_sequence(sequence, gene=gene) if sequence else fetch(gene)
        pool = design.tile(
            transcript.gene,
            transcript.transcript_id,
            transcript.sequence,
            chemistry=chemistry,
            step=step,
        )
        if not pool:
            raise ValueError("Transcript is too short to tile at this length")
        truncated = len(pool) > MAX_CANDIDATES
        pool = pool[:MAX_CANDIDATES]
        rows = ENGINE.score(pool)
        endpoints = ENGINE.endpoints_for(chemistry)
        primary = endpoints[0] if endpoints else None
        cached = {
            "transcript": transcript.as_dict(),
            "transcript_sequence_length": len(transcript.sequence),
            "chemistry": chemistry,
            "design": design.DESIGNS[chemistry],
            "step": step,
            "truncated": truncated,
            "endpoints": ENGINE.endpoint_metadata(chemistry),
            "primary_endpoint": primary,
            "rows": rows,
            "summary": _summary(rows, primary),
            "non_claims": NON_CLAIMS,
            "_transcript_sequence": transcript.sequence,
        }
        with LOCK:
            CACHE[key] = cached

    rows = list(cached["rows"])
    primary = cached["primary_endpoint"]

    def sort_key(row):
        predictions = row["predictions"]
        if sort == "position":
            return row["start"]
        if sort == "accessibility":
            return -(row.get("target_accessibility") or 0)
        if primary and primary in predictions:
            spec = ENGINE.model(primary).spec
            value = predictions[primary]["value"]
            if spec["direction"] == "deviation_from_baseline":
                return abs(value - spec["baseline"])
            return value
        return row["start"]

    rows.sort(key=sort_key)
    top = [dict(row) for row in rows[:limit]]
    for row in top:
        if row.get("hairpin_dg") is None:
            row["hairpin_dg"] = design.hairpin_dg(row["sequence"])
        if row.get("target_accessibility") is None and len(top) <= ENRICH_TOP:
            row["target_accessibility"] = design.target_accessibility(
                cached["_transcript_sequence"], row["start"], row["end"]
            )
    payload = {k: v for k, v in cached.items() if not k.startswith("_")}
    payload["rows"] = top
    payload["sort"] = sort
    payload["returned"] = len(top)
    return payload


def _csv(payload: dict) -> str:
    buffer = io.StringIO()
    endpoints = sorted(payload["endpoints"]["applicable"])
    columns = [
        "rank",
        "candidate_id",
        "sequence",
        "chemistry",
        "helm",
        "gene",
        "transcript_id",
        "target_start",
        "target_end",
        "target_window",
        "gc_fraction",
        "cpg_count",
        "guanine_distance_from_3prime",
        "longest_g_run",
        "hairpin_dg",
        "target_accessibility",
    ]
    for endpoint in endpoints:
        columns += [
            f"{endpoint}_predicted",
            f"{endpoint}_uncertainty",
            f"{endpoint}_novelty_percentile",
        ]
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "# UNVALIDATED HYPOTHESES - nothing here has been synthesised"
            " or tested. Predictions are not observations."
        ]
    )
    writer.writerow(
        [
            f"# gene={payload['transcript']['gene']}"
            f" transcript={payload['transcript']['transcript_id']}"
            f" chemistry={payload['chemistry']}"
        ]
    )
    writer.writerow(columns)
    for rank, row in enumerate(payload["rows"], start=1):
        record = [
            rank,
            row["candidate_id"],
            row["sequence"],
            row["chemistry"],
            row["helm"],
            payload["transcript"]["gene"],
            payload["transcript"]["transcript_id"],
            row["start"],
            row["end"],
            row["target_window"],
            round(row["gc_fraction"], 4),
            row["cpg_count"],
            row["guanine_distance_from_3prime"],
            row["longest_g_run"],
            row["hairpin_dg"],
            row["target_accessibility"],
        ]
        for endpoint in endpoints:
            prediction = row["predictions"].get(endpoint, {})
            record += [
                prediction.get("value"),
                prediction.get("uncertainty"),
                prediction.get("novelty_percentile"),
            ]
        writer.writerow(record)
    return buffer.getvalue()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def log_message(self, fmt, *args):  # quieter console
        if "/api/" in (args[0] if args else ""):
            super().log_message(fmt, *args)

    def _send(self, payload, status=200, content_type="application/json"):
        body = payload if isinstance(payload, bytes) else payload.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, exc, status=400):
        self._send(json.dumps({"error": str(exc)}), status=status)

    def do_GET(self):
        route = urlparse(self.path)
        params = parse_qs(route.query)
        try:
            if route.path == "/api/meta":
                return self._send(
                    json.dumps(
                        {
                            "chemistries": design.DESIGNS,
                            "endpoints": {
                                c: ENGINE.endpoint_metadata(c)
                                for c in design.CHEMISTRIES
                            },
                            "non_claims": NON_CLAIMS,
                        }
                    )
                )
            if route.path == "/api/design":
                return self._send(json.dumps(_panel(params)))
            if route.path == "/api/panel.csv":
                payload = _panel(params)
                name = f"{payload['transcript']['gene']}-candidates.csv"
                self.send_response(200)
                self.send_header("Content-Type", "text/csv")
                self.send_header(
                    "Content-Disposition", f'attachment; filename="{name}"'
                )
                body = _csv(payload).encode()
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                return self.wfile.write(body)
            if route.path == "/api/structure":
                sequence = params.get("sequence", [""])[0].upper()
                chemistry = params.get("chemistry", ["ps_moe_gapmer"])[0]
                spec = design.DESIGNS[chemistry]
                pdb = duplex_pdb(
                    sequence,
                    chemistry,
                    spec["wing5"],
                    spec["wing3"],
                    params.get("title", ["designed ASO"])[0],
                )
                return self._send(pdb, content_type="chemical/x-pdb")
        except (TranscriptError, ValueError) as error:
            return self._error(error)
        except Exception as error:  # surface the traceback locally, never silently
            traceback.print_exc()
            return self._error(error, status=500)
        return super().do_GET()

    def do_POST(self):
        route = urlparse(self.path)
        if route.path != "/api/design":
            return self._error(ValueError("Unknown endpoint"), status=404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or "{}")
            params = {k: [str(v)] for k, v in body.items() if k != "sequence"}
            return self._send(json.dumps(_panel(params, body.get("sequence"))))
        except (TranscriptError, ValueError) as error:
            return self._error(error)
        except Exception as error:
            traceback.print_exc()
            return self._error(error, status=500)


def warm() -> None:
    for key in ENDPOINT_KEYS:
        try:
            ENGINE.model(key)
            print(f"  fitted {key}", flush=True)
        except Exception as error:  # a missing endpoint must not stop the server
            print(f"  WARNING {key} unavailable: {error}", flush=True)


ENDPOINT_KEYS = ("neurotox_moe", "tlr7_inhibition", "tlr8_potentiation")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-warm", action="store_true")
    args = parser.parse_args()
    if not args.no_warm:
        print("Fitting endpoint predictors on all labelled rows...", flush=True)
        warm()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"\n  Design surface on http://{args.host}:{args.port}\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
