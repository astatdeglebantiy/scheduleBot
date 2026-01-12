import json
import datetime
import logging
from app.config import time, days, nameDays






# 1
def getJson():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# 2
def checkWeek(target):
    data = getJson()
    if not data: return "week1"
    
    sets = data.get('settings', {})
    aDate = sets.get('date', '12.01.2026')
    aWeek = sets.get('week', 'week2')
    aDay = sets.get('day', 'day1')
    
    off = int(aDay.replace("day", "")) - 1
    dates = datetime.datetime.strptime(aDate, "%d.%m.%Y").date()
    
    base = dates - datetime.timedelta(days=off)
    targ = target - datetime.timedelta(days=target.weekday())
    
    
    diff = (targ - base).days
    
    if diff % 2 == 0:
        return aWeek
    else:

        return "week2" if aWeek == "week1" else "week1"




# 3
def createMsg(week, idx, dates):
    data = getJson()
    key = days.get(idx)

    name = nameDays[idx]
    dStr = dates.strftime("%d.%m")
    
    head = f"<b>{name} ({dStr})</b>"

    if not key or key not in data.get(week, {}):
        return f"{head}\n\nНемає пар"

    lessons = data[week][key]
    if not lessons:
        return f"{head}\n\nНемає пар"

    lst = [head]
    sortKeys = sorted(lessons.keys(), key=lambda x: int(x))
    
    for n in sortKeys:
        info = lessons[n]
        t = time.get(n, "")
        subj = info.get("name", "")
        lnk = info.get("link", "")
        
        blk = f"<b>{n}. [{t}] {subj}</b>\n{lnk}"
        lst.append(blk)


    return "\n\n".join(lst)
