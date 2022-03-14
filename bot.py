import json
import logging
import sys
import traceback
from pathlib import Path
from typing import Optional

import aiohttp
import discord
from discord.ext import commands

# Setup logging
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
                or record.getMessage().startswith('Got a request to RESUME the websocket.'):
            return False  # dont log it
        return True


logging.getLogger('discord.gateway').addFilter(LoggingFilter())
logging.getLogger('discord.client').addFilter(LoggingFilter())

log = logging.getLogger(__name__)

with open('config.json', 'r') as f:
    botsettings = json.load(f)

    operatingSys = sys.platform
    log.info("USING OPERATING SYS: " + operatingSys)

    dev_server_id = botsettings["dev_server_id"]
    webhook_id = botsettings["webhook_id"]
    webhook_token = botsettings["webhook_token"]

    if sys.platform == "win32":
        token = botsettings["dev_bot_token"]  # development bot
        prefix = botsettings["dev_prefix"]
    else:
        token = botsettings["token"]  # production bot
        prefix = botsettings["prefix"]

    f.close()

# Define bot
bot = commands.Bot(command_prefix=[prefix], description="A discord bot!", owner_id=452187819738267687,
                   case_insensitive=True,
                   allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, users=True,
                                                            replied_user=False),
                   intents=discord.Intents.all(), help_command=None)
tree = bot.tree  # app_commands.CommandTree(bot)
bot.dev_server_id = dev_server_id

with open('stats.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    bot.commands_used = data["commands_used"]  # load command usage
    f.close()

with open('guild_settings.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    bot.guild_settings = data  # load guild settings
    f.close()


# Interactions - GLOBAL

# Report message
@tree.context_menu(name='Report Message')
async def globalReportMessage(interaction: discord.Interaction, message: discord.Message):
    await bot.get_cog("InteractionsCog").handleMessageReport(interaction, message)


# Report User
@tree.context_menu(name='Report User')
async def globalReportUser(interaction: discord.Interaction, member: discord.Member):
    await bot.get_cog("InteractionsCog").handleUserReport(interaction, member, None)


# Reports command
@tree.command(name='report', description='Report a member with a reason for staff to see.')
@discord.app_commands.describe(member='The member you are reporting.')
@discord.app_commands.describe(image='You can upload an image for staff to see if you wish.')
async def globalReportCommand(interaction: discord.Interaction, member: discord.User,
                              image: Optional[discord.Attachment] = None):
    await bot.get_cog("InteractionsCog").handleUserReport(interaction, member, image)


# Help command
@tree.command(name='help', description='Information on commands & bot setup.')
async def globalHelpCommand(interaction: discord.Interaction):
    await bot.get_cog("InteractionsCog").handleHelpCommand(interaction)


# settings command
@tree.command(name='settings', description='Configure how the bot works in your server.')
async def globalSettingsCommand(interaction: discord.Interaction):
    await bot.get_cog("SettingsCog").handleSettingsCommand(interaction)


# Interactions - dev server

# Report message
@tree.context_menu(name='Dev - Report Message', guild=discord.Object(id=dev_server_id))
async def devReportMessage(interaction: discord.Interaction, message: discord.Message):
    await bot.get_cog("InteractionsCog").handleMessageReport(interaction, message)


# Report User
@tree.context_menu(name='Dev - Report User', guild=discord.Object(id=dev_server_id))
async def devReportUser(interaction: discord.Interaction, member: discord.Member):
    await bot.get_cog("InteractionsCog").handleUserReport(interaction, member, None)


# Reports command
@tree.command(name='devreport', description='Report a member with a reason for staff to see.',
              guild=discord.Object(id=dev_server_id))
@discord.app_commands.describe(member='The member you are reporting.')
@discord.app_commands.describe(image='You can upload an image for staff to see if you wish.')
async def devReportCommand(interaction: discord.Interaction, member: discord.User,
                           image: Optional[discord.Attachment] = None):
    await bot.get_cog("InteractionsCog").handleUserReport(interaction, member, image)


# Help command
@tree.command(name='devhelp', description='Information on commands & bot setup',
              guild=discord.Object(id=dev_server_id))
async def devHelpCommand(interaction: discord.Interaction):
    await bot.get_cog("InteractionsCog").handleHelpCommand(interaction)


# settings command
@tree.command(name='devsettings', description='Configure how Coffee Bot is setup in your server.',
              guild=discord.Object(id=dev_server_id))
# @commands.has_permissions()
async def devSettingsCommand(interaction: discord.Interaction):
    await bot.get_cog("SettingsCog").handleSettingsCommand(interaction)


# Events

@bot.event
async def on_ready():
    log.info('Bot online!')
    log.info(f'Connected to {(len(bot.guilds))} Discord Servers.')


@bot.event
async def setup_hook():
    log.info(f'Logged in as {bot.user} (ID: {bot.user.id})')

    bot.hook = discord.Webhook.partial(webhook_id, webhook_token, session=aiohttp.ClientSession(loop=bot.loop))

    bot.uptime = discord.utils.utcnow()

    for file in Path('cogs').glob('**/*.py'):
        *filetree, _ = file.parts
        try:
            await bot.load_extension(f"{'.'.join(filetree)}.{file.stem}")
        except Exception as e:
            print(f'Failed to load extension {file}.', file=sys.stderr)
            traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.author.send('This command cannot be used in private messages.')
    elif isinstance(error, commands.DisabledCommand):
        await ctx.author.send('Sorry. This command is disabled and cannot be used.')
    elif isinstance(error, commands.NotOwner):
        await ctx.author.send('Sorry. This command can\'t be used by you.')

    elif isinstance(error, commands.CommandInvokeError):
        original = error.original
        if not isinstance(original, discord.HTTPException):
            print(f'Error in {ctx.command.qualified_name}:', file=sys.stderr)
            traceback.print_tb(original.__traceback__)
            print(f'{original.__class__.__name__}: {original}', file=sys.stderr)

    elif isinstance(error, commands.ArgumentParsingError):
        await ctx.send(error)


if __name__ == '__main__':
    bot.run(token)
