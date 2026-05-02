"""Fully interactive, task-based Learning Mode page."""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.learning.leaderboard import LeaderboardEntry, LeaderboardManager
from src.learning.manager import Achievement, Challenge, LearningManager
from src.learning.mistake_detector import MistakeWarning
from src.learning.task import Task
from src.education.widgets import (
    PLCalculatorWidget,
    VolatilityDemoWidget,
    RiskComparisonWidget,
    DCASimulatorWidget,
    MissionPanelWidget,
    PortfolioAllocationWidget,
    TradingFlowWidget,
)

# Backwards-compat aliases — existing code below uses these names unchanged
LearningSystem = LearningManager
TaskSpec       = Task

# ── Palette (matches main app) ────────────────────────────────────────────────
_BG     = "#0b0f1a"
_SURF   = "#111827"
_SURF2  = "#1a2235"
_SURF3  = "#0f1929"
_BORDER = "#1e2d45"
_ACCENT = "#2563eb"
_GREEN  = "#10b981"
_RED    = "#ef4444"
_AMBER  = "#f59e0b"
_PURPLE = "#8b5cf6"
_CYAN   = "#06b6d4"
_TEXT   = "#e2e8f0"
_TEXT2  = "#94a3b8"
_TEXT3  = "#64748b"


# ── Tiny helpers ──────────────────────────────────────────────────────────────

def _lbl(text: str = "", *, bold: bool = False, size: int = 0,
         color: str = "", wrap: bool = False) -> QLabel:
    w = QLabel(text)
    f = QFont()
    if bold:
        f.setBold(True)
    if size:
        f.setPointSize(size)
    w.setFont(f)
    if color:
        w.setStyleSheet(f"color:{color};")
    if wrap:
        w.setWordWrap(True)
    return w


def _sep(vertical: bool = False) -> QFrame:
    s = QFrame()
    s.setFrameShape(QFrame.Shape.VLine if vertical else QFrame.Shape.HLine)
    s.setStyleSheet(f"color:{_BORDER}; background:{_BORDER};")
    if vertical:
        s.setMaximumWidth(1)
    else:
        s.setMaximumHeight(1)
    return s


# ── XP Progress Bar ───────────────────────────────────────────────────────────

class _XPBar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._ratio = 0.0

    def set_ratio(self, r: float) -> None:
        self._ratio = max(0.0, min(1.0, r))
        self.update()

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # background
        p.setBrush(QColor(_SURF2))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, h // 2, h // 2)
        # fill
        bw = int(w * self._ratio)
        if bw > 4:
            grad = QLinearGradient(0, 0, w, 0)
            grad.setColorAt(0.0, QColor(_ACCENT))
            grad.setColorAt(1.0, QColor(_GREEN))
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(0, 0, bw, h, h // 2, h // 2)
        p.end()


# ── XP Header Bar ─────────────────────────────────────────────────────────────

class XPHeaderBar(QFrame):
    def __init__(self, ls: LearningSystem) -> None:
        super().__init__()
        self._ls = ls
        self.setObjectName("xpHeader")
        self.setFixedHeight(64)
        self._build()

    def _build(self) -> None:
        hl = QHBoxLayout(self)
        hl.setContentsMargins(20, 0, 20, 0)
        hl.setSpacing(16)

        self._level_badge = QLabel()
        self._level_badge.setObjectName("levelBadge")
        self._level_badge.setFixedHeight(36)
        self._level_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(self._level_badge)

        bar_col = QVBoxLayout()
        bar_col.setSpacing(4)
        self._bar_label = _lbl("", color=_TEXT3)
        self._bar_label.setStyleSheet("color:#64748b; font-size:10px; font-weight:700; letter-spacing:0.5px;")
        self._xp_bar = _XPBar()
        self._xp_bar.setFixedHeight(10)
        bar_col.addWidget(self._bar_label)
        bar_col.addWidget(self._xp_bar)
        hl.addLayout(bar_col, 1)

        self._xp_label = QLabel()
        self._xp_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hl.addWidget(self._xp_label)

    def refresh(self) -> None:
        ls   = self._ls
        icon = ls.current_level_icon
        name = ls.current_level_label
        curr_xp, level_xp = ls.level_progress()
        total_xp = ls.xp

        self._level_badge.setText(f"  {icon}  {name}  ")
        self._level_badge.setStyleSheet(
            f"background:{_ACCENT}22; border:1px solid {_ACCENT}55; border-radius:8px; "
            f"color:{_ACCENT}; font-size:12px; font-weight:800; padding:0 8px;"
        )
        ratio = curr_xp / level_xp if level_xp > 0 else 1.0
        self._xp_bar.set_ratio(ratio)
        self._bar_label.setText(
            f"SEVİYE İLERLEMESİ  —  {curr_xp} / {level_xp} XP"
        )
        self._xp_label.setText(f"⚡ {total_xp} XP")
        self._xp_label.setStyleSheet(
            f"color:{_AMBER}; font-size:14px; font-weight:800;"
        )


# ── Task Widget ───────────────────────────────────────────────────────────────

class TaskWidget(QFrame):
    """Interactive card for a single learning task."""

    def __init__(
        self,
        task: TaskSpec,
        navigate_cb: Callable[[int], None],
        validate_cb: Callable[[str], None],
    ) -> None:
        super().__init__()
        self._task       = task
        self._nav_cb     = navigate_cb
        self._validate_cb = validate_cb
        self._hint_open  = False
        self._status     = "locked"   # "locked" | "active" | "completed"
        self._build()

    def _build(self) -> None:
        self.setObjectName("taskCard")
        vl = QVBoxLayout(self)
        vl.setContentsMargins(18, 14, 18, 14)
        vl.setSpacing(10)

        # ── Top row: icon + title + badges ────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(14)

        self._icon_lbl = QLabel(self._task.icon)
        self._icon_lbl.setFixedSize(46, 46)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setStyleSheet(
            f"font-size:24px; background:{_SURF2}; border:1px solid {_BORDER}; border-radius:10px;"
        )
        top.addWidget(self._icon_lbl)

        mid = QVBoxLayout()
        mid.setSpacing(3)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self._title_lbl = QLabel(self._task.title)
        self._title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:14px; font-weight:800;")
        title_row.addWidget(self._title_lbl)
        title_row.addStretch()

        self._xp_badge = QLabel(f"+{self._task.xp} XP")
        self._xp_badge.setStyleSheet(
            f"color:{_AMBER}; background:#1c1200; border:1px solid #44330a; "
            f"border-radius:5px; font-size:11px; font-weight:700; padding:1px 7px;"
        )
        title_row.addWidget(self._xp_badge)

        self._status_badge = QLabel()
        title_row.addWidget(self._status_badge)
        mid.addLayout(title_row)

        self._obj_lbl = QLabel(self._task.objective)
        self._obj_lbl.setStyleSheet(f"color:{_TEXT2}; font-size:12px;")
        self._obj_lbl.setWordWrap(True)
        mid.addWidget(self._obj_lbl)

        top.addLayout(mid, 1)
        vl.addLayout(top)

        # ── Hint section (collapsible) ────────────────────────────────────
        self._hint_frame = QFrame()
        self._hint_frame.setStyleSheet(
            f"background:{_SURF3}; border:1px solid {_BORDER}; border-radius:7px;"
        )
        hint_vl = QVBoxLayout(self._hint_frame)
        hint_vl.setContentsMargins(14, 10, 14, 10)
        hint_lbl = QLabel(f"💡  {self._task.hint}")
        hint_lbl.setStyleSheet(f"color:{_TEXT2}; font-size:12px;")
        hint_lbl.setWordWrap(True)
        hint_vl.addWidget(hint_lbl)
        self._hint_frame.setVisible(False)
        vl.addWidget(self._hint_frame)

        # ── Lock overlay label ────────────────────────────────────────────
        self._lock_row = QHBoxLayout()
        self._lock_lbl = QLabel("🔒  Bu görev önceki görevi tamamladıktan sonra açılır.")
        self._lock_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:11px;")
        self._lock_row.addWidget(self._lock_lbl)
        self._lock_row.addStretch()
        vl.addLayout(self._lock_row)

        # ── Action row ────────────────────────────────────────────────────
        self._action_row = QHBoxLayout()
        self._action_row.setSpacing(8)

        self._hint_btn = QPushButton("💡 İpucu")
        self._hint_btn.setFixedHeight(32)
        self._hint_btn.setStyleSheet(
            f"background:{_SURF2}; color:{_AMBER}; border:1px solid #44330a; "
            f"border-radius:6px; font-size:11px; font-weight:600; padding:0 12px;"
        )
        self._hint_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hint_btn.clicked.connect(self._toggle_hint)
        self._action_row.addWidget(self._hint_btn)
        self._action_row.addStretch()

        self._nav_btn = QPushButton(self._task.navigate_label)
        self._nav_btn.setFixedHeight(32)
        self._nav_btn.setStyleSheet(
            f"background:{_SURF2}; color:{_TEXT2}; border:1px solid {_BORDER}; "
            f"border-radius:6px; font-size:11px; font-weight:600; padding:0 14px;"
        )
        self._nav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._nav_btn.clicked.connect(lambda: self._nav_cb(self._task.navigate_to))
        self._action_row.addWidget(self._nav_btn)

        self._validate_btn = QPushButton("✓ Doğrula")
        self._validate_btn.setFixedHeight(32)
        self._validate_btn.setStyleSheet(
            f"background:{_ACCENT}; color:white; border:none; "
            f"border-radius:6px; font-size:11px; font-weight:700; padding:0 16px;"
        )
        self._validate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._validate_btn.clicked.connect(lambda: self._validate_cb(self._task.id))
        self._action_row.addWidget(self._validate_btn)

        vl.addLayout(self._action_row)

    def _toggle_hint(self) -> None:
        self._hint_open = not self._hint_open
        self._hint_frame.setVisible(self._hint_open)
        self._hint_btn.setText("💡 İpucunu Gizle" if self._hint_open else "💡 İpucu")

    def set_status(self, status: str) -> None:
        """Update visual state: 'locked' | 'active' | 'completed'."""
        self._status = status
        locked    = status == "locked"
        completed = status == "completed"
        active    = status == "active"

        # Card border/background
        if completed:
            self.setStyleSheet(
                "QFrame#taskCard {"
                f"background:#061f12; border:1px solid #065f46; border-radius:10px;"
                "}"
            )
        elif active:
            self.setStyleSheet(
                "QFrame#taskCard {"
                f"background:{_SURF}; border:2px solid {_ACCENT}; border-radius:10px;"
                "}"
            )
        else:
            self.setStyleSheet(
                "QFrame#taskCard {"
                f"background:{_SURF}; border:1px solid {_BORDER}; border-radius:10px;"
                "opacity: 0.5;"
                "}"
            )

        # Icon opacity
        alpha = "55" if locked else ("ff" if active else "cc")
        self._icon_lbl.setStyleSheet(
            f"font-size:24px; background:{_SURF2}{alpha}; border:1px solid {_BORDER}; border-radius:10px;"
        )

        # Title
        title_col = _TEXT3 if locked else (_TEXT if active else "#64748b")
        self._title_lbl.setStyleSheet(f"color:{title_col}; font-size:14px; font-weight:800;")

        # Objective
        obj_col = _TEXT3 if locked else (_TEXT2 if active else _TEXT3)
        self._obj_lbl.setStyleSheet(f"color:{obj_col}; font-size:12px;")

        # Status badge
        if completed:
            self._status_badge.setText("✓ Tamamlandı")
            self._status_badge.setStyleSheet(
                f"color:{_GREEN}; background:#061f12; border:1px solid #065f46; "
                f"border-radius:5px; font-size:10px; font-weight:700; padding:1px 7px;"
            )
        elif active:
            self._status_badge.setText("● AKTİF")
            self._status_badge.setStyleSheet(
                f"color:{_ACCENT}; background:{_ACCENT}11; border:1px solid {_ACCENT}44; "
                f"border-radius:5px; font-size:10px; font-weight:700; padding:1px 7px;"
            )
        else:
            self._status_badge.setText("🔒 KİLİTLİ")
            self._status_badge.setStyleSheet(
                f"color:{_TEXT3}; background:{_SURF2}; border:1px solid {_BORDER}; "
                f"border-radius:5px; font-size:10px; font-weight:700; padding:1px 7px;"
            )

        # Show/hide action elements
        self._lock_lbl.setVisible(locked)
        for w in (self._hint_btn, self._nav_btn, self._validate_btn):
            w.setVisible(not locked and not completed)

        if completed and self._hint_open:
            self._hint_frame.setVisible(False)
            self._hint_open = False

    def flash_success(self) -> None:
        """Brief green flash on completion."""
        self.setStyleSheet(
            "QFrame#taskCard {"
            f"background:#0a3020; border:2px solid {_GREEN}; border-radius:10px;"
            "}"
        )
        QTimer.singleShot(800, lambda: self.set_status("completed"))


# ── Level Page ────────────────────────────────────────────────────────────────

class LevelPage(QScrollArea):
    def __init__(
        self,
        level: str,
        ls: LearningSystem,
        navigate_cb: Callable[[int], None],
        validate_cb: Callable[[str], None],
    ) -> None:
        super().__init__()
        self._level = level
        self._ls    = ls
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._inner = QWidget()
        self._vl    = QVBoxLayout(self._inner)
        self._vl.setContentsMargins(24, 20, 24, 20)
        self._vl.setSpacing(12)
        self.setWidget(self._inner)

        self._task_widgets: dict[str, TaskWidget] = {}

        meta = ls.LEVEL_META[level]
        tasks = ls.tasks_for_level(level)

        # ── Level header ──────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        icon_lbl = QLabel(meta[0])
        icon_lbl.setStyleSheet("font-size:28px;")
        hdr.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel(meta[1])
        title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:20px; font-weight:800;")
        self._prog_lbl = QLabel()
        self._prog_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:12px;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(self._prog_lbl)
        hdr.addLayout(title_col)
        hdr.addStretch()

        self._level_xp_lbl = QLabel()
        self._level_xp_lbl.setStyleSheet(f"color:{_AMBER}; font-size:13px; font-weight:700;")
        hdr.addWidget(self._level_xp_lbl)

        self._vl.addLayout(hdr)

        # Level mini progress bar
        self._prog_bar = _XPBar()
        self._prog_bar.setFixedHeight(6)
        self._vl.addWidget(self._prog_bar)
        self._vl.addSpacing(8)

        # ── Locked level overlay ──────────────────────────────────────────
        self._locked_overlay = QFrame()
        self._locked_overlay.setStyleSheet(
            f"background:{_SURF2}; border:1px solid {_BORDER}; border-radius:10px;"
        )
        lo_vl = QVBoxLayout(self._locked_overlay)
        lo_vl.setContentsMargins(24, 20, 24, 20)
        lo_vl.setSpacing(8)
        lock_icon = QLabel("🔒")
        lock_icon.setStyleSheet("font-size:32px;")
        lock_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lock_title = QLabel(f"{meta[1]} seviyesi kilitli")
        lock_title.setStyleSheet(f"color:{_TEXT}; font-size:15px; font-weight:700;")
        lock_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prev_idx = ls.LEVEL_ORDER.index(level)
        prev_level_name = ls.LEVEL_META[ls.LEVEL_ORDER[prev_idx - 1]][1] if prev_idx > 0 else ""
        lock_desc = QLabel(
            f"Bu seviyeyi açmak için '{prev_level_name}' seviyesindeki "
            f"tüm görevleri tamamla ve yeterli XP kazan."
        )
        lock_desc.setStyleSheet(f"color:{_TEXT2}; font-size:12px;")
        lock_desc.setWordWrap(True)
        lock_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lo_vl.addWidget(lock_icon)
        lo_vl.addWidget(lock_title)
        lo_vl.addWidget(lock_desc)
        self._vl.addWidget(self._locked_overlay)

        # ── Task cards ────────────────────────────────────────────────────
        for task in tasks:
            w = TaskWidget(task, navigate_cb, validate_cb)
            self._task_widgets[task.id] = w
            self._vl.addWidget(w)

        self._vl.addStretch()

    def refresh(self) -> None:
        ls    = self._ls
        level = self._level
        tasks = ls.tasks_for_level(level)
        n_done  = ls.completed_count(level)
        n_total = ls.total_tasks(level)
        level_unlocked = ls.is_level_unlocked(level)

        # level XP
        level_xp = sum(t.xp for t in tasks if ls.is_task_complete(t.id))
        total_xp = sum(t.xp for t in tasks)
        self._level_xp_lbl.setText(f"⚡ {level_xp} / {total_xp} XP")
        self._prog_lbl.setText(f"{n_done} / {n_total} görev tamamlandı")
        self._prog_bar.set_ratio(n_done / n_total if n_total > 0 else 0.0)

        self._locked_overlay.setVisible(not level_unlocked)
        for task in tasks:
            w = self._task_widgets.get(task.id)
            if not w:
                continue
            w.setVisible(level_unlocked)
            if not level_unlocked:
                continue
            if ls.is_task_complete(task.id):
                w.set_status("completed")
            elif ls.is_task_locked(task):
                w.set_status("locked")
            else:
                w.set_status("active")


# ── Achievement Card ──────────────────────────────────────────────────────────

class AchievementCard(QFrame):
    def __init__(self, ach: Achievement) -> None:
        super().__init__()
        self._ach = ach
        self.setFixedSize(145, 145)
        self._build()

    def _build(self) -> None:
        vl = QVBoxLayout(self)
        vl.setContentsMargins(12, 14, 12, 14)
        vl.setSpacing(6)
        vl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_lbl = QLabel(self._ach.icon)
        self._icon_lbl.setFixedSize(52, 52)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setStyleSheet("font-size:28px;")
        vl.addWidget(self._icon_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        self._title_lbl = QLabel(self._ach.title)
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_lbl.setWordWrap(True)
        self._title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:11px; font-weight:700;")
        vl.addWidget(self._title_lbl)

        self._xp_lbl = QLabel(f"+{self._ach.xp} XP")
        self._xp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._xp_lbl.setStyleSheet(f"color:{_AMBER}; font-size:10px; font-weight:700;")
        vl.addWidget(self._xp_lbl)

        self.refresh()

    def refresh(self) -> None:
        if self._ach.unlocked:
            self.setStyleSheet(
                f"QFrame {{background:{_SURF}; border:2px solid {_GREEN}; border-radius:10px;}}"
            )
            self._icon_lbl.setStyleSheet("font-size:28px; opacity: 1;")
            self._title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:11px; font-weight:700;")
            self._xp_lbl.setStyleSheet(f"color:{_GREEN}; font-size:10px; font-weight:700;")
        else:
            self.setStyleSheet(
                f"QFrame {{background:{_SURF2}; border:1px solid {_BORDER}; border-radius:10px;}}"
            )
            self._icon_lbl.setStyleSheet("font-size:28px; color: rgba(100,100,100,0.3);")
            self._title_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:11px; font-weight:700;")
            self._xp_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:10px; font-weight:600;")
            self._icon_lbl.setText("🔒")


# ── Achievements Page ─────────────────────────────────────────────────────────

class AchievementsPage(QScrollArea):
    def __init__(self, ls: LearningSystem) -> None:
        super().__init__()
        self._ls = ls
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._inner = QWidget()
        vl = QVBoxLayout(self._inner)
        vl.setContentsMargins(24, 20, 24, 20)
        vl.setSpacing(16)
        self.setWidget(self._inner)

        # Header
        hdr = QHBoxLayout()
        icon_lbl = QLabel("🏆")
        icon_lbl.setStyleSheet("font-size:28px;")
        hdr.addWidget(icon_lbl)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("Başarımlar")
        title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:20px; font-weight:800;")
        self._count_lbl = QLabel()
        self._count_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:12px;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(self._count_lbl)
        hdr.addLayout(title_col)
        hdr.addStretch()
        vl.addLayout(hdr)

        vl.addWidget(_sep())
        vl.addSpacing(4)

        # Grid of achievement cards
        self._grid = QGridLayout()
        self._grid.setSpacing(10)
        self._ach_cards: dict[str, AchievementCard] = {}
        for i, ach in enumerate(ls.achievements):
            card = AchievementCard(ach)
            self._ach_cards[ach.id] = card
            self._grid.addWidget(card, i // 4, i % 4)
        vl.addLayout(self._grid)
        vl.addSpacing(8)

        # Description area
        desc_frm = QFrame()
        desc_frm.setStyleSheet(
            f"background:{_SURF}; border:1px solid {_BORDER}; border-radius:8px;"
        )
        desc_vl = QVBoxLayout(desc_frm)
        desc_vl.setContentsMargins(16, 12, 16, 12)
        desc_vl.setSpacing(6)
        desc_title = QLabel("📋  Tüm Başarımlar")
        desc_title.setStyleSheet(f"color:{_TEXT3}; font-size:10px; font-weight:700; letter-spacing:1px;")
        desc_vl.addWidget(desc_title)
        for ach in ls.achievements:
            row = QHBoxLayout()
            row.setSpacing(8)
            icon = QLabel(ach.icon)
            icon.setFixedWidth(24)
            row.addWidget(icon)
            title_lbl = QLabel(f"<b>{ach.title}</b>")
            title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:12px;")
            row.addWidget(title_lbl)
            row.addWidget(QLabel("—"))
            desc_lbl = QLabel(ach.desc)
            desc_lbl.setStyleSheet(f"color:{_TEXT2}; font-size:11px;")
            row.addWidget(desc_lbl, 1)
            xp_lbl = QLabel(f"+{ach.xp} XP")
            xp_lbl.setStyleSheet(f"color:{_AMBER}; font-size:11px; font-weight:700;")
            row.addWidget(xp_lbl)
            desc_vl.addLayout(row)
        vl.addWidget(desc_frm)
        vl.addStretch()

    def refresh(self) -> None:
        unlocked = sum(1 for a in self._ls.achievements if a.unlocked)
        total    = len(self._ls.achievements)
        self._count_lbl.setText(f"{unlocked} / {total} kazanıldı")
        for ach in self._ls.achievements:
            card = self._ach_cards.get(ach.id)
            if card:
                card._ach = ach
                card.refresh()


# ── Challenge Card ────────────────────────────────────────────────────────────

class ChallengeCard(QFrame):
    def __init__(self, ch: Challenge) -> None:
        super().__init__()
        self._ch = ch
        self.setObjectName("challengeCard")
        self._build()

    def _build(self) -> None:
        hl = QHBoxLayout(self)
        hl.setContentsMargins(16, 14, 16, 14)
        hl.setSpacing(14)

        self._icon_lbl = QLabel(self._ch.icon)
        self._icon_lbl.setFixedSize(48, 48)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setStyleSheet(
            f"font-size:26px; background:{_SURF2}; border:1px solid {_BORDER}; border-radius:10px;"
        )
        hl.addWidget(self._icon_lbl)

        mid = QVBoxLayout()
        mid.setSpacing(4)
        self._title_lbl = QLabel(self._ch.title)
        self._title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:14px; font-weight:800;")
        self._desc_lbl = QLabel(self._ch.desc)
        self._desc_lbl.setStyleSheet(f"color:{_TEXT2}; font-size:12px;")
        self._desc_lbl.setWordWrap(True)
        req_row = QHBoxLayout()
        req_row.setSpacing(6)
        req_icon = QLabel("📋")
        req_icon.setStyleSheet("font-size:12px;")
        self._req_lbl = QLabel(self._ch.requirement)
        self._req_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:11px;")
        req_row.addWidget(req_icon)
        req_row.addWidget(self._req_lbl)
        req_row.addStretch()
        mid.addWidget(self._title_lbl)
        mid.addWidget(self._desc_lbl)
        mid.addLayout(req_row)
        hl.addLayout(mid, 1)

        right = QVBoxLayout()
        right.setSpacing(6)
        right.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._xp_lbl = QLabel(f"+{self._ch.xp} XP")
        self._xp_lbl.setStyleSheet(f"color:{_AMBER}; font-size:13px; font-weight:800;")
        self._xp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl = QLabel()
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self._xp_lbl)
        right.addWidget(self._status_lbl)
        hl.addLayout(right)

        self.refresh()

    def refresh(self) -> None:
        if self._ch.completed:
            self.setStyleSheet(
                f"QFrame#challengeCard {{background:#061f12; border:1px solid #065f46; border-radius:10px;}}"
            )
            self._status_lbl.setText("✓ Tamamlandı")
            self._status_lbl.setStyleSheet(
                f"color:{_GREEN}; font-size:11px; font-weight:700; "
                f"background:#061f12; border:1px solid #065f46; border-radius:5px; padding:2px 8px;"
            )
        else:
            self.setStyleSheet(
                f"QFrame#challengeCard {{background:{_SURF}; border:1px solid {_BORDER}; border-radius:10px;}}"
            )
            self._status_lbl.setText("⏳ Devam ediyor")
            self._status_lbl.setStyleSheet(
                f"color:{_TEXT3}; font-size:11px; font-weight:600; "
                f"background:{_SURF2}; border:1px solid {_BORDER}; border-radius:5px; padding:2px 8px;"
            )


# ── Challenges Page ───────────────────────────────────────────────────────────

class ChallengesPage(QScrollArea):
    def __init__(self, ls: LearningSystem) -> None:
        super().__init__()
        self._ls = ls
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._inner = QWidget()
        vl = QVBoxLayout(self._inner)
        vl.setContentsMargins(24, 20, 24, 20)
        vl.setSpacing(12)
        self.setWidget(self._inner)

        # Header
        hdr = QHBoxLayout()
        icon_lbl = QLabel("⚡")
        icon_lbl.setStyleSheet("font-size:28px;")
        hdr.addWidget(icon_lbl)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("Zorluklar")
        title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:20px; font-weight:800;")
        self._count_lbl = QLabel()
        self._count_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:12px;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(self._count_lbl)
        hdr.addLayout(title_col)
        hdr.addStretch()
        vl.addLayout(hdr)

        desc_lbl = QLabel(
            "Zorluklar sizi gerçek kararlar almaya zorlar. "
            "Her zorluk tamamlandığında büyük XP ödülü kazanırsınız."
        )
        desc_lbl.setStyleSheet(f"color:{_TEXT2}; font-size:12px;")
        desc_lbl.setWordWrap(True)
        vl.addWidget(desc_lbl)
        vl.addWidget(_sep())
        vl.addSpacing(4)

        self._ch_cards: dict[str, ChallengeCard] = {}
        for ch in ls.challenges:
            card = ChallengeCard(ch)
            self._ch_cards[ch.id] = card
            vl.addWidget(card)
        vl.addStretch()

    def refresh(self) -> None:
        done  = sum(1 for c in self._ls.challenges if c.completed)
        total = len(self._ls.challenges)
        self._count_lbl.setText(f"{done} / {total} tamamlandı")
        for ch in self._ls.challenges:
            card = self._ch_cards.get(ch.id)
            if card:
                card._ch = ch
                card.refresh()


# ── Analytics Page ────────────────────────────────────────────────────────────

class AnalyticsPage(QScrollArea):
    def __init__(self, ls: LearningSystem) -> None:
        super().__init__()
        self._ls = ls
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._inner = QWidget()
        self._vl    = QVBoxLayout(self._inner)
        self._vl.setContentsMargins(24, 20, 24, 20)
        self._vl.setSpacing(12)
        self.setWidget(self._inner)

        # Header
        hdr = QHBoxLayout()
        icon_lbl = QLabel("📊")
        icon_lbl.setStyleSheet("font-size:28px;")
        hdr.addWidget(icon_lbl)
        title_lbl = QLabel("Performans Analitiği")
        title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:20px; font-weight:800;")
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        self._vl.addLayout(hdr)
        self._vl.addWidget(_sep())
        self._vl.addSpacing(4)

        # Stats grid (2 rows × 4 cols)
        self._stat_labels: dict[str, QLabel] = {}
        stats = [
            ("total_trades",   "TOPLAM İŞLEM",      _TEXT,   "—"),
            ("buy_count",      "TOPLAM ALIM",        _GREEN,  "—"),
            ("sell_count",     "TOPLAM SATIM",       _RED,    "—"),
            ("total_volume",   "TOPLAM HACİM",       _CYAN,   "—"),
            ("total_pnl",      "TOPLAM K/Z",         _GREEN,  "—"),
            ("realized_pnl",   "GERÇEKLEŞMİŞ K/Z",  _GREEN,  "—"),
            ("unrealized_pnl", "GERÇEKLEŞMEMİŞ K/Z",_AMBER,  "—"),
            ("risk_level",     "RİSK SEVİYESİ",      _AMBER,  "—"),
        ]
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (key, title, color, default) in enumerate(stats):
            box = QFrame()
            box.setStyleSheet(
                f"QFrame {{background:{_SURF}; border:1px solid {_BORDER}; border-radius:8px;}}"
            )
            bvl = QVBoxLayout(box)
            bvl.setContentsMargins(14, 10, 14, 10)
            bvl.setSpacing(4)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:9px; font-weight:700; letter-spacing:1px;")
            v_lbl = QLabel(default)
            v_lbl.setStyleSheet(f"color:{color}; font-size:18px; font-weight:700; font-family:Consolas;")
            bvl.addWidget(t_lbl)
            bvl.addWidget(v_lbl)
            self._stat_labels[key] = v_lbl
            grid.addWidget(box, i // 4, i % 4)
        self._vl.addLayout(grid)
        self._vl.addSpacing(12)

        # Best / Worst trade
        trade_row = QHBoxLayout()
        trade_row.setSpacing(10)
        for attr, label, color in (("_best_box", "EN İYİ SATIŞ", _GREEN), ("_worst_box", "EN KÖTÜ SATIŞ", _RED)):
            frm = QFrame()
            frm.setStyleSheet(f"QFrame {{background:{_SURF}; border:1px solid {_BORDER}; border-radius:8px;}}")
            fvl = QVBoxLayout(frm)
            fvl.setContentsMargins(16, 12, 16, 12)
            fvl.setSpacing(4)
            title_lbl = QLabel(label)
            title_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:9px; font-weight:700; letter-spacing:1px;")
            val_lbl = QLabel("Henüz satış yok")
            val_lbl.setStyleSheet(f"color:{color}; font-size:14px; font-weight:700;")
            fvl.addWidget(title_lbl)
            fvl.addWidget(val_lbl)
            setattr(self, attr, val_lbl)
            trade_row.addWidget(frm, 1)
        self._vl.addLayout(trade_row)

        # Tip
        tip_frm = QFrame()
        tip_frm.setStyleSheet(
            f"background:{_SURF2}; border:1px solid {_BORDER}; border-radius:8px;"
        )
        tip_vl = QVBoxLayout(tip_frm)
        tip_vl.setContentsMargins(16, 12, 16, 12)
        tip_lbl = QLabel(
            "💡  <b>İpucu:</b> Gerçekleşmiş K/Z, kapattığınız pozisyonlardan elde ettiğiniz net kâr/zarardır. "
            "Gerçekleşmemiş K/Z ise hâlâ açık olan pozisyonlarınızın anlık değeridir — satmadan gerçek olmaz."
        )
        tip_lbl.setStyleSheet(f"color:{_TEXT2}; font-size:12px;")
        tip_lbl.setWordWrap(True)
        tip_vl.addWidget(tip_lbl)
        self._vl.addWidget(tip_frm)
        self._vl.addStretch()

    def refresh(self, state: object) -> None:
        data = self._ls.get_analytics(state)
        if not data:
            for lbl in self._stat_labels.values():
                lbl.setText("—")
            self._best_box.setText("Henüz satış yok")
            self._worst_box.setText("Henüz satış yok")
            return

        pnl_color = _GREEN if data["total_pnl"] >= 0 else _RED
        rpl_color = _GREEN if data["realized_pnl"] >= 0 else _RED
        upl_color = _GREEN if data["unrealized_pnl"] >= 0 else _RED

        updates = {
            "total_trades":   str(data["total_trades"]),
            "buy_count":      str(data["buy_count"]),
            "sell_count":     str(data["sell_count"]),
            "total_volume":   f"TL {data['total_volume']:,.0f}",
            "total_pnl":      f"{data['total_pnl']:+,.0f} TL",
            "realized_pnl":   f"{data['realized_pnl']:+,.0f} TL",
            "unrealized_pnl": f"{data['unrealized_pnl']:+,.0f} TL",
            "risk_level":     data["risk_level"],
        }
        color_map = {
            "total_pnl":      pnl_color,
            "realized_pnl":   rpl_color,
            "unrealized_pnl": upl_color,
        }
        for key, val in updates.items():
            lbl = self._stat_labels.get(key)
            if lbl:
                lbl.setText(val)
                if key in color_map:
                    lbl.setStyleSheet(
                        f"color:{color_map[key]}; font-size:18px; font-weight:700; font-family:Consolas;"
                    )

        if data["best_trade"]:
            bt = data["best_trade"]
            self._best_box.setText(f"{bt.symbol}  @ TL {bt.price:,.2f}  →  TL {bt.total:,.0f}")
        if data["worst_trade"]:
            wt = data["worst_trade"]
            self._worst_box.setText(f"{wt.symbol}  @ TL {wt.price:,.2f}  →  TL {wt.total:,.0f}")


# ── Leaderboard Page ──────────────────────────────────────────────────────────

class LeaderboardPage(QScrollArea):
    """Local JSON-backed session leaderboard, top-10 sorted by P/L."""

    _HEADERS = ["#", "Kullanıcı", "K/Z (TL)", "K/Z %", "İşlemler", "Kazanma %", "Risk", "Seviye", "XP"]
    _WIDTHS   = [28,   150,         100,         70,       80,          80,          60,     80,       60]

    def __init__(self, lb: LeaderboardManager, save_cb: "Callable[[], None] | None" = None) -> None:
        super().__init__()
        self._lb      = lb
        self._save_cb = save_cb
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._inner = QWidget()
        self._vl    = QVBoxLayout(self._inner)
        self._vl.setContentsMargins(24, 20, 24, 20)
        self._vl.setSpacing(16)
        self.setWidget(self._inner)

        self._build_header()
        self._build_my_card()
        self._build_table_section()
        self._vl.addStretch()

    def _build_header(self) -> None:
        hdr = QHBoxLayout()
        icon_lbl = QLabel("🏅")
        icon_lbl.setStyleSheet("font-size:28px;")
        hdr.addWidget(icon_lbl)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("Liderlik Tablosu")
        title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:20px; font-weight:800;")
        self._sub_lbl = QLabel()
        self._sub_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:12px;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(self._sub_lbl)
        hdr.addLayout(title_col)
        hdr.addStretch()

        self._save_btn = QPushButton("💾  Skoru Kaydet")
        self._save_btn.setFixedHeight(36)
        self._save_btn.setStyleSheet(
            f"background:{_ACCENT}; color:white; border:none; "
            f"border-radius:7px; font-size:12px; font-weight:700; padding:0 16px;"
        )
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if self._save_cb:
            self._save_btn.clicked.connect(self._save_cb)
        hdr.addWidget(self._save_btn)
        self._vl.addLayout(hdr)
        self._vl.addWidget(_sep())

    def _build_my_card(self) -> None:
        self._my_card = QFrame()
        self._my_card.setObjectName("myCard")
        self._my_card.setStyleSheet(
            f"QFrame#myCard {{background:{_ACCENT}0d; border:1px solid {_ACCENT}44; border-radius:10px;}}"
        )
        mcl = QHBoxLayout(self._my_card)
        mcl.setContentsMargins(18, 14, 18, 14)
        mcl.setSpacing(20)

        rank_col = QVBoxLayout()
        self._my_rank_lbl = QLabel("—")
        self._my_rank_lbl.setStyleSheet(f"color:{_ACCENT}; font-size:28px; font-weight:900; font-family:Consolas;")
        self._my_rank_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank_sub = QLabel("SIRANIZ")
        rank_sub.setStyleSheet(f"color:{_TEXT3}; font-size:9px; font-weight:700; letter-spacing:1px;")
        rank_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank_col.addWidget(self._my_rank_lbl)
        rank_col.addWidget(rank_sub)
        mcl.addLayout(rank_col)

        div = QFrame(); div.setFrameShape(QFrame.Shape.VLine)
        div.setStyleSheet(f"color:{_BORDER}; background:{_BORDER};"); div.setFixedWidth(1)
        mcl.addWidget(div)

        name_col = QVBoxLayout()
        self._my_name_lbl = QLabel(self._lb.username)
        self._my_name_lbl.setStyleSheet(f"color:{_TEXT}; font-size:15px; font-weight:800;")
        name_sub = QLabel("Oturum kullanıcı adı (her başlatmada yenilenir)")
        name_sub.setStyleSheet(f"color:{_TEXT3}; font-size:10px;")
        name_col.addWidget(self._my_name_lbl)
        name_col.addWidget(name_sub)
        mcl.addLayout(name_col, 1)

        for label, attr in (("K/Z TL", "_my_pnl_lbl"), ("İşlemler", "_my_trades_lbl"), ("XP", "_my_xp_lbl")):
            stat_col = QVBoxLayout()
            stat_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_lbl = QLabel("—")
            stat_lbl.setStyleSheet(f"color:{_TEXT}; font-size:15px; font-weight:700; font-family:Consolas;")
            stat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sub_lbl = QLabel(label)
            sub_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:9px; font-weight:700; letter-spacing:1px;")
            sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            setattr(self, attr, stat_lbl)
            stat_col.addWidget(stat_lbl)
            stat_col.addWidget(sub_lbl)
            mcl.addLayout(stat_col)

        self._vl.addWidget(self._my_card)

    def _build_table_section(self) -> None:
        sec = QFrame()
        sec.setStyleSheet(f"QFrame {{background:{_SURF}; border:1px solid {_BORDER}; border-radius:10px;}}")
        sec_vl = QVBoxLayout(sec)
        sec_vl.setContentsMargins(16, 14, 16, 14)
        sec_vl.setSpacing(8)

        top_hdr = QLabel("🏆  EN İYİ 10 TRADER")
        top_hdr.setStyleSheet(f"color:{_TEXT3}; font-size:10px; font-weight:700; letter-spacing:1.5px;")
        sec_vl.addWidget(top_hdr)

        # Column headers
        col_row = QHBoxLayout()
        col_row.setSpacing(0)
        for header, width in zip(self._HEADERS, self._WIDTHS):
            lbl = QLabel(header)
            lbl.setFixedWidth(width)
            lbl.setStyleSheet(f"color:{_TEXT3}; font-size:9px; font-weight:700; letter-spacing:0.8px;")
            col_row.addWidget(lbl)
        col_row.addStretch()
        sec_vl.addLayout(col_row)
        sec_vl.addWidget(_sep())

        self._table_vl = QVBoxLayout()
        self._table_vl.setSpacing(4)
        sec_vl.addLayout(self._table_vl)
        self._vl.addWidget(sec)

        notice = QLabel(
            "💡  Skoru kaydetmek için yukarıdaki <b>Skoru Kaydet</b> butonuna bas. "
            "Liderlik tablosu <code>leaderboard.json</code> dosyasına kaydedilir."
        )
        notice.setStyleSheet(f"color:{_TEXT3}; font-size:11px;")
        notice.setWordWrap(True)
        self._vl.addWidget(notice)

    def _clear_table(self) -> None:
        while self._table_vl.count():
            item = self._table_vl.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def refresh(self, current_entry: "LeaderboardEntry | None" = None) -> None:
        entries = self._lb.get_top_10()
        rank    = self._lb.current_rank()
        total   = self._lb.entry_count
        self._sub_lbl.setText(f"{total} kayıtlı oturum — en yüksek K/Z'a göre sıralandı")

        if current_entry:
            color = _GREEN if current_entry.total_pnl >= 0 else _RED
            self._my_pnl_lbl.setText(f"{current_entry.total_pnl:+,.0f}")
            self._my_pnl_lbl.setStyleSheet(
                f"color:{color}; font-size:15px; font-weight:700; font-family:Consolas;"
            )
            self._my_trades_lbl.setText(str(current_entry.trade_count))
            self._my_xp_lbl.setText(str(current_entry.xp))
        self._my_rank_lbl.setText(str(rank) if rank else "—")

        self._clear_table()
        if not entries:
            placeholder = QLabel("Henüz kayıtlı oturum yok. 'Skoru Kaydet' butonuna bas.")
            placeholder.setStyleSheet(f"color:{_TEXT3}; font-size:12px;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table_vl.addWidget(placeholder)
            return

        my_username = self._lb.username
        for i, entry in enumerate(entries, start=1):
            is_me = entry.username == my_username
            row_frame = QFrame()
            row_frame.setStyleSheet(
                f"QFrame {{background:{_ACCENT}11; border-radius:6px;}}"
                if is_me else
                f"QFrame {{background:{_SURF2}; border-radius:6px;}}"
            )
            row_hl = QHBoxLayout(row_frame)
            row_hl.setContentsMargins(6, 6, 6, 6)
            row_hl.setSpacing(0)

            rank_icon = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else str(i)))
            values = [
                rank_icon,
                entry.username + (" ◀ Sen" if is_me else ""),
                f"{entry.total_pnl:+,.0f}",
                f"{entry.pnl_pct:+.1f}%",
                str(entry.trade_count),
                f"%{entry.win_rate:.0f}",
                f"{entry.risk_score:.1f}/10",
                entry.level,
                str(entry.xp),
            ]
            pnl_color = _GREEN if entry.total_pnl >= 0 else _RED

            for j, (val, width) in enumerate(zip(values, self._WIDTHS)):
                lbl = QLabel(val)
                lbl.setFixedWidth(width)
                color = _TEXT
                if j == 2:
                    color = pnl_color
                elif j == 3:
                    color = pnl_color
                elif is_me:
                    color = _ACCENT if j == 1 else _TEXT
                lbl.setStyleSheet(
                    f"color:{color}; font-size:11px; "
                    + ("font-weight:700;" if j <= 1 or is_me else "font-weight:500;")
                    + " font-family:Consolas;" if j >= 2 else ""
                )
                row_hl.addWidget(lbl)
            row_hl.addStretch()
            self._table_vl.addWidget(row_frame)


# ── Level Completion Dialog ────────────────────────────────────────────────────

class LevelCompletionDialog(QFrame):
    """Semi-transparent overlay shown when a level is completed."""

    def __init__(self, parent: QWidget, level_name: str, level_icon: str, summary: dict) -> None:
        super().__init__(parent)
        self.setObjectName("levelCompleteDialog")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.raise_()
        self._build(level_name, level_icon, summary)
        self._center()
        self.show()
        QTimer.singleShot(8000, self.close)

    def _center(self) -> None:
        if self.parent():
            pr = self.parent().rect()
            self.move(
                (pr.width()  - self.width())  // 2,
                (pr.height() - self.height()) // 2,
            )

    def _build(self, name: str, icon: str, s: dict) -> None:
        self.setFixedWidth(420)
        self.setStyleSheet(
            f"QFrame#levelCompleteDialog {{"
            f"background:#0d1b2e; border:2px solid {_GREEN}; border-radius:16px;"
            f"}}"
        )
        vl = QVBoxLayout(self)
        vl.setContentsMargins(28, 24, 28, 24)
        vl.setSpacing(12)

        # Confetti header
        confetti = QLabel(f"{icon}  Seviye Tamamlandı!  {icon}")
        confetti.setAlignment(Qt.AlignmentFlag.AlignCenter)
        confetti.setStyleSheet(f"color:{_GREEN}; font-size:18px; font-weight:900;")
        vl.addWidget(confetti)

        level_lbl = QLabel(name)
        level_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        level_lbl.setStyleSheet(f"color:{_TEXT2}; font-size:13px; font-weight:600;")
        vl.addWidget(level_lbl)
        vl.addWidget(_sep())

        # Stats grid
        stats: list[tuple[str, str, str]] = [
            ("✅ Görevler",  f"{s.get('tasks_done',0)} / {s.get('total_tasks',0)}", _TEXT),
            ("⚡ Kazanılan XP", f"+{s.get('earned_xp',0)} XP",   _AMBER),
            ("📈 Toplam K/Z",   f"{s.get('total_pnl',0):+,.0f} TL", _GREEN if s.get('total_pnl',0) >= 0 else _RED),
            ("🔄 Toplam İşlem", str(s.get('total_trades',0)),           _TEXT),
        ]
        for row_label, row_val, col in stats:
            hl = QHBoxLayout()
            l1 = QLabel(row_label)
            l1.setStyleSheet(f"color:{_TEXT2}; font-size:12px;")
            l2 = QLabel(row_val)
            l2.setStyleSheet(f"color:{col}; font-size:13px; font-weight:700; font-family:Consolas;")
            l2.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            hl.addWidget(l1)
            hl.addStretch()
            hl.addWidget(l2)
            vl.addLayout(hl)

        vl.addWidget(_sep())

        best = s.get("best_trade")
        if best:
            best_lbl = QLabel(f"🏆  En İyi Satış:  {best.symbol}  →  TL {best.total:,.0f}")
            best_lbl.setStyleSheet(f"color:{_GREEN}; font-size:11px; font-weight:600;")
            best_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl.addWidget(best_lbl)

        close_btn = QPushButton("Devam Et  →")
        close_btn.setFixedHeight(38)
        close_btn.setStyleSheet(
            f"background:{_GREEN}; color:#051a0d; border:none; "
            f"border-radius:8px; font-size:13px; font-weight:800;"
        )
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        vl.addSpacing(4)
        vl.addWidget(close_btn)

        note = QLabel("Bu pencere 8 saniye sonra otomatik kapanır.")
        note.setStyleSheet(f"color:{_TEXT3}; font-size:10px;")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(note)
        self.adjustSize()


# ── Toast Notification ────────────────────────────────────────────────────────

class ToastNotification(QFrame):
    """Transient overlay notification shown after task/achievement completion."""

    def __init__(self, parent: QWidget, icon: str, title: str, body: str, color: str = _GREEN) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setFixedWidth(340)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.raise_()
        self._build(icon, title, body, color)
        self._reposition()
        self.show()
        QTimer.singleShot(4500, self.hide)

    def _build(self, icon: str, title: str, body: str, color: str) -> None:
        hl = QHBoxLayout(self)
        hl.setContentsMargins(14, 12, 14, 12)
        hl.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            f"font-size:22px; background:{color}22; border:1px solid {color}55; border-radius:8px;"
        )
        hl.addWidget(icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:13px; font-weight:800;")
        body_lbl  = QLabel(body)
        body_lbl.setStyleSheet(f"color:{_TEXT2}; font-size:11px;")
        body_lbl.setWordWrap(True)
        col.addWidget(title_lbl)
        col.addWidget(body_lbl)
        hl.addLayout(col, 1)

        self.setStyleSheet(
            f"QFrame#toast {{"
            f"background:{_SURF}; border:1px solid {color}; border-radius:10px;"
            f"border-left: 4px solid {color};"
            f"}}"
        )

    def _reposition(self) -> None:
        if self.parent():
            pr = self.parent().rect()
            self.move(pr.width() - self.width() - 20, pr.height() - self.height() - 54)


# ── AI Coach Page ─────────────────────────────────────────────────────────────

class AICoachPage(QScrollArea):
    """
    Hybrid AI Coach panel — rule-based fallback + optional Gemini enhancement.

    Features
    --------
    * Status bar showing Gemini availability + live portfolio snapshot
    * Smart Suggestion — updated after every trade/action
    * Ask AI — free-text Q&A wired to AICoach.answer_question()
    * Learning Hint — one-click hint for the current active task
    * API Key setup — inline input when key is missing
    """

    def __init__(self, ai_coach: "object | None" = None) -> None:
        super().__init__()
        self._coach    = ai_coach   # AICoach instance (or None)
        self._state: object | None    = None
        self._extra: object | None    = None
        self._ls:    object | None    = None
        self._lb:    object | None    = None
        self._active_task: object | None = None

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._inner = QWidget()
        self._vl    = QVBoxLayout(self._inner)
        self._vl.setContentsMargins(24, 20, 24, 24)
        self._vl.setSpacing(14)
        self.setWidget(self._inner)
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self._build_header()
        self._build_status_bar()
        self._build_suggestion_panel()
        self._build_qa_panel()
        self._build_hint_panel()
        self._build_context_panel()
        self._vl.addStretch()

    def _build_header(self) -> None:
        hdr = QHBoxLayout()
        icon_lbl = QLabel("🤖")
        icon_lbl.setStyleSheet("font-size:28px;")
        hdr.addWidget(icon_lbl)
        col = QVBoxLayout(); col.setSpacing(2)
        title = QLabel("AI Koç")
        title.setStyleSheet(f"color:{_TEXT}; font-size:20px; font-weight:800;")
        sub = QLabel("Portföy verilerine dayalı kişiselleştirilmiş koçluk.")
        sub.setStyleSheet(f"color:{_TEXT2}; font-size:12px;")
        col.addWidget(title); col.addWidget(sub)
        hdr.addLayout(col); hdr.addStretch()
        self._vl.addLayout(hdr)
        self._vl.addWidget(_sep())

    def _build_status_bar(self) -> None:
        frm = QFrame()
        frm.setObjectName("aiStatusBar")
        hl  = QHBoxLayout(frm)
        hl.setContentsMargins(14, 10, 14, 10)
        hl.setSpacing(12)

        self._status_dot = QLabel("●")
        self._status_dot.setFixedWidth(16)
        self._status_msg  = QLabel("Yükleniyor…")
        self._status_msg.setStyleSheet(f"color:{_TEXT2}; font-size:12px;")
        hl.addWidget(self._status_dot)
        hl.addWidget(self._status_msg, 1)

        # Inline API key input (shown when key missing)
        self._key_input = _create_line_edit("GEMINI_API_KEY yapıştırın…")
        self._key_input.setEchoMode(self._key_input.EchoMode.Password)
        self._key_input.setFixedWidth(280)
        self._key_btn = QPushButton("Bağlan")
        self._key_btn.setFixedHeight(30)
        self._key_btn.setStyleSheet(
            f"background:{_ACCENT}; color:white; border:none; border-radius:5px; "
            f"font-size:11px; font-weight:700; padding:0 12px;"
        )
        self._key_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._key_btn.clicked.connect(self._on_connect_key)
        hl.addWidget(self._key_input)
        hl.addWidget(self._key_btn)
        self._vl.addWidget(frm)
        self._refresh_status()

    def _build_suggestion_panel(self) -> None:
        frm = QFrame()
        frm.setObjectName("aiSuggPanel")
        frm.setStyleSheet(
            f"QFrame#aiSuggPanel {{background:{_SURF}; border:1px solid {_BORDER}; border-radius:10px;}}"
        )
        vl = QVBoxLayout(frm)
        vl.setContentsMargins(18, 14, 18, 14)
        vl.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("💡  Akıllı Öneri")
        title.setStyleSheet(f"color:{_TEXT3}; font-size:10px; font-weight:700; letter-spacing:1px;")
        hdr.addWidget(title)
        hdr.addStretch()
        self._sugg_loading = QLabel("⏳")
        self._sugg_loading.setStyleSheet(f"color:{_AMBER}; font-size:12px;")
        self._sugg_loading.setVisible(False)
        hdr.addWidget(self._sugg_loading)
        self._refresh_sugg_btn = QPushButton("↻ Yenile")
        self._refresh_sugg_btn.setFixedHeight(26)
        self._refresh_sugg_btn.setStyleSheet(
            f"background:{_SURF2}; color:{_TEXT2}; border:1px solid {_BORDER}; "
            f"border-radius:5px; font-size:10px; font-weight:600; padding:0 10px;"
        )
        self._refresh_sugg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_sugg_btn.clicked.connect(self._on_refresh_suggestion)
        hdr.addWidget(self._refresh_sugg_btn)
        vl.addLayout(hdr)

        self._sugg_lbl = QLabel("Henüz öneri yok. Bir işlem gerçekleştirin.")
        self._sugg_lbl.setStyleSheet(f"color:{_TEXT}; font-size:13px; line-height:1.5;")
        self._sugg_lbl.setWordWrap(True)
        vl.addWidget(self._sugg_lbl)

        self._sugg_source = QLabel()
        self._sugg_source.setStyleSheet(f"color:{_TEXT3}; font-size:10px;")
        vl.addWidget(self._sugg_source)
        self._vl.addWidget(frm)

    def _build_qa_panel(self) -> None:
        frm = QFrame()
        frm.setObjectName("aiQAPanel")
        frm.setStyleSheet(
            f"QFrame#aiQAPanel {{background:{_SURF}; border:1px solid {_BORDER}; border-radius:10px;}}"
        )
        vl = QVBoxLayout(frm)
        vl.setContentsMargins(18, 14, 18, 14)
        vl.setSpacing(10)

        title = QLabel("💬  AI'ya Sor")
        title.setStyleSheet(f"color:{_TEXT3}; font-size:10px; font-weight:700; letter-spacing:1px;")
        vl.addWidget(title)

        examples_lbl = QLabel("Örn: 'Portföy riskimi nasıl düşürürüm?'  ·  'En iyi işlemim ne?'  ·  'Ne alayım?'")
        examples_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:10px; font-style:italic;")
        vl.addWidget(examples_lbl)

        input_row = QHBoxLayout(); input_row.setSpacing(8)
        self._qa_input = _create_line_edit("Sorunuzu yazın…")
        self._qa_input.returnPressed.connect(self._on_ask)
        input_row.addWidget(self._qa_input, 1)
        ask_btn = QPushButton("Sor  →")
        ask_btn.setFixedHeight(36)
        ask_btn.setStyleSheet(
            f"background:{_ACCENT}; color:white; border:none; "
            f"border-radius:6px; font-size:12px; font-weight:700; padding:0 16px;"
        )
        ask_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ask_btn.clicked.connect(self._on_ask)
        input_row.addWidget(ask_btn)
        vl.addLayout(input_row)

        self._qa_loading = QLabel("⏳  Yanıt bekleniyor…")
        self._qa_loading.setStyleSheet(f"color:{_AMBER}; font-size:11px;")
        self._qa_loading.setVisible(False)
        vl.addWidget(self._qa_loading)

        self._qa_answer = QLabel("")
        self._qa_answer.setStyleSheet(
            f"color:{_TEXT}; font-size:13px; "
            f"background:{_SURF2}; border:1px solid {_BORDER}; border-radius:7px; "
            f"padding:10px 12px;"
        )
        self._qa_answer.setWordWrap(True)
        self._qa_answer.setVisible(False)
        vl.addWidget(self._qa_answer)

        self._qa_source = QLabel()
        self._qa_source.setStyleSheet(f"color:{_TEXT3}; font-size:10px;")
        vl.addWidget(self._qa_source)
        self._vl.addWidget(frm)

    def _build_hint_panel(self) -> None:
        frm = QFrame()
        frm.setObjectName("aiHintPanel")
        frm.setStyleSheet(
            f"QFrame#aiHintPanel {{background:{_SURF}; border:1px solid {_BORDER}; border-radius:10px;}}"
        )
        vl = QVBoxLayout(frm)
        vl.setContentsMargins(18, 14, 18, 14)
        vl.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("🎯  Görev İpucu")
        title.setStyleSheet(f"color:{_TEXT3}; font-size:10px; font-weight:700; letter-spacing:1px;")
        hdr.addWidget(title); hdr.addStretch()
        hint_btn = QPushButton("İpucu Al")
        hint_btn.setFixedHeight(28)
        hint_btn.setStyleSheet(
            f"background:{_PURPLE}22; color:{_PURPLE}; border:1px solid {_PURPLE}44; "
            f"border-radius:5px; font-size:11px; font-weight:700; padding:0 12px;"
        )
        hint_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        hint_btn.clicked.connect(self._on_get_hint)
        hdr.addWidget(hint_btn)
        vl.addLayout(hdr)

        self._hint_task_lbl = QLabel("Aktif görev: —")
        self._hint_task_lbl.setStyleSheet(f"color:{_TEXT2}; font-size:11px;")
        vl.addWidget(self._hint_task_lbl)

        self._hint_lbl = QLabel("")
        self._hint_lbl.setStyleSheet(
            f"color:{_PURPLE}; font-size:12px; font-weight:600; "
            f"background:{_PURPLE}0d; border:1px solid {_PURPLE}33; border-radius:7px; padding:8px 12px;"
        )
        self._hint_lbl.setWordWrap(True)
        self._hint_lbl.setVisible(False)
        vl.addWidget(self._hint_lbl)
        self._vl.addWidget(frm)

    def _build_context_panel(self) -> None:
        """Collapsible portfolio context snapshot (for transparency)."""
        frm = QFrame()
        frm.setObjectName("aiCtxPanel")
        frm.setStyleSheet(
            f"QFrame#aiCtxPanel {{background:{_SURF2}; border:1px solid {_BORDER}; border-radius:8px;}}"
        )
        vl = QVBoxLayout(frm)
        vl.setContentsMargins(16, 12, 16, 12)
        vl.setSpacing(6)

        hdr = QHBoxLayout()
        title = QLabel("🔍  AI'ya Gönderilen Veriler")
        title.setStyleSheet(f"color:{_TEXT3}; font-size:10px; font-weight:700; letter-spacing:1px;")
        hdr.addWidget(title); hdr.addStretch()
        toggle_btn = QPushButton("▼ Göster")
        toggle_btn.setFixedHeight(24)
        toggle_btn.setStyleSheet(
            f"background:transparent; color:{_TEXT3}; border:none; font-size:10px;"
        )
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        hdr.addWidget(toggle_btn)
        vl.addLayout(hdr)

        self._ctx_body = QLabel("—")
        self._ctx_body.setStyleSheet(
            f"color:{_TEXT3}; font-size:10px; font-family:Consolas; "
            f"background:{_SURF3}; border-radius:5px; padding:8px;"
        )
        self._ctx_body.setWordWrap(True)
        self._ctx_body.setVisible(False)
        self._ctx_open = False
        vl.addWidget(self._ctx_body)

        def _toggle() -> None:
            self._ctx_open = not self._ctx_open
            self._ctx_body.setVisible(self._ctx_open)
            toggle_btn.setText("▲ Gizle" if self._ctx_open else "▼ Göster")

        toggle_btn.clicked.connect(_toggle)
        self._vl.addWidget(frm)

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _on_connect_key(self) -> None:
        if not self._coach:
            return
        key = self._key_input.text().strip()
        if not key:
            return
        ok = self._coach._gemini.configure(key)
        self._refresh_status()
        if ok and self._state is not None:
            self._on_refresh_suggestion()

    def _on_refresh_suggestion(self) -> None:
        if not self._coach or self._state is None:
            return
        self._sugg_loading.setVisible(True)
        self._refresh_sugg_btn.setEnabled(False)
        self._coach.get_action_suggestion(
            self._state, self._extra, self._ls, "",
            callback=self._on_sugg_ready, lb=self._lb,
        )

    def _on_ask(self) -> None:
        if not self._coach or self._state is None:
            return
        question = self._qa_input.text().strip()
        if not question:
            return
        self._qa_loading.setVisible(True)
        self._qa_answer.setVisible(False)
        self._coach.answer_question(
            self._state, self._extra, self._ls, question,
            callback=self._on_qa_ready, lb=self._lb,
        )

    def _on_get_hint(self) -> None:
        if not self._coach or self._state is None or self._active_task is None:
            self._hint_lbl.setText("Aktif görev bulunamadı. Önce bir seviyedeki göreve başlayın.")
            self._hint_lbl.setVisible(True)
            return
        self._coach.get_learning_hint(
            self._state, self._extra, self._ls, self._active_task,
            callback=self._on_hint_ready, lb=self._lb,
        )

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_sugg_ready(self, text: str) -> None:
        self._sugg_lbl.setText(text)
        self._sugg_loading.setVisible(False)
        self._refresh_sugg_btn.setEnabled(True)
        is_ai = self._coach and self._coach.gemini_available
        self._sugg_source.setText(
            "🤖 Gemini AI yanıtı" if is_ai else "📋 Kural tabanlı analiz"
        )

    def _on_qa_ready(self, text: str) -> None:
        self._qa_loading.setVisible(False)
        self._qa_answer.setText(text)
        self._qa_answer.setVisible(True)
        is_ai = self._coach and self._coach.gemini_available
        self._qa_source.setText(
            "🤖 Gemini AI yanıtı" if is_ai else "📋 Kural tabanlı yanıt"
        )

    def _on_hint_ready(self, text: str) -> None:
        self._hint_lbl.setText(text)
        self._hint_lbl.setVisible(True)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def _refresh_status(self) -> None:
        if not self._coach:
            self._status_dot.setStyleSheet(f"color:{_TEXT3}; font-size:14px;")
            self._status_msg.setText("AI Koç bağlanmadı.")
            self._key_input.setVisible(True); self._key_btn.setVisible(True)
            return
        available = self._coach.gemini_available
        icon      = self._coach._gemini.status_icon
        status    = self._coach.gemini_status
        color     = _GREEN if available else _AMBER
        self._status_dot.setText(icon)
        self._status_dot.setStyleSheet(f"color:{color}; font-size:14px;")
        self._status_msg.setText(status)
        self._key_input.setVisible(not available)
        self._key_btn.setVisible(not available)

    def _update_context_display(self, ctx: dict) -> None:
        p    = ctx.get("portfolio", {})
        perf = ctx.get("performance", {})
        risk = ctx.get("risk", {})
        text = (
            f"Portföy: TL {p.get('total_value',0):,.0f}  |  Nakit: TL {p.get('cash',0):,.0f}\n"
            f"K/Z: {perf.get('profit_loss',0):+,.0f} TL ({perf.get('profit_loss_pct',0):+.1f}%)\n"
            f"Risk: {risk.get('risk_level','—')}  |  {risk.get('asset_count',0)} varlık  |  "
            f"Max konsantrasyon: %{risk.get('max_concentration_pct',0):.0f}\n"
            f"Uyarılar: {', '.join(risk.get('warnings',[])) or '—'}"
        )
        self._ctx_body.setText(text)

    def refresh(
        self,
        state: object,
        extra: object,
        ls: object,
        lb: "object | None" = None,
        auto_suggestion: bool = False,
    ) -> None:
        """Called by LearnPage.refresh() after every state update."""
        self._state = state
        self._extra = extra
        self._ls    = ls
        self._lb    = lb

        # Find active learning task
        self._active_task = None
        if ls:
            for lvl in ls.levels:
                if not lvl.is_unlocked(ls.xp):
                    continue
                t = lvl.get_next_task(ls._completed_tasks)
                if t:
                    self._active_task = t
                    break

        task_title = self._active_task.title if self._active_task else "—"
        self._hint_task_lbl.setText(f"Aktif görev: {task_title}")

        # Update context debug panel
        if self._coach and state is not None:
            ctx = self._coach.build_context(state, extra, ls, lb=lb)
            self._update_context_display(ctx)

        # Auto-generate suggestion if requested (e.g. after a trade)
        if auto_suggestion and self._coach and state is not None:
            self._on_refresh_suggestion()

        self._refresh_status()

    def push_suggestion(self, text: str, is_ai: bool = False) -> None:
        """Called directly by MainWindow after a trade with the AI response."""
        self._sugg_lbl.setText(text)
        self._sugg_loading.setVisible(False)
        self._refresh_sugg_btn.setEnabled(True)
        self._sugg_source.setText(
            "🤖 Gemini AI yanıtı" if is_ai else "📋 Kural tabanlı analiz"
        )


def _create_line_edit(placeholder: str = "") -> QLineEdit:
    w = QLineEdit()
    w.setPlaceholderText(placeholder)
    w.setObjectName("formInput")
    w.setFixedHeight(34)
    w.setStyleSheet(
        f"background:#1a2235; border:1px solid #1e2d45; border-radius:5px; "
        f"color:#e2e8f0; padding:0 8px; font-size:12px;"
    )
    return w


# ── Main LearnPage ────────────────────────────────────────────────────────────

class LearnPage(QWidget):
    """Fully interactive, task-based learning mode page."""

    _NAV_ITEMS = [
        ("🌱", "Başlangıç",    "beginner"),
        ("📈", "Orta",         "intermediate"),
        ("🚀", "İleri",        "advanced"),
        ("🏆", "Başarımlar",   "achievements"),
        ("⚡", "Zorluklar",    "challenges"),
        ("📊", "Analizlerim",  "analytics"),
        ("🏅", "Liderlik",     "leaderboard"),
        ("🧮", "Araçlar",      "tools"),
        ("🤖", "AI Koç",       "ai_coach"),
    ]

    def __init__(
        self,
        ls: LearningSystem,
        navigate_cb: Callable[[int], None],
        calc_used_cb: Callable[[], None] | None = None,
        lb_manager: "LeaderboardManager | None" = None,
        save_session_cb: "Callable[[], None] | None" = None,
        ai_coach: "object | None" = None,
        feature_datasets: dict | None = None,
    ) -> None:
        super().__init__()
        self._ls              = ls
        self._navigate        = navigate_cb
        self._calc_used_cb    = calc_used_cb
        self._lb              = lb_manager
        self._save_session_cb = save_session_cb
        self._ai_coach        = ai_coach
        self._feature_datasets = feature_datasets or {}
        self._active_section  = 0
        self._current_state: object = None
        self._build()
        self._setup_callbacks()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._xp_header = XPHeaderBar(self._ls)
        outer.addWidget(self._xp_header)
        outer.addWidget(_sep())

        body_widget = QWidget()
        body = QHBoxLayout(body_widget)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        body.addWidget(self._build_sidebar())
        body.addWidget(_sep(vertical=True))

        self._content = QStackedWidget()
        self._level_pages: dict[str, LevelPage] = {}

        for level in ["beginner", "intermediate", "advanced"]:
            pg = LevelPage(level, self._ls, self._navigate, self._on_validate_click)
            self._level_pages[level] = pg
            self._content.addWidget(pg)

        self._ach_page  = AchievementsPage(self._ls)
        self._ch_page   = ChallengesPage(self._ls)
        self._anal_page = AnalyticsPage(self._ls)
        self._lb_page   = LeaderboardPage(self._lb, self._save_session_cb) if self._lb else LeaderboardPage(
            type("_FakeLB", (), {
                "username": "—", "get_top_10": list, "current_rank": lambda s: None,
                "current_entry": lambda s: None, "entry_count": 0,
            })()
        )
        self._tools_page    = self._build_tools_page()
        self._ai_coach_page = AICoachPage(self._ai_coach)
        self._content.addWidget(self._ach_page)
        self._content.addWidget(self._ch_page)
        self._content.addWidget(self._anal_page)
        self._content.addWidget(self._lb_page)
        self._content.addWidget(self._tools_page)
        self._content.addWidget(self._ai_coach_page)

        body.addWidget(self._content, 1)
        outer.addWidget(body_widget, 1)

    def _build_tools_page(self) -> QScrollArea:
        """Interactive tools page: P/L calculator + DCA simulator."""
        from src.education.widgets import DCASimulatorWidget, PLCalculatorWidget

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(24, 20, 24, 20)
        vl.setSpacing(16)
        scroll.setWidget(inner)

        # Header
        hdr = QHBoxLayout()
        icon_lbl = QLabel("🧮")
        icon_lbl.setStyleSheet("font-size:28px;")
        hdr.addWidget(icon_lbl)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("İnteraktif Araçlar")
        title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:20px; font-weight:800;")
        sub_lbl = QLabel("K/Z Hesaplayıcı ve DCA Simülatörü — değerleri değiştirerek öğren.")
        sub_lbl.setStyleSheet(f"color:{_TEXT2}; font-size:12px;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)
        hdr.addLayout(title_col)
        hdr.addStretch()

        # Advanced task badge
        task_badge = QLabel("🚀 İleri Görev: Hesaplayıcıları Kullan")
        task_badge.setStyleSheet(
            f"color:{_PURPLE}; background:{_PURPLE}11; border:1px solid {_PURPLE}44; "
            f"border-radius:6px; font-size:11px; font-weight:700; padding:4px 12px;"
        )
        hdr.addWidget(task_badge)
        vl.addLayout(hdr)
        vl.addWidget(_sep())
        vl.addSpacing(4)

        # Notice
        notice_frm = QFrame()
        notice_frm.setStyleSheet(
            f"background:{_ACCENT}11; border:1px solid {_ACCENT}44; border-radius:8px;"
        )
        notice_vl = QVBoxLayout(notice_frm)
        notice_vl.setContentsMargins(14, 10, 14, 10)
        notice_lbl = QLabel(
            "💡  Bu sayfadaki araçlarla etkileşime geçtiğinde "
            "<b>'Hesaplayıcıları Kullan'</b> görevi otomatik olarak tamamlanacak."
        )
        notice_lbl.setStyleSheet(f"color:{_ACCENT}; font-size:12px;")
        notice_lbl.setWordWrap(True)
        notice_vl.addWidget(notice_lbl)
        vl.addWidget(notice_frm)
        vl.addSpacing(4)

        # P/L Calculator
        pl_frm = QFrame()
        pl_frm.setStyleSheet(
            f"background:{_SURF}; border:1px solid {_BORDER}; border-radius:10px;"
        )
        pl_vl = QVBoxLayout(pl_frm)
        pl_vl.setContentsMargins(20, 16, 20, 16)
        pl_calc = PLCalculatorWidget()
        # Wrap valueChanged to fire calc_used_cb
        orig_recalc = pl_calc._recalc
        def _pl_recalc_tracked():
            orig_recalc()
            if self._calc_used_cb:
                self._calc_used_cb()
        pl_calc.sp_buy.valueChanged.connect(lambda _v: _pl_recalc_tracked() if _v else None)
        pl_calc.sp_cur.valueChanged.connect(lambda _v: _pl_recalc_tracked() if _v else None)
        pl_calc.sp_qty.valueChanged.connect(lambda _v: _pl_recalc_tracked() if _v else None)
        pl_vl.addWidget(pl_calc)
        vl.addWidget(pl_frm)

        # DCA Simulator
        dca_frm = QFrame()
        dca_frm.setStyleSheet(
            f"background:{_SURF}; border:1px solid {_BORDER}; border-radius:10px;"
        )
        dca_vl = QVBoxLayout(dca_frm)
        dca_vl.setContentsMargins(20, 16, 20, 16)
        dca_sim = DCASimulatorWidget()
        orig_slide = dca_sim._on_slide
        def _dca_slide_tracked():
            orig_slide()
            if self._calc_used_cb:
                self._calc_used_cb()
        dca_sim.sl_amt.valueChanged.connect(lambda _v: _dca_slide_tracked())
        dca_sim.sl_mo.valueChanged.connect(lambda _v: _dca_slide_tracked())
        dca_vl.addWidget(dca_sim)
        vl.addWidget(dca_frm)
        vl.addStretch()

        return scroll

    def _build_sidebar(self) -> QFrame:
        side = QFrame()
        side.setObjectName("learnSidebar")
        side.setFixedWidth(200)
        vl = QVBoxLayout(side)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        hdr = QLabel("  🎓  Öğrenme Modu")
        hdr.setObjectName("learnHeader")
        hdr.setFixedHeight(50)
        vl.addWidget(hdr)

        self._nav_btns: list[QPushButton] = []
        for i, (icon, label, _key) in enumerate(self._NAV_ITEMS):
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("learnNavBtn")
            btn.setCheckable(True)
            btn.setFixedHeight(46)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _c, idx=i: self._switch_section(idx))
            self._nav_btns.append(btn)
            vl.addWidget(btn)

            # Separator before achievements
            if label == "İleri":
                vl.addSpacing(4)
                sep = _sep()
                sep.setStyleSheet(f"color:{_BORDER}; background:{_BORDER}; margin:0 12px;")
                vl.addWidget(sep)
                vl.addSpacing(4)

        vl.addStretch()

        # Mini XP summary at bottom of sidebar
        summary = QFrame()
        summary.setStyleSheet(
            f"background:{_SURF2}; border-top:1px solid {_BORDER};"
        )
        svl = QVBoxLayout(summary)
        svl.setContentsMargins(12, 10, 12, 10)
        svl.setSpacing(4)
        self._sidebar_xp_lbl = QLabel()
        self._sidebar_xp_lbl.setStyleSheet(f"color:{_AMBER}; font-size:12px; font-weight:800;")
        self._sidebar_level_lbl = QLabel()
        self._sidebar_level_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:10px;")
        svl.addWidget(self._sidebar_xp_lbl)
        svl.addWidget(self._sidebar_level_lbl)
        vl.addWidget(summary)

        if self._nav_btns:
            self._nav_btns[0].setChecked(True)
        return side

    def _setup_callbacks(self) -> None:
        self._ls.on_task_complete(self._on_task_complete)
        self._ls.on_achievement_unlock(self._on_achievement_unlock)
        self._ls.on_level_up(self._on_level_up)
        self._ls.on_level_complete(self._on_level_complete)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _switch_section(self, idx: int) -> None:
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)
        self._content.setCurrentIndex(idx)
        self._active_section = idx

    # ── Validation trigger ─────────────────────────────────────────────────────

    def _on_validate_click(self, task_id: str) -> None:
        """Called when user presses the Validate button on a task card."""
        # This is just a visual trigger — actual validation happens in check_all
        # Show a hint that validation is automatic
        task = next((t for t in self._ls.tasks if t.id == task_id), None)
        if not task:
            return
        if self._ls.is_task_complete(task_id):
            self._show_toast("✓", "Zaten tamamlandı!", f"'{task.title}' görevi zaten tamamlandı.", _GREEN)
        else:
            self._show_toast(
                "💡",
                "Doğrulama otomatik!",
                f"'{task.title}' görevini tamamlamak için belirtilen adımı gerçekleştir. "
                "Sistem otomatik olarak doğrulayacak.",
                _ACCENT,
            )

    # ── Callbacks from LearningSystem ──────────────────────────────────────────

    def _on_task_complete(self, task: TaskSpec, xp: int) -> None:
        self._show_toast(
            task.icon,
            f"Görev Tamamlandı! +{xp} XP",
            f"'{task.title}' görevini başarıyla tamamladın. Harika iş!",
            _GREEN,
        )
        # Flash the task card
        level_pg = self._level_pages.get(task.level)
        if level_pg:
            tw = level_pg._task_widgets.get(task.id)
            if tw:
                tw.flash_success()

    def _on_achievement_unlock(self, ach: Achievement) -> None:
        self._show_toast(
            ach.icon,
            f"Başarım Kazanıldı! +{ach.xp} XP",
            f"'{ach.title}' başarımını kazandın — {ach.desc}",
            _AMBER,
        )

    def _on_level_up(self, new_level: str) -> None:
        meta = self._ls.LEVEL_META.get(new_level, ("🎉", new_level))
        self._show_toast(
            meta[0],
            "Seviye Atladın!",
            f"Tebrikler! '{meta[1]}' seviyesine ulaştın. Yeni görevler açıldı!",
            _PURPLE,
        )

    def _on_level_complete(self, level: object) -> None:
        """Show level-completion dialog with performance summary."""
        # `level` is a Level object from manager.py
        summary = self._ls.get_level_summary(level.id, self._current_state)
        dlg = LevelCompletionDialog(self, level.name, level.icon, summary)
        dlg.show()

    def show_mistake_warning(self, warning: MistakeWarning) -> None:
        """Display a coaching toast for a detected mistake."""
        self._show_toast(
            warning.icon,
            warning.title,
            f"{warning.explanation}  —  {warning.suggestion}",
            warning.color,
        )

    def push_ai_suggestion(self, text: str, is_ai: bool = False) -> None:
        """Forward an AI suggestion (from MainWindow) to the AI Coach panel."""
        self._ai_coach_page.push_suggestion(text, is_ai=is_ai)
        if is_ai:
            self._show_toast("🤖", "AI Koç Önerisi", text, _CYAN)

    def _show_toast(self, icon: str, title: str, body: str, color: str) -> None:
        toast = ToastNotification(self, icon, title, body, color)
        toast.show()

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self, state: object, extra: dict) -> None:
        """Call after every state change to synchronize the UI."""
        self._current_state = state          # stored for level-complete dialog
        self._ls.check_all(state, extra)
        self._xp_header.refresh()
        for pg in self._level_pages.values():
            pg.refresh()
        self._ach_page.refresh()
        self._ch_page.refresh()
        self._anal_page.refresh(state)
        current_entry = self._lb.current_entry() if self._lb else None
        self._lb_page.refresh(current_entry)
        self._ai_coach_page.refresh(state, extra, self._ls, lb=self._lb)
        self._update_sidebar_summary()
        self._update_nav_lock_icons()

    def _update_sidebar_summary(self) -> None:
        self._sidebar_xp_lbl.setText(f"⚡ {self._ls.xp} XP")
        icon = self._ls.current_level_icon
        name = self._ls.current_level_label
        self._sidebar_level_lbl.setText(f"{icon} {name}")

    def _update_nav_lock_icons(self) -> None:
        for i, (icon, label, key) in enumerate(self._NAV_ITEMS):
            if key not in self._ls.LEVEL_META:
                continue
            btn    = self._nav_btns[i]
            locked = not self._ls.is_level_unlocked(key)
            meta   = self._ls.LEVEL_META[key]
            prefix = "  🔒" if locked else f"  {meta[0]}"
            btn.setText(f"{prefix}  {meta[1]}")
