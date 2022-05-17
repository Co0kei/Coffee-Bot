import datetime
import inspect
import logging
import os

import bedwarspro
import discord
import unicodedata
from bedwarspro import BedwarsProException
from discord.ext import commands

from constants import *

log = logging.getLogger(__name__)


class MetaCommands(commands.Cog):

    def __init__(self, bot) -> None:
        self.bot = bot

    async def cog_load(self):
        self.BW_PRO = bedwarspro.Client(BW_PRO_API_KEY)

    async def cog_unload(self):
        await self.BW_PRO.close()

    @commands.command(description="View player data for the bedwars pro Minecraft server", usage="<player>")
    @commands.cooldown(5, 10.0, type=commands.BucketType.member)
    async def bwpro(self, ctx, player=None):
        if player is None:
            return await ctx.message.reply("Please enter a player name or UUID!")

        async with self.BW_PRO:
            try:
                player = await self.BW_PRO.player(player)

                embed = discord.Embed()
                embed.title = f'[{player.rank}] {player.name}'
                embed.colour = discord.Colour.blurple()
                embed.add_field(name="First Login", value=discord.utils.format_dt(player.first_login))
                await ctx.message.reply(embed=embed)

            except BedwarsProException as error:
                await ctx.send(f'Error: {error}.')

    @commands.command(description="Displays a lil message")
    @commands.cooldown(5, 60.0, type=commands.BucketType.member)
    async def hello(self, ctx):
        owner = await self.bot.get_or_fetch_user(int(self.bot.owner_id))
        await ctx.reply(f'Hello! I\'m a robot! {owner} made me.')

    @commands.command(description="Shows you information about a number of characters", usage="<char>")
    async def charinfo(self, ctx, *, characters: str = None):
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

    @commands.command(description="Displays my full source code for for a specific command", usage="<command>")
    @commands.cooldown(1, 2.0, type=commands.BucketType.member)
    async def source(self, ctx, *, command: str = None):
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

    @commands.command(description="Sends an invite link")
    @commands.cooldown(1, 2.0, type=commands.BucketType.member)
    async def invite(self, ctx):
        await ctx.reply(f'<{discord.utils.oauth_url(self.bot.user.id, permissions=discord.Permissions(8))}>')

    # command stats
    async def show_guild_stats(self, ctx):
        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{SPORTS MEDAL}',
            '\N{SPORTS MEDAL}'
        )

        embed = discord.Embed(title='Server Command Stats', colour=discord.Colour.blurple())

        # total command uses
        query = "SELECT COUNT(*), MIN(used) FROM commands WHERE guild_id=$1;"
        count = await self.bot.pool.fetchrow(query, ctx.guild.id)

        embed.description = f'{count[0]} commands used in {ctx.guild}.'
        if count[1]:
            timestamp = count[1].replace(tzinfo=datetime.timezone.utc)
        else:
            timestamp = discord.utils.utcnow()

        embed.set_footer(text='Tracking command usage since').timestamp = timestamp

        query = """SELECT command,
                          COUNT(*) as "uses"
                   FROM commands
                   WHERE guild_id=$1
                   GROUP BY command
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await self.bot.pool.fetch(query, ctx.guild.id)

        value = '\n'.join(f'{lookup[index]}: {command} ({uses} uses)'
                          for (index, (command, uses)) in enumerate(records)) or 'No Commands'

        embed.add_field(name='Top Commands', value=value, inline=True)

        query = """SELECT command,
                          COUNT(*) as "uses"
                   FROM commands
                   WHERE guild_id=$1
                   AND used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY command
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await self.bot.pool.fetch(query, ctx.guild.id)

        value = '\n'.join(f'{lookup[index]}: {command} ({uses} uses)'
                          for (index, (command, uses)) in enumerate(records)) or 'No Commands.'
        embed.add_field(name='Top Commands Today', value=value, inline=True)
        embed.add_field(name='\u200b', value='\u200b', inline=True)

        query = """SELECT author_id,
                          COUNT(*) AS "uses"
                   FROM commands
                   WHERE guild_id=$1
                   GROUP BY author_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await self.bot.pool.fetch(query, ctx.guild.id)

        value = '\n'.join(f'{lookup[index]}: <@!{author_id}> ({uses} bot uses)'
                          for (index, (author_id, uses)) in enumerate(records)) or 'No bot users.'

        embed.add_field(name='Top Command Users', value=value, inline=True)

        query = """SELECT author_id,
                          COUNT(*) AS "uses"
                   FROM commands
                   WHERE guild_id=$1
                   AND used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY author_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await self.bot.pool.fetch(query, ctx.guild.id)

        value = '\n'.join(f'{lookup[index]}: <@!{author_id}> ({uses} bot uses)'
                          for (index, (author_id, uses)) in enumerate(records)) or 'No command users.'

        embed.add_field(name='Top Command Users Today', value=value, inline=True)
        await ctx.reply(embed=embed)

    async def show_member_stats(self, ctx, member):
        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{SPORTS MEDAL}',
            '\N{SPORTS MEDAL}'
        )

        embed = discord.Embed(title='Command Stats', colour=member.colour)
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)

        # total command uses
        query = "SELECT COUNT(*), MIN(used) FROM commands WHERE guild_id=$1 AND author_id=$2;"
        count = await self.bot.pool.fetchrow(query, ctx.guild.id, member.id)

        embed.description = f'{count[0]} commands used by {member} in {member.guild}.'
        if count[1]:
            timestamp = count[1].replace(tzinfo=datetime.timezone.utc)
        else:
            timestamp = discord.utils.utcnow()

        embed.set_footer(text='First command used').timestamp = timestamp

        query = """SELECT command,
                          COUNT(*) as "uses"
                   FROM commands
                   WHERE guild_id=$1 AND author_id=$2
                   GROUP BY command
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await self.bot.pool.fetch(query, ctx.guild.id, member.id)

        value = '\n'.join(f'{lookup[index]}: {command} ({uses} uses)'
                          for (index, (command, uses)) in enumerate(records)) or 'No Commands'

        embed.add_field(name='Most Used Commands', value=value, inline=False)

        query = """SELECT command,
                          COUNT(*) as "uses"
                   FROM commands
                   WHERE guild_id=$1
                   AND author_id=$2
                   AND used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY command
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await self.bot.pool.fetch(query, ctx.guild.id, member.id)

        value = '\n'.join(f'{lookup[index]}: {command} ({uses} uses)'
                          for (index, (command, uses)) in enumerate(records)) or 'No Commands'

        embed.add_field(name='Most Used Commands Today', value=value, inline=False)
        await ctx.reply(embed=embed)

    @commands.command(description="Tells you command usage stats for the current guild or a member", usage="<member>")
    @commands.cooldown(5, 30.0, type=commands.BucketType.member)
    # @commands.dynamic_cooldown(custom_cooldown, commands.BucketType.member)
    @commands.guild_only()
    @commands.is_owner()
    async def stats(self, ctx, *, member: discord.Member = None):
        async with ctx.typing():
            if member is None:
                await self.show_guild_stats(ctx)
            else:
                await self.show_member_stats(ctx, member)


async def setup(bot):
    await bot.add_cog(MetaCommands(bot))
