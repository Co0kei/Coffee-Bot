import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:  # slash commands or context menus

            type = interaction.data['type']
            name = interaction.data['name']

            self.bot.commands_used += 1

            # print(interaction.data)

            if type == 1:  # slash command
                log.info(
                    f'Slash command \'{name}\' ran by {interaction.user}. Commands used: {self.bot.commands_used}!')

            elif type == 2:  # context menu
                log.info(
                    f'User context menu command \'{name}\' ran by {interaction.user}. Commands used: {self.bot.commands_used}!')

            elif type == 3:  # message context menu
                log.info(
                    f'Message context menu command \'{name}\' ran by {interaction.user}. Commands used: {self.bot.commands_used}!')

            else:  # idk
                log.info(
                    f'Unknown type command \'{name}\' ran by {interaction.user}. Commands used: {self.bot.commands_used}!')


async def setup(bot):
    await bot.add_cog(EventCog(bot))
