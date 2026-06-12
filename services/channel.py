from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.db import get_setting


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Check if user is subscribed to required channel"""
    channel_required = await get_setting("channel_required")
    if channel_required != "1":
        return True  # No channel required

    channel_id = await get_setting("channel_id")
    if not channel_id:
        return True  # No channel set

    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        return True  # If error, allow access


async def get_subscribe_keyboard(lang: str):
    channel_username = await get_setting("channel_username")
    channel_id = await get_setting("channel_id")

    texts = {
        "uz": ("📢 Botdan foydalanish uchun kanalimizga obuna bo'ling!", "✅ Obuna bo'ldim"),
        "ru": ("📢 Для использования бота подпишитесь на наш канал!", "✅ Я подписался"),
        "en": ("📢 Subscribe to our channel to use the bot!", "✅ I subscribed"),
    }
    msg_text, btn_text = texts.get(lang, texts["uz"])

    builder = InlineKeyboardBuilder()
    if channel_username:
        url = f"https://t.me/{channel_username.lstrip('@')}"
        builder.button(text="📢 Kanal / Channel", url=url)
    builder.button(text=btn_text, callback_data="check_subscription")
    builder.adjust(1)

    return msg_text, builder.as_markup()


async def post_to_channel(bot: Bot, text: str, photo_file_id: str = None):
    """Post analysis result to channel"""
    channel_auto_post = await get_setting("channel_auto_post")
    if channel_auto_post != "1":
        return

    channel_id = await get_setting("channel_id")
    if not channel_id:
        return

    try:
        if photo_file_id:
            await bot.send_photo(channel_id, photo=photo_file_id)
        for i in range(0, len(text), 4096):
            await bot.send_message(channel_id, text[i:i + 4096])
    except Exception:
        pass
