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
        f'Monthly Votes: **{self.bot.stat_data["monthly_votes"]:,}**\n'
        f'Votes Last Month: **{self.bot.stat_data["last_months_votes"]:,}**\n'
        f'Total Votes: **{self.bot.stat_data["total_votes"]:,}**', inline=False)

        query = "SELECT total_coins, vote_streak, last_vote FROM user_votes WHERE user_id=$1;"
        user_vote_data = await self.bot.pool.fetchrow(query, interaction.user.id)

        total_votes = 0
        if user_vote_data:
            voted_before = True
            total_coins = user_vote_data[0]
            vote_streak = user_vote_data[1]
            last_vote_timestamp = int(user_vote_data[2].timestamp())

            difference = (int(time.time()) - last_vote_timestamp)

            last_vote = f'<t:{last_vote_timestamp}:R>.'
            if difference > 43200:  # num of seconds in 12 hours
                # can vote again now.
                last_vote += " You can [vote](https://top.gg/bot/950765718209720360/vote) again now!"
            else:
                # get time of last vote and add on seconds in 12 hours to get the time they can vote again
                last_vote += f' You can [vote](https://top.gg/bot/950765718209720360/vote) again <t:{last_vote_timestamp + 43200}:R>.'

            if difference > 86400:  # num of seconds in a day
                vote_streak = 0

            query = "SELECT coins, time, is_weekend FROM votes WHERE user_id=$1 ORDER BY time DESC;"
            vote_history = await self.bot.pool.fetch(query, interaction.user.id)

            individual_votes = len(vote_history)
            for vote in vote_history:
                if vote["is_weekend"]:
                    total_votes += 2
                else:
                    total_votes += 1

        else:
            voted_before = False
            total_coins = 0
            vote_streak = 0
            last_vote = "`Never`"
            individual_votes = 0
            vote_history = []

        embed.add_field(name="__Your Vote Info__", value=
        f'Your Coins: **{total_coins:,}**:coin:\n'
        f'Vote Streak: **{vote_streak:,}**\n'
        f'Total Votes: **{total_votes:,}**\n'
        f'Last Vote: {last_vote}', inline=False)

        embed.add_field(name="__How Votes Work__", value=
        f'**1.** Everyone can [vote](https://top.gg/bot/950765718209720360/vote) every 12 hours, but votes get doubled on the weekend.\n'
        f'**2.** Coffee Bot gives you between 20 to 25 coins for each vote, so you get double coins and votes on the weekend.\n'
        f'**3.** The vote count on the bot\'s page [here](https://top.gg/bot/950765718209720360) gets reset at the start of each month.\n'
        f'**4.** Nevertheless, Coffee Bot counts total votes and how many votes you contribute overall!', inline=False)
        embed.set_footer(text="Note: Have your private messages open to receive a message each time you vote, containing information and an optional reminder!")

        view = self.VoteHistoryButton(cog=self, user_id=interaction.user.id, total_votes=total_votes, individual_votes=individual_votes, vote_history=vote_history)

        if not voted_before:  # If they havent voted disable buttons.
            buttons = [item for item in view.children if item.type == discord.ComponentType.button]
            for button in buttons:
                if not button.url:
                    button.disabled = True

        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        view.message = await interaction.original_message()

    class VoteHistoryButton(discord.ui.View):
        def __init__(self, timeout=120, cog=None, user_id=None, total_votes=None, individual_votes=None, vote_history=None):
            super().__init__(timeout=timeout)
            self.message = None
            self.cog = cog
            self.user_id = user_id
            self.total_votes = total_votes
            self.individual_votes = individual_votes
            self.total_pages = int(math.ceil(self.individual_votes / 10.0))

            self.vote_history = []
            for vote in vote_history:
                message = f"`+` {vote['coins']}:coin: (<t:{int(vote['time'].timestamp())}:R>)"
                if vote["is_weekend"]:
                    message += " **DOUBLE** coins & votes!"
                self.vote_history.append(message)

            if str(user_id) not in self.cog.bot.stat_data["vote_reminders"]:
                self.remove_item(self.reminders)

            self.add_item(discord.ui.Button(label="Vote!", url="https://top.gg/bot/950765718209720360/vote"))

        def get_vote_history(self, start=0, end=10):
            history = list(itertools.islice(self.vote_history, start, end))
            return "\n".join(history)

        def get_embed(self, page: int):
            if self.total_votes >= ((page - 1) * 10 + 10):
                iteratingIndex = 10
            else:
                iteratingIndex = self.total_votes - ((page - 1) * 10)
            embed = discord.Embed(title="Your Vote History", colour=discord.Colour.dark_gold(),
                                  description=f'You have voted {self.individual_votes} times and now,\ndue to double vote weekends,\nhave a total of {self.total_votes} votes!\n\n'
                                              f'{self.get_vote_history(start=(page - 1) * 10, end=(page - 1) * 10 + iteratingIndex)[:3900]}')
            embed.set_footer(text=f"『 Page {page}/{self.total_pages}』")
            return embed

        async def on_timeout(self) -> None:
            buttons = [item for item in self.children if item.type == discord.ComponentType.button]
            for button in buttons:
                if not button.url:
                    self.remove_item(button)
            await self.message.edit(view=self)

        async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id == self.user_id:
                return True
            else:
                await interaction.response.send_message("Sorry, you cannot use this.", ephemeral=True)
                return False

        @discord.ui.button(label='Your Vote History', emoji="\U0001fa99", style=discord.ButtonStyle.green)
        async def voteHistory(self, interaction: discord.Interaction, button: discord.ui.Button):
            view = self.cog.PaginatedVoteHistory(main_view=self, total_pages=self.total_pages)
            await interaction.response.send_message(embed=self.get_embed(1), view=view, ephemeral=True)
            view.message = await interaction.original_message()

        @discord.ui.button(label='Disable Vote Reminders', style=discord.ButtonStyle.gray)
        async def reminders(self, interaction: discord.Interaction, button: discord.ui.Button):
            del self.cog.bot.stat_data["vote_reminders"][str(interaction.user.id)]
            self.remove_item(self.reminders)
            await self.message.edit(view=self)
            await interaction.response.send_message("You will no longer receive vote reminders.\n"
                                                    "You can re-enable reminders at any time by opening your DMs, voting for me, then clicking on the message I send you.", ephemeral=True)

    class PaginatedVoteHistory(discord.ui.View):
        def __init__(self, timeout=120, main_view=None, total_pages=None):
            super().__init__(timeout=timeout)
            self.message = None
            self.main_view = main_view
            self.page = 1
            self.total_pages = total_pages

        async def on_timeout(self) -> None:
            await self.message.edit(view=None)

        async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
            log.exception(error)
            if interaction.response.is_done():
                await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
            else:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        @discord.ui.button(emoji="<:left:882953998603288586>", style=discord.ButtonStyle.grey)
        async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page == 1:
                self.page = self.total_pages
            else:
                self.page -= 1
            await interaction.response.edit_message(embed=self.main_view.get_embed(self.page))

        @discord.ui.button(emoji="<:right:882953977388486676>", style=discord.ButtonStyle.grey)
        async def forward(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page == self.total_pages:
                self.page = 1
            else:
                self.page += 1
            await interaction.response.edit_message(embed=self.main_view.get_embed(self.page))


# @discord.ui.button(label='Top Voters', emoji="\U0001f31f", style=discord.ButtonStyle.green)
# async def topVoters(self, interaction: discord.Interaction, button: discord.ui.Button):
#
#     discord_list = []
#     votes_list = []
#     coins_list = []
#
#     for item in self.commandsCog.bot.vote_data:
#         if item == "vote_reminder":
#             continue
#
#         vote_history: list = self.commandsCog.bot.vote_data[item]["vote_history"]
#
#         total_votes = 0
#
#         for vote in vote_history:
#             if vote["is_weekend"]:
#                 total_votes += 2
#             else:
#                 total_votes += 1
#
#         total_coins = sum([element["coins"] for element in vote_history])
#
#         user = self.commandsCog.bot.get_user(int(item))
#
#         if user is None:
#             user = await self.commandsCog.bot.fetch_user(int(item))
#
#         if user is not None:
#             discord_list.append(user)
#             votes_list.append(total_votes)
#             coins_list.append(total_coins)
#
#     data_sort = [list(a) for a in zip(discord_list, votes_list, coins_list)]
#     list4 = sorted(data_sort, key=lambda x: x[2], reverse=True)
#     discordID_list, votes_list, coins_list = map(list, zip(*list4))
#
#     if len(discordID_list) >= 10:
#         iteratingIndex = 10
#     else:
#         iteratingIndex = len(discordID_list)
#
#     embed = discord.Embed(title="Top Voters", colour=discord.Colour.dark_gold())
#     msg = ""
#     for i in range(iteratingIndex):
#         msg += f"`#{i + 1}` **{discordID_list[i]}** Votes: **{votes_list[i]:,}** | Coins: **{coins_list[i]:,}**:coin:\n"
#
#     embed.description = msg
#     await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(VoteCommand(bot))
