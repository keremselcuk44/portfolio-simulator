"""Interactive educational widgets — learning through doing, not just reading."""

from __future__ import annotations

import random
from typing import Callable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.education.content import ASSET_INFO, TUTORIAL_STEPS


_BG     = "#0b0f1a"
_SURF   = "#111827"
_SURF2  = "#1a2235"
_BORDER = "#1e2d45"
_ACCENT = "#2563eb"
_GREEN  = "#10b981"
_RED    = "#ef4444"
_AMBER  = "#f59e0b"
_TEXT   = "#e2e8f0"
_TEXT2  = "#94a3b8"
_TEXT3  = "#64748b"


# ── tiny helpers ──────────────────────────────────────────────────────────────

def _lbl(text: str = "", *, bold: bool = False, size: int = 0,
         color: str = "", align: Qt.AlignmentFlag | None = None) -> QLabel:
    w = QLabel(text)
    f = QFont()
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


def _section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setStyleSheet(
        f"color:{_AMBER}; font-size:11px; font-weight:700; letter-spacing:1px;"
        f"border-bottom:1px solid {_BORDER}; padding-bottom:4px;"
    )
    return lbl


def _input_style() -> str:
    return (
        f"QDoubleSpinBox {{background:{_SURF2}; border:1px solid {_BORDER};"
        f"border-radius:5px; color:{_TEXT}; padding:0 8px; font-size:13px; min-height:32px;}}"
        f"QDoubleSpinBox:focus{{border-color:{_ACCENT};}}"
        f"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button"
        f"{{width:16px; background:{_BORDER}; border:none;}}"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  1. K/Z Hesaplayıcı — interactive profit/loss calculator
# ══════════════════════════════════════════════════════════════════════════════

class PLCalculatorWidget(QWidget):
    """Etkileşimli Kar / Zarar hesaplayıcı."""

    def __init__(self) -> None:
        super().__init__()
        self._build()

    def _build(self) -> None:
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(10)
        vl.addWidget(_section("ETKİLEŞİMLİ K/Z HESAPLAYICI"))

        hint = _lbl(
            "Değerleri değiştirin — formül anında hesaplanır.",
            color=_TEXT3,
        )
        hint.setWordWrap(True)
        vl.addWidget(hint)

        # input row
        inp_row = QHBoxLayout()
        inp_row.setSpacing(12)

        def _grp(label: str, default: float, prefix: str = "TL ") -> QDoubleSpinBox:
            col = QVBoxLayout()
            col.setSpacing(4)
            col.addWidget(_lbl(label, color=_TEXT3, bold=True))
            sp = QDoubleSpinBox()
            sp.setRange(0.01, 100_000_000)
            sp.setDecimals(2)
            sp.setValue(default)
            if prefix:
                sp.setPrefix(prefix)
            sp.setStyleSheet(_input_style())
            col.addWidget(sp)
            inp_row.addLayout(col, 1)
            return sp

        self.sp_buy = _grp("Alış Fiyatı",   50_000.0)
        self.sp_cur = _grp("Güncel Fiyat",   55_000.0)
        self.sp_qty = _grp("Miktar (Adet)",      2.0, prefix="")
        vl.addLayout(inp_row)

        # result card
        res = QFrame()
        res.setStyleSheet(
            f"background:{_SURF}; border:1px solid {_BORDER}; border-radius:8px;"
        )
        res_vl = QVBoxLayout(res)
        res_vl.setContentsMargins(18, 14, 18, 14)
        res_vl.setSpacing(8)

        self.res_main = _lbl(
            "—", bold=True, size=20,
            align=Qt.AlignmentFlag.AlignCenter,
        )
        res_vl.addWidget(self.res_main)

        self.bar = _PLBar()
        self.bar.setFixedHeight(24)
        res_vl.addWidget(self.bar)

        detail_row = QHBoxLayout()
        self.cost_lbl = _lbl("", color=_TEXT2)
        self.val_lbl  = _lbl("", color=_TEXT2)
        detail_row.addWidget(self.cost_lbl)
        detail_row.addStretch()
        detail_row.addWidget(self.val_lbl)
        res_vl.addLayout(detail_row)

        self.formula_lbl = _lbl("", color=_TEXT3)
        self.formula_lbl.setWordWrap(True)
        res_vl.addWidget(self.formula_lbl)

        vl.addWidget(res)

        self.sp_buy.valueChanged.connect(self._recalc)
        self.sp_cur.valueChanged.connect(self._recalc)
        self.sp_qty.valueChanged.connect(self._recalc)
        self._recalc()

    def _recalc(self) -> None:
        buy   = self.sp_buy.value()
        cur   = self.sp_cur.value()
        qty   = self.sp_qty.value()
        cost  = buy * qty
        value = cur * qty
        pl    = value - cost
        pct   = (pl / cost * 100) if cost > 0 else 0.0
        ratio = (pl / cost) if cost > 0 else 0.0

        color = _GREEN if pl >= 0 else _RED
        sign  = "+" if pl >= 0 else ""
        emoji = "🟢" if pl >= 0 else "🔴"

        self.res_main.setText(
            f"{emoji}  K/Z: {sign}TL {pl:,.0f}  ({sign}{pct:.2f}%)"
        )
        self.res_main.setStyleSheet(
            f"color:{color}; font-size:20px; font-weight:800;"
        )
        self.bar.set_ratio(ratio)
        self.cost_lbl.setText(f"Yatırılan: TL {cost:,.2f}")
        self.val_lbl.setText(f"Güncel Değer: TL {value:,.2f}")

        if abs(pct) < 0.01:
            note = "Fiyat değişmedi — K/Z sıfır."
        elif pct > 0:
            note = (
                f"Formül: ({cur:,.0f} − {buy:,.0f}) × {qty:.4g} = +TL {pl:,.0f}\n"
                f"Her 100 TL yatırım için {pct:.1f} TL kazandınız."
            )
        else:
            note = (
                f"Formül: ({cur:,.0f} − {buy:,.0f}) × {qty:.4g} = TL {pl:,.0f}\n"
                "Değer düştü — ama satmadıkça bu 'kâğıt üzerinde' bir kayıptır."
            )
        self.formula_lbl.setText(note)

    def set_price(self, buy: float, cur: float) -> None:
        self.sp_buy.setValue(buy)
        self.sp_cur.setValue(cur)


class _PLBar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._ratio = 0.0

    def set_ratio(self, r: float) -> None:
        self._ratio = max(-1.0, min(1.0, r))
        self.update()

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(_SURF2))
        cx = w // 2
        p.setPen(QPen(QColor(_BORDER), 1))
        p.drawLine(cx, 0, cx, h)
        fill = int(cx * min(abs(self._ratio) * 4, 1.0))
        color = QColor(_GREEN if self._ratio >= 0 else _RED)
        if self._ratio >= 0:
            p.fillRect(cx, 3, fill, h - 6, color)
        else:
            p.fillRect(cx - fill, 3, fill, h - 6, color)
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  2. Volatilite Demo — animated dual-chart
# ══════════════════════════════════════════════════════════════════════════════

class VolatilityDemoWidget(QWidget):
    """Canlı animasyonlu volatilite karşılaştırması (BTC vs Altın)."""

    def __init__(self) -> None:
        super().__init__()
        self._btc  = [50_000.0]
        self._gold = [50_000.0]
        self._running = True
        self._build()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(500)

    def _build(self) -> None:
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.addWidget(_section("CANLI VOLATİLİTE KARŞILAŞTIRMASI"))
        hdr.addStretch()
        self.btn_toggle = QPushButton("⏸ Duraklat")
        self.btn_toggle.setFixedSize(100, 28)
        self.btn_toggle.setStyleSheet(
            f"background:{_SURF2}; color:{_TEXT2}; border:1px solid {_BORDER};"
            f"border-radius:5px; font-size:11px;"
        )
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.clicked.connect(self._toggle)
        hdr.addWidget(self.btn_toggle)
        vl.addLayout(hdr)

        charts = QHBoxLayout()
        charts.setSpacing(10)
        self._btc_chart  = _MiniLineChart("₿  Bitcoin (Kripto)",  _RED)
        self._gold_chart = _MiniLineChart("🥇  Altın (Emtia)",    _GREEN)
        for c in (self._btc_chart, self._gold_chart):
            c.setMinimumHeight(140)
        charts.addWidget(self._btc_chart,  1)
        charts.addWidget(self._gold_chart, 1)
        vl.addLayout(charts)

        note = _lbl(
            "Bitcoin çok daha büyük ve hızlı dalgalanmalar gösterir → yüksek risk, yüksek fırsat. "
            "Altın ise sakin seyreder → düşük risk, düşük getiri. Bu farka 'volatilite' denir.",
            color=_TEXT3,
        )
        note.setWordWrap(True)
        vl.addWidget(note)

    def _tick(self) -> None:
        MAX = 60
        self._btc.append(max(self._btc[-1] * (1 + random.gauss(0, 0.030)), 1))
        self._gold.append(max(self._gold[-1] * (1 + random.gauss(0, 0.003)), 1))
        if len(self._btc)  > MAX: self._btc  = self._btc[-MAX:]
        if len(self._gold) > MAX: self._gold = self._gold[-MAX:]
        self._btc_chart.set_values(self._btc)
        self._gold_chart.set_values(self._gold)

    def _toggle(self) -> None:
        self._running = not self._running
        if self._running:
            self._timer.start(500)
            self.btn_toggle.setText("⏸ Duraklat")
        else:
            self._timer.stop()
            self.btn_toggle.setText("▶ Devam")


class _MiniLineChart(QWidget):
    def __init__(self, title: str, line_color: str) -> None:
        super().__init__()
        self._title = title
        self._color = line_color
        self._values: list[float] = []

    def set_values(self, v: list[float]) -> None:
        self._values = list(v)
        self.update()

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(_SURF))

        rect = self.rect().adjusted(8, 30, -8, -8)

        f = QFont()
        f.setPointSize(11)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(_TEXT2))
        p.drawText(self.rect().adjusted(8, 6, -8, 0),
                   Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, self._title)

        if len(self._values) < 2:
            p.setPen(QColor(_TEXT3))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Başlıyor…")
            p.end()
            return

        lo   = min(self._values)
        hi   = max(self._values)
        span = hi - lo or 1.0
        chg  = (self._values[-1] - self._values[0]) / self._values[0] * 100
        chg_c = _GREEN if chg >= 0 else _RED

        f2 = QFont("Consolas")
        f2.setPointSize(10)
        f2.setBold(True)
        p.setFont(f2)
        p.setPen(QColor(chg_c))
        p.drawText(self.rect().adjusted(8, 6, -8, 0),
                   Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
                   f"{chg:+.2f}%")

        p.setPen(QPen(QColor(_BORDER), 1))
        for i in range(1, 4):
            y = rect.top() + rect.height() * i / 4
            p.drawLine(rect.left(), int(y), rect.right(), int(y))

        pts = [
            (
                int(rect.left() + rect.width() * i / (len(self._values) - 1)),
                int(rect.bottom() - rect.height() * (v - lo) / span),
            )
            for i, v in enumerate(self._values)
        ]
        path = QPainterPath()
        path.moveTo(pts[0][0], rect.bottom())
        for x, y in pts:
            path.lineTo(x, y)
        path.lineTo(pts[-1][0], rect.bottom())
        path.closeSubpath()

        grad = QLinearGradient(0, rect.top(), 0, rect.bottom())
        c1, c2 = QColor(self._color), QColor(self._color)
        c1.setAlpha(70)
        c2.setAlpha(0)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)

        p.setPen(QPen(QColor(self._color), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            p.drawLine(x1, y1, x2, y2)

        p.setPen(QColor(self._color))
        p.setBrush(QColor(self._color))
        lx, ly = pts[-1]
        p.drawEllipse(lx - 5, ly - 5, 10, 10)

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  3. Risk Karşılaştırma — horizontal bar chart by asset
# ══════════════════════════════════════════════════════════════════════════════

class RiskComparisonWidget(QWidget):
    """CSV verisi verilirse volatiliteye göre risk karşılaştırması gösterir."""

    def __init__(self, feature_datasets: dict | None = None) -> None:
        super().__init__()
        self._feature_datasets = feature_datasets or {}
        self._build()

    def _risk_from_volatility(self, volatility: float) -> tuple[str, str]:
        vol_pct = volatility * 100

        if vol_pct < 1:
            return "Düşük", _GREEN
        if vol_pct < 3:
            return "Orta", _AMBER
        if vol_pct < 6:
            return "Yüksek", _RED

        return "Çok Yüksek", "#ff3060"

    def _build(self) -> None:
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(8)
        vl.addWidget(_section("VARLIK RİSK KARŞILAŞTIRMASI  (CSV Volatilitesine Göre)"))

        if not self._feature_datasets:
            msg = _lbl(
                "Risk karşılaştırması için CSV verisi bulunamadı.",
                color=_TEXT3,
            )
            msg.setWordWrap(True)
            vl.addWidget(msg)
            return

        sorted_assets = sorted(
            self._feature_datasets.items(),
            key=lambda item: item[1].last_volatility,
        )

        max_vol = max((feat.last_volatility for _, feat in sorted_assets), default=1.0)

        for sym, feat in sorted_assets:
            volatility = feat.last_volatility
            vol_pct = volatility * 100
            ratio = volatility / max_vol if max_vol > 0 else 0.0
            risk, color = self._risk_from_volatility(volatility)

            edu = ASSET_INFO.get(sym, {})

            row = QHBoxLayout()
            row.setSpacing(8)

            sym_lbl = _lbl(sym, bold=True, color=_TEXT)
            sym_lbl.setFixedWidth(44)
            row.addWidget(sym_lbl)

            bar = _HBar(color, ratio)
            bar.setFixedHeight(16)
            row.addWidget(bar, 1)

            vol_lbl = _lbl(f"{vol_pct:.2f}%/gün", color=_TEXT2)
            vol_lbl.setFixedWidth(90)
            row.addWidget(vol_lbl)

            risk_lbl = _lbl(risk, color=color)
            risk_lbl.setFixedWidth(90)
            row.addWidget(risk_lbl)

            desc_lbl = _lbl(edu.get("desc", "")[:60], color=_TEXT3)
            row.addWidget(desc_lbl, 1)

            vl.addLayout(row)

        note = _lbl(
            "Bu karşılaştırma yüklenen CSV dosyalarından hesaplanan volatiliteye göre yapılır.",
            color=_TEXT3,
        )
        note.setWordWrap(True)
        vl.addWidget(note)
        vl.addStretch()
    """CSV verilerinden hesaplanan volatiliteye göre varlık risk karşılaştırması."""

    def __init__(self, feature_datasets: dict | None = None) -> None:
        super().__init__()
        self._feature_datasets = feature_datasets or {}
        self._build()

    def _risk_from_volatility(self, volatility: float) -> tuple[str, str]:
        """
        volatility = 0.025 ise yaklaşık %2.5 günlük oynaklık anlamına gelir.
        """
        vol_pct = volatility * 100

        if vol_pct < 1:
            return "Düşük", _GREEN

        if vol_pct < 3:
            return "Orta", _AMBER

        if vol_pct < 6:
            return "Yüksek", _RED

        return "Çok Yüksek", "#ff3060"

    def _asset_name_from_csv(self, sym: str, feat) -> str:
        """
        CSV içindeki Name sütunundan varlık adını bulur.
        Name yoksa sembolü döndürür.
        """
        df = feat.df

        if "Name" in df.columns and not df["Name"].dropna().empty:
            return str(df["Name"].dropna().iloc[0])

        return sym

    def _build(self) -> None:
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(8)
        vl.addWidget(
            _section("VARLIK RİSK KARŞILAŞTIRMASI  (CSV Volatilitesine Göre)")
        )

        if not self._feature_datasets:
            empty_lbl = _lbl(
                "CSV verisi bulunamadı. Risk karşılaştırması için data/raw klasörüne geçerli CSV dosyaları ekleyin.",
                color=_TEXT3,
            )
            empty_lbl.setWordWrap(True)
            vl.addWidget(empty_lbl)
            vl.addStretch()
            return

        sorted_assets = sorted(
            self._feature_datasets.items(),
            key=lambda item: item[1].last_volatility,
        )

        max_vol = max(
            (feat.last_volatility for _, feat in sorted_assets),
            default=1.0,
        )

        for sym, feat in sorted_assets:
            volatility = feat.last_volatility
            vol_pct = volatility * 100
            ratio = volatility / max_vol if max_vol > 0 else 0.0

            risk, color = self._risk_from_volatility(volatility)

            edu = ASSET_INFO.get(sym, {})
            asset_name = self._asset_name_from_csv(sym, feat)

            row = QHBoxLayout()
            row.setSpacing(8)

            sym_lbl = _lbl(sym, bold=True, color=_TEXT)
            sym_lbl.setFixedWidth(44)
            row.addWidget(sym_lbl)

            bar = _HBar(color, ratio)
            bar.setFixedHeight(16)
            row.addWidget(bar, 1)

            vol_lbl = _lbl(f"{vol_pct:.2f}%/gün", color=_TEXT2)
            vol_lbl.setFixedWidth(90)
            row.addWidget(vol_lbl)

            risk_lbl = _lbl(risk, color=color)
            risk_lbl.setFixedWidth(90)
            row.addWidget(risk_lbl)

            desc = edu.get("desc", asset_name)
            desc_lbl = _lbl(desc[:60], color=_TEXT3)
            row.addWidget(desc_lbl, 1)

            vl.addLayout(row)

        note = _lbl(
            "Bu karşılaştırma, yüklenen CSV dosyalarından hesaplanan son 7 günlük volatiliteye göre yapılır.",
            color=_TEXT3,
        )
        note.setWordWrap(True)
        vl.addWidget(note)
        vl.addStretch()
    """Tüm varlıkların volatilite karşılaştırması."""

    def __init__(self) -> None:
        super().__init__()
        self._build()

    def _build(self) -> None:
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(8)
        vl.addWidget(_section("VARLIK RİSK KARŞILAŞTIRMASI  (Günlük Ortalama Oynaklık)"))

        sorted_assets = sorted(EDU_ASSET_RISK_DEMO.items(), key=lambda x: x[1]["vol"])
        max_vol = max(v["vol"] for _, v in sorted_assets)

        _risk_colors = {
            "Düşük": _GREEN, "Orta": _AMBER,
            "Yüksek": _RED,  "Çok Yüksek": "#ff3060",
        }

        for sym, info in sorted_assets:
            edu     = ASSET_INFO.get(sym, {})
            risk    = edu.get("risk", "Orta")
            col     = _risk_colors.get(risk, _AMBER)
            vol_pct = info["vol"] * 100
            ratio   = info["vol"] / max_vol

            row = QHBoxLayout()
            row.setSpacing(8)

            sym_lbl = _lbl(sym, bold=True, color=_TEXT)
            sym_lbl.setFixedWidth(44)
            row.addWidget(sym_lbl)

            bar = _HBar(col, ratio)
            bar.setFixedHeight(16)
            row.addWidget(bar, 1)

            vol_lbl = _lbl(f"{vol_pct:.1f}%/gün", color=_TEXT2)
            vol_lbl.setFixedWidth(76)
            row.addWidget(vol_lbl)

            risk_lbl = _lbl(risk, color=col)
            risk_lbl.setFixedWidth(80)
            row.addWidget(risk_lbl)

            desc_lbl = _lbl(edu.get("desc", "")[:50], color=_TEXT3)
            row.addWidget(desc_lbl, 1)

            vl.addLayout(row)

        note = _lbl(
            "Çubuk ne kadar uzunsa, fiyat o kadar çok dalgalanır. "
            "Kripto paralar hisse senetlerinden 2-5 kat daha volatildir.",
            color=_TEXT3,
        )
        note.setWordWrap(True)
        vl.addWidget(note)
        vl.addStretch()


class _HBar(QWidget):
    def __init__(self, color: str, ratio: float) -> None:
        super().__init__()
        self._color = color
        self._ratio = ratio

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(_SURF2))
        bw = int(self.width() * self._ratio)
        if bw > 0:
            p.fillRect(0, 2, bw, self.height() - 4, QColor(self._color))
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  4. DCA Simülatör — dollar-cost averaging demo
# ══════════════════════════════════════════════════════════════════════════════

class DCASimulatorWidget(QWidget):
    """DCA vs Toplu Alım karşılaştırma simülatörü."""

    def __init__(self) -> None:
        super().__init__()
        self._build()
        self._simulate()

    def _build(self) -> None:
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(10)
        vl.addWidget(_section("DCA (DÜZENLI ALIM) vs TOPLU ALIM SİMÜLATÖRÜ"))

        hint = _lbl(
            "Kaydırıcıları ayarlayın — hesaplama anında güncellenir.",
            color=_TEXT3,
        )
        vl.addWidget(hint)

        # sliders
        ctrl = QFrame()
        ctrl.setStyleSheet(
            f"background:{_SURF}; border:1px solid {_BORDER}; border-radius:8px;"
        )
        cl = QVBoxLayout(ctrl)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(8)

        def _slider(label: str, lo: int, hi: int, default: int,
                    unit: str, fmt: str = "{:,}") -> tuple[QSlider, QLabel]:
            hl = QHBoxLayout()
            hl.setSpacing(10)
            ll = _lbl(label, color=_TEXT3, bold=True)
            ll.setFixedWidth(140)
            hl.addWidget(ll)
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(lo, hi)
            sl.setValue(default)
            sl.setStyleSheet(
                f"QSlider::groove:horizontal{{background:{_SURF2}; height:6px; border-radius:3px;}}"
                f"QSlider::handle:horizontal{{background:{_ACCENT}; width:14px; height:14px; "
                f"margin:-4px 0; border-radius:7px;}}"
                f"QSlider::sub-page:horizontal{{background:{_ACCENT}; border-radius:3px;}}"
            )
            vl2 = _lbl(fmt.format(default) + f" {unit}", color=_TEXT, bold=True)
            vl2.setFixedWidth(100)
            hl.addWidget(sl, 1)
            hl.addWidget(vl2)
            cl.addLayout(hl)
            return sl, vl2

        self.sl_amt, self.sl_amt_lbl = _slider("Aylık Miktar", 500, 20000, 3000, "TL")
        self.sl_mo,  self.sl_mo_lbl  = _slider("Süre (Ay)",      3,    24,   12, "Ay", fmt="{}")
        vl.addWidget(ctrl)

        # summary boxes
        summ = QHBoxLayout()
        summ.setSpacing(8)
        for attr, label in (
            ("rb_dca_avg",  "DCA Ort. Maliyet"),
            ("rb_lump_avg", "Toplu Alım Maliyet"),
            ("rb_dca_val",  "DCA Son Değer"),
            ("rb_lump_val", "Toplu Alım Son Değer"),
        ):
            box = QFrame()
            box.setStyleSheet(
                f"background:{_SURF}; border:1px solid {_BORDER}; border-radius:7px;"
            )
            bl = QVBoxLayout(box)
            bl.setContentsMargins(12, 8, 12, 8)
            bl.setSpacing(3)
            bl.addWidget(_lbl(label, color=_TEXT3))
            lbl_v = _lbl("—", bold=True, color=_TEXT)
            setattr(self, attr, lbl_v)
            bl.addWidget(lbl_v)
            summ.addWidget(box, 1)
        vl.addLayout(summ)

        # result table
        self.tbl = QTableWidget(0, 5)
        self.tbl.setObjectName("tbl")
        self.tbl.setHorizontalHeaderLabels(
            ["Ay", "Fiyat (TL)", "DCA Alım Birimi", "DCA Ort. Maliyet", "Toplam Değer"]
        )
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.tbl.setShowGrid(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setMaximumHeight(180)
        for c in range(5):
            self.tbl.horizontalHeader().setSectionResizeMode(c, self.tbl.horizontalHeader().ResizeMode.Stretch)
        self.tbl.setStyleSheet(
            f"QTableWidget{{background:{_SURF}; border:1px solid {_BORDER}; color:{_TEXT}; font-size:11px;}}"
            f"QTableWidget::item{{padding:5px 8px;}}"
            f"QTableWidget::item:alternate{{background:{_SURF2};}}"
            f"QHeaderView::section{{background:{_SURF2}; color:{_TEXT3}; padding:5px 8px; "
            f"border:none; border-bottom:1px solid {_BORDER}; font-size:10px; font-weight:700;}}"
        )
        vl.addWidget(self.tbl)

        # chart
        self._chart = _DCAChart()
        self._chart.setMinimumHeight(140)
        vl.addWidget(self._chart)

        # insight
        self.insight = _lbl("", color=_TEXT2)
        self.insight.setWordWrap(True)
        vl.addWidget(self.insight)

        self.sl_amt.valueChanged.connect(self._on_slide)
        self.sl_mo.valueChanged.connect(self._on_slide)

    def _on_slide(self) -> None:
        self.sl_amt_lbl.setText(f"TL {self.sl_amt.value():,}")
        self.sl_mo_lbl.setText(f"{self.sl_mo.value()} Ay")
        self._simulate()

    def _simulate(self) -> None:
        monthly = self.sl_amt.value()
        months  = self.sl_mo.value()

        rng = random.Random(42)
        price = 50_000.0
        prices = [price]
        for _ in range(months - 1):
            prices.append(max(prices[-1] * (1 + rng.gauss(0.005, 0.06)), 100))

        # DCA
        dca_units = 0.0
        dca_cost  = 0.0
        dca_vals  = []
        rows = []
        for i, px in enumerate(prices):
            units = monthly / px
            dca_units += units
            dca_cost  += monthly
            avg = dca_cost / dca_units
            val = dca_units * px
            dca_vals.append(val)
            rows.append((i + 1, px, units, avg, val))

        # Lump sum
        total_budget = monthly * months
        lump_units   = total_budget / prices[0]
        lump_vals    = [lump_units * px for px in prices]

        # summary
        dca_final    = dca_units * prices[-1]
        lump_final   = lump_units * prices[-1]
        dca_avg      = dca_cost / dca_units if dca_units else 0
        dca_pl_pct   = (dca_final - monthly * months) / (monthly * months) * 100
        lump_pl_pct  = (lump_final - total_budget) / total_budget * 100

        def _sign_style(v: float) -> str:
            c = _GREEN if v >= 0 else _RED
            return f"color:{c}; font-weight:700;"

        self.rb_dca_avg.setText(f"TL {dca_avg:,.0f}")
        self.rb_lump_avg.setText(f"TL {prices[0]:,.0f}")
        self.rb_dca_val.setText(f"TL {dca_final:,.0f}  ({dca_pl_pct:+.1f}%)")
        self.rb_dca_val.setStyleSheet(_sign_style(dca_pl_pct))
        self.rb_lump_val.setText(f"TL {lump_final:,.0f}  ({lump_pl_pct:+.1f}%)")
        self.rb_lump_val.setStyleSheet(_sign_style(lump_pl_pct))

        # table
        self.tbl.setRowCount(len(rows))
        for r, (mo, px, units, avg, val) in enumerate(rows):
            for c, txt in enumerate([
                str(mo), f"{px:,.0f}", f"{units:.6f}", f"{avg:,.0f}", f"{val:,.0f}"
            ]):
                item = QTableWidgetItem(txt)
                item.setTextAlignment(int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter))
                item.setForeground(QColor(_TEXT))
                self.tbl.setItem(r, c, item)

        self._chart.set_data(prices, dca_vals, lump_vals)

        if dca_final > lump_final:
            self.insight.setText(
                f"✅  Bu senaryoda DCA daha iyi! Ortalama maliyetinizi TL {dca_avg:,.0f}'a düşürdünüz. "
                f"Toplu alım maliyeti TL {prices[0]:,.0f}'da kaldı."
            )
        else:
            self.insight.setText(
                "ℹ️  Bu senaryoda fiyat genel olarak yükseldiği için toplu alım daha iyi göründü. "
                "Gerçekte piyasanın yönünü önceden bilmek çok zordur — DCA bu belirsizliği azaltır."
            )


class _DCAChart(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._prices: list[float] = []
        self._dca:    list[float] = []
        self._lump:   list[float] = []

    def set_data(self, prices: list[float], dca: list[float], lump: list[float]) -> None:
        self._prices = prices
        self._dca    = dca
        self._lump   = lump
        self.update()

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(_SURF))

        if len(self._dca) < 2:
            p.end()
            return

        rect = self.rect().adjusted(10, 10, -10, -28)
        all_v = self._dca + self._lump
        lo    = min(all_v) * 0.98
        hi    = max(all_v) * 1.02
        span  = hi - lo or 1.0
        n     = len(self._dca)

        def _pts(series: list[float]) -> list[tuple[int, int]]:
            return [
                (
                    int(rect.left() + rect.width() * i / (n - 1)),
                    int(rect.bottom() - rect.height() * (v - lo) / span),
                )
                for i, v in enumerate(series)
            ]

        for series, color in ((self._dca, _ACCENT), (self._lump, _AMBER)):
            pts = _pts(series)
            p.setPen(QPen(QColor(color), 2))
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                p.drawLine(x1, y1, x2, y2)

        f = QFont()
        f.setPointSize(9)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(_ACCENT))
        p.drawText(10, self.height() - 6, "─── DCA (Aylık Alım)")
        p.setPen(QColor(_AMBER))
        p.drawText(200, self.height() - 6, "─── Toplu Alım")
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  5. Görev Kartları
# ══════════════════════════════════════════════════════════════════════════════

_MISSION_EXTRAS: dict[str, dict] = {
    "view_market":    {"icon": "👁",  "xp": 50,  "hint": "'İşlem' sayfasında fiyatların değişimini izleyin."},
    "first_buy":      {"icon": "🛒",  "xp": 100, "hint": "Herhangi bir varlıktan alım yapın."},
    "check_portfolio":{"icon": "📊",  "xp": 50,  "hint": "'Özet' sayfasında portföyünüzü inceleyin."},
    "first_sell":     {"icon": "💰",  "xp": 150, "hint": "Elinizdeki bir varlığı satın."},
    "check_history":  {"icon": "📋",  "xp": 50,  "hint": "'Geçmiş' sayfasında işlemlerinizi görün."},
    "run_analysis":   {"icon": "🔬",  "xp": 200, "hint": "'Analiz' sekmesinde senaryo simülasyonu çalıştırın."},
}


class MissionCard(QFrame):
    def __init__(
        self,
        mission: dict,
        done: bool,
        navigate_cb: Callable[[int], None],
    ) -> None:
        super().__init__()
        self.setObjectName("missionCard" + ("Done" if done else ""))
        self._build(mission, done, navigate_cb)

    def _build(self, mission: dict, done: bool, navigate_cb: Callable[[int], None]) -> None:
        hl = QHBoxLayout(self)
        hl.setContentsMargins(14, 12, 14, 12)
        hl.setSpacing(14)

        extras  = _MISSION_EXTRAS.get(mission["id"], {})
        icon    = extras.get("icon", "○")
        xp      = extras.get("xp", 0)
        hint    = extras.get("hint", mission["desc"])

        icon_lbl = QLabel(icon if done else icon)
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            f"font-size:22px; background:{_SURF2}; border:1px solid "
            f"{'#065f46' if done else _BORDER}; border-radius:6px;"
        )
        hl.addWidget(icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(3)

        title_row = QHBoxLayout()
        title_lbl = QLabel(mission["title"])
        title_lbl.setStyleSheet(
            f"color:{'#64748b' if done else _TEXT}; font-size:13px; font-weight:700;"
        )
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        xp_lbl = QLabel(f"+{xp} XP")
        xp_lbl.setStyleSheet(
            f"color:{'#10b981' if done else '#44556a'}; font-size:11px; font-weight:700;"
        )
        title_row.addWidget(xp_lbl)

        if done:
            done_badge = QLabel("✓ Tamamlandı")
            done_badge.setStyleSheet(
                f"color:{_GREEN}; font-size:10px; font-weight:700; "
                f"background:#061f12; border:1px solid #065f46; "
                f"border-radius:4px; padding:1px 6px;"
            )
            title_row.addWidget(done_badge)

        col.addLayout(title_row)

        desc_lbl = QLabel(hint)
        desc_lbl.setStyleSheet(f"color:{_TEXT3}; font-size:11px;")
        desc_lbl.setWordWrap(True)
        col.addWidget(desc_lbl)
        hl.addLayout(col, 1)

        if not done:
            go_btn = QPushButton("Git →")
            go_btn.setFixedSize(64, 30)
            go_btn.setStyleSheet(
                f"background:{_ACCENT}; color:white; border:none; "
                f"border-radius:5px; font-size:11px; font-weight:700;"
            )
            go_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            go_btn.clicked.connect(lambda: navigate_cb(mission["page"]))
            hl.addWidget(go_btn)


class MissionPanelWidget(QScrollArea):
    def __init__(self, navigate_cb: Callable[[int], None]) -> None:
        super().__init__()
        self._navigate_cb = navigate_cb
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._inner = QWidget()
        self._vl    = QVBoxLayout(self._inner)
        self._vl.setContentsMargins(0, 0, 0, 0)
        self._vl.setSpacing(8)
        self.setWidget(self._inner)

    def refresh(self, done_map: dict[str, bool]) -> None:
        while self._vl.count():
            item = self._vl.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        completed = sum(1 for v in done_map.values() if v)
        total_xp  = sum(
            _MISSION_EXTRAS.get(sid, {}).get("xp", 0)
            for sid, done in done_map.items()
            if done
        )
        max_xp = sum(_MISSION_EXTRAS.get(s["id"], {}).get("xp", 0) for s in TUTORIAL_STEPS)

        # header
        hdr = QHBoxLayout()
        title_lbl = QLabel(f"🎯  Görevler  —  {completed}/{len(done_map)} tamamlandı")
        title_lbl.setStyleSheet(f"color:{_TEXT}; font-size:15px; font-weight:800;")
        xp_lbl = QLabel(f"⚡ {total_xp} / {max_xp} XP")
        xp_lbl.setStyleSheet(f"color:{_AMBER}; font-size:13px; font-weight:700;")
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        hdr.addWidget(xp_lbl)
        self._vl.addLayout(hdr)

        # XP progress bar
        xp_bar = _XPBar(total_xp / max_xp if max_xp > 0 else 0.0)
        xp_bar.setFixedHeight(10)
        self._vl.addWidget(xp_bar)
        self._vl.addSpacing(10)

        if completed == len(done_map):
            done_lbl = QLabel(
                "🏆  Tüm görevleri tamamladınız! "
                "Artık kripto para yatırımlarının temellerini uygulamalı olarak öğrendiniz."
            )
            done_lbl.setStyleSheet(
                f"color:{_GREEN}; font-size:13px; font-weight:700; "
                f"background:#061f12; border:1px solid #065f46; "
                f"border-radius:8px; padding:12px 16px;"
            )
            done_lbl.setWordWrap(True)
            self._vl.addWidget(done_lbl)
            self._vl.addSpacing(10)

        for step in TUTORIAL_STEPS:
            done = done_map.get(step["id"], False)
            card = MissionCard(step, done, self._navigate_cb)
            self._vl.addWidget(card)

        self._vl.addStretch()


class _XPBar(QWidget):
    def __init__(self, ratio: float) -> None:
        super().__init__()
        self._ratio = ratio

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(_SURF2))
        bw = int(self.width() * self._ratio)
        if bw > 0:
            grad = QLinearGradient(0, 0, self.width(), 0)
            grad.setColorAt(0.0, QColor(_ACCENT))
            grad.setColorAt(1.0, QColor(_GREEN))
            p.fillRect(0, 0, bw, self.height(), QBrush(grad))
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  6. Portföy Dağılımı — live interactive pie / allocation bars
# ══════════════════════════════════════════════════════════════════════════════

class PortfolioAllocationWidget(QWidget):
    """Gösterir: portföyün nasıl dağıtıldığını ve çeşitlendirme etkisini."""

    # Default slices when no real portfolio available
    _DEFAULT = [
        ("BTC",  35, "#ef4444"),
        ("ETH",  20, "#f59e0b"),
        ("AAPL", 15, "#3b82f6"),
        ("GOLD", 15, "#10b981"),
        ("NAKIT",15, "#64748b"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._slices: list[tuple[str, float, str]] = list(self._DEFAULT)
        self._build()

    def _build(self) -> None:
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(10)
        vl.addWidget(_section("PORTFÖY DAĞILIMI GÖSTERGESI"))

        row = QHBoxLayout()
        row.setSpacing(16)

        # pie chart
        self._pie = _PieChart()
        self._pie.setMinimumSize(180, 180)
        self._pie.setMaximumSize(200, 200)
        row.addWidget(self._pie)

        # legend + bars
        self._bar_col = QVBoxLayout()
        self._bar_col.setSpacing(6)
        row.addLayout(self._bar_col, 1)

        vl.addLayout(row)

        note = _lbl(
            "Renk ne kadar çok varsa, portföyün o kadar tek bir varlığa bağımlı. "
            "Birden fazla rengi dengeli tut → risk dağılır.",
            color=_TEXT3,
        )
        note.setWordWrap(True)
        vl.addWidget(note)

        self._refresh_bars()

    def set_slices(self, slices: list[tuple[str, float, str]]) -> None:
        """Update with real portfolio data: [(symbol, pct, color), ...]"""
        if slices:
            self._slices = slices
            self._pie.set_slices(slices)
            self._refresh_bars()

    def _refresh_bars(self) -> None:
        while self._bar_col.count():
            item = self._bar_col.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._pie.set_slices(self._slices)
        for sym, pct, color in self._slices:
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{color}; font-size:14px;")
            dot.setFixedWidth(20)
            row.addWidget(dot)
            sym_lbl = _lbl(sym, bold=True, color=_TEXT)
            sym_lbl.setFixedWidth(48)
            row.addWidget(sym_lbl)
            bar = _HBar(color, pct / 100.0)
            bar.setFixedHeight(14)
            row.addWidget(bar, 1)
            pct_lbl = _lbl(f"{pct:.0f}%", color=color)
            pct_lbl.setFixedWidth(36)
            row.addWidget(pct_lbl)
            w = QWidget()
            w.setLayout(row)
            self._bar_col.addWidget(w)


class _PieChart(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._slices: list[tuple[str, float, str]] = []

    def set_slices(self, slices: list[tuple[str, float, str]]) -> None:
        self._slices = slices
        self.update()

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("transparent"))
        if not self._slices:
            p.end()
            return

        side = min(self.width(), self.height()) - 10
        x    = (self.width()  - side) // 2
        y    = (self.height() - side) // 2
        total = sum(pct for _, pct, _ in self._slices)
        angle = 0
        for sym, pct, color in self._slices:
            span = int(360 * 16 * pct / total) if total else 0
            p.setBrush(QColor(color))
            p.setPen(QPen(QColor(_BG), 2))
            p.drawPie(x, y, side, side, angle, span)
            angle += span
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  7. Alım/Satım Akış — animated step-by-step trade flow
# ══════════════════════════════════════════════════════════════════════════════

class TradingFlowWidget(QWidget):
    """Adım adım alım/satım akışını görsel olarak gösterir."""

    _STEPS = [
        ("1", "Varlık Seç", "Sol listeden bir sembol seç (örn. BTC)", _ACCENT),
        ("2", "Miktar Gir",  "Kaç adet veya TL değerinde almak istediğini yaz", "#8b5cf6"),
        ("3", "Fiyat Anında Hesapla", "Toplam TL = Fiyat × Miktar", _AMBER),
        ("4", "Onayla", "Butona bas — nakit düşer, pozisyon açılır", _GREEN),
        ("5", "İzle & Sat", "Değer yükselince aynı adımları SAT için yap", _RED),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._active = 0
        self._build()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_step)
        self._timer.start(1800)

    def _build(self) -> None:
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(10)
        vl.addWidget(_section("NASIL İŞLEM YAPILIR?  (Otomatik Canlandırma)"))

        self._step_widgets: list[QFrame] = []
        for num, title, desc, color in self._STEPS:
            card = QFrame()
            card.setObjectName("tradeStep")
            hl = QHBoxLayout(card)
            hl.setContentsMargins(14, 10, 14, 10)
            hl.setSpacing(14)

            num_lbl = QLabel(num)
            num_lbl.setFixedSize(32, 32)
            num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num_lbl.setStyleSheet(
                f"font-size:14px; font-weight:800; border-radius:16px; "
                f"background:{_SURF2}; color:{_TEXT3};"
            )
            hl.addWidget(num_lbl)

            col = QVBoxLayout()
            col.setSpacing(2)
            t = QLabel(title)
            t.setStyleSheet(f"color:{_TEXT3}; font-size:12px; font-weight:700;")
            d = QLabel(desc)
            d.setStyleSheet(f"color:{_TEXT3}; font-size:11px;")
            col.addWidget(t)
            col.addWidget(d)
            hl.addLayout(col, 1)

            card.setStyleSheet(
                f"background:{_SURF}; border:1px solid {_BORDER}; border-radius:7px;"
            )
            card._num     = num_lbl  # type: ignore[attr-defined]
            card._title   = t        # type: ignore[attr-defined]
            card._color   = color    # type: ignore[attr-defined]
            self._step_widgets.append(card)
            vl.addWidget(card)

        self._highlight(0)

    def _highlight(self, idx: int) -> None:
        for i, card in enumerate(self._step_widgets):
            active = (i == idx)
            color  = card._color if active else _BORDER  # type: ignore[attr-defined]
            card.setStyleSheet(
                f"background:{'#0f1f35' if active else _SURF}; "
                f"border:1px solid {color}; border-radius:7px;"
            )
            card._num.setStyleSheet(  # type: ignore[attr-defined]
                f"font-size:14px; font-weight:800; border-radius:16px; "
                f"background:{color}; color:{'white' if active else _TEXT3};"
            )
            card._title.setStyleSheet(  # type: ignore[attr-defined]
                f"color:{color if active else _TEXT3}; "
                f"font-size:12px; font-weight:700;"
            )

    def _next_step(self) -> None:
        self._active = (self._active + 1) % len(self._STEPS)
        self._highlight(self._active)
