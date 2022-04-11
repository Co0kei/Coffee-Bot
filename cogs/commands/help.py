import logging

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)


class HelpCommand(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(name='help', description='Discover what I can do!')
    async def globalHelpCommand(self, interaction: discord.Interaction):
        await self.handleHelpCommand(interaction)

    async def handleHelpCommand(self, interaction: discord.Interaction):
        embed = discord.Embed()
        embed.colour = discord.Colour.blurple()
        embed.set_author(name=f'Welcome to {self.bot.user.name}', icon_url=self.bot.user.display_avatar.url)
        embed.description = f"{self.bot.user.name} is an open source bot specialising in reports!\n\n" \
                            "For a detailed list of commands, features and examples, visit my [Top.gg](https://top.gg/bot/950765718209720360) page!"
        embed.add_field(name="__Commands__", value=
        f'**/help** - Displays help menu.\n'
        f'**Report Message** - Right click a message, scroll to \'Apps\', then click me to report a user.\n'
        f'**Report User** - Right click a user, scroll to \'Apps\', then click me to report a message.\n'
        f'**/report** - Used to report a user, as mobile devices do not support context menus.\n'
        f'**/settings** - Used to setup the bot in your server.\n'
        f'**/about** - Some stats about the bot.\n'
        f'**/vote** - Shows your voting history.', inline=False)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Top.gg", emoji="<:topgg:963166927843364874>", url="https://top.gg/bot/950765718209720360"))
        view.add_item(discord.ui.Button(label="GitHub", emoji="<:github:962089212365111327>", url="https://github.com/Co0kei/Coffee-Bot"))
        view.add_item(discord.ui.Button(label="Invite", emoji="📩", url=discord.utils.oauth_url(self.bot.user.id, permissions=discord.Permissions(8))))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)


async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
