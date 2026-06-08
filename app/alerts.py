import asyncio
import logging
import urllib.request
import json
import html
from datetime import datetime, time
from typing import Optional
from aiogram import Bot

async def checkAlertStatus(apiUrl: str) -> Optional[bool]:
    try:
        fullUrl = f"{apiUrl}/aerialalerts/"
        loop = asyncio.get_event_loop()

        response = await loop.run_in_executor(None, urllib.request.urlopen, fullUrl)
        data = json.loads(response.read())
        
        kyivData = data.get('states', {}).get('м. Київ', {})
        return kyivData.get('alertnow', False)

    except Exception as e:

        logging.error(f"Alert API error: {e}")
        return None







def getCurrentLesson(config) -> Optional[tuple[int, str, str, str]]:
    now = datetime.now(config.tz)
    currentTime = now.time()


    if not config.settings.time:
        return None

    for i, timeSlot in enumerate(config.settings.time):
        try:

            times = timeSlot.split('–')
            startTimeStr = times[0].strip()
            endTimeStr = times[1].strip()



            startHour, startMinute = map(int, startTimeStr.split(':'))
            endHour, endMinute = map(int, endTimeStr.split(':'))


            startTime = time(startHour, startMinute)
            endTime = time(endHour, endMinute)




            if startTime <= currentTime <= endTime:
                schedule = getTodaySchedule(config)
                if schedule and i < len(schedule) and schedule[i]:
                    lessonName = schedule[i].name if hasattr(schedule[i], 'name') else str(schedule[i])
                    return (i, lessonName, startTimeStr, endTimeStr)
                return (i, "Невідомо", startTimeStr, endTimeStr)
        except Exception:
            continue

    return None










def getTodaySchedule(config) -> Optional[list]:
    now = datetime.now(config.tz)
    dayIdx = now.weekday()
    dateStr = now.strftime("%d.%m.%Y")
    

    if config.settings.saturday_schedule and dateStr in config.settings.saturday_schedule:
        satRef = config.settings.saturday_schedule[dateStr]
        return config.get_day_schedule(satRef.week - 1, satRef.day - 1)
    



    if dayIdx < 5:
        weekNum = config.get_week_for_date(now)

        return config.get_day_schedule(weekNum - 1, dayIdx)
    
    return None















def isWithinScheduleTime(config) -> bool:
    now = datetime.now(config.tz)
    currentTime = now.time()
    
    todaySchedule = getTodaySchedule(config)
    if not todaySchedule:
        return False
    

    actualLessons = [l for l in todaySchedule if l is not None]
    if not actualLessons:
        return False
    
    if not config.settings.time:
        return False
    
    try:


        lastLessonIdx = len(todaySchedule) - 1
        while lastLessonIdx >= 0 and todaySchedule[lastLessonIdx] is None:
            lastLessonIdx -= 1
        
        if lastLessonIdx < 0:
            return False
        
        lastLessonTime = config.settings.time[lastLessonIdx]
        endTimeStr = lastLessonTime.split('–')[-1].strip()
        endHour, endMinute = map(int, endTimeStr.split(':'))
        scheduleEnd = time(endHour, endMinute)
        


        if currentTime > scheduleEnd:
            return False
        
        for i, lesson in enumerate(todaySchedule):
            if lesson is None or i >= len(config.settings.time):
                continue
            


            timeSlot = config.settings.time[i]
            times = timeSlot.split('–')
            startTimeStr = times[0].strip()
            endTimeStr = times[1].strip()
            
            startHour, startMinute = map(int, startTimeStr.split(':'))
            endHour, endMinute = map(int, endTimeStr.split(':'))
            
            lessonStart = time(startHour, startMinute)
            lessonEnd = time(endHour, endMinute)
            
            if lessonStart <= currentTime <= lessonEnd:
                return True
            



            currentMinutes = currentTime.hour * 60 + currentTime.minute
            lessonStartMinutes = lessonStart.hour * 60 + lessonStart.minute
            
            if 0 < lessonStartMinutes - currentMinutes <= 10:
                return True
        
        return False
    except Exception:
        return False





async def alertMonitorTask(bot: Bot, config):
    from app.db import getUsersWithAlerts, getGroupsWithAlerts

    async def _send_alert_broadcast(message: str, *, include_toggle_kb_for_private: bool = True, disable_preview: bool = False):

        users = getUsersWithAlerts()
        groups = getGroupsWithAlerts()

        for userId in users:
            try:
                chat = await bot.get_chat(userId)
                if chat.type == "private":
                    kb = None
                    if include_toggle_kb_for_private:
                        from app.keyboard import getAlertToggleKb
                        kb = getAlertToggleKb(True)
                    from app.raw_tg import send_message
                    await send_message(
                        bot,
                        userId,
                        message,
                        parse_mode="HTML",
                        disable_web_page_preview=disable_preview or None,
                        reply_markup=kb,
                    )
            except Exception as e:
                logging.error(f"Failed to send alert to {userId}: {e}")

        group_message = message + "\n\nВведіть /off або /on для вимкнення/увімкнення сповіщень в групі."
        for chat_id in groups:
            try:
                chat = await bot.get_chat(chat_id)
                if chat.type in {"group", "supergroup"}:
                    from app.raw_tg import send_message
                    await send_message(
                        bot,
                        chat_id,
                        group_message,
                        parse_mode="HTML",
                        disable_web_page_preview=disable_preview or None,
                    )
            except Exception as e:
                logging.error(f"Failed to send group alert to {chat_id}: {e}")

        return (len(users), len(groups))
    
    lastAlertState = False
    lastAlertStartedAt: Optional[datetime] = None
    lastAlertClearedAt: Optional[datetime] = None

    missedLessons = {}
    alertStartedOutsideSchedule = False

    lastConfigRevision = getattr(config, "revision", 0)

    while True:
        try:
            if not config.alert_api_url:
                await asyncio.sleep(config.alert_check_interval)
                continue
            
            currentAlert = await checkAlertStatus(config.alert_api_url)
            
            if currentAlert is None:
                await asyncio.sleep(config.alert_check_interval)
                continue
            
            now_dt = datetime.now(config.tz)
            prevAlertState = lastAlertState

            if currentAlert != lastAlertState:
                if currentAlert:
                    lastAlertStartedAt = now_dt
                    if not isWithinScheduleTime(config):
                        alertStartedOutsideSchedule = True
                else:
                    lastAlertClearedAt = now_dt
                    alertStartedOutsideSchedule = False
                    missedLessons.clear()

                lastAlertState = currentAlert

            withinSchedule = isWithinScheduleTime(config)


            currentRevision = getattr(config, "revision", 0)
            if currentRevision != lastConfigRevision:
                lastConfigRevision = currentRevision

            if not withinSchedule:
                await asyncio.sleep(config.alert_check_interval)
                continue
            



            currentLesson = getCurrentLesson(config)
            
            if currentAlert and not prevAlertState and not alertStartedOutsideSchedule:
                if currentLesson:

                    lessonIdx, lessonName, startTime, endTime = currentLesson

                    now = datetime.now(config.tz)
                    currentTime = now.time()

                    timeSlot = config.settings.time[lessonIdx]
                    times = timeSlot.split('–')
                    startTimeStr = times[0].strip()
                    startHour, startMinute = map(int, startTimeStr.split(':'))
                    lessonStart = time(startHour, startMinute)

                    todaySchedule = getTodaySchedule(config)
                    lessonObj = todaySchedule[lessonIdx] if todaySchedule and lessonIdx < len(todaySchedule) else None
                    lessonLink = lessonObj.link if lessonObj and hasattr(lessonObj, 'link') else None

                    safeLessonName = html.escape(str(lessonName or ""))
                    safeStartTime = html.escape(str(startTime or ""))
                    safeEndTime = html.escape(str(endTime or ""))
                    safeLessonLink = html.escape(str(lessonLink or ""), quote=True)

                    if currentTime < lessonStart:
                        if lessonLink:
                            message = f"<b>ПОВІТРЯНА ТРИВОГА!</b>\n\nСкоро почнеться пара <a href='{safeLessonLink}'>{safeLessonName}</a>\nЧас: {safeStartTime} – {safeEndTime}"
                        else:
                            message = f"<b>ПОВІТРЯНА ТРИВОГА!</b>\n\nСкоро почнеться пара <b>{safeLessonName}</b>\nЧас: {safeStartTime} – {safeEndTime}"
                    else:
                        if lessonLink:
                            message = f"<b>ПОВІТРЯНА ТРИВОГА!</b>\n\nПари <a href='{safeLessonLink}'>{safeLessonName}</a> поки не буде\nЧас: {safeStartTime} – {safeEndTime}"
                        else:
                            message = f"<b>ПОВІТРЯНА ТРИВОГА!</b>\n\nПари <b>{safeLessonName}</b> поки не буде\nЧас: {safeStartTime} – {safeEndTime}"
                        missedLessons.clear()
                        missedLessons[lessonIdx] = lessonName
                else:
                    message = "<b>ПОВІТРЯНА ТРИВОГА!</b>"

                user_cnt, group_cnt = await _send_alert_broadcast(message, disable_preview=True)
                logging.info(f"Alert sent to {user_cnt} users and {group_cnt} groups")
            
            elif currentAlert and alertStartedOutsideSchedule and currentLesson:
                lessonIdx, lessonName, startTime, endTime = currentLesson
                


                now = datetime.now(config.tz)
                currentTime = now.time()
                
                timeSlot = config.settings.time[lessonIdx]
                times = timeSlot.split('–')


                startTimeStr = times[0].strip()
                startHour, startMinute = map(int, startTimeStr.split(':'))
                lessonStart = time(startHour, startMinute)
                
                currentMinutes = currentTime.hour * 60 + currentTime.minute
                lessonStartMinutes = lessonStart.hour * 60 + lessonStart.minute
                


                warningKey = f"{lessonIdx}_warning"
                
                if 0 < lessonStartMinutes - currentMinutes <= 10 and warningKey not in missedLessons:
                    todaySchedule = getTodaySchedule(config)
                    lessonObj = todaySchedule[lessonIdx] if todaySchedule and lessonIdx < len(todaySchedule) else None
                    lessonLink = lessonObj.link if lessonObj and hasattr(lessonObj, 'link') else None

                    safeLessonName = html.escape(str(lessonName or ""))
                    safeStartTime = html.escape(str(startTime or ""))
                    safeEndTime = html.escape(str(endTime or ""))
                    safeLessonLink = html.escape(str(lessonLink or ""), quote=True)

                    if lessonLink:
                        message = f"<b>Тривога продовжується</b>\n\n<b>Скоро почнеться пара</b>\n\n<a href='{safeLessonLink}'>{safeLessonName}</a>\nЧас: {safeStartTime} – {safeEndTime}"
                    else:
                        message = f"<b>Тривога продовжується</b>\n\n<b>Скоро почнеться пара</b>\n\n<b>{safeLessonName}</b>\nЧас: {safeStartTime} – {safeEndTime}"
                    missedLessons[warningKey] = True

                    user_cnt, group_cnt = await _send_alert_broadcast(message, disable_preview=True)
                    logging.info(f"Lesson warning sent to {user_cnt} users and {group_cnt} groups")



                
                if lessonStart <= currentTime and lessonIdx not in missedLessons:
                    alertStartedOutsideSchedule = False

                    todaySchedule = getTodaySchedule(config)
                    lessonObj = todaySchedule[lessonIdx] if todaySchedule and lessonIdx < len(todaySchedule) else None
                    lessonLink = lessonObj.link if lessonObj and hasattr(lessonObj, 'link') else None

                    safeLessonName = html.escape(str(lessonName or ""))
                    safeStartTime = html.escape(str(startTime or ""))
                    safeEndTime = html.escape(str(endTime or ""))
                    safeLessonLink = html.escape(str(lessonLink or ""), quote=True)

                    if lessonLink:
                        message = f"<b>Тривога продовжується</b>\n\n<b>Почалась пара</b>\n\n<a href='{safeLessonLink}'>{safeLessonName}</a>\nЧас: {safeStartTime} – {safeEndTime}"
                    else:
                        message = f"<b>Тривога продовжується</b>\n\n<b>Почалась пара</b>\n\n<b>{safeLessonName}</b>\nЧас: {safeStartTime} – {safeEndTime}"

                    missedLessons[lessonIdx] = lessonName

                    user_cnt, group_cnt = await _send_alert_broadcast(message, disable_preview=True)
                    logging.info(f"Lesson start sent to {user_cnt} users and {group_cnt} groups")
            
            elif currentAlert and prevAlertState and currentLesson and not alertStartedOutsideSchedule:


                lessonIdx, lessonName, startTime, endTime = currentLesson
                
                now = datetime.now(config.tz)
                currentTime = now.time()
                
                timeSlot = config.settings.time[lessonIdx]
                times = timeSlot.split('–')
                startTimeStr = times[0].strip()
                endTimeStr = times[1].strip()


                startHour, startMinute = map(int, startTimeStr.split(':'))
                endHour, endMinute = map(int, endTimeStr.split(':'))
                lessonStart = time(startHour, startMinute)
                lessonEnd = time(endHour, endMinute)


                
                currentMinutes = currentTime.hour * 60 + currentTime.minute
                lessonStartMinutes = lessonStart.hour * 60 + lessonStart.minute
                lessonEndMinutes = lessonEnd.hour * 60 + lessonEnd.minute
                
                warningKey = f"{lessonIdx}_warning"
                
                if currentMinutes < lessonStartMinutes and 0 < lessonStartMinutes - currentMinutes <= 10 and warningKey not in missedLessons:
                    todaySchedule = getTodaySchedule(config)
                    lessonObj = todaySchedule[lessonIdx] if todaySchedule and lessonIdx < len(todaySchedule) else None
                    lessonLink = lessonObj.link if lessonObj and hasattr(lessonObj, 'link') else None

                    safeLessonName = html.escape(str(lessonName or ""))
                    safeStartTime = html.escape(str(startTime or ""))
                    safeEndTime = html.escape(str(endTime or ""))
                    safeLessonLink = html.escape(str(lessonLink or ""), quote=True)

                    if lessonLink:
                        message = f"<b>Тривога продовжується</b>\n\n<b>Скоро почнеться пара</b>\n\n<a href='{safeLessonLink}'>{safeLessonName}</a>\nЧас: {safeStartTime} – {safeEndTime}"
                    else:
                        message = f"<b>Тривога продовжується</b>\n\n<b>Скоро почнеться пара</b>\n\n<b>{safeLessonName}</b>\nЧас: {safeStartTime} – {safeEndTime}"
                    missedLessons[warningKey] = True

                    user_cnt, group_cnt = await _send_alert_broadcast(message, disable_preview=True)
                    logging.info(f"Lesson warning sent to {user_cnt} users and {group_cnt} groups")
                
                if lessonIdx not in missedLessons and lessonStart <= currentTime <= lessonEnd:
                    todaySchedule = getTodaySchedule(config)
                    lessonObj = todaySchedule[lessonIdx] if todaySchedule and lessonIdx < len(todaySchedule) else None
                    lessonLink = lessonObj.link if lessonObj and hasattr(lessonObj, 'link') else None

                    safeLessonName = html.escape(str(lessonName or ""))
                    safeStartTime = html.escape(str(startTime or ""))
                    safeEndTime = html.escape(str(endTime or ""))
                    safeLessonLink = html.escape(str(lessonLink or ""), quote=True)

                    if lessonLink:
                        message = f"<b>Тривога продовжується</b>\n\n<b>Почалась пара</b>\n\n<a href='{safeLessonLink}'>{safeLessonName}</a>\nЧас: {safeStartTime} – {safeEndTime}"
                    else:
                        message = f"<b>Тривога продовжується</b>\n\n<b>Почалась пара</b>\n\n<b>{safeLessonName}</b>\nЧас: {safeStartTime} – {safeEndTime}"

                    missedLessons[lessonIdx] = lessonName

                    user_cnt, group_cnt = await _send_alert_broadcast(message, disable_preview=True)
                    logging.info(f"Alert continuation sent to {user_cnt} users and {group_cnt} groups")
            


            if (not currentAlert) and prevAlertState:
                if isWithinScheduleTime(config):
                    now = datetime.now(config.tz)
                    currentTime = now.time()
                    todaySchedule = getTodaySchedule(config)
                    
                    nextLessonInfo = None
                    if todaySchedule and config.settings.time:
                        for i, lesson in enumerate(todaySchedule):
                            if lesson is None or i >= len(config.settings.time):
                                continue
                            
                            timeSlot = config.settings.time[i]
                            times = timeSlot.split('–')
                            startTimeStr = times[0].strip()
                            endTimeStr = times[1].strip()
                            
                            startHour, startMinute = map(int, startTimeStr.split(':'))
                            endHour, endMinute = map(int, endTimeStr.split(':'))
                            
                            lessonStart = time(startHour, startMinute)
                            lessonEnd = time(endHour, endMinute)
                            
                            if currentTime < lessonStart:
                                lessonName = lesson.name if hasattr(lesson, 'name') else str(lesson)
                                lessonLink = lesson.link if hasattr(lesson, 'link') else None
                                nextLessonInfo = (lessonName, lessonLink, startTimeStr, endTimeStr, None)
                                break
                            elif lessonStart <= currentTime <= lessonEnd:
                                lessonName = lesson.name if hasattr(lesson, 'name') else str(lesson)
                                lessonLink = lesson.link if hasattr(lesson, 'link') else None

                                currentMinutes = currentTime.hour * 60 + currentTime.minute
                                lessonEndMinutes = lessonEnd.hour * 60 + lessonEnd.minute
                                minutesLeft = lessonEndMinutes - currentMinutes

                                nextLessonInfo = (lessonName, lessonLink, startTimeStr, endTimeStr, minutesLeft)
                                break
                    




                    if nextLessonInfo:
                        lessonName, lessonLink, startTime, endTime, minutesLeft = nextLessonInfo

                        remainingLine = f"\nЗалишилось: {minutesLeft} хв" if minutesLeft is not None else ""

                        safeLessonName = html.escape(str(lessonName or ""))
                        safeStartTime = html.escape(str(startTime or ""))
                        safeEndTime = html.escape(str(endTime or ""))
                        safeRemainingLine = html.escape(str(remainingLine or ""))
                        safeLessonLink = html.escape(str(lessonLink or ""), quote=True)

                        if lessonLink:
                            message = (
                                f"<b>Тривога скасована</b>\n\n"
                                f"Зараз пара: <a href='{safeLessonLink}'>{safeLessonName}</a>\n"
                                f"Час: {safeStartTime} – {safeEndTime}{safeRemainingLine}"
                            )
                        else:
                            message = (
                                f"<b>Тривога скасована</b>\n\n"
                                f"Зараз пара: <b>{safeLessonName}</b>\n"
                                f"Час: {safeStartTime} – {safeEndTime}{safeRemainingLine}"
                            )
                        
                        user_cnt, group_cnt = await _send_alert_broadcast(message, disable_preview=True)
                        logging.info(f"Alert end sent to {user_cnt} users and {group_cnt} groups")

                        if lastAlertClearedAt is not None:
                            clear_age_min = int((now_dt - lastAlertClearedAt).total_seconds() // 60)
                            if clear_age_min >= 10:
                                currentMinutes = currentTime.hour * 60 + currentTime.minute
                                for i, lesson in enumerate(todaySchedule or []):
                                    if lesson is None or i >= len(config.settings.time):
                                        continue

                                    timeSlot = config.settings.time[i]
                                    times = timeSlot.split('–')
                                    startTimeStr = times[0].strip()
                                    endTimeStr = times[1].strip()

                                    startHour, startMinute = map(int, startTimeStr.split(':'))
                                    endHour, endMinute = map(int, endTimeStr.split(':'))

                                    lessonStart = time(startHour, startMinute)
                                    lessonEnd = time(endHour, endMinute)

                                    lessonStartMinutes = lessonStart.hour * 60 + lessonStart.minute
                                    lessonEndMinutes = lessonEnd.hour * 60 + lessonEnd.minute

                                    is_t_minus_10 = 0 < (lessonStartMinutes - currentMinutes) <= 10
                                    is_in_progress = lessonStartMinutes <= currentMinutes <= lessonEndMinutes
                                    if not (is_t_minus_10 or is_in_progress):
                                        continue

                                    flag_key = f"{i}_clear_early_{'tminus10' if is_t_minus_10 else 'started'}"
                                    if flag_key in missedLessons:
                                        continue

                                    lessonName2 = lesson.name if hasattr(lesson, 'name') else str(lesson)
                                    lessonLink2 = lesson.link if hasattr(lesson, 'link') else None

                                    title = "<b>Скоро почнеться пара</b>" if is_t_minus_10 else "<b>Почалась пара</b>"

                                    safeLessonName2 = html.escape(str(lessonName2 or ""))
                                    safeStartTimeStr = html.escape(str(startTimeStr or ""))
                                    safeEndTimeStr = html.escape(str(endTimeStr or ""))
                                    safeLessonLink2 = html.escape(str(lessonLink2 or ""), quote=True)

                                    if lessonLink2:
                                        body = f"\n\n<a href='{safeLessonLink2}'>{safeLessonName2}</a>\nЧас: {safeStartTimeStr} – {safeEndTimeStr}"
                                    else:
                                        body = f"\n\n<b>{safeLessonName2}</b>\nЧас: {safeStartTimeStr} – {safeEndTimeStr}"

                                    message2 = title + body + "\n\nВідбій був раніше"
                                    missedLessons[flag_key] = True

                                    user_cnt, group_cnt = await _send_alert_broadcast(message2)
                                    logging.info(f"Clear-early notify sent to {user_cnt} users and {group_cnt} groups")

                                    break

                missedLessons.clear()
            
        except Exception as e:
            logging.error(f"Alert monitor error: {e}")
        
        await asyncio.sleep(config.alert_check_interval)
