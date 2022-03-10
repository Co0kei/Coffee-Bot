import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("loaded")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        log.info(f'I have been invited to {guild.name} ({guild.id}) which has {len(guild.members)} members.')

        embed = discord.Embed(title='Joined Server', colour=discord.Colour.green())
        embed.add_field(name='Guild Info', value=f'{guild.name} (ID: {guild.id})', inline=False)
        embed.add_field(name='Guild Members', value=f'{len(guild.members)}', inline=False)
        embed.timestamp = discord.utils.utcnow()

        await self.bot.hook.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        log.info(f'I have been removed from {guild.name} ({guild.id}) which has {len(guild.members)} members.')

        embed = discord.Embed(title='Left Server', colour=discord.Colour.dark_red())
        embed.add_field(name='Guild Info', value=f'{guild.name} (ID: {guild.id})', inline=False)
        embed.add_field(name='Guild Members', value=f'{len(guild.members)}', inline=False)
        embed.timestamp = discord.utils.utcnow()

        await self.bot.hook.send(embed=embed)


def setup(bot):
    bot.add_cog(EventCog(bot))
