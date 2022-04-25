import enum
import logging
import re
from typing import Optional, List

import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands
from discord.ext.commands import Bot
from discord.ui import Button

log = logging.getLogger(__name__)


class SettingPage(enum.Enum):
    """ An enum of the pages in the /settings command"""
    Reports = 1
    Moderation = 2
    Logs = 3
    Misc = 4


class SettingsCommand(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(name='settings', description='Configure how I work in your server.')
    async def globalSettingsCommand(self, interaction: discord.Interaction):

        if interaction.guild is None:
            return await interaction.response.send_message("Please use this command in a Discord server.")

        member = interaction.guild.get_member(interaction.user.id)
        if not member.guild_permissions.manage_guild:
            return await interaction.response.send_message("You must have the `Manage Server` permission to use this.", ephemeral=True)

        guild = interaction.guild
        guild_id = guild.id

        if str(guild_id) not in self.bot.guild_settings:
            # Attempt to add guild to database
            query = "INSERT INTO guilds(guild_id) VALUES($1) ON CONFLICT(guild_id) DO NOTHING;"
            async with self.bot.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(query, interaction.guild.id)
                    log.info(f"Guild added to database: {guild_id}")
                    self.bot.guild_settings[str(guild_id)] = {}

        embed = self.getEmbed(guild, SettingPage.Reports)
        view = self.SettingsView(bot=self.bot,
                                 author_id=interaction.user.id,
                                 guild=guild,
                                 cog=self)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_message()  # set message in view

    #  Main View & dropdown
    class SettingsView(discord.ui.View):

        def __init__(self, *, timeout: float = 120, bot: Bot, author_id: int, guild: discord.Guild, cog) -> None:
            super().__init__(timeout=timeout)

            self.message: Optional[discord.Message] = None  # the original interaction message
            self.author_id: int = author_id  # the user id which is allowed to click the buttons
            self.guild: discord.Guild = guild
            self.bot = bot  # the main bot instance
            self.cog = cog  # instance of the outer cog class
            self.page: SettingPage = SettingPage.Reports  # default to reports page

            self.dropdown = self.cog.Dropdown(message=self.message,
                                              cog=self.cog,
                                              settingsView=self)
            self.updateButtons()

        async def on_timeout(self) -> None:
            await self.message.edit(view=None)

        async def on_error(self, error: Exception, item: discord.ui.Item, interaction: discord.Interaction) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user and interaction.user.id in (self.bot.owner_id, self.author_id):
                return True
            await interaction.response.send_message("Sorry, you cannot use this.", ephemeral=True)
            return False

        def updateButtons(self):
            """ Sets buttons for the current category"""
            buttons: List[Button] = self.cog.getButtons(self.guild, self.page)
            self.clear_items()
            self.add_item(self.dropdown)
            for button in buttons:
                button.label = button.custom_id
                callback = self.callback
                button.callback = callback
                self.add_item(button)

        async def refreshEmbed(self, interaction: discord.Interaction = None, reloadView=False):
            """ Used to reload values in the embed after a setting is changed """
            embed = self.cog.getEmbed(self.guild, self.page)
            if interaction:
                if reloadView:
                    self.updateButtons()
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    await interaction.response.edit_message(embed=embed)
            else:
                await self.message.edit(embed=embed)

        async def callback(self, interaction: discord.Interaction):
            """ This is called each time any button is clicked """
            # button = self.buttons[interaction.data["custom_id"]]
            button = interaction.data["custom_id"]

            # reports
            if button == "Reports Channel":
                model = self.cog.ReportsChannelModel(self.bot, self)
                await interaction.response.send_modal(model)
            elif button == "Reports Alert Role":
                model = self.cog.ReportsAlertRoleModel(self.bot, self)
                await interaction.response.send_modal(model)
            elif button == "Reports Banned Role":
                model = self.cog.ReportsBannedRoleModel(self.bot, self)
                await interaction.response.send_modal(model)
            elif button == "Report Self":
                await self.cog.toggleReportSelf(interaction, self)
            elif button == "Report Bots":
                await self.cog.toggleReportBots(interaction, self)
            elif button == "Report Admins":
                await self.cog.toggleReportAdmins(interaction, self)

            # moderation
            elif button == "Invite Filter":
                await self.cog.toggleInviteFilter(interaction, self)
            elif button == "Link Filter":
                await self.cog.toggleLinkFilter(interaction, self)
            elif button == "Whitelisted Links":
                model = self.cog.WhitelistedLinkModel(self.bot, self)
                await interaction.response.send_modal(model)
            elif button == "Chat Filter":
                model = self.cog.ChatFilterModel(self.bot, self)
                await interaction.response.send_modal(model)
            elif button == "Mod Log Channel":
                model = self.cog.ModLogChannelModel(self.bot, self)
                await interaction.response.send_modal(model)

            # logs
            elif button == "Message Delete":
                model = self.cog.MessageDeleteChannelModel(self.bot, self)
                await interaction.response.send_modal(model)
            elif button == "Mod Message Delete":
                model = self.cog.ModMessageDeleteChannelModel(self.bot, self)
                await interaction.response.send_modal(model)
            elif button == "Message Edit":
                model = self.cog.MessageEditChannelModel(self.bot, self)
                await interaction.response.send_modal(model)

            # misc
            elif button == "Prefix":
                prefixModel = self.cog.PrefixModel(self.bot, self)
                await interaction.response.send_modal(prefixModel)

            else:
                await interaction.response.send_message(f"{button}. This has not been implemented yet.", ephemeral=True)

    class Dropdown(discord.ui.Select):
        def __init__(self, *, message: discord.Message, cog, settingsView) -> None:
            self.message = message
            self.cog = cog
            self.settingsView = settingsView

            options = [
                discord.SelectOption(label='Select Page', emoji="<:dropdownselect:965687947582111784>", default=True),

                discord.SelectOption(label='Reports', description='Setup how reports are handled', emoji='<:admin:965698068831944734>'),
                discord.SelectOption(label='Moderation', description='Setup moderation', emoji='<:moderation:965698068706119730>'),
                discord.SelectOption(label='Logs', description='Setup extensive audit logging', emoji='<:logs:966670156925390928>'),
                discord.SelectOption(label='Misc', description='Setup miscellaneous properties', emoji='<:settings:966670162877087764>'),
            ]

            super().__init__(min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            page: SettingPage = SettingPage[self.values[0]]
            embed = self.cog.getEmbed(interaction.guild, page)
            self.settingsView.page = page
            self.settingsView.updateButtons()  # update buttons

            await interaction.response.edit_message(embed=embed, view=self.settingsView)  # update embed

    # Methods
    def getEmbed(self, guild: discord.Guild, type: SettingPage) -> discord.Embed:
        """ Returns the settings embed"""

        if type == SettingPage.Reports:
            embed = discord.Embed(title="Settings", description=f'Click a button to edit the value.', colour=discord.Colour.blurple())
            embed.set_author(name="Reports", icon_url="https://cdn.discordapp.com/attachments/878620836284747788/966669223134900224/dev2.png")

            reports_channel = self.getReportsChannel(guild)
            if reports_channel:
                reports_channel = reports_channel.mention
            else:
                reports_channel = "`None`"
            embed.add_field(name='<:channel:966662246581301308> **Reports Channel**',
                            value=f"_Description_: Set a channel for reports to get sent to.\n"
                                  f"_Value_: {reports_channel}", inline=False)

            reports_alert_role = self.getReportsAlertRole(guild)
            if reports_alert_role:
                reports_alert_role = reports_alert_role.mention
            else:
                reports_alert_role = "`None`"
            embed.add_field(name='<:role:966666974438490152> **Reports Alert Role**',
                            value=f"_Description_: Set a role to get pinged each time a report is received.\n"
                                  f"_Value_: {reports_alert_role}", inline=False)

            reports_banned_role = self.getReportsBannedRole(guild)
            if reports_banned_role:
                reports_banned_role = reports_banned_role.mention
            else:
                reports_banned_role = "`None`"
            embed.add_field(name='<:role:966664821527412857> **Reports Banned Role**',
                            value=f"_Description_: Set a role that prevents members with it from creating reports.\n"
                                  f"_Value_: {reports_banned_role}", inline=False)

            if self.isReportSelfEnabled(guild):
                report_self = "`Enabled` <:tick:873224615881748523>"
            else:
                report_self = "`Disabled` <:cross:872834807476924506>"
            embed.add_field(name='\U0001f465 **Report Self**',
                            value=f"_Description_: When enabled members can report themselves.\n"
                                  f"_Value_: {report_self}", inline=False)

            if self.isReportBotsEnabled(guild):
                report_bots = "`Enabled` <:tick:873224615881748523>"
            else:
                report_bots = "`Disabled` <:cross:872834807476924506>"
            embed.add_field(name='<:bot:966666994357248031> **Report Bots**',
                            value=f"_Description_: When enabled members can report bots.\n"
                                  f"_Value_: {report_bots}", inline=False)

            if self.isReportAdminsEnabled(guild):
                report_admins = "`Enabled` <:tick:873224615881748523>"
            else:
                report_admins = "`Disabled` <:cross:872834807476924506>"
            embed.add_field(name='<:admin:966668904313270322> **Report Admins**',
                            value=f"_Description_: When enabled members can report server admins.\n"
                                  f"_Value_: {report_admins}", inline=False)
            return embed

        elif type == SettingPage.Moderation:
            embed = discord.Embed(title="Settings", description=f'Click a button to edit the value.', colour=discord.Colour.blurple())
            embed.set_author(name="Moderation", icon_url="https://cdn.discordapp.com/attachments/878620836284747788/966669507856838676/moderation.png")

            if self.isInviteFilterEnabled(guild):
                invite_filter = "`Enabled` <:tick:873224615881748523>"
            else:
                invite_filter = "`Disabled` <:cross:872834807476924506>"
            embed.add_field(name='<:invite:966673137741729872> **Invite Filter**',
                            value=f"_Description_: When enabled members can't post Discord server invites.\n"
                                  f"_Value_: {invite_filter}", inline=False)

            if self.isLinkFilterEnabled(guild):
                link_filter = "`Enabled` <:tick:873224615881748523>"
            else:
                link_filter = "`Disabled` <:cross:872834807476924506>"
            embed.add_field(name='<:link:966673134033989645> **Link Filter**',
                            value=f"_Description_: When enabled members can only post whitelisted links.\n"
                                  f"_Value_: {link_filter}", inline=False)

            whitelisted_links = self.getWhitelistedLinks(guild)
            if whitelisted_links:
                whitelisted_links = f'`{", ".join(whitelisted_links)}`'
            else:
                whitelisted_links = "`None`"
            embed.add_field(name='<:Whitelist:966673595583586354> **Whitelisted Links**',
                            value=f"_Description_: Set links which members are allowed to post.\n"
                                  f"_Value_: {whitelisted_links}"[0:1024], inline=False)

            chat_filter = self.getChatFilter(guild)
            if chat_filter:
                chat_filter = f'||`{", ".join(chat_filter)}`||'
            else:
                chat_filter = "`None`"
            embed.add_field(name='<:chat:966783738547691520> **Chat Filter**',
                            value=f"_Description_: Set words which members can't use.\n"
                                  f"_Value_: {chat_filter}"[0:1024], inline=False)

            mod_log_channel = self.getModLogChannel(guild)
            if mod_log_channel:
                mod_log_channel = mod_log_channel.mention
            else:
                mod_log_channel = "`None`"
            embed.add_field(name='<:channel:966662246581301308> **Mod Log Channel**',
                            value=f"_Description_: Set a channel that notifies you of attempts to bypass the invite/link/chat filter.\n"
                                  f"_Value_: {mod_log_channel}", inline=False)
            return embed

        elif type == SettingPage.Logs:
            embed = discord.Embed(title="Settings", description=f'Click a button to edit the value.', colour=discord.Colour.blurple())
            embed.set_author(name="Logs", icon_url="https://cdn.discordapp.com/attachments/878620836284747788/966669748358250587/IconLogs.gif")

            msg_delete_channel = self.getMsgDeleteChannel(guild)
            if msg_delete_channel:
                msg_delete_channel = msg_delete_channel.mention
            else:
                msg_delete_channel = "`None`"
            embed.add_field(name=':grey_exclamation: **Message Delete**',
                            value=f"_Description_: Logs a deleted message when a member deletes their own message or a bot deletes their message.\n"
                                  f"_Value_: {msg_delete_channel}", inline=False)

            mod_msg_delete_channel = self.getModMsgDeleteChannel(guild)
            if mod_msg_delete_channel:
                mod_msg_delete_channel = mod_msg_delete_channel.mention
            else:
                mod_msg_delete_channel = "`None`"
            embed.add_field(name=':grey_exclamation: **Mod Message Delete**',
                            value=f"_Description_: Logs a deleted message when a human deletes another members message. Includes bulk message deletes.\n"
                                  f"_Value_: {mod_msg_delete_channel}", inline=False)

            msg_edit_channel = self.getMsgEditChannel(guild)
            if msg_edit_channel:
                msg_edit_channel = msg_edit_channel.mention
            else:
                msg_edit_channel = "`None`"
            embed.add_field(name=':grey_exclamation: **Message Edit**',
                            value=f"_Description_: Logs when a member edits their message.\n"
                                  f"_Value_: {msg_edit_channel}", inline=False)

            return embed

        elif type == SettingPage.Misc:
            embed = discord.Embed(title="Settings", description=f'Click a button to edit the value.', colour=discord.Colour.blurple())
            embed.set_author(name="Miscellaneous", icon_url="https://cdn.discordapp.com/attachments/878620836284747788/966669697149992990/Discord_settings.png")
            embed.add_field(name=':grey_exclamation: **Prefix**',
                            value=f"_Description_: Set the prefix for any non slash commands to respond to.\n"
                                  f"_Value_: `{self.getPrefix(guild)}`", inline=False)
            return embed

    def getButtons(self, guild: discord.Guild, type: SettingPage) -> List[discord.ui.Button]:
        """ Returns the buttons associated with the page """

        if type == SettingPage.Reports:
            return [
                discord.ui.Button(custom_id="Reports Channel", style=discord.ButtonStyle.blurple, emoji="<:channel:966662246581301308>", row=1),
                discord.ui.Button(custom_id="Reports Alert Role", style=discord.ButtonStyle.blurple, emoji="<:role:966666974438490152>", row=1),
                discord.ui.Button(custom_id="Reports Banned Role", style=discord.ButtonStyle.blurple, emoji="<:role:966664821527412857>", row=1),

                discord.ui.Button(custom_id="Report Self", style=discord.ButtonStyle.green if self.isReportSelfEnabled(guild) else discord.ButtonStyle.red, emoji="\U0001f465", row=2),
                discord.ui.Button(custom_id="Report Bots", style=discord.ButtonStyle.green if self.isReportBotsEnabled(guild) else discord.ButtonStyle.red, emoji="<:bot:966666994357248031>", row=2),
                discord.ui.Button(custom_id="Report Admins", style=discord.ButtonStyle.green if self.isReportAdminsEnabled(guild) else discord.ButtonStyle.red, emoji="<:admin:966668904313270322>",
                                  row=2)
            ]
        elif type == SettingPage.Moderation:
            return [
                discord.ui.Button(custom_id="Invite Filter", style=discord.ButtonStyle.green if self.isInviteFilterEnabled(guild) else discord.ButtonStyle.red, emoji="<:invite:966673137741729872>",
                                  row=1),
                discord.ui.Button(custom_id="Link Filter", style=discord.ButtonStyle.green if self.isLinkFilterEnabled(guild) else discord.ButtonStyle.red, emoji="<:link:966673134033989645>",
                                  row=1),
                discord.ui.Button(custom_id="Whitelisted Links", style=discord.ButtonStyle.blurple, emoji="<:Whitelist:966673595583586354>", row=1),
                discord.ui.Button(custom_id="Chat Filter", style=discord.ButtonStyle.blurple, emoji="<:chat:966783738547691520>", row=2),
                discord.ui.Button(custom_id="Mod Log Channel", style=discord.ButtonStyle.blurple, emoji="<:channel:966662246581301308>", row=2)
            ]
        elif type == SettingPage.Logs:
            return [
                discord.ui.Button(custom_id="Message Delete", style=discord.ButtonStyle.blurple, row=1),
                discord.ui.Button(custom_id="Mod Message Delete", style=discord.ButtonStyle.blurple, row=1),
                discord.ui.Button(custom_id="Message Edit", style=discord.ButtonStyle.blurple, row=1),
            ]

        elif type == SettingPage.Misc:
            return [
                discord.ui.Button(custom_id="Prefix", style=discord.ButtonStyle.blurple, emoji="\U00002755", row=1),
            ]

    def checkValidChannel(self, reportsChannel: str, guild: discord.Guild) -> discord.TextChannel:
        if reportsChannel.startswith("#"):
            reportsChannel = reportsChannel[1:]

        reportsChannel = reportsChannel.replace(' ', '-')
        reportsChannel = reportsChannel.lower()
        channel = None
        for textChannel in guild.text_channels:
            if textChannel.name == reportsChannel or str(textChannel.id) == reportsChannel:
                channel = textChannel
                break
        return channel

    def checkValidRole(self, role: str, guild: discord.Guild) -> discord.Role:
        if role.startswith("@"):
            role = role[1:]

        role = role.lower()
        roleFound = None
        for guild_role in guild.roles:
            if guild_role.name.lower() == role or str(guild_role.id) == role:
                roleFound = guild_role
                break
        return roleFound

    def getReportsChannel(self, guild: discord.Guild) -> discord.TextChannel:
        reportsChannel = None
        if str(guild.id) in self.bot.guild_settings:
            if "reports_channel_id" in self.bot.guild_settings[str(guild.id)]:
                reportsChannel = guild.get_channel(self.bot.guild_settings[str(guild.id)]["reports_channel_id"])
        return reportsChannel

    def getReportsAlertRole(self, guild: discord.Guild) -> discord.Role:
        reportsRole = None
        if str(guild.id) in self.bot.guild_settings:
            if "reports_alert_role_id" in self.bot.guild_settings[str(guild.id)]:
                reportsRole = guild.get_role(self.bot.guild_settings[str(guild.id)]["reports_alert_role_id"])
        return reportsRole

    def getReportsBannedRole(self, guild: discord.Guild) -> discord.Role:
        reportsBannedRole = None
        if str(guild.id) in self.bot.guild_settings:
            if "reports_banned_role_id" in self.bot.guild_settings[str(guild.id)]:
                reportsBannedRole = guild.get_role(self.bot.guild_settings[str(guild.id)]["reports_banned_role_id"])
        return reportsBannedRole

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

    def isInviteFilterEnabled(self, guild: discord.Guild) -> bool:
        invite_filter = False
        if str(guild.id) in self.bot.guild_settings:
            if "invite_filter" in self.bot.guild_settings[str(guild.id)]:
                invite_filter = self.bot.guild_settings[str(guild.id)]["invite_filter"]
        return invite_filter

    def isLinkFilterEnabled(self, guild: discord.Guild) -> bool:
        link_filter = False
        if str(guild.id) in self.bot.guild_settings:
            if "link_filter" in self.bot.guild_settings[str(guild.id)]:
                link_filter = self.bot.guild_settings[str(guild.id)]["link_filter"]
        return link_filter

    def getModLogChannel(self, guild: discord.Guild) -> discord.TextChannel:
        mod_log_channel = None
        if str(guild.id) in self.bot.guild_settings:
            if "mod_log_channel_id" in self.bot.guild_settings[str(guild.id)]:
                mod_log_channel = guild.get_channel(self.bot.guild_settings[str(guild.id)]["mod_log_channel_id"])
        return mod_log_channel

    def getWhitelistedLinks(self, guild: discord.Guild) -> list:
        whitelisted_links = []
        if str(guild.id) in self.bot.guild_settings:
            if "whitelisted_links" in self.bot.guild_settings[str(guild.id)]:
                whitelisted_links = self.bot.guild_settings[str(guild.id)]["whitelisted_links"]
        return whitelisted_links

    def getChatFilter(self, guild: discord.Guild) -> list:
        chat_filter = []
        if str(guild.id) in self.bot.guild_settings:
            if "chat_filter" in self.bot.guild_settings[str(guild.id)]:
                chat_filter = self.bot.guild_settings[str(guild.id)]["chat_filter"]
        return chat_filter

    def getMsgDeleteChannel(self, guild: discord.Guild) -> discord.TextChannel:
        msg_delete_channel = None
        if str(guild.id) in self.bot.guild_settings:
            if "msg_delete_channel_id" in self.bot.guild_settings[str(guild.id)]:
                msg_delete_channel = guild.get_channel(self.bot.guild_settings[str(guild.id)]["msg_delete_channel_id"])
        return msg_delete_channel

    def getModMsgDeleteChannel(self, guild: discord.Guild) -> discord.TextChannel:
        mod_msg_delete_channel = None
        if str(guild.id) in self.bot.guild_settings:
            if "mod_msg_delete_channel_id" in self.bot.guild_settings[str(guild.id)]:
                mod_msg_delete_channel = guild.get_channel(self.bot.guild_settings[str(guild.id)]["mod_msg_delete_channel_id"])
        return mod_msg_delete_channel

    def getMsgEditChannel(self, guild: discord.Guild) -> discord.TextChannel:
        msg_edit_channel = None
        if str(guild.id) in self.bot.guild_settings:
            if "msg_edit_channel_id" in self.bot.guild_settings[str(guild.id)]:
                msg_edit_channel = guild.get_channel(self.bot.guild_settings[str(guild.id)]["msg_edit_channel_id"])
        return msg_edit_channel

    def getPrefix(self, guild: discord.Guild) -> str:
        prefix = self.bot.default_prefix
        if str(guild.id) in self.bot.guild_settings:
            if "prefix" in self.bot.guild_settings[str(guild.id)]:
                prefix = self.bot.guild_settings[str(guild.id)]["prefix"]
        return prefix

    # BUTTON METHODS
    async def toggleReportSelf(self, interaction: discord.Interaction, main_view: discord.ui.View):
        guild_id = interaction.guild.id
        report_self = not self.isReportSelfEnabled(guild=interaction.guild)

        # Save to postgreSQL
        query = "UPDATE guilds SET report_self = $1 WHERE guild_id = $2;"
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, report_self, guild_id)

        # Save in memory
        self.bot.guild_settings[str(guild_id)]["report_self"] = report_self

        await main_view.refreshEmbed(interaction=interaction, reloadView=True)  # Update main embed

    async def toggleReportBots(self, interaction: discord.Interaction, main_view: discord.ui.View):
        guild_id = interaction.guild.id
        report_bots = not self.isReportBotsEnabled(guild=interaction.guild)

        # Save to postgreSQL
        query = "UPDATE guilds SET report_bots = $1 WHERE guild_id = $2;"
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, report_bots, guild_id)

        # Save in memory
        self.bot.guild_settings[str(guild_id)]["report_bots"] = report_bots

        await main_view.refreshEmbed(interaction=interaction, reloadView=True)  # Update main embed

    async def toggleReportAdmins(self, interaction: discord.Interaction, main_view: discord.ui.View):
        guild_id = interaction.guild.id
        report_admins = not self.isReportAdminsEnabled(guild=interaction.guild)

        # Save to postgreSQL
        query = "UPDATE guilds SET report_admins = $1 WHERE guild_id = $2;"
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, report_admins, guild_id)

        # Save in memory
        self.bot.guild_settings[str(guild_id)]["report_admins"] = report_admins

        await main_view.refreshEmbed(interaction=interaction, reloadView=True)  # Update main embed

    async def toggleInviteFilter(self, interaction: discord.Interaction, main_view: discord.ui.View):
        guild_id = interaction.guild.id
        invite_filter = not self.isInviteFilterEnabled(guild=interaction.guild)

        # Save to postgreSQL
        query = "UPDATE guilds SET invite_filter = $1 WHERE guild_id = $2;"
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, invite_filter, guild_id)

        # Save in memory
        self.bot.guild_settings[str(guild_id)]["invite_filter"] = invite_filter

        await main_view.refreshEmbed(interaction=interaction, reloadView=True)  # Update main embed

    async def toggleLinkFilter(self, interaction: discord.Interaction, main_view: discord.ui.View):
        guild_id = interaction.guild.id
        link_filter = not self.isLinkFilterEnabled(guild=interaction.guild)

        # Save to postgreSQL
        query = "UPDATE guilds SET link_filter = $1 WHERE guild_id = $2;"
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, link_filter, guild_id)

        # Save in memory
        self.bot.guild_settings[str(guild_id)]["link_filter"] = link_filter

        await main_view.refreshEmbed(interaction=interaction, reloadView=True)  # Update main embed

    # BUTTON MODALS
    class ReportsChannelModel(ui.Modal):
        def __init__(self, bot=None, main_view=None):
            super().__init__(title="Reports Channel")
            self.bot = bot
            self.main_view = main_view

        channel = ui.TextInput(label='Reports Channel', style=discord.TextStyle.short,
                               placeholder="Please enter the channel name, such as #reports",
                               required=True, max_length=1000)

        async def on_error(self, error: Exception, interaction: Interaction) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def on_submit(self, interaction: Interaction):
            guild_id = interaction.guild.id
            reportsChannel = self.channel.value.lower()
            channel = self.main_view.cog.checkValidChannel(reportsChannel, interaction.guild)

            if reportsChannel == "none" or reportsChannel == "reset":
                embed = discord.Embed(title="Channel reset", description="You have removed the Reports Channel.", colour=discord.Colour.green())

                if "reports_channel_id" in self.bot.guild_settings[str(guild_id)]:
                    # Save to postgreSQL - NONE
                    query = "UPDATE guilds SET reports_channel_id = $1 WHERE guild_id = $2;"
                    async with self.bot.pool.acquire() as conn:
                        async with conn.transaction():
                            await conn.execute(query, None, guild_id)

                    # Save in memory
                    del self.bot.guild_settings[str(guild_id)]["reports_channel_id"]

                    await self.main_view.refreshEmbed()

            elif channel is None:
                embed = discord.Embed(title="Channel not found",
                                      description="Please enter a valid channel name.\nTo remove the current channel, enter `reset` instead of a channel name.",
                                      colour=discord.Colour.dark_red())
            else:
                embed = discord.Embed(title="Reports Channel Updated", description=f"Successfully updated the reports channel to {channel.mention}", colour=discord.Colour.green())

                # Save to postgreSQL
                query = "UPDATE guilds SET reports_channel_id = $1 WHERE guild_id = $2;"
                async with self.bot.pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute(query, channel.id, guild_id)

                # Save in memory
                self.bot.guild_settings[str(guild_id)]["reports_channel_id"] = channel.id

                await self.main_view.refreshEmbed()

            await interaction.response.send_message(embed=embed, ephemeral=True)

    class ReportsAlertRoleModel(ui.Modal):
        def __init__(self, bot=None, main_view=None):
            super().__init__(title="Reports Alert Role")
            self.bot = bot
            self.main_view = main_view

        role = ui.TextInput(label='Alert Role', style=discord.TextStyle.short,
                            placeholder="Please enter the role name, such as @reports",
                            required=True, max_length=1000)

        async def on_error(self, error: Exception, interaction: Interaction) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def on_submit(self, interaction: Interaction):
            guild_id = interaction.guild.id
            reportsRole = self.role.value.lower()
            role = self.main_view.cog.checkValidRole(reportsRole, interaction.guild)

            if reportsRole == "none" or reportsRole == "reset":
                embed = discord.Embed(title="Role reset", description="You have removed the Alert Role.", colour=discord.Colour.green())

                if "reports_alert_role_id" in self.bot.guild_settings[str(guild_id)]:
                    # Save to postgreSQL - NONE
                    query = "UPDATE guilds SET reports_alert_role_id = $1 WHERE guild_id = $2;"
                    async with self.bot.pool.acquire() as conn:
                        async with conn.transaction():
                            await conn.execute(query, None, guild_id)

                    # Save in memory
                    del self.bot.guild_settings[str(guild_id)]["reports_alert_role_id"]

                    await self.main_view.refreshEmbed()

            elif role is None:
                embed = discord.Embed(title="Role not found",
                                      description="Please enter a valid role name.\nTo remove the current role, enter `reset` instead of a role name.",
                                      colour=discord.Colour.dark_red())
            else:

                embed = discord.Embed(title="Reports Alert Role Updated")
                embed.description = f"Successfully updated the reports alert role to {role.mention}"
                embed.colour = discord.Colour.green()

                # Save to postgreSQL
                query = "UPDATE guilds SET reports_alert_role_id = $1 WHERE guild_id = $2;"
                async with self.bot.pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute(query, role.id, guild_id)

                # Save in memory
                self.bot.guild_settings[str(guild_id)]["reports_alert_role_id"] = role.id

                await self.main_view.refreshEmbed()

            await interaction.response.send_message(embed=embed, ephemeral=True)

    class ReportsBannedRoleModel(ui.Modal):
        def __init__(self, bot=None, main_view=None):
            super().__init__(title="Reports Banned Role")
            self.bot = bot
            self.main_view = main_view

        role = ui.TextInput(label='Banned Role', style=discord.TextStyle.short,
                            placeholder="Please enter the role name, such as @muted",
                            required=True, max_length=1000)

        async def on_error(self, error: Exception, interaction: Interaction) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def on_submit(self, interaction: Interaction):
            guild_id = interaction.guild.id
            bannedRole = self.role.value.lower()
            role = self.main_view.cog.checkValidRole(bannedRole, interaction.guild)

            if bannedRole == "none" or bannedRole == "reset":
                embed = discord.Embed(title="Role reset", description="You have removed the Banned Role.", colour=discord.Colour.green())

                if "reports_banned_role_id" in self.bot.guild_settings[str(guild_id)]:
                    # Save to postgreSQL - NONE
                    query = "UPDATE guilds SET reports_banned_role_id = $1 WHERE guild_id = $2;"
                    async with self.bot.pool.acquire() as conn:
                        async with conn.transaction():
                            await conn.execute(query, None, guild_id)

                    # Save in memory
                    del self.bot.guild_settings[str(guild_id)]["reports_banned_role_id"]

                    await self.main_view.refreshEmbed()

            elif role is None:
                embed = discord.Embed(title="Role not found",
                                      description="Please enter a valid role name.\nTo remove the current role, enter `reset` instead of a role name.",
                                      colour=discord.Colour.dark_red())
            else:
                embed = discord.Embed(title="Reports Banned Role Updated")
                embed.description = f"Successfully updated the reports banned role to {role.mention}"
                embed.colour = discord.Colour.green()

                # Save to postgreSQL
                query = "UPDATE guilds SET reports_banned_role_id = $1 WHERE guild_id = $2;"
                async with self.bot.pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute(query, role.id, guild_id)

                # Save in memory
                self.bot.guild_settings[str(guild_id)]["reports_banned_role_id"] = role.id

                await self.main_view.refreshEmbed()

            await interaction.response.send_message(embed=embed, ephemeral=True)

    class WhitelistedLinkModel(ui.Modal):
        def __init__(self, bot=None, main_view=None):
            super().__init__(title="Whitelisted Links")
            self.bot = bot
            self.main_view = main_view

        add = ui.TextInput(label='Add Link', style=discord.TextStyle.short,
                           placeholder="Enter any links to add to the whitelist such as 'tenor.com'",
                           required=False, max_length=1000)
        remove = ui.TextInput(label='Remove Link', style=discord.TextStyle.short,
                              placeholder="Enter any links to remove from the whitelist",
                              required=False, max_length=1000)

        async def on_error(self, error: Exception, interaction: Interaction) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def on_submit(self, interaction: Interaction):
            add = self.add.value
            remove = self.remove.value

            if not add and not remove:
                embed = discord.Embed(title="No links found",
                                      description="Please enter some links to either add or remove from the whitelist.",
                                      colour=discord.Colour.dark_red())
            else:
                guild_id = interaction.guild.id
                whitelisted_links = self.main_view.cog.getWhitelistedLinks(interaction.guild)

                msg = []

                if add:
                    to_add = add.replace(" ", "")
                    to_add = to_add.replace("'", "")
                    to_add = to_add.replace("\"", "")
                    to_add = to_add.lower()
                    to_add = to_add.split(",")
                    to_add = list(dict.fromkeys(to_add))  # remove duplicates

                    LINKS_TO_ADD = []

                    for link in to_add:
                        if link not in whitelisted_links:
                            LINKS_TO_ADD.append(link)
                        else:
                            msg.append(f'`{link}` is already in the whitelist')

                    for link in LINKS_TO_ADD:
                        if re.match("([^\\s.]+\\.[^\\s]{2,})", link):
                            whitelisted_links.append(link)
                            msg.append(f'Added `{link}`')
                        else:
                            msg.append(f'`{link}` is an invalid link')

                if remove:

                    if remove.lower() == "all":
                        whitelisted_links = []
                        msg.append(f'Whitelisted Links has been `cleared`')
                    else:
                        to_remove = remove.replace(" ", "")
                        to_remove = to_remove.replace("'", "")
                        to_remove = to_remove.replace("\"", "")
                        to_remove = to_remove.lower()
                        to_remove = to_remove.split(",")
                        to_remove = list(dict.fromkeys(to_remove))  # remove duplicates

                        LINKS_TO_REMOVE = []

                        for link in to_remove:
                            if link in whitelisted_links:
                                LINKS_TO_REMOVE.append(link)
                            else:
                                msg.append(f'`{link}` is not in the whitelist')

                        for link in LINKS_TO_REMOVE:
                            whitelisted_links.remove(link)
                            msg.append(f'Removed `{link}`')

                # Save to postgreSQL
                query = "UPDATE guilds SET whitelisted_links = $1 WHERE guild_id = $2;"
                async with self.bot.pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute(query, whitelisted_links, guild_id)

                # Save in memory
                self.bot.guild_settings[str(guild_id)]["whitelisted_links"] = whitelisted_links

                embed = discord.Embed(title="Link Whitelist Updated")
                embed.description = '\n'.join(msg)[0:4000]
                embed.colour = discord.Colour.green()

                await self.main_view.refreshEmbed()

            embed.set_footer(text="You can add/remove multiple links at once by using commas such as 'a.com, b.net'.\nUse 'all' in the remove link field to remove all links.")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    class ChatFilterModel(ui.Modal):
        def __init__(self, bot=None, main_view=None):
            super().__init__(title="Chat Filter")
            self.bot = bot
            self.main_view = main_view

        add = ui.TextInput(label='Add Words', style=discord.TextStyle.short,
                           placeholder="Enter any words to add to the filter",
                           required=False, max_length=1000)
        remove = ui.TextInput(label='Remove Words', style=discord.TextStyle.short,
                              placeholder="Enter any words to remove from the filter",
                              required=False, max_length=1000)

        async def on_error(self, error: Exception, interaction: Interaction) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def on_submit(self, interaction: Interaction):
            add = self.add.value
            remove = self.remove.value

            if not add and not remove:
                embed = discord.Embed(title="No Words found",
                                      description="Please enter some words to either add or remove from the chat filter.",
                                      colour=discord.Colour.dark_red())
            else:
                guild_id = interaction.guild.id
                chat_filter = self.main_view.cog.getChatFilter(interaction.guild)
                msg = []

                if add:
                    to_add = add.replace(" ", "")
                    to_add = to_add.replace("'", "")
                    to_add = to_add.replace("\"", "")
                    to_add = to_add.lower()
                    to_add = to_add.split(",")
                    to_add = list(dict.fromkeys(to_add))  # remove duplicates

                    for word in to_add:
                        if word not in chat_filter:
                            chat_filter.append(word)
                            msg.append(f'Added `{word}`')
                        else:
                            msg.append(f'`{word}` is already in the filter')

                if remove:
                    if remove.lower() == "all":
                        chat_filter = []
                        msg.append(f'Chat Filter has been `cleared`')
                    else:
                        to_remove = remove.replace(" ", "")
                        to_remove = to_remove.replace("'", "")
                        to_remove = to_remove.replace("\"", "")
                        to_remove = to_remove.lower()
                        to_remove = to_remove.split(",")
                        to_remove = list(dict.fromkeys(to_remove))  # remove duplicates

                        for word in to_remove:
                            if word in chat_filter:
                                chat_filter.remove(word)
                                msg.append(f'Removed `{word}`')
                            else:
                                msg.append(f'`{word}` is not in the filter')

                # Save to postgreSQL
                query = "UPDATE guilds SET chat_filter = $1 WHERE guild_id = $2;"
                async with self.bot.pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute(query, chat_filter, guild_id)

                # Save in memory
                self.bot.guild_settings[str(guild_id)]["chat_filter"] = chat_filter

                embed = discord.Embed(title="Chat Filter Updated")
                embed.description = '\n'.join(msg)[0:4000]
                embed.colour = discord.Colour.green()

                await self.main_view.refreshEmbed()

            embed.set_footer(text="You can add/remove multiple words at once by using commas such as 'a, b'.\nUse 'all' in the remove words field to clear the filter.")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    class ModLogChannelModel(ui.Modal):
        def __init__(self, bot=None, main_view=None):
            super().__init__(title="Mod Log Channel")
            self.bot = bot
            self.main_view = main_view

        channel = ui.TextInput(label='Mod Log Channel', style=discord.TextStyle.short,
                               placeholder="Please enter the channel name, such as #logs",
                               required=True, max_length=1000)

        async def on_error(self, error: Exception, interaction: Interaction) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def on_submit(self, interaction: Interaction):
            guild_id = interaction.guild.id
            modLogChannel = self.channel.value.lower()
            channel = self.main_view.cog.checkValidChannel(modLogChannel, interaction.guild)

            if modLogChannel == "none" or modLogChannel == "reset":
                embed = discord.Embed(title="Channel reset", description="You have removed the Mod Log Channel.", colour=discord.Colour.green())

                if "mod_log_channel_id" in self.bot.guild_settings[str(guild_id)]:
                    # Save to postgreSQL - NONE
                    query = "UPDATE guilds SET mod_log_channel_id = $1 WHERE guild_id = $2;"
                    async with self.bot.pool.acquire() as conn:
                        async with conn.transaction():
                            await conn.execute(query, None, guild_id)

                    # Save in memory
                    del self.bot.guild_settings[str(guild_id)]["mod_log_channel_id"]

                    await self.main_view.refreshEmbed()

            elif channel is None:
                embed = discord.Embed(title="Channel not found",
                                      description="Please enter a valid channel name.\nTo remove the current channel, enter `reset` instead of a channel name.",
                                      colour=discord.Colour.dark_red())
            else:
                embed = discord.Embed(title="Mod Log Channel Updated", description=f"Successfully updated the mod log channel to {channel.mention}", colour=discord.Colour.green())

                # Save to postgreSQL
                query = "UPDATE guilds SET mod_log_channel_id = $1 WHERE guild_id = $2;"
                async with self.bot.pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute(query, channel.id, guild_id)

                # Save in memory
                self.bot.guild_settings[str(guild_id)]["mod_log_channel_id"] = channel.id

                await self.main_view.refreshEmbed()

            await interaction.response.send_message(embed=embed, ephemeral=True)

    class MessageDeleteChannelModel(ui.Modal):
        def __init__(self, bot=None, main_view=None):
            super().__init__(title="Message Delete Channel")
            self.bot = bot
            self.main_view = main_view

        channel = ui.TextInput(label='Message Delete Channel', style=discord.TextStyle.short,
                               placeholder="Please enter the channel name, such as #logs",
                               required=True, max_length=1000)

        async def on_error(self, error: Exception, interaction: Interaction) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def on_submit(self, interaction: Interaction):
            guild_id = interaction.guild.id
            msgDeleteChannel = self.channel.value.lower()
            channel = self.main_view.cog.checkValidChannel(msgDeleteChannel, interaction.guild)

            if msgDeleteChannel == "none" or msgDeleteChannel == "reset":
                embed = discord.Embed(title="Channel reset", description="You have removed the Message Delete Channel.", colour=discord.Colour.green())

                if "msg_delete_channel_id" in self.bot.guild_settings[str(guild_id)]:
                    # Save to postgreSQL - NONE
                    query = "UPDATE guilds SET msg_delete_channel_id = $1 WHERE guild_id = $2;"
                    async with self.bot.pool.acquire() as conn:
                        async with conn.transaction():
                            await conn.execute(query, None, guild_id)

                    # Save in memory
                    del self.bot.guild_settings[str(guild_id)]["msg_delete_channel_id"]

                    await self.main_view.refreshEmbed()

            elif channel is None:
                embed = discord.Embed(title="Channel not found",
                                      description="Please enter a valid channel name.\nTo remove the current channel, enter `reset` instead of a channel name.",
                                      colour=discord.Colour.dark_red())
            else:
                embed = discord.Embed(title="Message Delete Channel Updated", description=f"Successfully updated the message delete channel to {channel.mention}", colour=discord.Colour.green())

                # Save to postgreSQL
                query = "UPDATE guilds SET msg_delete_channel_id = $1 WHERE guild_id = $2;"
                async with self.bot.pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute(query, channel.id, guild_id)

                # Save in memory
                self.bot.guild_settings[str(guild_id)]["msg_delete_channel_id"] = channel.id

                await self.main_view.refreshEmbed()

            await interaction.response.send_message(embed=embed, ephemeral=True)
            # log.info(self.bot.guild_settings[str(guild_id)])

    class ModMessageDeleteChannelModel(ui.Modal):
        def __init__(self, bot=None, main_view=None):
            super().__init__(title="Mod Message Delete Channel")
            self.bot = bot
            self.main_view = main_view

        channel = ui.TextInput(label='Mod Message Delete Channel', style=discord.TextStyle.short,
                               placeholder="Please enter the channel name, such as #logs",
                               required=True, max_length=1000)

        async def on_error(self, error: Exception, interaction: Interaction) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def on_submit(self, interaction: Interaction):
            guild_id = interaction.guild.id
            modMsgDeleteChannel = self.channel.value.lower()
            channel = self.main_view.cog.checkValidChannel(modMsgDeleteChannel, interaction.guild)

            if modMsgDeleteChannel == "none" or modMsgDeleteChannel == "reset":
                embed = discord.Embed(title="Channel reset", description="You have removed the Mod Message Delete Channel.", colour=discord.Colour.green())

                if "mod_msg_delete_channel_id" in self.bot.guild_settings[str(guild_id)]:
                    # Save to postgreSQL - NONE
                    query = "UPDATE guilds SET mod_msg_delete_channel_id = $1 WHERE guild_id = $2;"
                    async with self.bot.pool.acquire() as conn:
                        async with conn.transaction():
                            await conn.execute(query, None, guild_id)

                    # Save in memory
                    del self.bot.guild_settings[str(guild_id)]["mod_msg_delete_channel_id"]

                    await self.main_view.refreshEmbed()

            elif channel is None:
                embed = discord.Embed(title="Channel not found",
                                      description="Please enter a valid channel name.\nTo remove the current channel, enter `reset` instead of a channel name.",
                                      colour=discord.Colour.dark_red())
            else:
                embed = discord.Embed(title="Mod Message Delete Channel Updated", description=f"Successfully updated the mod message delete channel to {channel.mention}",
                                      colour=discord.Colour.green())

                # Save to postgreSQL
                query = "UPDATE guilds SET mod_msg_delete_channel_id = $1 WHERE guild_id = $2;"
                async with self.bot.pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute(query, channel.id, guild_id)

                # Save in memory
                self.bot.guild_settings[str(guild_id)]["mod_msg_delete_channel_id"] = channel.id

                await self.main_view.refreshEmbed()

            await interaction.response.send_message(embed=embed, ephemeral=True)
            # log.info(self.bot.guild_settings[str(guild_id)])

    class MessageEditChannelModel(ui.Modal):
        def __init__(self, bot=None, main_view=None):
            super().__init__(title="Message Edit Channel")
            self.bot = bot
            self.main_view = main_view

        channel = ui.TextInput(label='Message Edit Channel', style=discord.TextStyle.short,
                               placeholder="Please enter the channel name, such as #logs",
                               required=True, max_length=1000)

        async def on_error(self, error: Exception, interaction: Interaction) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def on_submit(self, interaction: Interaction):
            guild_id = interaction.guild.id
            msgEditChannel = self.channel.value.lower()
            channel = self.main_view.cog.checkValidChannel(msgEditChannel, interaction.guild)

            if msgEditChannel == "none" or msgEditChannel == "reset":
                embed = discord.Embed(title="Channel reset", description="You have removed the Message Edit Channel.", colour=discord.Colour.green())

                if "msg_edit_channel_id" in self.bot.guild_settings[str(guild_id)]:
                    # Save to postgreSQL - NONE
                    query = "UPDATE guilds SET msg_edit_channel_id = $1 WHERE guild_id = $2;"
                    async with self.bot.pool.acquire() as conn:
                        async with conn.transaction():
                            await conn.execute(query, None, guild_id)

                    # Save in memory
                    del self.bot.guild_settings[str(guild_id)]["msg_edit_channel_id"]

                    await self.main_view.refreshEmbed()

            elif channel is None:
                embed = discord.Embed(title="Channel not found",
                                      description="Please enter a valid channel name.\nTo remove the current channel, enter `reset` instead of a channel name.",
                                      colour=discord.Colour.dark_red())
            else:
                embed = discord.Embed(title="Message Edit Channel Updated", description=f"Successfully updated the message edit channel to {channel.mention}",
                                      colour=discord.Colour.green())

                # Save to postgreSQL
                query = "UPDATE guilds SET msg_edit_channel_id = $1 WHERE guild_id = $2;"
                async with self.bot.pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute(query, channel.id, guild_id)

                # Save in memory
                self.bot.guild_settings[str(guild_id)]["msg_edit_channel_id"] = channel.id

                await self.main_view.refreshEmbed()

            await interaction.response.send_message(embed=embed, ephemeral=True)
            # log.info(self.bot.guild_settings[str(guild_id)])

    class PrefixModel(ui.Modal):
        def __init__(self, bot=None, main_view=None):
            super().__init__(title="Prefix")
            self.bot = bot
            self.main_view = main_view

        prefix = ui.TextInput(label='Prefix', style=discord.TextStyle.short,
                              placeholder="Please enter the new prefix, such as -",
                              required=True, min_length=1, max_length=5)

        async def on_error(self, error: Exception, interaction: Interaction) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def on_submit(self, interaction: Interaction):
            new_prefix = self.prefix.value
            guild_id = interaction.guild.id

            # Save to postgreSQL
            query = "UPDATE guilds SET prefix = $1 WHERE guild_id = $2;"
            async with self.bot.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(query, new_prefix, guild_id)

            # Save in memory
            self.bot.guild_settings[str(guild_id)]["prefix"] = new_prefix

            await self.main_view.refreshEmbed(interaction=interaction)  # Update main embed


async def setup(bot):
    await bot.add_cog(SettingsCommand(bot))
