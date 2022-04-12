import logging
import re
from datetime import timedelta

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class InviteFilterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def getModLogChannel(self, guild: discord.Guild) -> discord.TextChannel:
        mod_log_channel = None
        if str(guild.id) in self.bot.guild_settings:
            if "mod_log_channel" in self.bot.guild_settings[str(guild.id)]:
                mod_log_channel = guild.get_channel(self.bot.guild_settings[str(guild.id)]["mod_log_channel"])
        return mod_log_channel

        # if re.fullmatch(rf"<@!?{self.bot.user.id}>", message.content):
        #     return await message.channel.send(f"Hi!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.guild is None:
            return

        if not isinstance(message.author, discord.Member):
            return

        if message.author.guild_permissions.manage_messages:
            return

        content_lower = message.content.lower()

        if self.bot.get_cog("SettingsCommand").isInviteFilterEnabled(message.guild):
            if re.search("(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?", content_lower) or re.search(
                    "https?://dsc.gg/", content_lower):
                await message.delete()
                try:
                    await message.author.timeout(timedelta(seconds=10))
                except discord.Forbidden as e:  # no permission
                    pass

                # log it
                if self.getModLogChannel(message.guild) is not None:
                    # create an embed
                    embed = discord.Embed()
                    embed.set_author(name="Discord Invite Posted", icon_url=message.author.display_avatar.url)
                    embed.colour = discord.Colour(0x2F3136)
                    embedDescription = f'{message.author.mention} ({message.author}) tried to post a Discord server invite.\n\n'
                    embedDescription += f'**Message Content:**\n`{message.clean_content[0:2000]}`'  # only display first 2000 chars
                    embedDescription += f'\n\n**Message\'s Info:**\n' \
                                        f'Message ID: `{message.id}`\n' \
                                        f'Channel: {message.channel.mention}\n' \
                                        f'Time: {discord.utils.format_dt(message.created_at, "F")} ({discord.utils.format_dt(message.created_at, "R")})\n' \
                                        f'Attachments: `{len(message.attachments)}`'
                    if len(message.attachments) != 0:
                        attachement1 = message.attachments[0]
                        if attachement1.content_type.startswith("image"):
                            embed.set_image(url=attachement1.url)
                            embedDescription += f"\n\n**Message Image:**"
                    embed.description = embedDescription

                    await self.getModLogChannel(message.guild).send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.author.bot:
            return

        if after.guild is None:
            return

        if not isinstance(after.author, discord.Member):
            return

        if after.author.guild_permissions.manage_messages:
            return

        content_lower = after.content.lower()

        if self.bot.get_cog("SettingsCommand").isInviteFilterEnabled(after.guild):
            if re.search("(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?", content_lower) or re.search(
                    "https?://dsc.gg/", content_lower):
                await after.delete()
                try:
                    await after.author.timeout(timedelta(seconds=10))
                except discord.Forbidden as e:  # no permission
                    pass

                # log it
                if self.getModLogChannel(after.guild) is not None:
                    # create an embed
                    embed = discord.Embed()
                    embed.set_author(name="Discord Invite Posted", icon_url=after.author.display_avatar.url)
                    embed.colour = discord.Colour(0x2F3136)
                    embedDescription = f'{after.author.mention} ({after.author}) tried to edit a Discord server invite into a message.\n\n'
                    embedDescription += f'**Message Before:**\n`{before.clean_content[0:1000]}`\n\n'  # only display first 2000 chars
                    embedDescription += f'**Message After:**\n`{after.clean_content[0:1000]}`'  # only display first 2000 chars

                    embedDescription += f'\n\n**Message\'s Info:**\n' \
                                        f'Message ID: `{after.id}`\n' \
                                        f'Channel: {after.channel.mention}\n' \
                                        f'Time: {discord.utils.format_dt(after.created_at, "F")} ({discord.utils.format_dt(after.created_at, "R")})\n' \
                                        f'Attachments: `{len(after.attachments)}`'
                    if len(after.attachments) != 0:
                        attachement1 = after.attachments[0]
                        if attachement1.content_type.startswith("image"):
                            embed.set_image(url=attachement1.url)
                            embedDescription += f"\n\n**Message Image:**"
                    embed.description = embedDescription

                    await self.getModLogChannel(after.guild).send(embed=embed)


async def setup(bot):
    await bot.add_cog(InviteFilterCog(bot))
