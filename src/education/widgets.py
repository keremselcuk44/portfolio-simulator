"""Interactive educational widgets — learning through doing, not just reading."""

from __future__ import annotations

import random

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
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


# ── Stub widgets (referenced by learn_page.py) ────────────────────────────────

class VolatilityDemoWidget(QWidget):
    """Placeholder — not yet implemented."""
    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__()

class MissionPanelWidget(QWidget):
    """Placeholder — not yet implemented."""
    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__()

class PortfolioAllocationWidget(QWidget):
    """Placeholder — not yet implemented."""
    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__()

class TradingFlowWidget(QWidget):
    """Placeholder — not yet implemented."""
    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__()

