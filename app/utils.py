from datetime import datetime
from app.config import Config



async def create_msg(config: Config, day_idx: int, target_date: datetime = None, week_number: int = None):
    if target_date:
        week = config.get_week_for_date(target_date)
        day_str = target_date.strftime("%d.%m")
        header = f"<b>{config.days[day_idx]} ({day_str})</b>\n<i>Тиждень {week}</i>"
    else:
        week = week_number
        header = f"<b>{config.days[day_idx]}</b>\n<i>Тиждень {week}</i>"

    day_name = config.days[day_idx]




    if day_idx > 4:
        return f"{header}\n\n<b>Вихідний, пар немає</b>"




    day_schedule = config.get_day_schedule(week - 1, day_idx)

    if day_schedule is None:
        return f"{header}\n\nСьогодні пар немає"




    lesson_rows = []
    for i, subject in enumerate(day_schedule):
        if not subject or subject == "None":
            continue

        if isinstance(subject, str):
            subject_obj = config.settings.subjects.get(subject)
        else:
            subject_obj = subject

        lesson_time = config.settings.time[i] if i < len(config.settings.time) else "--:--"

        if subject_obj:
            
            row = f"<b>{i + 1}. [{lesson_time}] <a href='{subject_obj.link}'>{subject_obj.name}</a></b>"
            lesson_rows.append(row)



    if not lesson_rows:
        return f"{header}\n\nСьогодні пар немає"

    return header + "\n\n" + "\n\n".join(lesson_rows)