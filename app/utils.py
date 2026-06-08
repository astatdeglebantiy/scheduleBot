from datetime import datetime, timedelta, time
import html
from app.config import Config
from typing import Optional



async def create_msg(config: Config, dayIdx: int, targetDate: datetime = None, weekNumber: int = None, isSaturday: bool = False, checkSaturday: bool = False):
    headerWithWeek = None
    headerNoWeek = None

    show_audience = True
    if config.settings.offline_days is not None:
        show_audience = (dayIdx + 1) in config.settings.offline_days

    if isSaturday:
        satData = config.getNextSaturday()
        if not satData:
            return "<b>Субота</b>\n\nРозклад не знайдено"

        dateStr, satWeek, satDay = satData
        daySchedule = config.get_day_schedule(satWeek - 1, satDay - 1)

        dayName = config.days[satDay - 1]
        safeDayName = html.escape(str(dayName or ""))

        headerNoWeek = f"<b>Субота ({dateStr})</b>\n<i>За розкладом {safeDayName.lower()}</i>"
        headerWithWeek = f"<b>Субота ({dateStr})</b>\n<i>За розкладом {safeDayName.lower()}, {satWeek} тиждень</i>"
    elif targetDate:
        if checkSaturday and dayIdx == 5:
            satDateStr = targetDate.strftime("%d.%m.%Y")
            if config.settings.saturday_schedule and satDateStr in config.settings.saturday_schedule:
                satRef = config.settings.saturday_schedule[satDateStr]
                daySchedule = config.get_day_schedule(satRef.week - 1, satRef.day - 1)

                dayName = config.days[satRef.day - 1]
                safeDayName = html.escape(str(dayName or ""))

                headerNoWeek = f"<b>Субота ({targetDate.strftime('%d.%m')})</b>\n<i>За розкладом {safeDayName.lower()}</i>"
                headerWithWeek = f"<b>Субота ({targetDate.strftime('%d.%m')})</b>\n<i>За розкладом {safeDayName.lower()}, {satRef.week} тиждень</i>"
            else:
                dayStr = targetDate.strftime("%d.%m")
                safeDay = html.escape(str(config.days[dayIdx] or ""))
                headerNoWeek = f"<b>{safeDay} ({dayStr})</b>"
                return f"{headerNoWeek}\n\n<b>Вихідний, пар немає</b>"
        else:
            week = config.get_week_for_date(targetDate)
            dayStr = targetDate.strftime("%d.%m")
            safeDay = html.escape(str(config.days[dayIdx] or ""))
            headerNoWeek = f"<b>{safeDay} ({dayStr})</b>"
            headerWithWeek = f"<b>{safeDay} ({dayStr})</b>\n<i>Тиждень {week}</i>"
    else:
        week = weekNumber
        safeDay = html.escape(str(config.days[dayIdx] or ""))
        headerNoWeek = f"<b>{safeDay}</b>"
        headerWithWeek = f"<b>{safeDay}</b>\n<i>Тиждень {week}</i>"

    if headerWithWeek is None:
        headerWithWeek = headerNoWeek

    if not isSaturday and not (checkSaturday and dayIdx == 5 and targetDate):
        if dayIdx > 4:
            return f"{headerNoWeek}\n\n<b>Вихідний, пар немає</b>"

        daySchedule = config.get_day_schedule(week - 1, dayIdx)

        if daySchedule is None:
            return f"{headerNoWeek}\n\nСьогодні пар немає"

    lessonRows = []
    for i, subject in enumerate(daySchedule):
        if not subject or subject == "None":
            continue

        if isinstance(subject, str):
            subjectObj = config.settings.subjects.get(subject)
        else:
            subjectObj = subject

        lessonTime = config.settings.time[i] if i < len(config.settings.time) else "--:--"

        if subjectObj:
            link = subjectObj.link
            name = subjectObj.name
            audience = subjectObj.audience if hasattr(subjectObj, 'audience') else None
            audience_text = f" <i>авд.{audience}</i>" if (audience and show_audience) else ""
            row = f"<b>{i + 1}. [{lessonTime}] <a href='{html.escape(str(link or ''), quote=True)}'>{html.escape(str(name or ''))}</a></b>{audience_text}"
            lessonRows.append(row)

    if not lessonRows:
        return f"{headerNoWeek}\n\nСьогодні пар немає"

    return headerWithWeek + "\n\n" + "\n\n".join(lessonRows)






def findNextLesson(config: Config, subjectKey: str) -> Optional[tuple[str, str, int, int]]:

    now = datetime.now(config.tz)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)


    now_time = now.time()

    subjectObj = config.settings.subjects.get(subjectKey)
    if not subjectObj:
        return None

    def _parse_start_time(lesson_idx: int) -> Optional[time]:
        if not config.settings.time or lesson_idx >= len(config.settings.time):
            return None
        try:
            start_str = config.settings.time[lesson_idx].split('–')[0].strip()
            h, m = map(int, start_str.split(':'))
            return time(h, m)
        except Exception:
            return None





    def _day_has_future_subject_lesson(day_schedule, *, is_today: bool) -> bool:
        if not day_schedule:
            return False
        for lesson_idx, lesson in enumerate(day_schedule):
            if not lesson:
                continue
            if lesson == subjectObj or (hasattr(lesson, 'name') and lesson.name == subjectObj.name):
                if not is_today:
                    return True
                start_t = _parse_start_time(lesson_idx)
                if start_t is None:
                    return True
                if now_time < start_t:
                    return True
        return False



    for daysAhead in range(365):
        checkDate = today + timedelta(days=daysAhead)
        dayIdx = checkDate.weekday()
        dateStr = checkDate.strftime("%d.%m.%Y")
        is_today = daysAhead == 0

        if config.settings.saturday_schedule and dateStr in config.settings.saturday_schedule:
            satRef = config.settings.saturday_schedule[dateStr]
            daySchedule = config.get_day_schedule(satRef.week - 1, satRef.day - 1)
            if _day_has_future_subject_lesson(daySchedule, is_today=is_today):
                return (dateStr, config.days[satRef.day - 1], satRef.week, 5)
            continue

        if dayIdx < 5:
            weekNum = config.get_week_for_date(checkDate)
            daySchedule = config.get_day_schedule(weekNum - 1, dayIdx)
            if _day_has_future_subject_lesson(daySchedule, is_today=is_today):
                return (dateStr, config.days[dayIdx], weekNum, dayIdx)

    return None