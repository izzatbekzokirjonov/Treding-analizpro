from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from database.db import get_user_language, create_or_update_user


class LanguageMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user:
            is_new = await create_or_update_user(
                user_id=user.id,
                username=user.username or "",
                full_name=user.full_name or ""
            )
            lang = await get_user_language(user.id)
            data["lang"] = lang
            data["is_new_user"] = is_new

        return await handler(event, data)
