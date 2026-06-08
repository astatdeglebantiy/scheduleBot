from typing import Any

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

class ColoredInlineKeyboardButton(InlineKeyboardButton):
    style: str | None = None


class ColoredKeyboardButton(KeyboardButton):
    style: str | None = None


class ColoredInlineKeyboardMarkup(InlineKeyboardMarkup):
    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("serialize_as_any", True)
        return super().model_dump(*args, **kwargs)

    def model_dump_json(self, *args, **kwargs):
        kwargs.setdefault("serialize_as_any", True)
        return super().model_dump_json(*args, **kwargs)





class ColoredReplyKeyboardMarkup(ReplyKeyboardMarkup):
    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("serialize_as_any", True)
        return super().model_dump(*args, **kwargs)


    def model_dump_json(self, *args, **kwargs):
        kwargs.setdefault("serialize_as_any", True)
        return super().model_dump_json(*args, **kwargs)





def _chunk(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]





def getNextLessonInlineKb(alertEnabled: bool = True, isGroup: bool = False) -> Any:
    buttons = []

    if not isGroup:
        alertStatus = "увімк" if alertEnabled else "вимк"
        buttons.append([
            {
                "text": f"Повітряна тривога | {alertStatus}",
                "callback_data": "alert_toggle",
                "style": "success" if alertEnabled else "danger",
            }
        ])

    buttons.append([
        {
            "text": "Наступна пара",
            "callback_data": "next_lesson",
            "style": "primary",
        }
    ])

    buttons.append([
        {
            "text": "Розклад по даті",
            "callback_data": "schedule_by_date",
            "style": "danger",
        }
    ])

    return {"inline_keyboard": buttons}







def getAlertToggleKb(enabled: bool) -> Any:
    if enabled:
        btn = {
            "text": "Вимкнути сповіщення",
            "callback_data": "alert_disable",
            "style": "danger",
        }
    else:
        btn = {
            "text": "Увімкнути сповіщення",
            "callback_data": "alert_enable",
            "style": "success",
        }
    return {"inline_keyboard": [[btn]]}




def getSubjectsInlineKb(config) -> Any:
    buttons = []
    for subjectKey, subjectObj in config.settings.subjects.items():
        buttons.append({"text": subjectObj.name, "callback_data": f"next_{subjectKey}"})
    return {"inline_keyboard": _chunk(buttons, 2)}





def get_keyboard(config, viewing_week: int) -> Any:
    hasSaturday = config.getNextSaturday() is not None

    first_row = [
        {"text": "Сьогодні", "style": "primary"},
        {"text": "Завтра", "style": "success"},
    ]
    if hasSaturday:
        first_row.append({"text": "Субота", "style": "danger"})

    daysWithSchedule = []
    weekSchedule = config.settings.schedule[viewing_week - 1]

    for dayIdx, dayName in enumerate(config.days):
        dayKey = dayIdx + 1
        dayLessons = weekSchedule.get(dayKey)
        if dayLessons and any(lesson is not None for lesson in dayLessons):
            daysWithSchedule.append(dayName)

    day_buttons = [{"text": day} for day in daysWithSchedule]
    day_rows = []
    if day_buttons:
        pairs = len(day_buttons) // 2
        day_rows.extend(_chunk(day_buttons[: pairs * 2], 2))
        if len(day_buttons) % 2 == 1:
            day_rows.append([day_buttons[-1]])

    keyboard = [first_row, *day_rows, [{"text": "← Тиждень →"}]]
    return {"keyboard": keyboard, "resize_keyboard": True}









def get_stat_pagination_kb(current_page: int, total_pages: int, mode: str = "users") -> Any:
    buttons = []
    if current_page > 0:
        buttons.append({"text": "<", "callback_data": f"stat_{mode}_{current_page - 1}"})

    buttons.append({"text": f"{current_page + 1}/{total_pages}", "callback_data": "noop"})

    if current_page < total_pages - 1:
        buttons.append({"text": ">", "callback_data": f"stat_{mode}_{current_page + 1}"})

    switch_button_text = "Групи" if mode == "users" else "Користувачі"
    switch_callback = "stat_switch_groups" if mode == "users" else "stat_switch_users"

    return {"inline_keyboard": [buttons, [{"text": switch_button_text, "callback_data": switch_callback}]]}