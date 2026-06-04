import datetime
import os
import pytz
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

sbUrl = os.getenv('SUPABASE_URL')
sbKey = os.getenv('SUPABASE_KEY')

if not sbUrl or not sbKey:
    raise ValueError("SUPABASE_URL or SUPABASE_KEY err")

sb: Client = create_client(sbUrl, sbKey)
KYIV_TZ = pytz.timezone('Europe/Kyiv')




def updUser(user):
    now_kyiv = datetime.datetime.now(KYIV_TZ)
    data = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_active": now_kyiv.isoformat()
    }
    try:
        sb.table("users").upsert(data).execute()
    except Exception:
        pass






def get_total_users():
    try:
        res = sb.table("users").select("*", count="exact", head=True).execute()
        return res.count
    except Exception:
        return 0




def get_users_page(page: int, page_size: int = 40):
    start = page * page_size
    end = start + page_size - 1
    try:
        res = sb.table("users").select("*").order("last_active", desc=True).range(start, end).execute()
        return res.data
    except Exception:
        return []





def get_user_by_id(user_id: int):
    try:
        res = sb.table("users").select("*").eq("user_id", user_id).execute()
        if res.data:
            return res.data[0]
        return None
    except Exception:
        return None


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
