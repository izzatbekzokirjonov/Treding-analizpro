import io
import time
from collections import defaultdict
from aiogram import Router, F
from aiogram.fsm.state import default_state
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from database.db import is_premium, get_analysis_count, increment_analysis_count, save_analysis, get_bonus_analyses
from locales.texts import t
from services.claude_vision import analyze_chart
from services.channel import check_subscription, get_subscribe_keyboard, post_to_channel

router = Router()

_photo_ts: dict[int, list] = defaultdict(list)
_blocked:  dict[int, float] = {}
_RATE_LIMIT = 3   # max photos per 60 seconds
_BLOCK_SECS = 60  # block duration in seconds


def _rate_ok(user_id: int) -> tuple[bool, int]:
    """Returns (allowed, seconds_remaining_in_block)."""
    now = time.time()
    if user_id in _blocked:
        if now < _blocked[user_id]:
            return False, int(_blocked[user_id] - now)
        del _blocked[user_id]
    window = [ts for ts in _photo_ts[user_id] if now - ts < 60]
    _photo_ts[user_id] = window
    if len(window) >= _RATE_LIMIT:
        _blocked[user_id] = now + _BLOCK_SECS
        return False, _BLOCK_SECS
    _photo_ts[user_id].append(now)
    return True, 0

_REFERRAL_BTN = {
    "uz": "🤝 Do'st taklif qil (+1 tahlil)",
    "ru": "🤝 Пригласить друга (+1 анализ)",
    "en": "🤝 Invite a friend (+1 analysis)",
}


def premium_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=t(lang, "buy_premium"), callback_data="premium")
    builder.button(text=_REFERRAL_BTN.get(lang, _REFERRAL_BTN["uz"]), callback_data="show_referral")
    builder.adjust(1)
    return builder.as_markup()


async def handle_image_analysis(message: Message, image_bytes: bytes, lang: str, photo_file_id: str = None):
    user_id = message.from_user.id

    subscribed = await check_subscription(message.bot, user_id)
    if not subscribed:
        msg_text, keyboard = await get_subscribe_keyboard(lang)
        await message.answer(msg_text, reply_markup=keyboard)
        return

    premium = await is_premium(user_id)
    if not premium:
        count = await get_analysis_count(user_id)
        bonus = await get_bonus_analyses(user_id)
        if count >= config.FREE_LIMIT + bonus:
            await message.answer(
                t(lang, "free_limit_reached", limit=config.FREE_LIMIT),
                reply_markup=premium_keyboard(lang)
            )
            return

    analyzing_msg = await message.answer(t(lang, "analyzing"))

    try:
        result = await analyze_chart(image_bytes, lang)

        await increment_analysis_count(user_id)
        await save_analysis(user_id, result)

        footer = ""
        if not premium:
            new_count = await get_analysis_count(user_id)
            bonus = await get_bonus_analyses(user_id)
            remaining = max(0, config.FREE_LIMIT + bonus - new_count)
            if remaining == 0:
                footer_texts = {
                    "uz": "\n\n⚠️ Bu sizning oxirgi bepul tahlilingiz edi!",
                    "ru": "\n\n⚠️ Это был ваш последний бесплатный анализ!",
                    "en": "\n\n⚠️ This was your last free analysis!"
                }
                footer = footer_texts.get(lang, "")
            else:
                footer_texts = {
                    "uz": f"\n\n📊 Qolgan bepul tahlillar: <b>{remaining} ta</b>",
                    "ru": f"\n\n📊 Осталось бесплатных анализов: <b>{remaining}</b>",
                    "en": f"\n\n📊 Free analyses remaining: <b>{remaining}</b>"
                }
                footer = footer_texts.get(lang, "")

        await analyzing_msg.edit_text(result + footer)

        await post_to_channel(message.bot, result, photo_file_id)

    except Exception as e:
        await analyzing_msg.edit_text(t(lang, "error"))
        raise e


@router.callback_query(F.data == "show_referral")
async def cb_show_referral(callback: CallbackQuery, lang: str = "uz"):
    from database.db import get_user, get_or_create_referral_code
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer()
        return
    code = await get_or_create_referral_code(callback.from_user.id)
    bot_info = await callback.bot.get_me()
    from locales.texts import t as _t
    await callback.message.answer(
        _t(lang, "referral_info",
           code=code,
           bot_username=bot_info.username,
           count=user["referral_count"] or 0,
           bonus=user["bonus_analyses"] or 0),
        disable_web_page_preview=True
    )
    await callback.answer()


@router.callback_query(F.data == "check_subscription")
async def cb_check_subscription(callback: CallbackQuery, lang: str = "uz"):
    subscribed = await check_subscription(callback.bot, callback.from_user.id)
    if subscribed:
        await callback.message.delete()
        await callback.message.answer(t(lang, "send_screenshot"))
        await callback.answer("✅")
    else:
        not_subbed = {
            "uz": "❌ Siz hali obuna bo'lmadingiz!",
            "ru": "❌ Вы ещё не подписались!",
            "en": "❌ You haven't subscribed yet!"
        }
        await callback.answer(not_subbed.get(lang, not_subbed["uz"]), show_alert=True)


@router.message(F.photo, StateFilter(default_state))
async def handle_photo(message: Message, lang: str = "uz"):
    allowed, secs = _rate_ok(message.from_user.id)
    if not allowed:
        await message.answer(t(lang, "spam_block", seconds=secs))
        return
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_bytes_io = await message.bot.download_file(file.file_path)
    image_bytes = file_bytes_io.read() if isinstance(file_bytes_io, io.BytesIO) else file_bytes_io
    await handle_image_analysis(message, image_bytes, lang, photo_file_id=photo.file_id)


@router.message(F.document, StateFilter(default_state))
async def handle_document(message: Message, lang: str = "uz"):
    if message.document.mime_type and message.document.mime_type.startswith("image/"):
        allowed, secs = _rate_ok(message.from_user.id)
        if not allowed:
            await message.answer(t(lang, "spam_block", seconds=secs))
            return
        file = await message.bot.get_file(message.document.file_id)
        file_bytes_io = await message.bot.download_file(file.file_path)
        image_bytes = file_bytes_io.read() if isinstance(file_bytes_io, io.BytesIO) else file_bytes_io
        await handle_image_analysis(message, image_bytes, lang)
    else:
        await message.answer(t(lang, "not_image"))


@router.message(F.text & ~F.text.startswith("/"), StateFilter(default_state))
async def handle_text(message: Message, lang: str = "uz"):
    await message.answer(t(lang, "send_screenshot"))
