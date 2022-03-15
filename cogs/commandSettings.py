import logging

import discord
from discord import ui, app_commands
from discord.ext import commands

import dev_server

log = logging.getLogger(__name__)


class SettingsCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='settings', description='Configure how the bot works in your server.')
    async def globalSettingsCommand(self, interaction: discord.Interaction):
        await self.handleSettingsCommand(interaction)

    @app_commands.command(name='devsettings', description='Dev - Configure how Coffee Bot is setup in your server.')
    @app_commands.guilds(discord.Object(id=dev_server.DEV_SERVER_ID))
    async def devSettingsCommand(self, interaction: discord.Interaction):
        await self.handleSettingsCommand(interaction)

    # Methods
    def checkValidChannel(self, reportsChannel: str, guild: discord.Guild) -> discord.TextChannel:
        if reportsChannel.startswith("#"):
            reportsChannel = reportsChannel[1:]

        reportsChannel = reportsChannel.replace(' ', '-')

        channel = None
        for textChannel in guild.text_channels:
            if textChannel.name == reportsChannel.lower() or str(textChannel.id) == reportsChannel:
                channel = textChannel
                break

        return channel

    def checkValidRole(self, role: str, guild: discord.Guild) -> discord.Role:
        if role.startswith("@"):
            role = role[1:]

        roleFound = None
        for guild_role in guild.roles:
            if guild_role.name.lower() == role.lower() or str(guild_role.id) == role:
                roleFound = guild_role
                break

        return roleFound

    def getSettingsEmbed(self, guild: discord.Guild) -> discord.Embed:
        if str(guild.id) in self.bot.guild_settings:

            if "reports_channel_id" in self.bot.guild_settings[str(guild.id)]:
                reports_channel = guild.get_channel(
                    self.bot.guild_settings[str(guild.id)]["reports_channel_id"])
                if reports_channel is None:
                    reports_channel = "None"
                else:
                    reports_channel = reports_channel.mention
            else:
                reports_channel = "None"

            if "reports_alert_role_id" in self.bot.guild_settings[str(guild.id)]:
                reports_alert_role = guild.get_role(
                    self.bot.guild_settings[str(guild.id)]["reports_alert_role_id"])
                if reports_alert_role is None:
                    reports_alert_role = "None"
                else:
                    reports_alert_role = reports_alert_role.mention
            else:
                reports_alert_role = "None"

            if "reports_banned_role_id" in self.bot.guild_settings[str(guild.id)]:
                reports_banned_role_id = guild.get_role(
                    self.bot.guild_settings[str(guild.id)]["reports_banned_role_id"])
                if reports_banned_role_id is None:
                    reports_banned_role_id = "None"
                else:
                    reports_banned_role_id = reports_banned_role_id.mention
            else:
                reports_banned_role_id = "None"

        else:
            reports_channel = "None"
            reports_alert_role = "None"
            reports_banned_role_id = "None"

        embed = discord.Embed(title="Settings",
                              description=f'Click a button to edit the value.')

        embed.add_field(name="Reports Channel",
                        value=f"Which channel should I send reports to?\nValue: {reports_channel}", inline=False)
        embed.add_field(name="Reports Alert Role",
                        value=f"Would you like a role to get pinged each time a report is received?\nValue: {reports_alert_role}",
                        inline=False)
        embed.add_field(name="Reports Banned Role",
                        value=f"Would you like a role that prevents members with it from creating reports?\nValue: {reports_banned_role_id}",
                        inline=False)
        embed.colour = discord.Colour(0x2F3136)

        return embed

    async def handleSettingsCommand(self, interaction: discord.Interaction):

        if interaction.guild is None:
            await interaction.response.send_message("Please use this command in a Discord server.")
            return

        # check permissions is admin or manage server
        member = interaction.guild.get_member(interaction.user.id)

        if not member.guild_permissions.administrator and not member.guild_permissions.manage_guild:
            await interaction.response.send_message("You must have the manage server permission to use this.",
                                                    ephemeral=True)
            return

        view = self.SettingButtons(bot=self.bot,
                                   userID=interaction.user.id,
                                   settingsCog=self)

        await interaction.response.send_message(embed=self.getSettingsEmbed(interaction.guild), ephemeral=False,
                                                view=view)
        msg = await interaction.original_message()
        view.setOriginalMessage(msg)  # pass the original message into the class

    # BUTTONS ON EMBED

    class SettingButtons(discord.ui.View):
        """ The buttons which are on the settings page """

        def __init__(self, timeout=120, bot=None, userID=None, settingsCog=None):
            super().__init__(timeout=timeout)

            self.message = None  # the original interaction message
            self.userID = userID  # the user which is allowed to click the buttons
            self.bot = bot  # the main bot instance

            self.settingCog = settingsCog  # instance of the outer class

        def setOriginalMessage(self, message: discord.Message):
            self.message = message

        async def on_timeout(self) -> None:
            await self.message.edit(view=None)

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id == self.userID:
                return True
            else:
                await interaction.response.send_message("Sorry, you cannot use this.", ephemeral=True)
                return False

        async def reloadSettingsEmbed(self):
            await self.message.edit(embed=self.settingCog.getSettingsEmbed(self.message.guild))

        @discord.ui.button(label='Reports Channel', style=discord.ButtonStyle.green)
        async def reportsChannel(self, button: discord.ui.Button, interaction: discord.Interaction):
            reportsChannelModel = self.settingCog.ReportsChannelModel(self.bot, self)
            await interaction.response.send_modal(reportsChannelModel)

        @discord.ui.button(label='Reports Alert Role', style=discord.ButtonStyle.green)
        async def reportsAlertRole(self, button: discord.ui.Button, interaction: discord.Interaction):
            reportsAlertRoleModel = self.settingCog.ReportsAlertRoleModel(self.bot, self)
            await interaction.response.send_modal(reportsAlertRoleModel)

        @discord.ui.button(label='Reports Banned Role', style=discord.ButtonStyle.green)
        async def reportsBannedRole(self, button: discord.ui.Button, interaction: discord.Interaction):
            reportsBannedRoleModel = self.settingCog.ReportsBannedRoleModel(self.bot, self)
            await interaction.response.send_modal(reportsBannedRoleModel)

        @discord.ui.button(label='Finish', style=discord.ButtonStyle.grey)
        async def finish(self, button: discord.ui.Button, interaction: discord.Interaction):
            await self.on_timeout()
            self.stop()

        # @discord.ui.button(label='Report Bots', style=discord.ButtonStyle.green, emoji="")
        # async def finish(self, button: discord.ui.Button, interaction: discord.Interaction):
        #     await self.on_timeout()
        #     self.stop()

    # MODALS

    class ReportsChannelModel(ui.Modal, title="Reports Channel"):
        """ The modal that asks you to enter a channel for reports to get sent to"""

        def __init__(self, bot=None, settingButtons=None):
            super().__init__()
            self.bot = bot
            self.settingsButtons = settingButtons

        channel = ui.TextInput(label='Reports Channel', style=discord.TextStyle.short,
                               placeholder="Please enter the channel name, such as #reports",
                               required=True, max_length=1000)

        async def on_submit(self, interaction: discord.Interaction):

            reportsChannel = self.channel.value
            channel = self.settingsButtons.settingCog.checkValidChannel(reportsChannel, interaction.guild)

            if channel is None:
                embed = discord.Embed(title="Channel not found", description="Please enter a valid channel name.",
                                      colour=discord.Colour.dark_red())
            else:

                embed = discord.Embed(title="Reports Channel Updated")
                embed.description = f"Successfully updated the reports channel to {channel.mention}"
                embed.colour = discord.Colour.green()

                if not str(interaction.guild.id) in self.bot.guild_settings:
                    self.bot.guild_settings[str(interaction.guild.id)] = {}

                self.bot.guild_settings[str(interaction.guild.id)]["reports_channel_id"] = channel.id

                await self.settingsButtons.reloadSettingsEmbed()

            await interaction.response.send_message(embed=embed, ephemeral=True)

    class ReportsAlertRoleModel(ui.Modal, title="Reports Alert Role"):
        """ The modal that asks you to enter a role name for each report to tag"""

        def __init__(self, bot=None, settingButtons=None):
            super().__init__()
            self.bot = bot
            self.settingsButtons = settingButtons

        role = ui.TextInput(label='Alert Role', style=discord.TextStyle.short,
                            placeholder="Please enter the role name, such as @reports",
                            required=True, max_length=1000)

        async def on_submit(self, interaction: discord.Interaction):

            reportsAlertRole = self.role.value
            role = self.settingsButtons.settingCog.checkValidRole(reportsAlertRole, interaction.guild)

            if role is None:
                embed = discord.Embed(title="Role not found", description="Please enter a valid role name.",
                                      colour=discord.Colour.dark_red())
            else:
                embed = discord.Embed(title="Reports Alert Role Updated")
                embed.description = f"Successfully updated the reports alert role to {role.mention}"
                embed.colour = discord.Colour.green()

                if not str(interaction.guild.id) in self.bot.guild_settings:
                    self.bot.guild_settings[str(interaction.guild.id)] = {}

                self.bot.guild_settings[str(interaction.guild.id)]["reports_alert_role_id"] = role.id

                await self.settingsButtons.reloadSettingsEmbed()

            await interaction.response.send_message(embed=embed, ephemeral=True)

    class ReportsBannedRoleModel(ui.Modal, title="Reports Banned Role"):
        """ The modal that asks you to enter a role name for a role that prevents users from making reports """

        def __init__(self, bot=None, settingButtons=None):
            super().__init__()
            self.bot = bot
            self.settingsButtons = settingButtons

        role = ui.TextInput(label='Banned Role', style=discord.TextStyle.short,
                            placeholder="Please enter the role name, such as @banned from reports",
                            required=True, max_length=1000)

        async def on_submit(self, interaction: discord.Interaction):

            reportsBannedRole = self.role.value
            role = self.settingsButtons.settingCog.checkValidRole(reportsBannedRole, interaction.guild)

            if role is None:
                embed = discord.Embed(title="Role not found", description="Please enter a valid role name.",
                                      colour=discord.Colour.dark_red())
            else:
                embed = discord.Embed(title="Reports Banned Role Updated")
                embed.description = f"Successfully updated the reports banned role to {role.mention}"
                embed.colour = discord.Colour.green()

                if not str(interaction.guild.id) in self.bot.guild_settings:
                    self.bot.guild_settings[str(interaction.guild.id)] = {}

                self.bot.guild_settings[str(interaction.guild.id)]["reports_banned_role_id"] = role.id

                await self.settingsButtons.reloadSettingsEmbed()

            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(SettingsCommand(bot))
