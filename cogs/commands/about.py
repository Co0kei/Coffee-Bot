import datetime
import itertools
import logging
import math

import discord
import pkg_resources
import psutil
import pygit2
from discord import app_commands
from discord.ext import commands

from constants import DEV_SERVER_ID

log = logging.getLogger(__name__)


class AboutCommand(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.process = psutil.Process()

    @app_commands.command(name='about', description='Show statistics about me.')
    async def globalAboutCommand(self, interaction: discord.Interaction):
        await self.handleAboutCommand(interaction)

    async def handleAboutCommand(self, interaction: discord.Interaction):
        """Tells you information about the bot itself """
        embed = discord.Embed()
        embed.title = f'About {self.bot.user}'
        embed.url = 'https://github.com/Co0kei/Coffee-Bot'
        embed.colour = discord.Colour.blurple()

        # To properly cache myself, I need to use the bot dev server.
        dev_guild = self.bot.get_guild(DEV_SERVER_ID)
        owner = dev_guild.get_member(self.bot.owner_id)
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

        embed.add_field(name="Latest Commits", value=self.get_last_commits(), inline=False)

        bots = sum(u.bot for u in self.bot.users)
        embed.add_field(name='Members', value=f'{total_members:,} total\n{total_unique:,} unique\n{bots:,} bots')
        embed.add_field(name='Channels', value=f'{text + voice:,} total\n{text:,} text\n{voice:,} voice')

        memory_usage = self.process.memory_full_info().uss / 1024 ** 2
        cpu_usage = self.process.cpu_percent() / psutil.cpu_count()

        delta = discord.utils.utcnow() - self.bot.uptime
        minutes = delta.total_seconds() / 60
        total = sum(self.bot.socket_stats.values())
        cpm = total / minutes

        embed.add_field(name='Process', value=f'{memory_usage:.2f} MB\n{cpu_usage:.2f}% CPU\n{cpm:.2f} EPM')

        embed.add_field(name='Guilds', value=f'{guilds:,}')
        embed.add_field(name='Commands Run', value=f'{self.bot.stat_data["commands_used"]:,}')
        embed.add_field(name='Launch Time', value=discord.utils.format_dt(self.bot.uptime, "R"))

        # embed.add_field(name="Bot Ping", value=f"{self.bot.latency * 1000:.2f}ms")
        # embed.add_field(name="Socket Events", value=f"{cpm:.2f}/minute")

        version = pkg_resources.get_distribution('discord.py').version
        embed.set_footer(text=f'Made with discord.py v{version}', icon_url='http://i.imgur.com/5BFecvA.png')
        embed.timestamp = discord.utils.utcnow()

        view = self.CommitHistoryButton(commandsCog=self)

        await interaction.response.send_message(embed=embed, view=view)

        msg = await interaction.original_message()
        view.setOriginalMessage(msg)  # pass the original message into the class

    class CommitHistoryButton(discord.ui.View):

        def __init__(self, timeout=120, commandsCog=None):
            super().__init__(timeout=timeout)
            self.message = None  # the original interaction message
            self.commandsCog = commandsCog

        def setOriginalMessage(self, message: discord.Message):
            self.message = message

        async def on_timeout(self) -> None:
            await self.message.edit(view=None)

        @discord.ui.button(label='Commit History', emoji="<:github:962089212365111327>", style=discord.ButtonStyle.blurple)
        async def commitHistory(self, interaction: discord.Interaction, button: discord.ui.Button):
            totalCommits = self.commandsCog.get_total_commits()
            totalPages = int(math.ceil(totalCommits / 10.0))

            view = self.commandsCog.PaginatedCommitHistory(commandsCog=self.commandsCog, totalCommits=totalCommits, totalPages=totalPages)

            embed = discord.Embed(description=f'**GitHub Commit History** ({totalCommits} total)\n\n{self.commandsCog.get_last_commits(count=10)[:3900]}')
            embed.colour = discord.Colour.blurple()
            embed.set_footer(text=f"『 Page 1/{totalPages}』")

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

            msg = await interaction.original_message()
            view.setOriginalMessage(msg)  # pass the original message into the class

    class PaginatedCommitHistory(discord.ui.View):

        def __init__(self, timeout=120, commandsCog=None, totalCommits=None, totalPages=None):
            super().__init__(timeout=timeout)
            self.message = None  # the original interaction message
            self.commandsCog = commandsCog
            self.page = 1
            self.totalCommits = totalCommits
            self.totalPages = totalPages

        def setOriginalMessage(self, message: discord.Message):
            self.message = message

        async def on_timeout(self) -> None:
            await self.message.edit(view=None)

        @discord.ui.button(emoji="<:left:882953998603288586>", style=discord.ButtonStyle.grey)
        async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page == 1:
                self.page = self.totalPages
            else:
                self.page -= 1

            if self.totalCommits >= ((self.page - 1) * 10 + 10):
                iteratingIndex = 10
            else:
                iteratingIndex = self.totalCommits - ((self.page - 1) * 10)

            embed = discord.Embed(description=f'**GitHub Commit History** ({self.totalCommits} total)\n\n'
                                              f'{self.commandsCog.get_commits(start=(self.page - 1) * 10, end=(self.page - 1) * 10 + iteratingIndex)[:3900]}')
            embed.colour = discord.Colour.blurple()
            embed.set_footer(text=f"『 Page {self.page}/{self.totalPages}』")

            await interaction.response.edit_message(embed=embed)

        @discord.ui.button(emoji="<:right:882953977388486676>", style=discord.ButtonStyle.grey)
        async def forward(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page == self.totalPages:
                self.page = 1
            else:
                self.page += 1

            if self.totalCommits >= ((self.page - 1) * 10 + 10):
                iteratingIndex = 10
            else:
                iteratingIndex = self.totalCommits - ((self.page - 1) * 10)

            embed = discord.Embed(description=f'**GitHub Commit History** ({self.totalCommits} total)\n\n'
                                              f'{self.commandsCog.get_commits(start=(self.page - 1) * 10, end=(self.page - 1) * 10 + iteratingIndex)[:3900]}')
            embed.colour = discord.Colour.blurple()
            embed.set_footer(text=f"『 Page {self.page}/{self.totalPages}』")

            await interaction.response.edit_message(embed=embed)

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

    def get_commits(self, start=0, end=10):
        repo = pygit2.Repository('.git')
        commits = list(itertools.islice(repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL), start, end))
        return '\n'.join(self.format_commit(c) for c in commits)

    def get_total_commits(self):
        repo = pygit2.Repository('.git')
        return len([commit for commit in repo.walk(repo.head.target)])


async def setup(bot):
    await bot.add_cog(AboutCommand(bot))
