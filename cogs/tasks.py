import logging
import time

import discord.utils
from discord.ext import commands, tasks

log = logging.getLogger(__name__)


class TaskCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.updater.start()
        self.backup.start()

    async def cog_unload(self):
        self.updater.cancel()
        self.backup.cancel()

    @tasks.loop(hours=24)
    async def backup(self):
        cmd = self.bot.get_command("backup")
        await cmd(None)

    @tasks.loop(minutes=1.0)
    async def updater(self):
        cmd = self.bot.get_command("dump")
        await cmd(None)
        
        # check if the monthly vote count has reset - at midnight UTC. Updates after the first monthly vote on top.gg
        time_now = discord.utils.utcnow()
        if time_now.day == 1 and time_now.hour == 0 and time_now.minute == 0:
            # it is midnight on first day of month so reset monthly votes!
            self.bot.stat_data["monthly_votes"] = 0
            log.info("Reset monthly top.gg votes.")

        # check if there are any vote reminders to send!
        current_time: int = int(time.time())
        if "vote_reminder" in self.bot.vote_data:
            vote_reminders: list = self.bot.vote_data["vote_reminder"]
            reminders_send = []  # list of people that recieved a reminder
            if len(vote_reminders) != 0:
                for discordID in vote_reminders:
                    last_vote = self.bot.vote_data[str(discordID)]["last_vote"]
                    difference = (current_time - last_vote)
                    if difference > 43200:  # num of seconds in 12 hours
                        # if been more than 12 hours - send a reminder
                        user = self.bot.get_user(int(discordID))
                        print(f"Attempting to send vote reminder. User: {user}")
                        if user is None:
                            # user not in cache so attempt to retrieve them
                            user = await self.bot.fetch_user(int(discordID))
                            print(f"User was none attempting an API call. User: {user}")

                        if user is not None:
                            try:
                                await user.send(
                                    f"Hey {user.mention}, it has been 12 hours since you set a vote reminder! You can now vote again at https://top.gg/bot/950765718209720360/vote !",
                                    suppress_embeds=True)
                                log.info(f'Sent vote reminder to {user}!')
                            except discord.HTTPException:
                                pass
                        reminders_send.append(discordID)

            # now remove people from list that have been send a reminder
            for discordID in reminders_send:
                vote_reminders.remove(discordID)

    @updater.before_loop
    async def before_updater(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(TaskCog(bot))
