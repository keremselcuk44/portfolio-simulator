"""Learning system package — task-based learning mode for the portfolio simulator."""

from src.learning.leaderboard import LeaderboardEntry, LeaderboardManager
from src.learning.level import Level
from src.learning.manager import (
    Achievement,
    Challenge,
    LearningExtra,
    LearningManager,
)
from src.learning.mistake_detector import MistakeDetector, MistakeWarning
from src.learning.task import Task

# Backwards-compat alias
LearningSystem = LearningManager
TaskSpec       = Task

__all__ = [
    "Achievement",
    "Challenge",
    "LeaderboardEntry",
    "LeaderboardManager",
    "LearningExtra",
    "LearningManager",
    "LearningSystem",
    "Level",
    "MistakeDetector",
    "MistakeWarning",
    "Task",
    "TaskSpec",
]
