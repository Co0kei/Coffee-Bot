import logging

from discord.ext import commands

log = logging.getLogger(__name__)


class LoggerCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    class LoggingFilter(logging.Filter):
        def filter(self, record):
            if record.getMessage().startswith('Shard ID None has sent the RESUME payload.') \
                    or record.getMessage().startswith('Shard ID None has successfully RESUMED session') \
                    or record.getMessage().startswith('Shard ID None has sent the IDENTIFY payload.') \
                    or record.getMessage().startswith('Shard ID None has connected to Gateway: ["') \
                    or record.getMessage().startswith('logging in using static token') \
                    or record.getMessage().startswith('PyNaCl is not installed, voice will NOT be supported') \
                    or record.getMessage().startswith('Got a request to RESUME the websocket.') \
                    or record.getMessage().startswith('Websocket closed'):
                return False  # dont log it
            return True

    async def cog_load(self):
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%I:%M:%S %p')

        logging.getLogger('discord.gateway').addFilter(self.LoggingFilter())
        logging.getLogger('discord.client').addFilter(self.LoggingFilter())
        logging.getLogger('aiohttp.access').setLevel("WARNING")


async def setup(bot):
    await bot.add_cog(LoggerCog(bot))
