import logging
import sys

import discord
from discord.ext import commands

from constants import JOIN_LEAVE_HOOK_URL, DEV_PLATFORM

log = logging.getLogger(__name__)


class JoinLeaveCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self) -> None:
        self.join_leave_hook = discord.Webhook.from_url(JOIN_LEAVE_HOOK_URL, session=self.bot.session)

    async def cog_unload(self) -> None:
        pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        log.info(f'I have been invited to {guild.name} ({guild.id}) which has {len(guild.members):,} members.')
        e = discord.Embed(colour=0x53dda4, title='New Guild')  # green colour

        if guild.me.guild_permissions.view_audit_log:
            async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.bot_add):
                inviter = entry.user
                target = entry.target

                if target.id == self.bot.user.id:
                    try:
                        await inviter.send(f'Hey! :wave:\n'
                                           f'Thanks for inviting me to **{guild.name}**! To get started, check out the **/help** and **/settings** command!\n'
                                           f'For a detailed list of commands, features and examples, consider visiting my Top.gg page: '
                                           f'https://top.gg/bot/950765718209720360', suppress_embeds=True)
                    except discord.Forbidden:
                        pass
                    e.description = f"Invited by `{inviter}`!"
                    break

        await self.send_guild_stats(e, guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        log.info(f'I have been removed from {guild.name} ({guild.id}) which has {len(guild.members):,} members.')
        e = discord.Embed(colour=0xdd5f53, title='Left Guild')  # red colour
        await self.send_guild_stats(e, guild)

    async def send_guild_stats(self, e: discord.Embed, guild: discord.Guild):
        e.add_field(name='Name', value=guild.name)
        e.add_field(name='ID', value=guild.id)
        e.add_field(name='Shard ID', value=guild.shard_id or 'N/A')
        e.add_field(name='Owner', value=f'{guild.owner} (ID: {guild.owner_id})')
        bots = sum(m.bot for m in guild.members)
        total = guild.member_count
        e.add_field(name='Members', value=f"{total:,}")
        e.add_field(name='Bots', value=f'{bots:,} ({bots / total:.2%})')

        if guild.icon:
            e.set_thumbnail(url=guild.icon.url)

        if guild.me:
            e.timestamp = guild.me.joined_at

        await self.join_leave_hook.send(embed=e)

        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'{len(self.bot.guilds)} guilds'))

        if sys.platform != DEV_PLATFORM:
            try:
                await self.bot.topggpy.post_guild_count(shard_count=self.bot.shard_count)
                log.info(f"Posted to top.gg: server count ({self.bot.topggpy.guild_count}), shard count ({self.bot.shard_count})")

            except Exception as e:
                log.error(f"Failed to post to top.gg: {e}")


async def setup(bot):
    await bot.add_cog(JoinLeaveCog(bot))
