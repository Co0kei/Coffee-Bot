import logging
import sys

import discord
from discord.ext import commands

from constants import *

log = logging.getLogger(__name__)


class CommandCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self) -> None:
        self.command_hook = discord.Webhook.from_url(COMMAND_HOOK_URL, session=self.bot.session)

    async def cog_unload(self) -> None:
        pass

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:  # slash commands or context menus

            command_type = interaction.data['type']
            command_name = interaction.data['name']
            user = f'{interaction.user} (ID: {interaction.user.id})'

            if interaction.guild is None:
                guild = None
                guild_id = None
                destination = 'Private Message'
            else:
                guild = f'{interaction.guild.name} (ID: {interaction.guild.id}) ({len(interaction.guild.members):,} members)'
                guild_id = interaction.guild.id
                destination = f'#{interaction.channel}'

            self.bot.stat_data["commands_used"] += 1

            embed = discord.Embed(colour=discord.Colour.blurple())

            if command_type == 1:  # slash command
                # application_command_type = "Slash"
                command_name = f"/{command_name}"
                embed.add_field(name='Slash Command', value=f'{command_name}', inline=False)
                if "options" in interaction.data:
                    params = interaction.data["options"]
                    msg = ""
                    for param in params:
                        paramType = str(discord.AppCommandOptionType(value=param["type"])).split(".")[1]
                        msg += f"Name: {param['name']} | Type: {paramType} | Value {param['value']}\n"
                    embed.add_field(name='Parameters', value=msg)

            elif command_type == 2:  # user context menu
                # application_command_type = "User Context Menu"
                embed.add_field(name='User Context Menu Command', value=f'{command_name}', inline=False)

            elif command_type == 3:  # message context menu
                # application_command_type = "Message Context Menu"
                embed.add_field(name='Message Context Menu Command', value=f'{command_name}', inline=False)

            else:  # idk
                # application_command_type = "Unknown type"
                embed.add_field(name='Unknown Type Command', value=f'{command_name}', inline=False)

            log.info(f'{interaction.user} in {destination}: {command_name}')

            embed.set_author(name=f'Command ran by {user}', icon_url=interaction.user.display_avatar.url)
            embed.add_field(name='Guild', value=f'{guild}', inline=False)
            embed.add_field(name='Location', value=f'{destination}', inline=False)
            embed.timestamp = discord.utils.utcnow()
            embed.set_footer(text=f'Total commands ran: {self.bot.stat_data["commands_used"]:,}')

            # Send to stats thing
            await self.bot.get_cog('StatsCog').register_command(interaction.data['name'], guild_id, interaction.channel.id, interaction.user.id, interaction.created_at.isoformat(),
                                                                None, command_type)

            if (interaction.guild is not None and interaction.guild.id == DEV_SERVER_ID) or interaction.user.id == self.bot.owner_id:
                return

            if sys.platform != DEV_PLATFORM:
                await self.command_hook.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        message = ctx.message
        user = f'{ctx.author} (ID: {ctx.author.id})'

        if ctx.guild is None:
            guild = None
            guild_id = None
            destination = 'Private Message'
        else:
            guild = f'{ctx.guild.name} (ID: {ctx.guild.id}) ({len(ctx.guild.members):,} members)'
            guild_id = ctx.guild.id
            destination = f'#{message.channel}'

        self.bot.stat_data["commands_used"] += 1

        log.info(f'{message.author} in {destination}: {message.content}')

        embed = discord.Embed(colour=discord.Colour.blurple())
        embed.set_author(name=f'Command ran by {user}', icon_url=ctx.author.display_avatar.url)
        embed.add_field(name='Command', value=f'{message.content}', inline=False)
        embed.add_field(name='Guild', value=f'{guild}', inline=False)
        embed.add_field(name='Location', value=f'{destination}', inline=False)

        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text=f'Total commands ran: {self.bot.stat_data["commands_used"]:,}')

        # DONT SAVE MESSAGE BASED COMMANDS <---------------

        if (ctx.guild is not None and ctx.guild.id == DEV_SERVER_ID) or ctx.author.id == self.bot.owner_id:
            return

        if sys.platform != DEV_PLATFORM:
            await self.command_hook.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CommandCog(bot))
