import logging
import re
import sys
import traceback
from datetime import timedelta

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def getModLogChannel(self, guild: discord.Guild) -> discord.TextChannel:
        mod_log_channel = None
        if str(guild.id) in self.bot.guild_settings:
            if "mod_log_channel" in self.bot.guild_settings[str(guild.id)]:
                mod_log_channel = guild.get_channel(self.bot.guild_settings[str(guild.id)]["mod_log_channel"])
        return mod_log_channel

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.guild is None:
            return

        if message.author.guild_permissions.administrator:
            return

        content_lower = message.content.lower()

        # whitelisted_links = ["tenor.com"]
        # for link in whitelisted_links:
        #     content_lower = content_lower.replace(link, "")
        # print(f'removed allolwed links {content_lower}')
        # if re.search("(https?://(?:www\\.|(?!www))[^\\s.]+\\.[^\\s]{2,}|www\\.[^\\s]+\\.[^\\s]{2,})", content_lower):
        #     await message.delete()
        #     print("found a link")

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

        if after.author.guild_permissions.administrator:
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

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        log.info(f'I have been invited to {guild.name} ({guild.id}) which has {len(guild.members)} members.')

        embed = discord.Embed(title='Joined Server', colour=discord.Colour.green())
        embed.add_field(name='Guild Info', value=f'{guild.name} (ID: {guild.id})', inline=False)
        embed.add_field(name='Guild Members', value=f'{len(guild.members)}', inline=False)
        embed.timestamp = discord.utils.utcnow()

        await self.bot.hook.send(embed=embed)

        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=f'{len(self.bot.guilds)} guilds'))

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        log.info(f'I have been removed from {guild.name} ({guild.id}) which has {len(guild.members)} members.')

        embed = discord.Embed(title='Left Server', colour=discord.Colour.dark_red())
        embed.add_field(name='Guild Info', value=f'{guild.name} (ID: {guild.id})', inline=False)
        embed.add_field(name='Guild Members', value=f'{len(guild.members)}', inline=False)
        embed.timestamp = discord.utils.utcnow()

        await self.bot.hook.send(embed=embed)

        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=f'{len(self.bot.guilds)} guilds'))

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:  # slash commands or context menus

            command_type = interaction.data['type']
            command_name = interaction.data['name']
            user = f'{interaction.user} (ID: {interaction.user.id})'

            if interaction.guild is None:
                guild = None
            else:
                guild = f'{interaction.guild.name} (ID: {interaction.guild.id})'

            self.bot.commands_used += 1

            if command_type == 1:  # slash command
                application_command_type = "Slash"

            elif command_type == 2:  # user context menu
                application_command_type = "User Context Menu"

            elif command_type == 3:  # message context menu
                application_command_type = "Message Context Menu"

            else:  # idk
                application_command_type = "Unknown type"

            log.info(
                f'{application_command_type} command \'{command_name}\' ran by {user}. Guild: {guild}. Commands used: {self.bot.commands_used}!')

            embed = discord.Embed(colour=discord.Colour.blurple())
            embed.set_author(name=f'Command ran by {user}', icon_url=interaction.user.display_avatar.url)
            embed.add_field(name='Type', value=f'{application_command_type}', inline=False)
            embed.add_field(name='Command Name', value=f'{command_name}', inline=False)
            embed.add_field(name='Guild', value=f'{guild}', inline=False)
            embed.timestamp = discord.utils.utcnow()
            embed.set_footer(text=f"Total commands ran: {self.bot.commands_used}")

            if interaction.user.id != self.bot.owner_id:
                await self.bot.hook.send(embed=embed)

    @commands.Cog.listener()
    async def on_autopost_success(self):
        log.info(f"Posted server count ({self.bot.topggpy.guild_count}), shard count ({self.bot.shard_count})")

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        """An event that is called whenever someone votes for the bot on Top.gg."""

        discordID = data["user"]
        user = self.bot.get_user(int(discordID))
        if user is not None:
            try:
                await user.send("Thank you very much for voting for me! :hugging:")
            except discord.HTTPException:
                pass

        if user is None:
            await self.bot.hook.send(f'Discord ID: {discordID} just voted for me!')
        else:
            await self.bot.hook.send(f'{user.mention} just voted for me!')

        if data["type"] == "test":
            return self.bot.dispatch("dbl_test", data)

        print(f"Received a vote:\n{data}")

    @commands.Cog.listener()
    async def on_dbl_test(self, data):
        """An event that is called whenever someone tests the webhook system for your bot on Top.gg."""
        print(f"Received a test vote:\n{data}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.NotOwner):
            await ctx.author.send('Sorry. This command can\'t be used by you.')

        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                print(f'Error in {ctx.command.qualified_name}:', file=sys.stderr)
                traceback.print_tb(original.__traceback__)
                print(f'{original.__class__.__name__}: {original}', file=sys.stderr)


async def setup(bot):
    await bot.add_cog(EventCog(bot))
