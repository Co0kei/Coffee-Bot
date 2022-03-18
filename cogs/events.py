import logging
import random
import re
import sys
import time
import traceback
from datetime import timedelta

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def getModLogChannel(self, guild: discord.Guild) -> discord.TextChannel:
        mod_log_channel = None
        if str(guild.id) in self.bot.guild_settings:
            if "mod_log_channel" in self.bot.guild_settings[str(guild.id)]:
                mod_log_channel = guild.get_channel(self.bot.guild_settings[str(guild.id)]["mod_log_channel"])
        return mod_log_channel

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if re.fullmatch(rf"<@!?{self.bot.user.id}>", message.content):
            return await message.channel.send(f"Hi!")

        if message.guild is None:
            return

        if message.author.guild_permissions.administrator:
            return

        content_lower = message.content.lower()

        # whitelisted_links = ["tenor.com"]
        # for link in whitelisted_links:
        #     content_lower = content_lower.replace(link, "")
        # print(f'removed allolwed links {content_lower}')
        # if re.search("(https?://(?:www\\.|(?!www))[^\\s.]+\\.[^\\s]{2,}|www\\.[^\\s]+\\.[^\\s]{2,})", content_lower):
        #     await message.delete()
        #     print("found a link")

        if self.bot.get_cog("SettingsCommand").isInviteFilterEnabled(message.guild):
            if re.search("(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?", content_lower) or re.search(
                    "https?://dsc.gg/", content_lower):
                await message.delete()
                try:
                    await message.author.timeout(timedelta(seconds=10))
                except discord.Forbidden as e:  # no permission
                    pass

                # log it
                if self.getModLogChannel(message.guild) is not None:
                    # create an embed
                    embed = discord.Embed()
                    embed.set_author(name="Discord Invite Posted", icon_url=message.author.display_avatar.url)
                    embed.colour = discord.Colour(0x2F3136)
                    embedDescription = f'{message.author.mention} ({message.author}) tried to post a Discord server invite.\n\n'
                    embedDescription += f'**Message Content:**\n`{message.clean_content[0:2000]}`'  # only display first 2000 chars
                    embedDescription += f'\n\n**Message\'s Info:**\n' \
                                        f'Message ID: `{message.id}`\n' \
                                        f'Channel: {message.channel.mention}\n' \
                                        f'Time: {discord.utils.format_dt(message.created_at, "F")} ({discord.utils.format_dt(message.created_at, "R")})\n' \
                                        f'Attachments: `{len(message.attachments)}`'
                    if len(message.attachments) != 0:
                        attachement1 = message.attachments[0]
                        if attachement1.content_type.startswith("image"):
                            embed.set_image(url=attachement1.url)
                            embedDescription += f"\n\n**Message Image:**"
                    embed.description = embedDescription

                    await self.getModLogChannel(message.guild).send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.author.bot:
            return

        if after.guild is None:
            return

        if after.author.guild_permissions.administrator:
            return

        content_lower = after.content.lower()

        if self.bot.get_cog("SettingsCommand").isInviteFilterEnabled(after.guild):
            if re.search("(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?", content_lower) or re.search(
                    "https?://dsc.gg/", content_lower):
                await after.delete()
                try:
                    await after.author.timeout(timedelta(seconds=10))
                except discord.Forbidden as e:  # no permission
                    pass

                # log it
                if self.getModLogChannel(after.guild) is not None:
                    # create an embed
                    embed = discord.Embed()
                    embed.set_author(name="Discord Invite Posted", icon_url=after.author.display_avatar.url)
                    embed.colour = discord.Colour(0x2F3136)
                    embedDescription = f'{after.author.mention} ({after.author}) tried to edit a Discord server invite into a message.\n\n'
                    embedDescription += f'**Message Before:**\n`{before.clean_content[0:1000]}`\n\n'  # only display first 2000 chars
                    embedDescription += f'**Message After:**\n`{after.clean_content[0:1000]}`'  # only display first 2000 chars

                    embedDescription += f'\n\n**Message\'s Info:**\n' \
                                        f'Message ID: `{after.id}`\n' \
                                        f'Channel: {after.channel.mention}\n' \
                                        f'Time: {discord.utils.format_dt(after.created_at, "F")} ({discord.utils.format_dt(after.created_at, "R")})\n' \
                                        f'Attachments: `{len(after.attachments)}`'
                    if len(after.attachments) != 0:
                        attachement1 = after.attachments[0]
                        if attachement1.content_type.startswith("image"):
                            embed.set_image(url=attachement1.url)
                            embedDescription += f"\n\n**Message Image:**"
                    embed.description = embedDescription

                    await self.getModLogChannel(after.guild).send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        log.info(f'I have been invited to {guild.name} ({guild.id}) which has {len(guild.members)} members.')

        embed = discord.Embed(title='Joined Server', colour=discord.Colour.green())
        embed.add_field(name='Guild Info', value=f'{guild.name} (ID: {guild.id})', inline=False)
        embed.add_field(name='Guild Members', value=f'{len(guild.members)}', inline=False)
        embed.timestamp = discord.utils.utcnow()

        await self.bot.hook.send(embed=embed)

        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=f'{len(self.bot.guilds)} guilds'))

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        log.info(f'I have been removed from {guild.name} ({guild.id}) which has {len(guild.members)} members.')

        embed = discord.Embed(title='Left Server', colour=discord.Colour.dark_red())
        embed.add_field(name='Guild Info', value=f'{guild.name} (ID: {guild.id})', inline=False)
        embed.add_field(name='Guild Members', value=f'{len(guild.members)}', inline=False)
        embed.timestamp = discord.utils.utcnow()

        await self.bot.hook.send(embed=embed)

        await self.bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=f'{len(self.bot.guilds)} guilds'))

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:  # slash commands or context menus

            command_type = interaction.data['type']
            command_name = interaction.data['name']
            user = f'{interaction.user} (ID: {interaction.user.id})'

            if interaction.guild is None:
                guild = None
            else:
                guild = f'{interaction.guild.name} (ID: {interaction.guild.id})'

            self.bot.stat_data["commands_used"] += 1

            if command_type == 1:  # slash command
                application_command_type = "Slash"

            elif command_type == 2:  # user context menu
                application_command_type = "User Context Menu"

            elif command_type == 3:  # message context menu
                application_command_type = "Message Context Menu"

            else:  # idk
                application_command_type = "Unknown type"

            log.info(
                f'{application_command_type} command \'{command_name}\' ran by {user}. Guild: {guild}. Commands used: {self.bot.stat_data["commands_used"]}!')

            embed = discord.Embed(colour=discord.Colour.blurple())
            embed.set_author(name=f'Command ran by {user}', icon_url=interaction.user.display_avatar.url)
            embed.add_field(name='Type', value=f'{application_command_type}', inline=False)
            embed.add_field(name='Command Name', value=f'{command_name}', inline=False)
            embed.add_field(name='Guild', value=f'{guild}', inline=False)
            embed.timestamp = discord.utils.utcnow()
            embed.set_footer(text=f'Total commands ran: {self.bot.stat_data["commands_used"]}')

            if interaction.user.id != self.bot.owner_id:
                await self.bot.hook.send(embed=embed)

    @commands.Cog.listener()
    async def on_autopost_success(self):
        log.info(f"Posted server count ({self.bot.topggpy.guild_count}), shard count ({self.bot.shard_count})")

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        """ An event that is called whenever someone votes for the bot on Top.gg. """
        if data["type"] == "test":
            return self.bot.dispatch("dbl_test", data)

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
        embed.add_field(name='Total Coins', value=f'{total_coins}:coin:', inline=False)
        embed.add_field(name='Streak message', value=f'{streak_message}', inline=False)
        embed.timestamp = discord.utils.utcnow()

        await self.bot.hook.send(embed=embed)

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
        async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
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
        async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
            await interaction.response.send_message('OK. I will not send any vote reminders.', ephemeral=True)
            await self.on_timeout()

    @commands.Cog.listener()
    async def on_dbl_test(self, data):
        """ An event that is called whenever someone tests the webhook system for your bot on Top.gg. """
        log.info(f'Received a test vote from {data["user"]}')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.NotOwner):
            await ctx.author.send('Sorry. This command can\'t be used by you.')

        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                print(f'Error in {ctx.command.qualified_name}:', file=sys.stderr)
                traceback.print_tb(original.__traceback__)
                print(f'{original.__class__.__name__}: {original}', file=sys.stderr)


async def setup(bot):
    await bot.add_cog(EventCog(bot))
