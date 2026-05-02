from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]


@dataclass
class DatasetInfo:
    path: Path
    columns: list[str]
    row_count: int


@dataclass
class LoadedDataset:
    """Full in-memory dataset loaded from a Kaggle-style crypto CSV."""

    path: Path
    symbol: str
    df: pd.DataFrame  # sorted by date, index = RangeIndex
    date_column: str
    price_columns: list[str]

    @property
    def close_series(self) -> list[float]:
        """Return Close price as a plain Python list (oldest → newest)."""
        for col in self.price_columns:
            if col.strip().lower() == "close":
                return self.df[col].tolist()
        # fall back to first price column
        if self.price_columns:
            return self.df[self.price_columns[0]].tolist()
        return []


class DataLoader:
    """Loads CSV metadata and full data for Kaggle-style crypto datasets."""

    _DATE_CANDIDATES = {"date", "timestamp", "datetime"}
    _PRICE_CANDIDATES = {"close", "open", "high", "low", "price", "adj close"}

    # ── metadata-only (legacy) ────────────────────────────────────────────────

    def inspect_csv(self, file_path: str) -> DatasetInfo:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dosya bulunamadi: {file_path}")
        if path.suffix.lower() != ".csv":
            raise ValueError("Su anda sadece CSV dosyalari destekleniyor.")

        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            try:
                columns = next(reader)
            except StopIteration as error:
                raise ValueError("CSV dosyasi bos.") from error

            row_count = sum(1 for _ in reader)

        normalized_columns = [column.strip() for column in columns]
        return DatasetInfo(path=path, columns=normalized_columns, row_count=row_count)

    # ── full load ─────────────────────────────────────────────────────────────

    def load_csv(self, file_path: str) -> LoadedDataset:
        """Load and minimally validate a Kaggle crypto CSV.

        Expected columns (case-insensitive):
            SNo, Name, Symbol, Date, High, Low, Open, Close, Volume, Marketcap
        Any extra / missing optional columns are tolerated.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dosya bulunamadi: {file_path}")
        if path.suffix.lower() != ".csv":
            raise ValueError("Su anda sadece CSV dosyalari destekleniyor.")

        df = pd.read_csv(path, encoding="utf-8-sig")
        if df.empty:
            raise ValueError("CSV dosyasi bos.")

        # Normalise column names for detection (keep originals for data access)
        col_map: dict[str, str] = {c.strip().lower(): c.strip() for c in df.columns}
        df.columns = [c.strip() for c in df.columns]

        # ── detect date column ────────────────────────────────────────────────
        date_column: str | None = None
        for norm, orig in col_map.items():
            if norm in self._DATE_CANDIDATES:
                date_column = orig
                break

        if date_column is None:
            raise ValueError(
                "Tarih sütunu bulunamadi. "
                "Beklenen sütun adlari: Date, Timestamp, Datetime"
            )

        # ── detect price columns ──────────────────────────────────────────────
        price_columns = [
            orig for norm, orig in col_map.items() if norm in self._PRICE_CANDIDATES
        ]

        if not price_columns:
            raise ValueError(
                "Fiyat sütunu bulunamadi. "
                "Beklenen sütun adlari: Open, High, Low, Close, Price"
            )

        # ── detect symbol ─────────────────────────────────────────────────────
        symbol = "UNKNOWN"
        if "symbol" in col_map and col_map["symbol"] in df.columns:
            sym_col = col_map["symbol"]
            first_sym = df[sym_col].dropna().iloc[0] if not df[sym_col].dropna().empty else None
            if first_sym:
                symbol = str(first_sym).strip().upper()
        elif "name" in col_map and col_map["name"] in df.columns:
            name_col = col_map["name"]
            first_name = df[name_col].dropna().iloc[0] if not df[name_col].dropna().empty else None
            if first_name:
                name_str: str = str(first_name).strip().upper()
                symbol = name_str[:6]  # type: ignore[index]

        assert date_column is not None  # already raised above if None
        return LoadedDataset(
            path=path,
            symbol=symbol,
            df=df,
            date_column=date_column,
            price_columns=price_columns,
        )

    # ── bulk folder load ──────────────────────────────────────────────────────

    def load_raw_folder(self, folder: Path) -> dict[str, LoadedDataset]:
        """Scan *folder* for *.csv files and load each one.

        Returns a dict keyed by the symbol detected inside the CSV
        (e.g. ``{"BTC": LoadedDataset(...), "ETH": LoadedDataset(...)}``)
        Silently skips files that fail to parse.
        """
        results: dict[str, LoadedDataset] = {}
        if not folder.exists():
            return results
        for csv_path in sorted(folder.glob("*.csv")):
            try:
                dataset = self.load_csv(str(csv_path))
                results[dataset.symbol] = dataset
            except Exception as error:
                print(f"[DataLoader] {csv_path.name} yuklenemedi: {error}")
        return results
