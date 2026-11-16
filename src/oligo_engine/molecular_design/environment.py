"""Dependency-free state machine, with a separate optional Gymnasium adapter."""

from dataclasses import asdict
from typing import Callable

from .contracts import Campaign
from .grammar import Construction, Grammar, TransactionalGrammar
from .preflight import preflight
from .scoring import FrozenRegistry, Session


class DesignCore:
    def __init__(
        self,
        campaign: Campaign,
        registry: FrozenRegistry,
        site_capacity: int | None = None,
        archive_capacity: int | None = None,
        on_receipt: Callable[[dict], None] | None = None,
        decoder: str = "transactional-v2",
    ) -> None:
        report = preflight(campaign, registry)
        if report["status"] == "blocked":
            raise ValueError(f"Profile preflight failed: {report['reasons']}")
        self.campaign, self.registry = campaign, registry
        if decoder not in {"legacy-v1", "transactional-v2"}:
            raise ValueError("Unknown construction decoder")
        if decoder == "transactional-v2" and campaign.tokens < 7:
            raise ValueError("Transactional search needs seven construction tokens")
        self.decoder = decoder
        self.on_receipt = on_receipt
        grammar_class = Grammar if decoder == "legacy-v1" else TransactionalGrammar
        self.grammar = grammar_class(
            campaign,
            site_capacity or len(campaign.target.sequence),
            archive_capacity or campaign.requests,
        )
        self.reset()

    def reset(self) -> dict:
        self.session = Session(self.campaign, self.registry, self.on_receipt)
        self.construction = Construction()
        self.steps = 0
        self.done = self.session.remaining == 0
        self.end_reason = "request_budget" if self.done else ""
        self.actions: list[dict] = []
        return self.observe()

    def masks(self) -> list[bool]:
        if self.done:
            return [False] * len(self.grammar.tokens)
        mask = self.grammar.legal(self.construction, self.session.parents)
        if self.decoder == "transactional-v2" and self.construction.stage == "ready":
            remaining = self.campaign.tokens - self.steps
            for i, token in enumerate(self.grammar.tokens):
                if token.kind == "NEW" and remaining < 7:
                    mask[i] = False
                if token.kind == "PARENT" and remaining < 8:
                    mask[i] = False
            if not any(mask):
                mask[0] = True
        return mask

    def step(self, action: int) -> tuple[dict, float, bool, dict]:
        if self.done:
            raise RuntimeError("Episode already terminated")
        if type(action) is not int or not 0 <= action < len(self.grammar.tokens):
            raise ValueError("Action outside Discrete vocabulary")
        if not self.masks()[action]:
            raise ValueError("Action forbidden by published mask")
        state, design, stop = self.grammar.apply(
            self.construction, action, self.session.parents
        )
        self.steps += 1
        self.construction = state
        reward = 0.0
        if design is not None:
            try:
                _, reward = self.session.query(design)
            except Exception:
                self.done, self.end_reason = True, "execution_failed"
                raise
        self.done = (
            stop or self.session.remaining == 0 or self.steps >= self.campaign.tokens
        )
        if self.done:
            self.end_reason = (
                "stop"
                if stop
                else "request_budget"
                if self.session.remaining == 0
                else "construction_budget"
            )
        self.actions.append(
            {
                "action": action,
                "token": asdict(self.grammar.tokens[action]),
                "reward": reward,
                "requests": self.session.requests,
            }
        )
        return (
            self.observe(),
            reward,
            self.done,
            {"end_reason": self.end_reason, "quality": self.session.quality},
        )

    def observe(self) -> dict:
        """Full permitted state; includes no unqueried predictions."""
        return {
            "target": asdict(self.campaign.target),
            "profile": asdict(self.campaign.profile),
            "contexts": {
                h.manifest.name: dict(h.manifest.context) for h in self.registry.heads
            },
            "construction": asdict(self.construction),
            "history": self.session.trace,
            "archive_ids": list(self.session.archive),
            "remaining_requests": self.session.remaining,
            "remaining_tokens": self.campaign.tokens - self.steps,
            "quality": self.session.quality,
            "action_mask": self.masks(),
        }

    def receipt(self) -> dict:
        return {
            **self.session.receipt(),
            "decoder": self.decoder,
            "construction_tokens": self.steps,
            "end_reason": self.end_reason,
            "actions": self.actions,
            "status": "execution_failed"
            if self.session.failed
            else "complete"
            if self.done
            else "in_progress",
        }
