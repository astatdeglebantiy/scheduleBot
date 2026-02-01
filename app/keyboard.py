from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_keyboard(config, viewing_week: int) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Сьогодні"), KeyboardButton(text="Завтра"))

    days_with_schedule = []
    week_schedule = config.settings.schedule[viewing_week - 1]

    for day_idx, day_name in enumerate(config.days):
        day_key = day_idx + 1
        day_lessons = week_schedule.get(day_key)
        if day_lessons and any(lesson is not None for lesson in day_lessons):
            days_with_schedule.append(day_name)

    for day in days_with_schedule:
        builder.add(KeyboardButton(text=day))

    builder.add(
        KeyboardButton(text="← Тиждень →")
    )

    sizes = [2]
    num_day_buttons = len(days_with_schedule)
    if num_day_buttons > 0:
        sizes.extend([2] * (num_day_buttons // 2))
        if num_day_buttons % 2 == 1:
            sizes.append(1)
    sizes.append(1)
    builder.adjust(*sizes)

    return builder.as_markup(resize_keyboard=True)







def get_stat_pagination_kb(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    buttons = []
    if current_page > 0:
        buttons.append(InlineKeyboardButton(text="<", callback_data=f"stat_page_{current_page - 1}"))
    
    buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="noop"))
    
    if current_page < total_pages - 1:
        buttons.append(InlineKeyboardButton(text=">", callback_data=f"stat_page_{current_page + 1}"))
        
    builder.row(*buttons)
    return builder.as_markup()