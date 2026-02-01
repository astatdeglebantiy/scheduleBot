import logging
import os
import urllib.request
import pytz
import yaml
from pathlib import Path
from pydantic import BaseModel, model_validator
from typing import Dict, List, Optional, Union
from datetime import datetime

class Subject(BaseModel):
    name: str
    link: str



class AcademicContext(BaseModel):
    reference_date: str
    reference_week: int




class ConfigSchema(BaseModel):
    subjects: Dict[str, Subject]
    schedule: List[Dict[int, List[Optional[Union[str, Subject]]]]]
    time: List[str]
    admins: List[int]
    academic_context: AcademicContext

    @model_validator(mode='after')
    def map_subjects(self):
        new_schedule = []
        for week in self.schedule:
            new_week = {}
            for day_idx, lessons in week.items():
                new_week[day_idx] = [
                    self.subjects.get(lesson) if isinstance(lesson, str) else lesson
                    for lesson in lessons
                ]
            new_schedule.append(new_week)
        self.schedule = new_schedule
        return self






class RootConfig(BaseModel):
    settings: ConfigSchema





class Config:
    def __init__(self):
        self.days: List[str] = [
            "Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"
        ]
        self.tz = pytz.timezone('Europe/Kyiv')
        self.settings = None
        self.bot_token = os.getenv('BOT_TOKEN')
        self.config_url = os.getenv('CONFIG_URL')
        
        if not self.bot_token:
            raise ValueError("BOT_TOKEN not set")
        if not self.config_url:
            raise ValueError("CONFIG_URL not set")
            
        self.load()




    def load(self):
        try:
            with urllib.request.urlopen(self.config_url) as response:
                raw_data = yaml.safe_load(response)
                
            root = RootConfig(**raw_data)
            self.settings = root.settings
            logging.info("Config loaded from URL")
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            raise e

    @property
    def total_weeks(self) -> int:
        return len(self.settings.schedule)




    @property
    def current_week_number(self) -> int:
        return self.get_week_for_date(datetime.now(self.tz))






    def get_week_for_date(self, date: datetime) -> int:
        ctx = self.settings.academic_context
        try:
            ref_date = datetime.strptime(ctx.reference_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid reference_date format")

        delta_days = (date.replace(tzinfo=None) - ref_date).days
        weeks_passed = delta_days // 7

        if self.total_weeks == 0:
            return 1

        return (ctx.reference_week - 1 + weeks_passed) % self.total_weeks + 1






    def get_day_schedule(self, week_idx: int, day_idx: int) -> Optional[List[Optional[Subject]]]:
        if week_idx < 0 or week_idx >= len(self.settings.schedule):
            return None
        
        week_schedule = self.settings.schedule[week_idx]
        return week_schedule.get(day_idx + 1)