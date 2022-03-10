import json
import logging

from discord.ext import commands, tasks

log = logging.getLogger(__name__)


class TaskCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.updater.start()

    def cog_unload(self):
        self.updater.cancel()

    @tasks.loop(minutes=5.0)
    async def updater(self):
        with open('stats.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            f.close()

        data["commands_used"] = self.bot.commands_used

        with open('stats.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            f.close()

        log.info("Saved commands_used: " + str(self.bot.commands_used))

    @updater.before_loop
    async def before_printer(self):
        with open('stats.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.bot.commands_used = data["commands_used"]  # load command usage
        f.close()

        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(TaskCog(bot))
