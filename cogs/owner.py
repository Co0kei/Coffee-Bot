import asyncio
import datetime
import gc
import io
import json
import linecache
import logging
import os
import re
import shutil
import sys
import textwrap
import time
import traceback
import tracemalloc
import typing
from contextlib import redirect_stdout
from pathlib import Path

import asyncpg
import discord
import psutil
import pygit2
from discord.ext import commands

from constants import *

log = logging.getLogger(__name__)


class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.lock = asyncio.Lock()

    async def cog_check(self, ctx) -> bool:
        return await self.bot.is_owner(ctx.author)

    async def cog_load(self) -> None:
        await self.connect_to_postgreSQL()

    async def cog_unload(self) -> None:
        await self.bot.pool.close()  # close connection pool

    async def connect_to_postgreSQL(self):
        if sys.platform == DEV_PLATFORM:
            url = DEV_POSTGRE_URL
        else:
            url = POSTGRE_URL

        kwargs = {
            'command_timeout': 60,
            'max_size': 20,
            'min_size': 20,
        }

        def _encode_jsonb(value):
            return json.dumps(value)

        def _decode_jsonb(value):
            return json.loads(value)

        async def init(con):
            await con.set_type_codec('jsonb', schema='pg_catalog', encoder=_encode_jsonb, decoder=_decode_jsonb, format='text')

        try:
            self.bot.pool = await asyncpg.create_pool(url, init=init, **kwargs)
            log.info("Connected to PostgreSQL")
        except Exception as e:
            log.exception('Could not set up PostgreSQL. Exiting.', e)

    @commands.command(description="Shows all owner help commands")
    async def owner(self, ctx):
        owner_commands = ""
        for command in self.get_commands():
            cmd = f'**{ctx.prefix}{command.name}'
            if command.usage:
                cmd += f' {command.usage}'
            cmd += "**"
            if command.aliases:
                cmd += f" - {command.aliases}"
            cmd += f" - {command.description}\n"
            owner_commands += cmd

        embed = discord.Embed(title="Owner Commands", description=owner_commands, colour=discord.Colour.blurple())
        await ctx.message.reply(embed=embed)

    @commands.command(description="Shows all cogs")
    async def cogs(self, ctx):
        """ Command to list all cogs and whether they are loaded or not """
        embed = discord.Embed(colour=discord.Colour.blurple())

        loaded_extensions = [str(e) for e in self.bot.extensions]

        cogs_data = ""
        for file in Path('cogs').glob('**/*.py'):
            *tree, _ = file.parts
            cog_path = f"{'.'.join(tree)}.{file.stem}"
            if cog_path in loaded_extensions:
                cogs_data += f"<:online:821068743987429438> {cog_path}\n"
            else:
                cogs_data += f"<:offline:821068938036379679> {cog_path}\n"

        embed.description = f"**Extensions**\n{cogs_data}"
        embed.add_field(name="**Cogs**", value=f"{str([str(e) for e in self.bot.cogs])}", inline=False)

        await ctx.send(embed=embed)

    @commands.command(description="Loads a cog")
    async def load(self, ctx, *, module=None):
        """ Load a specific cog """
        if module is None:
            return await ctx.send(f"\U0000274c Enter a cog to load!")

        module = module.lower()

        found = False
        for file in Path('cogs').glob('**/*.py'):
            *tree, _ = file.parts
            if file.stem == module:
                found = True
                break

        if not found:
            return await ctx.send("\U0000274c This cog could not be found!")
        try:
            await self.bot.load_extension(f"{'.'.join(tree)}.{file.stem}")
            await ctx.send(f"\U00002705 Cog {module} loaded successfully!")

        except commands.ExtensionAlreadyLoaded:
            await ctx.send("\U0000274c This cog is already loaded!")

        except Exception as e:
            traceback.print_exc()
            await ctx.send(f"\U0000274c {e}")

    @commands.command(description="Unloads a cog")
    async def unload(self, ctx, *, module=None):
        """ Unload a specific cog """
        if module is None:
            return await ctx.send(f"\U0000274c Enter a cog to unload!")

        module = module.lower()

        found = False
        for file in Path('cogs').glob('**/*.py'):
            *tree, _ = file.parts
            if file.stem == module:
                found = True
                break

        if not found:
            return await ctx.send("\U0000274c This cog could not be found!")
        try:
            await self.bot.unload_extension(f"{'.'.join(tree)}.{file.stem}")
            await ctx.send(f"\U00002705 Cog {module} unloaded successfully!")

        except commands.ExtensionNotLoaded:
            await ctx.send("\U0000274c This cog is already unloaded!")

        except Exception as e:
            traceback.print_exc()
            await ctx.send(f"\U0000274c {e}")

    @commands.command(description="Reloads a cog", aliases=["r"])
    async def reload(self, ctx, *, module=None):
        """" Reload a specific cog """

        if not hasattr(self.bot, '_last_module'):
            self.bot._last_module = None

        module = module or self.bot._last_module

        if module is None:
            return await ctx.send(f"\U0000274c Enter a cog to reload!")

        module = module.lower()

        found = False
        for file in Path('cogs').glob('**/*.py'):
            *tree, _ = file.parts
            if file.stem == module:
                found = True
                break

        if not found:
            return await ctx.send("\U0000274c This cog could not be found!")
        try:
            await self.bot.reload_extension(f"{'.'.join(tree)}.{file.stem}")
            await ctx.send(f"\U00002705 Successfully reloaded {module}!")
            self.bot._last_module = file.stem

        except commands.ExtensionNotLoaded:  # if not loaded then load
            await self.bot.load_extension(f"{'.'.join(tree)}.{file.stem}")
            await ctx.send(f"\U00002705 Successfully loaded {module}!")

        except Exception as e:
            traceback.print_exc()
            await ctx.send(f"\U0000274c {e}")

    @commands.command(description="Reloads all cogs", aliases=["rall"])
    async def reloadall(self, ctx):
        loaded_extensions = [e for e in self.bot.extensions]

        # UNLOAD ALL EXTENSIONS
        for extension in loaded_extensions:
            try:
                await self.bot.unload_extension(extension)
            except:  # if file got deleted ignore
                pass

        # if an extensions file got deleted then just unload the cog
        loaded_cogs = [e for e in self.bot.cogs]
        for cog in loaded_cogs:
            await self.bot.remove_cog(cog)

        msg = "**Unloaded All Cogs**\n"
        msg += "Extensions: " + str([str(e) for e in self.bot.extensions]) + "\n"
        msg += "Cogs:" + str([str(e) for e in self.bot.cogs]) + "\n"

        # LOAD ALL EXTENSIONS
        msg += "\n**Loaded All Cogs:**\n"
        for file in Path('cogs').glob('**/*.py'):
            *tree, _ = file.parts
            try:
                await self.bot.load_extension(f"{'.'.join(tree)}.{file.stem}")
                msg += f"\U00002705 Successfully loaded {file.stem}!\n"

            except Exception as e:
                log.warning(f'Failed to reload extension {file}.')
                msg += f"\U0000274c Failed to load {file.stem} with reason: {e}\n"
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)

        # if ctx is not None:
        await ctx.send(msg)

    @commands.is_owner()
    @commands.command(description="Saves stat and vote data to disk")
    async def dump(self, ctx):
        """ Save data to disk """

        def _dump():
            with open('stats.json', 'w', encoding='utf-8') as f:
                json.dump(self.bot.stat_data, f, ensure_ascii=False, indent=4)
                f.close()

            # # save guild settings
            # with open('guild_settings.json', 'w', encoding='utf-8') as f:
            #     json.dump(self.bot.guild_settings, f, ensure_ascii=False, indent=4)
            #     f.close()
            # # save vote data
            # with open('votes.json', 'w', encoding='utf-8') as f:
            #     json.dump(self.bot.vote_data, f, ensure_ascii=False, indent=4)
            #     f.close()

        async with self.lock:
            await self.bot.loop.run_in_executor(None, _dump)

            if ctx is not None:
                await ctx.message.reply("Data saved")

    @commands.is_owner()
    @commands.command(aliases=["loadmemory"], description="Reloads the data in memory by reading from disk and postgreSQL")
    async def refreshmemory(self, ctx):
        """ Reload data from disk"""

        def _load():
            with open('stats.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.bot.stat_data = data
                f.close()

            # with open('guild_settings.json', 'r', encoding='utf-8') as f:
            #     data = json.load(f)
            #     self.bot.guild_settings = data  # load guild settings
            #     f.close()
            # with open('votes.json', 'r', encoding='utf-8') as f:
            #     data = json.load(f)
            #     self.bot.vote_data = data  # load vote data
            #     f.close()

        await self.load_guilds()

        async with self.lock:
            await self.bot.loop.run_in_executor(None, _load)

            if ctx is not None:
                await ctx.message.reply("Data reloaded")

    async def load_guilds(self):
        """ Loads all guild data into memory from postgreSQL"""
        query = "SELECT * FROM guilds;"

        # async with self.bot.pool.acquire() as conn:
        #     async with conn.transaction():

        guild_data = await self.bot.pool.fetch(query)

        guild_settings = {}

        for guild in guild_data:
            guild_id = guild["guild_id"]
            guild_settings[str(guild_id)] = {}

            for column, value in guild.items():
                if column == "id" or column == "guild_id":
                    continue
                elif value is not None:
                    guild_settings[str(guild_id)][column] = value

        self.bot.guild_settings = guild_settings
        # log.info(guild_settings)

    # @commands.is_owner()
    # @commands.command(description="Shows 1000 most recent votes for the bot")
    # async def votes(self, ctx):
    #     users = await self.bot.topggpy.get_bot_votes()
    #
    #     peoplethatvoted = []
    #
    #     for user in users:
    #         username = user["username"]
    #         peoplethatvoted.append(username)
    #
    #     await ctx.send(f'Bot Vote History:\n' + "\n".join(peoplethatvoted))

    @commands.is_owner()
    @commands.command(name="backup", description="Backups files")
    async def backup(self, ctx):

        def _backup():
            files = ['stats.json']

            shutil.rmtree("backups")
            os.mkdir('backups')

            for f in files:
                shutil.copy(f, 'backups')

        async with self.lock:
            await self.bot.loop.run_in_executor(None, _backup)

            if ctx is not None:
                await ctx.reply("Done")

    @commands.is_owner()
    @commands.command(description="Simulate a player voting. Used for testing purposes", usage="[user_id] [is_weekend]")
    async def simvote(self, ctx, id=None, is_weekend=False):  # add optional weekend param
        id = id or ctx.author.id

        # {'user': 'id', 'type': 'upvote', 'query': {}, 'bot': 950765718209720360, 'is_weekend': False}
        example_data = {'user': id, 'type': 'upvote', 'query': {}, 'bot': 950765718209720360,
                        'is_weekend': is_weekend}

        await self.bot.get_cog("VoteCog").on_dbl_vote(example_data)
        await ctx.message.reply("Vote simulated!\n" + str(example_data))

    @commands.is_owner()
    @commands.command(description="Syncs the command tree for the dev server")
    async def syncdev(self, ctx):
        await ctx.send("Processing")

        self.bot.tree.copy_global_to(guild=discord.Object(id=DEV_SERVER_ID))
        result = await self.bot.tree.sync(guild=discord.Object(id=DEV_SERVER_ID))

        msg = ""
        for val in result:
            msg += f"{val.name}\n"

        await ctx.message.reply("Synced dev server interactions:\n" + str(msg))

    @commands.is_owner()
    @commands.command(description="Removes guild specific command tree commands from the dev server")
    async def cleardev(self, ctx):
        await ctx.send("Processing")

        for command in await self.bot.tree.fetch_commands(guild=discord.Object(id=DEV_SERVER_ID)):
            self.bot.tree.remove_command(command.name, guild=discord.Object(id=DEV_SERVER_ID), type=command.type)

        result = await self.bot.tree.sync(guild=discord.Object(id=DEV_SERVER_ID))
        await ctx.message.reply("Dev server local interactions removed:\n" + str(result))

    @commands.is_owner()
    @commands.command(description="Syncs the global command tree; This takes one hour to propogate")
    async def syncglobal(self, ctx):
        await ctx.send("Processing global sync")
        result = await self.bot.tree.sync()

        msg = ""
        for val in result:
            msg += f"{val.name}\n"

        await ctx.message.reply("Global interaction sync complete:\n" + str(msg))

    @commands.is_owner()
    @commands.command(name="stop", aliases=["close"], description="Gracefully stops the bot")
    async def _stop(self, ctx):
        # Alert me if anyone is expecting an alert in next 2 hours
        msg = ""
        current_time: int = int(time.time())
        for discord_id, last_vote in self.bot.stat_data["vote_reminders"].items():
            difference = (current_time - last_vote)
            if difference > 36000:  # num of seconds in 10 hours
                msg += f'`+` Discord ID {discord_id} is expecting a vote reminder <t:{last_vote + 43200}:R>\n'

        if msg == "":
            msg = "None"

        embed = discord.Embed(title="Vote reminders in the next 2 hours", description=msg[:4000], color=discord.Colour.dark_theme())
        value = await ctx.prompt('Do you want to continue?', embed=embed)
        if not value:  # stop if None or False returned.
            return

        cmd = self.bot.get_command("dump")
        await cmd(ctx)

        await self.bot.close()

    @commands.is_owner()
    @commands.command(aliases=["clonerepo"], description="Pulls commits and optionally files from GitHub. Include true for files.", usage="[pull_files]")
    async def pullgit(self, ctx, py=False):
        """Clone commit history. Optionally pull files from git. """
        if sys.platform == DEV_PLATFORM:
            return await ctx.send("Don't need to.")

        def _pull():
            try:
                # remove files
                shutil.rmtree(".git")
                if py:
                    shutil.rmtree("cogs")
            except:
                pass

            # clone
            pygit2.clone_repository("https://github.com/Co0kei/Coffee-Bot", ".git", bare=not py)

            msg = ""
            # move py files
            if py:
                shutil.move(".git/cogs", "cogs")
                shutil.move(".git/bot.py", "bot.py")
                msg += "Updated files. Don't forget to reload all cogs now!"
            return msg

        async with self.lock:
            msg = await self.bot.loop.run_in_executor(None, _pull)

            if ctx is not None:
                await ctx.send(f'Pulled commits.\n{msg}')

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @commands.is_owner()
    @commands.command(name="eval", description="Evaluates code", usage="<code>")
    async def _eval(self, ctx, *, body: str = None):
        """Evaluates code"""

        if not body:
            return await ctx.send("Please enter some code.")

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }

        env.update(globals())
        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.is_owner()
    @commands.command(aliases=["health"], description="Various bot health monitoring tools")
    async def bothealth(self, ctx):
        """Various bot health monitoring tools."""

        HEALTHY = discord.Colour(value=0x43B581)
        UNHEALTHY = discord.Colour(value=0xF04947)
        WARNING = discord.Colour(value=0xF09E47)
        total_warnings = 0

        embed = discord.Embed(title='Bot Health Report', colour=HEALTHY)

        # Check the connection pool health.
        pool = self.bot.pool
        total_waiting = len(pool._queue._getters)
        current_generation = pool._generation

        description = [
            f'Total `Pool.acquire` Waiters: {total_waiting}',
            f'Current Pool Generation: {current_generation}',
            f'Connections In Use: {len(pool._holders) - pool._queue.qsize()}'
        ]

        questionable_connections = 0
        connection_value = []
        for index, holder in enumerate(pool._holders, start=1):
            generation = holder._generation
            in_use = holder._in_use is not None
            is_closed = holder._con is None or holder._con.is_closed()
            display = f'gen={holder._generation} in_use={in_use} closed={is_closed}'
            questionable_connections += any((in_use, generation != current_generation))
            connection_value.append(f'<Holder i={index} {display}>')

        joined_value = '\n'.join(connection_value)
        embed.add_field(name='Connections', value=f'```py\n{joined_value}\n```', inline=False)

        description.append(f'Questionable Connections: {questionable_connections}')
        total_warnings += questionable_connections

        try:
            task_retriever = asyncio.Task.all_tasks
        except AttributeError:
            task_retriever = asyncio.all_tasks

        all_tasks = task_retriever(loop=self.bot.loop)

        event_tasks = [
            t for t in all_tasks
            if 'Client._run_event' in repr(t) and not t.done()
        ]  # most likelys its on_message waiting

        cogs_directory = os.path.dirname(__file__)
        tasks_directory = os.path.join('discord', 'ext', 'tasks', '__init__.py')
        inner_tasks = [
            t for t in all_tasks
            if cogs_directory in repr(t) or tasks_directory in repr(t)
        ]

        bad_inner_tasks = ", ".join(hex(id(t)) for t in inner_tasks if t.done() and t._exception is not None)
        total_warnings += bool(bad_inner_tasks)
        embed.add_field(name='Inner Tasks', value=f'Total: {len(inner_tasks)}\nFailed: {bad_inner_tasks or "None"}')
        embed.add_field(name='Events Waiting', value=f'Total: {len(event_tasks)}', inline=False)

        command_waiters = len(self.bot.get_cog('StatsCog')._data_batch)
        is_locked = self.bot.get_cog('StatsCog')._batch_lock.locked()
        description.append(f'Commands Waiting: {command_waiters}, Batch Locked: {is_locked}')

        memory_usage = self.bot.get_cog('AboutCommand').process.memory_full_info().uss / 1024 ** 2
        cpu_usage = self.bot.get_cog('AboutCommand').process.cpu_percent() / psutil.cpu_count()
        embed.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU', inline=False)

        global_rate_limit = self.bot.is_ws_ratelimited()  # not self.bot.http._global_over.is_set()
        description.append(f'Global Rate Limit: {global_rate_limit}')


        description.append(f'User cache size: {len(self.bot.users)}')
        description.append(f'Message cache size: {len(self.bot.cached_messages)}')
        description.append(f'Msg delete cache size: {len(self.bot.delete_log_cache)}')
        description.append(f'Role delete cache size: {len(self.bot.delete_role_cache)}')

        description.append(f"updater Task running: {self.bot.get_cog('TaskCog').updater.is_running()}")
        description.append(f"vote_reminder Task running: {self.bot.get_cog('TaskCog').vote_reminder.is_running()}")


        if command_waiters >= 8:
            total_warnings += 1
            embed.colour = WARNING

        if global_rate_limit or total_warnings >= 9:
            embed.colour = UNHEALTHY

        embed.set_footer(text=f'{total_warnings} warning(s)')
        embed.description = '\n'.join(description)
        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command(aliases=['socket'], description="Shows gateway events")
    async def socketstats(self, ctx):
        delta = discord.utils.utcnow() - self.bot.uptime
        minutes = delta.total_seconds() / 60
        total = sum(self.bot.socket_stats.values())
        cpm = total / minutes
        await ctx.send(f'{total} socket events observed ({cpm:.2f}/minute)\n'
                       f' - {self.bot.socket_stats["MESSAGE_CREATE"] / minutes:.2f} messages/minute\n'
                       f' - {self.bot.socket_stats["MESSAGE_UPDATE"] / minutes:.2f} message updates/minute\n'
                       f' - {self.bot.socket_stats["MESSAGE_DELETE"] / minutes:.2f} message deletes/minute\n'
                        f' - {self.bot.socket_stats["MESSAGE_DELETE_BULK"] / minutes:.2f} bulk deletes/minute\n'
                       f' - {self.bot.socket_stats["GUILD_MEMBER_UPDATE"] / minutes:.2f} guild member updates/minute\n'
                       f'Events:'
                       f'\n{self.bot.socket_stats}')

    @commands.is_owner()
    @commands.command(aliases=['cancel_task'], description="Debug a task by a memory location", usage="<memory_id>")
    async def debug_task(self, ctx, memory_id: str = None):
        """Debug a task by a memory location."""
        if not memory_id:
            return await ctx.send("Please enter a task.")

        def hex_value(arg):
            return int(arg, base=16)

        memory_id = hex_value(memory_id)

        def object_at(addr):
            for o in gc.get_objects():
                if id(o) == addr:
                    return o
            return None

        task = object_at(memory_id)
        if task is None or not isinstance(task, asyncio.Task):
            return await ctx.send(f'Could not find Task object at {hex(memory_id)}.')

        if ctx.invoked_with == 'cancel_task':
            task.cancel()
            return await ctx.send(f'Cancelled task object {task!r}.')

        paginator = commands.Paginator(prefix='```py')
        fp = io.StringIO()
        frames = len(task.get_stack())
        paginator.add_line(f'# Total Frames: {frames}')
        task.print_stack(file=fp)

        for line in fp.getvalue().splitlines():
            paginator.add_line(line)

        for page in paginator.pages:
            await ctx.send(page)

    @commands.is_owner()
    @commands.command(aliases=['debugperms'], description="Shows permission resolution for a guild and an optional author", usage="[guild_id] [author_id]")
    async def debugpermissions(self, ctx, guild_id=None, author_id=None):
        """Shows permission resolution for a guild and an optional author."""
        if not guild_id and not author_id:
            return await ctx.send(f"{ctx.prefix}{ctx.command.name} <guild_id> <author_id>")

        guild = self.bot.get_guild(int(guild_id)) or ctx.guild
        if guild is None:
            return await ctx.send('Guild not found?')

        if author_id is None:
            member = guild.me
        else:
            member = await self.bot.get_or_fetch_member(guild, int(author_id))

        if member is None:
            return await ctx.send('Member not found?')

        permissions = member.guild_permissions
        allowed, denied = [], []
        for name, value in permissions:
            name = name.replace('_', ' ').replace('guild', 'server').title()
            if value:
                allowed.append(name)
            else:
                denied.append(name)

        e = discord.Embed(colour=discord.Colour.dark_theme(), description=f'Perms in `{guild.name}` for **{member}**')

        if allowed:
            e.add_field(name='Allowed', value='\n'.join(allowed))
        if denied:
            e.add_field(name='Denied', value='\n'.join(denied))
        await ctx.send(embed=e)

    # command stats
    def censor_object(self, obj):
        self.bot.blacklist = []

        if not isinstance(obj, str) and obj.id in self.bot.blacklist:
            return '[censored]'
        return self.censor_invite(obj)

    _INVITE_REGEX = re.compile(r'(?:https?:\/\/)?discord(?:\.gg|\.com|app\.com\/invite)?\/[A-Za-z0-9]+')

    def censor_invite(self, obj, *, _regex=_INVITE_REGEX):
        return _regex.sub('[censored-invite]', str(obj))

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
    #@commands.cooldown(5, 30.0, type=commands.BucketType.member)
    # @commands.dynamic_cooldown(custom_cooldown, commands.BucketType.member)
    @commands.guild_only()
    @commands.is_owner()
    async def stats(self, ctx, *, member: discord.Member = None):
        async with ctx.typing():
            if member is None:
                await self.show_guild_stats(ctx)
            else:
                await self.show_member_stats(ctx, member)

    @commands.command(description="Global all time command statistics.")
    async def globalstats(self, ctx):
        query = "SELECT COUNT(*) FROM commands;"
        total = await self.bot.pool.fetchrow(query)

        e = discord.Embed(title='Command Stats', colour=discord.Colour.blurple())
        e.description = f'{total[0]} commands used globally.'

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

    @commands.command(description="Global command statistics for the day")
    async def todaystats(self, ctx):
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

    @commands.command(aliases=['cmdh'], description="Global Command history")
    @commands.is_owner()
    async def commandhistory(self, ctx):
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

    @commands.command(aliases=['cmdhf'], description="Command history for a command", usage="[days=7] <command>")
    @commands.is_owner()
    async def commandhistoryfor(self, ctx, days: typing.Optional[int] = 7, *, command: str):
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

    @commands.command(aliases=['cmdhg'], description="Command history for a guild", usage="<guild_id>")
    @commands.is_owner()
    async def commandhistoryguild(self, ctx, guild_id: int):
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

    @commands.command(aliases=['cmdhu'], description="Command history for a user", usage="<user_id>")
    @commands.is_owner()
    async def commandhistoryuser(self, ctx, user_id: int):
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

    @commands.command(aliases=['cmdlog'], description="Command history log for the last N days", usage="[days=7]")
    @commands.is_owner()
    async def commandlog(self, ctx, days=7):
        query = """SELECT command, COUNT(*)
                   FROM commands
                   WHERE used > (CURRENT_TIMESTAMP - $1::interval)
                   GROUP BY command
                   ORDER BY 2 DESC
                """

        all_commands = {
            # add meta commands
            c.qualified_name: 0 for c in self.bot.get_cog('MetaCommands').walk_commands()
        }
        # add application commands
        for command in self.bot.tree.get_commands():
            all_commands[command.name] = 0

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



    # def display_top(self, snapshot, key_type='lineno', limit=10):
    #     snapshot = snapshot.filter_traces((
    #         tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
    #         tracemalloc.Filter(False, "<unknown>"),
    #     ))
    #     top_stats = snapshot.statistics(key_type)
    #
    #     print("Top %s lines" % limit)
    #     for index, stat in enumerate(top_stats[:limit], 1):
    #         frame = stat.traceback[0]
    #         print("#%s: %s:%s: %.1f KiB"
    #               % (index, frame.filename, frame.lineno, stat.size / 1024))
    #         line = linecache.getline(frame.filename, frame.lineno).strip()
    #         if line:
    #             print('    %s' % line)
    #
    #     other = top_stats[limit:]
    #     if other:
    #         size = sum(stat.size for stat in other)
    #         print("%s other: %.1f KiB" % (len(other), size / 1024))
    #     total = sum(stat.size for stat in top_stats)
    #     print("Total allocated size: %.1f KiB" % (total / 1024))
    #
    # @commands.command(description="Record a snapshot")
    # async def snap1(self, ctx):
    #     """ Record a snapshot """
    #     self.bot.snapshot1 = tracemalloc.take_snapshot()
    #
    # @commands.command(description="Display the differences since snap1")
    # async def snap2(self, ctx):
    #     """ Display the differences since snap1 """
    #     snapshot2 = tracemalloc.take_snapshot()
    #
    #     top_stats = snapshot2.compare_to(self.bot.snapshot1, 'lineno')
    #
    #     print("[ Top 10 differences ]")
    #     for stat in top_stats[:10]:
    #         print(stat)
    #
    # @commands.command(description="Display the traceback of the biggest memory block")
    # async def snapbig(self, ctx):
    #     """ Display the traceback of the biggest memory block """
    #     snapshot = tracemalloc.take_snapshot()
    #     top_stats = snapshot.statistics('traceback')
    #
    #     # pick the biggest memory block
    #     stat = top_stats[0]
    #     print("%s memory blocks: %.1f KiB" % (stat.count, stat.size / 1024))
    #     for line in stat.traceback.format():
    #         print(line)
    #
    # @commands.command(description="Display the 10 files allocating the most memory")
    # async def snaptop(self, ctx):
    #     """ Display the 10 files allocating the most memory """
    #     snapshot = tracemalloc.take_snapshot()
    #     top_stats = snapshot.statistics('lineno')
    #
    #     print("[ Top 10 ]")
    #     for stat in top_stats[:10]:
    #         print(stat)
    #
    # @commands.command(description="Display the 10 files allocating the most memory with a pretty output")
    # async def snapprettytop(self, ctx):
    #     """ Display the 10 files allocating the most memory with a pretty output """
    #     snapshot = tracemalloc.take_snapshot()
    #     self.display_top(snapshot)
    #
    # @commands.command(description="Trigger explicity GC")
    # async def gccollect(self, ctx):
    #     gc.collect()
    #     del gc.garbage[:]

async def setup(bot):
    if not hasattr(bot, 'uptime'):
        bot.uptime = discord.utils.utcnow()

        # Start tracing Python memory allocations
        #tracemalloc.start(25)  # Store 25 frames
        #bot.snapshot1 = tracemalloc.take_snapshot() #take first snapshot

    await bot.add_cog(OwnerCog(bot))
