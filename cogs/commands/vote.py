import itertools
import logging
import math
import time

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)


class VoteCommand(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(name='vote', description='Help more servers to find me, and earn some coins!')
    async def globalVoteCommand(self, interaction: discord.Interaction):
        await self.handleVoteCommand(interaction)

    async def handleVoteCommand(self, interaction: discord.Interaction):
        embed = discord.Embed()
        embed.title = 'Vote for me!'
        embed.url = 'https://top.gg/bot/950765718209720360'
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.colour = discord.Colour.dark_gold()

        embed.add_field(name="__Global Votes __", value=
        f'Monthly Votes: **{self.bot.stat_data["monthly_votes"]}**\n'
        f'Total Votes: **{self.bot.stat_data["total_votes"]}**', inline=False)

        # get coins for member
        discordID = str(interaction.user.id)
        if discordID in self.bot.vote_data:
            vote_history: list = self.bot.vote_data[discordID]["vote_history"]
            total_votes = 0

            for vote in vote_history:
                if vote["is_weekend"]:
                    total_votes += 2
                else:
                    total_votes += 1

            total_coins = sum([element["coins"] for element in vote_history])
            last_vote = f'<t:{self.bot.vote_data[discordID]["last_vote"]}:R>.'

            difference = (int(time.time()) - self.bot.vote_data[discordID]["last_vote"])
            if difference > 43200:  # num of seconds in 12 hours
                # can vote again now.
                last_vote += " You can [vote](https://top.gg/bot/950765718209720360/vote) again now!"
            else:
                # must wait some time
                # get time of last vote and add on seconds in 12 hours to get the time they can vote again
                last_vote += f' You can [vote](https://top.gg/bot/950765718209720360/vote) again <t:{self.bot.vote_data[discordID]["last_vote"] + 43200}:R>.'

            if difference > 86400:  # num of seconds in a day
                vote_streak = 0
            else:
                vote_streak = self.bot.vote_data[discordID]["vote_streak"]
        else:
            total_votes = 0

            total_coins = 0
            vote_streak = 0
            last_vote = "`None`"

        embed.add_field(name="__Your Vote Info__", value=
        f'Your Coins: **{total_coins:,}**:coin:\n'
        f'Vote Streak: **{vote_streak:,}**\n'
        f'Total Votes: **{total_votes:,}**\n'
        f'Last Vote: {last_vote}', inline=False)

        # embed.add_field(name="__Your Vote History__", value=f'{formatted}', inline=False)

        embed.add_field(name="__How Votes Work__", value=
        f'**1.** Everyone can [vote](https://top.gg/bot/950765718209720360/vote) every 12 hours, but votes get doubled on the weekend.\n'
        f'**2.** Coffee Bot gives you between 20 to 25 coins for each vote, so you get double coins and votes on the weekend.\n'
        f'**3.** The vote count on the bot\'s page [here](https://top.gg/bot/950765718209720360) gets reset at the start of each month.\n'
        f'**4.** Nevertheless, Coffee Bot counts total votes and how many votes you contribute overall!', inline=False)
        embed.set_footer(text="Note: Have your private messages open to receive a message each time you vote, containing information and an optional reminder!")

        view = self.VoteHistoryButton(commandsCog=self, userID=interaction.user.id)

        if total_votes == 0:  # If they havent voted disabled buttons.
            buttons = [item for item in view.children if item.type == discord.ComponentType.button]
            for button in buttons:
                if not button.url:
                    button.disabled = True

        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

        view.message = await interaction.original_message()

    class VoteHistoryButton(discord.ui.View):

        def __init__(self, timeout=120, commandsCog=None, userID=None):
            super().__init__(timeout=timeout)
            self.message = None  # the original interaction message
            self.commandsCog = commandsCog
            self.userID = userID  # the user which is allowed to click the buttons
            self.add_item(discord.ui.Button(label="Vote!", url="https://top.gg/bot/950765718209720360/vote"))

        async def on_timeout(self) -> None:
            await self.message.edit(view=None)

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id == self.userID:
                return True
            else:
                await interaction.response.send_message("Sorry, you cannot use this.", ephemeral=True)
                return False

        @discord.ui.button(label='Your Vote History', emoji="\U0001fa99", style=discord.ButtonStyle.green)
        async def voteHistory(self, interaction: discord.Interaction, button: discord.ui.Button):
            totalVotes, timesVoted = self.commandsCog.get_total_votes(interaction.user.id)

            if totalVotes == 0:
                embed = discord.Embed(title="Your Vote History", description=f'You have never voted :(', colour=discord.Colour.dark_gold())
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            else:
                totalPages = int(math.ceil(timesVoted / 10.0))

                view = self.commandsCog.PaginatedVoteHistory(commandsCog=self.commandsCog, totalVotes=totalVotes, timesVoted=timesVoted, totalPages=totalPages)

                embed = discord.Embed(title="Your Vote History", description=f'You have voted {timesVoted} times and now,\ndue to double vote weekends,\nhave a total of {totalVotes} votes!\n\n'
                                                                             f'{self.commandsCog.get_vote_history(interaction.user.id)[:3900]}')
                embed.colour = discord.Colour.dark_gold()
                embed.set_footer(text=f"『 Page 1/{totalPages}』")

                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

                msg = await interaction.original_message()
                view.setOriginalMessage(msg)  # pass the original message into the class

        @discord.ui.button(label='Top Voters', emoji="\U0001f31f", style=discord.ButtonStyle.green)
        async def topVoters(self, interaction: discord.Interaction, button: discord.ui.Button):

            discord_list = []
            votes_list = []
            coins_list = []

            for item in self.commandsCog.bot.vote_data:
                if item == "vote_reminder":
                    continue

                vote_history: list = self.commandsCog.bot.vote_data[item]["vote_history"]

                total_votes = 0

                for vote in vote_history:
                    if vote["is_weekend"]:
                        total_votes += 2
                    else:
                        total_votes += 1

                total_coins = sum([element["coins"] for element in vote_history])

                user = self.commandsCog.bot.get_user(int(item))

                if user is None:
                    user = await self.commandsCog.bot.fetch_user(int(item))

                if user is not None:
                    discord_list.append(user)
                    votes_list.append(total_votes)
                    coins_list.append(total_coins)

            data_sort = [list(a) for a in zip(discord_list, votes_list, coins_list)]
            list4 = sorted(data_sort, key=lambda x: x[2], reverse=True)
            discordID_list, votes_list, coins_list = map(list, zip(*list4))

            if len(discordID_list) >= 10:
                iteratingIndex = 10
            else:
                iteratingIndex = len(discordID_list)

            embed = discord.Embed(title="Top Voters", colour=discord.Colour.dark_gold())
            msg = ""
            for i in range(iteratingIndex):
                msg += f"`#{i + 1}` **{discordID_list[i]}** Votes: **{votes_list[i]:,}** | Coins: **{coins_list[i]:,}**:coin:\n"

            embed.description = msg
            await interaction.response.send_message(embed=embed, ephemeral=True)

    class PaginatedVoteHistory(discord.ui.View):

        def __init__(self, timeout=120, commandsCog=None, totalVotes=None, timesVoted=None, totalPages=None):
            super().__init__(timeout=timeout)
            self.message = None  # the original interaction message
            self.commandsCog = commandsCog
            self.page = 1
            self.totalVotes = totalVotes
            self.timesVoted = timesVoted
            self.totalPages = totalPages

        def setOriginalMessage(self, message: discord.Message):
            self.message = message

        async def on_timeout(self) -> None:
            await self.message.edit(view=None)

        @discord.ui.button(emoji="<:left:882953998603288586>", style=discord.ButtonStyle.grey)
        async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page == 1:
                self.page = self.totalPages
            else:
                self.page -= 1

            if self.totalVotes >= ((self.page - 1) * 10 + 10):
                iteratingIndex = 10
            else:
                iteratingIndex = self.totalVotes - ((self.page - 1) * 10)

            embed = discord.Embed(title="Your Vote History", description=f'You have voted {self.timesVoted} times and now,\ndue to double vote weekends,\nhave a total of {self.totalVotes} votes!\n\n'
                                                                         f'{self.commandsCog.get_vote_history(interaction.user.id, start=(self.page - 1) * 10, end=(self.page - 1) * 10 + iteratingIndex)[:3900]}')
            embed.colour = discord.Colour.dark_gold()
            embed.set_footer(text=f"『 Page {self.page}/{self.totalPages}』")

            await interaction.response.edit_message(embed=embed)

        @discord.ui.button(emoji="<:right:882953977388486676>", style=discord.ButtonStyle.grey)
        async def forward(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page == self.totalPages:
                self.page = 1
            else:
                self.page += 1

            if self.totalVotes >= ((self.page - 1) * 10 + 10):
                iteratingIndex = 10
            else:
                iteratingIndex = self.totalVotes - ((self.page - 1) * 10)

            embed = discord.Embed(title="Your Vote History", description=f'You have voted {self.timesVoted} times and now,\ndue to double vote weekends,\nhave a total of {self.totalVotes} votes!\n\n'
                                                                         f'{self.commandsCog.get_vote_history(interaction.user.id, start=(self.page - 1) * 10, end=(self.page - 1) * 10 + iteratingIndex)[:3900]}')
            embed.colour = discord.Colour.dark_gold()
            embed.set_footer(text=f"『 Page {self.page}/{self.totalPages}』")

            await interaction.response.edit_message(embed=embed)

    def get_vote_history(self, userID, start=0, end=10):
        discordID = str(userID)
        if discordID in self.bot.vote_data:
            vote_history: list = self.bot.vote_data[discordID]["vote_history"]
            total_votes = 0

            voteMessage_list = []
            timeStamp_list = []
            for vote in vote_history:
                message = "`+` " + str(vote["coins"]) + ":coin: (<t:" + str(vote["time"]) + ":R>)"
                if vote["is_weekend"]:
                    total_votes += 2
                    message += " **DOUBLE** coins & votes!"
                else:
                    total_votes += 1
                voteMessage_list.append(message)
                timeStamp_list.append(vote["time"])

            data_sort = [list(a) for a in zip(voteMessage_list, timeStamp_list)]
            list4 = sorted(data_sort, key=lambda x: x[1], reverse=True)
            voteMessage_list, timeStamp_list = map(list, zip(*list4))

            history = list(itertools.islice(voteMessage_list, start, end))
            return "\n".join(history)
        else:
            return "`None`"

    def get_total_votes(self, userID):
        discordID = str(userID)
        if discordID in self.bot.vote_data:
            vote_history: list = self.bot.vote_data[discordID]["vote_history"]

            total_votes = 0

            for vote in vote_history:
                if vote["is_weekend"]:
                    total_votes += 2
                else:
                    total_votes += 1

            return total_votes, len(vote_history)
        else:
            return 0, 0


async def setup(bot):
    await bot.add_cog(VoteCommand(bot))
