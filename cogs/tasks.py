import asyncio
import logging
import time
import traceback
from typing import Any

import discord.utils
from discord.ext import commands, tasks

log = logging.getLogger(__name__)


class TaskCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.updater.start()
        self.vote_reminder.start()

    async def cog_unload(self):
        self.updater.cancel()
        self.vote_reminder.cancel()

    async def check_first_vote_reminder(self):
        """ Check if its been 12 hours since a vote. But not any longer."""
        current_time: int = int(time.time())
        for discord_id, last_vote in self.bot.stat_data["vote_reminders"].items():
            difference = (current_time - last_vote)
            # log.info(f'{discord_id} {last_vote} {difference}')
            if 43198 <= difference <= 43262:  # num of seconds in 12 hours # 0 < difference < 60:  #
                user = await self.bot.get_or_fetch_user(int(discord_id))
                log.info(f"Attempting to send vote reminder to {user}")
                if user:
                    try:
                        await user.send(
                            f"Hey {user.mention}, it has been 12 hours since you last voted! You can now vote again at https://top.gg/bot/950765718209720360/vote !",
                            suppress_embeds=True)
                        log.info(f'Sent vote reminder to {user}!')
                    except discord.HTTPException:
                        pass

    async def check_followup_vote_reminders(self):
        """ Check if its been longer then 16 hours since someone has voted. This is called every 4 hours """

        to_remove = [] #list of people to remove from reminders

        current_time: int = int(time.time())
        for discord_id, last_vote in self.bot.stat_data["vote_reminders"].items():
            difference = (current_time - last_vote)
            # log.info(f'{discord_id} {last_vote} {difference}')
            if difference > 57600:  # num of seconds in 16 hours - so reminders send every 4 hours after if you don't vote before that
                user = await self.bot.get_or_fetch_user(int(discord_id))
                log.info(f"Attempting to send vote reminder to {user}")
                if user:
                    try:
                        if difference > 259200:
                            # if its been more than 3 days then say they will no longer receive reminders
                            await user.send(
                                f"Hey {user.mention}, you last voted <t:{last_vote}:R>! You can vote again at https://top.gg/bot/950765718209720360/vote ! "
                                f"You have not voted in over 3 days, so will now stop receiving reminders.",
                                suppress_embeds=True)
                            to_remove.append(discord_id)
                            log.info(f'Sent vote reminder stopping notification to {user}!')
                        else:
                            await user.send(
                                f"Hey {user.mention}, you last voted <t:{last_vote}:R>! You can vote again at https://top.gg/bot/950765718209720360/vote ! "
                                f"(You can disable reminders on the /vote command)",
                                suppress_embeds=True)
                            log.info(f'Sent vote reminder to {user}!')
                    except discord.HTTPException:
                        # they blocked the bot or no mutual guilds
                        to_remove.append(discord_id)
                else:
                    # they no longer in guild with bot i guess
                    to_remove.append(discord_id)

        for discord_id in to_remove:
            del self.bot.stat_data["vote_reminders"][discord_id]
            log.info(f'Removed {discord_id} from vote reminders.')


    @tasks.loop(hours=4)
    async def vote_reminder(self):
        await self.check_followup_vote_reminders()

    @vote_reminder.before_loop
    async def before_vote_reminder(self):
        await self.bot.wait_until_ready()

    @vote_reminder.error
    async def on_vote_reminder_error(self, *args: Any) -> None:
        exception: Exception = args[-1]
        log.error(f'Unhandled exception in internal background task vote_reminder')
        traceback.print_exception(type(exception), exception, exception.__traceback__)

        await asyncio.sleep(5)
        log.info("Restarting task...")

        self.vote_reminder.restart()

    @tasks.loop(minutes=1.0)
    async def updater(self):
        cmd = self.bot.get_command("dump")
        if cmd:  # make sure not NONE
            await cmd(None)

        # check if the monthly vote count has reset - at midnight UTC. Updates after the first monthly vote on top.gg
        time_now = discord.utils.utcnow()
        if time_now.day == 1 and time_now.hour == 0 and time_now.minute == 0:
            # it is midnight on first day of month so reset monthly votes!
            self.bot.stat_data["last_months_votes"] = self.bot.stat_data["monthly_votes"]
            self.bot.stat_data["monthly_votes"] = 0
            log.info("Reset monthly top.gg votes.")

        # Do backup once per day
        if time_now.hour == 0 and time_now.minute == 0:
            cmd = self.bot.get_command("backup")
            if cmd:
                await cmd(None)
                log.info("Completed data backup.")

        # check if there are any vote reminders to send!
        await self.check_first_vote_reminder()

    @updater.before_loop
    async def before_updater(self):
        await self.bot.wait_until_ready()

    @updater.error
    async def on_updater_error(self, *args: Any) -> None:
        exception: Exception = args[-1]
        log.error(f'Unhandled exception in internal background task updater')
        traceback.print_exception(type(exception), exception, exception.__traceback__)

        await asyncio.sleep(5)
        log.info("Restarting task...")

        self.updater.restart()


async def setup(bot):
    await bot.add_cog(TaskCog(bot))
