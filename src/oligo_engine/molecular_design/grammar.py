"""Stage-aware Discrete vocabulary; legality never reads predictions."""

from dataclasses import dataclass, replace
from functools import lru_cache

from .contracts import Campaign, Design

STAGES = ("ready", "length", "site", "layout", "pattern", "terminal", "review")


@dataclass(frozen=True)
class Token:
    kind: str
    value: object = None


@dataclass(frozen=True)
class Construction:
    stage: str = "ready"
    length: int | None = None
    site: int | None = None
    layout: tuple[int, int, int] | None = None
    pattern: str | None = None
    terminal: str | None = None
    parent: str = ""
    edit_pending: bool = False


class Grammar:
    def __init__(
        self, campaign: Campaign, site_capacity: int, archive_capacity: int
    ) -> None:
        if site_capacity < len(campaign.target.sequence):
            raise ValueError("Site capacity cannot truncate the transcript")
        if archive_capacity < campaign.requests:
            raise ValueError("Archive capacity cannot truncate query history")
        self.campaign = campaign
        self.tokens = [Token("STOP"), Token("NEW"), Token("CANCEL"), Token("COMMIT")]
        self.tokens += [Token("PARENT", i) for i in range(archive_capacity)]
        self.tokens += [Token("EDIT", s) for s in STAGES[1:-1]]
        self.tokens += [
            Token("LENGTH", v)
            for v in sorted({p.length for p in campaign.profile.patterns})
        ]
        self.tokens += [Token("SITE", i) for i in range(site_capacity)]
        self.tokens += [
            Token("LAYOUT", v)
            for v in sorted({p.layout for p in campaign.profile.patterns})
        ]
        self.tokens += [Token("PATTERN", p.name) for p in campaign.profile.patterns]
        self.tokens += [
            Token("TERMINAL", v)
            for v in sorted({v for p in campaign.profile.patterns for v in p.terminals})
        ]

    def compatible(self, state: Construction) -> tuple:
        return tuple(
            p
            for p in self.campaign.profile.patterns
            if (state.length is None or p.length == state.length)
            and (state.layout is None or p.layout == state.layout)
        )

    def legal(self, state: Construction, parents: tuple[Design, ...]) -> list[bool]:
        patterns = self.compatible(state)
        mask = []
        for token in self.tokens:
            kind, value = token.kind, token.value
            allowed = kind == "STOP"
            if state.stage == "ready":
                allowed |= kind == "NEW" or (kind == "PARENT" and value < len(parents))
            else:
                allowed |= kind == "CANCEL"
            if state.stage == "length" and kind == "LENGTH":
                allowed = bool(self.campaign.target.sites(value))
            elif state.stage == "site" and kind == "SITE":
                allowed = value in self.campaign.target.sites(state.length)
            elif state.stage == "layout" and kind == "LAYOUT":
                allowed = any(p.layout == value for p in patterns)
            elif state.stage == "pattern" and kind == "PATTERN":
                allowed = any(p.name == value for p in patterns)
            elif state.stage == "terminal" and kind == "TERMINAL":
                allowed = any(
                    p.name == state.pattern and value in p.terminals for p in patterns
                )
            elif state.stage == "review":
                allowed |= kind in {"COMMIT", "EDIT"}
            mask.append(bool(allowed))
        return mask

    def apply(
        self, state: Construction, action: int, parents: tuple[Design, ...]
    ) -> tuple[Construction, Design | None, bool]:
        if type(action) is not int or not 0 <= action < len(self.tokens):
            raise ValueError("Action outside Discrete vocabulary")
        if not self.legal(state, parents)[action]:
            raise ValueError("Action forbidden by published mask")
        token = self.tokens[action]
        kind, value = token.kind, token.value
        if kind == "STOP":
            return state, None, True
        if kind == "NEW":
            return Construction(stage="length"), None, False
        if kind == "CANCEL":
            return Construction(), None, False
        if kind == "PARENT":
            d = parents[value]
            p = next(p for p in self.campaign.profile.patterns if p.name == d.pattern)
            return (
                Construction(
                    "review", p.length, d.start, p.layout, p.name, d.terminal, d.key
                ),
                None,
                False,
            )
        if kind == "EDIT":
            # Earlier-field edits invalidate all coupled downstream decisions.
            fields = {
                "length": None,
                "site": None,
                "layout": None,
                "pattern": None,
                "terminal": None,
            }
            order = list(fields)
            keep = order[: order.index(value)]
            fields.update({k: getattr(state, k) for k in keep})
            return Construction(stage=value, parent=state.parent, **fields), None, False
        if kind == "COMMIT":
            design = self.campaign.construct(
                state.site, state.pattern, state.terminal, state.parent
            )
            return Construction(), design, False
        field, next_stage = {
            "LENGTH": ("length", "site"),
            "SITE": ("site", "layout"),
            "LAYOUT": ("layout", "pattern"),
            "PATTERN": ("pattern", "terminal"),
            "TERMINAL": ("terminal", "review"),
        }[kind]
        return replace(state, stage=next_stage, **{field: value}), None, False


@lru_cache(maxsize=32)
def _catalog(campaign: Campaign) -> tuple[tuple[str, tuple], ...]:
    """Label-free completion metadata; shared across resets, never scores."""
    patterns = {p.name: p for p in campaign.profile.patterns}
    return tuple(
        (
            d.key,
            (
                len(d.sequence),
                d.start,
                patterns[d.pattern].layout,
                d.pattern,
                d.terminal,
            ),
        )
        for d in campaign.designs()
    )


class TransactionalGrammar(Grammar):
    """Finite complete-proposal decoder, not an open-ended draft editor.

    NEW follows the six remaining fields/commit. PARENT permits one field-edit
    decision and then forward completion. STOP is a campaign-boundary decision,
    after at least one new proposal (or exhaustion). Identity-only completion
    masks prevent replaying cached parents; no prediction enters these masks.
    """

    fields = ("length", "site", "layout", "pattern", "terminal")

    def __init__(
        self, campaign: Campaign, site_capacity: int, archive_capacity: int
    ) -> None:
        super().__init__(campaign, site_capacity, archive_capacity)
        self.catalog = _catalog(campaign)
        self.initial_keys = {
            campaign.construct(*start).key for start in campaign.starts
        }

    def legal(self, state: Construction, parents: tuple[Design, ...]) -> list[bool]:
        visited = {d.key for d in parents}
        remaining = [
            (key, values) for key, values in self.catalog if key not in visited
        ]
        mask = [False] * len(self.tokens)
        if state.stage == "ready":
            for i, t in enumerate(self.tokens):
                mask[i] = (
                    t.kind == "STOP"
                    and (bool(visited - self.initial_keys) or not remaining)
                    or t.kind == "NEW"
                    and bool(remaining)
                    or t.kind == "PARENT"
                    and t.value < len(parents)
                    and bool(remaining)
                )
            return mask
        current = tuple(getattr(state, field) for field in self.fields)
        if state.edit_pending:
            for i, t in enumerate(self.tokens):
                if t.kind == "EDIT":
                    prefix = self.fields.index(t.value)
                    mask[i] = any(
                        values[:prefix] == current[:prefix] for _, values in remaining
                    )
            return mask
        completions = [
            values
            for _, values in remaining
            if all(a is None or a == b for a, b in zip(current, values, strict=True))
        ]
        if state.stage == "review":
            mask[self.tokens.index(Token("COMMIT"))] = bool(completions)
        else:
            field = self.fields.index(state.stage)
            values = {v[field] for v in completions}
            for i, t in enumerate(self.tokens):
                mask[i] = t.kind == state.stage.upper() and t.value in values
        if not any(mask):
            raise RuntimeError("Transactional draft has no unqueried completion")
        return mask

    def apply(
        self, state: Construction, action: int, parents: tuple[Design, ...]
    ) -> tuple[Construction, Design | None, bool]:
        next_state, design, stop = super().apply(state, action, parents)
        if self.tokens[action].kind == "PARENT":
            next_state = replace(next_state, edit_pending=True)
        return next_state, design, stop
