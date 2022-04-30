import logging
from typing import Optional

import asyncpg
import discord
from aiohttp import ClientSession
from discord.ext import commands
from discord.ext.commands import Context

log = logging.getLogger(__name__)


class CustomContextCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.bot.get_context = self.get_context

    # Custom Context
    class MyContext(commands.Context):

        async def tick(self, value):
            emoji = '\N{WHITE HEAVY CHECK MARK}' if value else '\N{CROSS MARK}'
            try:
                await self.message.add_reaction(emoji)
            except discord.HTTPException:
                pass

        @property
        def session(self) -> ClientSession:
            return self.bot.session

        @property
        def pool(self) -> asyncpg.Pool:
            return self.bot.pool

        class ConfirmationView(discord.ui.View):
            def __init__(self, *, timeout: float, author_id: int, ctx: Context, delete_after: bool) -> None:
                super().__init__(timeout=timeout)
                self.value: Optional[bool] = None
                self.delete_after: bool = delete_after
                self.author_id: int = author_id
                self.ctx: Context = ctx
                self.message: Optional[discord.Message] = None

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                if interaction.user and interaction.user.id == self.author_id:
                    return True
                else:
                    await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
                    return False

            async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
                log.exception(error)
                if interaction.response.is_done():
                    await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
                else:
                    await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

            async def on_timeout(self) -> None:
                if self.delete_after and self.message:
                    await self.message.delete()

            @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = True
                await interaction.response.defer()
                if self.delete_after:
                    await interaction.delete_original_message()
                self.stop()

            @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = False
                await interaction.response.defer()
                if self.delete_after:
                    await interaction.delete_original_message()
                self.stop()

        async def prompt(
                self,
                message: str,
                embed: discord.Embed = None,
                *,
                timeout: float = 60.0,
                delete_after: bool = True,
                author_id: Optional[int] = None,
        ) -> Optional[bool]:
            """An interactive reaction confirmation dialog.
            Parameters
            -----------
            message: str
                The message to show along with the prompt.
            timeout: float
                How long to wait before returning.
            delete_after: bool
                Whether to delete the confirmation message after we're done.
            author_id: Optional[int]
                The member who should respond to the prompt. Defaults to the author of the
                Context's message.
            Returns
            --------
            Optional[bool]
                ``True`` if explicit confirm,
                ``False`` if explicit deny,
                ``None`` if deny due to timeout
            """

            author_id = author_id or self.author.id
            view = self.ConfirmationView(
                timeout=timeout,
                delete_after=delete_after,
                ctx=self,
                author_id=author_id,
            )
            view.message = await self.send(content=message, embed=embed, view=view)
            await view.wait()
            return view.value

    async def get_context(self, message, *, cls=MyContext):
        return await super(commands.Bot, self.bot).get_context(message, cls=cls)

    # Example usage:
    # @commands.command()
    # async def guess(self, ctx, number: int):
    #     value = random.randint(1, 2)
    #     await ctx.tick(number == value)


async def setup(bot):
    await bot.add_cog(CustomContextCog(bot))
