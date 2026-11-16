"""Process-isolated actual Atlas artifacts with request timeout and strict IPC."""

import json
import os
import selectors
import subprocess
from pathlib import Path

from .contracts import Design
from .scoring import Prediction


class AtlasWorker:
    def __init__(
        self,
        python: Path,
        repository: Path,
        owner: Path,
        checkpoint: str,
        expected_hash: str,
        backbone: Path | None = None,
        cache: Path | None = None,
        adapt: bool = False,
        timeout: float = 120,
    ) -> None:
        self.timeout = timeout
        command = [
            str(python),
            "-u",
            str(repository / "scripts/atlas_inference_worker.py"),
            "--repository",
            str(repository),
            "--owner-checkout",
            str(owner),
            "--checkpoint",
            checkpoint,
        ]
        if backbone is not None:
            command += ["--backbone", str(backbone)]
        if cache is not None:
            command += ["--cache", str(cache)]
        if adapt:
            command += ["--adapt"]
        env = {
            **os.environ,
            "PYTHONPATH": str(owner / "src"),
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
        }
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        try:
            response = self._read()
            if not response.get("ready") or response["artifact_hash"] != expected_hash:
                raise ValueError("Wrong actual checkpoint loaded")
            self.receipt = response
        except Exception:
            self.close()
            raise

    def _read(self) -> dict:
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            if not selector.select(self.timeout):
                self.close()
                raise TimeoutError("Atlas inference process timed out")
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("Atlas inference process exited")
        response = json.loads(line)
        if "error" in response:
            raise RuntimeError(response["error"])
        return response

    def predict_batch(self, inputs: list[dict]) -> list[float]:
        self.process.stdin.write(json.dumps(inputs, allow_nan=False) + "\n")
        self.process.stdin.flush()
        values = self._read()["means"]
        if len(values) != len(inputs):
            raise ValueError("Atlas batch cardinality mismatch")
        return values

    def __call__(
        self, design: Design, context: tuple[tuple[str, str], ...]
    ) -> Prediction:
        return Prediction(
            self.predict_batch([{"HELM Annotation": design.helm, **dict(context)}])[0]
        )

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        for stream in (self.process.stdin, self.process.stdout):
            if stream:
                stream.close()

    def __enter__(self) -> "AtlasWorker":
        return self

    def __exit__(self, *args) -> None:
        self.close()
