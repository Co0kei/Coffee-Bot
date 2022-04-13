import logging
import sys
import textwrap
import traceback
from io import BytesIO
from typing import Optional, Union

import discord
from discord.app_commands import ContextMenu, Command
from discord.ext import commands

from constants import *

log = logging.getLogger(__name__)


class ErrorCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        bot.tree.on_error = self.on_command_tree_error
        bot.on_error = self.on_error

    async def cog_load(self) -> None:
        self.error_hook = discord.Webhook.from_url(ERROR_HOOK_URL, session=self.bot.session)

    async def on_error(self, event, *args, **kwargs):

        (exc_type, exc, tb) = sys.exc_info()
        exc = ''.join(traceback.format_exception(exc_type, exc, tb, chain=True))

        log.error(f'Error in event \'{event}\':\n{exc}')

        # Silence command errors that somehow get bubbled up far enough here
        if isinstance(exc, commands.CommandInvokeError):
            return

        e = discord.Embed(title='Event Error', colour=0xa32952)
        e.add_field(name='Event', value=event)

        # e.description = f'```py\n{trace}\n```'
        e.timestamp = discord.utils.utcnow()

        args_str = ['```py']
        for index, arg in enumerate(args):
            args_str.append(f'[{index}]: {arg!r}')
        args_str.append('```')
        e.add_field(name='Args', value='\n'.join(args_str), inline=False)

        content = exc
        buffer = BytesIO(content.encode('utf-8'))
        file = discord.File(fp=buffer, filename='error.txt')

        if sys.platform != DEV_PLATFORM:
            await self.error_hook.send(embed=e, file=file)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.NotOwner):
            await ctx.send('Sorry. This command can\'t be used by you.')
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:,.2f} secs.")

        elif isinstance(error, commands.CommandInvokeError):
            original = error.original

            if not isinstance(original, discord.HTTPException):

                exc = ''.join(traceback.format_exception(type(error), error, error.__traceback__, chain=True))

                log.error(f'Error in command \'{ctx.command.qualified_name}\': {original}\n{exc}')

                await ctx.message.reply("Sorry, an unexpected error has occured. I will notify the bot developer now.")

                e = discord.Embed(title='Command Error', colour=0xcc3366)
                e.add_field(name='Name', value=ctx.command.qualified_name)
                e.add_field(name='Author', value=f'{ctx.author} (ID: {ctx.author.id})')

                fmt = f'Channel: {ctx.channel} (ID: {ctx.channel.id})'
                if ctx.guild:
                    fmt = f'{fmt}\nGuild: {ctx.guild} (ID: {ctx.guild.id})'

                e.add_field(name='Location', value=fmt, inline=False)
                e.add_field(name='Content', value=textwrap.shorten(ctx.message.content, width=512))

                # e.description = f'```py\n{exc}\n```'
                e.timestamp = discord.utils.utcnow()

                content = exc
                buffer = BytesIO(content.encode('utf-8'))
                file = discord.File(fp=buffer, filename='error.txt')

                if sys.platform != DEV_PLATFORM:
                    await self.error_hook.send(embed=e, file=file)
            else:
                log.error(original)

    async def on_command_tree_error(self, interaction: discord.Interaction,
                                    command: Optional[Union[Command, ContextMenu]],
                                    error: discord.app_commands.AppCommandError):

        if command is None:
            log.error(f'Command Tree Error: {traceback.format_exc()}')
            return

        exc = ''.join(traceback.format_exception(type(error), error, error.__traceback__, chain=True))

        log.error(f'Error in Command Tree command \'{command.name}\':\n{exc}')

        if interaction.response.is_done():
            try:
                await interaction.user.send(f"Sorry, an unexpected error has occured in command '{command.name}'. I will notify the bot developer now.")
            except:
                pass
        else:
            await interaction.response.send_message("Sorry, an unexpected error has occured. I will notify the bot developer now.", ephemeral=True)

        e = discord.Embed(title='Command Tree Error', colour=0xcc3366)
        e.add_field(name='Command Name', value=command.name)
        e.add_field(name='Author', value=f'{interaction.user} (ID: {interaction.user.id})')

        fmt = f'Channel: {interaction.channel} (ID: {interaction.channel.id})'
        if interaction.guild:
            fmt = f'{fmt}\nGuild: {interaction.guild} (ID: {interaction.guild.id})'

        e.add_field(name='Location', value=fmt, inline=False)

        command_type = command.to_dict()["type"]
        if command_type == 1:  # slash command

            if "options" in interaction.data:
                params = interaction.data["options"]
                e.add_field(name='Command Parameters', value=params)

            application_command_type = "Slash"

        elif command_type == 2:  # user context menu
            application_command_type = "User Context Menu"
        elif command_type == 3:  # message context menu
            application_command_type = "Message Context Menu"
        else:  # idk
            application_command_type = "Unknown type"

        e.add_field(name='Command Type', value=application_command_type)

        # e.description = f'```py\n{exc}\n```'
        e.timestamp = discord.utils.utcnow()

        content = exc
        buffer = BytesIO(content.encode('utf-8'))
        file = discord.File(fp=buffer, filename='error.txt')

        if sys.platform != DEV_PLATFORM:
            await self.error_hook.send(embed=e, file=file)


async def setup(bot):
    await bot.add_cog(ErrorCog(bot))
