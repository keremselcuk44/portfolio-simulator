"""PortfolioState — central application state with full buy/sell trading logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from src.alerts.alert_system import Alert, build_price_alert, build_stable_alert
from src.portfolio.asset import Position
from src.portfolio.trade import Trade


@dataclass
class PortfolioState:
    starting_balance: float = 1_000_000.0
    cash: float = 0.0
    positions: list[Position] = field(default_factory=list)
    trade_history: list[Trade] = field(default_factory=list)
    value_history: list[float] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    simulation_status: str = "Hazir"
    loaded_dataset: Path | None = None
    _next_id: int = field(default=1, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.cash == 0.0:
            self.cash = self.starting_balance
        if not self.value_history:
            self.value_history = [round(self.starting_balance, 2)]

    # ── factory ───────────────────────────────────────────────────────────────

    @classmethod
    def with_demo_data(cls) -> "PortfolioState":
        """
        Demo fiyatlar kaldırıldı.
        Uygulama artık gerçek CSV fiyat akışıyla çalışır.
        """
        state = cls(starting_balance=1_000_000.0, cash=1_000_000.0)
        state.simulation_status = "Boş portföy oluşturuldu"
        return state

    # ── computed properties ───────────────────────────────────────────────────

    @property
    def portfolio_value(self) -> float:
        return round(self.cash + sum(p.market_value for p in self.positions), 2)

    @property
    def invested_capital(self) -> float:
        return round(sum(p.total_cost for p in self.positions), 2)

    @property
    def total_unrealized_pnl(self) -> float:
        return round(sum(p.unrealized_pnl for p in self.positions), 2)

    @property
    def total_pnl(self) -> float:
        return round(self.portfolio_value - self.starting_balance, 2)

    @property
    def total_pnl_pct(self) -> float:
        return 0.0 if self.starting_balance == 0 else self.total_pnl / self.starting_balance

    @property
    def total_realized_pnl(self) -> float:
        return round(self.total_pnl - self.total_unrealized_pnl, 2)

    # ── trade execution ────────────────────────────────────────────────────────

    def execute_buy(self, symbol: str, quantity: float, price: float) -> Trade:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("Sembol bos birakilamaz.")
        if quantity <= 0:
            raise ValueError("Miktar sifirdan buyuk olmali.")
        if price <= 0:
            raise ValueError("Fiyat sifirdan buyuk olmali.")

        total = round(quantity * price, 2)
        if total > self.cash + 0.01:
            raise ValueError(
                f"Yetersiz bakiye.\n"
                f"Gereken  : TL {total:,.2f}\n"
                f"Mevcut   : TL {self.cash:,.2f}"
            )

        existing = self._find(symbol)
        if existing:
            new_qty = round(existing.quantity + quantity, 8)
            existing.avg_cost = round(
                (existing.total_cost + total) / new_qty, 4
            )
            existing.quantity = new_qty
            existing.current_price = price
        else:
            self.positions.append(
                Position(
                    symbol=symbol,
                    quantity=round(quantity, 8),
                    avg_cost=round(price, 4),
                    current_price=price,
                )
            )

        self.cash = round(self.cash - total, 2)
        trade = Trade.new(self._next_id, "AL", symbol, quantity, price)
        self._next_id += 1
        self.trade_history.append(trade)
        self._push_value()
        self.simulation_status = f"Alim: {quantity:.4g} {symbol} @ TL {price:,.2f}"
        return trade

    def execute_sell(self, symbol: str, quantity: float, price: float) -> Trade:
        symbol = symbol.strip().upper()
        existing = self._find(symbol)
        if not existing:
            raise ValueError(f"{symbol} icin acik pozisyon bulunamadi.")
        if quantity <= 0:
            raise ValueError("Miktar sifirdan buyuk olmali.")
        if quantity > existing.quantity + 1e-9:
            raise ValueError(
                f"Yetersiz pozisyon.\n"
                f"Satilmak istenen : {quantity:.6g}\n"
                f"Mevcut miktar    : {existing.quantity:.6g}"
            )

        total = round(quantity * price, 2)
        new_qty = round(existing.quantity - quantity, 8)
        if new_qty < 1e-8:
            self.positions.remove(existing)
        else:
            existing.quantity = new_qty

        self.cash = round(self.cash + total, 2)
        trade = Trade.new(self._next_id, "SAT", symbol, quantity, price)
        self._next_id += 1
        self.trade_history.append(trade)
        self._push_value()
        self.simulation_status = f"Satim: {quantity:.4g} {symbol} @ TL {price:,.2f}"
        return trade

    def update_prices(self, prices: dict[str, float]) -> None:
        for pos in self.positions:
            if pos.symbol in prices:
                pos.current_price = prices[pos.symbol]
        self._push_value()

    # ── misc mutations ────────────────────────────────────────────────────────

    def set_starting_balance(self, value: float) -> None:
        self.starting_balance = value

    def attach_dataset(self, file_path: str) -> None:
        self.loaded_dataset = Path(file_path)
        self.simulation_status = "Veri dosyasi secildi"

    # ── scenario simulation (used by Analysis tab) ────────────────────────────

    def run_simulation(self, start_date: date, end_date: date) -> None:
        if not self.positions:
            raise ValueError("Simulasyon icin en az bir pozisyon olmali.")
        if end_date < start_date:
            raise ValueError("Bitis tarihi baslangic tarihinden once olamaz.")

        days = max((end_date - start_date).days, 1)
        generated: list[Alert] = []
        for pos in self.positions:
            ret = self._project_return(pos.symbol, days)
            pos.current_price = round(pos.avg_cost * (1.0 + ret), 2)
            alert = build_price_alert(pos.symbol, ret)
            if alert:
                generated.append(alert)

        self.alerts = generated or [build_stable_alert()]
        self._rebuild_history()
        self.simulation_status = (
            f"Simulasyon tamamlandi ({start_date.isoformat()} → {end_date.isoformat()})"
        )

    def build_report(self, start_date: date, end_date: date) -> str:
        lines = [
            "PORTFOLIO SIMULATOR RAPORU",
            "=" * 50,
            f"Baslangic bakiyesi  : TL {self.starting_balance:>16,.2f}",
            f"Mevcut nakit        : TL {self.cash:>16,.2f}",
            f"Portfoy degeri      : TL {self.portfolio_value:>16,.2f}",
            f"Toplam K/Z          : TL {self.total_pnl:>+16,.2f}  ({self.total_pnl_pct*100:+.2f}%)",
            f"Gerceklesmis K/Z    : TL {self.total_realized_pnl:>+16,.2f}",
            f"Gerceklesmemis K/Z  : TL {self.total_unrealized_pnl:>+16,.2f}",
            f"Tarih araligi       : {start_date} → {end_date}",
            "",
            "POZISYONLAR:",
            "-" * 50,
        ]
        for p in self.positions:
            lines.append(
                f"  {p.symbol:<8} "
                f"miktar={p.quantity:<12.6g} "
                f"maliyet={p.avg_cost:>12,.2f} TL  "
                f"guncel={p.current_price:>12,.2f} TL  "
                f"P/L={p.unrealized_pnl:>+12,.2f} TL"
            )

        lines += ["", "ISLEM GECMISI (son 30):", "-" * 50]
        for t in self.trade_history[-30:]:
            lines.append(
                f"  [{t.timestamp}]  {t.side:<4}  {t.symbol:<8}  "
                f"{t.quantity:.6g} adet  @ TL {t.price:>12,.2f}  "
                f"→ TL {t.total:>12,.2f}"
            )

        if self.loaded_dataset:
            lines += ["", f"Veri dosyasi: {self.loaded_dataset}"]
        return "\n".join(lines)

    # ── internals ─────────────────────────────────────────────────────────────

    def _find(self, symbol: str) -> Position | None:
        for p in self.positions:
            if p.symbol == symbol:
                return p
        return None

    def _push_value(self) -> None:
        self.value_history.append(round(self.portfolio_value, 2))
        if len(self.value_history) > 200:
            self.value_history = self.value_history[-200:]

    def _rebuild_history(self, steps: int = 14) -> None:
        end_val   = self.portfolio_value
        start_val = self.starting_balance
        diff      = end_val - start_val
        self.value_history = [
            round(
                start_val + diff * i / max(steps - 1, 1)
                + ((i % 3) - 1) * max(abs(diff) * 0.04, 500),
                2,
            )
            for i in range(steps)
        ]

    def _project_return(self, symbol: str, days: int) -> float:
        score = sum(ord(c) for c in symbol.upper())
        base  = ((score % 19) - 7) / 100
        bonus = min(days / 3650, 0.08)
        bias  = ((len(symbol) * 3) % 5) / 100
        return round(base + bonus - bias, 4)
