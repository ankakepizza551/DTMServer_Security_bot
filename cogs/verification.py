import logging

import discord
from discord.ext import commands

import config
from utils import storage

logger = logging.getLogger("SecurityBot.verification")


def build_request_embed(member: discord.Member) -> discord.Embed:
    embed = discord.Embed(
        title="🔔 認証申請",
        description=f"{member.mention} さんがサーバーに参加しました。",
        color=discord.Color.orange(),
    )
    embed.add_field(name="ユーザー", value=f"{member} ({member.id})", inline=False)
    embed.add_field(
        name="アカウント作成日",
        value=discord.utils.format_dt(member.created_at, style="R"),
        inline=False,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="管理者が下のボタンで承認・拒否できます。")
    return embed


def build_result_embed(
    member_display: str,
    avatar_url: str | None,
    moderator: discord.abc.User,
    approved: bool,
) -> discord.Embed:
    if approved:
        embed = discord.Embed(
            title="✅ 認証承認済み",
            description=f"{member_display} を「{config.MEMBER_ROLE_NAME}」として承認しました。",
            color=discord.Color.green(),
        )
    else:
        action = "Kickしました" if config.KICK_ON_REJECT else "拒否しました"
        embed = discord.Embed(
            title="❌ 認証拒否",
            description=f"{member_display} の申請を{action}。",
            color=discord.Color.red(),
        )
    embed.set_footer(text=f"操作者: {moderator}")
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    return embed


class VerificationView(discord.ui.View):
    """承認/拒否ボタンを持つ永続View。custom_id に user_id を埋め込む。"""

    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

        approve = discord.ui.Button(
            label="承認",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id=f"dtmverify:approve:{user_id}",
        )
        approve.callback = self.approve
        self.add_item(approve)

        reject = discord.ui.Button(
            label="拒否",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            custom_id=f"dtmverify:reject:{user_id}",
        )
        reject.callback = self.reject
        self.add_item(reject)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.guild_permissions.administrator:
            await interaction.response.send_message(
                "この操作は管理者権限を持つメンバーのみ実行できます。", ephemeral=True
            )
            return False
        return True

    async def _resolve_member(self, guild: discord.Guild) -> discord.Member | None:
        member = guild.get_member(self.user_id)
        if member is not None:
            return member
        try:
            return await guild.fetch_member(self.user_id)
        except discord.NotFound:
            return None

    async def approve(self, interaction: discord.Interaction):
        guild = interaction.guild
        assert guild is not None
        member = await self._resolve_member(guild)

        if member is None:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="⚠️ 対象ユーザーが見つかりません",
                    description="ユーザーはすでにサーバーを退出しています。",
                    color=discord.Color.greyple(),
                ),
                view=None,
            )
            await storage.remove_pending(interaction.message.id)
            return

        member_role = discord.utils.get(guild.roles, name=config.MEMBER_ROLE_NAME)
        if member_role is None:
            await interaction.response.send_message(
                f"ロール「{config.MEMBER_ROLE_NAME}」が見つかりません。サーバー設定を確認してください。",
                ephemeral=True,
            )
            return

        pending_role = discord.utils.get(guild.roles, name=config.PENDING_ROLE_NAME)

        try:
            await member.add_roles(member_role, reason=f"{interaction.user} が認証を承認")
            if pending_role is not None and pending_role in member.roles:
                await member.remove_roles(pending_role, reason="認証承認によるロール入れ替え")
        except discord.Forbidden:
            await interaction.response.send_message(
                "Botにロール操作権限がありません。Botのロールを対象ロールより上に配置してください。",
                ephemeral=True,
            )
            return

        embed = build_result_embed(str(member), member.display_avatar.url, interaction.user, approved=True)
        await interaction.response.edit_message(embed=embed, view=None)
        await storage.remove_pending(interaction.message.id)
        logger.info(f"認証承認: {member} by {interaction.user}")

        if config.APPROVED_DM_MESSAGE:
            try:
                await member.send(config.APPROVED_DM_MESSAGE.format(guild_name=guild.name))
            except discord.HTTPException:
                pass

        if config.WELCOME_CHANNEL_NAME:
            welcome_channel = discord.utils.get(guild.text_channels, name=config.WELCOME_CHANNEL_NAME)
            if welcome_channel is not None:
                try:
                    await welcome_channel.send(
                        config.WELCOME_MESSAGE_TEMPLATE.format(member=member.mention, guild=guild.name)
                    )
                except discord.Forbidden:
                    logger.error(f"ウェルカムチャンネルへの送信権限がありません ({guild.name})")
            else:
                logger.error(f"ウェルカムチャンネル「{config.WELCOME_CHANNEL_NAME}」が見つかりません ({guild.name})")

    async def reject(self, interaction: discord.Interaction):
        guild = interaction.guild
        assert guild is not None
        member = await self._resolve_member(guild)

        if member is None:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="⚠️ 対象ユーザーが見つかりません",
                    description="ユーザーはすでにサーバーを退出しています。",
                    color=discord.Color.greyple(),
                ),
                view=None,
            )
            await storage.remove_pending(interaction.message.id)
            return

        member_display = str(member)
        avatar_url = member.display_avatar.url

        if config.REJECTED_DM_MESSAGE:
            try:
                await member.send(config.REJECTED_DM_MESSAGE.format(guild_name=guild.name))
            except discord.HTTPException:
                pass

        try:
            if config.KICK_ON_REJECT:
                await member.kick(reason=f"{interaction.user} が認証を拒否")
        except discord.Forbidden:
            await interaction.response.send_message(
                "BotにKick権限がありません。Botの権限設定を確認してください。",
                ephemeral=True,
            )
            return

        embed = build_result_embed(member_display, avatar_url, interaction.user, approved=False)
        await interaction.response.edit_message(embed=embed, view=None)
        await storage.remove_pending(interaction.message.id)
        logger.info(f"認証拒否: {member_display} by {interaction.user} (kick={config.KICK_ON_REJECT})")


class Verification(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # 保留中の承認申請に対して永続Viewを再登録し、再起動後もボタンを有効にする
        pending = await storage.load_pending()
        for message_id, entry in pending.items():
            self.bot.add_view(VerificationView(entry["user_id"]), message_id=int(message_id))
        if pending:
            logger.info(f"保留中の認証申請 {len(pending)} 件のViewを再登録しました。")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        pending_role = discord.utils.get(guild.roles, name=config.PENDING_ROLE_NAME)

        if pending_role is None:
            logger.error(f"ロール「{config.PENDING_ROLE_NAME}」が見つかりません ({guild.name})")
        else:
            try:
                await member.add_roles(pending_role, reason="新規参加: 認証待ちロール付与")
            except discord.Forbidden:
                logger.error(f"ロール付与権限がありません ({guild.name})")

        channel = discord.utils.get(guild.text_channels, name=config.REQUEST_CHANNEL_NAME)
        if channel is None:
            logger.error(f"承認申請チャンネル「{config.REQUEST_CHANNEL_NAME}」が見つかりません ({guild.name})")
            return

        embed = build_request_embed(member)
        view = VerificationView(member.id)
        try:
            msg = await channel.send(embed=embed, view=view)
        except discord.Forbidden:
            logger.error(f"承認申請チャンネルへの送信権限がありません ({guild.name})")
            return

        await storage.add_pending(msg.id, member.id, guild.id)
        logger.info(f"認証申請投稿: {member} ({guild.name})")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        message_id = await storage.find_pending_by_user(member.guild.id, member.id)
        if message_id is None:
            return

        channel = discord.utils.get(member.guild.text_channels, name=config.REQUEST_CHANNEL_NAME)
        if channel is not None:
            try:
                msg = await channel.fetch_message(message_id)
                await msg.edit(
                    embed=discord.Embed(
                        title="⚠️ ユーザーが退出しました",
                        description=f"{member} は承認前にサーバーを退出しました。",
                        color=discord.Color.greyple(),
                    ),
                    view=None,
                )
            except discord.NotFound:
                pass

        await storage.remove_pending(message_id)

    @commands.command(name="verify_diag")
    @commands.has_permissions(administrator=True)
    async def verify_diag(self, ctx: commands.Context):
        """認証Botの設定状況を診断する"""
        guild = ctx.guild
        pending_role = discord.utils.get(guild.roles, name=config.PENDING_ROLE_NAME)
        member_role = discord.utils.get(guild.roles, name=config.MEMBER_ROLE_NAME)
        channel = discord.utils.get(guild.text_channels, name=config.REQUEST_CHANNEL_NAME)
        bot_member = guild.me

        def ok(cond: bool) -> str:
            return "✅" if cond else "❌"

        embed = discord.Embed(title="認証Bot 診断結果", color=discord.Color.blurple())
        embed.add_field(
            name=f"{ok(pending_role is not None)} 認証待ちロール ({config.PENDING_ROLE_NAME})",
            value=pending_role.mention if pending_role else "見つかりません",
            inline=False,
        )
        embed.add_field(
            name=f"{ok(member_role is not None)} メンバーロール ({config.MEMBER_ROLE_NAME})",
            value=member_role.mention if member_role else "見つかりません",
            inline=False,
        )
        embed.add_field(
            name=f"{ok(channel is not None)} 承認申請チャンネル ({config.REQUEST_CHANNEL_NAME})",
            value=channel.mention if channel else "見つかりません",
            inline=False,
        )
        embed.add_field(
            name=f"{ok(bot_member.guild_permissions.manage_roles)} ロール管理権限",
            value=str(bot_member.guild_permissions.manage_roles),
            inline=True,
        )
        embed.add_field(
            name=f"{ok(bot_member.guild_permissions.kick_members)} Kick権限",
            value=str(bot_member.guild_permissions.kick_members),
            inline=True,
        )
        if pending_role and bot_member.top_role <= pending_role:
            embed.add_field(
                name="⚠️ ロール階層",
                value=f"Botのロール({bot_member.top_role.mention})が「{config.PENDING_ROLE_NAME}」以下です。上に配置してください。",
                inline=False,
            )
        if member_role and bot_member.top_role <= member_role:
            embed.add_field(
                name="⚠️ ロール階層",
                value=f"Botのロール({bot_member.top_role.mention})が「{config.MEMBER_ROLE_NAME}」以下です。上に配置してください。",
                inline=False,
            )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Verification(bot))
