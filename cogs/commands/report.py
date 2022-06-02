import logging
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional, Union

import discord
from discord import app_commands, ui
from discord.ext import commands

log = logging.getLogger(__name__)


class ReportCommand(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.on_cooldown = {}

        self.messageContextMenu = app_commands.ContextMenu(name='Report Message', callback=self.globalReportMessage)
        self.bot.tree.add_command(self.messageContextMenu)

        self.userContextMenu = app_commands.ContextMenu(name='Report User', callback=self.globalReportUser)
        self.bot.tree.add_command(self.userContextMenu)

        self.resetReportMenu = app_commands.ContextMenu(name='Reset Report', callback=self.resetReport)
        self.bot.tree.add_command(self.resetReportMenu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.messageContextMenu.name, type=self.messageContextMenu.type)
        self.bot.tree.remove_command(self.userContextMenu.name, type=self.userContextMenu.type)
        self.bot.tree.remove_command(self.resetReportMenu.name, type=self.resetReportMenu.type)

    # Setup Slash Command & Context Menus
    @app_commands.command(name='report', description='Report a member with a reason for staff to see.')
    @app_commands.describe(member='The member you are reporting.',
                           image='You can upload an image for staff to see if you wish.')
    @app_commands.guild_only()
    async def globalReportCommand(self, interaction: discord.Interaction, member: discord.User, image: Optional[discord.Attachment] = None):
        await self.handleUserReport(interaction, member, image)

    @app_commands.guild_only()
    async def globalReportMessage(self, interaction: discord.Interaction, message: discord.Message):
        await self.handleMessageReport(interaction, message)

    @app_commands.guild_only()
    async def globalReportUser(self, interaction: discord.Interaction, member: discord.Member):
        await self.handleUserReport(interaction, member, None)

    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def resetReport(self, interaction: discord.Interaction, message: discord.Message):
        await self.reset_report_state(interaction, message)

    # Methods
    def getNoReportsChannelEmbed(self) -> discord.Embed:
        embed = discord.Embed(title="Configuration Error")
        embed.description = f'This Discord server has not been configured yet.\nPlease ask a server administrator to use the **/settings** command and set a reports channel.' \
                            f'\nCurrently I don\'t know which channel to send reports to!'
        embed.colour = discord.Colour.dark_red()
        embed.set_image(url="https://cdn.discordapp.com/attachments/767356269873987615/968971013255749652/unknown.png")
        return embed

    def getReportsBannedEmbed(self, guild: discord.Guild) -> discord.Embed:
        settingsCog = self.bot.get_cog("SettingsCommand")
        embed = discord.Embed(title="Reports Ban")
        embed.description = f'You have the {settingsCog.getReportsBannedRole(guild).mention} role which is preventing you from creating reports.'
        embed.colour = discord.Colour.red()
        return embed

    def check_cooldown(self, member: discord.Member) -> int:
        cooldown_end = self.on_cooldown.get(member.id)
        if member.guild_permissions.manage_guild or cooldown_end is None or cooldown_end < datetime.now():  # If there's no cooldown or it's over or privilaged member
            self.on_cooldown[member.id] = datetime.now() + timedelta(seconds=10)  # Add the datetime of the cooldown's end to the dictionary
            return 0  # allow the command to run
        else:
            return (cooldown_end - datetime.now()).total_seconds()

    # Message reports
    async def handleMessageReport(self, interaction: discord.Interaction, message: discord.Message):

        if message.guild is None:
            return await interaction.response.send_message("Please use this command in a Discord server.")

        if message.author.id == self.bot.user.id:
            return await interaction.response.send_message("Sorry, my message is too awesome to be reported!", ephemeral=True)

        settingsCog = self.bot.get_cog("SettingsCommand")

        if not settingsCog.getReportsChannel(message.guild):
            return await interaction.response.send_message(embed=self.getNoReportsChannelEmbed(), ephemeral=True)

        if settingsCog.getReportsBannedRole(message.guild):
            if interaction.user.get_role(settingsCog.getReportsBannedRole(message.guild).id):
                return await interaction.response.send_message(embed=self.getReportsBannedEmbed(message.guild), ephemeral=True)

        if not settingsCog.isReportSelfEnabled(message.guild):
            if message.author.id == interaction.user.id:
                return await interaction.response.send_message("Sorry, you can't report your own messages!", ephemeral=True)

        if not settingsCog.isReportBotsEnabled(message.guild):
            if message.author.bot:
                return await interaction.response.send_message("Sorry, you can't report a bot's message!", ephemeral=True)

        if not settingsCog.isReportAdminsEnabled(interaction.guild):
            if message.author.guild_permissions.administrator and not message.author.bot and not message.author.id == interaction.user.id:
                return await interaction.response.send_message("Sorry, you can't report a server administrator's message!", ephemeral=True)

        await interaction.response.send_modal(self.MessageReportModal(message=message, settingsCog=settingsCog, reportsCog=self))

    class MessageReportModal(ui.Modal, title="Report Message"):

        def __init__(self, message=None, settingsCog=None, reportsCog=None):
            super().__init__()
            self.message = message
            self.settingsCog = settingsCog
            self.reportsCog = reportsCog

        reason = ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, placeholder="Report reason",
                              required=True, max_length=2000)

        async def on_error(self, error: Exception, interaction: discord.Interaction) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def on_submit(self, interaction: discord.Interaction):

            # Check cooldown
            cooldown = self.reportsCog.check_cooldown(interaction.user)
            if cooldown != 0:
                return await interaction.response.send_message(f"Please wait {cooldown:,.2f}s before posting another report!", ephemeral=True)

            # Send to user
            embed = discord.Embed(colour=discord.Colour(0x2F3136))
            embed.set_author(name="Message Reported", icon_url=self.message.author.display_avatar.url)
            reportReason = self.reason.value.replace("`", "")
            embed.description = f"You successfully reported [this]({self.message.jump_url}) message from {self.message.author.mention} ({self.message.author}). Staff have been alerted." \
                                f"\n\n**Report reason:**\n`{reportReason}`"
            for attachment in self.message.attachments:
                if attachment.content_type.startswith("image"):
                    embed.set_image(url=attachment.url)
                    embed.description += f"\n\n**Message Image:**"
                    break
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Jump to message", url=self.message.jump_url))
            await interaction.response.send_message(embed=embed, ephemeral=True, view=view)

            # Send to reports channel
            embed = discord.Embed(colour=discord.Colour(0x2F3136), timestamp=discord.utils.utcnow(),
                                  description=f'{interaction.user.mention} ({interaction.user}) has reported [this]({self.message.jump_url}) message '
                                              f'from {self.message.author.mention} ({self.message.author})!')
            embed.set_author(name="Message Report Received", icon_url=interaction.user.display_avatar.url)
            embed.set_thumbnail(url=self.message.author.display_avatar.url)
            embed.description += f'\n\n**Reported Message\'s Info:**\n' \
                                 f'Message ID: `{self.message.id}`\n' \
                                 f'Channel: {self.message.channel.mention}\n' \
                                 f'Created: {discord.utils.format_dt(self.message.created_at, "F")} ({discord.utils.format_dt(self.message.created_at, "R")})\n' \
                                 f'Attachments: `{len(self.message.attachments)}`\n' \
                                 f'Reactions: `{len(self.message.reactions)}\n`'

            if self.message.content:
                content = self.message.clean_content.replace("`", "")  # remove so no messed up format
            else:
                content = "None"
            embed.description += f'Content: `{content}`'

            embed.description += f"\n\n**Report reason:**\n`{reportReason}`"

            for attachment in self.message.attachments:
                if attachment.content_type.startswith("image"):
                    embed.set_image(url=attachment.url)
                    embed.description += f"\n\n**Message Image:**"
                    break

            # Check embed size
            file = None
            content = None
            if len(embed.description) > 4096 or len(embed) > 6000:
                # attach as a file
                embed = None
                content = "**Message Report!**"
                fileContent = f'{interaction.user} has reported a message from {self.message.author}\n\n' \
                              f'Message ID: {self.message.id}\n' \
                              f'Channel: #{self.message.channel}\n' \
                              f'Created (UTC): {self.message.created_at.strftime("%Y-%m-%d %H:%M-%S")}\n' \
                              f'Attachments: {len(self.message.attachments)}\n' \
                              f'Content: {self.message.clean_content}' \
                              f"\n\nReport reason:\n{self.reason.value}"

                buffer = BytesIO(fileContent.encode('utf-8'))
                file = discord.File(fp=buffer, filename='message_report.txt')

            if self.settingsCog.getReportsAlertRole(interaction.guild):
                if content:
                    content = f"{self.settingsCog.getReportsAlertRole(interaction.guild).mention}\n{content}"
                else:
                    content = f"{self.settingsCog.getReportsAlertRole(interaction.guild).mention}"

            #view: discord.ui.View = discord.ui.View()
            view.add_item(discord.ui.Button(label="Actioned", custom_id="Actioned", style=discord.ButtonStyle.green))
            view.add_item(discord.ui.Button(label="False Positive", custom_id="False Positive", style=discord.ButtonStyle.red))

            await self.settingsCog.getReportsChannel(interaction.guild).send(
                content=content, embed=embed, view=view, file=file,
                allowed_mentions=discord.AllowedMentions(roles=True))

    # User reports
    async def handleUserReport(self, interaction: discord.Interaction, member: Union[discord.Member, discord.User], attachment: Optional[discord.Attachment]):

        if interaction.guild is None:
            return await interaction.response.send_message("Please use this command in a Discord server.")

        if isinstance(member, discord.User):
            return await interaction.response.send_message("This user is no longer in this server.", ephemeral=True)

        if member.id == self.bot.user.id:
            return await interaction.response.send_message("Sorry, I am too awesome to be reported!", ephemeral=True)

        settingsCog = self.bot.get_cog("SettingsCommand")

        if not settingsCog.getReportsChannel(member.guild):
            return await interaction.response.send_message(embed=self.getNoReportsChannelEmbed(), ephemeral=True)

        if settingsCog.getReportsBannedRole(member.guild):
            if interaction.user.get_role(settingsCog.getReportsBannedRole(member.guild).id):
                return await interaction.response.send_message(embed=self.getReportsBannedEmbed(member.guild), ephemeral=True)

        if not settingsCog.isReportSelfEnabled(interaction.guild):
            if member.id == interaction.user.id:
                return await interaction.response.send_message("Sorry, you can't report yourself!", ephemeral=True)

        if not settingsCog.isReportBotsEnabled(interaction.guild):
            if member.bot:
                return await interaction.response.send_message("Sorry, you can't report a bot!", ephemeral=True)

        if not settingsCog.isReportAdminsEnabled(interaction.guild):
            if member.guild_permissions.administrator and not member.bot and not member.id == interaction.user.id:
                return await interaction.response.send_message("Sorry, you can't report a server administrator!", ephemeral=True)

        await interaction.response.send_modal(self.UserReportModal(member=member, settingsCog=settingsCog, reportsCog=self, attachment=attachment))

    class UserReportModal(ui.Modal, title="Report User"):

        def __init__(self, member=None, settingsCog=None, reportsCog=None, attachment=None):
            super().__init__()
            self.member = member
            self.settingsCog = settingsCog
            self.reportsCog = reportsCog
            self.attachment = attachment

        reason = ui.TextInput(label='Reason', style=discord.TextStyle.paragraph, placeholder="Report reason",
                              required=True, max_length=2000)

        async def on_error(self, error: Exception, interaction: discord.Interaction) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def on_submit(self, interaction: discord.Interaction):

            # Check cooldown
            cooldown = self.reportsCog.check_cooldown(interaction.user)
            if cooldown != 0:
                return await interaction.response.send_message(f"Please wait {cooldown:,.2f}s before posting another report!", ephemeral=True)

            # sent to user
            reportReason = self.reason.value.replace("`", "")
            embed = discord.Embed(colour=discord.Colour(0x2F3136), description=f"You successfully reported {self.member.mention} ({self.member}). Staff have been alerted.\n\n" \
                                                                               f"**Report reason:**\n`{reportReason}`")
            embed.set_author(name="User Reported", icon_url=self.member.display_avatar.url)
            if self.attachment and self.attachment.content_type.startswith("image"):
                embed.set_image(url=self.attachment.url)
                embed.description += f"\n\n**Image Provided:**"
            await interaction.response.send_message(embed=embed, ephemeral=True)

            # send to reports channel
            if self.member.joined_at is None:
                reportedUserServerJoinTime = "`Unknown`"
            else:
                reportedUserServerJoinTime = f'{discord.utils.format_dt(self.member.joined_at, "F")} ({discord.utils.format_dt(self.member.joined_at, "R")})'

            embed = discord.Embed(colour=discord.Colour(0x2F3136), timestamp=discord.utils.utcnow(),
                                  description=f"" \
                                              f'{interaction.user.mention} ({interaction.user}) has reported {self.member.mention} ({self.member})!\n\n' \
                                              f'**Reported User\'s Info:**\n' \
                                              f'Discord Tag: `{self.member}`\n' \
                                              f'Discord ID: `{self.member.id}`\n' \
                                              f'Account Created: {discord.utils.format_dt(self.member.created_at, "F")} ({discord.utils.format_dt(self.member.created_at, "R")})\n' \
                                              f'Joined Server: {reportedUserServerJoinTime}\n\n'
                                              f"**Report reason:**\n`{reportReason}`")

            embed.set_author(name="User Report Received", icon_url=interaction.user.display_avatar.url)
            embed.set_thumbnail(url=self.member.display_avatar.url)

            if self.attachment and self.attachment.content_type.startswith("image"):
                embed.set_image(url=self.attachment.url)
                embed.description += f"\n\n**Image Provided:**"

            if self.settingsCog.getReportsAlertRole(interaction.guild):
                content = f"{self.settingsCog.getReportsAlertRole(interaction.guild).mention}"
            else:
                content = None

            view: discord.ui.View = discord.ui.View()
            view.add_item(discord.ui.Button(label="Actioned", custom_id="Actioned", style=discord.ButtonStyle.green))
            view.add_item(discord.ui.Button(label="False Positive", custom_id="False Positive", style=discord.ButtonStyle.red))

            await self.settingsCog.getReportsChannel(interaction.guild).send(
                content=content, embed=embed, view=view,
                allowed_mentions=discord.AllowedMentions(roles=True))

    async def reset_report_state(self, interaction: discord.Interaction, message: discord.Message):
        """ Context menu command to reset a reports handled state - used by admins if mods mess up """

        if message.author != self.bot.user:
            return await interaction.response.send_message("This command can only be used on a report.", ephemeral=True)

        if len(message.embeds) != 1:
            return await interaction.response.send_message("This command can only be used on a report.", ephemeral=True)

        embed = message.embeds[0]
        if "Report Received" not in embed.author.name:
            return await interaction.response.send_message("This command can only be used on a report.", ephemeral=True)


        split_description = embed.description.split("\n")

        if "false" in split_description[-1] or "handled" in split_description[-1]:
            split_description = split_description[:-1]
            split_description.append(f"{interaction.user.mention} ({discord.utils.escape_markdown(str(interaction.user))}) reset the report state.")
            embed.description = "\n".join(split_description)

            embed.colour = discord.Colour.dark_theme()

            view: discord.ui.View = discord.ui.View.from_message(message)
            for button in view.children:
                if not button.url:
                    button.disabled = False

            await message.edit(embed=embed, view=view)
            await interaction.response.send_message("This report has been reset.", ephemeral=True)

        else:
            await interaction.response.send_message("This report has not been marked as handled or false yet.", ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        # Listen for button interactions
        if interaction.type == discord.InteractionType.component:

            button = interaction.data["custom_id"]
            msg = interaction.message

            if button == "Actioned":
                view: discord.ui.View = discord.ui.View.from_message(msg)
                for button in view.children:
                    if not button.url:
                        button.disabled = True

                embed: discord.Embed = msg.embeds[0]

                # remove reset message
                split_description = embed.description.split("\n")
                if "reset" in split_description[-1]:
                    split_description = split_description[:-2]
                    embed.description = "\n".join(split_description)
                #

                embed.description += f"\n\n<:tick:873224615881748523> {interaction.user.mention} ({discord.utils.escape_markdown(str(interaction.user))}) marked this report as handled."
                embed.colour = discord.Colour.green()

                await interaction.response.edit_message(embed=embed, view=view)

            elif button == "False Positive":
                view: discord.ui.View = discord.ui.View.from_message(msg)
                for button in view.children:
                    if not button.url:
                        button.disabled = True

                embed: discord.Embed = msg.embeds[0]

                # remove reset message
                split_description = embed.description.split("\n")
                if "reset" in split_description[-1]:
                    split_description = split_description[:-2]
                    embed.description = "\n".join(split_description)
                #

                embed.description += f"\n\n<:cross:872834807476924506> {interaction.user.mention} ({discord.utils.escape_markdown(str(interaction.user))}) marked this as a false report."
                embed.colour = discord.Colour.dark_red()

                await interaction.response.edit_message(embed=embed, view=view)



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
