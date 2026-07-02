import asyncio
import json
import os

import config

_lock = asyncio.Lock()


def _ensure_file() -> None:
    os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)
    if not os.path.exists(config.DB_PATH):
        with open(config.DB_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)


async def load_pending() -> dict:
    """message_id(str) -> {user_id, guild_id} の保留中承認申請一覧を返す"""
    async with _lock:
        _ensure_file()
        with open(config.DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)


async def add_pending(message_id: int, user_id: int, guild_id: int) -> None:
    async with _lock:
        _ensure_file()
        with open(config.DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        data[str(message_id)] = {"user_id": user_id, "guild_id": guild_id}
        with open(config.DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


async def remove_pending(message_id: int) -> None:
    async with _lock:
        _ensure_file()
        with open(config.DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.pop(str(message_id), None)
        with open(config.DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


async def find_pending_by_user(guild_id: int, user_id: int) -> int | None:
    """指定ユーザーの保留中申請メッセージIDを返す (無ければNone)"""
    data = await load_pending()
    for message_id, entry in data.items():
        if entry.get("guild_id") == guild_id and entry.get("user_id") == user_id:
            return int(message_id)
    return None
