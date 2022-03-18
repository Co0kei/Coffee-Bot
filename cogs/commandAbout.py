import datetime
import itertools
import logging

import discord
import pkg_resources
import psutil
import pygit2
from dateutil.relativedelta import relativedelta
from discord import app_commands
from discord.ext import commands

import dev_server

log = logging.getLogger(__name__)


class AboutCommand(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.process = psutil.Process()

    @app_commands.command(name='about', description='Shows statistics about the bot itself.')
    async def globalAboutCommand(self, interaction: discord.Interaction):
        await self.handleAboutCommand(interaction)

    @app_commands.command(name='devabout', description='Dev - Shows statistics about the bot itself.')
    @app_commands.guilds(discord.Object(id=dev_server.DEV_SERVER_ID))
    async def devAboutCommand(self, interaction: discord.Interaction):
        await self.handleAboutCommand(interaction)

    async def handleAboutCommand(self, interaction: discord.Interaction):
        """Tells you information about the bot itself """

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
        embed.add_field(name='Commands Run', value=self.bot.stat_data["commands_used"])

        embed.add_field(name='Uptime', value=self.get_bot_uptime(brief=True))
        embed.set_footer(text=f'Made with discord.py v{version}', icon_url='http://i.imgur.com/5BFecvA.png')
        embed.timestamp = discord.utils.utcnow()

        view = self.Button(commandsCog=self)

        await interaction.response.send_message(embed=embed, view=view)

        msg = await interaction.original_message()
        view.setOriginalMessage(msg)  # pass the original message into the class

    class Button(discord.ui.View):
        """ The buttons which are on the settings page """

        def __init__(self, timeout=120, commandsCog=None):
            super().__init__(timeout=timeout)
            self.message = None  # the original interaction message
            self.commandsCog = commandsCog

        def setOriginalMessage(self, message: discord.Message):
            self.message = message

        async def on_timeout(self) -> None:
            await self.message.edit(view=None)

        @discord.ui.button(label='More Changes', style=discord.ButtonStyle.green)
        async def moreChanges(self, button: discord.ui.Button, interaction: discord.Interaction):
            revision = self.commandsCog.get_last_commits(count=20)
            embed = discord.Embed(description='Latest 20 GitHub Commits:\n' + revision[:3900])
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # methods
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


async def setup(bot):
    await bot.add_cog(AboutCommand(bot))
