import httpx
import base64
from config import config

PROMPTS = {
    "uz": """Sen professional trading analistisan. Menga bu grafik haqida batafsil texnik tahlil ber.

Quyidagilarni aniqla:
1. 📊 AKTIV va TIMEFRAME — qaysi bozor, qaysi vaqt oralig'i
2. 📈 TREND — Bullish, Bearish yoki Sideways (kuchli yoki zaif)
3. 🎯 SUPPORT va RESISTANCE — asosiy darajalar (aniq narxlar)
4. 🕯 CANDLESTICK PATTERN — agar ko'rinsa
5. 📉 INDIKATORLAR — grafikda ko'ringan indikatorlar tahlili
6. ⚡ SIGNAL — BUY / SELL / WAIT (asoslash bilan)
7. 🛡 RISK MANAGEMENT — taxminiy Stop Loss va Take Profit darajalari
8. 📝 XULOSA — qisqa va aniq

Faqat ko'ringan narsalarni ayt, taxmin qilma. O'zbek tilida javob ber.""",

    "ru": """Ты профессиональный торговый аналитик. Дай мне подробный технический анализ этого графика.

Определи:
1. 📊 АКТИВ и ТАЙМФРЕЙМ — какой рынок, какой период
2. 📈 ТРЕНД — Bullish, Bearish или Sideways (сильный или слабый)
3. 🎯 SUPPORT и RESISTANCE — ключевые уровни (точные цены)
4. 🕯 CANDLESTICK ПАТТЕРН — если виден
5. 📉 ИНДИКАТОРЫ — анализ видимых индикаторов
6. ⚡ СИГНАЛ — BUY / SELL / WAIT (с обоснованием)
7. 🛡 РИСК-МЕНЕДЖМЕНТ — примерные уровни Stop Loss и Take Profit
8. 📝 ВЫВОД — кратко и чётко

Говори только о том, что видно на графике. Ответ на русском языке.""",

    "en": """You are a professional trading analyst. Give me a detailed technical analysis of this chart.

Identify:
1. 📊 ASSET & TIMEFRAME — which market, which time period
2. 📈 TREND — Bullish, Bearish or Sideways (strong or weak)
3. 🎯 SUPPORT & RESISTANCE — key levels (exact prices)
4. 🕯 CANDLESTICK PATTERN — if visible
5. 📉 INDICATORS — analysis of visible indicators
6. ⚡ SIGNAL — BUY / SELL / WAIT (with reasoning)
7. 🛡 RISK MANAGEMENT — approximate Stop Loss and Take Profit levels
8. 📝 CONCLUSION — brief and clear

Only mention what is visible on the chart. Reply in English."""
}


async def analyze_chart(image_bytes: bytes, lang: str = "uz") -> str:
    image_base64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    prompt = PROMPTS.get(lang, PROMPTS["uz"])

    payload = {
        "model": "claude-opus-4-5",
        "max_tokens": 1500,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": config.CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]
