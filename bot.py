import logging
import sys
import traceback
from pathlib import Path

import aiohttp
import discord
from discord.ext import commands

from constants import *

log = logging.getLogger(__name__)

# Check environment
if sys.platform == DEV_PLATFORM:
    token = DEV_BOT_TOKEN
    prefix = DEV_PREFIX
else:
    token = TOKEN
    prefix = PREFIX


# Bot prefix function
def get_prefix(bot, msg):
    prefix = bot.default_prefix

    if msg.guild:
        guild_id = msg.guild.id
        if str(guild_id) in bot.guild_settings:
            if "prefix" in bot.guild_settings[str(guild_id)]:
                prefix = bot.guild_settings[str(guild_id)]["prefix"]

    return commands.when_mentioned_or(prefix)(bot, msg)


# Define bot
bot = commands.Bot(command_prefix=get_prefix, owner_id=452187819738267687,
                   case_insensitive=True,
                   allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, replied_user=False, users=True),
                   intents=discord.Intents.all(), help_command=None)
bot.default_prefix = prefix


# Setup Context Menus
@bot.tree.context_menu(name='Report Message')
async def globalReportMessage(interaction: discord.Interaction, message: discord.Message):
    await bot.get_cog("ReportCommand").handleMessageReport(interaction, message)


@bot.tree.context_menu(name='Report User')
async def globalReportUser(interaction: discord.Interaction, member: discord.Member):
    await bot.get_cog("ReportCommand").handleUserReport(interaction, member, None)


# Events
@bot.event
async def on_ready():
    log.info(f'Bot online! Connected to {(len(bot.guilds))} Discord Servers.')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'{len(bot.guilds)} guilds'))


@bot.event
async def setup_hook():
    bot.session = aiohttp.ClientSession(loop=bot.loop)
    await load_cogs()  # load logging first
    log.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    await (bot.get_command("loadmemory"))(None)  # load data into memory


@bot.event
async def close():
    await bot.session.close()
    await super(commands.Bot, bot).close()  # dont eat the super method


# Methods
async def load_cogs():
    for file in Path('cogs').glob('**/*.py'):
        *filetree, _ = file.parts
        try:
            await bot.load_extension(f"{'.'.join(filetree)}.{file.stem}")
        except Exception as e:
            log.warning(f'Failed to load extension {file}.')
            traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)


# Start Bot
if __name__ == '__main__':
    bot.run(token, reconnect=True)
