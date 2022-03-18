import logging

import discord
from discord import app_commands
from discord.ext import commands

import dev_server

log = logging.getLogger(__name__)


class HelpCommand(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(name='help', description='Information on commands & bot setup.')
    async def globalHelpCommand(self, interaction: discord.Interaction):
        await self.handleHelpCommand(interaction)

    @app_commands.command(name='devhelp', description='Dev - Information on commands & bot setup.')
    @app_commands.guilds(discord.Object(id=dev_server.DEV_SERVER_ID))
    async def devHelpCommand(self, interaction: discord.Interaction):
        await self.handleHelpCommand(interaction)

    async def handleHelpCommand(self, interaction: discord.Interaction):
        embed = discord.Embed()
        embed.title = 'Official Bot Server Invite'
        embed.url = 'https://discord.gg/rcUzqaQN8k'
        embed.colour = discord.Colour.blurple()

        embed.add_field(name="__Commands__", value=
        f'**/help** - Displays help menu.\n'
        f'**Report Message** - Right click a message, scroll to \'Apps\', then click me to report a user.\n'
        f'**Report User** - Right click a user, scroll to \'Apps\', then click me to report a message.\n'
        f'**/report** - Used to report a user, as mobile devices do not support context menus.\n'
        f'**/settings** - Used to setup the bot in your server.\n'
        f'**/about** - Some stats about the bot.\n'
        f'**/vote** - Shows your voting history.', inline=False)

        embed.add_field(name="__Setup__", value=
        f'1. First invite me to your server, using the button on my profile.\n'
        f'2. Use the /settings command and enter a channel name for reports to be sent to.\n'
        f'3. Now you can right click on a user or message then scroll to \'Apps\' and click the report button!\n'
        f'\n'
        f'**NOTE:** Members must have the \'Use Application Commands\' permission. Also Discord is sometimes weird so if no \'Apps\' section is showing after you right click a message or user, then do CTRL + R to reload your Discord',
                        inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
