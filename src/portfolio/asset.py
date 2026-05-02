"""Position dataclass — represents an open portfolio holding."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_cost: float        # weighted-average purchase price
    current_price: float   # updated by the market feed

    # ── computed ──────────────────────────────────────────────────────────────

    @property
    def market_value(self) -> float:
        return round(self.quantity * self.current_price, 2)

    @property
    def total_cost(self) -> float:
        return round(self.quantity * self.avg_cost, 2)

    @property
    def unrealized_pnl(self) -> float:
        return round(self.market_value - self.total_cost, 2)

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.total_cost == 0:
            return 0.0
        return self.unrealized_pnl / self.total_cost

