import logging

import discord
from discord import ui
from discord.ext import commands

log = logging.getLogger(__name__)


class InteractionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def getReportsChannel(self, guild: discord.Guild) -> discord.TextChannel:
        reportsChannel = None
        if str(guild.id) in self.bot.guild_settings:
            if "reports_channel_id" in self.bot.guild_settings[str(guild.id)]:
                reportsChannel = guild.get_channel(self.bot.guild_settings[str(guild.id)]["reports_channel_id"])
        return reportsChannel

    def getNoReportsChannelEmbed(self) -> discord.Embed:
        embed = discord.Embed(title="Configuration Error")
        embed.description = f'This Discord server has not been configured yet.\nPlease ask a server administrator to use the /settings command and set a reports channel.' \
                            f'\nCurrently I don\'t know which channel to send reports to!'
        embed.colour = discord.Colour.red()
        return embed

    # Message reports
    async def handleMessageReport(self, interaction: discord.Interaction, message: discord.Message):

        if message.guild is None:
            await interaction.response.send_message("Please use this command in a Discord server.")
            return

        if self.getReportsChannel(message.guild) is None:
            await interaction.response.send_message(embed=self.getNoReportsChannelEmbed(), ephemeral=True)
            return

        # Check the message is not from a bot or an admin

        messageReportModal = self.MessageReportModal()

        messageReportModal.setMessage(message)

        await interaction.response.send_modal(messageReportModal)

        await messageReportModal.wait()  # Wait for the moda to stop listening

        embed = discord.Embed(title="Message Report")
        line1 = f'{interaction.user.mention} has reported [this]({message.jump_url}) message from {message.author.mention}'
        line2 = f"**Report reason:**\n`{messageReportModal.reason.value}`"
        if len(str(message.clean_content)) == 0:
            line3 = "**Message reported:**\n`No message content`"
        else:
            line3 = f'**Message reported:**\n`{message.clean_content[0:2000]}`'  # only discplay first 2000 chars

        if len(message.attachments) != 0:
            attachement1 = message.attachments.pop(0)
            # print(attachement1.content_type)
            if attachement1.content_type.startswith("image"):
                embed.set_image(url=attachement1.url)

        embed.description = f"{line1}\n" \
                            f"\n{line2}\n" \
                            f"\n{line3}"

        await self.getReportsChannel(message.guild).send(embed=embed)

    class MessageReportModal(ui.Modal, title="Report Message"):
        reason = ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, placeholder="Report reason",
                              required=True, max_length=1000)
        message = None

        def setMessage(self, msg: discord.Message):
            self.message = msg

        async def on_submit(self, interaction: discord.Interaction):
            embed = discord.Embed(title="Message Reported")
            if len(str(self.message.clean_content)) == 0:
                msgContent = "No message content"
            else:
                msgContent = self.message.clean_content[0:2000]

            embed.description = f"You successfully reported [this]({self.message.jump_url}) message. Staff have been alerted.\n\n" \
                                f"**Report reason:**\n`{self.reason}`" \
                                f"\n\n**Message reported:**\n`{msgContent}`"

            await interaction.response.send_message(embed=embed, ephemeral=True)

    # User reports

    async def handleUserReport(self, interaction: discord.Interaction, member: discord.Member):

        if isinstance(member, discord.User):
            await interaction.response.send_message("Please use this command in a Discord server.")
            return

            # check that their is a channel called reports
        if self.getReportsChannel(member.guild) is None:
            await interaction.response.send_message(embed=self.getNoReportsChannelEmbed(), ephemeral=True)
            return

        # Check the message is not from a bot or an admin

        userReportModal = self.UserReportModal()

        userReportModal.setMember(member)

        await interaction.response.send_modal(userReportModal)

        await userReportModal.wait()  # Wait for the modal to stop listening

        embed = discord.Embed(title="User Report")
        line1 = f'{interaction.user.mention} has reported {member.mention} ({member})\nReported user\'s Discord ID: `{member.id}`'
        line2 = f"**Report reason:**\n`{userReportModal.reason.value}`"

        embed.description = f"{line1}\n\n{line2}\n"

        await self.getReportsChannel(member.guild).send(embed=embed)

    class UserReportModal(ui.Modal, title="Report User"):
        reason = ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, placeholder="Report reason",
                              required=True, max_length=1000)
        member = None

        def setMember(self, msg: discord.Member):
            self.member = msg

        async def on_submit(self, interaction: discord.Interaction):
            embed = discord.Embed(title="User Reported")

            embed.description = f"You successfully reported {self.member.mention} ({self.member}). Staff have been alerted.\n\n" \
                                f"**Report reason:**\n`{self.reason}`"
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def handleHelpCommand(self, interaction: discord.Interaction):

        embed = discord.Embed(title="Help", description=f'Support server: https://discord.gg/rcUzqaQN8k')
        embed.add_field(name="Commands", value=
        f'/help - Displays help menu\n'
        f'/report - Used to report a user as mobile devices do not support context menus\n'
        f'/settings - Used to setup the bot in your server.', inline=False)

        embed.add_field(name="Setup", value=
        f'To set me up in your server just invite me, using the button on my profile, and then enter a channel name in the /settings command for reports to go to.'
        f'Now you can right click on a user or message then scroll to Apps and click the report button!\n'
        f'Discord is sometimes annoying so if no Apps section is showing after you right click a message or user. then do CTRL + R to reload Discord',
                        inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    async def handleSettingsCommand(self, interaction: discord.Interaction):

        if interaction.guild is None:
            await interaction.response.send_message("Please use this command in a Discord server.")
            return

        # check permissions is admin or manage server
        member = interaction.guild.get_member(interaction.user.id)

        permissions = [
            (name.replace('_', ' ').title(), value)
            for name, value in member.guild_permissions
        ]

        allowed = [name for name, value in permissions if value]

        if "Administrator" in allowed or "Manage Guild" in allowed:
            pass
        else:
            await interaction.response.send_message("You must have the manage server permissions to use this.",
                                                    ephemeral=True)
            return

        if str(interaction.guild.id) in self.bot.guild_settings:

            if "reports_channel_id" in self.bot.guild_settings[str(interaction.guild.id)]:
                reports_channel = interaction.guild.get_channel(
                    self.bot.guild_settings[str(interaction.guild.id)]["reports_channel_id"])
                if reports_channel is None:
                    reports_channel = "None"
                else:
                    reports_channel = reports_channel.mention
            else:
                reports_channel = "None"

        else:
            reports_channel = "None"

        embed = discord.Embed(title="Settings",
                              description=f'Click a button to edit a value.\n\n**Reports Channel:** {reports_channel}')
        # f'Role to get tagged for each report: @apple\n'
        # f'Banned Role: @banned\n'
        # f'Allow members to report bots or messages from bots? yes\n'
        # f'Allow members to report server admins or messages from admins? yes')

        view = self.SettingButtons()

        await interaction.response.send_message(embed=embed, ephemeral=False, view=view)

        origMsg = await interaction.original_message()

        view.setMessage(origMsg)
        view.setRequiredUserId(interaction.user.id)
        view.setBot(self.bot)

    class SettingButtons(discord.ui.View):
        def __init__(self, timeout=30):
            super().__init__(timeout=timeout)

            self.message = None  # the original interaction message
            self.userID = None  # the user which is allowed to click the buttons
            self.bot = None  # the main bot instance

            self.reportsChannel = None  # the reports channel

        def setMessage(self, message: discord.Message):
            self.message = message

        def setRequiredUserId(self, userID: int):
            self.userID = userID

        def setBot(self, bot: discord.Client):
            self.bot = bot

        async def on_timeout(self) -> None:
            await self.message.edit(view=None)

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id == self.userID:
                return True
            else:
                await interaction.response.send_message("Sorry, you cannot use this.", ephemeral=True)
                return False

        @discord.ui.button(label='Reports Channel', style=discord.ButtonStyle.green)
        async def reportsChannel(self, button: discord.ui.Button, interaction: discord.Interaction):

            reportsChannelModel = self.ReportsChannelModel()

            await interaction.response.send_modal(reportsChannelModel)

            await reportsChannelModel.wait()  # Wait for the modal to stop listening

            self.reportsChannel = reportsChannelModel.channel.value
            if self.reportsChannel.startswith("#"):
                self.reportsChannel = self.reportsChannel[1:]

            channel = None
            for textChannel in interaction.guild.text_channels:
                if textChannel.name == self.reportsChannel.lower():
                    channel = textChannel

            if channel is not None:
                embed = discord.Embed(title="Settings", description=f'**Reports Channel:** {channel.mention}')
                await self.message.edit(embed=embed)

                if not str(interaction.guild.id) in self.bot.guild_settings:
                    self.bot.guild_settings[str(interaction.guild.id)] = {}

                self.bot.guild_settings[str(interaction.guild.id)]["reports_channel_id"] = channel.id

        @discord.ui.button(label='Finish', style=discord.ButtonStyle.grey)
        async def finish(self, button: discord.ui.Button, interaction: discord.Interaction):
            await self.on_timeout()
            self.stop()

        class ReportsChannelModel(ui.Modal, title="Reports Channel"):
            channel = ui.TextInput(label='Reports Channel', style=discord.TextStyle.short,
                                   placeholder="Please enter the channel name, such as #reports",
                                   required=True, max_length=1000)
            member = None

            def setMember(self, msg: discord.Member):
                self.member = msg

            async def on_submit(self, interaction: discord.Interaction):

                reportsChannel = self.channel.value

                if reportsChannel.startswith("#"):
                    reportsChannel = reportsChannel[1:]

                channel = None
                for textChannel in interaction.guild.text_channels:
                    if textChannel.name == reportsChannel.lower():
                        channel = textChannel

                if channel is None:
                    embed = discord.Embed(title="Channel not found", description="Please enter a valid channel name.",
                                          colour=discord.Colour.dark_red())
                else:
                    embed = discord.Embed(title="Reports Channel Updated")
                    embed.description = f"Successfully updated the reports channel to {channel.mention}"
                    embed.colour = discord.Colour.green()

                await interaction.response.send_message(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(InteractionsCog(bot))
