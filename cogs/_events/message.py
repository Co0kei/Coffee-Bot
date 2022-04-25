import logging
import re

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class MessageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if re.fullmatch(rf"<@!?{self.bot.user.id}>", message.content):
            return await message.channel.send(f"Hi! Use `/help` to learn more about me!")

        if message.guild is None:
            return

        if not isinstance(message.author, discord.Member):
            return

        if message.author.guild_permissions.manage_messages:  # members with this permission bypass all filters / checks
            return

        settingsCommand = self.bot.get_cog("SettingsCommand")

        if settingsCommand.getChatFilter(message.guild):
            message_deleted = await self.bot.get_cog("ChatFilterCog").handleChat(message)
            if message_deleted: return

        if settingsCommand.isInviteFilterEnabled(message.guild):
            message_deleted = await self.bot.get_cog("InviteFilterCog").handleInvite(message)
            if message_deleted: return

        if settingsCommand.isLinkFilterEnabled(message.guild):
            message_deleted = await self.bot.get_cog("LinkFilterCog").handleLink(message)
            if message_deleted: return

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.author.bot:
            return

        if before.content == after.content:
            return

        if after.guild is None:
            return

        if not isinstance(after.author, discord.Member):
            return

        settingsCommand = self.bot.get_cog("SettingsCommand")

        if settingsCommand.getMsgEditChannel(after.guild):  # do message edit log here
            await self.bot.get_cog("AuditLogCog").handleEdit(before, after)

        if after.author.guild_permissions.manage_messages:  # members with this permission bypass all filters / checks
            return

        if settingsCommand.getChatFilter(after.guild):
            message_deleted = await self.bot.get_cog("ChatFilterCog").handleChatEdit(before, after)
            if message_deleted: return

        if settingsCommand.isInviteFilterEnabled(after.guild):
            message_deleted = await self.bot.get_cog("InviteFilterCog").handleInviteEdit(before, after)
            if message_deleted: return

        if settingsCommand.isLinkFilterEnabled(after.guild):
            message_deleted = await self.bot.get_cog("LinkFilterCog").handleLinkEdit(before, after)
            if message_deleted: return

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if not payload.guild_id or payload.cached_message:  # Cached messages are handled by the non raw event
            return

        settingsCommand = self.bot.get_cog("SettingsCommand")
        guild = self.bot.get_guild(payload.guild_id)
        if settingsCommand.getMsgEditChannel(guild):
            await self.bot.get_cog("AuditLogCog").handleRawEdit(payload, guild)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return

        settingsCommand = self.bot.get_cog("SettingsCommand")
        if settingsCommand.getMsgDeleteChannel(message.guild) or settingsCommand.getModMsgDeleteChannel(message.guild):
            await self.bot.get_cog("AuditLogCog").handleDelete(message)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if not payload.guild_id or payload.cached_message:  # Cached messages are handled by the non raw event
            return

        settingsCommand = self.bot.get_cog("SettingsCommand")
        guild = self.bot.get_guild(payload.guild_id)
        if settingsCommand.getMsgDeleteChannel(guild) or settingsCommand.getModMsgDeleteChannel(guild):
            await self.bot.get_cog("AuditLogCog").handleRawDelete(payload, guild)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        if not payload.guild_id:
            return

        settingsCommand = self.bot.get_cog("SettingsCommand")
        guild = self.bot.get_guild(payload.guild_id)
        if settingsCommand.getModMsgDeleteChannel(guild):
            await self.bot.get_cog("AuditLogCog").handleRawBulkDelete(payload, guild)


async def setup(bot):
    if not hasattr(bot, 'delete_log_cache'):
        bot.delete_log_cache = {}
    await bot.add_cog(MessageCog(bot))
