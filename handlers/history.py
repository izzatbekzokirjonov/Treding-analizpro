from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from database.db import get_analysis_history
from locales.texts import t

router = Router()


async def _history_text(user_id: int, lang: str) -> str:
    history = await get_analysis_history(user_id, limit=5)
    if not history:
        return t(lang, "history_empty")
    text = t(lang, "history_title")
    for i, row in enumerate(history, 1):
        date = row["created_at"][:10]
        snippet = row["result"][:150].replace("\n", " ")
        text += f"<b>#{i}</b> — 📅 {date}\n{snippet}...\n\n"
    return text


@router.message(Command("history"))
async def cmd_history(message: Message, lang: str = "uz"):
    await message.answer(await _history_text(message.from_user.id, lang))


@router.callback_query(F.data == "menu_history")
async def cb_menu_history(callback: CallbackQuery, lang: str = "uz"):
    await callback.message.answer(await _history_text(callback.from_user.id, lang))
    await callback.answer()
