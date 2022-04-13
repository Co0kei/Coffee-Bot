import logging
from collections import Counter

from discord.ext import commands

log = logging.getLogger(__name__)


class GatewayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_socket_event_type(self, event_type):
        self.bot.socket_stats[event_type] += 1


async def setup(bot):
    if not hasattr(bot, 'socket_stats'):
        bot.socket_stats = Counter()
    await bot.add_cog(GatewayCog(bot))
