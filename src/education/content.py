"""Educational content — all text in Turkish, targeted at complete beginners."""

from __future__ import annotations

# ── glossary & topics (referenced by main_window imports) ─────────────────────

GLOSSARY: list[dict] = []
TOPICS: list[dict] = []

# ── asset educational info ────────────────────────────────────────────────────

ASSET_INFO: dict[str, dict] = {
    "BTC":  {"risk": "Çok Yüksek", "risk_level": 5, "desc": "Bitcoin — dünyanın ilk kripto parası. 'Dijital altın' olarak bilinir."},
    "ETH":  {"risk": "Çok Yüksek", "risk_level": 5, "desc": "Ethereum — akıllı sözleşmeler ve DeFi platformu."},
    "BNB":  {"risk": "Yüksek",     "risk_level": 4, "desc": "Binance'in kripto parası. Borsa işlem ücretlerinde indirim sağlar."},
    "SOL":  {"risk": "Çok Yüksek", "risk_level": 5, "desc": "Solana — hızlı ve ucuz işlemler sunan blokzincir."},
    "AAPL": {"risk": "Orta",       "risk_level": 2, "desc": "Apple Inc. — dünyanın en yüksek piyasa değerli şirketlerinden biri."},
    "MSFT": {"risk": "Orta",       "risk_level": 2, "desc": "Microsoft — yazılım ve bulut bilişim devi."},
    "NVDA": {"risk": "Yüksek",     "risk_level": 4, "desc": "Nvidia — yapay zeka ve GPU sektörünün lideri."},
    "TSLA": {"risk": "Yüksek",     "risk_level": 4, "desc": "Tesla — elektrikli araç ve enerji şirketi."},
    "GOOG": {"risk": "Orta",       "risk_level": 3, "desc": "Alphabet (Google) — arama ve reklam teknolojisi."},
    "AMZN": {"risk": "Orta",       "risk_level": 3, "desc": "Amazon — e-ticaret ve bulut altyapısı (AWS)."},
    "GOLD": {"risk": "Düşük",      "risk_level": 1, "desc": "Altın — tarihin en güvenli yatırım araçlarından biri."},
    "BIST": {"risk": "Düşük",      "risk_level": 1, "desc": "BIST 100 — Türkiye'nin en büyük 100 şirket endeksi."},
}

# ── beginner tips (shown randomly in status bar) ──────────────────────────────

TIPS: list[str] = [
    "İPUCU: Piyasayı bir süre gözlemleyin. Fiyatların nasıl hareket ettiğini anlamak için acele etmeyin.",
    "İPUCU: Altın (GOLD) ve BIST100 en düşük riskli varlıklardır — başlamak için iyi bir yer!",
    "İPUCU: Asla tüm nakdinizi tek bir varlığa yatırmayın. Çeşitlendirme riski azaltır.",
    "İPUCU: K/Z değeri kırmızı görünse endişelenmeyin — bu bir simülasyon, öğrenmek için buradayız.",
    "İPUCU: 'Öğren' sayfasında her kavramın detaylı açıklamasını bulabilirsiniz.",
    "İPUCU: BTC ve ETH en likit kripto paralardır — her zaman alıcı ve satıcı bulunur.",
    "İPUCU: Piyasa fiyatı her 3 saniyede bir güncelleniyor. Gerçek piyasalarda bu anlık olur!",
    "İPUCU: İşlem geçmişinizi inceleyerek hangi kararların iyi sonuç verdiğini analiz edin.",
    "İPUCU: 'Senaryo Simülasyonu' ile mevcut portföyünüzün farklı tarihlerdeki performansını test edin.",
    "İPUCU: TSLA ve SOL en volatil varlıklar arasında — küçük miktarlarla deneyin.",
]

# ── tutorial steps ────────────────────────────────────────────────────────────

TUTORIAL_STEPS: list[dict] = [
    {
        "id":    "view_market",
        "title": "Piyasayı inceleyin",
        "desc":  "'İşlem' sayfasına gidin ve fiyatların değişimini izleyin.",
        "page":  1,
    },
    {
        "id":    "first_buy",
        "title": "İlk alımınızı yapın",
        "desc":  "Bir varlığa tıklayıp miktar girerek ilk işleminizi gerçekleştirin.",
        "page":  1,
    },
    {
        "id":    "check_portfolio",
        "title": "Portföyünüzü izleyin",
        "desc":  "'Özet' sayfasında K/Z değerinin değişimini gözlemleyin.",
        "page":  0,
    },
    {
        "id":    "first_sell",
        "title": "İlk satışınızı yapın",
        "desc":  "SATIŞ moduna geçerek elinizdeki varlığın bir kısmını satın.",
        "page":  1,
    },
    {
        "id":    "check_history",
        "title": "Geçmişi inceleyin",
        "desc":  "'Geçmiş' sayfasında tüm işlemlerinizi görün.",
        "page":  2,
    },
    {
        "id":    "run_analysis",
        "title": "Senaryo analizi çalıştırın",
        "desc":  "'Analiz' sayfasından portföyünüzü projekte edin.",
        "page":  4,
    },
]
