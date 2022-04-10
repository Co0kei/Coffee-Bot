import logging

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)


class HelpCommand(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(name='help', description='Information on commands & bot setup.')
    async def globalHelpCommand(self, interaction: discord.Interaction):
        await self.handleHelpCommand(interaction)

    async def handleHelpCommand(self, interaction: discord.Interaction):
        embed = discord.Embed()
        embed.title = 'My Top.gg Page'
        embed.url = 'https://top.gg/bot/950765718209720360'
        embed.colour = discord.Colour.blurple()

        embed.add_field(name="__Commands__", value=
        f'**/help** - Displays help menu.\n'
        f'**Report Message** - Right click a message, scroll to \'Apps\', then click me to report a user.\n'
        f'**Report User** - Right click a user, scroll to \'Apps\', then click me to report a message.\n'
        f'**/report** - Used to report a user, as mobile devices do not support context menus.\n'
        f'**/settings** - Used to setup the bot in your server.\n'
        f'**/about** - Some stats about the bot.\n'
        f'**/vote** - Shows your voting history.', inline=False)

        embed.add_field(name="__Setup__", value=
        f'1. First invite me to your server, using the button on my profile.\n'
        f'2. Use the /settings command and enter a channel name for reports to be sent to.\n'
        f'3. Now you can right click on a user or message then scroll to \'Apps\' and click the report button!\n'
        f'\n'
        f'**NOTE:** Members must have the \'Use Application Commands\' permission. Also Discord is sometimes weird so if no \'Apps\' section is showing after you right click a message or user, then do CTRL + R to reload your Discord',
                        inline=False)
        # self.bot.help_command.
        # self.bot.help_command.send_command_help()

        # cmd = self.bot.get_command("help")
        # await cmd(interaction)
        # a = await discord.ext.commands.Context.send_help(self)
        # print(a)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    #
    # class MyMenuPages(ui.View, menus.MenuPages):
    #     def __init__(self, source, *, delete_message_after=False):
    #         super().__init__(timeout=60)
    #         self._source = source
    #         self.current_page = 0
    #         self.ctx = None
    #         self.message = None
    #         self.delete_message_after = delete_message_after
    #
    #     async def start(self, ctx, *, channel=None, wait=False):
    #         # We wont be using wait/channel, you can implement them yourself. This is to match the MenuPages signature.
    #         await self._source._prepare_once()
    #         self.ctx = ctx
    #         self.message = await self.send_initial_message(ctx, ctx.channel)
    #
    #     async def _get_kwargs_from_page(self, page):
    #         """This method calls ListPageSource.format_page class"""
    #         value = await super()._get_kwargs_from_page(page)
    #         if 'view' not in value:
    #             value.update({'view': self})
    #         return value
    #
    #     async def interaction_check(self, interaction):
    #         """Only allow the author that invoke the command to be able to use the interaction"""
    #         return interaction.user == self.ctx.author
    #
    #     @ui.button(emoji='<:before_fast_check:754948796139569224>', style=discord.ButtonStyle.blurple)
    #     async def first_page(self, button, interaction):
    #         await self.show_page(0)
    #
    #     @ui.button(emoji='<:before_check:754948796487565332>', style=discord.ButtonStyle.blurple)
    #     async def before_page(self, button, interaction):
    #         await self.show_checked_page(self.current_page - 1)
    #
    #     @ui.button(emoji='<:stop_check:754948796365930517>', style=discord.ButtonStyle.blurple)
    #     async def stop_page(self, button, interaction):
    #         self.stop()
    #         if self.delete_message_after:
    #             await self.message.delete(delay=0)
    #
    #     @ui.button(emoji='<:next_check:754948796361736213>', style=discord.ButtonStyle.blurple)
    #     async def next_page(self, button, interaction):
    #         await self.show_checked_page(self.current_page + 1)
    #
    #     @ui.button(emoji='<:next_fast_check:754948796391227442>', style=discord.ButtonStyle.blurple)
    #     async def last_page(self, button, interaction):
    #         await self.show_page(self._source.get_max_pages() - 1)
    #
    # class HelpPageSource(menus.ListPageSource):
    #     def __init__(self, data, helpcommand):
    #         super().__init__(data, per_page=6)
    #         self.helpcommand = helpcommand
    #
    #     def format_command_help(self, no, command):
    #         signature = self.helpcommand.get_command_signature(command)
    #         docs = self.helpcommand.get_command_brief(command)
    #         return f"{no}. {signature}\n{docs}"
    #
    #     async def format_page(self, menu, entries):
    #         page = menu.current_page
    #         max_page = self.get_max_pages()
    #         starting_number = page * self.per_page + 1
    #         iterator = starmap(self.format_command_help, enumerate(entries, start=starting_number))
    #         page_content = "\n".join(iterator)
    #         embed = discord.Embed(
    #             title=f"Help Command[{page + 1}/{max_page}]",
    #             description=page_content,
    #             color=0xffcccb
    #         )
    #         author = menu.ctx.author
    #         embed.set_footer(text=f"Requested by {author}", icon_url=author.avatar)  # author.avatar in 2.0
    #         return embed
    #
    # class MyHelp(commands.MinimalHelpCommand):
    #     def get_command_brief(self, command):
    #         return command.short_doc or "Command is not documented."
    #
    #     async def send_bot_help(self, mapping):
    #         all_commands = list(chain.from_iterable(mapping.values()))
    #         formatter = HelpCommand.HelpPageSource(all_commands, self)
    #         menu = HelpCommand.MyMenuPages(formatter, delete_message_after=True)
    #         await menu.start(self.context)

    # # testing
    #
    # class MyMenuPages(ui.View, menus.MenuPages):
    #     def __init__(self, source):
    #         super().__init__(timeout=60)
    #         self._source = source
    #         self.current_page = 0
    #         self.ctx = None
    #         self.message = None
    #
    #     async def start(self, ctx, *, channel=None, wait=False):
    #         # We wont be using wait/channel, you can implement them yourself. This is to match the MenuPages signature.
    #         await self._source._prepare_once()
    #         self.ctx = ctx
    #         self.message = await self.send_initial_message(ctx, ctx.channel)
    #
    #     async def _get_kwargs_from_page(self, page):
    #         """This method calls ListPageSource.format_page class"""
    #         value = await super()._get_kwargs_from_page(page)
    #         if 'view' not in value:
    #             value.update({'view': self})
    #         return value
    #
    #     async def interaction_check(self, interaction):
    #         """Only allow the author that invoke the command to be able to use the interaction"""
    #         return interaction.user == self.ctx.author
    #
    #     # This is extremely similar to Custom MenuPages(I will not explain these)
    #     @ui.button(emoji='<:before_fast_check:754948796139569224>', style=discord.ButtonStyle.blurple)
    #     async def first_page(self, button, interaction):
    #         await self.show_page(0)
    #
    #     @ui.button(emoji='<:before_check:754948796487565332>', style=discord.ButtonStyle.blurple)
    #     async def before_page(self, button, interaction):
    #         await self.show_checked_page(self.current_page - 1)
    #
    #     @ui.button(emoji='<:stop_check:754948796365930517>', style=discord.ButtonStyle.blurple)
    #     async def stop_page(self, button, interaction):
    #         self.stop()
    #
    #     @ui.button(emoji='<:next_check:754948796361736213>', style=discord.ButtonStyle.blurple)
    #     async def next_page(self, button, interaction):
    #         await self.show_checked_page(self.current_page + 1)
    #
    #     @ui.button(emoji='<:next_fast_check:754948796391227442>', style=discord.ButtonStyle.blurple)
    #     async def last_page(self, interaction, button):
    #         # page = await self._source.get_page(self.current_page)
    #         kwargs = await self._get_kwargs_from_page(self._source.get_max_pages() - 1)
    #
    #         await interaction.response.edit_message(embed=kwargs)
    #
    # class MySource(menus.ListPageSource):
    #     async def format_page(self, menu, entries):
    #         embed = discord.Embed(
    #             description=f"This is number {entries}.",
    #             color=discord.Colour.random()
    #         )
    #         embed.set_footer(text=f"Requested by {menu.ctx.author}")
    #         return embed
    #
    # @commands.command()
    # async def a(self, ctx):
    #     data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    #     formatter = HelpCommand.MySource(data, per_page=1)  # MySource came from Custom MenuPages subtopic. [Please refer to that]
    #     menu = HelpCommand.MyMenuPages(formatter)
    #     await menu.start(ctx)

    # class MyPaginator(buttons.Paginator):
    #     def __init__(self, *args, **kwargs):
    #         super().__init__(*args, **kwargs)
    #
    # @commands.command(brief='A simple example usage of the buttons ext.')
    # async def testbutton(self, ctx):
    #     my_list = ['Hello!', 'This is a list...', '...that will become paginated soon™️']
    #     page = MyPaginator(colour=0xff1493, embed=True, entries=my_list, length=1, title='This is an example usage of buttons.', timeout=90, use_defaults=True)
    #     await page.start(ctx)


async def setup(bot):
    # bot.help_command = HelpCommand.MyHelp()
    await bot.add_cog(HelpCommand(bot))
