from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def getKbd(typeMode="week1"):
    if typeMode == "week1":
        txt = "Показати 2-й тиждень"
    else:
        txt = "Показати 1-й тиждень"

    kb = [
        [KeyboardButton(text="Сьогодні"), KeyboardButton(text="Завтра")],
        [KeyboardButton(text="Понеділок"), KeyboardButton(text="Вівторок")],
        [KeyboardButton(text="Середа"), KeyboardButton(text="Четвер")],
        [KeyboardButton(text="П'ятниця")],
        [KeyboardButton(text=txt)]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
