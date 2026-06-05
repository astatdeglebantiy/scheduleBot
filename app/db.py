import datetime
import pytz
import sqlite3


KYIV_TZ = pytz.timezone('Europe/Kyiv')

def get_db_connection():
    conn = sqlite3.connect('scheduleBot.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_active TEXT)')
    conn.commit()
    conn.close()

def updUser(user):
    now_kyiv = datetime.datetime.now(KYIV_TZ)

    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO users (user_id, username, first_name, last_active) VALUES (?, ?, ?, ?)',
                 (user.id, user.username, user.first_name, now_kyiv.isoformat()))
    conn.commit()
    conn.close()

def get_total_users():
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    conn.close()
    return count

def get_users_page(page: int, page_size: int = 40):
    start = page * page_size
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY last_active DESC LIMIT ? OFFSET ?', (page_size, start)).fetchall()
    conn.close()
    return [dict(user) for user in users]

def get_user_by_id(user_id: int):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

init_db()


def setAlertNotifications(userId: int, enabled: bool):
    try:
        sb.table("users").update({"alert_notifications": enabled}).eq("user_id", userId).execute()
    except Exception:
        pass


def getAlertNotifications(userId: int) -> bool:
    try:
        res = sb.table("users").select("alert_notifications").eq("user_id", userId).execute()
        if res.data:
            alertValue = res.data[0].get("alert_notifications")
            if alertValue is None:
                return True
            return alertValue
        return True
    except Exception:
        return True


def getUsersWithAlerts():
    try:
        res = sb.table("users").select("user_id, alert_notifications").execute()
        users = []
        for u in res.data:
            alertValue = u.get("alert_notifications")
            if alertValue is None or alertValue is True:
                userId = u.get("user_id")
                if userId:
                    users.append(userId)
        return users
    except Exception:
        return []



def upsertGroupChat(chat):

    try:
        chat_type = getattr(chat, "type", None)
        if chat_type not in {"group", "supergroup"}:
            return

        now_kyiv = datetime.datetime.now(KYIV_TZ)
        data = {
            "chat_id": chat.id,
            "title": getattr(chat, "title", None),
            "username": getattr(chat, "username", None),
            "type": chat_type,
            "last_active": now_kyiv.isoformat(),
        }
        sb.table("groups").upsert(data).execute()
    except Exception:
        pass


def setGroupAlertNotifications(chat_id: int, enabled: bool):
    try:
        sb.table("groups").update({"alert_notifications": enabled}).eq("chat_id", chat_id).execute()
    except Exception:
        pass


def getGroupAlertNotifications(chat_id: int) -> bool:
    try:
        res = sb.table("groups").select("alert_notifications").eq("chat_id", chat_id).execute()
        if res.data:
            v = res.data[0].get("alert_notifications")
            if v is None:
                return True
            return bool(v)
        return True
    except Exception:
        return True


def getGroupsWithAlerts():
    try:
        res = sb.table("groups").select("chat_id, alert_notifications").execute()
        chats: list[int] = []
        for g in res.data:
            v = g.get("alert_notifications")
            if v is None or v is True:
                cid = g.get("chat_id")
                if cid:
                    chats.append(cid)
        return chats
    except Exception:
        return []
