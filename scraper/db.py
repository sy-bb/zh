import os
from supabase import create_client, Client


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def upsert_stats(data: dict) -> None:
    client = get_client()
    client.table("daily_mining_stats").upsert(
        data, on_conflict="date,pool"
    ).execute()
    print(f"[DB] Saved: {data['pool']} / {data['date']}")
