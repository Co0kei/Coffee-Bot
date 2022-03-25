import json
import logging
import sys
import traceback
from pathlib import Path

import aiohttp
import discord
import topgg
from discord.ext import commands

# Setup logging
from constants import WEBHOOK_URL, TOKEN, PREFIX, DEV_BOT_TOKEN, DEV_PREFIX, DEV_SERVER_ID, TOPGG_PORT, TOPGG_TOKEN, \
    TOPGG_URL, TOPGG_PASSWORD

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%I:%M:%S %p')


class LoggingFilter(logging.Filter):
    def filter(self, record):
        if record.getMessage().startswith('Shard ID None has sent the RESUME payload.') \
                or record.getMessage().startswith('Shard ID None has successfully RESUMED session') \
                or record.getMessage().startswith('Shard ID None has sent the IDENTIFY payload.') \
                or record.getMessage().startswith('Shard ID None has connected to Gateway: ["') \
                or record.getMessage().startswith('logging in using static token') \
                or record.getMessage().startswith('PyNaCl is not installed, voice will NOT be supported') \
                or record.getMessage().startswith('Got a request to RESUME the websocket.') \
                or record.getMessage().startswith('Websocket closed'):
            return False  # dont log it
        return True


logging.getLogger('discord.gateway').addFilter(LoggingFilter())
logging.getLogger('discord.client').addFilter(LoggingFilter())

log = logging.getLogger(__name__)

operatingSys = sys.platform
log.info("USING OPERATING SYS: " + operatingSys)

if sys.platform == "win32":
    token = DEV_BOT_TOKEN  # development bot
    prefix = DEV_PREFIX
else:
    token = TOKEN  # production bot
    prefix = PREFIX

# Define bot
bot = commands.Bot(command_prefix=[prefix], description="A discord bot!", owner_id=452187819738267687,
                   case_insensitive=True,
                   allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, users=True,
                                                            replied_user=False),
                   intents=discord.Intents.all(), help_command=None)
tree = bot.tree

with open('stats.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    bot.stat_data = data
    f.close()

with open('guild_settings.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    bot.guild_settings = data  # load guild settings
    f.close()

with open('votes.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    bot.vote_data = data  # load vote data
    f.close()


# Report message
@tree.context_menu(name='Report Message')
async def globalReportMessage(interaction: discord.Interaction, message: discord.Message):
    await bot.get_cog("ReportCommand").handleMessageReport(interaction, message)


@tree.context_menu(name='Dev - Report Message', guild=discord.Object(id=DEV_SERVER_ID))
async def devReportMessage(interaction: discord.Interaction, message: discord.Message):
    await bot.get_cog("ReportCommand").handleMessageReport(interaction, message)


# Report User
@tree.context_menu(name='Report User')
async def globalReportUser(interaction: discord.Interaction, member: discord.Member):
    await bot.get_cog("ReportCommand").handleUserReport(interaction, member, None)


@tree.context_menu(name='Dev - Report User', guild=discord.Object(id=DEV_SERVER_ID))
async def devReportUser(interaction: discord.Interaction, member: discord.Member):
    await bot.get_cog("ReportCommand").handleUserReport(interaction, member, None)


@bot.event
async def on_ready():
    log.info(f'Connected to {(len(bot.guilds))} Discord Servers.')
    log.info('Bot online!')
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f'{len(bot.guilds)} guilds'))


@bot.event
async def setup_hook():
    log.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    bot.hook = discord.Webhook.from_url(WEBHOOK_URL, session=aiohttp.ClientSession(loop=bot.loop))
    bot.uptime = discord.utils.utcnow()

    if sys.platform != "win32":
        # topgg stuff - only run if on productions bot
        bot.topggpy = topgg.DBLClient(bot, TOPGG_TOKEN)
        bot.topgg_webhook = topgg.WebhookManager(bot).dbl_webhook(TOPGG_URL, TOPGG_PASSWORD)
        await bot.topgg_webhook.run(TOPGG_PORT)

    await load_cogs()


async def load_cogs():
    for file in Path('cogs').glob('**/*.py'):
        *filetree, _ = file.parts
        try:
            await bot.load_extension(f"{'.'.join(filetree)}.{file.stem}")
        except Exception as e:
            print(f'Failed to load extension {file}.', file=sys.stderr)
            traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)


if __name__ == '__main__':
    bot.run(token)
