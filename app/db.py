import datetime
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

sbUrl = os.getenv('SUPABASE_URL')
sbKey = os.getenv('SUPABASE_KEY')

if not sbUrl or not sbKey:
    raise ValueError("SUPABASE_URL or SUPABASE_KEY err")


sb: Client = create_client(sbUrl, sbKey)




def updUser(user):
    data = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_active": datetime.datetime.now().isoformat()
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
