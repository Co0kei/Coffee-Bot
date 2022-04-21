import asyncio
import datetime
import io
import logging
import re
import typing

import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)


class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self._batch_lock = asyncio.Lock()
        self._data_batch = []

        self.bulk_insert_loop.start()

    async def cog_unload(self) -> None:
        self.bulk_insert_loop.stop()

    @tasks.loop(seconds=10.0)
    async def bulk_insert_loop(self):
        async with self._batch_lock:
            await self.bulk_insert()

    async def bulk_insert(self):
        query = """INSERT INTO commands (guild_id, channel_id, author_id, used, prefix, command, type)
                   SELECT x.guild, x.channel, x.author, x.used, x.prefix, x.command, x.type
                   FROM jsonb_to_recordset($1::jsonb) AS
                   x(guild BIGINT, channel BIGINT, author BIGINT, used TIMESTAMP, prefix TEXT, command TEXT, type INT)
                """

        if self._data_batch:
            await self.bot.pool.execute(query, self._data_batch)
            total = len(self._data_batch)
            if total >= 1:
                log.info('Registered %s commands to the database.', total)
            self._data_batch.clear()

    async def register_command(self, command_name, guild_id, channel_id, author_id, time_used, prefix, command_type):
        """ Saves slash commands / context menu usage """

        async with self._batch_lock:
            self._data_batch.append({
                'guild': guild_id,
                'channel': channel_id,
                'author': author_id,
                'used': time_used,
                'prefix': prefix,
                'command': command_name,
                'type': command_type,
            })

    def censor_object(self, obj):
        self.bot.blacklist = []

        if not isinstance(obj, str) and obj.id in self.bot.blacklist:
            return '[censored]'
        return self.censor_invite(obj)

    _INVITE_REGEX = re.compile(r'(?:https?:\/\/)?discord(?:\.gg|\.com|app\.com\/invite)?\/[A-Za-z0-9]+')

    def censor_invite(self, obj, *, _regex=_INVITE_REGEX):
        return _regex.sub('[censored-invite]', str(obj))

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

        embed.description = f'{count[0]} commands used.'
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
        await ctx.send(embed=embed)

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

        embed.description = f'{count[0]} commands used.'
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
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    # @commands.cooldown(1, 30.0, type=commands.BucketType.member)
    async def stats(self, ctx, *, member: discord.Member = None):
        """Tells you command usage stats for the current guild or a member."""

        async with ctx.typing():
            if member is None:
                await self.show_guild_stats(ctx)
            else:
                await self.show_member_stats(ctx, member)

    @commands.command()
    @commands.is_owner()
    async def stats_global(self, ctx):
        """Global all time command statistics."""

        query = "SELECT COUNT(*) FROM commands;"
        total = await self.bot.pool.fetchrow(query)

        e = discord.Embed(title='Command Stats', colour=discord.Colour.blurple())
        e.description = f'{total[0]} commands used.'

        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{SPORTS MEDAL}',
            '\N{SPORTS MEDAL}'
        )

        query = """SELECT command, COUNT(*) AS "uses"
                   FROM commands
                   GROUP BY command
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await self.bot.pool.fetch(query)
        value = '\n'.join(f'{lookup[index]}: {command} ({uses} uses)' for (index, (command, uses)) in enumerate(records))
        e.add_field(name='Top Commands', value=value, inline=False)

        query = """SELECT guild_id, COUNT(*) AS "uses"
                   FROM commands
                   GROUP BY guild_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await self.bot.pool.fetch(query)
        value = []
        for (index, (guild_id, uses)) in enumerate(records):
            if guild_id is None:
                guild = 'Private Message'
            else:
                guild = self.censor_object(self.bot.get_guild(guild_id) or f'<Unknown {guild_id}>')

            emoji = lookup[index]
            value.append(f'{emoji}: {guild} ({uses} uses)')

        e.add_field(name='Top Guilds', value='\n'.join(value), inline=False)

        query = """SELECT author_id, COUNT(*) AS "uses"
                   FROM commands
                   GROUP BY author_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await self.bot.pool.fetch(query)
        value = []
        for (index, (author_id, uses)) in enumerate(records):
            user = self.censor_object(self.bot.get_user(author_id) or f'<Unknown {author_id}>')
            emoji = lookup[index]
            value.append(f'{emoji}: {user} ({uses} uses)')

        e.add_field(name='Top Users', value='\n'.join(value), inline=False)
        await ctx.send(embed=e)

    @commands.command()
    @commands.is_owner()
    async def stats_today(self, ctx):
        """Global command statistics for the day."""

        query = "SELECT type, COUNT(*) FROM commands WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day') GROUP BY type;"
        total = await self.bot.pool.fetch(query)
        slash = 0
        context = 0
        message = 0
        for type, count in total:
            if type == 1:
                slash += count
            elif type == 2 or type == 3:
                context += count
            else:
                message += count

        e = discord.Embed(title='Last 24 Hour Command Stats', colour=discord.Colour.blurple())
        e.description = f'{slash + context + message} commands used today. ' \
                        f'({slash} slash, {context} context menus, {message} prefix commands)'

        lookup = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{SPORTS MEDAL}',
            '\N{SPORTS MEDAL}'
        )

        query = """SELECT command, COUNT(*) AS "uses"
                   FROM commands
                   WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY command
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await self.bot.pool.fetch(query)
        value = '\n'.join(f'{lookup[index]}: {command} ({uses} uses)' for (index, (command, uses)) in enumerate(records))
        e.add_field(name='Top Commands', value=value, inline=False)

        query = """SELECT guild_id, COUNT(*) AS "uses"
                   FROM commands
                   WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY guild_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await self.bot.pool.fetch(query)
        value = []
        for (index, (guild_id, uses)) in enumerate(records):
            if guild_id is None:
                guild = 'Private Message'
            else:
                guild = self.censor_object(self.bot.get_guild(guild_id) or f'<Unknown {guild_id}>')
            emoji = lookup[index]
            value.append(f'{emoji}: {guild} ({uses} uses)')

        e.add_field(name='Top Guilds', value='\n'.join(value), inline=False)

        query = """SELECT author_id, COUNT(*) AS "uses"
                   FROM commands
                   WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY author_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

        records = await self.bot.pool.fetch(query)
        value = []
        for (index, (author_id, uses)) in enumerate(records):
            user = self.censor_object(self.bot.get_user(author_id) or f'<Unknown {author_id}>')
            emoji = lookup[index]
            value.append(f'{emoji}: {user} ({uses} uses)')

        e.add_field(name='Top Users', value='\n'.join(value), inline=False)
        await ctx.send(embed=e)

    class TabularData:
        def __init__(self):
            self._widths = []
            self._columns = []
            self._rows = []

        def set_columns(self, columns):
            self._columns = columns
            self._widths = [len(c) + 2 for c in columns]

        def add_row(self, row):
            rows = [str(r) for r in row]
            self._rows.append(rows)
            for index, element in enumerate(rows):
                width = len(element) + 2
                if width > self._widths[index]:
                    self._widths[index] = width

        def add_rows(self, rows):
            for row in rows:
                self.add_row(row)

        def render(self):
            """Renders a table in rST format.
            Example:
            +-------+-----+
            | Name  | Age |
            +-------+-----+
            | Alice | 24  |
            |  Bob  | 19  |
            +-------+-----+
            """

            sep = '+'.join('-' * w for w in self._widths)
            sep = f'+{sep}+'

            to_draw = [sep]

            def get_entry(d):
                elem = '|'.join(f'{e:^{self._widths[i]}}' for i, e in enumerate(d))
                return f'|{elem}|'

            to_draw.append(get_entry(self._columns))
            to_draw.append(sep)

            for row in self._rows:
                to_draw.append(get_entry(row))

            to_draw.append(sep)
            return '\n'.join(to_draw)

    async def tabulate_query(self, ctx, query, *args):
        records = await self.bot.pool.fetch(query, *args)

        if len(records) == 0:
            return await ctx.send('No results found.')

        headers = list(records[0].keys())

        table = self.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in records)
        render = table.render()

        fmt = f'```\n{render}\n```'
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode('utf-8'))
            await ctx.send('Too many results...', file=discord.File(fp, 'results.txt'))
        else:
            await ctx.send(fmt)

    @commands.command()
    @commands.is_owner()
    async def command_history(self, ctx):
        """ Global Command history."""

        query = """SELECT
                        command,
                        to_char(used, 'Mon DD HH12:MI:SS AM') AS "invoked",
                        author_id,
                        guild_id
                   FROM commands
                   ORDER BY used DESC
                   LIMIT 15;
                """
        await self.tabulate_query(ctx, query)

    @commands.command()
    @commands.is_owner()
    async def command_history_for(self, ctx, days: typing.Optional[int] = 7, *, command: str):
        """Command history for a command."""

        query = """SELECT *
                   FROM (
                       SELECT guild_id,
                              SUM(1) AS "total"
                       FROM commands
                       WHERE command=$1
                       AND used > (CURRENT_TIMESTAMP - $2::interval)
                       GROUP BY guild_id
                   ) AS t
                   ORDER BY "total" DESC
                   LIMIT 30;
                """

        await self.tabulate_query(ctx, query, command, datetime.timedelta(days=days))

    @commands.command()
    @commands.is_owner()
    async def command_history_guild(self, ctx, guild_id: int):
        """Command history for a guild."""

        query = """SELECT
                        command,
                        channel_id,
                        author_id,
                        used
                   FROM commands
                   WHERE guild_id=$1
                   ORDER BY used DESC
                   LIMIT 15;
                """
        await self.tabulate_query(ctx, query, guild_id)

    @commands.command()
    @commands.is_owner()
    async def command_history_user(self, ctx, user_id: int):
        """Command history for a user."""

        query = """SELECT
                        command,
                        guild_id,
                        used
                   FROM commands
                   WHERE author_id=$1
                   ORDER BY used DESC
                   LIMIT 20;
                """
        await self.tabulate_query(ctx, query, user_id)

    @commands.command()
    @commands.is_owner()
    async def command_history_log(self, ctx, days=7):
        """Command history log for the last N days."""

        query = """SELECT command, COUNT(*)
                   FROM commands
                   WHERE used > (CURRENT_TIMESTAMP - $1::interval)
                   GROUP BY command
                   ORDER BY 2 DESC
                """

        all_commands = {
            c.qualified_name: 0
            for c in self.bot.walk_commands()
        }

        records = await self.bot.pool.fetch(query, datetime.timedelta(days=days))
        for name, uses in records:
            if name in all_commands:
                all_commands[name] = uses

        as_data = sorted(all_commands.items(), key=lambda t: t[1], reverse=True)
        table = self.TabularData()
        table.set_columns(['Command', 'Uses'])
        table.add_rows(tup for tup in as_data)
        render = table.render()

        embed = discord.Embed(title='Summary', colour=discord.Colour.green())
        embed.set_footer(text='Since').timestamp = discord.utils.utcnow() - datetime.timedelta(days=days)

        top_ten = '\n'.join(f'{command}: {uses}' for command, uses in records[:10])
        bottom_ten = '\n'.join(f'{command}: {uses}' for command, uses in records[-10:])
        embed.add_field(name='Top 10', value=top_ten)
        embed.add_field(name='Bottom 10', value=bottom_ten)

        unused = ', '.join(name for name, uses in as_data if uses == 0)
        if len(unused) > 1024:
            unused = 'Way too many...'

        embed.add_field(name='Unused', value=unused, inline=False)

        await ctx.send(embed=embed, file=discord.File(io.BytesIO(render.encode()), filename='full_results.txt'))

    # @commands.command()
    # @commands.is_owner()
    # async def command_history_cog(self, ctx, days: typing.Optional[int] = 7, *, cog: str = None):
    #     """Command history for a cog or grouped by a cog."""
    #
    #     interval = datetime.timedelta(days=days)
    #     if cog is not None:
    #         cog = self.bot.get_cog(cog)
    #         if cog is None:
    #             return await ctx.send(f'Unknown cog: {cog}')
    #
    #         query = """SELECT *
    #                    FROM (
    #                        SELECT command,
    #                               SUM(1) AS "total"
    #                        FROM commands
    #                        WHERE command = any($1::text[])
    #                        AND used > (CURRENT_TIMESTAMP - $2::interval)
    #                        GROUP BY command
    #                    ) AS t
    #                    ORDER BY "total" DESC
    #                    LIMIT 30;
    #                 """
    #         command_names = [c.qualified_name for c in cog.walk_commands()]
    #         #command_names += [t.name for t in self.bot.tree.walk_commands()]
    #         return await self.tabulate_query(ctx, query, command_names, interval)
    #
    #     # A more manual query with a manual grouper.
    #     query = """SELECT *
    #                FROM (
    #                    SELECT command,
    #                           SUM(1) AS "total"
    #                    FROM commands
    #                    WHERE used > (CURRENT_TIMESTAMP - $1::interval)
    #                    GROUP BY command
    #                ) AS t;
    #             """
    #
    #     class Count:
    #         __slots__ = ('success', 'failed', 'total')
    #
    #         def __init__(self):
    #             self.success = 0
    #             self.failed = 0
    #             self.total = 0
    #
    #         def add(self, record):
    #             # self.success += record['success']
    #             # self.failed += record['failed']
    #             self.total += record['total']
    #
    #     data = defaultdict(Count)
    #     records = await self.bot.pool.fetch(query, interval)
    #     for record in records:
    #         command = self.bot.get_command(record['command'])
    #         if command is None or command.cog is None:
    #             data['No Cog'].add(record)
    #         else:
    #             data[command.cog.qualified_name].add(record)
    #
    #     table = self.TabularData()
    #     table.set_columns(['Cog', 'Total'])
    #     data = sorted([
    #         (cog, e.total)
    #         for cog, e in data.items()
    #     ], key=lambda t: t[-1], reverse=True)
    #
    #     table.add_rows(data)
    #     render = table.render()
    #     if len(render) > 2000:
    #         await ctx.send(file=discord.File(io.BytesIO(render.encode()), filename='full_results.txt'))
    #     else:
    #         await ctx.send(f'```\n{render}\n```')


async def setup(bot):
    await bot.add_cog(StatsCog(bot))
