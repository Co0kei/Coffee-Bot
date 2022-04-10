import asyncio
import io
import json
import logging
import os
import shutil
import sys
import textwrap
import time
import traceback
from contextlib import redirect_stdout
from pathlib import Path

import discord
import psutil
import pygit2
from discord.ext import commands

from constants import DEV_SERVER_ID

log = logging.getLogger(__name__)


class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx) -> bool:
        return await self.bot.is_owner(ctx.author)

    @commands.command(description="Shows all owner help commands")
    async def owner(self, ctx):
        owner_commands = ""
        for command in self.get_commands():
            owner_commands += f'**{ctx.prefix}{command.name}** - {command.aliases} - {command.description}\n'

        embed = discord.Embed(title="Owner Commands", description=owner_commands, colour=discord.Colour(0x2F3136))

        await ctx.message.reply(embed=embed)

    @commands.command(description="Shows all cogs.")
    async def cogs(self, ctx):
        """ Command to list all cogs and whether they are loaded or not """
        embed = discord.Embed(colour=discord.Colour.blue())

        loaded_extensions = [str(e) for e in self.bot.extensions]

        cogs_data = ""
        for file in Path('cogs').glob('**/*.py'):
            *tree, _ = file.parts
            cog_path = f"{'.'.join(tree)}.{file.stem}"
            if cog_path in loaded_extensions:
                cogs_data += f"<:online:821068743987429438> {cog_path}\n"
            else:
                cogs_data += f"<:offline:821068938036379679> {cog_path}\n"

        embed.add_field(name="**Cogs**", value=f"{cogs_data}", inline=True)

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
        msg = ""
        for file in Path('cogs').glob('**/*.py'):
            *tree, _ = file.parts
            try:
                await self.bot.reload_extension(f"{'.'.join(tree)}.{file.stem}")
                msg += f"\U00002705 Successfully reloaded {file}!\n"

            except commands.ExtensionNotLoaded:  # if not loaded then load
                await self.bot.load_extension(f"{'.'.join(tree)}.{file.stem}")
                msg += f"\U00002705 Successfully loaded {file}!\n"

            except Exception as e:
                log.warning(f'Failed to reload extension {file}.', file=sys.stderr)
                msg += f"\U0000274c Failed to reload {file} with reason: {e}\n"
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        if ctx is not None:
            await ctx.send(msg)

    @commands.is_owner()
    @commands.command(description="Saves all data to disk.")
    async def dump(self, ctx):
        """ Save data to disk """

        with open('stats.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.stat_data, f, ensure_ascii=False, indent=4)
            f.close()

        # save guild settings
        with open('guild_settings.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.guild_settings, f, ensure_ascii=False, indent=4)
            f.close()

        # save vote data
        with open('votes.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.vote_data, f, ensure_ascii=False, indent=4)
            f.close()

        if ctx is not None:
            await ctx.message.reply("Data saved")

    @commands.is_owner()
    @commands.command(aliases=["loadmemory"], description="Reloads the data in memory by reading from disk")
    async def refreshmemory(self, ctx):
        """ Reload data from disk"""
        with open('stats.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.bot.stat_data = data
            f.close()

        with open('guild_settings.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.bot.guild_settings = data  # load guild settings
            f.close()

        with open('votes.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.bot.vote_data = data  # load vote data
            f.close()

        if ctx is not None:
            await ctx.message.reply("Data reloaded")

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
    #
    # @commands.is_owner()
    # @commands.command(description="Manually update the bots server and shard count to top.gg")
    # async def updatetopgg(self, ctx):
    #     await self.bot.get_cog("EventCog").post_guild_count()
    #     await ctx.message.reply("Done")

    @commands.is_owner()
    @commands.command(name="backup", description="Backups files")
    async def backup(self, ctx):
        files = ['guild_settings.json', 'stats.json', 'votes.json']

        shutil.rmtree("backups")
        os.mkdir('backups')

        for f in files:
            shutil.copy(f, 'backups')

        if ctx is not None:
            await ctx.reply("Done")

    @commands.is_owner()
    @commands.command(description="Simulate a player voting. Used for testing purposes")
    async def simvote(self, ctx, id=None, is_weekend=False):  # add optional weekend param
        id = id or ctx.author.id

        # {'user': 'id', 'type': 'upvote', 'query': {}, 'bot': 950765718209720360, 'is_weekend': False}
        example_data = {'user': id, 'type': 'upvote', 'query': {}, 'bot': 950765718209720360,
                        'is_weekend': is_weekend}

        await self.bot.get_cog("EventCog").on_dbl_vote(example_data)
        await ctx.message.reply("Vote simulated!\n" + str(example_data))

    @commands.is_owner()
    @commands.command(description="Syncs the command tree for the dev server")
    async def syncdev(self, ctx):
        await ctx.send("Processing")

        self.bot.tree.copy_global_to(guild=discord.Object(id=DEV_SERVER_ID))
        result = await self.bot.tree.sync(guild=discord.Object(id=DEV_SERVER_ID))

        await ctx.message.reply("Synced dev server interactions:\n" + str(result))

    @commands.is_owner()
    @commands.command(description="Removes guild specific command tree commands from the dev server")
    async def cleardev(self, ctx):
        await ctx.send("Processing")

        for command in await self.bot.tree.fetch_commands(guild=discord.Object(id=DEV_SERVER_ID)):
            self.bot.tree.remove_command(command.name, guild=discord.Object(id=DEV_SERVER_ID), type=command.type)

        result = await self.bot.tree.sync(guild=discord.Object(id=DEV_SERVER_ID))
        await ctx.message.reply("Dev server local interactions removed:\n" + str(result))

    @commands.is_owner()
    @commands.command(description="Syncs the global command tree. This takes one hour to propogate")
    async def syncglobal(self, ctx):
        await ctx.send("Processing global sync")
        result = await self.bot.tree.sync()
        await ctx.message.reply("Global interaction sync complete:\n" + str(result))

    @commands.is_owner()
    @commands.command(name="stop", aliases=["close"], description="Gracefully stops the bot")
    async def _stop(self, ctx):

        # check for vote alerts within the next 2 hours
        msg = ""
        current_time: int = int(time.time())
        if "vote_reminder" in self.bot.vote_data:
            vote_reminders: list = self.bot.vote_data["vote_reminder"]
            if len(vote_reminders) != 0:
                for discordID in vote_reminders:
                    last_vote = self.bot.vote_data[str(discordID)]["last_vote"]
                    difference = (current_time - last_vote)
                    if difference > 36000:  # num of seconds in 10 hours
                        # alert me if anyone is expecting an alert in next 2 hours
                        msg += f'`+` Discord ID {discordID} is expecting a vote reminder <t:{self.bot.vote_data[str(discordID)]["last_vote"] + 43200}:R>\n'

        if msg != "":
            # ask if wants to continue
            embed = discord.Embed(title="Vote reminders in the next 2 hours", description=msg[:4000],
                                  color=discord.Colour.dark_theme())
            view = self.Confirm()

            sent_msg = await ctx.send(content='Do you want to continue?', embed=embed, view=view)

            await view.wait()  # Wait for the View to stop listening for input...

            await sent_msg.edit(view=None)

            if view.value is None:
                return  # timed out
            elif view.value:
                pass  # confirm
            else:
                return  # cancelled

        await self.bot.change_presence(status=discord.Status.dnd, activity=discord.Game("Shutting down..."))
        await asyncio.sleep(1)

        cmd = self.bot.get_command("dump")
        await cmd(ctx)

        # unload all cogs
        msg = ""
        for file in Path('cogs').glob('**/*.py'):
            *tree, _ = file.parts
            try:
                await self.bot.unload_extension(f"{'.'.join(tree)}.{file.stem}")
                msg += f"\U00002705 Successfully unloaded {file}!\n"

            except Exception as e:
                log.warning(f'Failed to unload extension {file}.', file=sys.stderr)
                msg += f"\U0000274c Failed to unload {file} with reason: {e}\n"
                traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)

        await ctx.send(msg)

        await self.bot.close()

    class Confirm(discord.ui.View):
        def __init__(self):
            super().__init__()
            self.value = None

        @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message('Stopping bot...', ephemeral=True)
            self.value = True
            self.stop()

        @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message('Cancelling', ephemeral=True)
            self.value = False
            self.stop()

    @commands.is_owner()
    @commands.command(name="clonerepo", description="Pulls github commits")
    async def forceRefreshGithub(self, ctx):
        if sys.platform == "win32":
            await ctx.send("dont need to")
            return
        try:
            shutil.rmtree(".git")
        except:
            pass
        repo = pygit2.clone_repository("https://github.com/Co0kei/Coffee-Bot", ".git", bare=True)
        await ctx.send(repo)

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @commands.is_owner()
    @commands.command(name="eval", description="Evaluates code")
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

    @commands.is_owner()
    @commands.command(aliases=["health"], description="Various bot health monitoring tools")
    async def bothealth(self, ctx):
        """Various bot health monitoring tools."""

        HEALTHY = discord.Colour(value=0x43B581)
        UNHEALTHY = discord.Colour(value=0xF04947)
        WARNING = discord.Colour(value=0xF09E47)
        total_warnings = 0

        embed = discord.Embed(title='Bot Health Report', colour=HEALTHY)
        description = []

        try:
            task_retriever = asyncio.Task.all_tasks
        except AttributeError:
            task_retriever = asyncio.all_tasks

        all_tasks = task_retriever(loop=self.bot.loop)

        event_tasks = [
            t for t in all_tasks
            if 'Client._run_event' in repr(t) and not t.done()
        ]

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

        memory_usage = self.bot.get_cog('AboutCommand').process.memory_full_info().uss / 1024 ** 2
        cpu_usage = self.bot.get_cog('AboutCommand').process.cpu_percent() / psutil.cpu_count()
        embed.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU', inline=False)

        global_rate_limit = not self.bot.http._global_over.is_set()
        description.append(f'Global Rate Limit: {global_rate_limit}')

        if global_rate_limit or total_warnings >= 9:
            embed.colour = UNHEALTHY

        embed.set_footer(text=f'{total_warnings} warning(s)')
        embed.description = '\n'.join(description)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
