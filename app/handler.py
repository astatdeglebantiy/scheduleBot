import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.config import days
from app.state import Mode
from app.keyboard import getKbd
from app.utils import checkWeek, createMsg

rout = Router()


# 1
@rout.message(Command("start"))
async def start(msg: types.Message, state: FSMContext):
    now = datetime.date.today()
    wk = checkWeek(now)

    if wk == "week1":
        await state.set_state(Mode.week1)
        kb = getKbd("week1")
    else:
        await state.set_state(Mode.week2)
        kb = getKbd("week2")

    await msg.answer("Меню", reply_markup=kb)


# 2
@rout.message(F.text == "Показати 2-й тиждень")
async def setW2(msg: types.Message, state: FSMContext):
    await state.set_state(Mode.week2)
    await msg.answer("Увімкнено перегляд: 2-й тиждень", reply_markup=getKbd("week2"))


# 3
@rout.message(F.text == "Показати 1-й тиждень")
async def setW1(msg: types.Message, state: FSMContext):
    await state.set_state(Mode.week1)
    await msg.answer("Увімкнено перегляд: 1-й тиждень", reply_markup=getKbd("week1"))


# 4
@rout.message(F.text.in_({"Сьогодні", "Завтра"}))
async def relShow(msg: types.Message):
    now = datetime.date.today()
    targ = now if msg.text == "Сьогодні" else now + datetime.timedelta(days=1)
    realWk = checkWeek(targ)
    txt = createMsg(realWk, targ.weekday(), targ)
    await msg.answer(txt, disable_web_page_preview=True)


# 5
@rout.message(F.text.in_({"Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця"}))
async def manShow(msg: types.Message, state: FSMContext):
    curState = await state.get_state()

    aim = "week1"

    if curState == Mode.week2:
        aim = "week2"

    wDay = -1
    for k, v in days.items():
        if v == days.get(msg.text) and isinstance(k, int):
            wDay = k
            break

    now = datetime.date.today()
    curDay = now.weekday()
    cand = now + datetime.timedelta(days=(wDay - curDay))

    candWk = checkWeek(cand)

    fin = cand

    if candWk != aim:
        fin = cand + datetime.timedelta(days=7)

    txt = createMsg(aim, wDay, fin)
    await msg.answer(txt, disable_web_page_preview=True)
