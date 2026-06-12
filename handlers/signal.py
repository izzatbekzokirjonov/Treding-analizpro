from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from config import config
from database.db import get_all_users
from locales.texts import t

router = Router()


class SignalState(StatesGroup):
    waiting_signal = State()


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(Command("signal"))
async def cmd_signal(message: Message, state: FSMContext, lang: str = "uz"):
    if not is_admin(message.from_user.id):
        await message.answer(t(lang, "admin_only"))
        return
    await state.set_state(SignalState.waiting_signal)
    await message.answer(t(lang, "signal_ask"))


@router.message(SignalState.waiting_signal)
async def process_signal(message: Message, state: FSMContext, lang: str = "uz"):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    await state.clear()
    signal_text = t(lang, "signal_header") + message.text

    users = await get_all_users()
    count = 0
    for user in users:
        try:
            await message.bot.send_message(user["user_id"], signal_text)
            count += 1
        except Exception:
            pass

    await message.answer(t(lang, "signal_sent", count=count))
