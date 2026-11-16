"""Local frozen-profile molecular designer. Never fits or downloads a model."""

import argparse
import json
import uuid
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from oligo_engine.molecular_design.artifacts import (
    QueryJournal,
    export_csv,
    run_artifact,
    write_new,
)
from oligo_engine.molecular_design.cli import load_study
from oligo_engine.molecular_design.optimizers import search
from oligo_engine.molecular_design.preflight import preflight
from oligo_engine.molecular_design.scoring import Session


class MolecularService:
    def __init__(self, config: Path, output: Path, policy: Path | None = None) -> None:
        self.config, self.campaigns, self.registry = load_study(config)
        self.output, self.policy = output, policy
        self.methods = ["random", "greedy", "genetic", "sweep", "initial"]
        if policy is not None:
            self.methods.append("ppo")

    def metadata(self) -> dict:
        return {
            "campaigns": [
                preflight(c, self.registry)
                | {
                    "max_requests": c.requests,
                    "gene": c.target.gene,
                    "transcript": c.target.transcript,
                    "applicability": c.profile.applicability,
                }
                for c in self.campaigns
            ],
            "methods": self.methods,
            "risk": "model-based screens"
            if any(h.manifest.property_kind == "risk" for h in self.registry.heads)
            else "unknown: no applicable risk predictor",
            "claim": "Generated molecules are unvalidated computational hypotheses.",
        }

    def run(self, parameters: dict) -> dict:
        if set(parameters) - {
            "campaign",
            "method",
            "requests",
            "seed",
            "panel_size",
            "diversity",
        }:
            raise ValueError("Unknown request fields")
        index = parameters.get("campaign", 0)
        if type(index) is not int or not 0 <= index < len(self.campaigns):
            raise ValueError("Unknown campaign")
        campaign = self.campaigns[index]
        budget = parameters.get("requests", campaign.requests)
        if (
            type(budget) is not int
            or not max(1, len(campaign.starts)) <= budget <= campaign.requests
        ):
            raise ValueError("Budget outside compiled campaign limits")
        method = parameters.get("method", "random")
        if method not in self.methods:
            raise ValueError("Unknown optimizer")
        seed, size = parameters.get("seed", 0), parameters.get("panel_size", 10)
        diversity = parameters.get("diversity", 0.0)
        if type(diversity) not in {float, int} or not 0 <= diversity <= 1:
            raise ValueError("Panel diversity must be between zero and one")
        if type(seed) is not int or type(size) is not int or not 1 <= size <= 100:
            raise ValueError("Integer seed and panel size 1–100 required")
        if campaign.partition == "final":
            raise ValueError("Locked final campaigns run through the study CLI")
        campaign = replace(campaign, requests=budget)
        name = uuid.uuid4().hex
        journal = QueryJournal(self.output / f"{name}.queries.jsonl")
        if method == "ppo":
            from oligo_engine.molecular_design.gym_env import MolecularEnv
            from oligo_engine.molecular_design.training import load_policy, rollout

            training = json.loads((self.policy / "training.json").read_text())
            env = MolecularEnv(
                (campaign,),
                self.registry,
                training["protocol"]["site_capacity"],
                training["protocol"]["archive_capacity"],
                journal,
                decoder=training["protocol"]["config"].get("decoder", "legacy-v1"),
                candidate_capacity=training["protocol"]["config"].get(
                    "candidate_capacity"
                ),
                collapse_forced=training["protocol"]["config"].get(
                    "collapse_forced", False
                ),
            )
            receipt = rollout(load_policy(self.policy, env), env, seed=seed)
        else:
            receipt = search(Session(campaign, self.registry, journal), method, seed)
        artifact = run_artifact(campaign, receipt, size, diversity)
        self.output.mkdir(parents=True, exist_ok=True)
        write_new(self.output / f"{name}.json", artifact)
        export_csv(artifact, self.output / f"{name}.csv")
        return {"artifact": artifact, "run_id": name}


def handler(service: MolecularService) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def send(self, raw: bytes, content_type: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            if self.path == "/":
                self.send(
                    (Path(__file__).parent / "static/molecular.html").read_bytes(),
                    "text/html; charset=utf-8",
                )
            elif self.path == "/styles.css":
                self.send(
                    (Path(__file__).parent / "static/styles.css").read_bytes(),
                    "text/css",
                )
            elif self.path == "/api/profile":
                self.send(json.dumps(service.metadata()).encode(), "application/json")
            elif self.path.startswith("/runs/"):
                name = self.path.removeprefix("/runs/")
                stem, _, suffix = name.partition(".")
                if (
                    len(stem) != 32
                    or any(c not in "0123456789abcdef" for c in stem)
                    or suffix not in {"json", "csv"}
                ):
                    self.send(b"Invalid run", "text/plain", 400)
                    return
                path = service.output / name
                if not path.is_file():
                    self.send(b"Not found", "text/plain", 404)
                    return
                self.send(
                    path.read_bytes(),
                    "application/json" if suffix == "json" else "text/csv",
                )
            else:
                self.send(b"Not found", "text/plain", 404)

        def do_POST(self) -> None:
            if self.path != "/api/search":
                self.send(b"Not found", "text/plain", 404)
                return
            # Only local same-origin JSON requests can launch computation.
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.send(b"JSON required", "text/plain", 415)
                return
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + self.headers.get("Host", ""):
                self.send(b"Origin mismatch", "text/plain", 403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4096:
                    raise ValueError("Request must be 1–4096 bytes")
                value = json.loads(self.rfile.read(length))
                if not isinstance(value, dict):
                    raise ValueError("JSON object required")
                result = service.run(value)
                self.send(
                    json.dumps(result, allow_nan=False).encode(), "application/json"
                )
            except (ValueError, KeyError) as exc:
                self.send(
                    json.dumps({"error": str(exc)}).encode(), "application/json", 400
                )
            except Exception as exc:
                self.send(
                    json.dumps(
                        {"error": str(exc), "status": "execution_failed"}
                    ).encode(),
                    "application/json",
                    500,
                )

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/molecular-app"))
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    service = MolecularService(args.config, args.output, args.policy)
    print(f"Molecular designer: http://127.0.0.1:{args.port}", flush=True)
    HTTPServer(("127.0.0.1", args.port), handler(service)).serve_forever()


if __name__ == "__main__":
    main()
