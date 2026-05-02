from __future__ import annotations

from dataclasses import dataclass

import pandas as pd  # type: ignore[import-untyped]

from src.data_processing.data_loader import DatasetInfo, LoadedDataset


@dataclass
class CleanedDataset:
    columns: list[str]
    row_count: int
    date_column: str | None
    price_columns: list[str]


class DataCleaner:
    """Prepares CSV data: parses dates, sorts, fills NaN, converts types."""

    DATE_CANDIDATES = {"date", "timestamp", "datetime"}
    PRICE_CANDIDATES = {"close", "open", "high", "low", "price", "adj close"}

    # ── metadata-only plan (legacy, used by main_window for column map display) ─

    def build_cleaning_plan(self, dataset_info: DatasetInfo) -> CleanedDataset:
        normalized_columns = [column.strip().lower() for column in dataset_info.columns]

        date_column = None
        for original, normalized in zip(dataset_info.columns, normalized_columns):
            if normalized in self.DATE_CANDIDATES:
                date_column = original
                break

        price_columns = [
            original
            for original, normalized in zip(dataset_info.columns, normalized_columns)
            if normalized in self.PRICE_CANDIDATES
        ]

        return CleanedDataset(
            columns=dataset_info.columns,
            row_count=dataset_info.row_count,
            date_column=date_column,
            price_columns=price_columns,
        )

    # ── full clean ────────────────────────────────────────────────────────────

    def clean(self, loaded: LoadedDataset) -> LoadedDataset:
        """Return a new LoadedDataset with a fully cleaned DataFrame.

        Steps:
        1. Parse the date column to datetime and sort ascending.
        2. Convert price columns to numeric (coerce bad values → NaN).
        3. Forward-fill then back-fill NaN in price columns.
        4. Drop rows where all price columns are still NaN.
        5. Reset index.
        """
        df = loaded.df.copy()
        date_col = loaded.date_column

        # 1. Parse & sort by date
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col])
        df = df.sort_values(date_col).reset_index(drop=True)

        # 2. Numeric conversion for price columns
        for col in loaded.price_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # 3. Fill NaN (forward then backward to handle leading NaNs)
        df[loaded.price_columns] = (
            df[loaded.price_columns].ffill().bfill()
        )

        # 4. Drop rows where all price columns are still NaN
        df = df.dropna(subset=loaded.price_columns, how="all")
        df = df.reset_index(drop=True)

        return LoadedDataset(
            path=loaded.path,
            symbol=loaded.symbol,
            df=df,
            date_column=loaded.date_column,
            price_columns=loaded.price_columns,
        )
