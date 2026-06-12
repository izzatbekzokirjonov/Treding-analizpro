from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from database.db import get_user, get_or_create_referral_code
from locales.texts import t

router = Router()


async def _referral_message(user_id: int, bot, lang: str) -> str | None:
    user = await get_user(user_id)
    if not user:
        return None
    code = await get_or_create_referral_code(user_id)
    bot_info = await bot.get_me()
    return t(lang, "referral_info",
             code=code,
             bot_username=bot_info.username,
             count=user["referral_count"] or 0,
             bonus=user["bonus_analyses"] or 0)


@router.message(Command("referral"))
async def cmd_referral(message: Message, lang: str = "uz"):
    text = await _referral_message(message.from_user.id, message.bot, lang)
    if text:
        await message.answer(text, disable_web_page_preview=True)


@router.callback_query(F.data == "menu_referral")
async def cb_menu_referral(callback: CallbackQuery, lang: str = "uz"):
    text = await _referral_message(callback.from_user.id, callback.bot, lang)
    if text:
        await callback.message.answer(text, disable_web_page_preview=True)
    await callback.answer()
