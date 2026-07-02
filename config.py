import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("BOT_PREFIX", "!")

# ロール設定
PENDING_ROLE_NAME = os.getenv("PENDING_ROLE_NAME", "認証待ち")
MEMBER_ROLE_NAME = os.getenv("MEMBER_ROLE_NAME", "DTMメンバー")

# 承認申請を投稿するチャンネル名
REQUEST_CHANNEL_NAME = os.getenv("REQUEST_CHANNEL_NAME", "認証申請")

# 拒否時にKickするかどうか
KICK_ON_REJECT = os.getenv("KICK_ON_REJECT", "true").lower() == "true"

# 承認後にメンバーへ送るDMメッセージ (空にすると送信しない)
APPROVED_DM_MESSAGE = os.getenv(
    "APPROVED_DM_MESSAGE",
    "{guild_name} で認証されました。ようこそ！",
)

# 拒否(Kick)時にメンバーへ送るDMメッセージ (空にすると送信しない)
REJECTED_DM_MESSAGE = os.getenv(
    "REJECTED_DM_MESSAGE",
    "{guild_name} への参加申請が承認されませんでした。",
)

# データ保存先
DB_PATH = os.getenv("DB_PATH", "data/pending.json")
