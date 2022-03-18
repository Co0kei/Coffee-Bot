import logging
import time

import discord
from discord import app_commands
from discord.ext import commands

import dev_server

log = logging.getLogger(__name__)


class VoteCommand(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(name='vote', description='Help more people discover Coffee Bot and earn coins!')
    async def globalVoteCommand(self, interaction: discord.Interaction):
        await self.handleVoteCommand(interaction)

    @app_commands.command(name='devvote', description='Dev - Help more people discover coffee bot and earn coins!')
    @app_commands.guilds(discord.Object(id=dev_server.DEV_SERVER_ID))
    async def devVoteCommand(self, interaction: discord.Interaction):
        await self.handleVoteCommand(interaction)

    async def handleVoteCommand(self, interaction: discord.Interaction):
        embed = discord.Embed()
        embed.title = 'Vote for me!'
        embed.url = 'https://top.gg/bot/950765718209720360/vote'
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.colour = discord.Colour.blurple()

        embed.add_field(name="__Global Votes __", value=
        f'Monthly Votes: **{self.bot.stat_data["monthly_votes"]}**\n'
        f'Total Votes: **{self.bot.stat_data["total_votes"]}**', inline=False)

        # get coins for member
        discordID = str(interaction.user.id)
        if discordID in self.bot.vote_data:
            vote_history: list = self.bot.vote_data[discordID]["vote_history"]
            total_votes = 0

            formatted = []
            vote_history.reverse()
            for vote in vote_history:
                message = "`+` " + str(vote["coins"]) + ":coin: (<t:" + str(vote["time"]) + ":R>)"
                if vote["is_weekend"]:
                    total_votes += 2
                    message += " **DOUBLE** coins & 2 votes!"
                else:
                    total_votes += 1
                formatted.append(message)
            formatted = "\n".join(formatted)

            total_coins = sum([element["coins"] for element in vote_history])
            vote_streak = self.bot.vote_data[discordID]["vote_streak"]
            last_vote = f'<t:{self.bot.vote_data[discordID]["last_vote"]}:R>.'

            difference = (int(time.time()) - self.bot.vote_data[discordID]["last_vote"])
            # print(difference)
            if difference > 43200:  # num of seconds in 12 hours
                # can vote again now.
                last_vote += " You can [vote](https://top.gg/bot/950765718209720360/vote) again now!"
            else:
                # must wait some time
                # get time of last vote and add on seconds in 12 hours to get the time they can vote again
                last_vote += f' You can [vote](https://top.gg/bot/950765718209720360/vote) again <t:{self.bot.vote_data[discordID]["last_vote"] + 43200}:R>.'
        else:
            total_votes = 0
            formatted = "`None`"

            total_coins = 0
            vote_streak = 0
            last_vote = "`None`"

        embed.add_field(name="__Your Vote Info__", value=
        f'Your Coins: **{total_coins}**:coin:\n'
        f'Vote Streak: **{vote_streak}**\n'
        f'Total Votes: **{total_votes}**\n'
        f'Last Vote: {last_vote}', inline=False)

        embed.add_field(name="__Your Vote History__", value=f'{formatted}', inline=False)

        embed.add_field(name="__How Votes Work__", value=
        f'**1.** Everyone can [vote](https://top.gg/bot/950765718209720360/vote) every 12 hours, but votes get doubled on the weekend.\n'
        f'**2.** Coffee Bot gives you between 20 to 25 coins for each vote, so you get double coins and votes on the weekend.\n'
        f'**3.** The vote count on the bot\'s page [here](https://top.gg/bot/950765718209720360) gets reset at the start of each month.\n'
        f'**4.** Nevertheless, Coffee Bot counts total votes and how many votes you contribute overall!', inline=False)
        embed.set_footer(
            text="Note: Have your private messages open to receive a message each time you vote, containing information and an optional reminder!")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Vote!", url="https://top.gg/bot/950765718209720360/vote"))
        # todo add button that shows vote history

        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)


async def setup(bot):
    await bot.add_cog(VoteCommand(bot))
