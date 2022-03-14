import datetime
import io
import itertools
import json
import logging
import os
import sys
import textwrap
import traceback
from contextlib import redirect_stdout
from pathlib import Path

import discord
import pkg_resources
import psutil
import pygit2
from dateutil.relativedelta import relativedelta
from discord.ext import commands

# from bot import dev_server_id

log = logging.getLogger(__name__)


class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.process = psutil.Process()

    @commands.is_owner()
    @commands.command()
    async def cogs(self, ctx):
        """ Command to list all cogs """
        embed = discord.Embed(title=f"**Cogs**", colour=discord.Colour.blue())

        cogs_data = ""
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.bot.load_extension(f'cogs.{filename[:-3]}')
                except commands.ExtensionAlreadyLoaded:
                    cogs_data += f"<:online:821068743987429438> {filename}\n"
                    # loaded
                else:
                    await self.bot.unload_extension(f'cogs.{filename[:-3]}')
                    cogs_data += f"<:offline:821068938036379679> {filename}\n"
                    # unloaded

        embed.add_field(name="**Cogs**", value=f"{cogs_data}", inline=True)
        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command()
    async def load(self, ctx, *, module=None):
        """ Load a specific cog """
        if module is None:
            await ctx.send(f"\U0000274c Enter a cog to load!")
            return
        try:
            await self.bot.load_extension(f'cogs.{module}')
            await ctx.send(f"\U00002705 Cog {module} loaded successfully!")

        except commands.ExtensionAlreadyLoaded:
            await ctx.send("\U0000274c This cog is already loaded!")

        except commands.ExtensionNotFound:
            await ctx.send("\U0000274c This cog could not be found!")

        except Exception as e:
            traceback.print_exc()
            await ctx.send(f"\U0000274c {e}")

    @commands.is_owner()
    @commands.command()
    async def unload(self, ctx, *, module=None):
        """ Unload a specific cog """
        if module is None:
            await ctx.send(f"\U0000274c Enter a cog to unload!")
            return
        try:
            await self.bot.unload_extension(f'cogs.{module}')
            await ctx.send(f"\U00002705 Cog {module} unloaded successfully!")

        except commands.ExtensionNotLoaded:
            await ctx.send("\U0000274c This cog is already unloaded!")

        except commands.ExtensionNotFound:
            await ctx.send("\U0000274c This cog could not be found!")

        except Exception as e:
            traceback.print_exc()
            await ctx.send(f"\U0000274c {e}")

    @commands.is_owner()
    @commands.command(aliases=["r"])
    async def reload(self, ctx, *, module="interactions"):
        """" Reload a specific cog """
        if module is None:
            await ctx.send(f"\U0000274c Enter a cog to reload!")
            return
        try:
            await self.bot.reload_extension(f"cogs.{module}")
            await ctx.send(f"\U00002705 Successfully reloaded {module}!")

        except commands.ExtensionNotFound:
            await ctx.send("\U0000274c This cog could not be found!")

        except Exception as e:
            traceback.print_exc()
            await ctx.send(f"\U0000274c {e}")

    @commands.is_owner()
    @commands.command(aliases=["rall"])
    async def reloadall(self, ctx):
        msg = ""
        for file in Path('cogs').glob('**/*.py'):
            *tree, _ = file.parts
            try:
                await self.bot.reload_extension(f"{'.'.join(tree)}.{file.stem}")
                msg += f"\U00002705 Successfully reloaded {file}!\n"

            except Exception as e:
                print(f'Failed to reload extension {file}.', file=sys.stderr)
                msg += f"\U0000274c Failed to reload {file} with reason: {e}\n"
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)

        await ctx.send(msg)

    @commands.is_owner()
    @commands.command()
    async def dump(self, ctx):

        # save commands used
        data = {"commands_used": self.bot.commands_used}
        with open('stats.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            f.close()

        log.info("[DUMP] Saved commands_used: " + str(self.bot.commands_used))

        # save guild settings
        with open('guild_settings.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.guild_settings, f, ensure_ascii=False, indent=4)
            f.close()

        log.info("[DUMP] Saved guild_settings: " + str(self.bot.guild_settings))

        await ctx.message.reply("Data saved")

    @commands.is_owner()
    @commands.command()
    async def sync(self, ctx):
        await ctx.send("processing")
        a = await self.bot.tree.sync(guild=discord.Object(id=self.bot.dev_server_id))
        await ctx.message.reply("Dev server interactions synced: " + str(a))

    @commands.is_owner()
    @commands.command()
    async def globalsync(self, ctx):
        await ctx.send("processing global sync")
        a = await self.bot.tree.sync()
        await ctx.message.reply("Global interaction sync done: " + str(a))

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @commands.is_owner()
    @commands.command(name="eval")
    async def _eval(self, ctx, *, body: str):
        """Evaluates code"""

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

    # def format_dt(self, dt, style=None):
    #     if dt.tzinfo is None:
    #         dt = dt.replace(tzinfo=datetime.timezone.utc)
    #
    #     if style is None:
    #         return f'<t:{int(dt.timestamp())}>'
    #     return f'<t:{int(dt.timestamp())}:{style}>'
    #
    # def format_relative(self, dt):
    #     return self.format_dt(dt, 'R')

    def format_commit(self, commit):
        short, _, _ = commit.message.partition('\n')
        short_sha2 = commit.hex[0:6]
        commit_tz = datetime.timezone(datetime.timedelta(minutes=commit.commit_time_offset))
        commit_time = datetime.datetime.fromtimestamp(commit.commit_time).astimezone(commit_tz)

        offset = discord.utils.format_dt(commit_time, style='R')
        return f'[`{short_sha2}`](https://github.com/Co0kei/Coffee-Bot/commit/{commit.hex}) {short} ({offset})'

    def get_last_commits(self, count=6):
        repo = pygit2.Repository('.git')
        commits = list(itertools.islice(repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL), count))
        return '\n'.join(self.format_commit(c) for c in commits)

    def get_bot_uptime(self, *, brief=False):
        return self.human_timedelta(self.bot.uptime, accuracy=None, brief=brief, suffix=False)

    class plural:
        def __init__(self, value):
            self.value = value

        def __format__(self, format_spec):
            v = self.value
            singular, sep, plural = format_spec.partition('|')
            plural = plural or f'{singular}s'
            if abs(v) != 1:
                return f'{v} {plural}'
            return f'{v} {singular}'

    def human_join(self, seq, delim=', ', final='or'):
        size = len(seq)
        if size == 0:
            return ''

        if size == 1:
            return seq[0]

        if size == 2:
            return f'{seq[0]} {final} {seq[1]}'

        return delim.join(seq[:-1]) + f' {final} {seq[-1]}'

    def human_timedelta(self, dt, *, source=None, accuracy=3, brief=False, suffix=True):
        now = source or datetime.datetime.now(datetime.timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)

        if now.tzinfo is None:
            now = now.replace(tzinfo=datetime.timezone.utc)

        # Microsecond free zone
        now = now.replace(microsecond=0)
        dt = dt.replace(microsecond=0)

        # This implementation uses relativedelta instead of the much more obvious
        # divmod approach with seconds because the seconds approach is not entirely
        # accurate once you go over 1 week in terms of accuracy since you have to
        # hardcode a month as 30 or 31 days.
        # A query like "11 months" can be interpreted as "!1 months and 6 days"
        if dt > now:
            delta = relativedelta(dt, now)
            suffix = ''
        else:
            delta = relativedelta(now, dt)
            suffix = ' ago' if suffix else ''

        attrs = [
            ('year', 'y'),
            ('month', 'mo'),
            ('day', 'd'),
            ('hour', 'h'),
            ('minute', 'm'),
            ('second', 's'),
        ]

        output = []
        for attr, brief_attr in attrs:
            elem = getattr(delta, attr + 's')
            if not elem:
                continue

            if attr == 'day':
                weeks = delta.weeks
                if weeks:
                    elem -= weeks * 7
                    if not brief:
                        output.append(format(self.plural(weeks), 'week'))
                    else:
                        output.append(f'{weeks}w')

            if elem <= 0:
                continue

            if brief:
                output.append(f'{elem}{brief_attr}')
            else:
                output.append(format(self.plural(elem), attr))

        if accuracy is not None:
            output = output[:accuracy]

        if len(output) == 0:
            return 'now'
        else:
            if not brief:
                return self.human_join(output, final='and') + suffix
            else:
                return ' '.join(output) + suffix

    @commands.command()
    async def about(self, ctx):
        """Tells you information about the bot itself """
        self.bot.commands_used += 1

        revision = self.get_last_commits()
        embed = discord.Embed(description='Latest Changes:\n' + revision)
        embed.title = 'Official Bot Server Invite'
        embed.url = 'https://discord.gg/rcUzqaQN8k'
        embed.colour = discord.Colour.blurple()

        owner = self.bot.get_user(self.bot.owner_id)
        embed.set_author(name="Created by " + str(owner), icon_url=owner.display_avatar.url)

        # statistics
        total_members = 0
        total_unique = len(self.bot.users)

        text = 0
        voice = 0
        guilds = 0
        for guild in self.bot.guilds:
            guilds += 1
            if guild.unavailable:
                continue

            total_members += len(guild.members)
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    text += 1
                elif isinstance(channel, discord.VoiceChannel):
                    voice += 1

        embed.add_field(name='Members', value=f'{total_members} total\n{total_unique} unique')
        embed.add_field(name='Channels', value=f'{text + voice} total\n{text} text\n{voice} voice')

        memory_usage = self.process.memory_full_info().uss / 1024 ** 2
        cpu_usage = self.process.cpu_percent() / psutil.cpu_count()
        embed.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU')

        version = pkg_resources.get_distribution('discord.py').version
        embed.add_field(name='Guilds', value=guilds)
        embed.add_field(name='Commands Run', value=self.bot.commands_used)

        embed.add_field(name='Uptime', value=self.get_bot_uptime(brief=True))
        embed.set_footer(text=f'Made with discord.py v{version}', icon_url='http://i.imgur.com/5BFecvA.png')
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
