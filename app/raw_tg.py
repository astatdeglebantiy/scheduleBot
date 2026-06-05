import json
from typing import Any, Optional

import aiohttp
from aiogram import Bot


async def _request(bot: Bot, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{bot.token}/{method}"
    data = dict(payload)
    if "reply_markup" in data and isinstance(data["reply_markup"], (dict, list)):
        data["reply_markup"] = json.dumps(data["reply_markup"], ensure_ascii=False)



    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as resp:
            res = await resp.json(content_type=None)
            if not res.get("ok"):
                raise RuntimeError(f"Telegram API error ({method}): {res}")
            return res





async def send_message(bot: Bot, chat_id: int, text: str, *, reply_markup: Any = None, parse_mode: Optional[str] = None, disable_web_page_preview: Optional[bool] = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    if parse_mode is not None:
        payload["parse_mode"] = parse_mode
    if disable_web_page_preview is not None:
        payload["disable_web_page_preview"] = disable_web_page_preview
    return await _request(bot, "sendMessage", payload)




async def edit_message_reply_markup(bot: Bot, chat_id: int, message_id: int, *, reply_markup: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"chat_id": chat_id, "message_id": message_id}

    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return await _request(bot, "editMessageReplyMarkup", payload)
