import logging

from discord.ext import commands

log = logging.getLogger(__name__)


class ContextMenus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # # not supported in cogs yet
    # # Report message
    # @app_commands.context_menu(name='Report Message')
    # async def globalReportMessage(self, interaction: discord.Interaction, message: discord.Message):
    #     await self.bot.get_cog("InteractionsCog").handleMessageReport(interaction, message)
    #
    # @app_commands.context_menu(name='Dev - Report Message')
    # @app_commands.guilds(discord.Object(id=dev_server.DEV_SERVER_ID))
    # async def devReportMessage(self, interaction: discord.Interaction, message: discord.Message):
    #     await self.bot.get_cog("InteractionsCog").handleMessageReport(interaction, message)
    #
    # # Report User
    # @app_commands.context_menu(name='Report User')
    # async def globalReportUser(self, interaction: discord.Interaction, member: discord.Member):
    #     await self.bot.get_cog("InteractionsCog").handleUserReport(interaction, member, None)
    #
    # @app_commands.context_menu(name='Dev - Report User')
    # @app_commands.guilds(discord.Object(id=dev_server.DEV_SERVER_ID))
    # async def devReportUser(self, interaction: discord.Interaction, member: discord.Member):
    #     await self.bot.get_cog("InteractionsCog").handleUserReport(interaction, member, None)


async def setup(bot):
    await bot.add_cog(ContextMenus(bot))
