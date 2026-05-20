import datetime
from aiogram import Router, types, F, Bot
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.config import Config
from app.utils import create_msg
from app.keyboard import get_keyboard, get_stat_pagination_kb
from app.db import get_total_users, get_users_page, get_user_by_id




rout = Router()




REL_BUTTONS = {"Сьогодні": 0, "Завтра": 1}




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
        
        last_active_str = "?"
        raw_time = u.get('last_active')
        if raw_time:
            try:
                dt = datetime.datetime.fromisoformat(raw_time)
                last_active_str = dt.strftime("%d.%m %H:%M")
            except: pass

        link = f"https://t.me/{bot_username}?start=info_{uid}"
        txt += f"• <a href='{link}'>{name}</a> {last_active_str}\n"
    
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




@rout.message(Command('reload'))
async def reload_config(msg: types.Message, state: FSMContext, config: Config):
    if msg.from_user.id in config.settings.admins:
        try:
            config.load()
            await msg.answer("Успішно оновлено!")
            await show_menu(msg, state, config)
        except Exception as e:
            await msg.answer(f"Помилка: {e}")






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
                    dt = datetime.datetime.fromisoformat(u.get('last_active'))
                    la = dt.strftime("%d.%m.%Y %H:%M:%S")
                except: pass
            info = f"ID: <code>{u.get('user_id')}</code>\nІм'я: {u.get('first_name')}\nЮзер: @{u.get('username')}\nАктивність: {la}"
            await msg.answer(info, parse_mode="HTML")
            return
        except:
            await msg.answer("Помилка")
            return

    start_text = (
        f"<blockquote>"
        f"<tg-emoji emoji-id='5366288132834599020'>🛠</tg-emoji> Dev: @RTCET\n\n"
        f"<tg-emoji emoji-id='5317028762074750983'>💻</tg-emoji><tg-emoji emoji-id='5318827507263217597'>💻</tg-emoji> Contributor: @astatf"
        f"<tg-emoji emoji-id='5294325496228620537'>❓</tg-emoji> Якщо розклад змінився, надішліть пулл-реквест з оновленим конфігом <a href='https://github.com/rtplugate-hub/SRooT'>сюди</a>"
        f"</blockquote>\n\n"
    )

    await msg.answer(start_text, parse_mode="HTML", disable_web_page_preview=True)
    await show_menu(msg, state, config)






@rout.message(F.text == "← Тиждень →")
async def switch_week(msg: types.Message, state: FSMContext, config: Config):
    data = await state.get_data()
    viewing_week = data.get("viewing_week", config.current_week_number)
    new_week = (viewing_week % config.total_weeks) + 1
    await state.update_data(viewing_week=new_week)
    await msg.answer(f"Тиждень: <b>{new_week}</b>", parse_mode="HTML")










@rout.message(F.text.in_({"Сьогодні", "Завтра"}))
async def rel_show(msg: types.Message, state: FSMContext, config: Config):
    target_date = datetime.datetime.now(config.tz) + datetime.timedelta(days=REL_BUTTONS[msg.text])
    txt = await create_msg(config, day_idx=target_date.weekday(), target_date=target_date)
    await msg.answer(txt, parse_mode="HTML", disable_web_page_preview=True)





@rout.message(lambda msg, config: msg.text in config.days)
async def man_show(msg: types.Message, state: FSMContext, config: Config):
    data = await state.get_data()
    viewing_week = data.get("viewing_week", config.current_week_number)
    day_idx = config.days.index(msg.text)

    txt = await create_msg(config, day_idx=day_idx, target_date=None, week_number=viewing_week)
    await msg.answer(txt, parse_mode="HTML", disable_web_page_preview=True)









async def show_menu(msg: types.Message, state: FSMContext, config: Config):
    from app.state import Mode
    await state.set_state(Mode.main)
    data = await state.get_data()
    viewing_week = data.get("viewing_week", config.current_week_number)
    await msg.answer("Меню:", reply_markup=get_keyboard(config, viewing_week))