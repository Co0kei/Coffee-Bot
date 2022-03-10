import logging

import discord
from discord import ui
from discord.ext import commands

log = logging.getLogger(__name__)


class InteractionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("loaded")

    def getReportsChannel(self, guild: discord.Guild) -> discord.TextChannel:
        reportsChannel = None;
        for textChannel in guild.text_channels:
            if "reports" in textChannel.name:
                reportsChannel = textChannel
                break
        return reportsChannel

    # Message reports

    def getNoReportsChannelEmbed(self) -> discord.Embed:
        embed = discord.Embed(title="Configuration Error")
        embed.description = f'This Discord server has not been configured yet.\nPlease ask a server administrator to create a text channel named \'reports\'' \
                            f'\nCurrently I don\'t know which channel to send reports to!'
        embed.colour = discord.Colour.red()
        return embed

    async def handleMessageReport(self, interaction: discord.Interaction, message: discord.Message):

        log.info(f'{interaction.user} used command \'Report Message\'')
        self.bot.commands_used += 1

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

        log.info(f'{interaction.user} used command \'Report User\'')
        self.bot.commands_used += 1

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
        log.info(f'{interaction.user} used command \'help\'')
        self.bot.commands_used += 1

        embed = discord.Embed(title="Help", description=f'Support server: https://discord.gg/rcUzqaQN8k')
        embed.add_field(name="Commands", value=
        f'/help - Displays help menu\n'
        f'/report - Used to report a user as mobile devices do not support context menus', inline=False)

        embed.add_field(name="Setup", value=
        f'To set me up in your server just invite me, using the button on my profile, and then create a channel called \'reports\'! '
        f'Now you can right click on a user or message then scroll to Apps and click the report button!\n'
        f'Discord is sometimes annoying so if no Apps section is showing after you right click a message or user. then do CTRL + R to reload Discord',
                        inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=False)


def setup(bot):
    bot.add_cog(InteractionsCog(bot))
