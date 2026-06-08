import asyncio
import logging
import html
from datetime import datetime, time
from typing import Optional, Tuple, List, Dict, Any
from aiogram import Bot
import aiohttp

from app.db import getUsersWithAlerts, getGroupsWithAlerts
from app.keyboard import getAlertToggleKb
from app.raw_tg import send_message

class AlertManager:
    def __init__(self, bot: Bot, config: Any):
        self.bot = bot
        self.config = config
        self.session = aiohttp.ClientSession()
        self.last_alert_state = False
        self.last_alert_started_at: Optional[datetime] = None
        self.missed_lessons: Dict[Any, Any] = {}
        self.alert_started_outside_schedule = False

    async def check_alert_status(self) -> Optional[bool]:
        if not self.config.alert_api_url:
            return None
        try:
            async with self.session.get(f"{self.config.alert_api_url}/aerialalerts/") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('states', {}).get('м. Київ', {}).get('alertnow', False)
                else:
                    logging.error(f"Alert API request failed with status {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logging.error(f"Alert API error: {e}")
            return None

    def get_today_schedule(self) -> Optional[List[Any]]:
        now = datetime.now(self.config.tz)
        day_idx = now.weekday()
        date_str = now.strftime("%d.%m.%Y")

        if self.config.settings.saturday_schedule and date_str in self.config.settings.saturday_schedule:
            sat_ref = self.config.settings.saturday_schedule[date_str]
            return self.config.get_day_schedule(sat_ref.week - 1, sat_ref.day - 1)

        if day_idx < 5:
            week_num = self.config.get_week_for_date(now)
            return self.config.get_day_schedule(week_num - 1, day_idx)
        
        return None

    def get_current_lesson(self) -> Optional[Tuple[int, str, str, str]]:
        now = datetime.now(self.config.tz)
        current_time = now.time()

        if not self.config.settings.time:
            return None

        for i, time_slot in enumerate(self.config.settings.time):
            try:
                start_time_str, end_time_str = map(str.strip, time_slot.split('–'))
                start_hour, start_minute = map(int, start_time_str.split(':'))
                end_hour, end_minute = map(int, end_time_str.split(':'))
                start_time = time(start_hour, start_minute)
                end_time = time(end_hour, end_minute)

                if start_time <= current_time <= end_time:
                    schedule = self.get_today_schedule()
                    if schedule and i < len(schedule) and schedule[i]:
                        lesson_name = schedule[i].name if hasattr(schedule[i], 'name') else str(schedule[i])
                        return i, lesson_name, start_time_str, end_time_str
                    return i, "Невідомо", start_time_str, end_time_str
            except (ValueError, IndexError):
                continue
        return None

    def is_within_schedule_time(self) -> bool:
        now = datetime.now(self.config.tz)
        current_time = now.time()
        today_schedule = self.get_today_schedule()

        if not today_schedule or not self.config.settings.time:
            return False

        try:
            last_lesson_idx = next((i for i, l in reversed(list(enumerate(today_schedule))) if l), -1)
            if last_lesson_idx == -1:
                return False

            end_time_str = self.config.settings.time[last_lesson_idx].split('–')[-1].strip()
            end_hour, end_minute = map(int, end_time_str.split(':'))
            if current_time > time(end_hour, end_minute):
                return False

            for i, lesson in enumerate(today_schedule):
                if lesson and i < len(self.config.settings.time):
                    start_str, end_str = self.config.settings.time[i].split('–')
                    start_time = time(*map(int, start_str.strip().split(':')))
                    end_time = time(*map(int, end_str.strip().split(':')))
                    
                    if start_time <= current_time <= end_time:
                        return True
                    
                    if 0 < (start_time.hour * 60 + start_time.minute) - (current_time.hour * 60 + current_time.minute) <= 10:
                        return True
            return False
        except (ValueError, IndexError):
            return False

    async def send_broadcast(self, message: str, include_kb: bool = True, disable_preview: bool = False):
        users = getUsersWithAlerts()
        groups = getGroupsWithAlerts()

        user_tasks = [
            self.send_to_user(uid, message, include_kb, disable_preview) for uid in users
        ]
        group_tasks = [
            self.send_to_group(gid, message, disable_preview) for gid in groups
        ]
        
        await asyncio.gather(*user_tasks, *group_tasks)
        return len(users), len(groups)

    async def send_to_user(self, user_id: int, message: str, include_kb: bool, disable_preview: bool):
        try:
            kb = getAlertToggleKb(True) if include_kb else None
            await send_message(
                self.bot, user_id, message,
                disable_web_page_preview=disable_preview, reply_markup=kb
            )
        except Exception as e:
            logging.error(f"Failed to send alert to {user_id}: {e}")

    async def send_to_group(self, group_id: int, message: str, disable_preview: bool):
        group_message = f"{message}\n\nВведіть /off або /on для вимкнення/увімкнення сповіщень в групі."
        try:
            await send_message(
                self.bot, group_id, group_message,
                disable_web_page_preview=disable_preview
            )
        except Exception as e:
            logging.error(f"Failed to send group alert to {group_id}: {e}")

    def format_lesson_message(self, title: str, lesson_info: Tuple) -> str:
        lesson_name, lesson_link, start_time, end_time, *_ = lesson_info
        safe_lesson_name = html.escape(str(lesson_name or ""))
        safe_start_time = html.escape(str(start_time or ""))
        safe_end_time = html.escape(str(end_time or ""))
        
        if lesson_link:
            safe_lesson_link = html.escape(str(lesson_link or ""), quote=True)
            lesson_str = f"<a href='{safe_lesson_link}'>{safe_lesson_name}</a>"
        else:
            lesson_str = f"<b>{safe_lesson_name}</b>"
            
        return f"<b>{title}</b>\n\n{lesson_str}\nЧас: {safe_start_time} – {safe_end_time}"

    async def handle_alert_start(self, current_lesson):
        self.last_alert_started_at = datetime.now(self.config.tz)
        if not self.is_within_schedule_time():
            self.alert_started_outside_schedule = True
            return

        if current_lesson:
            lesson_idx, lesson_name, start_time, end_time = current_lesson
            now = datetime.now(self.config.tz)
            lesson_start_time = time(*map(int, start_time.split(':')))
            
            today_schedule = self.get_today_schedule()
            lesson_obj = today_schedule[lesson_idx] if today_schedule and lesson_idx < len(today_schedule) else None
            lesson_link = lesson_obj.link if lesson_obj and hasattr(lesson_obj, 'link') else None

            title = "ПОВІТРЯНА ТРИВОГА!"
            if now.time() < lesson_start_time:
                message = self.format_lesson_message(f"{title} Скоро почнеться пара", (lesson_name, lesson_link, start_time, end_time))
            else:
                message = self.format_lesson_message(f"{title} Пари поки не буде", (lesson_name, lesson_link, start_time, end_time))
                self.missed_lessons[lesson_idx] = lesson_name
        else:
            message = "<b>ПОВІТРЯНА ТРИВОГА!</b>"
        
        user_cnt, group_cnt = await self.send_broadcast(message, disable_preview=True)
        logging.info(f"Alert sent to {user_cnt} users and {group_cnt} groups")

    async def handle_alert_end(self):
        self.alert_started_outside_schedule = False
        self.missed_lessons.clear()

        if self.is_within_schedule_time():
            message = "<b>Тривога скасована</b>"
            user_cnt, group_cnt = await self.send_broadcast(message)
            logging.info(f"Alert end sent to {user_cnt} users and {group_cnt} groups")

    async def handle_ongoing_alert(self, current_lesson):
        if not current_lesson:
            return

        lesson_idx, lesson_name, start_time, end_time = current_lesson
        now = datetime.now(self.config.tz)
        current_time = now.time()
        lesson_start_time = time(*map(int, start_time.split(':')))
        
        minutes_to_lesson = (lesson_start_time.hour * 60 + lesson_start_time.minute) - (current_time.hour * 60 + current_time.minute)
        warning_key = f"{lesson_idx}_warning"

        today_schedule = self.get_today_schedule()
        lesson_obj = today_schedule[lesson_idx] if today_schedule and lesson_idx < len(today_schedule) else None
        lesson_link = lesson_obj.link if lesson_obj and hasattr(lesson_obj, 'link') else None
        lesson_info = (lesson_name, lesson_link, start_time, end_time)

        if 0 < minutes_to_lesson <= 10 and warning_key not in self.missed_lessons:
            message = self.format_lesson_message("Тривога триває. Скоро почнеться пара", lesson_info)
            self.missed_lessons[warning_key] = True
            user_cnt, group_cnt = await self.send_broadcast(message, disable_preview=True)
            logging.info(f"Lesson warning sent to {user_cnt} users and {group_cnt} groups")

        elif lesson_start_time <= current_time and lesson_idx not in self.missed_lessons:
            message = self.format_lesson_message("Тривога триває. Почалась пара", lesson_info)
            self.missed_lessons[lesson_idx] = lesson_name
            user_cnt, group_cnt = await self.send_broadcast(message, disable_preview=True)
            logging.info(f"Lesson start sent to {user_cnt} users and {group_cnt} groups")

    async def run(self):
        while True:
            try:
                current_alert = await self.check_alert_status()
                if current_alert is None:
                    await asyncio.sleep(self.config.alert_check_interval)
                    continue

                if current_alert != self.last_alert_state:
                    if current_alert:
                        await self.handle_alert_start(self.get_current_lesson())
                    else:
                        await self.handle_alert_end()
                    self.last_alert_state = current_alert
                
                elif current_alert:
                    await self.handle_ongoing_alert(self.get_current_lesson())

            except Exception as e:
                logging.error(f"Alert monitor error: {e}")
            
            await asyncio.sleep(self.config.alert_check_interval)

async def alertMonitorTask(bot: Bot, config: Any):
    manager = AlertManager(bot, config)
    await manager.run()
