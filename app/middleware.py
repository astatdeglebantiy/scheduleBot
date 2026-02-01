from aiogram import BaseMiddleware
from aiogram.types import Message
from app.db import updUser

class DbMdw(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.from_user:
            try:
                updUser(event.from_user)
            except Exception as e:
                print(f"db error: {e}")
        
        return await handler(event, data)