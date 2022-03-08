import logging

from discord.ext import commands

log = logging.getLogger(__name__)


class OtherCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("loaded")


def setup(bot):
    bot.add_cog(OtherCog(bot))
