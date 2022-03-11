import json
import logging

from discord.ext import commands, tasks

log = logging.getLogger(__name__)


class TaskCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.updater.start()

    def cog_unload(self):
        if self.updater.is_running():
            self.updater.cancel()

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


def setup(bot):
    bot.add_cog(TaskCog(bot))
