"""Historical price feed driven only by CSV datasets loaded from data/raw/."""

from __future__ import annotations


class HistoricalPriceFeed:
    """
    CSV'den gelen geçmiş Close fiyatlarıyla çalışan fiyat akışı.

    Her tick() çağrıldığında veri setindeki bir sonraki satıra geçer.
    Fiyatlar random üretilmez; sadece Kaggle/CSV verisinden gelir.
    """

    def __init__(self, datasets: dict) -> None:
        self._datasets = datasets
        self._index = 0
        self._prices: dict[str, float] = {}
        self._prev: dict[str, float] = {}
        self._open: dict[str, float] = {}

        for symbol, dataset in datasets.items():
            closes = dataset.close_series
            if closes:
                clean_symbol = symbol.upper()
                self._prices[clean_symbol] = float(closes[0])

        self._prev = dict(self._prices)
        self._open = dict(self._prices)

    def tick(self) -> dict[str, float]:
        """
        CSV'deki bir sonraki satıra geçer ve güncel fiyatları döndürür.
        """
        self._prev = dict(self._prices)

        for symbol, dataset in self._datasets.items():
            closes = dataset.close_series
            if not closes:
                continue

            safe_index = min(self._index, len(closes) - 1)
            self._prices[symbol.upper()] = float(closes[safe_index])

        self._index += 1
        return dict(self._prices)

    def get_all(self) -> dict[str, float]:
        return dict(self._prices)

    def get_price(self, symbol: str) -> float:
        return self._prices.get(symbol.upper(), 0.0)

    def change_pct(self, symbol: str) -> float:
        symbol = symbol.upper()
        curr = self._prices.get(symbol, 0.0)
        prev = self._prev.get(symbol, curr)
        return 0.0 if prev == 0 else (curr - prev) / prev * 100

    def day_change_pct(self, symbol: str) -> float:
        symbol = symbol.upper()
        curr = self._prices.get(symbol, 0.0)
        opn = self._open.get(symbol, curr)
        return 0.0 if opn == 0 else (curr - opn) / opn * 100

    @property
    def symbols(self) -> list[str]:
        return list(self._prices)

    @property
    def current_index(self) -> int:
        return self._index