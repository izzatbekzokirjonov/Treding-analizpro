import httpx
from aiogram import Router, F
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from locales.texts import t

router = Router()

SYSTEM_PROMPT = (
    "You are an expert forex and cryptocurrency trading assistant. "
    "Answer questions about technical analysis, fundamental analysis, "
    "trading strategies, risk management, chart patterns, indicators, "
    "and financial markets. Be concise, practical, and professional. "
    "Format your answers clearly with sections when helpful. "
    "If asked in Uzbek, reply in Uzbek. If in Russian, reply in Russian. "
    "If in English, reply in English."
)

CLAUDE_MODEL = "claude-opus-4-5"


class AIChatState(StatesGroup):
    chatting = State()


def _back_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ " + {"uz": "Asosiy menyu", "ru": "Главное меню", "en": "Main menu"}.get(lang, "Asosiy menyu"),
                   callback_data="main_menu")
    return builder.as_markup()


async def _ask_claude(messages: list[dict]) -> str:
    headers = {
        "x-api-key": config.CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


@router.callback_query(F.data == "menu_ai_chat")
async def cb_menu_ai_chat(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    await state.set_state(AIChatState.chatting)
    await state.update_data(chat_history=[])
    await callback.message.answer(t(lang, "ai_chat_welcome"), reply_markup=_back_keyboard(lang))
    await callback.answer()


@router.message(Command("cancel"), StateFilter(AIChatState.chatting))
async def cmd_cancel_chat(message: Message, state: FSMContext, lang: str = "uz"):
    await state.clear()
    await message.answer({"uz": "AI Chat yopildi.", "ru": "AI Chat закрыт.", "en": "AI Chat closed."}.get(lang, "AI Chat yopildi."))


@router.message(StateFilter(AIChatState.chatting))
async def handle_ai_message(message: Message, state: FSMContext, lang: str = "uz"):
    user_text = (message.text or "").strip()
    if not user_text:
        return

    data = await state.get_data()
    history: list[dict] = data.get("chat_history", [])

    history.append({"role": "user", "content": user_text})

    thinking_msg = await message.answer(t(lang, "ai_chat_thinking"))

    try:
        answer = await _ask_claude(history[-20:])
        history.append({"role": "assistant", "content": answer})
        await state.update_data(chat_history=history)
        await thinking_msg.edit_text(answer, reply_markup=_back_keyboard(lang))
    except Exception:
        await thinking_msg.edit_text(t(lang, "ai_chat_error"), reply_markup=_back_keyboard(lang))
