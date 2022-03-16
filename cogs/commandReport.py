import logging
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord import app_commands, ui
from discord.ext import commands

import dev_server

log = logging.getLogger(__name__)


class ReportCommand(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.on_cooldown = {}

    @app_commands.command(name='report', description='Report a member with a reason for staff to see.')
    @app_commands.describe(member='The member you are reporting.')
    @app_commands.describe(image='You can upload an image for staff to see if you wish.')
    async def globalReportCommand(self, interaction: discord.Interaction, member: discord.User,
                                  image: Optional[discord.Attachment] = None):
        await self.handleUserReport(interaction, member, image)

    @app_commands.command(name='devreport', description='Dev- Report a member with a reason for staff to see.')
    @app_commands.guilds(discord.Object(id=dev_server.DEV_SERVER_ID))
    @discord.app_commands.describe(member='The member you are reporting.')
    @discord.app_commands.describe(image='You can upload an image for staff to see if you wish.')
    async def devReportCommand(self, interaction: discord.Interaction, member: discord.User,
                               image: Optional[discord.Attachment] = None):
        await self.handleUserReport(interaction, member, image)

    # Methods
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
        embed.description = f'This Discord server has not been configured yet.\nPlease ask a server administrator to use the **/settings** command and set a reports channel.' \
                            f'\nCurrently I don\'t know which channel to send reports to!'
        embed.colour = discord.Colour.red()
        embed.set_image(url="https://cdn.discordapp.com/attachments/764846716557197323/953752057725202472/unknown.png")
        return embed

    def getReportsBannedEmbed(self, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(title="Reports Ban")
        embed.description = f'You have the {self.getReportsBannedRole(guild).mention} role which is preventing you from creating reports.'
        embed.colour = discord.Colour.red()
        return embed

    def check_cooldown(self, member: discord.Member) -> int:
        cooldown_end = self.on_cooldown.get(member.id)

        if cooldown_end is None or cooldown_end < datetime.now():  # If there's no cooldown or it's over
            self.on_cooldown[member.id] = datetime.now() + timedelta(
                seconds=10)  # Add the datetime of the cooldown's end to the dictionary
            return 0  # allow the command to run
        else:
            return (cooldown_end - datetime.now()).total_seconds()

    # Message reports
    async def handleMessageReport(self, interaction: discord.Interaction, message: discord.Message):

        if message.guild is None:
            await interaction.response.send_message("Please use this command in a Discord server.")
            return

        # check reports channel setup
        if self.getReportsChannel(message.guild) is None:
            await interaction.response.send_message(embed=self.getNoReportsChannelEmbed(), ephemeral=True)
            return

        # check if user is banned from creating reports
        if self.getReportsBannedRole(message.guild) is not None:
            if interaction.user.get_role(self.getReportsBannedRole(interaction.guild).id) is not None:
                await interaction.response.send_message(embed=self.getReportsBannedEmbed(message.guild), ephemeral=True)
                return

        # Check not from self
        if not self.bot.get_cog("SettingsCommand").isReportSelfEnabled(interaction.guild):
            if message.author.id == interaction.user.id:
                await interaction.response.send_message("Sorry, you can't report your own messages!", ephemeral=True)
                return

        # Check the message author is not a bot
        if not self.bot.get_cog("SettingsCommand").isReportBotsEnabled(interaction.guild):
            if message.author.bot:
                await interaction.response.send_message("Sorry, you can't report a bot's message!", ephemeral=True)
                return

        # Check the member is not an admin
        if not self.bot.get_cog("SettingsCommand").isReportAdminsEnabled(interaction.guild):
            if message.author.guild_permissions.administrator and not message.author.bot and not message.author.id == interaction.user.id:
                await interaction.response.send_message("Sorry, you can't report a server administrator's message!",
                                                        ephemeral=True)
                return

        cooldown = self.check_cooldown(interaction.user)
        if cooldown != 0:
            return await interaction.response.send_message(
                f"Please wait {cooldown:,.2f}s before posting another report!", ephemeral=True)

        await interaction.response.send_modal(self.MessageReportModal(message=message, interactionsCog=self))

    class MessageReportModal(ui.Modal, title="Report Message"):
        """ A modal for user to enter a reason as to why they are reporting a message """

        def __init__(self, message=None, interactionsCog=None):
            super().__init__()
            self.message = message
            self.interactionsCog = interactionsCog

        reason = ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, placeholder="Report reason",
                              required=True, max_length=2000)

        async def on_submit(self, interaction: discord.Interaction):
            # Send to user
            embed = discord.Embed()
            embed.set_author(name="Message Content", icon_url=self.message.author.display_avatar.url)
            embed.colour = discord.Colour(0x2F3136)

            if len(str(self.message.clean_content)) == 0:
                msgContent = "No message content"
            else:
                msgContent = self.message.clean_content[0:2000]

            embedDescription = f"You successfully reported [this]({self.message.jump_url}) message from {self.message.author.mention} ({self.message.author}). Staff have been alerted.\n\n" \
                               f"**Message reported:**\n`{msgContent}`" \
                               f"\n\n**Report reason:**\n`{self.reason.value}`"

            if len(self.message.attachments) != 0:
                attachement1 = self.message.attachments[0]
                if attachement1.content_type.startswith("image"):
                    embed.set_image(url=attachement1.url)
                    embedDescription += f"\n\n**Message Image:**"

            embed.description = embedDescription

            await interaction.response.send_message(embed=embed, ephemeral=True)

            # send to reports channel
            embed = discord.Embed()
            embed.set_author(name="Message Report Received", icon_url=self.message.author.display_avatar.url)
            embed.colour = discord.Colour(0x2F3136)

            embedDescription = f'{interaction.user.mention} ({interaction.user}) has reported [this]({self.message.jump_url}) message from {self.message.author.mention} ({self.message.author})\n\n'

            if len(str(self.message.clean_content)) == 0:
                embedDescription += "**Message Content:**\n`No message content`"
            else:
                embedDescription += f'**Message Content:**\n`{self.message.clean_content[0:2000]}`'  # only display first 2000 chars

            embedDescription += f'\n\n**Reported Message\'s Info:**\n' \
                                f'Message ID: `{self.message.id}`\n' \
                                f'Channel: {self.message.channel.mention}\n' \
                                f'Created: {discord.utils.format_dt(self.message.created_at, "F")} ({discord.utils.format_dt(self.message.created_at, "R")})\n' \
                                f'Attachments: `{len(self.message.attachments)}`\n' \
                                f'Reactions: `{len(self.message.reactions)}`\n\n'

            embedDescription += f"**Report reason:**\n`{self.reason.value}`"

            if len(self.message.attachments) != 0:
                attachement1 = self.message.attachments[0]
                if attachement1.content_type.startswith("image"):
                    embed.set_image(url=attachement1.url)
                    embedDescription += f"\n\n**Message Image:**"

            embed.description = embedDescription

            if self.interactionsCog.getReportsAlertRole(interaction.guild) is not None:
                content = f"{self.interactionsCog.getReportsAlertRole(interaction.guild).mention}"
            else:
                content = None

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Jump to message", url=self.message.jump_url))

            await self.interactionsCog.getReportsChannel(interaction.guild).send(
                content=content, embed=embed, view=view,
                allowed_mentions=discord.AllowedMentions(roles=True))

    # User reports
    async def handleUserReport(self, interaction: discord.Interaction, member: discord.Member,
                               attachment: discord.Attachment):

        if isinstance(member, discord.User):
            await interaction.response.send_message("Please use this command in a Discord server.")
            return

        # check that their is a channel setup
        if self.getReportsChannel(member.guild) is None:
            await interaction.response.send_message(embed=self.getNoReportsChannelEmbed(), ephemeral=True)
            return

        # check if user is banned from creating reports
        if self.getReportsBannedRole(member.guild) is not None:
            if interaction.user.get_role(self.getReportsBannedRole(member.guild).id) is not None:
                await interaction.response.send_message(embed=self.getReportsBannedEmbed(member.guild), ephemeral=True)
                return

        # Check not from self
        if not self.bot.get_cog("SettingsCommand").isReportSelfEnabled(interaction.guild):
            if member.id == interaction.user.id:
                await interaction.response.send_message("Sorry, you can't report yourself!", ephemeral=True)
                return

        # Check the member is not a bot
        if not self.bot.get_cog("SettingsCommand").isReportBotsEnabled(interaction.guild):
            if member.bot:
                await interaction.response.send_message("Sorry, you can't report a bot!", ephemeral=True)
                return

        # Check the member is not an admin
        if not self.bot.get_cog("SettingsCommand").isReportAdminsEnabled(interaction.guild):
            if member.guild_permissions.administrator and not member.bot and not member.id == interaction.user.id:
                await interaction.response.send_message("Sorry, you can't report a server administrator!",
                                                        ephemeral=True)
                return

        cooldown = self.check_cooldown(interaction.user)
        if cooldown != 0:
            return await interaction.response.send_message(
                f"Please wait {cooldown:,.2f}s before posting another report!", ephemeral=True)

        await interaction.response.send_modal(
            self.UserReportModal(member=member, interactionsCog=self, attachment=attachment))

    class UserReportModal(ui.Modal, title="Report User"):
        """ A modal for user to enter a reason as to why they are reporting a user """

        def __init__(self, member=None, interactionsCog=None, attachment=None):
            super().__init__()
            self.member = member
            self.interactionsCog = interactionsCog
            self.attachment = attachment

        reason = ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, placeholder="Report reason",
                              required=True, max_length=2000)

        async def on_submit(self, interaction: discord.Interaction):
            # sent to user
            embed = discord.Embed()
            embed.set_author(name="User Reported", icon_url=self.member.display_avatar.url)
            embed.colour = discord.Colour(0x2F3136)
            embedDescription = f"You successfully reported {self.member.mention} ({self.member}). Staff have been alerted.\n\n" \
                               f"**Report reason:**\n`{self.reason.value}`"

            if self.attachment is not None:
                if self.attachment.content_type.startswith("image"):
                    embed.set_image(url=self.attachment.url)
                    embedDescription += f"\n\n**Image Provided:**"

            embed.description = embedDescription
            await interaction.response.send_message(embed=embed, ephemeral=True)

            # send to reports channel
            embed = discord.Embed()

            # get server join time
            if self.member.joined_at is None:
                reportedUserServerJoinTime = "`Unknown`"
            else:
                reportedUserServerJoinTime = f'{discord.utils.format_dt(self.member.joined_at, "F")} ({discord.utils.format_dt(self.member.joined_at, "R")})'  # .timestamp()

            line1 = f'{interaction.user.mention} ({interaction.user}) has reported {self.member.mention} ({self.member})\n\n' \
                    f'**Reported User\'s Info:**\n' \
                    f'Discord Tag: `{self.member}`\n' \
                    f'Discord ID: `{self.member.id}`\n' \
                    f'Account Created: {discord.utils.format_dt(self.member.created_at, "F")} ({discord.utils.format_dt(self.member.created_at, "R")})\n' \
                    f'Joined Server: {reportedUserServerJoinTime}'

            line2 = f"**Report reason:**\n`{self.reason.value}`"

            embedDescription = f"{line1}\n\n{line2}\n"
            embed.set_author(name="User Report Received", icon_url=self.member.display_avatar.url)
            embed.colour = discord.Colour(0x2F3136)
            embed.timestamp = discord.utils.utcnow()

            if self.attachment is not None:
                if self.attachment.content_type.startswith("image"):
                    embed.set_image(url=self.attachment.url)
                    embedDescription += f"\n**Image Provided:**"

            embed.description = embedDescription

            if self.interactionsCog.getReportsAlertRole(interaction.guild) is not None:
                finalMsg = await self.interactionsCog.getReportsChannel(interaction.guild).send(
                    content=f"{self.interactionsCog.getReportsAlertRole(interaction.guild).mention}", embed=embed,
                    allowed_mentions=discord.AllowedMentions(roles=True))
            else:
                finalMsg = await self.interactionsCog.getReportsChannel(interaction.guild).send(embed=embed)

            # get recent messages
            # counter = 0
            # msg = f"\n           {self.member.name}'s Message History For the last 7 days\n\n"
            #
            # for textChannel in interaction.guild.text_channels:
            #     channelHasMessages = False
            #
            #     async for message in textChannel.history(limit=100, after=discord.utils.utcnow() - timedelta(days=7),
            #                                              oldest_first=False):
            #         if message.author.id == self.member.id:
            #             if len(str(message.clean_content)) != 0:
            #                 if not channelHasMessages:
            #                     channelHasMessages = True
            #                     msg += f'\n\n=================== Messages Found in #{textChannel.name} ===================\n\n'
            #
            #                 # print(f"Found message: {message.clean_content}")
            #                 msg += f'{message.created_at.strftime("%d/%m/%y %H:%M:%S")} {message.clean_content}\n'
            #                 counter += 1
            #
            # content = msg
            # buffer = BytesIO(content.encode('utf-8'))
            # file = discord.File(fp=buffer, filename='text.txt')
            #
            # await finalMsg.reply(
            #     content=f"Total Messages from {self.member.name} in {interaction.guild.name} in the last 7 days: `{counter}`",
            #     file=file)


async def setup(bot):
    await bot.add_cog(ReportCommand(bot))
