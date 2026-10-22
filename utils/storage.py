import asyncio
import json
import os
from datetime import datetime

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


def _state_path() -> str:
    # 保留中申請ファイルと同じ場所（Fly.io ではボリューム）に置く
    return os.path.join(os.path.dirname(config.DB_PATH) or ".", "state.json")


async def get_last_seen() -> datetime | None:
    """Botが最後に稼働していた時刻（UTC）。一度も記録がなければNone"""
    async with _lock:
        try:
            with open(_state_path(), "r", encoding="utf-8") as f:
                value = json.load(f).get("last_seen")
        except FileNotFoundError:
            return None
    return datetime.fromisoformat(value) if value else None


async def set_last_seen(at: datetime) -> None:
    async with _lock:
        _ensure_file()
        with open(_state_path(), "w", encoding="utf-8") as f:
            json.dump({"last_seen": at.isoformat()}, f)
