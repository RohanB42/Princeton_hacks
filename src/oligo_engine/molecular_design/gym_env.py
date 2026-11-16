"""Optional Gymnasium observation encoding. No sequence/history truncation."""

import json
from dataclasses import asdict
from typing import Callable

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from oligo_engine.provenance import identity

from .contracts import Campaign
from .environment import DesignCore
from .grammar import STAGES, Grammar, Token, TransactionalGrammar
from .preflight import preflight
from .scoring import FrozenRegistry


class MolecularEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        campaigns: tuple[Campaign, ...],
        registry: FrozenRegistry,
        site_capacity: int | None = None,
        archive_capacity: int | None = None,
        on_receipt: Callable[[dict], None] | None = None,
        decoder: str = "transactional-v2",
        candidate_capacity: int | None = None,
        collapse_forced: bool = False,
    ) -> None:
        if not campaigns or any(
            c.profile.key != registry.profile.key for c in campaigns
        ):
            raise ValueError("One compatible frozen profile per policy")
        if any(c.requests <= len(c.starts) for c in campaigns):
            raise ValueError("Gym episodes require at least one request after starts")
        self.campaigns, self.registry = campaigns, registry
        if decoder not in {"legacy-v1", "transactional-v2"}:
            raise ValueError("Unknown construction decoder")
        if decoder == "transactional-v2" and any(c.tokens < 7 for c in campaigns):
            raise ValueError(
                "Transactional search needs at least seven construction tokens"
            )
        self.decoder = decoder
        if (
            candidate_capacity is not None or collapse_forced
        ) and decoder != "transactional-v2":
            raise ValueError("Candidate representation/forced collapse requires v2")
        self.candidate_capacity = candidate_capacity
        self.collapse_forced = collapse_forced
        self.policy_decisions = 0
        self._candidate_cache = {}
        self.on_receipt = on_receipt
        self.site_capacity = site_capacity or max(
            len(c.target.sequence) for c in campaigns
        )
        self.archive_capacity = archive_capacity or max(c.requests for c in campaigns)
        self.max_length = max(p.length for p in registry.profile.patterns)
        # Construction of a Gym wrapper must never incur hidden initial queries.
        self.core = None
        for campaign in campaigns:
            Grammar(campaign, self.site_capacity, self.archive_capacity)
            if preflight(campaign, registry)["status"] == "blocked":
                raise ValueError("Campaign metadata preflight failed")
        grammar = Grammar(campaigns[0], self.site_capacity, self.archive_capacity)
        self.patterns = registry.profile.patterns
        self.context_bytes = (
            np.frombuffer(
                json.dumps(
                    [
                        asdict(h.manifest)
                        | {
                            "training_ids": (),
                            "validation_ids": (),
                            "calibration_ids": (),
                            "reference": (),
                        }
                        for h in registry.heads
                    ],
                    sort_keys=True,
                ).encode(),
                dtype=np.uint8,
            ).astype(np.float32)
            / 255
        )
        self.history_width = 9 + sum(
            8 + len(h.manifest.diagnostics) for h in registry.heads
        )
        self.observation_space = spaces.Dict(
            {
                "target": spaces.Box(0, 1, (self.site_capacity, 7), np.float32),
                "patterns": spaces.Box(
                    0, 1, (len(self.patterns), self.max_length, 9), np.float32
                ),
                "construction": spaces.Box(
                    -1, 1, (17 if decoder == "transactional-v2" else 16,), np.float32
                ),
                "history": spaces.Box(
                    -np.inf,
                    np.inf,
                    (self.archive_capacity, self.history_width),
                    np.float32,
                ),
                "history_mask": spaces.Box(0, 1, (self.archive_capacity,), np.float32),
                "context": spaces.Box(0, 1, self.context_bytes.shape, np.float32),
                "action_mask": spaces.Box(0, 1, (len(grammar.tokens),), np.float32),
            }
        )
        self.action_space = spaces.Discrete(len(grammar.tokens))
        if candidate_capacity is not None:
            if candidate_capacity < max(sum(1 for _ in c.designs()) for c in campaigns):
                raise ValueError("Candidate capacity must include every legal design")
            self.observation_space.spaces.update(
                {
                    "candidates": spaces.Box(
                        0, 1, (candidate_capacity, self.max_length, 16), np.float32
                    ),
                    "candidate_tokens": spaces.Box(
                        0, len(grammar.tokens) - 1, (candidate_capacity, 5), np.float32
                    ),
                    "candidate_mask": spaces.Box(
                        0, 1, (candidate_capacity,), np.float32
                    ),
                    "completion_mask": spaces.Box(
                        0, 1, (candidate_capacity,), np.float32
                    ),
                }
            )
        self.schema_id = identity(
            {
                "version": "full-history-v1"
                if decoder == "legacy-v1"
                else "full-history-v2-transactional",
                "profile": registry.profile.key,
                "registry": registry.key,
                "site_capacity": self.site_capacity,
                "archive_capacity": self.archive_capacity,
                "tokens": [asdict(t) for t in grammar.tokens],
                "history_encoding": "raw-asinh-with-presence-and-diagnostic-schema-v1",
                **(
                    {
                        "candidate_encoding": "antisense-chemistry-v3",
                        "candidate_capacity": candidate_capacity,
                    }
                    if candidate_capacity is not None
                    else {}
                ),
                **({"collapse_forced": True} if collapse_forced else {}),
            }
        )

    def reset(
        self, *, seed: int | None = None, options: dict | None = None
    ) -> tuple[dict[str, np.ndarray], dict]:
        super().reset(seed=seed)
        index = int(self.np_random.integers(len(self.campaigns)))
        if options is not None and "campaign_index" in options:
            index = options["campaign_index"]
            if type(index) is not int or not 0 <= index < len(self.campaigns):
                raise ValueError("Invalid campaign index")
        self.core = DesignCore(
            self.campaigns[index],
            self.registry,
            self.site_capacity,
            self.archive_capacity,
            self.on_receipt,
            self.decoder,
        )
        self.policy_decisions = 0
        return self._observation(), {"campaign_id": self.core.campaign.key}

    def action_masks(self) -> np.ndarray:
        if self.core is None:
            raise RuntimeError("Reset the environment before requesting masks")
        return np.asarray(self.core.masks(), dtype=bool)

    def step(
        self, action: int
    ) -> tuple[dict[str, np.ndarray], float, bool, bool, dict]:
        _, reward, done, info = self.core.step(int(action))
        self.policy_decisions += 1
        forced = 0
        while self.collapse_forced and not done:
            legal = np.flatnonzero(self.action_masks())
            if len(legal) != 1:
                break
            _, extra, done, info = self.core.step(int(legal[0]))
            reward += extra
            forced += 1
        info["forced_actions"] = forced
        if done:
            info["episode_receipt"] = self.receipt()
        # Budget is intrinsic to this task: no bootstrapping beyond its horizon.
        return self._observation(), reward, done, False, info

    def receipt(self) -> dict:
        return {
            **self.core.receipt(),
            "policy_decisions": self.policy_decisions,
            "collapse_forced": self.collapse_forced,
        }

    def _candidates(self) -> dict[str, np.ndarray]:
        from .candidate_encoding import encode_candidate

        c, state = self.core.campaign, self.core.construction
        if c.key not in self._candidate_cache:
            designs = tuple(c.designs())
            features = np.zeros(
                (self.candidate_capacity, self.max_length, 16), np.float32
            )
            tokens = np.zeros((self.candidate_capacity, 5), np.float32)
            present = np.zeros(self.candidate_capacity, np.float32)
            values = []
            for i, d in enumerate(designs):
                p = next(p for p in self.patterns if p.name == d.pattern)
                features[i] = encode_candidate(d, p, self.max_length)
                fields = (p.length, d.start, p.layout, p.name, d.terminal)
                values.append(fields)
                tokens[i] = [
                    self.core.grammar.tokens.index(Token(k.upper(), v))
                    for k, v in zip(TransactionalGrammar.fields, fields, strict=True)
                ]
                present[i] = 1
            self._candidate_cache[c.key] = designs, features, tokens, present, values
        designs, features, tokens, present, values = self._candidate_cache[c.key]
        completion = np.zeros(self.candidate_capacity, np.float32)
        current = tuple(getattr(state, f) for f in TransactionalGrammar.fields)
        for i, (d, fields) in enumerate(zip(designs, values, strict=True)):
            completion[i] = d.key not in self.core.session.archive and (
                state.stage == "ready"
                or state.edit_pending
                or all(
                    a is None or a == b for a, b in zip(current, fields, strict=True)
                )
            )
        return {
            "candidates": features.copy(),
            "candidate_tokens": tokens.copy(),
            "candidate_mask": present.copy(),
            "completion_mask": completion,
        }

    def _observation(self) -> dict[str, np.ndarray]:
        c, s = self.core.campaign, self.core.construction
        target = np.zeros((self.site_capacity, 7), np.float32)
        for i, base in enumerate(c.target.sequence):
            target[i, "ACGTN".index(base)] = 1
            target[i, 5] = i / max(1, len(c.target.sequence) - 1)
            target[i, 6] = any(left <= i < right for left, right in c.target.intervals)
        patterns = np.zeros((len(self.patterns), self.max_length, 9), np.float32)
        for j, p in enumerate(self.patterns):
            for i, sugar in enumerate(p.sugars):
                patterns[j, i, ("DNA", "MOE", "OMe", "cEt").index(sugar)] = 1
                patterns[j, i, 4] = p.methyl_c[i]
                patterns[j, i, 5] = i < p.length - 1 and p.links[i] == "PS"
                patterns[j, i, 6] = i < p.length - 1 and p.links[i] == "PO"
                patterns[j, i, 7] = 1
                patterns[j, i, 8] = p.wing5 <= i < p.length - p.wing3
        current = np.full(self.observation_space["construction"].shape, -1, np.float32)
        current[: len(STAGES)] = 0
        current[STAGES.index(s.stage)] = 1
        current[7] = s.length / self.max_length if s.length else -1
        current[8] = s.site / self.site_capacity if s.site is not None else -1
        current[9] = next(
            (
                i / len(self.patterns)
                for i, p in enumerate(self.patterns)
                if p.name == s.pattern
            ),
            -1,
        )
        current[10] = ("none", "PO", "PS").index(s.terminal) / 2 if s.terminal else -1
        current[11] = self.core.session.remaining / self.archive_capacity
        current[12] = (c.tokens - self.core.steps) / c.tokens
        current[13] = self.core.session.quality
        if s.layout:
            current[14:16] = np.asarray((s.layout[0], s.layout[2])) / self.max_length
        if self.decoder == "transactional-v2":
            current[16] = s.edit_pending
        history = np.zeros((self.archive_capacity, self.history_width), np.float32)
        present = np.zeros(self.archive_capacity, np.float32)
        for i, event in enumerate(self.core.session.trace):
            if event["status"] != "scored":
                continue
            d, score = event["design"], event["score"]
            pindex = next(
                j for j, p in enumerate(self.patterns) if p.name == d["pattern"]
            )
            history[i, :9] = [
                d["start"] / self.site_capacity,
                len(d["sequence"]) / self.max_length,
                pindex / len(self.patterns),
                ("none", "PO", "PS").index(d["terminal"]) / 2,
                score["eligible"],
                event["cache_hit"],
                event["quality"],
                event["gain"],
                event["initial"],
            ]
            offset = 9
            for result, head in zip(
                score["endpoints"], self.registry.heads, strict=True
            ):
                raw, u, uncertainty = (
                    result["raw"],
                    result["utility"],
                    result["uncertainty"],
                )
                history[i, offset : offset + 8] = [
                    np.arcsinh(raw) if raw is not None else 0,
                    raw is not None,
                    u if u is not None else 0,
                    u is not None,
                    np.arcsinh(uncertainty) if uncertainty is not None else 0,
                    uncertainty is not None,
                    result["status"] == "scored",
                    result["status"] == "screen_failed",
                ]
                offset += 8
                diagnostics = dict(result["diagnostics"])
                for name in head.manifest.diagnostics:
                    history[i, offset] = np.arcsinh(diagnostics.get(name, 0))
                    offset += 1
            present[i] = 1
        return {
            "target": target,
            "patterns": patterns,
            "construction": current,
            "history": history,
            "history_mask": present,
            "context": self.context_bytes.copy(),
            "action_mask": self.action_masks().astype(np.float32),
            **(self._candidates() if self.candidate_capacity is not None else {}),
        }
