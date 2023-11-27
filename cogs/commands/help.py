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
        embed = discord.Embed(colour=discord.Colour.blurple())
        embed.set_author(name=f'Welcome to {self.bot.user.name}', icon_url=self.bot.user.display_avatar.url)
        embed.description = f"{self.bot.user.name} is an open source bot specialising in reports!\n\n" \
                            "For a detailed list of commands, features and examples, visit my [Top.gg](https://top.gg/bot/950765718209720360) page!"
        embed.add_field(name="__Commands__", value=
        f'**/help** - Displays help menu.\n'
        f'**Report Message** - Right click a message, scroll to \'Apps\', then click me to report a user.\n'
        f'**Report User** - Right click a user, scroll to \'Apps\', then click me to report a message.\n'
        f'**Reset Report** - For moderators to reset a report\'s state.\n'
        f'**/report** - Used to report a user, as not all devices support context menus.\n'
        f'**/settings** - Used to setup the bot in your server.\n'
        f'**/about** - Some stats about the bot.\n'
        f'**/vote** - Shows your voting history.', inline=False)

        view = self.MiscCommandsButton(cog=self)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    class MiscCommandsButton(discord.ui.View):

        def __init__(self, timeout=None, cog=None):
            super().__init__(timeout=timeout)
            self.message = None
            self.cog = cog

            self.add_item(discord.ui.Button(label="Top.gg", emoji="<:topgg:963166927843364874>", url="https://top.gg/bot/950765718209720360"))
            self.add_item(discord.ui.Button(label="GitHub", emoji="<:github:962089212365111327>", url="https://github.com/Co0kei/Coffee-Bot"))
            self.add_item(discord.ui.Button(label="Invite", emoji="📩", url=discord.utils.oauth_url(cog.bot.user.id, permissions=discord.Permissions(8))))
            self.add_item(discord.ui.Button(label="Support", emoji="<:Discord:853958437847564298>", url="https://discord.gg/rcUzqaQN8k"))
            # self.remove_item(self.miscCommands)  # reorder
            # self.add_item(self.miscCommands)

        # async def on_timeout(self) -> None:
        #     self.remove_item(self.miscCommands)
        #     await self.message.edit(view=self)

        async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        # @discord.ui.button(label='Misc Commands', emoji="\U00002755", style=discord.ButtonStyle.blurple)
        # async def miscCommands(self, interaction: discord.Interaction, button: discord.ui.Button):
        #
        #     if interaction.guild:
        #         prefix = self.cog.bot.get_cog('SettingsCommand').getPrefix(interaction.guild)
        #     else:
        #         prefix = self.cog.bot.default_prefix
        #
        #     prefix_commands = ""
        #     for command in self.cog.bot.get_cog('MetaCommands').walk_commands():
        #         cmd = f'**{prefix}{command.name}'
        #         if command.usage:
        #             cmd += f' {command.usage}'
        #         cmd += "**"
        #         if command.aliases:
        #             cmd += f" - ({', '.join(command.aliases)})"
        #         cmd += f" - {command.description}\n"
        #         prefix_commands += cmd
        #
        #     embed = discord.Embed(colour=discord.Colour.blurple())
        #     embed.description = f"**__Misc Commands__**\n{prefix_commands}"
        #     embed.set_footer(text="You can configure the prefix in the /settings command")
        #     await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
