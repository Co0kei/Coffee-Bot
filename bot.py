#Discord imports
import discord
from discord.ext import commands

#Other imports
import json


# Define bot
bot = commands.Bot(command_prefix = ['-'], reconnect=True, case_insensitive=True, intents = discord.Intents.all())
bot.remove_command('help')

@bot.event
async def on_ready():
    print('Bot online!')


# Retrieve token and start bot
with open('config.json', 'r') as f:
    botsettings = json.load(f)
    token = botsettings["token"]
    f.close()

bot.run(token)
