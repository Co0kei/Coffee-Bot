import logging
from datetime import timedelta

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class ChatFilterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def handleChat(self, message: discord.Message) -> bool:
        content_lower = message.content.lower()

        settingsCog = self.bot.get_cog("SettingsCommand")

        chat_filter = settingsCog.getChatFilter(message.guild)

        delete = False
        for word in chat_filter:
            if word in content_lower:
                delete = True
                break
        
        if delete:
            try:
                await message.delete()
            except discord.NotFound:  # another bot deleted it
                pass
            try:
                await message.author.timeout(timedelta(seconds=3))
            except discord.Forbidden as e:  # no permission
                pass
            # log it
            modLogChannel = settingsCog.getModLogChannel(message.guild)
            if modLogChannel:
                embed = discord.Embed()
                embed.set_author(name="Chat Filter", icon_url=message.author.display_avatar.url)
                embed.colour = discord.Colour(0x2F3136)
                embedDescription = f'{message.author.mention} ({message.author}) tried to send a message with filtered words.\n\n'
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

    async def handleChatEdit(self, before, after) -> bool:
        content_lower = after.content.lower()

        settingsCog = self.bot.get_cog("SettingsCommand")

        chat_filter = settingsCog.getChatFilter(after.guild)

        delete = False
        for word in chat_filter:
            if word in content_lower:
                delete = True
                break

        if delete:
            try:
                await after.delete()
            except discord.NotFound:  # another bot deleted it
                pass
            try:
                await after.author.timeout(timedelta(seconds=3))
            except discord.Forbidden as e:  # no permission
                pass
            # log it
            modLogChannel = settingsCog.getModLogChannel(after.guild)
            if modLogChannel:
                embed = discord.Embed()
                embed.set_author(name="Chat Filter", icon_url=after.author.display_avatar.url)
                embed.colour = discord.Colour(0x2F3136)
                embedDescription = f'{after.author.mention} ({after.author}) tried to edit a filtered word into their message.\n\n'
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
    await bot.add_cog(ChatFilterCog(bot))
