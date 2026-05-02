"""Welcome / onboarding dialog shown on first launch."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_BG     = "#0b0f1a"
_SURF   = "#111827"
_BORDER = "#1e2d45"
_ACCENT = "#2563eb"
_GREEN  = "#10b981"
_AMBER  = "#f59e0b"
_TEXT   = "#e2e8f0"
_TEXT2  = "#94a3b8"
_TEXT3  = "#64748b"


class WelcomeDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.go_learn = False
        self.setWindowTitle("PortfolioSim — Hoş Geldiniz")
        self.setFixedSize(620, 580)
        self.setModal(True)
        self._build()
        self._style()

    def _build(self) -> None:
        vl = QVBoxLayout(self)
        vl.setContentsMargins(40, 36, 40, 28)
        vl.setSpacing(0)

        # ── header ────────────────────────────────────────────────────────────
        header = QLabel("◆  PortfolioSim'e Hoş Geldiniz!")
        header.setStyleSheet(f"color:{_TEXT}; font-size:20px; font-weight:800;")
        vl.addWidget(header)
        vl.addSpacing(10)

        sub = QLabel(
            "Kripto para yatırımlarını gerçek para riski olmadan öğrenmek için "
            "tasarlanmış bir simülasyon ortamı."
        )
        sub.setStyleSheet(f"color:{_TEXT2}; font-size:13px;")
        sub.setWordWrap(True)
        vl.addWidget(sub)
        vl.addSpacing(28)

        # ── feature cards ─────────────────────────────────────────────────────
        features = [
            ("⇄", _ACCENT,  "Alım / Satım Simülasyonu",
             "12 farklı varlık üzerinden gerçek bir borsayı andıran ortamda alım ve satım emirleri verin."),
            ("📊", _GREEN,  "Canlı Piyasa",
             "Fiyatlar her 3 saniyede bir güncellenir. Piyasa hareketlerini gerçek zamanlı izleyin."),
            ("📚", _AMBER,  "Öğrenme Merkezi",
             "Kripto para nedir, K/Z nasıl hesaplanır, volatilite ne demek — hepsini adım adım öğrenin."),
            ("💰", "#8b5cf6", "Güvenli Pratik",
             "TL 1.000.000 sanal başlangıç bakiyesi — gerçek para riski yok, dilediğinizce deneyin."),
        ]

        for icon, color, title, desc in features:
            row = QHBoxLayout()
            row.setSpacing(14)

            icon_lbl = QLabel(icon)
            icon_lbl.setFixedSize(44, 44)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_lbl.setStyleSheet(
                f"background:{color}22; border:1px solid {color}44; "
                f"border-radius:8px; font-size:20px;"
            )

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            t = QLabel(title)
            t.setStyleSheet(f"color:{_TEXT}; font-size:13px; font-weight:700;")
            d = QLabel(desc)
            d.setStyleSheet(f"color:{_TEXT2}; font-size:11px;")
            d.setWordWrap(True)
            text_col.addWidget(t)
            text_col.addWidget(d)

            row.addWidget(icon_lbl)
            row.addLayout(text_col, 1)

            card = QWidget()
            card.setStyleSheet(
                f"background:{_SURF}; border:1px solid {_BORDER}; border-radius:8px;"
            )
            card.setLayout(row)
            card.layout().setContentsMargins(14, 10, 14, 10)
            vl.addWidget(card)
            vl.addSpacing(6)

        vl.addSpacing(10)

        # ── balance notice ─────────────────────────────────────────────────────
        notice = QLabel("💰  Başlangıç bakiyeniz: TL 1.000.000  —  tamamen sanal, dilediğinizce deneyin!")
        notice.setStyleSheet(
            f"color:{_GREEN}; font-size:12px; font-weight:600; "
            f"background:#061f12; border:1px solid #065f46; "
            f"border-radius:6px; padding:8px 14px;"
        )
        notice.setWordWrap(True)
        vl.addWidget(notice)
        vl.addSpacing(22)

        # ── buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_learn = QPushButton("📚  Öğren Sayfasını Aç")
        self.btn_learn.setObjectName("btnLearn")
        self.btn_learn.setFixedHeight(44)
        self.btn_learn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_start = QPushButton("Başla  →")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.setFixedHeight(44)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_row.addWidget(self.btn_learn, 1)
        btn_row.addWidget(self.btn_start, 2)
        vl.addLayout(btn_row)

        self.btn_learn.clicked.connect(self._on_learn)
        self.btn_start.clicked.connect(self.accept)

    def _on_learn(self) -> None:
        self.go_learn = True
        self.accept()

    def _style(self) -> None:
        self.setStyleSheet(f"""
        QDialog {{
            background: {_BG};
            color: {_TEXT};
        }}
        QPushButton#btnStart {{
            background: {_ACCENT};
            color: white;
            border: none;
            border-radius: 7px;
            font-size: 14px;
            font-weight: 700;
        }}
        QPushButton#btnStart:hover {{ background: #1d4ed8; }}

        QPushButton#btnLearn {{
            background: {_SURF};
            color: {_AMBER};
            border: 1px solid #44330a;
            border-radius: 7px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton#btnLearn:hover {{ background: #1a140a; border-color: {_AMBER}; }}
        """)
