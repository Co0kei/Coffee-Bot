import inspect
import logging
import os

import discord
import unicodedata
from discord.ext import commands

from constants import *

log = logging.getLogger(__name__)


class MetaCommands(commands.Cog):
    """Commands for utilities related to Discord or the Bot itself."""

    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.command()
    async def hello(self, ctx):
        """Displays my intro message."""
        await ctx.reply(f'Hello! I\'m a robot! {self.bot.get_guild(DEV_SERVER_ID).get_member(self.bot.owner_id)} made me.')

    @commands.command()
    async def charinfo(self, ctx, *, characters: str = None):
        """Shows you information about a number of characters. Only up to 25 characters at a time."""

        if not characters:
            return await ctx.send("Please enter some chars.")
        
        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            return f'`\\U{digit:>08}`: {name} - {c} \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>'

        msg = '\n'.join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.send('Output too long to display.')
        await ctx.reply(msg)

    @commands.command()
    async def source(self, ctx, *, command: str = None):
        """Displays my full source code or for a specific command."""
        source_url = 'https://github.com/Co0kei/Coffee-Bot'
        branch = 'master'
        if command is None:
            return await ctx.send(source_url)

        command = command.lower()

        obj = self.bot.get_command(command) or self.bot.tree.get_command(command)
        if obj is None:
            return await ctx.send('Could not find command.')

        # since we found the command we're looking for, presumably anyway, let's
        # try to access the code itself
        src = obj.callback.__code__
        filename = src.co_filename

        lines, firstlineno = inspect.getsourcelines(src)
        location = os.path.relpath(filename).replace('\\', '/')
        final_url = f'<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>'
        await ctx.reply(final_url)

    @commands.command(aliases=['invite'])
    async def join(self, ctx):
        """Joins a server."""
        await ctx.reply(f'<{discord.utils.oauth_url(self.bot.user.id, permissions=discord.Permissions(8))}>')


async def setup(bot):
    await bot.add_cog(MetaCommands(bot))
