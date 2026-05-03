"""Main application window — full trading platform UI."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.analysis import FeatureBuilder, FeatureDataset, ForecastPoint, RegressionForecaster, TrendAnalyzer, TrendSummary
from src.data_processing import CleanedDataset, DataCleaner, DataLoader, DatasetInfo, LoadedDataset
from src.education import ASSET_INFO, GLOSSARY, TIPS, TOPICS, TUTORIAL_STEPS
from src.ai import AICoach, ContextBuilder, GeminiService
from src.learning import (
    LeaderboardManager,
    LearningExtra,
    LearningManager,
    MistakeDetector,
)

LearningSystem = LearningManager   # backwards-compat alias
from src.portfolio import HistoricalPriceFeed
from src.portfolio.portfolio import PortfolioState
from src.ui.learn_page import LearnPage
from src.ui.welcome_dialog import WelcomeDialog
from src.visualization.charts import ChartPlaceholder

# ── palette ───────────────────────────────────────────────────────────────────
_BG      = "#0b0f1a"
_SURF    = "#111827"
_SURF2   = "#1a2235"
_BORDER  = "#1e2d45"
_ACCENT  = "#2563eb"
_ACCH    = "#1d4ed8"
_GREEN   = "#10b981"
_RED     = "#ef4444"
_AMBER   = "#f59e0b"
_TEXT    = "#e2e8f0"
_TEXT2   = "#94a3b8"
_TEXT3   = "#64748b"
_TOPBAR  = "#060c18"


# ── small helpers ─────────────────────────────────────────────────────────────

def _lbl(text: str = "", *, obj: str = "", bold: bool = False,
         size: int = 0, color: str = "", align: Qt.AlignmentFlag | None = None,
         mono: bool = False) -> QLabel:
    w = QLabel(text)
    if obj:
        w.setObjectName(obj)
    f = QFont("Consolas") if mono else QFont()
    if bold:
        f.setBold(True)
    if size:
        f.setPointSize(size)
    w.setFont(f)
    if color:
        w.setStyleSheet(f"color:{color};")
    if align is not None:
        w.setAlignment(align)
    return w


def _btn(text: str, obj: str = "btnPrimary", *, h: int = 38, minw: int = 0) -> QPushButton:
    b = QPushButton(text)
    b.setObjectName(obj)
    b.setFixedHeight(h)
    if minw:
        b.setMinimumWidth(minw)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def _sep(vertical: bool = False) -> QFrame:
    s = QFrame()
    s.setFrameShape(QFrame.Shape.VLine if vertical else QFrame.Shape.HLine)
    s.setObjectName("sep")
    return s


def _card(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    f = QFrame()
    f.setObjectName("card")
    vl = QVBoxLayout(f)
    vl.setContentsMargins(16, 14, 16, 14)
    vl.setSpacing(10)
    if title:
        vl.addWidget(_lbl(title, obj="cardTitle"))
    return f, vl


def _compute_risk_label(state: "PortfolioState") -> dict:
    pv = state.portfolio_value
    if pv <= 0:
        return {"label": "—", "color": _TEXT3, "detail": "Portföy boş"}
    max_weight = max((p.market_value / pv * 100 for p in state.positions), default=0.0)
    upl_pct = state.total_unrealized_pnl / pv * 100 if pv > 0 else 0.0
    if max_weight >= 70 or upl_pct <= -15:
        return {"label": "YÜKSEK", "color": _RED,   "detail": f"En yüksek konsantrasyon %{max_weight:.0f}"}
    if max_weight >= 45 or upl_pct <= -7:
        return {"label": "ORTA",   "color": _AMBER, "detail": f"En yüksek konsantrasyon %{max_weight:.0f}"}
    return     {"label": "DÜŞÜK",  "color": _GREEN, "detail": f"Portföy dengeli"}
def _risk_from_volatility(volatility: float) -> dict:
    """
    CSV verisinden hesaplanan günlük volatiliteye göre risk sınıfı üretir.

    volatility değeri 0.025 ise yaklaşık %2.5 günlük oynaklık anlamına gelir.
    """
    vol_pct = volatility * 100

    if vol_pct < 1:
        return {
            "label": "Düşük",
            "color": _GREEN,
            "detail": f"{vol_pct:.2f}% oynaklık",
        }

    if vol_pct < 3:
        return {
            "label": "Orta",
            "color": _AMBER,
            "detail": f"{vol_pct:.2f}% oynaklık",
        }

    if vol_pct < 6:
        return {
            "label": "Yüksek",
            "color": _RED,
            "detail": f"{vol_pct:.2f}% oynaklık",
        }

    return {
        "label": "Çok Yüksek",
        "color": "#ff3060",
        "detail": f"{vol_pct:.2f}% oynaklık",
    }
def _fmt_price(price: float) -> str:
    """
    Küçük fiyatlı varlıkların 0.00 görünmesini engeller.
    """
    if price >= 100:
        return f"{price:,.2f}"
    if price >= 1:
        return f"{price:,.4f}"
    if price >= 0.01:
        return f"{price:,.6f}"
    return f"{price:,.8f}"
def _metric(title: str) -> tuple[QFrame, QLabel, QLabel]:
    box = QFrame()
    box.setObjectName("metricBox")
    vl = QVBoxLayout(box)
    vl.setContentsMargins(16, 12, 16, 12)
    vl.setSpacing(3)
    t = _lbl(title, obj="metricTitle")
    v = _lbl("—", obj="metricValue", bold=True, mono=True)
    s = _lbl("", obj="metricSub")
    vl.addWidget(t)
    vl.addWidget(v)
    vl.addWidget(s)
    return box, v, s


def _table(cols: list[str], obj: str = "tbl", stretch_cols: list[int] | None = None) -> QTableWidget:
    t = QTableWidget(0, len(cols))
    t.setObjectName(obj)
    t.setHorizontalHeaderLabels(cols)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setShowGrid(False)
    t.setAlternatingRowColors(True)
    
    hdr = t.horizontalHeader()
    stretch_cols = stretch_cols or []
    for i in range(len(cols)):
        mode = QHeaderView.ResizeMode.Stretch if i in stretch_cols else QHeaderView.ResizeMode.ResizeToContents
        hdr.setSectionResizeMode(i, mode)
    return t


def _item(text: str, color: str = _TEXT, bold: bool = False,
          align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter,
          mono: bool = False) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    it.setForeground(QColor(color))
    it.setTextAlignment(int(Qt.AlignmentFlag.AlignVCenter | align))
    if bold or mono:
        f = QFont("Consolas")
        f.setBold(bold)
        it.setFont(f)
    return it


def _ai_src(is_ai: bool) -> str:
    return "🤖 Gemini AI yanıtı" if is_ai else "📋 Kural tabanlı analiz"


# ── sidebar nav button ────────────────────────────────────────────────────────

class _NavBtn(QPushButton):
    def __init__(self, icon: str, label: str, idx: int) -> None:
        super().__init__()
        self._icon  = icon
        self._label = label
        self.nav_index = idx
        self.setObjectName("navBtn")
        self.setCheckable(True)
        self.setFixedHeight(62)
        self.setToolTip(label)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        checked = self.isChecked()
        hovered = self.underMouse()

        if checked:
            p.fillRect(self.rect(), QColor("#1a2030"))
            p.fillRect(0, 0, 3, self.height(), QColor(_ACCENT))
        elif hovered:
            p.fillRect(self.rect(), QColor("#111827"))

        color = _ACCENT if checked else (_TEXT2 if hovered else _TEXT3)
        p.setPen(QColor(color))

        f = QFont()
        f.setPointSize(17)
        p.setFont(f)
        p.drawText(self.rect().adjusted(0, -10, 0, -10), Qt.AlignmentFlag.AlignCenter, self._icon)

        f2 = QFont()
        f2.setPointSize(9)
        f2.setBold(checked)
        p.setFont(f2)
        p.setPen(QColor(_TEXT if checked else _TEXT3))
        p.drawText(self.rect().adjusted(0, 18, 0, 18), Qt.AlignmentFlag.AlignCenter, self._label)
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  MainWindow
# ══════════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self, state: PortfolioState | None = None, *,
                 db: "Database | None" = None,
                 user_id: int = 0,
                 username: str = "Demo",
                 session_id: str = "") -> None:
        super().__init__()
        self.state    = state or PortfolioState()
        self._db         = db
        self._user_id    = user_id
        self._username   = username
        self._session_id = session_id
        self._loader  = DataLoader()
        self._cleaner = DataCleaner()
        self._features = FeatureBuilder()
        self._trend   = TrendAnalyzer()
        self._fore    = RegressionForecaster()

        # ── auto-load data/raw/ on startup ────────────────────────────────────
        _raw_folder = Path(__file__).resolve().parents[2] / "data" / "raw"
        self._csv_datasets: dict[str, FeatureDataset] = {}
        _seed: dict[str, float] = {}
        _raw_loaded = self._loader.load_raw_folder(_raw_folder)
        for sym, raw_ds in _raw_loaded.items():
            try:
                cleaned_ds = self._cleaner.clean(raw_ds)
                feat_ds    = self._features.build(cleaned_ds)
                self._csv_datasets[sym] = feat_ds
                _seed[sym] = feat_ds.last_close
            except Exception:
                pass

        if not self._csv_datasets:
            raise RuntimeError(
                "data/raw klasöründe geçerli CSV verisi bulunamadı. "
                "Uygulama sadece Kaggle CSV verisiyle çalışacak şekilde ayarlandı."
            )

        self._feed = HistoricalPriceFeed(self._csv_datasets)
        self.state.simulation_status = "Geçmiş CSV verisiyle piyasa akışı başlatıldı"
        self.dataset_info: DatasetInfo | None = None
        self.cleaned:      CleanedDataset | None = None
        self.loaded_data:  LoadedDataset | None = None
        self.feature_data: FeatureDataset | None = None
        self.trend_summary: TrendSummary | None = None
        self.forecast:     list[ForecastPoint] = []

        self._order_side = "AL"       # "AL" | "SAT"
        self._prev_prices: dict[str, float] = {}
        self._tutorial_done: dict[str, bool] = {s["id"]: False for s in TUTORIAL_STEPS}
        self._tip_index = 0
        self._trade_count = 0   # tracks first buy / first sell for edu messages

        # ── Learning system ───────────────────────────────────────────────
        self._ls       = LearningSystem()
        self._extra    = LearningExtra(dashboard_visited=True)
        self._detector = MistakeDetector()
        self._lb       = LeaderboardManager()

        # ── AI Coach (hybrid rule-based + Gemini) ─────────────────────────
        self._gemini           = GeminiService()
        self._ctx_builder      = ContextBuilder(detector=self._detector)
        self._ai_coach         = AICoach(self._gemini, self._ctx_builder)
        self._last_ai_sugg     = ""
        self._last_ai_is_gemini = False

        self.setWindowTitle("Portfolio Simulator")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

        self.setStyleSheet(STYLESHEET)
        self._build_ui()
        self._connect_signals()

        # initialise price feed with current market prices and refresh
        self._prev_prices = self._feed.get_all()
        self.state.update_prices(self._feed.get_all())
        self._full_refresh()

        # market tick — every 3 s
        self._market_timer = QTimer(self)
        self._market_timer.timeout.connect(self._tick_market)
        self._market_timer.start(3000)

        # rotating tips — every 12 s
        self._tip_timer = QTimer(self)
        self._tip_timer.timeout.connect(self._rotate_tip)
        self._tip_timer.start(12000)

        # show welcome dialog after window is visible
        QTimer.singleShot(200, self._show_welcome)

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD Helpers
    # ══════════════════════════════════════════════════════════════════════════
    
    def _build_metric_row(self, layout: QHBoxLayout, metrics_info: list[tuple[str, str, str | None]]) -> None:
        """Helper to build repeated metric boxes dynamically."""
        for title, val_attr, sub_attr in metrics_info:
            box, v, s = _metric(title)
            setattr(self, val_attr, v)
            if sub_attr:
                setattr(self, sub_attr, s)
            layout.addWidget(box, 1)

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_topbar())
        outer.addWidget(_sep())

        body = QWidget()
        hl   = QHBoxLayout(body)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        hl.addWidget(self._build_sidebar())
        hl.addWidget(_sep(vertical=True))
        hl.addWidget(self._build_stack(), 1)
        outer.addWidget(body, 1)

        self.statusBar().setObjectName("statusBar")
        self.statusBar().showMessage("Hazir — piyasa simulasyonu aktif")

    # ── topbar ────────────────────────────────────────────────────────────────

    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(54)
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(22, 0, 22, 0)
        hl.setSpacing(0)

        logo_lbl = _lbl("◆  PortfolioSim", bold=True, size=14, color=_TEXT)
        hl.addWidget(logo_lbl)
        hl.addStretch()

        for label, attr_v, attr_s in (
            ("PORTFOY",   "h_value", "h_value_s"),
            ("TOPLAM K/Z","h_pl",    "h_pl_s"),
            ("NAKIT",     "h_cash",  "h_cash_s"),
            ("POZISYON",  "h_pos",   "h_pos_s"),
        ):
            v = _lbl("—", bold=True, mono=True, size=13)
            s = _lbl(label, color=_TEXT3)
            s.setStyleSheet(f"color:{_TEXT3}; font-size:9px; letter-spacing:1px;")
            setattr(self, attr_v, v)
            setattr(self, attr_s, s)
            cell = QVBoxLayout()
            cell.setSpacing(1)
            cell.setContentsMargins(20, 4, 20, 4)
            cell.addWidget(s)
            cell.addWidget(v)
            hl.addLayout(cell)
            hl.addWidget(_sep(vertical=True))

        hl.addStretch()
        return bar

    # ── sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> QFrame:
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(82)
        vl = QVBoxLayout(side)
        vl.setContentsMargins(0, 10, 0, 0)
        vl.setSpacing(0)

        pages = [
            ("◎", "Özet", 0),
            ("⇄", "İşlem", 1),
            ("≡", "Geçmiş", 2),
            ("⊙", "Analiz", 3),
            ("📚", "Öğren", 4),
        ]
        self._nav: list[_NavBtn] = []
        for icon, lbl, idx in pages:
            btn = _NavBtn(icon, lbl, idx)
            btn.clicked.connect(lambda _c, i=idx: self._goto(i))
            self._nav.append(btn)
            vl.addWidget(btn)

        self._nav[0].setChecked(True)
        vl.addStretch()

        # ── user card (bottom of sidebar) ─────────────────────────────────────
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtCore import QPoint

        user_card = QPushButton()
        user_card.setObjectName("userCard")
        user_card.setFixedHeight(72)
        user_card.setCursor(Qt.CursorShape.PointingHandCursor)
        user_card.setToolTip("Hesap menüsü")

        card_vl = QVBoxLayout(user_card)
        card_vl.setContentsMargins(0, 8, 0, 8)
        card_vl.setSpacing(2)

        avatar_lbl = QLabel("👤")
        avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_lbl.setStyleSheet(f"""
            font-size: 20px;
            color: white;
            background: {_ACCENT};
            border-radius: 16px;
            min-width: 32px;
            max-width: 32px;
            min-height: 32px;
            max-height: 32px;
        """)

        name_lbl = QLabel(self._username)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet(f"""
            color: {_TEXT};
            font-size: 10px;
            font-weight: 700;
            max-width: 78px;
        """)

        card_vl.addWidget(avatar_lbl, alignment=Qt.AlignmentFlag.AlignHCenter)
        card_vl.addWidget(name_lbl)

        user_card.setStyleSheet(f"""
            QPushButton#userCard {{
                background: transparent;
                border: none;
                border-top: 1px solid {_BORDER};
            }}
            QPushButton#userCard:hover {{
                background: {_SURF2};
            }}
        """)

        def _show_user_menu() -> None:
            menu = QMenu(self)
            menu.setStyleSheet(f"""
                QMenu {{
                    background: {_SURF};
                    border: 1px solid {_BORDER};
                    border-radius: 8px;
                    color: {_TEXT};
                    font-size: 13px;
                    padding: 4px;
                }}
                QMenu::item {{
                    padding: 8px 20px;
                    border-radius: 5px;
                }}
                QMenu::item:selected {{
                    background: #3f0000;
                    color: #ef4444;
                }}
                QMenu::separator {{
                    height: 1px;
                    background: {_BORDER};
                    margin: 4px 8px;
                }}
            """)
            info_action = menu.addAction(f"👤  {self._username}")
            info_action.setEnabled(False)
            menu.addSeparator()
            logout_action = menu.addAction("🚪  Çıkış Yap")
            logout_action.setEnabled(True)

            # Show menu above the button
            pos = user_card.mapToGlobal(QPoint(0, -menu.sizeHint().height() - 4))
            chosen = menu.exec(pos)
            if chosen == logout_action:
                self._logout()

        user_card.clicked.connect(_show_user_menu)
        vl.addWidget(user_card)
        return side

    def _goto(self, idx: int) -> None:
        for b in self._nav:
            b.setChecked(b.nav_index == idx)
            b.update()
        self._stack.setCurrentIndex(idx)
        # Track page visits for learning extra state
        if idx == 0:
            self._extra.dashboard_visited = True
        elif idx == 2:
            self._extra.history_visited = True
        elif idx == 3 and self._extra.analysis_run:
            # User is viewing analysis page after a simulation — they see the forecast
            self._extra.forecast_viewed = True
        # Refresh learning system on every navigation
        if hasattr(self, "_learn_page"):
            self._learn_page.refresh(self.state, self._extra.to_dict())

    # ── stack ─────────────────────────────────────────────────────────────────

    def _build_stack(self) -> QStackedWidget:
        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_dashboard())
        self._stack.addWidget(self._page_trade())
        self._stack.addWidget(self._page_history())
        self._stack.addWidget(self._page_analysis())
        self._learn_page = LearnPage(
            self._ls, self._goto, self._on_calc_used,
            lb_manager=self._lb,
            save_session_cb=self._save_leaderboard_session,
            ai_coach=self._ai_coach,
            feature_datasets=self._csv_datasets,
        )
        self._stack.addWidget(self._learn_page)
        return self._stack

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 0 — DASHBOARD
    # ══════════════════════════════════════════════════════════════════════════

    def _page_dashboard(self) -> QWidget:
        page = QWidget()
        vl   = QVBoxLayout(page)
        vl.setContentsMargins(22, 18, 22, 16)
        vl.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.addWidget(_lbl("Portföy Özeti", bold=True, size=15, color=_TEXT))
        title_row.addStretch()
        self.d_risk_badge = QLabel("Risk: —")
        self.d_risk_badge.setStyleSheet(
            f"color:{_TEXT3}; background:{_SURF2}; border:1px solid {_BORDER}; "
            f"border-radius:5px; font-size:11px; font-weight:700; padding:3px 10px;"
        )
        title_row.addWidget(self.d_risk_badge)
        vl.addLayout(title_row)

        # ── 5 metric boxes ────────────────────────────────────────────────────
        row = QHBoxLayout()
        row.setSpacing(10)
        self._build_metric_row(row, [
            ("PORTFÖY DEĞERİ", "d_pv", "d_pv_s"),
            ("TOPLAM K/Z", "d_pl", "d_pl_s"),
            ("GERÇEKLEŞMEMİŞ K/Z", "d_upl", "d_upl_s"),
            ("GERÇEKLEŞMİŞ K/Z", "d_rpl", "d_rpl_s"),
            ("ÖĞRENME SEVİYESİ", "d_xp_val", "d_level_sub")
        ])
        vl.addLayout(row)

        # ── Center: chart + right column ──────────────────────────────────────
        center = QHBoxLayout()
        center.setSpacing(12)

        chart_frm, chart_vl = _card("PORTFÖY DEĞER GRAFİĞİ")
        self.d_chart = ChartPlaceholder("Portfoy degeri", "line")
        self.d_chart.setMinimumHeight(200)
        chart_vl.addWidget(self.d_chart, 1)
        center.addWidget(chart_frm, 3)

        right = QVBoxLayout()
        right.setSpacing(10)

        wl_frm, wl_vl = _card("PİYASA (CANLI)")
        self.d_mini_wl = _table(["Sembol", "Fiyat", "Değ.%"], "tbl", stretch_cols=[1])
        self.d_mini_wl.setMaximumHeight(180)
        wl_vl.addWidget(self.d_mini_wl)
        right.addWidget(wl_frm)

        rec_frm, rec_vl = _card("SON İŞLEMLER")
        self.d_recent = _table(["Zaman", "İşlem", "Sembol", "Tutar TL"], "tbl", stretch_cols=[0, 1, 2, 3])
        self.d_recent.setMaximumHeight(140)
        rec_vl.addWidget(self.d_recent)
        right.addWidget(rec_frm)

        center.addLayout(right, 2)
        vl.addLayout(center, 1)

        # ── Bottom: learning panel + AI suggestion + shortcuts ────────────────
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        learn_frm, learn_vl = _card()
        learn_hdr = QHBoxLayout()
        learn_hdr.addWidget(_lbl("ÖĞRENME DURUMU", obj="cardTitle"))
        learn_hdr.addStretch()
        self.d_learn_goto_btn = _btn("→ Öğren", "btnAmber", h=26)
        self.d_learn_goto_btn.clicked.connect(lambda: self._goto(4))
        learn_hdr.addWidget(self.d_learn_goto_btn)
        learn_vl.addLayout(learn_hdr)

        xp_row = QHBoxLayout()
        xp_row.setSpacing(8)
        self.d_level_badge = QLabel("🌱 Başlangıç")
        self.d_level_badge.setStyleSheet(
            f"color:{_ACCENT}; background:{_ACCENT}15; border:1px solid {_ACCENT}44; "
            f"border-radius:5px; font-size:11px; font-weight:700; padding:2px 8px;"
        )
        self.d_xp_txt = QLabel("0 XP")
        self.d_xp_txt.setStyleSheet(f"color:{_AMBER}; font-size:12px; font-weight:800; font-family:Consolas;")
        xp_row.addWidget(self.d_level_badge)
        xp_row.addStretch()
        xp_row.addWidget(self.d_xp_txt)
        learn_vl.addLayout(xp_row)

        self.d_xp_prog = QProgressBar()
        self.d_xp_prog.setRange(0, 100)
        self.d_xp_prog.setValue(0)
        self.d_xp_prog.setTextVisible(False)
        self.d_xp_prog.setFixedHeight(7)
        self.d_xp_prog.setStyleSheet(
            f"QProgressBar {{background:{_SURF2}; border:none; border-radius:3px;}}"
            f"QProgressBar::chunk {{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {_ACCENT},stop:1 #10b981); border-radius:3px;}}"
        )
        learn_vl.addWidget(self.d_xp_prog)

        task_frm = QFrame()
        task_frm.setStyleSheet(f"background:{_SURF2}; border:1px solid {_BORDER}; border-radius:7px;")
        task_hl = QHBoxLayout(task_frm)
        task_hl.setContentsMargins(12, 8, 12, 8)
        task_hl.setSpacing(10)
        self.d_task_icon_lbl = QLabel("🎯")
        self.d_task_icon_lbl.setStyleSheet("font-size:20px;")
        self.d_task_icon_lbl.setFixedWidth(28)
        
        task_col = QVBoxLayout()
        task_col.setSpacing(2)
        self.d_task_title_lbl = QLabel("Aktif görev yükleniyor…")
        self.d_task_title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:12px; font-weight:700;")
        self.d_task_obj_lbl = QLabel("")
        self.d_task_obj_lbl.setStyleSheet(f"color:{_TEXT2}; font-size:10px;")
        self.d_task_obj_lbl.setWordWrap(True)
        task_col.addWidget(self.d_task_title_lbl)
        task_col.addWidget(self.d_task_obj_lbl)
        
        task_hl.addWidget(self.d_task_icon_lbl)
        task_hl.addLayout(task_col, 1)
        self.d_task_nav_btn = _btn("→", "btnPrimary", h=28)
        self.d_task_nav_btn.setFixedWidth(36)
        self.d_task_nav_btn.setToolTip("Göreve git")
        task_hl.addWidget(self.d_task_nav_btn)
        learn_vl.addWidget(task_frm)
        bottom.addWidget(learn_frm, 3)

        ai_frm, ai_vl = _card()
        ai_hdr = QHBoxLayout()
        ai_hdr.addWidget(_lbl("AI KOÇ ÖNERİSİ", obj="cardTitle"))
        ai_hdr.addStretch()
        self.d_ai_status_dot = QLabel("●")
        self.d_ai_status_dot.setStyleSheet(f"color:{_TEXT3}; font-size:11px;")
        ai_hdr.addWidget(self.d_ai_status_dot)
        ai_vl.addLayout(ai_hdr)

        self.d_ai_sugg_lbl = QLabel("Henüz öneri yok. Bir işlem gerçekleştirin.")
        self.d_ai_sugg_lbl.setStyleSheet(f"color:{_TEXT}; font-size:12px; line-height:1.4;")
        self.d_ai_sugg_lbl.setWordWrap(True)
        ai_vl.addWidget(self.d_ai_sugg_lbl, 1)

        self.d_ai_source_lbl = QLabel("")
        self.d_ai_source_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:10px;")
        ai_vl.addWidget(self.d_ai_source_lbl)

        d_ai_ask_btn = _btn("🤖 AI Koç'a Git", "btnSecondary", h=30)
        d_ai_ask_btn.clicked.connect(lambda: self._goto(4))
        ai_vl.addWidget(d_ai_ask_btn)
        bottom.addWidget(ai_frm, 3)

        act = QVBoxLayout()
        act.setSpacing(8)
        sb1 = _btn("⇄  İşlem Yap",   "btnPrimary",   h=44, minw=160)
        sb2 = _btn("📚  Öğren",       "btnAmber",     h=44, minw=160)
        sb3 = _btn("🤖  AI Koç",      "btnSecondary", h=44, minw=160)
        sb4 = _btn("⊙  Analiz Yap",  "btnSecondary", h=44, minw=160)
        sb1.clicked.connect(lambda: self._goto(1))
        sb2.clicked.connect(lambda: self._goto(4))
        sb3.clicked.connect(lambda: self._goto(4))
        sb4.clicked.connect(lambda: self._goto(3))
        act.addStretch()
        for b in (sb1, sb2, sb3, sb4): act.addWidget(b)
        act.addStretch()
        bottom.addLayout(act)
        
        vl.addLayout(bottom)
        return page

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — İŞLEM (TRADE)
    # ══════════════════════════════════════════════════════════════════════════

    def _page_trade(self) -> QWidget:
        page = QWidget()
        hl   = QHBoxLayout(page)
        hl.setContentsMargins(16, 14, 16, 14)
        hl.setSpacing(12)
        hl.addWidget(self._trade_left(),  3)
        hl.addWidget(self._trade_right(), 2)
        return page

    def _trade_left(self) -> QWidget:
        w  = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(10)

        wl_frm, wl_vl = _card("PIYASA  —  Simüle Fiyatlar (3 sn'de güncellenir)  ·  Bir satıra tıklayarak işlem yapın")
        self.wl_table = _table(
            ["Sembol", "İsim", "Fiyat (TL)", "Gün Değ. %", "Risk Seviyesi", "Açıklama"], "tbl", stretch_cols=[5]
        )
        self.wl_table.setToolTip(
            "Piyasa fiyatları her 3 saniyede bir güncellenir.\nBir satıra tıklayarak o varlık için otomatik işlem formu açılır."
        )
        self.wl_table.setMinimumHeight(240)
        wl_vl.addWidget(self.wl_table)
        vl.addWidget(wl_frm, 3)

        pos_frm, pos_vl = _card("ACIK POZISYONLAR")
        self.pos_table = _table(
            ["Sembol", "Miktar", "Ort. Maliyet", "Piyasa Fiy.", "Deger", "K/Z (TL)", "K/Z %"], "tbl", stretch_cols=[2,3,4,5,6]
        )
        pos_vl.addWidget(self.pos_table, 1)

        pos_btns = QHBoxLayout()
        pos_btns.setSpacing(8)
        self.btn_close_pos = _btn("Pozisyonu Kapat (Tümü)", "btnDanger", h=34)
        self.btn_close_pos.setToolTip("Seçili pozisyonun tamamını piyasa fiyatından sat")
        pos_btns.addStretch()
        pos_btns.addWidget(self.btn_close_pos)
        pos_vl.addLayout(pos_btns)
        vl.addWidget(pos_frm, 2)
        return w

    def _trade_right(self) -> QWidget:
        w  = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(10)

        self.t_task_banner = QFrame()
        self.t_task_banner.setObjectName("card")
        self.t_task_banner.setStyleSheet(f"QFrame#card{{background:{_ACCENT}18; border:1px solid {_ACCENT}44; border-radius:8px;}}")
        t_hl = QHBoxLayout(self.t_task_banner)
        t_hl.setContentsMargins(12, 8, 12, 8)
        t_hl.setSpacing(10)
        self.t_task_icon = QLabel("🎯")
        self.t_task_icon.setStyleSheet("font-size:18px;")
        t_col = QVBoxLayout()
        t_col.setSpacing(1)
        self.t_task_title = QLabel("Görev: —")
        self.t_task_title.setStyleSheet(f"color:{_TEXT}; font-size:11px; font-weight:700;")
        self.t_task_obj = QLabel("")
        self.t_task_obj.setStyleSheet(f"color:{_TEXT2}; font-size:10px;")
        self.t_task_obj.setWordWrap(True)
        t_col.addWidget(self.t_task_title)
        t_col.addWidget(self.t_task_obj)
        t_hl.addWidget(self.t_task_icon)
        t_hl.addLayout(t_col, 1)
        goto_learn = _btn("Öğren", "btnAmber", h=26)
        goto_learn.setFixedWidth(64)
        goto_learn.clicked.connect(lambda: self._goto(4))
        t_hl.addWidget(goto_learn)
        vl.addWidget(self.t_task_banner)

        vl.addWidget(self._order_form_card())
        vl.addWidget(self._account_summary_card())
        return w

    def _order_form_card(self) -> QFrame:
        frm, vl = _card("iSLEM EMRI")

        side_row = QHBoxLayout()
        side_row.setSpacing(0)
        self.btn_buy_mode  = _btn("  ALIŞ  ", "sideActive", h=44)
        self.btn_sell_mode = _btn("  SATIŞ  ", "sideInactive", h=44)
        self.btn_buy_mode.clicked.connect(lambda: self._set_side("AL"))
        self.btn_sell_mode.clicked.connect(lambda: self._set_side("SAT"))
        side_row.addWidget(self.btn_buy_mode,  1)
        side_row.addWidget(self.btn_sell_mode, 1)
        vl.addLayout(side_row)
        vl.addSpacing(6)

        def _row(lbl_txt: str, widget: QWidget) -> None:
            hl = QHBoxLayout()
            hl.setSpacing(8)
            lb = _lbl(lbl_txt, color=_TEXT3)
            lb.setFixedWidth(86)
            hl.addWidget(lb)
            hl.addWidget(widget, 1)
            vl.addLayout(hl)

        self.o_symbol = QLineEdit()
        self.o_symbol.setPlaceholderText("BTC, ETH, AAPL …")
        self.o_symbol.setObjectName("formInput")
        self.o_symbol.setMaxLength(8)

        self.o_qty = QDoubleSpinBox()
        self.o_qty.setRange(0.0001, 1_000_000)
        self.o_qty.setDecimals(6)
        self.o_qty.setObjectName("formInput")
        self.o_qty.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)

        self.o_price = QDoubleSpinBox()
        self.o_price.setRange(0.01, 100_000_000)
        self.o_price.setDecimals(2)
        self.o_price.setPrefix("TL ")
        self.o_price.setObjectName("formInput")
        self.o_price.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)

        self.o_total_lbl = _lbl("—  TL", bold=True, mono=True, size=14, color=_TEXT)
        self.o_avail_lbl = _lbl("", color=_TEXT3)

        _row("Sembol",   self.o_symbol)
        _row("Miktar",   self.o_qty)
        _row("Fiyat",    self.o_price)

        vl.addSpacing(4)
        total_row = QHBoxLayout()
        total_row.addWidget(_lbl("Toplam:", color=_TEXT3, bold=True))
        total_row.addStretch()
        total_row.addWidget(self.o_total_lbl)
        vl.addLayout(total_row)

        avail_row = QHBoxLayout()
        avail_row.addWidget(_lbl("Kullanılabilir:", color=_TEXT3))
        avail_row.addStretch()
        avail_row.addWidget(self.o_avail_lbl)
        vl.addLayout(avail_row)

        vl.addSpacing(8)
        self.btn_execute = _btn("İŞLEM GERÇEKLEŞTIR", "btnExecute", h=50)
        self.btn_execute.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        vl.addWidget(self.btn_execute)

        reset_row = QHBoxLayout()
        self.btn_max   = _btn("Maksimum", "btnGhost", h=30)
        self.btn_half  = _btn("Yarı",     "btnGhost", h=30)
        self.btn_reset = _btn("Temizle",  "btnGhost", h=30)
        for b in (self.btn_max, self.btn_half, self.btn_reset): reset_row.addWidget(b, 1)
        vl.addLayout(reset_row)
        return frm

    def _account_summary_card(self) -> QFrame:
        frm, vl = _card("HESAP ÖZETİ")

        def _kv(k: str, attr: str, color: str = _TEXT) -> None:
            hl = QHBoxLayout()
            hl.setSpacing(4)
            hl.addWidget(_lbl(k, color=_TEXT3))
            hl.addStretch()
            lbl = _lbl("—", bold=True, mono=True, color=color)
            setattr(self, attr, lbl)
            hl.addWidget(lbl)
            vl.addLayout(hl)

        _kv("Nakit Bakiye",       "acc_cash")
        _kv("Portföy Değeri",     "acc_pv")
        _kv("Toplam K/Z",         "acc_tpl")
        _kv("Gerçekleşmiş K/Z",   "acc_rpl")
        _kv("Gerçekleşmemiş K/Z", "acc_upl")
        vl.addWidget(_sep())
        _kv("Kazanma Oranı",   "acc_winrate")
        _kv("Risk Seviyesi",   "acc_risk")
        _kv("Toplam İşlem",    "acc_trade_count")

        vl.addSpacing(6)
        self.btn_report = _btn("⬇  Rapor Kaydet", "btnGhost", h=34)
        vl.addWidget(self.btn_report)
        return frm

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — GEÇMİŞ (HISTORY)
    # ══════════════════════════════════════════════════════════════════════════

    def _page_history(self) -> QWidget:
        page = QWidget()
        vl   = QVBoxLayout(page)
        vl.setContentsMargins(22, 18, 22, 16)
        vl.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.addWidget(_lbl("İşlem Geçmişi", bold=True, size=15, color=_TEXT))
        title_row.addStretch()
        self.hist_filter = QLineEdit()
        self.hist_filter.setPlaceholderText("Sembol ile filtrele …")
        self.hist_filter.setObjectName("formInput")
        self.hist_filter.setFixedWidth(200)
        title_row.addWidget(self.hist_filter)
        vl.addLayout(title_row)

        frm, fl = _card()
        self.hist_table = _table(
            ["#", "Tarih / Saat", "İşlem", "Sembol", "Miktar", "Fiyat (TL)", "Toplam (TL)"], "tbl", stretch_cols=[4,5,6]
        )
        fl.addWidget(self.hist_table, 1)

        top_stats = QHBoxLayout()
        top_stats.setSpacing(10)
        self._build_metric_row(top_stats, [
            ("TOPLAM İŞLEM", "hi_total", None),
            ("TOPLAM ALIM", "hi_buy", None),
            ("TOPLAM SATIM", "hi_sell", None),
            ("TOPLAM HACİM (TL)", "hi_volume", None)
        ])
        vl.addLayout(top_stats)

        bot_stats = QHBoxLayout()
        bot_stats.setSpacing(10)
        self._build_metric_row(bot_stats, [
            ("KAZANMA ORANI", "hi_winrate", "hi_winrate_sub"),
            ("KÂRLI SATIMLAR", "hi_profitsell", None),
            ("KAZANILAN XP", "hi_xp_earned", None),
            ("RİSK SKORU", "hi_risk", "hi_risk_sub")
        ])
        vl.addLayout(bot_stats)
        vl.addWidget(frm, 1)
        return page

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3 — VERİ
    # ══════════════════════════════════════════════════════════════════════════

    def _page_data(self) -> QWidget:
        page = QWidget()
        vl   = QVBoxLayout(page)
        vl.setContentsMargins(22, 18, 22, 16)
        vl.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.addWidget(_lbl("Veri İşleme", bold=True, size=15, color=_TEXT))
        title_row.addStretch()
        self.btn_load_csv = _btn("⬆  CSV Yukle", "btnPrimary", h=38, minw=150)
        title_row.addWidget(self.btn_load_csv)
        vl.addLayout(title_row)
        vl.addWidget(_lbl("CSV dosyasını yükleyin; kolon haritası ve metadata otomatik analiz edilir.", color=_TEXT3))

        stat_row = QHBoxLayout()
        stat_row.setSpacing(10)
        self._build_metric_row(stat_row, [
            ("DOSYA ADI", "dv_file", None),
            ("SATIR SAYISI", "dv_rows", None),
            ("TARIH KOLONU", "dv_date", None),
            ("FIYAT KOLONLARI", "dv_price", None)
        ])
        vl.addLayout(stat_row)

        frm, fl = _card("KOLON HARiTASI")
        self.dv_table = _table(["Kolon Adı", "Tespit Edilen Rol", "Örnek"], "tbl", stretch_cols=[0, 2])
        fl.addWidget(self.dv_table)
        self.dv_status = _lbl("Henüz CSV seçilmedi. 'CSV Yükle' butonunu kullanın.", color=_TEXT3)
        self.dv_status.setWordWrap(True)
        fl.addWidget(self.dv_status)
        vl.addWidget(frm, 1)
        return page

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 4 — ANALİZ
    # ══════════════════════════════════════════════════════════════════════════

    def _page_analysis(self) -> QWidget:
        page = QWidget()
        vl   = QVBoxLayout(page)
        vl.setContentsMargins(22, 18, 22, 16)
        vl.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.addWidget(_lbl("Analiz Modülü", bold=True, size=15, color=_TEXT))
        title_row.addStretch()

        self.an_start = QDateEdit(QDate(2022, 1, 1))
        self.an_start.setCalendarPopup(True)
        self.an_start.setObjectName("formInput")
        self.an_start.setFixedWidth(120)

        self.an_end = QDateEdit(QDate(2022, 12, 31))
        self.an_end.setCalendarPopup(True)
        self.an_end.setObjectName("formInput")
        self.an_end.setFixedWidth(120)

        self.btn_sim = _btn("▶  Senaryo Simülasyonu", "btnSuccess", h=38, minw=190)
        self.btn_ai_analysis = _btn("🤖 AI Analizi", "btnSecondary", h=38, minw=130)
        title_row.addWidget(_lbl("Tarih:", color=_TEXT3))
        title_row.addWidget(self.an_start)
        title_row.addWidget(_lbl("→", color=_TEXT3))
        title_row.addWidget(self.an_end)
        title_row.addSpacing(10)
        title_row.addWidget(self.btn_sim)
        title_row.addWidget(self.btn_ai_analysis)
        vl.addLayout(title_row)
        vl.addWidget(_lbl("Mevcut pozisyonları seçilen tarih aralığında projekte ederek senaryo analizi yapar.", color=_TEXT3))

        stat_row = QHBoxLayout()
        stat_row.setSpacing(10)
        self._build_metric_row(stat_row, [
            ("TREND YÖNÜ", "an_dir", None),
            ("DEĞİŞİM %", "an_chg", None),
            ("VOLATİLİTE %", "an_vol", None),
            ("SONRAKİ TAHMİN", "an_next", None)
        ])
        vl.addLayout(stat_row)

        center = QHBoxLayout()
        center.setSpacing(12)

        an_chart_frm, an_chart_vl = _card("SENARYO GRAFİĞİ")
        self.an_chart = ChartPlaceholder("Senaryo sonucu bekleniyor", "line")
        self.an_chart.setMinimumHeight(200)
        an_chart_vl.addWidget(self.an_chart, 1)
        center.addWidget(an_chart_frm, 3)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        fore_frm, fore_vl = _card("TAHMİN NOKTALARI")
        self.an_table = _table(["Adım", "Beklenen Değer (TL)", "Fark"], "tbl", stretch_cols=[0, 1, 2])
        fore_vl.addWidget(self.an_table, 1)
        self.an_status = _lbl("", color=_TEXT3)
        self.an_status.setWordWrap(True)
        fore_vl.addWidget(self.an_status)
        right_col.addWidget(fore_frm, 2)

        ai_frm = QFrame()
        ai_frm.setObjectName("card")
        ai_frm.setStyleSheet(f"QFrame#card{{background:{_SURF2}; border:1px solid {_BORDER}; border-radius:8px;}}")
        ai_vl = QVBoxLayout(ai_frm)
        ai_vl.setContentsMargins(14, 12, 14, 12)
        ai_vl.setSpacing(6)
        ai_hdr = QHBoxLayout()
        ai_hdr.addWidget(_lbl("🤖 AI KOÇUN YORUMU", obj="cardTitle"))
        ai_hdr.addStretch()
        self.an_ai_spinner = QLabel("")
        self.an_ai_spinner.setStyleSheet(f"color:{_TEXT3}; font-size:10px;")
        ai_hdr.addWidget(self.an_ai_spinner)
        ai_vl.addLayout(ai_hdr)
        self.an_ai_lbl = QLabel("Simülasyonu çalıştırdıktan sonra 'AI Analizi' butonuna basın.")
        self.an_ai_lbl.setStyleSheet(f"color:{_TEXT}; font-size:12px; line-height:1.5;")
        self.an_ai_lbl.setWordWrap(True)
        ai_vl.addWidget(self.an_ai_lbl, 1)
        self.an_ai_source = QLabel("")
        self.an_ai_source.setStyleSheet(f"color:{_TEXT3}; font-size:10px;")
        ai_vl.addWidget(self.an_ai_source)
        right_col.addWidget(ai_frm, 1)

        center.addLayout(right_col, 2)
        vl.addLayout(center, 1)
        return page

    # ══════════════════════════════════════════════════════════════════════════
    # SIGNALS, EVENT HANDLERS & REFRESH LOGIC (Kept As-Is Functionally)
    # ══════════════════════════════════════════════════════════════════════════

    def _connect_signals(self) -> None:
        self.wl_table.cellClicked.connect(self._wl_row_clicked)
        self.btn_close_pos.clicked.connect(self._close_position)
        self.o_symbol.textChanged.connect(self._fill_market_price)
        self.o_qty.valueChanged.connect(self._update_order_total)
        self.o_price.valueChanged.connect(self._update_order_total)
        self.btn_max.clicked.connect(self._fill_max)
        self.btn_half.clicked.connect(self._fill_half)
        self.btn_reset.clicked.connect(self._reset_form)
        self.btn_execute.clicked.connect(self._execute_order)
        self.hist_filter.textChanged.connect(self._refresh_history)
        # data
        #self.btn_load_csv.clicked.connect(self._load_csv)
        # analysis
        self.btn_sim.clicked.connect(self._run_scenario)
        self.btn_ai_analysis.clicked.connect(self._fire_analysis_ai)
        self.btn_report.clicked.connect(self._save_report)

    def _tick_market(self) -> None:
        self._prev_prices = self._feed.get_all()
        prices = self._feed.tick()
        self.state.update_prices(prices)

        self._sync_order_price_with_market()

        self._refresh_topbar()
        self._refresh_watchlist()
        self._refresh_positions()
        self._refresh_dashboard_metrics()
        self._refresh_account_summary()
    def _sync_order_price_with_market(self) -> None:
        """
        İşlem formunda seçili sembol varsa fiyat alanını güncel piyasa fiyatıyla eşitler.
        Böylece kullanıcı eski fiyattan işlem yapmaz.
        """
        symbol = self.o_symbol.text().strip().upper()

        if not symbol:
            return

        current_price = self._feed.get_price(symbol)

        if current_price <= 0:
            return

        self.o_price.setValue(current_price)


    # ══════════════════════════════════════════════════════════════════════════
    # ORDER FORM INTERACTIONS
    # ══════════════════════════════════════════════════════════════════════════

    def _set_side(self, side: str) -> None:
        self._order_side = side
        is_buy = side == "AL"
        self.btn_buy_mode.setObjectName("sideActive"   if is_buy  else "sideInactive")
        self.btn_sell_mode.setObjectName("sideInactive" if is_buy else "sideActive")
        for b in (self.btn_buy_mode, self.btn_sell_mode):
            b.style().unpolish(b)
            b.style().polish(b)
        self.btn_execute.setObjectName("btnExecuteBuy" if is_buy else "btnExecuteSell")
        self.btn_execute.style().unpolish(self.btn_execute)
        self.btn_execute.style().polish(self.btn_execute)
        self._update_order_total()

    def _fill_market_price(self, text: str) -> None:
        sym = text.strip().upper()
        price = self._feed.get_price(sym)
        if price > 0:
            self.o_price.blockSignals(True)
            self.o_price.setValue(price)
            self.o_price.blockSignals(False)
        self._update_order_total()

    def _update_order_total(self) -> None:
        qty   = self.o_qty.value()
        price = self.o_price.value()
        total = qty * price
        self.o_total_lbl.setText(f"TL {total:,.2f}")

        if self._order_side == "AL":
            self.o_avail_lbl.setText(f"Nakit: TL {self.state.cash:,.2f}")
        else:
            sym = self.o_symbol.text().strip().upper()
            pos = self.state._find(sym)
            qty_held = pos.quantity if pos else 0.0
            self.o_avail_lbl.setText(f"{sym} miktar: {qty_held:,.6g}")

    def _fill_max(self) -> None:
        price = self.o_price.value()
        if price <= 0:
            return
        if self._order_side == "AL":
            max_qty = self.state.cash / price
        else:
            sym = self.o_symbol.text().strip().upper()
            pos = self.state._find(sym)
            max_qty = pos.quantity if pos else 0.0
        self.o_qty.setValue(max(max_qty, 0.0001))

    def _fill_half(self) -> None:
        self._fill_max()
        self.o_qty.setValue(self.o_qty.value() / 2)

    def _reset_form(self) -> None:
        self.o_symbol.clear()
        self.o_qty.setValue(self.o_qty.minimum())
        self.o_price.setValue(self.o_price.minimum())
        self.o_symbol.setFocus()

    def _wl_row_clicked(self, row: int, _col: int) -> None:
        sym_item = self.wl_table.item(row, 0)
        if not sym_item:
            return
        sym   = sym_item.text().strip()
        price = self._feed.get_price(sym)
        self.o_symbol.blockSignals(True)
        self.o_symbol.setText(sym)
        self.o_symbol.blockSignals(False)
        self.o_price.blockSignals(True)
        self.o_price.setValue(price)
        self.o_price.blockSignals(False)
        self._update_order_total()
        self._goto(1)

    def _execute_order(self) -> None:
        sym        = self.o_symbol.text().strip().upper()
        qty        = self.o_qty.value()
        price      = self.o_price.value()
        cash_before = self.state.cash

        try:
            if self._order_side == "AL":
                trade = self.state.execute_buy(sym, qty, price)
                self._trade_count += 1
                self._extra.user_buy_count    += 1
                self._extra.max_single_buy_tl  = max(self._extra.max_single_buy_tl, trade.total)

                self._show_warnings(
                    self._detector.check_after_buy(self.state, sym, trade.total, cash_before)
                    + self._detector.check_portfolio_health(self.state)
                )

                action_desc = f"Bought {sym} TL {trade.total:,.0f}"
                self._fire_ai_suggestion(action_desc)

                if self._trade_count == 1:
                    msg = (f"Tebrikler! İlk alımınız gerçekleşti: {trade.quantity:.6g} {sym} @ TL {trade.price:,.2f} · "
                           f"Şimdi 'Özet' sayfasında K/Z değerinin nasıl değiştiğini izleyin!")
                else:
                    info = ASSET_INFO.get(sym, {})
                    risk = info.get("risk", "")
                    tip  = f"  ·  Risk: {risk}" if risk else ""
                    msg  = f"Alım: {trade.quantity:.6g} {sym} @ TL {trade.price:,.2f}  ←  TL {trade.total:,.2f}{tip}"
            else:
                pos = self.state._find(sym)
                avg_cost_before = pos.avg_cost if pos else 0.0
                is_profitable   = bool(pos and price > pos.avg_cost)

                trade = self.state.execute_sell(sym, qty, price)
                self._extra.user_sell_count += 1
                if is_profitable:
                    self._extra.profitable_sell_count += 1

                self._show_warnings(
                    self._detector.check_after_sell(self.state, sym, price, avg_cost_before)
                    + self._detector.check_portfolio_health(self.state)
                )

                pnl_label = "kâr" if is_profitable else "zarar"
                action_desc = f"Sold {sym} TL {trade.total:,.0f} ({pnl_label})"
                self._fire_ai_suggestion(action_desc)

                pl = self.state.total_pnl
                edu = "  ·  Portföyünüz kârda — iyi zamanlama!" if pl >= 0 else "  ·  Piyasalar zaman zaman düşer — bu normaldir."
                msg = f"Satım: {trade.quantity:.6g} {sym} @ TL {trade.price:,.2f}  →  TL {trade.total:,.2f}{edu}"
        except ValueError as exc:
            self._warn(str(exc))
            return

        # ── DB'ye kaydet ──────────────────────────────────────────────────
        if self._db and self._user_id:
            self._db.save_trade(
                user_id=self._user_id,
                session_id=self._session_id,
                side=trade.side,
                symbol=trade.symbol,
                quantity=trade.quantity,
                price=trade.price,
                total=trade.total,
                timestamp=trade.timestamp,
            )

        self._full_refresh()
        self.statusBar().showMessage(msg, 6000)

    def _close_position(self) -> None:
        row = self.pos_table.currentRow()
        if row < 0:
            self._warn("Kapatmak için tablodan bir pozisyon seçin.")
            return
        sym_item = self.pos_table.item(row, 0)
        if not sym_item: return
        sym = sym_item.text().strip().upper()
        pos = self.state._find(sym)
        if not pos:
            self._warn(f"{sym} pozisyonu bulunamadı.")
            return
        price = self._feed.get_price(sym) or pos.current_price
        reply = QMessageBox.question(
            self, "Pozisyonu Kapat",
            f"{pos.quantity:.6g} {sym} adet\nPiyasa fiyatı: TL {price:,.2f}\nTahmini gelir: TL {pos.quantity * price:,.2f}\n\nSatışı onaylıyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes: return
        avg_cost_before = pos.avg_cost
        is_profitable   = price > pos.avg_cost
        try:
            trade = self.state.execute_sell(sym, pos.quantity, price)
        except ValueError as exc:
            self._warn(str(exc))
            return
        self._extra.user_sell_count += 1
        if is_profitable: self._extra.profitable_sell_count += 1

        self._show_warnings(
            self._detector.check_after_sell(self.state, sym, price, avg_cost_before)
            + self._detector.check_portfolio_health(self.state)
        )
        # ── DB'ye kaydet ──────────────────────────────────────────────────
        if self._db and self._user_id:
            self._db.save_trade(
                user_id=self._user_id,
                session_id=self._session_id,
                side=trade.side,
                symbol=trade.symbol,
                quantity=trade.quantity,
                price=trade.price,
                total=trade.total,
                timestamp=trade.timestamp,
            )
        self._full_refresh()
        self.statusBar().showMessage(f"{sym} pozisyonu kapatıldı. Gelir: TL {trade.total:,.2f}", 5000)

    def _load_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "CSV Seç", "", "CSV (*.csv);;Tüm Dosyalar (*.*)")
        if not path: return
        try:
            # 1. Metadata (for column map display)
            self.dataset_info = self._loader.inspect_csv(path)
            self.cleaned      = self._cleaner.build_cleaning_plan(self.dataset_info)
            # 2. Full load → clean → features
            raw               = self._loader.load_csv(path)
            cleaned_data      = self._cleaner.clean(raw)
            self.loaded_data  = cleaned_data
            self.feature_data = self._features.build(cleaned_data)
            # 3. Seed PriceFeed with last known close price
            last_close = self.feature_data.last_close
            sym = self.feature_data.symbol
            if sym in self._feed._prices:
                self._feed._prices[sym]  = last_close
                self._feed._prev[sym]    = last_close
                self._feed._open[sym]    = last_close
            # 4. Pre-compute trend + forecast from close series
            close_series = self.feature_data.close_series
            self.trend_summary = self._trend.summarize(close_series)
            self.forecast      = self._fore.predict_next(close_series, steps=6)
        except (FileNotFoundError, ValueError) as exc:
            self._warn(str(exc))
            return
        self.state.attach_dataset(path)
        #self._refresh_data()
        self._refresh_analysis()
        self._goto(3)
        rows = self.dataset_info.row_count
        self.statusBar().showMessage(
            f"Yüklendi: {Path(path).name}  ({rows:,} satır) — "
            f"Son kapanış: {self.feature_data.last_close:,.2f}  "
            f"Trend: {self.trend_summary.direction}",
            7000,
        )
    def _build_portfolio_value_series_from_csv(self, start_date, end_date) -> list[float]:
        """
        Seçilen tarih aralığında, mevcut açık pozisyonların CSV fiyatlarına göre
        portföy değer serisini üretir.

        Örnek:
        Gün 1: nakit + BTC miktarı * BTC fiyatı + ETH miktarı * ETH fiyatı
        Gün 2: nakit + BTC miktarı * BTC fiyatı + ETH miktarı * ETH fiyatı
        ...
        """
        if not self.state.positions:
            raise ValueError("Analiz için en az bir açık pozisyon olmalı.")

        series_by_symbol: dict[str, list[float]] = {}

        for pos in self.state.positions:
            feat = self._csv_datasets.get(pos.symbol)

            if feat is None:
                raise ValueError(
                    f"{pos.symbol} için CSV verisi bulunamadı. "
                    f"Bu varlık analiz ekranında gerçek veriyle simüle edilemez."
                )

            df = feat.df.copy()
            date_col = feat.date_col
            close_col = feat.close_col

            mask = (
                (df[date_col].dt.date >= start_date)
                & (df[date_col].dt.date <= end_date)
            )

            selected = df.loc[mask, close_col].astype(float).tolist()

            if not selected:
                raise ValueError(
                    f"{pos.symbol} için seçilen tarih aralığında veri bulunamadı."
                )

            series_by_symbol[pos.symbol] = selected

        min_len = min(len(values) for values in series_by_symbol.values())

        portfolio_values: list[float] = []

        for i in range(min_len):
            total_value = self.state.cash

            for pos in self.state.positions:
                price = series_by_symbol[pos.symbol][i]
                total_value += pos.quantity * price

            portfolio_values.append(round(total_value, 2))

        return portfolio_values
    def _run_scenario(self) -> None:
        start = self.an_start.date().toPyDate()
        end = self.an_end.date().toPyDate()

        try:
            portfolio_series = self._build_portfolio_value_series_from_csv(start, end)
        except ValueError as exc:
            self._warn(str(exc))
            return

        # Gerçek CSV verisine göre hesaplanan portföy değer geçmişini kullan
        self.state.value_history = portfolio_series

        # Son değeri pozisyonların güncel fiyatına da yansıt
        last_prices: dict[str, float] = {}

        for pos in self.state.positions:
            feat = self._csv_datasets.get(pos.symbol)
            if feat is None:
                continue

            df = feat.df.copy()
            date_col = feat.date_col
            close_col = feat.close_col

            mask = (
                (df[date_col].dt.date >= start)
                & (df[date_col].dt.date <= end)
            )

            selected = df.loc[mask, close_col].astype(float).tolist()

            if selected:
                last_prices[pos.symbol] = selected[-1]

        self.state.update_prices(last_prices)

        # Analiz metrikleri artık gerçek CSV tabanlı portföy serisinden hesaplanıyor
        self.trend_summary = self._trend.summarize(portfolio_series)
        self.forecast = self._fore.predict_next(portfolio_series, steps=6)

        self.state.simulation_status = (
            f"CSV tabanlı analiz tamamlandı ({start.isoformat()} → {end.isoformat()})"
        )

        self._extra.analysis_run = True
        self._extra.forecast_viewed = True

        self._refresh_topbar()
        self._refresh_positions()
        self._refresh_dashboard_metrics()
        self._refresh_account_summary()
        self._refresh_analysis()
        self._refresh_learn()

        self.statusBar().showMessage(
            f"CSV tabanlı analiz tamamlandı: {len(portfolio_series)} veri noktası kullanıldı.",
            6000,
        )

    def _save_report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Raporu Kaydet", "portfolio_report.txt", "Metin (*.txt);;Tüm (*.*)")
        if not path: return
        try:
            Path(path).write_text(
                self.state.build_report(self.an_start.date().toPyDate(), self.an_end.date().toPyDate()),
                encoding="utf-8",
            )
        except OSError as exc:
            self._warn(f"Kayıt hatası: {exc}")
            return
        self._extra.report_saved = True
        self._refresh_learn()
        self.statusBar().showMessage(f"Rapor kaydedildi: {Path(path).name}", 4000)

    def _full_refresh(self) -> None:
        self._refresh_topbar()
        self._refresh_dashboard_metrics()
        self._refresh_dashboard_charts()
        self._refresh_dashboard_learning()
        self._refresh_watchlist()
        self._refresh_positions()
        self._refresh_account_summary()
        self._refresh_history()
        #self._refresh_data()
        self._refresh_analysis()
        self._refresh_tutorial()
        self._refresh_learn()

    def _refresh_learn(self) -> None:
        if hasattr(self, "_learn_page"): self._learn_page.refresh(self.state, self._extra.to_dict())

    def _refresh_dashboard_learning(self) -> None:
        if not hasattr(self, "d_level_badge"): return
        xp = self._ls.xp
        icon = getattr(self._ls, "current_level_icon", "🌱")
        label = getattr(self._ls, "current_level_label", "Başlangıç")
        curr, total = self._ls.level_progress() if hasattr(self._ls, "level_progress") else (xp, 700)
        pct = int(min(curr / total * 100, 100)) if total > 0 else 100

        self.d_level_badge.setText(f"{icon} {label}")
        self.d_xp_txt.setText(f"{xp} XP")
        self.d_xp_prog.setValue(pct)
        self.d_xp_val.setText(f"{xp} XP")
        self.d_level_sub.setText(f"{icon} {label}  ·  {curr}/{total}")

        active_task = self._get_active_task()
        if active_task:
            self.d_task_icon_lbl.setText(active_task.icon)
            self.d_task_title_lbl.setText(active_task.title)
            self.d_task_obj_lbl.setText(active_task.objective)
            self._d_task_goto = active_task.navigate_to
            try: self.d_task_nav_btn.clicked.disconnect()
            except (RuntimeError, TypeError): pass
            self.d_task_nav_btn.clicked.connect(lambda: self._goto(self._d_task_goto))
            self.d_task_nav_btn.setVisible(True)
        else:
            self.d_task_icon_lbl.setText("🏆")
            self.d_task_title_lbl.setText("Tüm görevler tamamlandı!")
            self.d_task_obj_lbl.setText("Artık bir portföy ustasısın. Liderliği koru!")
            self.d_task_nav_btn.setVisible(False)

        risk = _compute_risk_label(self.state)
        self.d_risk_badge.setText(f"Risk: {risk['label']}")
        self.d_risk_badge.setStyleSheet(
            f"color:{risk['color']}; background:{risk['color']}18; "
            f"border:1px solid {risk['color']}44; border-radius:5px; font-size:11px; font-weight:700; padding:3px 10px;"
        )
        if self._last_ai_sugg:
            self.d_ai_sugg_lbl.setText(self._last_ai_sugg)
            self.d_ai_source_lbl.setText(_ai_src(self._last_ai_is_gemini))

        dot = "🟢" if self._ai_coach.gemini_available else "🟡"
        self.d_ai_status_dot.setText(f"{dot} {self._ai_coach.gemini_status}")

    def _refresh_trade_task(self) -> None:
        if not hasattr(self, "t_task_title"): return
        active_task = self._get_active_task()
        if active_task:
            self.t_task_icon.setText(active_task.icon)
            self.t_task_title.setText(f"Görev: {active_task.title}")
            self.t_task_obj.setText(active_task.objective)
            self.t_task_banner.setVisible(True)
        else:
            self.t_task_banner.setVisible(False)

    def _refresh_topbar(self) -> None:
        pv = self.state.portfolio_value
        pl = self.state.total_pnl
        pl_color = _GREEN if pl >= 0 else _RED

        self.h_value.setText(f"TL {pv:,.0f}")
        self.h_pl.setText(f"{pl:+,.0f}")
        self.h_pl.setStyleSheet(f"color:{pl_color}; font-weight:700; font-family:Consolas; font-size:13px;")
        self.h_cash.setText(f"TL {self.state.cash:,.0f}")
        self.h_pos.setText(str(len(self.state.positions)))

        if "tamamlandi" in self.state.simulation_status:
            self.statusBar().showMessage("● SENARYO MODU AKTİF", 10000)
        elif "Veri" in self.state.simulation_status:
            self.statusBar().showMessage("● VERİ YÜKLENDİ", 10000)

    def _refresh_dashboard_metrics(self) -> None:
        pv  = self.state.portfolio_value
        pl  = self.state.total_pnl
        upl = self.state.total_unrealized_pnl
        rpl = self.state.total_realized_pnl
        pc  = self.state.total_pnl_pct * 100
        pl_c  = _GREEN if pl  >= 0 else _RED
        upl_c = _GREEN if upl >= 0 else _RED
        rpl_c = _GREEN if rpl >= 0 else _RED

        self.d_pv.setText(f"TL {pv:,.0f}")
        self.d_pv_s.setText(f"Başlangıç: TL {self.state.starting_balance:,.0f}")
        self.d_pl.setText(f"{pl:+,.0f} TL")
        self.d_pl.setStyleSheet(f"color:{pl_c}; font-weight:700; font-family:Consolas; font-size:18px;")
        self.d_pl_s.setText(f"% {pc:+.2f}")
        self.d_pl_s.setStyleSheet(f"color:{pl_c}; font-size:10px;")
        self.d_upl.setText(f"{upl:+,.0f} TL")
        self.d_upl.setStyleSheet(f"color:{upl_c}; font-weight:700; font-family:Consolas; font-size:18px;")
        self.d_rpl.setText(f"{rpl:+,.0f} TL")
        self.d_rpl.setStyleSheet(f"color:{rpl_c}; font-weight:700; font-family:Consolas; font-size:18px;")

    def _refresh_dashboard_charts(self) -> None:
        self.d_chart.set_line_values(self.state.value_history)
        prices = self._feed.get_all()
        all_syms = list(self._csv_datasets.keys())

        self.d_mini_wl.setRowCount(len(all_syms))

        for r, sym in enumerate(all_syms):
            price = prices.get(sym, 0.0)
            day_chg = self._feed.day_change_pct(sym)
            chg_c = _GREEN if day_chg >= 0 else _RED

            self.d_mini_wl.setItem(
                r, 0,
                _item(sym, _TEXT, bold=True, align=Qt.AlignmentFlag.AlignLeft)
            )
            self.d_mini_wl.setItem(
                r, 1,
                _item(_fmt_price(price), _TEXT, mono=True)
            )
            self.d_mini_wl.setItem(
                r, 2,
                _item(f"{day_chg:+.2f}%", chg_c)
            )

        trades = list(reversed(self.state.trade_history[-6:]))
        self.d_recent.setRowCount(len(trades))
        for r, t in enumerate(trades):
            c = _GREEN if t.side == "AL" else _RED
            self.d_recent.setItem(r, 0, _item(t.timestamp[-8:], _TEXT3))
            self.d_recent.setItem(r, 1, _item(t.side, c, bold=True))
            self.d_recent.setItem(r, 2, _item(t.symbol, _TEXT))
            self.d_recent.setItem(r, 3, _item(f"{t.total:,.0f}", c))

    def _refresh_watchlist(self) -> None:
        prices = self._feed.get_all()
        syms = list(self._csv_datasets.keys())
        self.wl_table.setRowCount(len(syms))

        for r, sym in enumerate(syms):
            feat = self._csv_datasets.get(sym)
            edu = ASSET_INFO.get(sym, {})

            name = sym
            if feat is not None:
                df = feat.df
                if "Name" in df.columns and not df["Name"].dropna().empty:
                    name = str(df["Name"].dropna().iloc[0])

            price = prices.get(sym, 0.0)
            prev = self._prev_prices.get(sym, price)
            day_chg = self._feed.day_change_pct(sym)
            tick_up = price >= prev
            chg_c = _GREEN if day_chg >= 0 else _RED

            if feat is not None:
                risk_info = _risk_from_volatility(feat.last_volatility)
                risk_txt = risk_info["label"]
                risk_c = risk_info["color"]
                risk_detail = risk_info["detail"]
            else:
                risk_txt = "—"
                risk_c = _TEXT3
                risk_detail = "CSV verisi yok"

            desc = edu.get("desc", "")
            if risk_detail != "CSV verisi yok":
                desc = f"{desc} | Risk ölçümü: {risk_detail}"

            self.wl_table.setItem(
                r, 0,
                _item(sym, _TEXT, bold=True, align=Qt.AlignmentFlag.AlignLeft)
            )
            self.wl_table.setItem(
                r, 1,
                _item(name, _TEXT2, align=Qt.AlignmentFlag.AlignLeft)
            )
            self.wl_table.setItem(
                r, 2,
                _item(_fmt_price(price), _GREEN if tick_up else _RED, mono=True)
            )
            self.wl_table.setItem(
                r, 3,
                _item(f"{day_chg:+.2f}%", chg_c)
            )
            self.wl_table.setItem(
                r, 4,
                _item(risk_txt, risk_c, align=Qt.AlignmentFlag.AlignLeft)
            )
            self.wl_table.setItem(
                r, 5,
                _item(desc, _TEXT3, align=Qt.AlignmentFlag.AlignLeft)
            )
    # ── positions ─────────────────────────────────────────────────────────────

    def _refresh_positions(self) -> None:
        self.pos_table.setRowCount(len(self.state.positions))
        for r, pos in enumerate(self.state.positions):
            pl    = pos.unrealized_pnl
            plpct = pos.unrealized_pnl_pct * 100
            c     = _GREEN if pl >= 0 else _RED
            self.pos_table.setItem(r, 0, _item(pos.symbol,                          _TEXT,  bold=True, align=Qt.AlignmentFlag.AlignLeft))
            self.pos_table.setItem(r, 1, _item(f"{pos.quantity:.6g}",               _TEXT2))
            self.pos_table.setItem(r, 2, _item(f"{pos.avg_cost:>10,.2f}",           _TEXT2, mono=True))
            self.pos_table.setItem(r, 3, _item(f"{pos.current_price:>10,.2f}",      _TEXT,  mono=True))
            self.pos_table.setItem(r, 4, _item(f"{pos.market_value:>12,.2f}",       _TEXT,  mono=True))
            self.pos_table.setItem(r, 5, _item(f"{pl:>+10,.2f}",                    c,      bold=True))
            self.pos_table.setItem(r, 6, _item(f"{plpct:+.2f}%",                    c))

    def _refresh_account_summary(self) -> None:
        pl  = self.state.total_pnl
        upl = self.state.total_unrealized_pnl
        rpl = self.state.total_realized_pnl
        self.acc_cash.setText(f"TL {self.state.cash:,.2f}")
        self.acc_pv.setText(f"TL {self.state.portfolio_value:,.2f}")
        self.acc_tpl.setText(f"{pl:+,.2f} TL")
        self.acc_tpl.setStyleSheet(f"color:{'#10b981' if pl >= 0 else '#ef4444'}; font-weight:700;")
        self.acc_rpl.setText(f"{rpl:+,.2f} TL")
        self.acc_rpl.setStyleSheet(f"color:{'#10b981' if rpl >= 0 else '#ef4444'}; font-weight:700;")
        self.acc_upl.setText(f"{upl:+,.2f} TL")
        self.acc_upl.setStyleSheet(f"color:{'#10b981' if upl >= 0 else '#ef4444'}; font-weight:700;")

        sells       = [t for t in self.state.trade_history if t.side == "SAT"]
        profit_sell = self._extra.profitable_sell_count
        win_rate    = (profit_sell / len(sells) * 100) if sells else 0.0
        wr_color    = _GREEN if win_rate >= 50 else (_AMBER if win_rate >= 30 else _RED)
        if hasattr(self, "acc_winrate"):
            self.acc_winrate.setText(f"% {win_rate:.1f}")
            self.acc_winrate.setStyleSheet(f"color:{wr_color}; font-weight:700; font-family:Consolas;")

        risk = _compute_risk_label(self.state)
        if hasattr(self, "acc_risk"):
            self.acc_risk.setText(risk["label"])
            self.acc_risk.setStyleSheet(f"color:{risk['color']}; font-weight:700;")

        if hasattr(self, "acc_trade_count"):
            self.acc_trade_count.setText(str(len(self.state.trade_history)))

        self._refresh_trade_task()
        self._update_order_total()

    def _refresh_history(self, _text: str = "") -> None:
        filt   = self.hist_filter.text().strip().upper()
        trades = [t for t in reversed(self.state.trade_history) if not filt or filt in t.symbol]
        self.hist_table.setRowCount(len(trades))
        buy_count   = sum(1 for t in self.state.trade_history if t.side == "AL")
        sell_count  = len(self.state.trade_history) - buy_count
        volume      = sum(t.total for t in self.state.trade_history)
        profit_sell = self._extra.profitable_sell_count
        win_rate    = (profit_sell / sell_count * 100) if sell_count > 0 else 0.0
        wr_color    = _GREEN if win_rate >= 50 else (_AMBER if win_rate >= 30 else _RED)
        risk        = _compute_risk_label(self.state)

        self.hi_total.setText(str(len(self.state.trade_history)))
        self.hi_buy.setText(str(buy_count))
        self.hi_sell.setText(str(sell_count))
        self.hi_volume.setText(f"TL {volume:,.0f}")

        if hasattr(self, "hi_winrate"):
            self.hi_winrate.setText(f"% {win_rate:.1f}")
            self.hi_winrate.setStyleSheet(f"color:{wr_color}; font-weight:700; font-family:Consolas; font-size:18px;")
            self.hi_winrate_sub.setText(f"{profit_sell} kârlı / {sell_count} satım")

        if hasattr(self, "hi_profitsell"):
            self.hi_profitsell.setText(str(profit_sell))
            self.hi_profitsell.setStyleSheet(f"color:{_GREEN}; font-weight:700; font-family:Consolas; font-size:18px;")

        if hasattr(self, "hi_xp_earned"):
            self.hi_xp_earned.setText(f"{self._ls.xp} XP")
            self.hi_xp_earned.setStyleSheet(f"color:{_AMBER}; font-weight:700; font-family:Consolas; font-size:18px;")

        if hasattr(self, "hi_risk"):
            self.hi_risk.setText(risk["label"])
            self.hi_risk.setStyleSheet(f"color:{risk['color']}; font-weight:700; font-family:Consolas; font-size:18px;")
            self.hi_risk_sub.setText(risk["detail"])

        for r, t in enumerate(trades):
            c = _GREEN if t.side == "AL" else _RED
            self.hist_table.setItem(r, 0, _item(str(t.trade_id), _TEXT3))
            self.hist_table.setItem(r, 1, _item(t.timestamp,     _TEXT2))
            self.hist_table.setItem(r, 2, _item(t.side,          c, bold=True))
            self.hist_table.setItem(r, 3, _item(t.symbol,        _TEXT, bold=True, align=Qt.AlignmentFlag.AlignLeft))
            self.hist_table.setItem(r, 4, _item(f"{t.quantity:.6g}", _TEXT2))
            self.hist_table.setItem(r, 5, _item(f"{t.price:>12,.2f}",  _TEXT, mono=True))
            self.hist_table.setItem(r, 6, _item(f"{t.total:>12,.2f}",  c,     bold=True))

    def _refresh_data(self) -> None:
        if self.dataset_info is None:
            for lbl in (self.dv_file, self.dv_rows, self.dv_date, self.dv_price): lbl.setText("—")
            self.dv_table.setRowCount(0)
            self.dv_status.setText("Henüz CSV seçilmedi.")
            return

        di, cd = self.dataset_info, self.cleaned
        self.dv_file.setText(di.path.name)
        self.dv_rows.setText(f"{di.row_count:,}")
        self.dv_date.setText(cd.date_column if cd and cd.date_column else "—")
        self.dv_price.setText(", ".join(cd.price_columns[:3]) if cd and cd.price_columns else "—")

        price_set = set(cd.price_columns) if cd else set()
        date_col  = cd.date_column if cd else None
        self.dv_table.setRowCount(len(di.columns))
        for r, col in enumerate(di.columns):
            if col == date_col: role, icon = "Tarih",  "🗓"
            elif col in price_set: role, icon = "Fiyat",  "💹"
            else: role, icon = "Genel",  "—"
            self.dv_table.setItem(r, 0, _item(col,          _TEXT, align=Qt.AlignmentFlag.AlignLeft))
            self.dv_table.setItem(r, 1, _item(f"{icon}  {role}", _TEXT2))
            self.dv_table.setItem(r, 2, _item("–",          _TEXT3))
        self.dv_status.setText("Dosya analiz edildi. Pandas entegrasyonu aktif olunca tam temizleme akışı devreye girecek.")

    def _refresh_analysis(self) -> None:
        self.an_chart.set_line_values(self.state.value_history)
        if self.trend_summary is None:
            for lbl in (self.an_dir, self.an_chg, self.an_vol, self.an_next): lbl.setText("—")
            self.an_table.setRowCount(0)
            self.an_status.setText("Senaryo simülasyonu henüz çalıştırılmadı.")
            return

        ts   = self.trend_summary
        DIR  = {"up": "YÜKSELİŞ ↑", "down": "DÜŞÜŞ ↓", "flat": "YATAY →"}
        dc   = _GREEN if ts.direction == "up" else (_RED if ts.direction == "down" else _AMBER)
        cc   = _GREEN if ts.change_pct >= 0 else _RED

        self.an_dir.setText(DIR.get(ts.direction, ts.direction))
        self.an_dir.setStyleSheet(f"color:{dc}; font-weight:700; font-family:Consolas; font-size:18px;")
        self.an_chg.setText(f"%{ts.change_pct:+.2f}")
        self.an_chg.setStyleSheet(f"color:{cc}; font-weight:700; font-family:Consolas; font-size:18px;")
        self.an_vol.setText(f"%{ts.volatility_pct:.2f}")
        self.an_next.setText(f"TL {self.forecast[0].value:,.0f}" if self.forecast else "—")

        self.an_table.setRowCount(len(self.forecast))
        prev = self.state.value_history[-1] if self.state.value_history else 0.0
        for r, fp in enumerate(self.forecast):
            diff  = fp.value - prev
            dc2   = _GREEN if diff >= 0 else _RED
            self.an_table.setItem(r, 0, _item(f"Adım {fp.index + 1}", _TEXT3))
            self.an_table.setItem(r, 1, _item(f"TL {fp.value:,.2f}", _TEXT, mono=True))
            self.an_table.setItem(r, 2, _item(f"{diff:+,.2f}", dc2, bold=True))
            prev = fp.value
        self.an_status.setText(f"Son senaryo: {self.state.simulation_status}")

    def _show_warnings(self, warnings: list) -> None:
        if hasattr(self, "_learn_page"):
            for w in warnings: self._learn_page.show_mistake_warning(w)

    def _get_active_task(self) -> "object | None":
        xp = self._ls.xp
        for lvl in getattr(self._ls, "levels", []):
            if not lvl.is_unlocked(xp): continue
            t = lvl.get_next_task(getattr(self._ls, "_completed_tasks", set()))
            if t: return t
        return None

    def _fire_analysis_ai(self) -> None:
        if not hasattr(self, "an_ai_lbl"): return
        self.an_ai_spinner.setText("⏳ yükleniyor…")
        self.an_ai_lbl.setText("AI Koç analiz yapıyor…")
        action = "Senaryo simülasyonu tamamlandı, trend analizi yapıldı."
        is_ai  = self._ai_coach.gemini_available

        def _on_result(text: str) -> None:
            self._last_ai_sugg      = text
            self._last_ai_is_gemini = is_ai
            if hasattr(self, "an_ai_lbl"):
                self.an_ai_lbl.setText(text)
                self.an_ai_source.setText(_ai_src(is_ai))
                self.an_ai_spinner.setText("")
            self._refresh_dashboard_learning()

        self._ai_coach.get_action_suggestion(self.state, self._extra, self._ls, action, _on_result, lb=self._lb)

    def _warn(self, msg: str) -> None:
        QMessageBox.warning(self, "Portfolio Simulator", msg)

    def _on_calc_used(self) -> None:
        if not self._extra.calc_used:
            self._extra.calc_used = True
            self._refresh_learn()

    def _fire_ai_suggestion(self, action: str = "") -> None:
        is_ai = self._ai_coach.gemini_available
        def _on_result(text: str) -> None:
            self._last_ai_sugg      = text
            self._last_ai_is_gemini = is_ai
            if hasattr(self, "_learn_page"): self._learn_page.push_ai_suggestion(text, is_ai=is_ai)
            self._refresh_dashboard_learning()
        self._ai_coach.get_action_suggestion(self.state, self._extra, self._ls, action, _on_result, lb=self._lb)

    def _save_leaderboard_session(self) -> None:
        try:
            entry = self._lb.save_session(self.state, self._ls, self._extra.profitable_sell_count)
            self.statusBar().showMessage(
                f"Liderlik tablosuna kaydedildi: {entry.username}  ·  K/Z: {entry.total_pnl:+,.0f} TL  ·  XP: {entry.xp}", 6000
            )
        except Exception as exc:
            self.statusBar().showMessage(f"Kayıt hatası: {exc}", 4000)
        self._refresh_learn()

    def _show_welcome(self) -> None:
        dlg = WelcomeDialog(self)
        dlg.exec()
        if dlg.go_learn:
            self._goto(4)

    def _rotate_tip(self) -> None:
        if TIPS:
            self.statusBar().showMessage(TIPS[self._tip_index % len(TIPS)], 10000)
            self._tip_index += 1

    def _refresh_tutorial(self) -> None:
        has_trade = len(self.state.trade_history) > 0
        has_sell  = any(t.side == "SAT" for t in self.state.trade_history)
        self._tutorial_done["view_market"]     = True
        self._tutorial_done["first_buy"]       = has_trade
        self._tutorial_done["check_portfolio"] = has_trade or bool(self.state.positions)
        self._tutorial_done["first_sell"]      = has_sell
        self._tutorial_done["check_history"]   = has_sell
        self._tutorial_done["run_analysis"]    = self.trend_summary is not None

    # ── Logout ────────────────────────────────────────────────────────────────

    def _logout(self) -> None:
        """Save current session and show the login dialog again."""
        # 1. Stop timers so nothing fires while we rebuild
        if hasattr(self, "_market_timer"):
            self._market_timer.stop()
        if hasattr(self, "_tip_timer"):
            self._tip_timer.stop()

        # 2. Persist session to DB
        if self._db and self._user_id and self._session_id:
            try:
                self._db.end_session(
                    session_id=self._session_id,
                    final_value=self.state.portfolio_value,
                    total_pnl=self.state.total_pnl,
                    trade_count=len(self.state.trade_history),
                    xp_earned=self._ls.xp,
                )
            except Exception:
                pass

        # 3. Show login dialog again (DB stays open — no need to reconnect)
        from src.ui.login_dialog import LoginDialog
        login = LoginDialog(self._db)
        self.hide()
        if login.exec() != LoginDialog.DialogCode.Accepted or login.user_row is None:
            # User closed login → exit app
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()
            return

        # 4. Reset state for new user session
        from src.portfolio.portfolio import PortfolioState
        new_window = MainWindow(
            PortfolioState(),
            db=self._db,
            user_id=login.user_row.id,
            username=login.user_row.username,
            session_id=login.session_id,
        )
        new_window.show()
        self._is_logging_out = True
        self.close()

    # ── Window close — persist session to DB ──────────────────────────────────

    def closeEvent(self, event) -> None:  # type: ignore[override]
        is_logout = getattr(self, "_is_logging_out", False)
        if self._db and self._user_id and self._session_id:
            try:
                self._db.end_session(
                    session_id=self._session_id,
                    final_value=self.state.portfolio_value,
                    total_pnl=self.state.total_pnl,
                    trade_count=len(self.state.trade_history),
                    xp_earned=self._ls.xp,
                )
                if not is_logout:
                    self._db.close()
            except Exception:
                pass
        super().closeEvent(event)



# ══════════════════════════════════════════════════════════════════════════════
# STYLESHEET (Extracted for readability)
# ══════════════════════════════════════════════════════════════════════════════

STYLESHEET = f"""
QMainWindow, QWidget {{ background: {_BG}; color: {_TEXT}; }}
QFrame#topbar {{ background: {_TOPBAR}; border-bottom: 1px solid {_BORDER}; }}
QFrame#sidebar {{ background: {_TOPBAR}; }}
QPushButton#navBtn {{ border: none; background: transparent; }}
QFrame#sep {{ color: {_BORDER}; background: {_BORDER}; max-height: 1px; max-width: 1px; }}
QFrame#card {{ background: {_SURF}; border: 1px solid {_BORDER}; border-radius: 8px; }}
QLabel#cardTitle {{ color: {_TEXT3}; font-size: 10px; font-weight: 700; letter-spacing: 1.5px; }}

/* metric boxes */
QFrame#metricBox {{ background: {_SURF}; border: 1px solid {_BORDER}; border-radius: 8px; }}
QLabel#metricTitle {{ color: {_TEXT3}; font-size: 9px; font-weight: 700; letter-spacing: 1.5px; }}
QLabel#metricValue {{ color: {_TEXT}; font-size: 18px; font-weight: 700; }}
QLabel#metricSub {{ color: {_TEXT3}; font-size: 10px; }}

/* tables */
QTableWidget#tbl {{ background: {_SURF}; gridline-color: transparent; border: none; color: {_TEXT}; font-size: 12px; outline: none; }}
QTableWidget#tbl::item {{ padding: 7px 10px; border: none; }}
QTableWidget#tbl::item:selected {{ background: #1a2d50; color: {_TEXT}; }}
QTableWidget#tbl::item:alternate {{ background: {_SURF2}; }}
QHeaderView::section {{ background: {_SURF2}; color: {_TEXT3}; padding: 8px 10px; border: none; border-bottom: 1px solid {_BORDER}; font-size: 10px; font-weight: 700; letter-spacing: 0.8px; }}

/* form inputs */
QLineEdit#formInput, QDoubleSpinBox#formInput, QDateEdit#formInput {{ background: {_SURF2}; border: 1px solid {_BORDER}; border-radius: 5px; color: {_TEXT}; padding: 0 8px; min-height: 32px; font-size: 13px; selection-background-color: {_ACCENT}; }}
QLineEdit#formInput:focus, QDoubleSpinBox#formInput:focus, QDateEdit#formInput:focus {{ border: 1px solid {_ACCENT}; }}
QDoubleSpinBox#formInput::up-button, QDoubleSpinBox#formInput::down-button {{ width: 18px; background: {_BORDER}; border: none; }}

/* buttons */
QPushButton {{ border-radius: 6px; font-size: 12px; font-weight: 600; padding: 0 14px; }}
QPushButton#btnPrimary {{ background: {_ACCENT}; color: white; border: none; }}
QPushButton#btnPrimary:hover {{ background: {_ACCH}; }}
QPushButton#btnPrimary:pressed {{ background: #1e40af; }}
QPushButton#btnSuccess {{ background: #064e3b; color: {_GREEN}; border: 1px solid #065f46; }}
QPushButton#btnSuccess:hover {{ background: #065f46; border-color: {_GREEN}; }}
QPushButton#btnDanger {{ background: transparent; color: {_RED}; border: 1px solid #7f1d1d; }}
QPushButton#btnDanger:hover {{ background: #1a0505; border-color: {_RED}; }}
QPushButton#btnSecondary {{ background: {_SURF2}; color: {_TEXT2}; border: 1px solid {_BORDER}; }}
QPushButton#btnSecondary:hover {{ background: #1e2d45; color: {_TEXT}; }}
QPushButton#btnGhost {{ background: transparent; color: {_TEXT3}; border: 1px solid {_BORDER}; }}
QPushButton#btnGhost:hover {{ color: {_TEXT}; border-color: {_TEXT3}; }}

/* order side toggle */
QPushButton#sideActive {{ background: {_ACCENT}; color: white; border: none; border-radius: 0px; font-size: 14px; font-weight: 800; }}
QPushButton#sideInactive {{ background: {_SURF2}; color: {_TEXT3}; border: none; border-radius: 0px; font-size: 13px; }}
QPushButton#sideInactive:hover {{ background: {_BORDER}; color: {_TEXT2}; }}

/* execute order button */
QPushButton#btnExecute, QPushButton#btnExecuteBuy {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1d6fe8, stop:1 #1450c4); color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: 800; letter-spacing: 1px; }}
QPushButton#btnExecute:hover, QPushButton#btnExecuteBuy:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2878f0, stop:1 #1a5ad4); }}
QPushButton#btnExecuteSell {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d42020, stop:1 #a01818); color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: 800; letter-spacing: 1px; }}
QPushButton#btnExecuteSell:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e42828, stop:1 #b02020); }}

/* status / scroll */
QStatusBar {{ background: {_TOPBAR}; color: {_TEXT3}; font-size: 11px; border-top: 1px solid {_BORDER}; }}
QScrollBar:vertical {{ background: {_SURF}; width: 6px; }}
QScrollBar::handle:vertical {{ background: {_BORDER}; border-radius: 3px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: {_SURF}; height: 6px; }}
QScrollBar::handle:horizontal {{ background: {_BORDER}; border-radius: 3px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── learn sidebar ── */
QFrame#learnSidebar {{ background: {_TOPBAR}; border-right: 1px solid {_BORDER}; }}
QLabel#learnHeader {{ color: {_AMBER}; font-size: 13px; font-weight: 700; padding-left: 12px; background: {_TOPBAR}; border-bottom: 1px solid {_BORDER}; }}
QPushButton#learnTopicBtn, QPushButton#learnNavBtn {{ background: transparent; color: {_TEXT2}; border: none; border-radius: 0px; font-size: 12px; font-weight: 500; text-align: left; padding-left: 16px; }}
QPushButton#learnTopicBtn:hover, QPushButton#learnNavBtn:hover {{ background: {_SURF}; color: {_TEXT}; }}
QPushButton#learnTopicBtn:checked, QPushButton#learnNavBtn:checked {{ background: #1a2d45; color: {_ACCENT}; font-weight: 700; border-left: 3px solid {_ACCENT}; }}

/* ── learn content ── */
QStackedWidget#learnContent, QScrollArea#learnScroll, QScrollArea#learnScroll > QWidget > QWidget {{ background: {_BG}; }}
QLabel#topicTitle {{ color: {_TEXT}; font-size: 22px; font-weight: 800; }}
QLabel#topicSummary {{ color: {_ACCENT}; font-size: 13px; font-style: italic; }}
QLabel#topicHeading {{ color: {_AMBER}; font-size: 13px; font-weight: 700; letter-spacing: 0.5px; }}
QLabel#topicBody {{ color: {_TEXT2}; font-size: 13px; line-height: 1.7; }}

/* ── glossary ── */
QFrame#glossRow {{ background: {_SURF}; border: 1px solid {_BORDER}; border-radius: 6px; }}
QLabel#glossTerm {{ color: {_TEXT}; font-size: 12px; font-weight: 700; }}
QLabel#glossDef {{ color: {_TEXT2}; font-size: 12px; }}
QFrame#tutCard {{ background: {_SURF}; border: 1px solid {_BORDER}; border-radius: 8px; }}
QFrame#xpHeader {{ background: {_TOPBAR}; border-bottom: 1px solid {_BORDER}; }}

/* ── amber button ── */
QPushButton#btnAmber {{ background: #1c1200; color: {_AMBER}; border: 1px solid #44330a; border-radius: 6px; font-size: 12px; font-weight: 700; }}
QPushButton#btnAmber:hover {{ background: #2a1c00; border-color: {_AMBER}; }}
"""