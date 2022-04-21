import logging
import re
from datetime import timedelta

import discord
from discord import NotFound
from discord.ext import commands

log = logging.getLogger(__name__)


class LinkFilterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def handleLink(self, message: discord.Message) -> bool:
        content_lower = message.content.lower()

        settingsCog = self.bot.get_cog("SettingsCommand")

        whitelisted_links = settingsCog.getWhitelistedLinks(message.guild)

        for link in whitelisted_links:
            content_lower = content_lower.replace(link, "")

        if re.search("(https?://(?:www\\.|(?!www))[^\\s.]+\\.[^\\s]{2,}|www\\.[^\\s]+\\.[^\\s]{2,})", content_lower):
            try:
                await message.delete()
            except NotFound:  # another bot deleted it
                pass
            try:
                await message.author.timeout(timedelta(seconds=3))
            except discord.Forbidden as e:  # no permission
                pass
            # log it
            modLogChannel = settingsCog.getModLogChannel(message.guild)
            if modLogChannel:
                embed = discord.Embed()
                embed.set_author(name="Link Posted", icon_url=message.author.display_avatar.url)
                embed.colour = discord.Colour(0x2F3136)
                embedDescription = f'{message.author.mention} ({message.author}) tried to post a link.\n\n'
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
                await modLogChannel.send(embed=embed)
            return True
        else:
            return False

    async def handleLinkEdit(self, before, after) -> bool:
        content_lower = after.content.lower()

        settingsCog = self.bot.get_cog("SettingsCommand")

        whitelisted_links = settingsCog.getWhitelistedLinks(after.guild)

        for link in whitelisted_links:
            content_lower = content_lower.replace(link, "")

        if re.search("(https?://(?:www\\.|(?!www))[^\\s.]+\\.[^\\s]{2,}|www\\.[^\\s]+\\.[^\\s]{2,})", content_lower):
            try:
                await after.delete()
            except NotFound:  # another bot deleted it
                pass
            try:
                await after.author.timeout(timedelta(seconds=3))
            except discord.Forbidden as e:  # no permission
                pass
            # log it
            modLogChannel = settingsCog.getModLogChannel(after.guild)
            if modLogChannel:
                embed = discord.Embed()
                embed.set_author(name="Link Posted", icon_url=after.author.display_avatar.url)
                embed.colour = discord.Colour(0x2F3136)
                embedDescription = f'{after.author.mention} ({after.author}) tried to edit a link into a message.\n\n'
                embedDescription += f'**Message Before:**\n`{before.clean_content[0:1000]}`\n\n'  # only display first 1000 chars
                embedDescription += f'**Message After:**\n`{after.clean_content[0:1000]}`'  # only display first 1000 chars
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
                await modLogChannel.send(embed=embed)
            return True
        else:
            return False


async def setup(bot):
    await bot.add_cog(LinkFilterCog(bot))
