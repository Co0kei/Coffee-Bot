import logging
import sys
import traceback
from pathlib import Path

import aiohttp
import discord
import topgg
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

# Define bot
bot = commands.Bot(command_prefix=commands.when_mentioned_or(*[prefix]), owner_id=452187819738267687,
                   case_insensitive=True,
                   allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, replied_user=False, users=True),
                   intents=discord.Intents.all(), help_command=None)


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
    log.info(f'Connected to {(len(bot.guilds))} Discord Servers.')
    log.info('Bot online!')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'{len(bot.guilds)} guilds'))


@bot.event
async def setup_hook():
    await load_cogs()

    log.info(f'Logged in as {bot.user} (ID: {bot.user.id})')

    bot.hook = discord.Webhook.from_url(WEBHOOK_URL, session=aiohttp.ClientSession(loop=bot.loop))
    bot.error_hook = discord.Webhook.from_url(ERROR_HOOK_URL, session=aiohttp.ClientSession(loop=bot.loop))
    bot.uptime = discord.utils.utcnow()
    bot._last_module = None

    if sys.platform != DEV_PLATFORM:
        await setup_topgg()

    await (bot.get_command("loadmemory"))(None)  # load data into memory


# Methods
async def load_cogs():
    for file in Path('cogs').glob('**/*.py'):
        *filetree, _ = file.parts
        try:
            await bot.load_extension(f"{'.'.join(filetree)}.{file.stem}")
        except Exception as e:
            log.warning(f'Failed to load extension {file}.')
            traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)


async def setup_topgg():
    # topgg stuff - only run if on productions bot
    bot.topggpy = topgg.DBLClient(bot, TOPGG_TOKEN)
    bot.topgg_webhook = topgg.WebhookManager(bot).dbl_webhook(TOPGG_URL, TOPGG_PASSWORD)
    await bot.topgg_webhook.run(TOPGG_PORT)


# Start Bot
if __name__ == '__main__':
    bot.run(token)
