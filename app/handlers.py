import datetime
import re
import html
from aiogram import Router, types, F, Bot
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.config import Config
from app.utils import create_msg
from app.keyboard import get_keyboard, get_stat_pagination_kb
from app.db import get_total_users, get_users_page, get_user_by_id




rout = Router()




REL_BUTTONS = {"Сьогодні": 0, "Завтра": 1, "Субота": -1}




async def generate_stat_message(bot_username: str, page: int = 0):
    limit = 40
    total_users = get_total_users()
    total_pages = (total_users + limit - 1) // limit
    if total_pages == 0: total_pages = 1
    
    users = get_users_page(page, limit)
    
    txt = f"Всього користувачів: {total_users}\nСторінка: {page + 1}/{total_pages}\n\n"
    
    if not users:
        txt += "Список порожній"
    
    for u in users:
        uid = u.get('user_id')
        name = u.get('first_name', 'NoName') or 'NoName'
        if len(name) > 15: name = name[:15] + ".."
        name = html.escape(name)
        
        last_active_str = "?"
        raw_time = u.get('last_active')
        if raw_time:
            try:
                import pytz
                dt = datetime.datetime.fromisoformat(raw_time)
                if dt.tzinfo is None:
                    dt = pytz.utc.localize(dt).astimezone(pytz.timezone('Europe/Kyiv'))
                else:
                    dt = dt.astimezone(pytz.timezone('Europe/Kyiv'))
                last_active_str = dt.strftime("%d.%m %H:%M")
            except: pass

        link = f"https://t.me/{bot_username}?start=info_{uid}"

        alertValue = u.get('alert_notifications')
        alertStatus = str(alertValue)
        txt += f"• <a href='{link}'>{name}</a> {last_active_str}; {alertStatus}\n"
    
    return txt, get_stat_pagination_kb(page, total_pages)







@rout.message(Command("stat"))
async def statCmd(msg: types.Message, config: Config, bot: Bot):
    if msg.from_user.id not in config.settings.admins:
        return
    bot_info = await bot.get_me()
    text, kb = await generate_stat_message(bot_info.username, 0)
    await msg.answer(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)






@rout.callback_query(F.data.startswith("stat_page_"))
async def stat_pagination(call: CallbackQuery, config: Config, bot: Bot):
    if call.from_user.id not in config.settings.admins:
        await call.answer()
        return
    page = int(call.data.split("_")[-1])
    bot_info = await bot.get_me()
    text, kb = await generate_stat_message(bot_info.username, page)
    if call.message.html_text != text:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
    await call.answer()


@rout.callback_query(F.data == "next_lesson")
async def nextLessonCallback(call: CallbackQuery, config: Config):
    from app.keyboard import getSubjectsInlineKb
    kb = getSubjectsInlineKb(config)
    await call.message.answer("Оберіть предмет:", reply_markup=kb, parse_mode="HTML")
    await call.answer()


@rout.callback_query(F.data == "schedule_by_date")
async def scheduleByDateCallback(call: CallbackQuery, state: FSMContext):
    from app.state import Mode
    await state.set_state(Mode.waiting_date)
    await call.message.answer("Введіть дату у форматі РРРР.МM.ДД або ММ.ДД")
    await call.answer()


@rout.callback_query(F.data == "alert_toggle")
async def alertToggleCallback(call: CallbackQuery):
    if call.message.chat.type != "private":
        await call.answer("Ця функція доступна тільки в особистих повідомленнях", show_alert=True)
        return
    
    from app.db import setAlertNotifications, getAlertNotifications
    from app.keyboard import getNextLessonInlineKb
    
    currentState = getAlertNotifications(call.from_user.id)
    newState = not currentState
    setAlertNotifications(call.from_user.id, newState)
    
    status = "увімкнено" if newState else "вимкнено"
    kb = getNextLessonInlineKb(newState)

    from app.raw_tg import edit_message_reply_markup
    await edit_message_reply_markup(call.bot, call.message.chat.id, call.message.message_id, reply_markup=kb)
    await call.answer(f"Сповіщення {status}")


@rout.callback_query(F.data.in_({"alert_enable", "alert_disable"}))
async def alertEnableDisableCallback(call: CallbackQuery):
    if call.message.chat.type != "private":
        await call.answer("Ця функція доступна тільки в особистих повідомленнях", show_alert=True)
        return
    
    from app.db import setAlertNotifications
    from app.keyboard import getAlertToggleKb
    
    newState = call.data == "alert_enable"
    setAlertNotifications(call.from_user.id, newState)
    
    status = "увімкнено" if newState else "вимкнено"
    kb = getAlertToggleKb(newState)

    from app.raw_tg import edit_message_reply_markup
    await edit_message_reply_markup(call.bot, call.message.chat.id, call.message.message_id, reply_markup=kb)
    await call.answer(f"Сповіщення {status}")




@rout.message(Command('wn'))
async def whats_new(msg: types.Message, config: Config):
    version = getattr(config.settings, 'app_version', '0.0.0')
    raw_body = getattr(config.settings, 'whats_new_text', '') or ""

    _TG_EMOJI_RE = re.compile(r"\[(\d{10,})\]")

    def _format_whats_new(text: str) -> str:

        lines = [ln.rstrip() for ln in text.splitlines()]

        out: list[str] = []
        blank_streak = 0
        for ln in lines:
            if not ln.strip():
                blank_streak += 1
                if blank_streak <= 1:
                    out.append("")
                continue

            blank_streak = 0
            stripped = ln.lstrip()
            if stripped.startswith("- ") or stripped.startswith("-"):
                item = stripped[1:].lstrip()
                out.append(f"• {item}")
            else:
                out.append(ln.strip())

        formatted = "\n".join(out).strip()

        tgEmojiTagRe = re.compile(r"<tg-emoji\s+emoji-id=[\"'](\d{10,})[\"']\s*>.*?<\/tg-emoji>", re.I | re.S)

        emojiIds: list[str] = []

        def _stash_emoji(m: re.Match) -> str:
            emojiIds.append(m.group(1))
            return f"{{{{TG_EMOJI_{len(emojiIds) - 1}}}}}"

        formatted = tgEmojiTagRe.sub(_stash_emoji, formatted)
        formatted = _TG_EMOJI_RE.sub(_stash_emoji, formatted)
        formatted = html.escape(formatted)

        for i, emojiId in enumerate(emojiIds):
            formatted = formatted.replace(f"{{{{TG_EMOJI_{i}}}}}", f"<tg-emoji emoji-id=\"{emojiId}\">✨</tg-emoji>")

        return formatted

    body = _format_whats_new(raw_body)
    if not body:
        body = "(порожньо)"

    txt = f"<b>Версія {version}</b>\n\n{body}"
    await msg.answer(txt, parse_mode="HTML", disable_web_page_preview=True)


@rout.message(Command('reload'))
async def reload_config(msg: types.Message, state: FSMContext, config: Config):
    if msg.from_user.id in config.settings.admins:
        try:
            old_rev = getattr(config, "revision", 0)
            config.load()
            new_rev = getattr(config, "revision", 0)
            await msg.answer(f"Успішно оновлено! ({old_rev} → {new_rev})")
            await show_menu(msg, state, config)
        except Exception as e:
            err = html.escape(str(e))
            await msg.answer(f"Помилка завантаження конфігу:\n<pre>{err}</pre>", parse_mode="HTML", disable_web_page_preview=True)


@rout.message(Command("on"))
async def group_on(msg: types.Message):
    if msg.chat.type not in {"group", "supergroup"}:
        await msg.reply("Ця команда працює тільки в групі. В особистих — керування через кнопку сповіщень.")
        return

    from app.db import setGroupAlertNotifications

    setGroupAlertNotifications(msg.chat.id, True)
    await msg.reply("Сповіщення в цій групі: увімкнено.\nЩоб вимкнути — введіть /off")


@rout.message(Command("off"))
async def group_off(msg: types.Message):
    if msg.chat.type not in {"group", "supergroup"}:
        await msg.reply("Ця команда працює тільки в групі. В особистих — керування через кнопку сповіщень.")
        return

    from app.db import setGroupAlertNotifications

    setGroupAlertNotifications(msg.chat.id, False)
    await msg.reply("Сповіщення в цій групі: вимкнено.\nЩоб увімкнути — введіть /on")






@rout.callback_query(F.data.startswith("next_"))
async def nextSubjectCallback(call: CallbackQuery, config: Config):
    subjectKey = call.data.split("_", 1)[1]
    from app.utils import findNextLesson
    result = findNextLesson(config, subjectKey)
    if result:
        dateStr, dayName, weekNum, dayIdx = result
        parsedDate = datetime.datetime.strptime(dateStr, "%d.%m.%Y")
        targetDate = config.tz.localize(parsedDate)
        txt = await create_msg(config, dayIdx=dayIdx, targetDate=targetDate, checkSaturday=True)
        await call.message.edit_text(txt, parse_mode="HTML", disable_web_page_preview=True)
    else:
        await call.message.edit_text("Пари з цього предмету не знайдено")
    await call.answer()


@rout.message(CommandStart())
async def start(msg: types.Message, state: FSMContext, config: Config, command: CommandObject):
    args = command.args

    if args and args.startswith("info_") and msg.from_user.id in config.settings.admins:
        try:
            target_id = int(args.split("_")[1])
            u = get_user_by_id(target_id)
            if not u:
                await msg.answer("Не знайдено")
                return
            la = "Невідомо"
            if u.get('last_active'):
                try:
                    import pytz
                    dt = datetime.datetime.fromisoformat(u.get('last_active'))
                    if dt.tzinfo is None:
                        dt = pytz.utc.localize(dt).astimezone(pytz.timezone('Europe/Kyiv'))
                    else:
                        dt = dt.astimezone(pytz.timezone('Europe/Kyiv'))
                    la = dt.strftime("%d.%m.%Y %H:%M:%S")
                except: pass
            first_name = html.escape(str(u.get('first_name') or ""))
            username = html.escape(str(u.get('username') or ""))

            alertValue = u.get('alert_notifications')
            alertStatus = str(alertValue)

            info = f"ID: <code>{u.get('user_id')}</code>\nІм'я: {first_name}\nЮзер: @{username}\nАктивність: {la}\nТривога: {alertStatus}"
            await msg.answer(info, parse_mode="HTML")
            return
        except:
            await msg.answer("Помилка")
            return

    startText = (
        f"<blockquote>"
        f"<tg-emoji emoji-id='5366288132834599020'>🛠</tg-emoji> Dev: <a href='https://t.me/RTCET'>RTCET</a>\n\n"
        f"<tg-emoji emoji-id='5317028762074750983'>💻</tg-emoji><tg-emoji emoji-id='5318827507263217597'>💻</tg-emoji> Contributor: <a href='https://t.me/astatf'>astatf</a>"
        f"</blockquote>\n\n"
        f"<tg-emoji emoji-id='5382357040008021292'>🔔</tg-emoji> Версія {config.settings.app_version} - /wn"
    )
    
    from app.state import Mode
    await state.set_state(Mode.main)
    data = await state.get_data()
    viewingWeek = data.get("viewing_week", config.current_week_number)
    
    from app.raw_tg import send_message

    if msg.chat.type == "private":
        from app.keyboard import getNextLessonInlineKb
        from app.db import getAlertNotifications

        alertEnabled = getAlertNotifications(msg.from_user.id)
        inlineKb = getNextLessonInlineKb(alertEnabled)
        await send_message(
            msg.bot,
            msg.chat.id,
            startText,
            reply_markup=inlineKb,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    else:
        groupHint = "\n\n<b>Сповіщення для групи:</b> введіть /on або /off"
        await send_message(
            msg.bot,
            msg.chat.id,
            startText + groupHint,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    await send_message(msg.bot, msg.chat.id, "Меню:", reply_markup=get_keyboard(config, viewingWeek))






@rout.message(F.text == "← Тиждень →")
async def switch_week(msg: types.Message, state: FSMContext, config: Config):
    data = await state.get_data()
    viewing_week = data.get("viewing_week", config.current_week_number)
    new_week = (viewing_week % config.total_weeks) + 1
    await state.update_data(viewing_week=new_week)
    await msg.answer(f"Тиждень: <b>{new_week}</b>", parse_mode="HTML")










@rout.message(F.text.in_({"Сьогодні", "Завтра", "Субота"}))
async def rel_show(msg: types.Message, state: FSMContext, config: Config):
    from app.state import Mode
    await state.set_state(Mode.main)
    if msg.text == "Субота":
        txt = await create_msg(config, dayIdx=5, targetDate=None, isSaturday=True)
    else:
        targetDate = datetime.datetime.now(config.tz) + datetime.timedelta(days=REL_BUTTONS[msg.text])
        txt = await create_msg(config, dayIdx=targetDate.weekday(), targetDate=targetDate, checkSaturday=True)
    await msg.answer(txt, parse_mode="HTML", disable_web_page_preview=True)





@rout.message(lambda msg, config: msg.text in config.days)
async def man_show(msg: types.Message, state: FSMContext, config: Config):
    from app.state import Mode
    await state.set_state(Mode.main)
    data = await state.get_data()
    viewingWeek = data.get("viewing_week", config.current_week_number)
    dayIdx = config.days.index(msg.text)

    txt = await create_msg(config, dayIdx=dayIdx, targetDate=None, weekNumber=viewingWeek)
    await msg.answer(txt, parse_mode="HTML", disable_web_page_preview=True)


@rout.message(lambda msg: True)
async def date_input_handler(msg: types.Message, state: FSMContext, config: Config):
    from app.state import Mode
    current_state = await state.get_state()

    date_text = msg.text.strip()

    try:
        if date_text.count('.') == 2:
            parts = date_text.split('.')
            if len(parts[0]) == 4:
                target_date = datetime.datetime.strptime(date_text, "%Y.%m.%d")
            else:
                target_date = datetime.datetime.strptime(date_text, "%d.%m.%Y")
        elif date_text.count('.') == 1:
            current_year = datetime.datetime.now(config.tz).year
            target_date = datetime.datetime.strptime(f"{date_text}.{current_year}", "%m.%d.%Y")
        else:
            if current_state == Mode.waiting_date:
                await state.set_state(Mode.main)
                await msg.answer("Неправильний формат. Використовуйте РРРР.ММ.ДД або ММ.ДД")
            return

        await state.set_state(Mode.main)
        target_date = config.tz.localize(target_date)
        day_idx = target_date.weekday()

        txt = await create_msg(config, dayIdx=day_idx, targetDate=target_date, checkSaturday=True)
        await msg.answer(txt, parse_mode="HTML", disable_web_page_preview=True)

    except ValueError:
        if current_state == Mode.waiting_date:
            await state.set_state(Mode.main)
            await msg.answer("Неправильний формат дати. Використовуйте РРРР.ММ.ДД або ММ.ДД")









async def show_menu(msg: types.Message, state: FSMContext, config: Config):
    from app.state import Mode
    await state.set_state(Mode.main)
    data = await state.get_data()
    viewingWeek = data.get("viewing_week", config.current_week_number)
    from app.raw_tg import send_message
    await send_message(msg.bot, msg.chat.id, "Меню:", reply_markup=get_keyboard(config, viewingWeek))