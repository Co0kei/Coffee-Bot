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

        discordID = str(data["user"])  # just in case they change in future: force string

        # create new vote object
        is_weekend = data["is_weekend"]
        if is_weekend:
            coins = random.randint(40, 50)
            self.bot.stat_data["monthly_votes"] += 2  # weekend votes count as 2!
            self.bot.stat_data["total_votes"] += 2
        else:
            self.bot.stat_data["monthly_votes"] += 1
            self.bot.stat_data["total_votes"] += 1
            coins = random.randint(20, 25)

        current_time: int = int(time.time())

        vote_object: dict = {"time": current_time,
                             "is_weekend": is_weekend,
                             "coins": coins}

        # check if they have voted before
        if discordID in self.bot.vote_data:
            # They have voted before! Check if their vote streak increases or gets reset!
            first_vote: bool = False
            time_last_vote: int = self.bot.vote_data[discordID]["last_vote"]

            difference = (current_time - time_last_vote)
            if difference > 86400:  # num of seconds in a day
                # RESET STREAK
                self.bot.vote_data[discordID]["vote_streak"] = 1  # streak starts at 1
                streak_message = f' Your vote streak is now **1** as your previous vote was more than 24 hours ago (<t:{time_last_vote}:R>).'
            else:
                # increment streak by 1
                self.bot.vote_data[discordID]["vote_streak"] += 1
                streak_message = f' Your vote streak is now **{self.bot.vote_data[discordID]["vote_streak"]}**.'

            # update last vote time
            self.bot.vote_data[discordID]["last_vote"] = current_time

        else:
            # initiate an object for the user
            first_vote: bool = True
            self.bot.vote_data[discordID] = {"vote_streak": 1,
                                             "last_vote": current_time,
                                             "vote_history": []}
            streak_message = f' You now have a vote streak of **1**. Remember to vote for me at least every 24 hours to keep your streak!'

        vote_history: list = self.bot.vote_data[discordID]["vote_history"]

        # append new vote
        vote_history.append(vote_object)

        # Now get their total coins
        total_coins = sum([element["coins"] for element in vote_history])

        # Try to send the user a DM
        user = self.bot.get_user(int(discordID))

        if user is None:
            # user could not in cache so attempt to retrieve them
            user = await self.bot.fetch_user(int(discordID))

        if user is not None:
            try:
                if first_vote:
                    msg = "Thank you very much for taking the time to vote for me! :hugging: " \
                          f"As a token of appreciation you have received **{coins}**:coin:!"
                else:
                    msg = "Thank you very much for voting for me! :hugging: " \
                          f"You have received **{coins}**:coin: as a reward and " \
                          f"now have a total of **{total_coins}**:coin:!"

                msg += streak_message

                if is_weekend:
                    msg += "\n\nYou got **DOUBLE** coins as you voted on a weekend when each vote counts as two! :partying_face:"

                msg += f'\n\nWould you like me to send you a reminder <t:{current_time + 43200}:R> when you can vote again? :pleading_face:'

                view = self.ReminderButtons(bot=self.bot)

                oring_msg = await user.send(msg, view=view)

                view.setOriginalMessage(oring_msg)  # pass the original message into the class

            except discord.HTTPException:
                pass

        # log it
        embed = discord.Embed(colour=discord.Colour.dark_gold())
        if user is not None:
            embed.set_author(name=f'Vote from {user}', icon_url=user.display_avatar.url)
            log.info(f'Received a vote from {user}')
        else:
            embed.set_author(name=f'Vote from {discordID}')
            log.info(f'Received a vote from {discordID}')

        embed.add_field(name='Coins received', value=f'{coins}:coin:', inline=False)
        embed.add_field(name='Total Coins', value=f'{total_coins:,}:coin:', inline=False)
        embed.add_field(name='Streak message', value=f'{streak_message}', inline=False)
        embed.timestamp = discord.utils.utcnow()

        await self.vote_hook.send(embed=embed)

    class ReminderButtons(discord.ui.View):
        """ The buttons which are on the "thanks for voting" message """

        def __init__(self, timeout=300, bot=None):
            super().__init__(timeout=timeout)

            self.message = None  # the original interaction message
            self.bot = bot  # the main bot instance

        def setOriginalMessage(self, message: discord.Message):
            self.message = message

        async def on_timeout(self) -> None:
            await self.message.edit(view=None)
            self.stop()

        @discord.ui.button(label='Yes! Remind me', style=discord.ButtonStyle.green)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            # add them to a list of user ids
            if "vote_reminder" not in self.bot.vote_data:
                self.bot.vote_data["vote_reminder"] = []

            if interaction.user.id not in self.bot.vote_data["vote_reminder"]:
                self.bot.vote_data["vote_reminder"].append(interaction.user.id)

            await interaction.response.send_message(
                f'Thanks! I will send you a message when you can vote again. :star_struck:',
                ephemeral=True)
            await self.on_timeout()

        @discord.ui.button(label='No :(', style=discord.ButtonStyle.grey)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message('OK. I will not send any vote reminders.', ephemeral=True)
            await self.on_timeout()


async def setup(bot):
    await bot.add_cog(VoteCog(bot))
