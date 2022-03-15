import io
import json
import logging
import os
import shutil
import sys
import textwrap
import traceback
from contextlib import redirect_stdout
from pathlib import Path

import discord
import pygit2
from discord.ext import commands

log = logging.getLogger(__name__)


class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

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
    async def test(self, ctx):

        users = await self.bot.topggpy.get_bot_votes()

        peoplethatvoted = []

        for user in users:
            username = user["username"]
            peoplethatvoted.append(username)

        await ctx.send(f'Bot Vote History:\n' + "\n".join(peoplethatvoted))
        print(users)

    @commands.is_owner()
    @commands.command()
    async def syncdev(self, ctx):
        await ctx.send("Processing")
        a = await self.bot.tree.sync(guild=discord.Object(id=self.bot.dev_server_id))
        # print(self.bot.tree)
        # print(ctx.guild.id)
        # a = await self.bot.tree.copy_global_to(guild=discord.Object(ctx.guild.id))

        await ctx.message.reply("Server interactions synced: " + str(a))

    # @commands.is_owner()
    # @commands.command()
    # async def removelocal(self, ctx, guild=None):
    #     await ctx.send("Processing")
    #
    #     for command in self.bot.tree.get_commands(guild=discord.Object(guild or ctx.guild.id)):
    #         self.bot.tree.remove_command(command.name, guild=discord.Object(guild or ctx.guild.id))
    #
    #     await ctx.message.reply("Server interactions removed")

    @commands.is_owner()
    @commands.command()
    async def syncglobal(self, ctx):
        await ctx.send("processing global sync")
        a = await self.bot.tree.sync()
        await ctx.message.reply("Global interaction sync done: " + str(a))

    @commands.is_owner()
    @commands.command(name="clonerepo")
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


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
