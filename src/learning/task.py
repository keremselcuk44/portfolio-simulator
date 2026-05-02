"""Task data model — single learning unit with validator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Task:
    """A single learning task with clear objective, hint, XP reward, and validator."""

    id: str
    title: str
    description: str        # one-sentence summary shown in task list
    objective: str          # what the user must do (full sentence)
    hint: str               # step-by-step guidance (shown on demand)
    xp: int
    icon: str
    level_id: str           # "beginner" | "intermediate" | "advanced"
    navigate_to: int        # main stack page index
    navigate_label: str
    _validator: Callable[[Any, dict], bool]

    def validate(self, state: Any, extra: dict) -> bool:
        try:
            return bool(self._validator(state, extra))
        except Exception:
            return False

    # Backwards-compatibility alias used in learn_page.py
    @property
    def level(self) -> str:
        return self.level_id
