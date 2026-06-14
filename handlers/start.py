from aiogram.types import WebAppInfo
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config
from database.db import get_analysis_count, get_user, set_user_language, is_premium
from locales.texts import t

router = Router()

def main_keyboard(lang):
    builder = InlineKeyboardBuilder()
    builder.button(text="📸 Grafik Tahlil", callback_data="send_analysis")
    builder.button(text="💎 Premium", callback_data="premium")
    builder.button(text="📊 Bozor", callback_data="market")
    builder.button(text="🧮 Kalkulyator", callback_data="calculator")
    builder.button(text="👥 Referral", callback_data="referral")
    builder.button(text="📜 Tarix", callback_data="history")
    builder.button(text="ℹ️ Yordam", callback_data="help")
    builder.button(text="🌐 Til", callback_data="language")
    builder.button(text="🌐 Web App", web_app=WebAppInfo(url="https://treding-analizpro-production.up.railway.app/webapp"))
    builder.adjust(2)
    return builder.as_markup()

def language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbek", callback_data="set_lang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="set_lang_ru")
    builder.button(text="🇬🇧 English", callback_data="set_lang_en")
    builder.adjust(1)
    return builder.as_markup()

@router.message(CommandStart())
async def cmd_start(message: Message, lang: str = "uz"):
    premium = await is_premium(message.from_user.id)
    count = await get_analysis_count(message.from_user.id)
    remaining = max(0, config.FREE_LIMIT - count)
    free_text = "♾️ Sizda Cheksiz tahlil!" if premium else f"🎁 Sizda <b>{remaining} ta bepul</b> tahlil qolgan."
    text = f"👋 <b>Xush kelibsiz, {message.from_user.first_name}!</b>\n\n📊 Forex, Crypto, Aksiya, Tovar\n\n📸 Grafik skrinshot yuboring!\n\n{free_text}"
    await message.answer(text, reply_markup=main_keyboard(lang))

@router.message(Command("help"))
async def cmd_help(message: Message, lang: str = "uz"):
    await message.answer(t(lang, "help"), reply_markup=main_keyboard(lang))

@router.message(Command("language"))
async def cmd_language(message: Message, lang: str = "uz"):
    await message.answer(t(lang, "choose_language"), reply_markup=language_keyboard())

@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery, lang: str = "uz"):
    await callback.message.edit_text(t(lang, "help"), reply_markup=main_keyboard(lang))
    await callback.answer()

@router.callback_query(F.data == "language")
async def cb_language(callback: CallbackQuery, lang: str = "uz"):
    await callback.message.edit_text(t(lang, "choose_language"), reply_markup=language_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("set_lang_"))
async def cb_set_lang(callback: CallbackQuery, lang: str = "uz"):
    new_lang = callback.data.replace("set_lang_", "")
    await set_user_language(callback.from_user.id, new_lang)
    await callback.message.edit_text(t(new_lang, "language_set"), reply_markup=main_keyboard(new_lang))
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, lang: str = "uz"):
    premium = await is_premium(callback.from_user.id)
    count = await get_analysis_count(callback.from_user.id)
    remaining = max(0, config.FREE_LIMIT - count)
    free_text = "♾️ Sizda Cheksiz tahlil!" if premium else f"🎁 Sizda <b>{remaining} ta bepul</b> tahlil qolgan."
    text = f"👋 <b>Xush kelibsiz!</b>\n\n📸 Grafik skrinshot yuboring!\n\n{free_text}"
    await callback.message.edit_text(text, reply_markup=main_keyboard(lang))
    await callback.answer()

@router.callback_query(F.data == "send_analysis")
async def cb_send_analysis(callback: CallbackQuery, lang: str = "uz"):
    await callback.message.edit_text(t(lang, "send_screenshot"))
    await callback.answer()
