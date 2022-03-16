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

    def isReportSelfEnabled(self, guild: discord.Guild) -> bool:
        report_self = True

        if str(guild.id) in self.bot.guild_settings:
            if "report_self" in self.bot.guild_settings[str(guild.id)]:
                report_self = self.bot.guild_settings[str(guild.id)]["report_self"]
        return report_self

    def isReportBotsEnabled(self, guild: discord.Guild) -> bool:
        report_bots = True

        if str(guild.id) in self.bot.guild_settings:
            if "report_bots" in self.bot.guild_settings[str(guild.id)]:
                report_bots = self.bot.guild_settings[str(guild.id)]["report_bots"]
        return report_bots

    def isReportAdminsEnabled(self, guild: discord.Guild) -> bool:
        report_admins = True

        if str(guild.id) in self.bot.guild_settings:
            if "report_admins" in self.bot.guild_settings[str(guild.id)]:
                report_admins = self.bot.guild_settings[str(guild.id)]["report_admins"]
        return report_admins

    def getSettingsEmbed(self, guild: discord.Guild) -> discord.Embed:

        reports_channel = "`None`"
        reports_alert_role = "`None`"
        reports_banned_role_id = "`None`"

        report_self = self.isReportSelfEnabled(guild)
        report_bots = self.isReportBotsEnabled(guild)
        report_admins = self.isReportAdminsEnabled(guild)

        if str(guild.id) in self.bot.guild_settings:

            if "reports_channel_id" in self.bot.guild_settings[str(guild.id)]:
                reports_channel = guild.get_channel(self.bot.guild_settings[str(guild.id)]["reports_channel_id"])
                if reports_channel is None:
                    reports_channel = "`None`"
                else:
                    reports_channel = reports_channel.mention

            if "reports_alert_role_id" in self.bot.guild_settings[str(guild.id)]:
                reports_alert_role = guild.get_role(self.bot.guild_settings[str(guild.id)]["reports_alert_role_id"])
                if reports_alert_role is None:
                    reports_alert_role = "`None`"
                else:
                    reports_alert_role = reports_alert_role.mention

            if "reports_banned_role_id" in self.bot.guild_settings[str(guild.id)]:
                reports_banned_role_id = guild.get_role(
                    self.bot.guild_settings[str(guild.id)]["reports_banned_role_id"])
                if reports_banned_role_id is None:
                    reports_banned_role_id = "`None`"
                else:
                    reports_banned_role_id = reports_banned_role_id.mention

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

        embed.add_field(name="\uFEFF",
                        value=f"Allow members to report themselves? `{report_self}`\n"
                              f"Allow members to report bots? `{report_bots}`\n"
                              f"Allow members to report server admins? `{report_admins}`",
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
        for item in view.children:
            if item.label == "Report Self":
                if self.isReportSelfEnabled(interaction.guild):
                    item.style = discord.ButtonStyle.green
                else:
                    item.style = discord.ButtonStyle.red
            if item.label == "Report Bots":
                if self.isReportBotsEnabled(interaction.guild):
                    item.style = discord.ButtonStyle.green
                else:
                    item.style = discord.ButtonStyle.red
            if item.label == "Report Admins":
                if self.isReportAdminsEnabled(interaction.guild):
                    item.style = discord.ButtonStyle.green
                else:
                    item.style = discord.ButtonStyle.red

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

        @discord.ui.button(label='Report Self', row=1)
        async def reportSelf(self, button: discord.ui.Button, interaction: discord.Interaction):
            report_self = True  # default

            if str(interaction.guild.id) in self.bot.guild_settings:
                if "report_self" in self.bot.guild_settings[str(interaction.guild.id)]:
                    report_self = self.bot.guild_settings[str(interaction.guild.id)]["report_self"]
            else:
                self.bot.guild_settings[str(interaction.guild.id)] = {}

            if report_self:
                embed = discord.Embed(title="Self Report Disabled")
                embed.description = "Members can no longer report themselves."
                embed.colour = discord.Colour.dark_red()
                button.style = discord.ButtonStyle.red

            else:
                embed = discord.Embed(title="Self Report Enabled")
                embed.description = "Members can now report themselves."
                embed.colour = discord.Colour.green()
                button.style = discord.ButtonStyle.green

            self.bot.guild_settings[str(interaction.guild.id)]["report_self"] = not report_self
            await self.message.edit(view=self)
            await self.reloadSettingsEmbed()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            # print(self.bot.guild_settings)

        @discord.ui.button(label='Report Bots', row=1)
        async def reportBots(self, button: discord.ui.Button, interaction: discord.Interaction):
            report_bots = True  # default

            if str(interaction.guild.id) in self.bot.guild_settings:
                if "report_bots" in self.bot.guild_settings[str(interaction.guild.id)]:
                    report_bots = self.bot.guild_settings[str(interaction.guild.id)]["report_bots"]
            else:
                self.bot.guild_settings[str(interaction.guild.id)] = {}

            if report_bots:
                embed = discord.Embed(title="Bot Reports Disabled")
                embed.description = "Members can no longer report bots."
                embed.colour = discord.Colour.dark_red()
                button.style = discord.ButtonStyle.red

            else:
                embed = discord.Embed(title="Bot Reports Enabled")
                embed.description = "Members can now report bots."
                embed.colour = discord.Colour.green()
                button.style = discord.ButtonStyle.green

            self.bot.guild_settings[str(interaction.guild.id)]["report_bots"] = not report_bots
            await self.message.edit(view=self)
            await self.reloadSettingsEmbed()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            # print(self.bot.guild_settings)

        @discord.ui.button(label='Report Admins', row=1)
        async def reportAdmins(self, button: discord.ui.Button, interaction: discord.Interaction):
            report_admins = True  # default

            if str(interaction.guild.id) in self.bot.guild_settings:
                if "report_admins" in self.bot.guild_settings[str(interaction.guild.id)]:
                    report_admins = self.bot.guild_settings[str(interaction.guild.id)]["report_admins"]
            else:
                self.bot.guild_settings[str(interaction.guild.id)] = {}

            if report_admins:
                embed = discord.Embed(title="Admin Reports Disabled")
                embed.description = "Members can no longer report server admins."
                embed.colour = discord.Colour.dark_red()
                button.style = discord.ButtonStyle.red

            else:
                embed = discord.Embed(title="Admin Reports Enabled")
                embed.description = "Members can now report server admins."
                embed.colour = discord.Colour.green()
                button.style = discord.ButtonStyle.green

            self.bot.guild_settings[str(interaction.guild.id)]["report_admins"] = not report_admins
            await self.message.edit(view=self)
            await self.reloadSettingsEmbed()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            # print(self.bot.guild_settings)

        @discord.ui.button(label='Finish', style=discord.ButtonStyle.grey, row=1)
        async def finish(self, button: discord.ui.Button, interaction: discord.Interaction):
            await self.on_timeout()
            self.stop()

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

            if reportsChannel.lower() == "none" or reportsChannel.lower() == "reset":
                embed = discord.Embed(title="Channel reset", description="You have removed the Alert Channel.",
                                      colour=discord.Colour.green())
                if str(interaction.guild.id) in self.bot.guild_settings:
                    if "reports_channel_id" in self.bot.guild_settings[str(interaction.guild.id)]:
                        del self.bot.guild_settings[str(interaction.guild.id)]["reports_channel_id"]

                await self.settingsButtons.reloadSettingsEmbed()

            elif channel is None:
                embed = discord.Embed(title="Channel not found",
                                      description="Please enter a valid channel name.\nTo remove the current channel, enter `reset` instead of a channel name.",
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
            # print(self.bot.guild_settings)

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

            if reportsAlertRole.lower() == "none" or reportsAlertRole.lower() == "reset":
                embed = discord.Embed(title="Role reset", description="You have removed the Alert Role.",
                                      colour=discord.Colour.green())
                if str(interaction.guild.id) in self.bot.guild_settings:
                    if "reports_alert_role_id" in self.bot.guild_settings[str(interaction.guild.id)]:
                        del self.bot.guild_settings[str(interaction.guild.id)]["reports_alert_role_id"]

                await self.settingsButtons.reloadSettingsEmbed()

            elif role is None:
                embed = discord.Embed(title="Role not found",
                                      description="Please enter a valid role name.\nTo remove the current role, enter `reset` instead of a role name.",
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

            # print(self.bot.guild_settings)

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

            if reportsBannedRole.lower() == "none" or reportsBannedRole.lower() == "reset":
                embed = discord.Embed(title="Role reset", description="You have removed the Banned Role.",
                                      colour=discord.Colour.green())
                if str(interaction.guild.id) in self.bot.guild_settings:
                    if "reports_banned_role_id" in self.bot.guild_settings[str(interaction.guild.id)]:
                        del self.bot.guild_settings[str(interaction.guild.id)]["reports_banned_role_id"]

                await self.settingsButtons.reloadSettingsEmbed()

            elif role is None:
                embed = discord.Embed(title="Role not found",
                                      description="Please enter a valid role name.\nTo remove the current role, enter `reset` instead of a role name.",
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
            # print(self.bot.guild_settings)


async def setup(bot):
    await bot.add_cog(SettingsCommand(bot))
