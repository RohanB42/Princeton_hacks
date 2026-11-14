"""Single-task ASO RNA-FM with aligned chemistry and reusable source priors."""

import copy
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn

from oligo_engine.atlas.baselines import BASES, LINKS, SUGARS, Features
from oligo_engine.atlas.chemistry import parse_helm
from oligo_engine.models.rnafm_lora import inject_qv_adapters, tensor_digest
from oligo_engine.representations.aso_rnafm import ASORNAFM


class ChemistryHead(nn.Module):
    def __init__(self, context_dim: int, hidden: int = 640):
        super().__init__()
        self.base = nn.Embedding(len(BASES) + 1, 8, padding_idx=len(BASES))
        self.sugar = nn.Embedding(len(SUGARS) + 1, 8, padding_idx=len(SUGARS))
        self.link = nn.Embedding(len(LINKS) + 1, 4, padding_idx=len(LINKS))
        self.terminal = nn.Embedding(3, 4)
        self.fusion = nn.Sequential(nn.Linear(hidden + 24, 64), nn.GELU())
        self.output = nn.Sequential(
            nn.Linear(64 + context_dim, 64), nn.GELU(), nn.Linear(64, 1)
        )

    def forward(self, h, mask, base, sugar, link, terminal, context):
        t = self.terminal(terminal)[:, None, :].expand(-1, h.shape[1], -1)
        features = torch.cat(
            [h, self.base(base), self.sugar(sugar), self.link(link), t], dim=-1
        )
        z = self.fusion(features) * mask[:, :, None]
        pooled = z.sum(dim=1) / mask.sum(dim=1, keepdim=True)
        return self.output(torch.cat([pooled, context], dim=-1)).squeeze(-1)


class ASOPredictor:
    def __init__(self, checkpoint: Path, cache: Path, seed: int, adapt: bool):
        torch.manual_seed(seed)
        self.encoder = ASORNAFM(checkpoint, cache)
        self.adapt, self.seed = adapt, seed
        if adapt:
            inject_qv_adapters(self.encoder.backbone, 4, 8.0)
        self.encoder.backbone.eval()
        self.context = Features(chemistry=False)
        self.head = None
        self.receipts = []

    def _base(self) -> dict:
        return {
            k: v
            for k, v in self.encoder.backbone.state_dict().items()
            if ".parametrizations." not in k or k.endswith(".original")
        }

    def _trainable_state(self) -> dict:
        return {
            k: v.detach().clone()
            for k, v in self.encoder.backbone.named_parameters()
            if v.requires_grad
        }

    def snapshot(self) -> dict:
        return {
            "head": copy.deepcopy(self.head.state_dict()),
            "adapters": self._trainable_state(),
            "context": copy.deepcopy(self.context),
            "mean": self.mean,
            "scale": self.scale,
            "source_ids": list(self.source_ids),
            "encoder_identity": self.encoder.identity,
        }

    def restore(self, state: dict) -> None:
        if state["encoder_identity"] != self.encoder.identity:
            raise ValueError("Wrong source checkpoint")
        self.head.load_state_dict(state["head"])
        with torch.no_grad():
            for k, v in self.encoder.backbone.named_parameters():
                if v.requires_grad:
                    v.copy_(state["adapters"][k])
        self.context = copy.deepcopy(state["context"])
        self.mean = state["mean"]
        self.scale = state["scale"]
        self.source_ids = list(state["source_ids"])

    def _batch(self, frame: pd.DataFrame, frozen: list[np.ndarray] | None = None):
        parsed = [parse_helm(h) for h in frame["HELM Annotation"]]
        seq = [c.natural_rna for c in parsed]
        if frozen is None:
            h, mask = self.encoder.forward(seq)
        else:
            width = max(map(len, seq))
            h = torch.zeros(len(seq), width, 640)
            mask = (
                torch.arange(width)[None, :]
                < torch.tensor(list(map(len, seq)))[:, None]
            )
            for i, a in enumerate(frozen):
                h[i, : len(a)] = torch.from_numpy(a)
        base = torch.full(mask.shape, len(BASES), dtype=torch.long)
        sugar = torch.full(mask.shape, len(SUGARS), dtype=torch.long)
        link = torch.full(mask.shape, len(LINKS), dtype=torch.long)
        for i, c in enumerate(parsed):
            base[i, : len(c.bases)] = torch.tensor([BASES.index(b) for b in c.bases])
            sugar[i, : len(c.bases)] = torch.tensor([SUGARS.index(s) for s in c.sugars])
            link[i, : len(c.bases)] = torch.tensor(
                [LINKS.index(linkage) for linkage in c.links]
            )
        terminal = torch.tensor(
            [["none", "PO", "PS"].index(c.terminal) for c in parsed]
        )
        context = torch.tensor(
            self.context.transform(frame).toarray(), dtype=torch.float32
        )
        return self.head(h, mask, base, sugar, link, terminal, context)

    def fit(
        self,
        frame: pd.DataFrame,
        y: np.ndarray,
        epochs: int = 3,
        source: dict | None = None,
        *,
        validation: tuple[pd.DataFrame, np.ndarray] | None = None,
        record_history: bool = False,
        min_epochs: int = 3,
        patience: int = 5,
        min_delta: float = 1e-6,
        checkpoint_epochs: tuple[int, ...] = (),
        epoch_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        if "Inhibition_pct" in frame:
            raise ValueError("Labels in predictor records")
        if len(frame) != len(y) or not np.isfinite(y).all():
            raise ValueError("Invalid labels")
        if epochs < 1 or patience < 1 or min_epochs < 1 or min_delta < 0:
            raise ValueError("Invalid epoch-selection settings")
        validation_ids = []
        if validation is not None:
            vf, vy = validation
            if "Inhibition_pct" in vf or len(vf) != len(vy):
                raise ValueError("Invalid validation records")
            if not len(vf) or not np.isfinite(vy).all():
                raise ValueError("Invalid validation labels")
            validation_ids = vf.source_row_id.tolist()
            if set(frame.source_row_id) & set(validation_ids):
                raise ValueError("Fitting and validation rows overlap")
        self.history, self.checkpoints = [], {}
        best_state, best_score, best_epoch, stale = None, float("inf"), None, 0
        start = time.monotonic()
        if source is None:
            if self.head is not None:
                raise ValueError("New source fit requires a fresh predictor")
            self.context.fit(frame)
            torch.manual_seed(self.seed + 10000)
            self.head = ChemistryHead(self.context.transform(frame.iloc[:1]).shape[1])
            self.mean = float(np.mean(y))
            self.scale = max(float(np.std(y)), 1.0)
            self.source_ids = frame.source_row_id.tolist()
        else:
            self.restore(source)
        before = tensor_digest(self._base())
        adapters_before = tensor_digest(self._trainable_state())
        params = list(self.head.parameters()) + [
            v for v in self.encoder.backbone.parameters() if v.requires_grad
        ]
        optimizer = torch.optim.AdamW(params, lr=0.001, weight_decay=0.0)
        target = torch.tensor(
            (np.asarray(y) - self.mean) / self.scale, dtype=torch.float32
        )
        frozen = (
            None
            if self.adapt
            else self.encoder.encode_helms(frame["HELM Annotation"].tolist())
        )
        rng = np.random.default_rng(self.seed)
        self.head.train()
        for epoch in range(1, epochs + 1):
            self.head.train()
            running_loss = 0.0
            order = rng.permutation(len(frame))
            for start_idx in range(0, len(frame), 8):
                ix = order[start_idx : start_idx + 8]
                optimizer.zero_grad()
                pred = self._batch(
                    frame.iloc[ix], None if frozen is None else [frozen[i] for i in ix]
                )
                loss = nn.functional.mse_loss(pred, target[ix])
                if not torch.isfinite(loss):
                    raise FloatingPointError("Nonfinite training loss")
                running_loss += float(loss.detach()) * len(ix)
                loss.backward()
                nn.utils.clip_grad_norm_(params, 1.0)
                optimizer.step()
            if record_history or validation is not None:
                train_mse = float(np.mean((self.predict(frame) - y) ** 2))
                row = {
                    "epoch": epoch,
                    "train_mse": train_mse,
                    "train_rmse": train_mse**0.5,
                    "train_normalized_mse": train_mse / self.scale**2,
                    "minibatch_normalized_mse": running_loss / len(frame),
                }
                if validation is not None:
                    val_mse = float(np.mean((self.predict(vf) - vy) ** 2))
                    score = val_mse**0.5
                    if not np.isfinite(score):
                        raise FloatingPointError("Nonfinite validation loss")
                    improved = score < best_score - min_delta
                    if improved:
                        best_state, best_score = self.snapshot(), score
                        best_epoch, stale = epoch, 0
                    else:
                        stale += 1
                    row.update(
                        validation_mse=val_mse,
                        validation_rmse=score,
                        validation_normalized_mse=val_mse / self.scale**2,
                        best_epoch=best_epoch,
                        improved=improved,
                    )
                row["elapsed_s"] = time.monotonic() - start
                self.history.append(row)
                if epoch_callback is not None:
                    epoch_callback(copy.deepcopy(row))
            if epoch in checkpoint_epochs:
                self.checkpoints[epoch] = self.snapshot()
            if validation is not None and epoch >= min_epochs and stale >= patience:
                break
        if best_state is not None:
            self.restore(best_state)
        self.head.eval()
        after = tensor_digest(self._base())
        changed = adapters_before != tensor_digest(self._trainable_state())
        if before != after:
            raise AssertionError("Frozen base changed")
        if self.adapt and not changed:
            raise AssertionError("Adapters did not update")
        receipt = {
            "ids": frame.source_row_id.tolist(),
            "n_labels": len(frame),
            "source_labels": len(self.source_ids),
            "source_ids": self.source_ids,
            "epochs": epoch,
            "requested_epochs": epochs,
            "history": copy.deepcopy(self.history),
            "validation_ids": validation_ids,
            "validation_labels": len(validation_ids),
            "total_fit_validation_labels": len(frame) + len(validation_ids),
            "selected_epoch": best_epoch if validation is not None else epoch,
            "restored_best": best_state is not None,
            "min_epochs": min_epochs if validation is not None else None,
            "patience": patience if validation is not None else None,
            "min_delta_rmse": min_delta if validation is not None else None,
            "saved_checkpoint_epochs": sorted(self.checkpoints),
            "base_unchanged": before == after,
            "adapters_changed": changed,
            "elapsed_s": time.monotonic() - start,
            "trainable_parameters": sum(v.numel() for v in params),
        }
        self.receipts.append(receipt)
        return receipt

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        if "Inhibition_pct" in frame:
            raise ValueError("Labels in prediction records")
        predictions = []
        frozen = (
            None
            if self.adapt
            else self.encoder.encode_helms(frame["HELM Annotation"].tolist())
        )
        self.head.eval()
        with torch.no_grad():
            for start in range(0, len(frame), 16):
                pred = self._batch(
                    frame.iloc[start : start + 16],
                    None if frozen is None else frozen[start : start + 16],
                )
                predictions.extend(
                    (pred * self.scale + self.mean).cpu().numpy().tolist()
                )
        return np.array(predictions)
