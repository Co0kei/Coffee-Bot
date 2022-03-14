import json
import logging

from discord.ext import commands, tasks

log = logging.getLogger(__name__)


class TaskCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.updater.start()

    # self.update_topdotgg_stats.start()

    async def cog_unload(self):
        self.updater.cancel()

    # self.update_topdotgg_stats.stop()

    @tasks.loop(minutes=1.0)
    async def updater(self):
        # save commands used
        data = {"commands_used": self.bot.commands_used}
        with open('stats.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            f.close()

        # log.info("[TASK] Saved commands_used: " + str(self.bot.commands_used))

        # save guild settings
        with open('guild_settings.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.guild_settings, f, ensure_ascii=False, indent=4)
            f.close()

        # log.info("[TASk] Saved guild_settings: " + str(self.bot.guild_settings))

    @updater.before_loop
    async def before_updater(self):
        await self.bot.wait_until_ready()

    # @tasks.loop(minutes=30)
    # async def update_topdotgg_stats(self):
    #     """This function runs every 30 minutes to automatically update the server count."""
    #     try:
    #         await self.bot.topggpy.post_guild_count()
    #         print(f"Posted server count ({self.bot.topggpy.guild_count})")
    #     except Exception as e:
    #         print(f"Failed to post server count\n{e.__class__.__name__}: {e}")


async def setup(bot):
    await bot.add_cog(TaskCog(bot))
