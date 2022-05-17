import asyncio
import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class MemberUpdateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        settingsCommand = self.bot.get_cog("SettingsCommand")

        if settingsCommand.getRoleUpdateChannel(role.guild):
            await self.bot.get_cog("AuditLogCog").handleRoleDelete(role)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.guild is None:
            return

        if not isinstance(after, discord.Member):
            return

        settingsCommand = self.bot.get_cog("SettingsCommand")

        if before.roles != after.roles and settingsCommand.getRoleUpdateChannel(after.guild):

            roles_gained = []
            for role in after.roles:
                if role not in before.roles:
                    roles_gained.append(role)

            roles_lost = []
            for role in before.roles:
                if role not in after.roles:
                    roles_lost.append(role)

            # # TEST
            # __role = after.guild.get_role(878653340865683457)
            # _role = after.guild.get_role(872828547562082314)
            # if __role in roles_gained:
            #     await after.add_roles(_role)
            # if __role in roles_lost:
            #     await after.remove_roles(_role)

            await asyncio.sleep(0.2)  # give role delete event time
            for role in roles_lost:  # if a role is deleted, dont send members losing role individually but in one embed / file
                if str(role.id) in self.bot.delete_role_cache:
                    self.bot.delete_role_cache[str(role.id)].append(after.id)
                    return

            await self.bot.get_cog("AuditLogCog").handleRoleUpdate(before, after, roles_gained, roles_lost)

        elif before.nick != after.nick and settingsCommand.getNickUpdateChannel(after.guild):
            await self.bot.get_cog("AuditLogCog").handleNickUpdate(before, after)

        elif before.is_timed_out() != after.is_timed_out() and settingsCommand.getMemberTimeoutChannel(after.guild):
            await self.bot.get_cog("AuditLogCog").handleTimeout(before, after)


async def setup(bot):
    if not hasattr(bot, 'delete_role_cache'):
        bot.delete_role_cache = {}
    await bot.add_cog(MemberUpdateCog(bot))
