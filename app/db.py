import datetime
import sqlite3

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
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO users (user_id, username, first_name, last_active) VALUES (?, ?, ?, ?)',
                 (user.id, user.username, user.first_name, datetime.datetime.now().isoformat()))
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
