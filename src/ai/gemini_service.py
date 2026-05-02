"""GeminiService — replaceable API layer wrapping google-generativeai.

Design principles
-----------------
* Single responsibility: only knows how to talk to Gemini.
* Stateless context: callers pass the full context dict each time.
* Response cache keyed by (context_hash + question) — avoids duplicate calls.
* Graceful degradation: is_available=False when key/package missing.
* Non-blocking: provides a GeminiWorker (QThread) for UI use.
"""

from __future__ import annotations

import hashlib
import json
import os
from PyQt6.QtCore import QThread, pyqtSignal

# ── System instruction (shared across all prompt types) ───────────────────────

_SYSTEM_INSTRUCTION = (
    "You are a financial AI coach embedded in a portfolio management app. "
    "You receive structured portfolio data and must give exactly 1-2 sentences "
    "of specific, actionable advice. "
    "Always reference actual numbers, asset names, or percentages from the data. "
    "Never give generic advice like 'diversify your portfolio'. "
    "Instead say: 'BTC represents 72% of your portfolio — reduce it below 50% by buying ETH or AAPL.' "
    "If the user asks a question, answer it directly using the data. "
    "In learning mode, give a hint, not the full solution. "
    "Respond in the same language the user writes in (Turkish or English)."
)


# ── Async worker (QThread) ────────────────────────────────────────────────────

class GeminiWorker(QThread):
    """Run a Gemini API call off the main thread so the UI stays responsive."""

    result_ready = pyqtSignal(str)    # emitted with the AI response text
    failed       = pyqtSignal(str)    # emitted with a fallback rule-based message

    def __init__(
        self,
        service: "GeminiService",
        context: dict,
        question: str | None = None,
        fallback: str = "",
    ) -> None:
        super().__init__()
        self._service  = service
        self._context  = context
        self._question = question
        self._fallback = fallback

    def run(self) -> None:
        text = self._service.send_prompt(self._context, self._question)
        if text:
            self.result_ready.emit(text)
        else:
            self.failed.emit(self._fallback)


# ── GeminiService ─────────────────────────────────────────────────────────────

class GeminiService:
    """
    Thin, replaceable wrapper around google-generativeai.

    Swap this class for any other LLM service by keeping the same public API:
      - is_available  → bool
      - send_prompt(context, question=None)  → str | None
      - build_prompt(context, question=None) → str
      - make_worker(context, question, fallback) → GeminiWorker
    """

    MODEL_NAME       = "gemini-1.5-flash"
    MAX_OUTPUT_CHARS = 450
    MIN_OUTPUT_CHARS = 12
    MAX_CACHE_SIZE   = 60

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key    = api_key or self._read_key()
        self._model: object | None = None
        self._cache: dict[str, str] = {}
        self._available  = False
        self._error_msg  = ""
        self._init_model()

    # ── Initialisation ────────────────────────────────────────────────────────

    @staticmethod
    def _read_key() -> str:
        """Try env var, then .env file in project root."""
        key = os.environ.get("GEMINI_API_KEY", "")
        if key:
            return key
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        try:
            for line in open(env_path, encoding="utf-8"):
                line = line.strip()
                if line.startswith("GEMINI_API_KEY"):
                    _, _, val = line.partition("=")
                    return val.strip().strip('"').strip("'")
        except (FileNotFoundError, OSError):
            pass
        return ""

    def _init_model(self) -> None:
        if not self._api_key:
            self._error_msg = "API anahtarı bulunamadı. GEMINI_API_KEY ortam değişkenini ayarlayın."
            return
        try:
            import google.generativeai as genai  # type: ignore[import]
            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(
                model_name=self.MODEL_NAME,
                system_instruction=_SYSTEM_INSTRUCTION,
                generation_config={"max_output_tokens": 150, "temperature": 0.4},
            )
            self._available = True
        except ImportError:
            self._error_msg = "google-generativeai paketi yüklü değil."
        except Exception as exc:
            self._error_msg = f"Model başlatılamadı: {exc}"

    def configure(self, api_key: str) -> bool:
        """Re-initialise with a new API key (called from settings UI)."""
        self._api_key   = api_key.strip()
        self._available = False
        self._model     = None
        self._cache.clear()
        self._init_model()
        return self._available

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def status_message(self) -> str:
        if self._available:
            return f"Gemini {self.MODEL_NAME} bağlı"
        return self._error_msg if self._error_msg else "Bağlantı yok"

    @property
    def status_icon(self) -> str:
        return "✓" if self._available else "✗"

    # ── Prompt builder ────────────────────────────────────────────────────────

    def build_prompt(self, context: dict, user_question: str | None = None) -> str:
        """Build a compact, information-dense prompt from the context dict."""
        p     = context.get("portfolio", {})
        perf  = context.get("performance", {})
        risk  = context.get("risk", {})
        learn = context.get("learning", {})
        action = context.get("user_action", "")

        lines: list[str] = [
            f"Portfolio: TL {p.get('total_value', 0):,.0f}  |  Cash: TL {p.get('cash', 0):,.0f}",
        ]

        assets = p.get("assets", [])
        if assets:
            asset_str = "  ".join(
                f"{a['symbol']} {a['weight_pct']:.0f}% (K/Z {a['pnl']:+,.0f} TL)"
                for a in assets[:6]
            )
            lines.append(f"Assets: {asset_str}")

        pnl     = perf.get("profit_loss", 0)
        pnl_pct = perf.get("profit_loss_pct", 0)
        r_pnl   = perf.get("realized_pnl", 0)
        lines.append(
            f"P/L: {pnl:+,.0f} TL ({pnl_pct:+.1f}%)  |  Realized: {r_pnl:+,.0f} TL"
            f"  |  Trades: {perf.get('total_trades', 0)}"
        )

        risk_level = risk.get("risk_level", "?")
        max_conc   = risk.get("max_concentration_pct", 0)
        lines.append(
            f"Risk: {risk_level}  |  Max concentration: {max_conc:.0f}%"
            f"  |  Assets: {risk.get('asset_count', 0)}"
        )

        warnings = risk.get("warnings", [])
        if warnings:
            lines.append(f"Active warnings: {'; '.join(warnings[:2])}")

        best  = perf.get("best_trade")
        worst = perf.get("worst_trade")
        if best:
            lines.append(f"Best trade: {best}  |  Worst trade: {worst or '—'}")

        lvl  = learn.get("current_level", "")
        task = learn.get("current_task", "")
        obj  = learn.get("current_task_objective", "")
        if lvl:
            lines.append(f"Learning: {lvl} level  |  Task: {task or '—'}")
        if obj:
            lines.append(f"Task objective: {obj}")

        if action:
            lines.append(f"Last user action: {action}")

        data_block = "\n".join(lines)

        if user_question:
            return f"[Portfolio Data]\n{data_block}\n\n[User Question]\n{user_question}"
        return f"[Portfolio Data]\n{data_block}\n\n[Request]\nProvide 1-2 sentence specific coaching advice."

    # ── Synchronous call ──────────────────────────────────────────────────────

    def _ctx_hash(self, context: dict, question: str | None) -> str:
        raw = json.dumps(context, sort_keys=True, default=str) + str(question)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def send_prompt(self, context: dict, user_question: str | None = None) -> str | None:
        """Send prompt to Gemini. Returns text or None on failure/invalid response."""
        if not self._available or not self._model:
            return None

        h = self._ctx_hash(context, user_question)
        if h in self._cache:
            return self._cache[h]

        prompt = self.build_prompt(context, user_question)
        try:
            resp = self._model.generate_content(prompt)  # type: ignore[union-attr]
            text = resp.text.strip() if hasattr(resp, "text") else ""
        except Exception:
            return None

        if not (self.MIN_OUTPUT_CHARS <= len(text) <= self.MAX_OUTPUT_CHARS):
            return None

        # Evict oldest entry if cache is full
        if len(self._cache) >= self.MAX_CACHE_SIZE:
            del self._cache[next(iter(self._cache))]
        self._cache[h] = text
        return text

    # ── Async factory ─────────────────────────────────────────────────────────

    def make_worker(
        self, context: dict, question: str | None = None, fallback: str = ""
    ) -> GeminiWorker:
        return GeminiWorker(self, context, question, fallback)
