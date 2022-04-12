import logging

import bedwarspro
import discord
from bedwarspro import BedwarsProException
from discord.ext import commands

from constants import BW_PRO_API_KEY

log = logging.getLogger(__name__)


class BWPROCommand(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    async def cog_load(self):
        self.BW_PRO = bedwarspro.Client(BW_PRO_API_KEY)

    async def cog_unload(self):
        await self.BW_PRO.close()

    @commands.command()
    async def bwpro(self, ctx, player=None):
        if player is None:
            return await ctx.message.reply("Please enter a player name or UUID!")

        async with self.BW_PRO:
            try:
                player = await self.BW_PRO.player(player)

                embed = discord.Embed()
                embed.title = f'[{player.rank}] {player.name}'
                embed.colour = discord.Colour.blurple()
                embed.add_field(name="First Login", value=discord.utils.format_dt(player.first_login))
                await ctx.message.reply(embed=embed)

            except BedwarsProException as error:
                await ctx.send(f'Error: {error}.')


async def setup(bot):
    await bot.add_cog(BWPROCommand(bot))
