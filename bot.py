import json
import logging
import sys
import traceback

import discord
from discord.ext import commands

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%I:%M:%S %p')

log = logging.getLogger(__name__)

# Define bot
dev_server_id = 759418498228158465

bot = commands.Bot(command_prefix=['-'], description="A discord bot!", owner_id=452187819738267687,
                   case_insensitive=True,
                   allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, users=True,
                                                            replied_user=False),
                   intents=discord.Intents.all(), help_command=None)
tree = bot.tree  # app_commands.CommandTree(bot)


# Interactions - GLOBAL

# Report message
@tree.context_menu(name='Report Message')
async def globalReportMessage(interaction: discord.Interaction, message: discord.Message):
    await bot.get_cog("InteractionsCog").handleMessageReport(interaction, message)


# Report User
@tree.context_menu(name='Report User')
async def globalReportUser(interaction: discord.Interaction, member: discord.Member):
    await bot.get_cog("InteractionsCog").handleUserReport(interaction, member)


# Reports command
@tree.command(name='report', description='Report a member with a reason for staff to see.')
@discord.app_commands.describe(member='The member you are reporting.')
async def globalReportCommand(interaction: discord.Interaction, member: discord.User):
    await bot.get_cog("InteractionsCog").handleUserReport(interaction, member)


# Help command
@tree.command(name='help', description='Information on commands & bot setup')
async def globalHelpCommand(interaction: discord.Interaction):
    await bot.get_cog("InteractionsCog").handleHelpCommand(interaction)


# Interactions - dev server

# Report message
@tree.context_menu(name='Dev - Report Message', guild=discord.Object(id=dev_server_id))
async def devReportMessage(interaction: discord.Interaction, message: discord.Message):
    await bot.get_cog("InteractionsCog").handleMessageReport(interaction, message)


# Report User
@tree.context_menu(name='Dev - Report User', guild=discord.Object(id=dev_server_id))
async def devReportUser(interaction: discord.Interaction, member: discord.Member):
    await bot.get_cog("InteractionsCog").handleUserReport(interaction, member)


# Reports command
@tree.command(name='devreport', description='Report a member with a reason for staff to see.',
              guild=discord.Object(id=dev_server_id))
@discord.app_commands.describe(member='The member you are reporting.')
async def devReportCommand(interaction: discord.Interaction, member: discord.User):
    await bot.get_cog("InteractionsCog").handleUserReport(interaction, member)


# Help command
@tree.command(name='devhelp', description='Information on commands & bot setup',
              guild=discord.Object(id=dev_server_id))
async def devHelpCommand(interaction: discord.Interaction):
    await bot.get_cog("InteractionsCog").handleHelpCommand(interaction)


# Msg commands
@commands.is_owner()
@bot.command()
async def sync(ctx):
    await ctx.send("processing")
    a = await tree.sync(guild=discord.Object(id=dev_server_id))
    await ctx.message.reply("Dev server interactions synced: " + str(a))


@commands.is_owner()
@bot.command()
async def globalsync(ctx):
    await ctx.send("processing global sync")
    a = await tree.sync()
    await ctx.message.reply("Global interaction sync done: " + str(a))


# Events
@bot.event
async def on_ready():
    log.info('Bot online!')
    log.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    log.info(f'Connected to {(len(bot.guilds))} Discord Servers.')

    bot.uptime = discord.utils.utcnow()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.author.send('This command cannot be used in private messages.')
    elif isinstance(error, commands.DisabledCommand):
        await ctx.author.send('Sorry. This command is disabled and cannot be used.')

    elif isinstance(error, commands.NotOwner):
        await ctx.author.send('Sorry. This command can\'t be used my you.')

    elif isinstance(error, commands.CommandInvokeError):
        original = error.original
        if not isinstance(original, discord.HTTPException):
            print(f'Error in {ctx.command.qualified_name}:', file=sys.stderr)
            traceback.print_tb(original.__traceback__)
            print(f'{original.__class__.__name__}: {original}', file=sys.stderr)

    elif isinstance(error, commands.ArgumentParsingError):
        await ctx.send(error)


# Load extensions
initial_extensions = (
    'cogs.owner',
    'cogs.interactions'
)

for extension in initial_extensions:
    try:
        bot.load_extension(extension)
    except Exception as e:
        print(f'Failed to load extension {extension}.', file=sys.stderr)
        traceback.print_exc()

# Retrieve token and start bot
with open('config.json', 'r') as f:
    botsettings = json.load(f)
    token = botsettings["token"]
    f.close()

bot.run(token)
