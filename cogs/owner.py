import json
import logging
import os
import sys
import traceback
from pathlib import Path

import discord
from discord.ext import commands

# from bot import dev_server_id

log = logging.getLogger(__name__)


class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command()
    async def cogs(self, ctx):
        """ Command to list all cogs """
        embed = discord.Embed(title=f"**Cogs**", colour=discord.Colour.blue())

        cogs_data = ""
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    self.bot.load_extension(f'cogs.{filename[:-3]}')
                except commands.ExtensionAlreadyLoaded:
                    cogs_data += f"<:online:821068743987429438> {filename}\n"
                    # loaded
                else:
                    self.bot.unload_extension(f'cogs.{filename[:-3]}')
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
            self.bot.load_extension(f'cogs.{module}')
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
            self.bot.unload_extension(f'cogs.{module}')
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
            self.bot.reload_extension(f"cogs.{module}")
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
                self.bot.reload_extension(f"{'.'.join(tree)}.{file.stem}")
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

    @commands.command()
    async def about(self, ctx):
        """Tells you information about the bot itself """
        self.bot.commands_used += 1

        embed = discord.Embed()  # description='Latest Changes:\n')
        embed.title = 'Official Bot Server Invite'
        embed.url = 'https://discord.gg/rcUzqaQN8k'
        embed.colour = discord.Colour.blurple()

        owner = self.bot.get_user(self.bot.owner_id)
        embed.set_author(name=str(owner), icon_url=owner.display_avatar.url)

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

        #  memory_usage = self.process.memory_full_info().uss / 1024**2
        # cpu_usage = self.process.cpu_percent() / psutil.cpu_count()
        # embed.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU')

        #   version = pkg_resources.get_distribution('discord.py').version
        embed.add_field(name='Guilds', value=guilds)
        embed.add_field(name='Commands Used', value=self.bot.commands_used)

        # embed.add_field(name='Commands Run', value=sum(self.bot.command_stats.values()))
        # embed.add_field(name='Uptime', value=self.get_bot_uptime(brief=True))
        #   embed.set_footer(text=f'Made with discord.py v{version}', icon_url='http://i.imgur.com/5BFecvA.png')
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(OwnerCog(bot))
