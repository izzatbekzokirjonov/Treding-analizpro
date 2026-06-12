# 📊 Universal Trading Analysis Bot

Istalgan bozorni (Forex, Crypto, Aksiya, Tovar) AI yordamida tahlil qiluvchi Telegram bot.

## 🚀 O'rnatish

### 1. .env fayl yarating
```
cp .env.example .env
```

`.env` faylni tahrirlang:
```
BOT_TOKEN=@BotFather dan olgan token
CLAUDE_API_KEY=sk-ant-... (Claude API key)
ADMIN_IDS=sizning_telegram_id_ingiz
```

### 2. Lokal ishga tushurish
```bash
pip install -r requirements.txt
python bot.py
```

### 3. Railway Deploy

1. GitHub ga push qiling
2. Railway.app da yangi loyiha oching
3. GitHub repo ni ulang
4. Environment variables qo'shing:
   - `BOT_TOKEN`
   - `CLAUDE_API_KEY`
   - `ADMIN_IDS`
5. Deploy tugmasini bosing ✅

## 📱 Bot buyruqlari

- `/start` — Botni boshlash
- `/help` — Yordam
- `/status` — Mening holatim
- `/language` — Til o'zgartirish
- `/admin` — Admin panel (faqat adminlar uchun)

## 💡 Ishlatish

1. TradingView, Binance yoki boshqa platformadan grafik skrinshot oling
2. Botga yuboring
3. 5-10 soniya ichida to'liq tahlil oling

## 💰 Monetizatsiya

- **Free:** 7 ta bepul tahlil
- **Premium:** Oyiga 299 Stars yoki 50,000 so'm
  - Cheksiz tahlil
  - Telegram Stars orqali avtomatik to'lov
  - Karta orqali admin tasdiqlashi bilan

## 🛠 Tech Stack

- Python 3.11+
- Aiogram 3.x
- Claude claude-opus-4-5 (Vision)
- SQLite
- Railway
