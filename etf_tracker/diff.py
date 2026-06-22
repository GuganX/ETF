"""Compute the change between two holdings snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field

from .scraper import Holding


@dataclass
class WeightChange:
    stock_code: str
    stock_name: str
    old_weight: float
    new_weight: float

    @property
    def delta(self) -> float:
        return round(self.new_weight - self.old_weight, 4)


@dataclass
class SharesChange:
    stock_code: str
    stock_name: str
    old_shares: int
    new_shares: int

    @property
    def delta(self) -> int:
        return self.new_shares - self.old_shares


@dataclass
class HoldingsDiff:
    added: list[Holding] = field(default_factory=list)
    removed: list[Holding] = field(default_factory=list)
    weight_changes: list[WeightChange] = field(default_factory=list)
    shares_changes: list[SharesChange] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (
            self.added or self.removed or self.weight_changes or self.shares_changes
        )


def diff_snapshots(
    old: list[Holding], new: list[Holding]
) -> HoldingsDiff:
    """Diff two snapshots keyed by stock_code (old -> new)."""
    old_by_code = {h.stock_code: h for h in old}
    new_by_code = {h.stock_code: h for h in new}

    result = HoldingsDiff()

    for code, h in new_by_code.items():
        if code not in old_by_code:
            result.added.append(h)

    for code, h in old_by_code.items():
        if code not in new_by_code:
            result.removed.append(h)

    for code in old_by_code.keys() & new_by_code.keys():
        o, n = old_by_code[code], new_by_code[code]
        if o.weight_pct != n.weight_pct:
            result.weight_changes.append(
                WeightChange(code, n.stock_name, o.weight_pct, n.weight_pct)
            )
        if o.shares != n.shares:
            result.shares_changes.append(
                SharesChange(code, n.stock_name, o.shares, n.shares)
            )

    result.added.sort(key=lambda h: h.weight_pct, reverse=True)
    result.removed.sort(key=lambda h: h.weight_pct, reverse=True)
    result.weight_changes.sort(key=lambda c: abs(c.delta), reverse=True)
    result.shares_changes.sort(key=lambda c: abs(c.delta), reverse=True)
    return result
