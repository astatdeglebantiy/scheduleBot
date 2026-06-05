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
    conn.execute('CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, title TEXT, username TEXT, type TEXT, last_active TEXT)')

    try:
        conn.execute('SELECT alert_notifications FROM users LIMIT 1')
    except sqlite3.OperationalError:
        conn.execute('ALTER TABLE users ADD COLUMN alert_notifications INTEGER DEFAULT 1')

    try:
        conn.execute('SELECT alert_notifications FROM groups LIMIT 1')
    except sqlite3.OperationalError:
        conn.execute('ALTER TABLE groups ADD COLUMN alert_notifications INTEGER DEFAULT 1')

    conn.commit()
    conn.close()

def updUser(user):
    now_kyiv = datetime.datetime.now(KYIV_TZ)

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO users (user_id, username, first_name, last_active)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_active = excluded.last_active
    ''', (user.id, user.username, user.first_name, now_kyiv.isoformat()))
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

def setAlertNotifications(userId: int, enabled: bool):
    try:
        conn = get_db_connection()
        conn.execute('UPDATE users SET alert_notifications = ? WHERE user_id = ?', (int(enabled), userId))
        conn.commit()
        conn.close()
    except Exception:
        pass


def getAlertNotifications(userId: int) -> bool:
    try:
        conn = get_db_connection()
        res = conn.execute('SELECT alert_notifications FROM users WHERE user_id = ?', (userId,)).fetchone()
        conn.close()
        if res and res['alert_notifications'] is not None:
            return bool(res['alert_notifications'])
        return True
    except Exception:
        return True


def getUsersWithAlerts():
    try:
        conn = get_db_connection()
        res = conn.execute('SELECT user_id FROM users WHERE alert_notifications = 1 OR alert_notifications IS NULL').fetchall()
        conn.close()
        return [row['user_id'] for row in res]
    except Exception:
        return []



def upsertGroupChat(chat):

    try:
        chat_type = getattr(chat, "type", None)
        if chat_type not in {"group", "supergroup"}:
            return

        now_kyiv = datetime.datetime.now(KYIV_TZ)
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO groups (chat_id, title, username, type, last_active)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                username = excluded.username,
                type = excluded.type,
                last_active = excluded.last_active
        ''', (
            chat.id,
            getattr(chat, "title", None),
            getattr(chat, "username", None),
            chat_type,
            now_kyiv.isoformat(),
        ))
        conn.commit()
        conn.close()
    except Exception:
        pass


def setGroupAlertNotifications(chat_id: int, enabled: bool):
    try:
        conn = get_db_connection()
        conn.execute('UPDATE groups SET alert_notifications = ? WHERE chat_id = ?', (int(enabled), chat_id))
        conn.commit()
        conn.close()
    except Exception:
        pass


def getGroupAlertNotifications(chat_id: int) -> bool:
    try:
        conn = get_db_connection()
        res = conn.execute('SELECT alert_notifications FROM groups WHERE chat_id = ?', (chat_id,)).fetchone()
        conn.close()
        if res and res['alert_notifications'] is not None:
            return bool(res['alert_notifications'])
        return True
    except Exception:
        return True


def getGroupsWithAlerts():
    try:
        conn = get_db_connection()
        res = conn.execute('SELECT chat_id FROM groups WHERE alert_notifications = 1 OR alert_notifications IS NULL').fetchall()
        conn.close()
        return [row['chat_id'] for row in res]
    except Exception:
        return []

init_db()
