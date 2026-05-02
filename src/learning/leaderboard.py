"""LeaderboardManager — local JSON leaderboard with session-based scoring.

Design decisions
----------------
* No login required: each app session generates a random username (User1234).
* Scores are persisted to ``leaderboard.json`` in the project root.
* Schema is flat and database-ready: adding a user_id column is trivial later.
* LeaderboardEntry is a frozen dataclass — immutable, hashable, JSON-serialisable.
* Top-10 view is sorted by total_pnl descending (can be resorted by any metric).
"""

from __future__ import annotations

import json
import random
import string
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

_LEADERBOARD_PATH = Path(__file__).parent.parent.parent / "leaderboard.json"

_ADJECTIVES = [
    "Cesur", "Akıllı", "Hızlı", "Güçlü", "Zeki",
    "Keskin", "Becerikli", "Stratejik", "Analitik", "Başarılı",
]
_NOUNS = [
    "Trader", "Yatırımcı", "Analist", "Portföy", "Uzman",
    "Büyükelçi", "Pionyer", "Stratejist", "Mühendis", "Kahraman",
]


def _generate_username() -> str:
    adj  = random.choice(_ADJECTIVES)
    noun = random.choice(_NOUNS)
    num  = random.randint(100, 9999)
    return f"{adj}{noun}{num}"


@dataclass(frozen=True)
class LeaderboardEntry:
    username:      str
    total_pnl:     float
    pnl_pct:       float   # percent relative to starting balance
    trade_count:   int
    risk_score:    float   # 0–10 (0=safe, 10=risky)
    win_rate:      float   # percent of profitable sells
    level:         str     # current learning level label
    xp:            int
    timestamp:     str     # ISO-8601

    # ------------------------------------------------------------------
    # Database migration helper — call .as_db_row() when adding a DB later
    # ------------------------------------------------------------------
    def as_db_row(self) -> dict:
        return asdict(self)


def _calc_risk_score(state: Any) -> float:
    """
    Risk score 0–10 based on portfolio concentration.
    0 = perfectly diversified; 10 = all in one asset.
    """
    pv = state.portfolio_value
    if pv <= 0 or not state.positions:
        return 0.0
    max_weight = max(p.market_value / pv for p in state.positions)
    return round(max_weight * 10, 2)


class LeaderboardManager:
    """
    Manages the local session leaderboard.

    Lifecycle
    ---------
    1. Instantiate once in MainWindow.__init__.
    2. Call ``save_session(state, lm)`` any time (e.g. when user clicks Save).
    3. Call ``get_top_10()`` to render the leaderboard table.
    """

    def __init__(self) -> None:
        self.username: str = _generate_username()
        self._entries: list[LeaderboardEntry] = self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> list[LeaderboardEntry]:
        try:
            raw = json.loads(_LEADERBOARD_PATH.read_text(encoding="utf-8"))
            return [LeaderboardEntry(**e) for e in raw.get("entries", [])]
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            return []

    def _save(self) -> None:
        data = {"entries": [asdict(e) for e in self._entries]}
        _LEADERBOARD_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Session operations ────────────────────────────────────────────────────

    def save_session(
        self,
        state: Any,
        learning_manager: Any,
        profitable_sell_count: int = 0,
    ) -> LeaderboardEntry:
        """
        Snapshot current session and persist to JSON.
        Overwrites any existing entry with the same username.
        """
        sells = [t for t in state.trade_history if t.side == "SAT"]
        win_rate = (
            round(profitable_sell_count / len(sells) * 100, 1)
            if sells else 0.0
        )
        entry = LeaderboardEntry(
            username=self.username,
            total_pnl=round(state.total_pnl, 2),
            pnl_pct=round(state.total_pnl_pct * 100, 2),
            trade_count=len(state.trade_history),
            risk_score=_calc_risk_score(state),
            win_rate=win_rate,
            level=learning_manager.current_level_label,
            xp=learning_manager.xp,
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
        self._entries = [e for e in self._entries if e.username != self.username]
        self._entries.append(entry)
        self._save()
        return entry

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_top_10(self) -> list[LeaderboardEntry]:
        return sorted(self._entries, key=lambda e: e.total_pnl, reverse=True)[:10]

    def current_rank(self) -> int | None:
        ranked = sorted(self._entries, key=lambda e: e.total_pnl, reverse=True)
        for i, e in enumerate(ranked, start=1):
            if e.username == self.username:
                return i
        return None

    def current_entry(self) -> LeaderboardEntry | None:
        return next((e for e in self._entries if e.username == self.username), None)

    @property
    def entry_count(self) -> int:
        return len(self._entries)
