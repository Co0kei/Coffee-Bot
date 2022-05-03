import datetime
import logging
import random
import sys
import time

import discord
import topgg
from discord.ext import commands

from constants import *

log = logging.getLogger(__name__)


class VoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self) -> None:
        self.vote_hook = discord.Webhook.from_url(VOTE_HOOK_URL, session=self.bot.session)
        if sys.platform != DEV_PLATFORM:  # top.gg things
            self.bot.topggpy = topgg.DBLClient(self.bot, TOPGG_TOKEN)
            self.topgg_webhook = topgg.WebhookManager(self.bot).dbl_webhook(TOPGG_URL, TOPGG_PASSWORD)
            await self.topgg_webhook.run(TOPGG_PORT)

    async def cog_unload(self) -> None:
        if sys.platform != DEV_PLATFORM:  # top.gg things
            await self.bot.topggpy.close()
            await self.topgg_webhook.close()

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        """ An event that is called whenever someone votes for the bot on Top.gg. """

        if data["type"] == "test":
            """ Called whenever someone tests the webhook system for your bot on Top.gg. """
            log.info(f'Received a test vote from {data["user"]}')
            return

        discord_ID = str(data["user"])  # just in case they change in future: force string

        query = "SELECT total_coins, vote_streak, last_vote FROM user_votes WHERE user_id=$1;"
        user_vote_data = await self.bot.pool.fetchrow(query, int(discord_ID))

        if user_vote_data:
            first_vote = False
            total_coins = user_vote_data[0]
            vote_streak = user_vote_data[1]
            last_vote = user_vote_data[2]
        else:
            first_vote = True
            total_coins = 0

        # get coins
        is_weekend = data["is_weekend"]
        if is_weekend:
            coins_received = random.randint(40, 50)
            self.bot.stat_data["monthly_votes"] += 2  # weekend votes count as 2!
            self.bot.stat_data["total_votes"] += 2
        else:
            coins_received = random.randint(20, 25)
            self.bot.stat_data["monthly_votes"] += 1
            self.bot.stat_data["total_votes"] += 1

        total_coins += coins_received

        current_timestamp = int(time.time())
        current_time = datetime.datetime.fromtimestamp(current_timestamp)

        # check vote streak
        if first_vote:
            vote_streak = 1
            streak_message = f' You now have a vote streak of **1**. Remember to vote for me at least every 24 hours to keep your streak!'
        else:
            # They have voted before! Check if their vote streak increases or gets reset!
            difference = (current_time - last_vote)
            if difference > datetime.timedelta(seconds=86400):  # num of seconds in a day
                vote_streak = 1  # RESET STREAK - starts at 1
                streak_message = f' Your vote streak is now **1** as your previous vote was more than 24 hours ago (<t:{int(last_vote.timestamp())}:R>).'
            else:
                vote_streak += 1  # increment streak by 1
                streak_message = f' Your vote streak is now **{vote_streak:,}**.'

        last_vote = current_time  # update last vote time

        # Insert new vote to database
        query1 = "INSERT INTO votes(user_id, coins, time, is_weekend) VALUES($1, $2, $3, $4);"
        # Upsert user_votes database
        if first_vote:
            query2 = "INSERT INTO user_votes (user_id, total_coins, vote_streak, last_vote) VALUES($1, $2, $3, $4);"
        else:
            query2 = "UPDATE user_votes SET total_coins=$2, vote_streak=$3, last_vote=$4 WHERE user_id=$1;"

        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query1, int(discord_ID), coins_received, current_time, is_weekend)
                await conn.execute(query2, int(discord_ID), total_coins, vote_streak, last_vote)

        user = self.bot.get_user(int(discord_ID)) or await self.bot.fetch_user(int(discord_ID))

        if first_vote:
            msg = f"Thank you very much for taking the time to vote for me! :hugging: You have received **{coins_received:,}**:coin:!"
        else:
            msg = "Thank you very much for voting for me! :hugging: " \
                  f"You have received **{coins_received:,}**:coin: and " \
                  f"now have a total of **{total_coins:,}**:coin:!"
        msg += streak_message
        if is_weekend:
            msg += "\n\nYou got **DOUBLE** coins as you voted on a weekend when each vote counts as two! :partying_face:"

        reminder = f'\n\nWould you like me to send you a reminder <t:{current_timestamp + 43200}:R> when you can vote again? :pleading_face: ' \
                   f'You can disable this at any point on the /vote command.\n'

        if user:
            try:
                # Try to send the user a DM
                if discord_ID in self.bot.stat_data["vote_reminders"]:
                    self.bot.stat_data["vote_reminders"][discord_ID] = current_timestamp
                    await user.send(f"{msg}")
                else:
                    view = self.ReminderButtons(bot=self.bot, last_vote=current_timestamp, msg=msg)
                    view.message = await user.send(f"{msg}{reminder}", view=view)
            except discord.HTTPException:
                pass

        # Log it
        embed = discord.Embed(colour=discord.Colour.dark_gold(), description=msg, timestamp=discord.utils.utcnow())
        if user:
            embed.set_author(name=f'Vote from {user}', icon_url=user.display_avatar.url)
            log.info(f'Received a vote from {user}')
        else:
            embed.set_author(name=f'Vote from {discord_ID}')
            log.info(f'Received a vote from {discord_ID}')

        if sys.platform != DEV_PLATFORM:
            await self.vote_hook.send(embed=embed)

    class ReminderButtons(discord.ui.View):

        def __init__(self, timeout=300, bot=None, last_vote=None, msg=None):
            super().__init__(timeout=timeout)
            self.message = None  # the original interaction message
            self.bot = bot  # the main bot instance
            self.last_vote = last_vote  # last vote
            self.msg = msg  # the vote message content without reminder bit

        async def on_timeout(self) -> None:
            await self.message.edit(view=None)

        async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        @discord.ui.button(label='Yes, remind me!', style=discord.ButtonStyle.green)
        async def voteReminders(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.bot.stat_data["vote_reminders"][str(interaction.user.id)] = self.last_vote
            log.info(self.bot.stat_data["vote_reminders"])

            content = f"{self.msg}\n\nThanks! I will send you a message in 12 hours! :star_struck:"
            await interaction.response.edit_message(content=content, view=None)
            self.stop()

        @discord.ui.button(label='No :(', style=discord.ButtonStyle.grey)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            content = f"{self.msg}\n\nOK. I will not send any vote reminders. :cry:"
            await interaction.response.edit_message(content=content, view=None)
            self.stop()


async def setup(bot):
    await bot.add_cog(VoteCog(bot))
