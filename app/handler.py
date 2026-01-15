from datetime import datetime, timedelta
import logging

import pytz
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from app.config import Config
from app.state import Mode
from app.utils import create_msg

rout = Router()


@rout.message(Command('reload'))
async def reload_config(msg: types.Message, config: Config):
    if msg.from_user.id in config.settings.admins:
        config.reload()
        await msg.answer("Config reloaded")


@rout.message(Command("start"))
async def start(msg: types.Message, state: FSMContext, config: Config):
    await state.set_state(Mode.main)
    builder = ReplyKeyboardBuilder()

    builder.add(KeyboardButton(text="Сьогодні"), KeyboardButton(text="Завтра"))

    for day in config.days[:5]:
        builder.add(KeyboardButton(text=day))

    builder.add(
        KeyboardButton(text="<- Попередній тиждень"),
        KeyboardButton(text="Наступний тиждень ->")
    )

    # 2 — Сьогодні, Завтра
    # 2 — Понеділок, Вівторок
    # 2 — Середа, Четвер
    # 1 — П'ятниця
    # 2 — Попередній, Наступний тиждень
    builder.adjust(2, 2, 2, 1, 2)

    await msg.answer(
        "Оберіть день або тиждень:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )


@rout.message(F.text.in_({"<- Попередній тиждень", "Наступний тиждень ->"}))
async def switch_week(msg: types.Message, state: FSMContext, config: Config):
    data = await state.get_data()
    curr = data.get("viewing_week", config.current_week_number)
    total = config.total_weeks

    if msg.text == "Наступний тиждень ->":
        new_week = curr + 1
        if new_week > total:
            new_week = 1
    else:
        new_week = curr - 1
        if new_week < 1:
            new_week = total

    await state.update_data(viewing_week=new_week)
    await msg.answer(f"Увімкнено перегляд: <b>{new_week}-й тиждень</b>", parse_mode="HTML")


@rout.message(F.text.in_({"Сьогодні", "Завтра"}))
async def rel_show(msg: types.Message, state: FSMContext, config: Config):
    target_date = datetime.now(config.tz)

    if msg.text == "Завтра":
        target_date += timedelta(days=1)

    day_idx = target_date.weekday()

    txt = await create_msg(config, state, day_idx=day_idx, target_date=target_date)

    await msg.answer(txt, parse_mode="HTML", disable_web_page_preview=True)


@rout.message(lambda msg, config: msg.text in config.days[:5])
async def man_show(msg: types.Message, state: FSMContext, config: Config):
    data = await state.get_data()
    viewing_week = data.get("viewing_week", config.current_week_number)
    day_idx = config.days.index(msg.text)

    today = datetime.now(config.tz).replace(hour=0, minute=0, second=0, microsecond=0)
    days_diff = day_idx - today.weekday()
    target_date = today + timedelta(days=days_diff)

    actual_week = config.get_week_for_date(target_date)

    if actual_week != viewing_week:
        week_diff = viewing_week - actual_week
        target_date += timedelta(weeks=week_diff)

    await state.update_data(viewing_day=day_idx)
    txt = await create_msg(config, state, day_idx=day_idx, target_date=target_date)
    await msg.answer(txt, parse_mode="HTML", disable_web_page_preview=True)
