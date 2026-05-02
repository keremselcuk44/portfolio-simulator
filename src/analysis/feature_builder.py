from __future__ import annotations

from dataclasses import dataclass

import numpy as np  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]

from src.data_processing.data_loader import LoadedDataset


@dataclass
class FeatureDataset:
    """DataFrame enriched with technical indicators, plus convenience lists."""

    symbol: str
    df: pd.DataFrame          # contains original cols + MA7, MA30, daily_return, volatility_7
    close_col: str            # name of the Close column in df
    date_col: str

    @property
    def close_series(self) -> list[float]:
        return self.df[self.close_col].tolist()

    @property
    def ma7_series(self) -> list[float]:
        return self.df["MA7"].tolist()

    @property
    def ma30_series(self) -> list[float]:
        return self.df["MA30"].tolist()

    @property
    def last_close(self) -> float:
        return float(self.df[self.close_col].iloc[-1])

    @property
    def last_ma7(self) -> float:
        return float(self.df["MA7"].iloc[-1])

    @property
    def last_ma30(self) -> float:
        return float(self.df["MA30"].iloc[-1])

    @property
    def last_volatility(self) -> float:
        return float(self.df["volatility_7"].iloc[-1])


class FeatureBuilder:
    """Adds technical indicators to a cleaned LoadedDataset."""

    def build(self, loaded: LoadedDataset) -> FeatureDataset:
        """Compute MA7, MA30, daily_return, and 7-day rolling volatility."""
        df = loaded.df.copy()

        # Identify Close column (case-insensitive)
        close_col: str | None = None
        for col in loaded.price_columns:
            if col.strip().lower() == "close":
                close_col = col
                break
        if close_col is None and loaded.price_columns:
            close_col = loaded.price_columns[0]
        if close_col is None:
            raise ValueError("Fiyat sütunu bulunamadı; feature hesaplanamaz.")

        close = df[close_col].astype(float)

        df["MA7"]          = close.rolling(window=7,  min_periods=1).mean().round(4)
        df["MA30"]         = close.rolling(window=30, min_periods=1).mean().round(4)
        df["daily_return"] = close.pct_change().fillna(0.0).round(6)
        df["volatility_7"] = (
            df["daily_return"].rolling(window=7, min_periods=1).std().fillna(0.0).round(6)
        )

        return FeatureDataset(
            symbol=loaded.symbol,
            df=df,
            close_col=close_col,
            date_col=loaded.date_column,
        )
