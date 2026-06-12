import os
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BotCommand, BotCommandScopeDefault, WebAppInfo
from aiogram.filters import CommandStart, Command
from aiogram.filters.command import CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from database.db import (
    get_analysis_count, get_user, set_user_language,
    is_premium, apply_referral, get_bonus_analyses, get_user_language
)
from locales.texts import t

_DOMAIN = os.getenv("REPLIT_DOMAINS", "").split(",")[0].strip()
_WEBAPP_URL = f"https://{_DOMAIN}/webapp"

router = Router()


def main_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔵 " + t(lang, "btn_analyze"),       callback_data="menu_analyze")
    builder.button(text=t(lang, "btn_webapp"),                 web_app=WebAppInfo(url=_WEBAPP_URL))
    builder.button(text="🔴 " + t(lang, "btn_ai_chat"),       callback_data="menu_ai_chat")
    builder.button(text="🟢 " + t(lang, "btn_premium_short"), callback_data="premium")
    builder.button(text="🔵 " + t(lang, "btn_market"),        callback_data="menu_market")
    builder.button(text="🔵 " + t(lang, "btn_calc"),          callback_data="menu_calc")
    builder.button(text="🔵 " + t(lang, "btn_referral"),      callback_data="menu_referral")
    builder.button(text="🔵 " + t(lang, "btn_history"),       callback_data="menu_history")
    builder.button(text="🔵 " + t(lang, "help_btn"),          callback_data="help")
    builder.button(text="🔵 " + t(lang, "lang_btn"),          callback_data="language")
    builder.adjust(1, 1, 2, 2, 2, 2)
    return builder.as_markup()


def language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbek", callback_data="set_lang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="set_lang_ru")
    builder.button(text="🇬🇧 English", callback_data="set_lang_en")
    builder.adjust(1)
    return builder.as_markup()


def onboard_keyboard():
    """Language selection keyboard shown to brand-new users."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbek",  callback_data="onboard_lang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="onboard_lang_ru")
    builder.button(text="🇬🇧 English", callback_data="onboard_lang_en")
    builder.adjust(1)
    return builder.as_markup()


async def _count_line(uid: int, lang: str, premium: bool) -> str:
    if premium:
        lines = {
            "uz": "♾️ Sizda Cheksiz tahlil!",
            "ru": "♾️ У вас безлимитный анализ!",
            "en": "♾️ You have unlimited analyses!",
        }
        return lines.get(lang, lines["uz"])
    count = await get_analysis_count(uid)
    bonus = await get_bonus_analyses(uid)
    remaining = max(0, config.FREE_LIMIT + bonus - count)
    lines = {
        "uz": f"Sizda <b>{remaining} ta bepul</b> tahlil qolgan.",
        "ru": f"У вас осталось <b>{remaining} бесплатных</b> анализов.",
        "en": f"You have <b>{remaining} free</b> analyses remaining.",
    }
    return lines.get(lang, lines["uz"])


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, lang: str = "uz", is_new_user: bool = False):
    uid = message.from_user.id

    # Handle referral deep link
    if command.args:
        referrer_id = await apply_referral(uid, command.args)
        if referrer_id:
            referrer_lang = await get_user_language(referrer_id)
            try:
                await message.bot.send_message(
                    referrer_id,
                    t(referrer_lang, "referral_bonus_given")
                )
            except Exception:
                pass

    # Brand-new user: ask language first, welcome comes after selection
    if is_new_user:
        await message.answer(
            t("uz", "choose_language_first"),
            reply_markup=onboard_keyboard()
        )
        return

    premium = await is_premium(uid)
    count_line = await _count_line(uid, lang, premium)
    await message.answer(
        t(lang, "welcome", name=message.from_user.first_name, count_line=count_line),
        reply_markup=main_keyboard(lang)
    )


@router.callback_query(F.data.startswith("onboard_lang_"))
async def cb_onboard_lang(callback: CallbackQuery, lang: str = "uz"):
    new_lang = callback.data.replace("onboard_lang_", "")
    await set_user_language(callback.from_user.id, new_lang)
    uid = callback.from_user.id
    premium = await is_premium(uid)
    count_line = await _count_line(uid, new_lang, premium)
    await callback.message.edit_text(
        t(new_lang, "welcome", name=callback.from_user.first_name, count_line=count_line),
        reply_markup=main_keyboard(new_lang)
    )
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message, lang: str = "uz"):
    await message.answer(t(lang, "help"), reply_markup=main_keyboard(lang))


@router.message(Command("status"))
async def cmd_status(message: Message, lang: str = "uz"):
    await show_status(message, lang)


@router.message(Command("profile"))
async def cmd_profile(message: Message, lang: str = "uz"):
    await show_profile(message, lang)


@router.message(Command("language"))
async def cmd_language(message: Message, lang: str = "uz"):
    await message.answer(t(lang, "choose_language"), reply_markup=language_keyboard())


@router.callback_query(F.data == "menu_analyze")
async def cb_menu_analyze(callback: CallbackQuery, lang: str = "uz"):
    await callback.message.answer(t(lang, "send_screenshot"))
    await callback.answer()


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery, lang: str = "uz"):
    await callback.message.edit_text(t(lang, "help"), reply_markup=main_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data == "status")
async def cb_status(callback: CallbackQuery, lang: str = "uz"):
    await show_status(callback.message, lang, user_id=callback.from_user.id, edit=True)
    await callback.answer()


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery, lang: str = "uz"):
    await show_profile(callback.message, lang, user_id=callback.from_user.id, edit=True)
    await callback.answer()


@router.callback_query(F.data == "language")
async def cb_language(callback: CallbackQuery, lang: str = "uz"):
    await callback.message.edit_text(
        t(lang, "choose_language"),
        reply_markup=language_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_lang_"))
async def cb_set_lang(callback: CallbackQuery, lang: str = "uz"):
    new_lang = callback.data.replace("set_lang_", "")
    await set_user_language(callback.from_user.id, new_lang)
    await callback.message.edit_text(
        t(new_lang, "language_set"),
        reply_markup=main_keyboard(new_lang)
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, lang: str = "uz"):
    uid = callback.from_user.id
    premium = await is_premium(uid)
    count_line = await _count_line(uid, lang, premium)
    await callback.message.edit_text(
        t(lang, "welcome", name=callback.from_user.first_name, count_line=count_line),
        reply_markup=main_keyboard(lang)
    )
    await callback.answer()


async def show_profile(message: Message, lang: str, user_id: int = None, edit: bool = False):
    uid = user_id or message.chat.id
    user = await get_user(uid)
    if not user:
        return

    premium = await is_premium(uid)
    joined = (user["created_at"] or "")[:10] or "—"

    days_line = ""
    if premium and user["premium_until"]:
        try:
            until = datetime.fromisoformat(user["premium_until"])
            days_left = max(0, (until - datetime.now()).days)
            day_texts = {
                "uz": f"\n⏳ <b>{days_left}</b> kun qoldi",
                "ru": f"\n⏳ Осталось <b>{days_left}</b> дней",
                "en": f"\n⏳ <b>{days_left}</b> days left",
            }
            days_line = day_texts.get(lang, day_texts["uz"])
        except Exception:
            pass

    text = t(
        lang, "profile",
        name=user["full_name"] or "—",
        joined=joined,
        count=user["analysis_count"] or 0,
        referrals=user["referral_count"] or 0,
        bonus=user["bonus_analyses"] or 0,
        premium=t(lang, "premium_yes") if premium else t(lang, "premium_no"),
        days_line=days_line,
    )

    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "main_menu"), callback_data="main_menu")

    if edit:
        await message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await message.answer(text, reply_markup=builder.as_markup())


async def show_status(message: Message, lang: str, user_id: int = None, edit: bool = False):
    uid = user_id or message.chat.id
    user = await get_user(uid)
    if not user:
        return

    premium = await is_premium(uid)
    count = user["analysis_count"]

    lang_names = {"uz": "O'zbek", "ru": "Русский", "en": "English"}
    lang_name = lang_names.get(user["language"], user["language"])

    until_text = ""
    if premium and user["premium_until"]:
        date_str = user["premium_until"][:10]
        until_text = t(lang, "premium_until", date=date_str)

    text = t(lang, "status",
             name=user["full_name"],
             user_lang=lang_name,
             count=count,
             premium=t(lang, "premium_yes") if premium else t(lang, "premium_no"),
             until=until_text)

    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "main_menu"), callback_data="main_menu")

    if edit:
        await message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await message.answer(text, reply_markup=builder.as_markup())


async def set_bot_commands(bot) -> None:
    uz = [
        BotCommand(command="start",      description="Botni boshlash"),
        BotCommand(command="profile",    description="Mening profilim"),
        BotCommand(command="history",    description="So'nggi 5 ta tahlil"),
        BotCommand(command="referral",   description="Do'stlarni taklif qil (+1 tahlil)"),
        BotCommand(command="market",     description="Jonli bozor narxlari"),
        BotCommand(command="calculator", description="Risk kalkulyator"),
        BotCommand(command="signal",     description="Signal yuborish (admin)"),
        BotCommand(command="language",   description="Tilni o'zgartirish"),
        BotCommand(command="help",       description="Yordam"),
    ]
    ru = [
        BotCommand(command="start",      description="Запустить бота"),
        BotCommand(command="profile",    description="Мой профиль"),
        BotCommand(command="history",    description="Последние 5 анализов"),
        BotCommand(command="referral",   description="Пригласить друга (+1 анализ)"),
        BotCommand(command="market",     description="Актуальные цены рынка"),
        BotCommand(command="calculator", description="Риск-калькулятор"),
        BotCommand(command="signal",     description="Отправить сигнал (admin)"),
        BotCommand(command="language",   description="Сменить язык"),
        BotCommand(command="help",       description="Помощь"),
    ]
    en = [
        BotCommand(command="start",      description="Start the bot"),
        BotCommand(command="profile",    description="My profile"),
        BotCommand(command="history",    description="Last 5 analyses"),
        BotCommand(command="referral",   description="Invite a friend (+1 analysis)"),
        BotCommand(command="market",     description="Live market prices"),
        BotCommand(command="calculator", description="Risk calculator"),
        BotCommand(command="signal",     description="Send signal (admin)"),
        BotCommand(command="language",   description="Change language"),
        BotCommand(command="help",       description="Help"),
    ]
    scope = BotCommandScopeDefault()
    await bot.set_my_commands(uz, scope=scope, language_code="uz")
    await bot.set_my_commands(ru, scope=scope, language_code="ru")
    await bot.set_my_commands(en, scope=scope)
