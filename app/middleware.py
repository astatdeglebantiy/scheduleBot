from aiogram import BaseMiddleware

from app.db import updUser, upsertGroupChat


class DbMdw(BaseMiddleware):
    async def __call__(self, handler, event, data):
        result = await handler(event, data)

        user = getattr(event, "from_user", None)
        if user is not None:
            try:
                updUser(user)
            except Exception as e:
                print(f"db error: {e}")

        chat = getattr(event, "chat", None)
        if chat is not None:
            try:
                upsertGroupChat(chat)
            except Exception as e:
                print(f"db group error: {e}")

        return result
