import asyncio
import logging
import os

import discord
from discord.ext import commands

import config

os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("data/bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("SecurityBot")

COGS = [
    "cogs.verification",
]

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)


@bot.event
async def on_ready():
    logger.info(f"Bot起動: {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="新規参加者を確認中")
    )


@bot.command(name="status")
@commands.has_permissions(administrator=True)
async def status(ctx):
    """Botのステータスを表示"""
    embed = discord.Embed(title="Security Bot ステータス", color=discord.Color.green())
    embed.add_field(name="稼働中のCog", value="\n".join(f"✅ {c}" for c in bot.cogs), inline=False)
    embed.add_field(name="サーバー数", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    await ctx.send(embed=embed)


async def main():
    if not config.TOKEN:
        raise SystemExit("DISCORD_TOKEN が設定されていません。.env を確認してください。")

    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                logger.info(f"Cog読み込み: {cog}")
            except Exception as e:
                logger.error(f"Cog読み込み失敗 {cog}: {e}")
        await bot.start(config.TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
