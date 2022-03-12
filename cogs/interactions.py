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

    def getNoReportsChannelEmbed(self) -> discord.Embed:
        embed = discord.Embed(title="Configuration Error")
        embed.description = f'This Discord server has not been configured yet.\nPlease ask a server administrator to use the /settings command and set a reports channel.' \
                            f'\nCurrently I don\'t know which channel to send reports to!'
        embed.colour = discord.Colour.red()
        return embed

    def getReportsBannedEmbed(self, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(title="Reports Ban")
        embed.description = f'You have the {self.getReportsBannedRole(guild).mention} role which is preventing you from creating reports.'
        embed.colour = discord.Colour.red()
        return embed

    # Message reports
    async def handleMessageReport(self, interaction: discord.Interaction, message: discord.Message):

        if message.guild is None:
            await interaction.response.send_message("Please use this command in a Discord server.")
            return

        if self.getReportsChannel(message.guild) is None:  # check reports channel setup
            await interaction.response.send_message(embed=self.getNoReportsChannelEmbed(), ephemeral=True)
            return

        if self.getReportsBannedRole(message.guild) is not None:  # check if user is banned from creating reports
            if interaction.user.get_role(self.getReportsBannedRole(interaction.guild).id) is not None:
                await interaction.response.send_message(embed=self.getReportsBannedEmbed(message.guild), ephemeral=True)
                return

        # Check the message is not from a bot or an admin TODO

        # Check not from self
        if message.author.id == interaction.user.id:
            await interaction.response.send_message("Sorry, you can't report your own messages!", ephemeral=True)
            return

        await interaction.response.send_modal(self.MessageReportModal(message=message, interactionsCog=self))

    class MessageReportModal(ui.Modal, title="Report Message"):
        """ A modal for user to enter a reason as to why they are reporting a message """

        def __init__(self, message=None, interactionsCog=None):
            super().__init__()
            self.message = message
            self.interactionsCog = interactionsCog

        reason = ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, placeholder="Report reason",
                              required=True, max_length=1000)

        async def on_submit(self, interaction: discord.Interaction):
            # Send to user
            embed = discord.Embed(title="Message Reported")
            if len(str(self.message.clean_content)) == 0:
                msgContent = "No message content"
            else:
                msgContent = self.message.clean_content[0:2000]
            embed.description = f"You successfully reported [this]({self.message.jump_url}) message. Staff have been alerted.\n\n" \
                                f"**Report reason:**\n`{self.reason.value}`" \
                                f"\n\n**Message reported:**\n`{msgContent}`"

            await interaction.response.send_message(embed=embed, ephemeral=True)

            # send to reports channel
            embed = discord.Embed(title="Message Report")
            line1 = f'{interaction.user.mention} ({interaction.user}) has reported [this]({self.message.jump_url}) message from {self.message.author.mention} ({self.message.author})'
            line2 = f"**Report reason:**\n`{self.reason.value}`"
            if len(str(self.message.clean_content)) == 0:
                line3 = "**Message reported:**\n`No message content`"
            else:
                line3 = f'**Message reported:**\n`{self.message.clean_content[0:2000]}`'  # only display first 2000 chars

            if len(self.message.attachments) != 0:
                attachement1 = self.message.attachments.pop(0)
                # print(attachement1.content_type)
                if attachement1.content_type.startswith("image"):
                    embed.set_image(url=attachement1.url)

            embed.description = f"{line1}\n" \
                                f"\n{line2}\n" \
                                f"\n{line3}"

            if self.interactionsCog.getReportsAlertRole(interaction.guild) is not None:
                await self.interactionsCog.getReportsChannel(interaction.guild).send(
                    content=f"{self.interactionsCog.getReportsAlertRole(interaction.guild).mention}", embed=embed,
                    allowed_mentions=discord.AllowedMentions(roles=True))
            else:
                await self.interactionsCog.getReportsChannel(interaction.guild).send(embed=embed)

    # User reports

    async def handleUserReport(self, interaction: discord.Interaction, member: discord.Member):

        if isinstance(member, discord.User):
            await interaction.response.send_message("Please use this command in a Discord server.")
            return

        # check that their is a channel setup
        if self.getReportsChannel(member.guild) is None:
            await interaction.response.send_message(embed=self.getNoReportsChannelEmbed(), ephemeral=True)
            return

        if self.getReportsBannedRole(member.guild) is not None:  # check if user is banned from creating reports
            if interaction.user.get_role(self.getReportsBannedRole(member.guild).id) is not None:
                await interaction.response.send_message(embed=self.getReportsBannedEmbed(member.guild), ephemeral=True)
                return

        # Check the message is not from a bot or an admin TODO

        # Check not from self
        if member.id == interaction.user.id:
            await interaction.response.send_message("Sorry, you can't report yourself!", ephemeral=True)
            return

        await interaction.response.send_modal(self.UserReportModal(member=member, interactionsCog=self))

    class UserReportModal(ui.Modal, title="Report User"):
        """ A modal for user to enter a reason as to why they are reporting a user """

        def __init__(self, member=None, interactionsCog=None):
            super().__init__()
            self.member = member
            self.interactionsCog = interactionsCog

        reason = ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, placeholder="Report reason",
                              required=True, max_length=1000)

        async def on_submit(self, interaction: discord.Interaction):
            # sent to user
            embed = discord.Embed(title="User Reported")
            embed.description = f"You successfully reported {self.member.mention} ({self.member}). Staff have been alerted.\n\n" \
                                f"**Report reason:**\n`{self.reason.value}`"
            await interaction.response.send_message(embed=embed, ephemeral=True)

            # send to reports channel
            embed = discord.Embed(title="User Report")
            line1 = f'{interaction.user.mention} has reported {self.member.mention} ({self.member})\nReported user\'s Discord ID: `{self.member.id}`'
            line2 = f"**Report reason:**\n`{self.reason.value}`"

            embed.description = f"{line1}\n\n{line2}\n"

            if self.interactionsCog.getReportsAlertRole(interaction.guild) is not None:
                await self.interactionsCog.getReportsChannel(interaction.guild).send(
                    content=f"{self.interactionsCog.getReportsAlertRole(interaction.guild).mention}", embed=embed,
                    allowed_mentions=discord.AllowedMentions(roles=True))
            else:
                await self.interactionsCog.getReportsChannel(interaction.guild).send(embed=embed)

    async def handleHelpCommand(self, interaction: discord.Interaction):

        embed = discord.Embed()  # title="Help", description=f'Support server: https://discord.gg/rcUzqaQN8k')

        embed.title = 'Official Bot Server Invite'
        embed.url = 'https://discord.gg/rcUzqaQN8k'
        embed.colour = discord.Colour.blurple()

        embed.add_field(name="__Commands__", value=
        f'**/help** - Displays help menu.\n'
        f'**Report Message** - Right click a message, scroll to \'Apps\', then click me to report a user.\n'
        f'**Report User** - Right click a user, scroll to \'Apps\', then click me to report a message.\n'
        f'**/report** - Used to report a user, as mobile devices do not support context menus.\n'
        f'**/settings** - Used to setup the bot in your server.', inline=False
                        )

        embed.add_field(name="__Setup__", value=
        f'1. First invite me to your server, using the button on my profile.\n'
        f'2. Use the /settings command and enter a channel name for reports to be sent to.\n'
        f'3. Now you can right click on a user or message then scroll to \'Apps\' and click the report button!\n'
        f'\n'
        f'**NOTE:** Members must have the \'Use Application Commands\' permission. Also Discord is sometimes weird so if no \'Apps\' section is showing after you right click a message or user, then do CTRL + R to reload your Discord',
                        inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=False)


def setup(bot):
    bot.add_cog(InteractionsCog(bot))
