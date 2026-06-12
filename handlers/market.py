from datetime import datetime, timezone

import httpx
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from locales.texts import t

router = Router()

_YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "application/json",
}


async def fetch_prices() -> dict:
    prices = {"btc": "N/A", "eth": "N/A", "gold": "N/A", "eurusd": "N/A"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        # BTC & ETH via CoinGecko
        try:
            r = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin,ethereum", "vs_currencies": "usd"},
            )
            data = r.json()
            prices["btc"] = f"{data['bitcoin']['usd']:,.0f}"
            prices["eth"] = f"{data['ethereum']['usd']:,.0f}"
        except Exception:
            pass

        # EUR/USD via Frankfurter
        try:
            r = await client.get("https://api.frankfurter.app/latest?from=EUR&to=USD")
            data = r.json()
            prices["eurusd"] = f"{data['rates']['USD']:.4f}"
        except Exception:
            pass

        # Gold — try metals.live first, fall back to Yahoo Finance
        try:
            r = await client.get("https://api.metals.live/v1/spot/gold", timeout=5.0)
            data = r.json()
            if isinstance(data, list) and data:
                gold_price = float(data[0].get("price", 0))
            else:
                gold_price = float(data.get("price", 0))
            if gold_price > 0:
                prices["gold"] = f"{gold_price:,.2f}"
                return prices
        except Exception:
            pass

        # Gold fallback — Yahoo Finance GC=F
        try:
            r = await client.get(
                "https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF",
                params={"interval": "1d", "range": "1d"},
                headers=_YAHOO_HEADERS,
                timeout=8.0,
            )
            meta = r.json()["chart"]["result"][0]["meta"]
            gold_price = meta.get("regularMarketPrice") or meta.get("previousClose", 0)
            if gold_price:
                prices["gold"] = f"{float(gold_price):,.2f}"
        except Exception:
            pass

    return prices


async def _send_market(send_fn, edit_fn, lang: str):
    msg = await send_fn(t(lang, "market_loading"))
    try:
        prices = await fetch_prices()
        time_str = datetime.now(timezone.utc).strftime("%H:%M")
        await edit_fn(msg, t(lang, "market_result",
                             time=time_str,
                             btc=prices["btc"],
                             eth=prices["eth"],
                             gold=prices["gold"],
                             eurusd=prices["eurusd"]))
    except Exception:
        await edit_fn(msg, t(lang, "market_error"))


@router.message(Command("market"))
async def cmd_market(message: Message, lang: str = "uz"):
    async def _send(text): return await message.answer(text)
    async def _edit(m, text): await m.edit_text(text)
    await _send_market(_send, _edit, lang)


@router.callback_query(F.data == "menu_market")
async def cb_menu_market(callback: CallbackQuery, lang: str = "uz"):
    await callback.answer()
    async def _send(text): return await callback.message.answer(text)
    async def _edit(m, text): await m.edit_text(text)
    await _send_market(_send, _edit, lang)
