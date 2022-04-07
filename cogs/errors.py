import logging
import sys
import traceback
from typing import Optional, Union

import discord
from discord.app_commands import ContextMenu, Command
from discord.ext import commands

from constants import ERROR_CHANNEL_ID

log = logging.getLogger(__name__)


class ErrorCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        bot.tree.on_error = self.on_command_tree_error

    @commands.Cog.listener()
    async def on_error(self, event):
        log.warning(f'Error in event {event}: {traceback.format_exc()}')
        await self.log_error(f'Error in event {event}: {traceback.format_exc()}')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.NotOwner):
            await ctx.send('Sorry. This command can\'t be used by you.')
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:,.2f} secs.")

        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                log.warning(f'Error in {ctx.command.qualified_name}:')
                traceback.print_tb(original.__traceback__)
                log.warning(f'{original.__class__.__name__}: {original}')
                await self.log_error(f'Error in {ctx.command.qualified_name}: {original.__traceback__}')

    async def on_command_tree_error(self, interaction: discord.Interaction,
                                    command: Optional[Union[Command, ContextMenu]],
                                    error: discord.app_commands.AppCommandError):
        log.warning(f'Error in {command}:')
        traceback.print_tb(error.__traceback__)
        log.warning(f'{error.__class__.__name__}: {error}')
        await self.log_error(f'Error in {command}: {error.__traceback__}')

    async def log_error(self, message):
        if sys.platform != "win32":  # Only log errors in productions. There will be many in testing...
            await self.bot.get_channel(ERROR_CHANNEL_ID).send(message)


async def setup(bot):
    await bot.add_cog(ErrorCog(bot))
