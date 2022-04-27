import logging
import re
from datetime import timedelta
from io import BytesIO

import discord
from discord import NotFound
from discord.ext import commands

log = logging.getLogger(__name__)


class InviteFilterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def handleInvite(self, message: discord.Message) -> bool:
        content_lower = message.content.lower()

        if re.search("(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?", content_lower) or re.search("https?://dsc.gg/", content_lower):
            try:
                await message.delete()
            except NotFound:  # another bot deleted it
                pass
            try:
                await message.author.timeout(timedelta(seconds=3))
            except discord.Forbidden as e:  # no permission
                pass

            # log it
            settingsCog = self.bot.get_cog("SettingsCommand")
            modLogChannel = settingsCog.getModLogChannel(message.guild)
            if modLogChannel:
                embed = discord.Embed()
                embed.set_author(name="Discord Invite Posted", icon_url=message.author.display_avatar.url)
                embed.colour = discord.Colour(0x2F3136)
                embedDescription = f'{message.author.mention} ({message.author}) tried to post a Discord server invite.\n\n'

                msg_content = message.clean_content.replace("`", "")

                embedDescription += f'**Message\'s Info:**\n' \
                                    f'Message ID: `{message.id}`\n' \
                                    f'Channel: {message.channel.mention}\n' \
                                    f'Time: {discord.utils.format_dt(message.created_at, "F")} ({discord.utils.format_dt(message.created_at, "R")})\n' \
                                    f'Attachments: `{len(message.attachments)}`'
                embedDescription += f'\n\n**Message Content:**\n`{msg_content}`'

                if len(message.attachments) != 0:
                    attachement1 = message.attachments[0]
                    if attachement1.content_type.startswith("image"):
                        embed.set_image(url=attachement1.url)
                        embedDescription += f"\n\n**Message Image:**"
                embed.description = embedDescription

                file = None
                content = None
                if len(embed.description) > 4096 or len(embed) > 6000:
                    # attach as a file
                    embed = None
                    content = "**Server Invite Filter!**"
                    fileContent = f'{message.author} tried to post a Discord server invite.\n\n' \
                                  f'Message ID: {message.id}\n' \
                                  f'Channel: #{message.channel}\n' \
                                  f'Time (UTC): {message.created_at.strftime("%Y-%m-%d %H:%M-%S")}\n' \
                                  f'Attachments: {len(message.attachments)}\n\n' \
                                  f'Message Content:\n{message.clean_content}'
                    buffer = BytesIO(fileContent.encode('utf-8'))
                    file = discord.File(fp=buffer, filename='invite_filter.txt')

                await modLogChannel.send(content=content, embed=embed, file=file)
            return True
        else:
            return False

    async def handleInviteEdit(self, before, after) -> bool:
        content_lower = after.content.lower()

        if re.search("(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?", content_lower) or re.search("https?://dsc.gg/", content_lower):
            try:
                await after.delete()
            except NotFound:  # another bot deleted it
                pass
            try:
                await after.author.timeout(timedelta(seconds=3))
            except discord.Forbidden as e:  # no permission
                pass

            # log it
            settingsCog = self.bot.get_cog("SettingsCommand")
            modLogChannel = settingsCog.getModLogChannel(after.guild)
            if modLogChannel:
                embed = discord.Embed()
                embed.set_author(name="Discord Invite Posted", icon_url=after.author.display_avatar.url)
                embed.colour = discord.Colour(0x2F3136)
                embedDescription = f'{after.author.mention} ({after.author}) tried to edit a Discord server invite into a message.\n\n'

                embedDescription += f'**Message\'s Info:**\n' \
                                    f'Message ID: `{after.id}`\n' \
                                    f'Channel: {after.channel.mention}\n' \
                                    f'Time: {discord.utils.format_dt(after.created_at, "F")} ({discord.utils.format_dt(after.created_at, "R")})\n' \
                                    f'Attachments: `{len(after.attachments)}`'

                content_before = before.clean_content.replace("`", "")
                content_after = after.clean_content.replace("`", "")

                embedDescription += f'\n\n**Message Before:**\n`{content_before}`'
                embedDescription += f'\n\n**Message After:**\n`{content_after}`'

                if len(after.attachments) != 0:
                    attachement1 = after.attachments[0]
                    if attachement1.content_type.startswith("image"):
                        embed.set_image(url=attachement1.url)
                        embedDescription += f"\n\n**Message Image:**"
                embed.description = embedDescription

                file = None
                content = None
                if len(embed.description) > 4096 or len(embed) > 6000:
                    # attach as a file
                    embed = None
                    content = "**Server Invite Filter!**"
                    fileContent = f'{after.author} tried to edit a Discord server invite into a message.\n\n' \
                                  f'Message ID: {after.id}\n' \
                                  f'Channel: #{after.channel}\n' \
                                  f'Time (UTC): {after.created_at.strftime("%Y-%m-%d %H:%M-%S")}\n' \
                                  f'Attachments: {len(after.attachments)}' \
                                  f'\n\nMessage Content Before:\n{before.clean_content}' \
                                  f'\n\nMessage Content After:\n{after.clean_content}'
                    buffer = BytesIO(fileContent.encode('utf-8'))
                    file = discord.File(fp=buffer, filename='invite_filter.txt')

                await modLogChannel.send(content=content, embed=embed, file=file)
            return True
        else:
            return False


async def setup(bot):
    await bot.add_cog(InviteFilterCog(bot))
