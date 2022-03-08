# Discord imports
import json
# Other imports
import logging
import sys
import traceback

import discord
from discord import app_commands
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
tree = app_commands.CommandTree(bot)


# Interactions
@tree.context_menu(name='Report User', guild=discord.Object(id=dev_server_id))
async def reportUser(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message('Done', ephemeral=True)


@tree.context_menu(name='Report Message', guild=discord.Object(id=dev_server_id))
async def reportMessage(interaction: discord.Interaction, message: discord.Message):
    if not message.content:
        await interaction.response.send_message('No content!', ephemeral=True)
        return

    await interaction.response.send_message("Done", ephemeral=True)


@tree.command(name='report', guild=discord.Object(id=dev_server_id))
async def reportCommand(interaction: discord.Interaction, member: discord.Member, reason: str):
    await interaction.response.send_message(f'{member=} {reason=}', ephemeral=True)


# A command
@commands.is_owner()
@bot.command()
async def sync(ctx):
    await tree.sync(guild=discord.Object(id=759418498228158465))
    await ctx.message.reply("done")


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
    'cogs.other'
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
